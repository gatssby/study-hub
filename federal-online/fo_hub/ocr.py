"""Low-resource incremental PDF OCR. Output remains blocked for visual review.

Run only through the unit sharing index.lock: no concurrent indexer/OCR.
Original private PDFs are never changed or exposed as downloadable artifacts.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from .pdf_privacy import PRIVACY_POLICY_VERSION, sanitize_page
from .store import FOStore

RESERVE_BYTES = 4 * 1024**3


def extract_page(path: Path, page: int, temp: Path) -> str:
    env = {**os.environ, "OMP_THREAD_LIMIT": "1", "OMP_NUM_THREADS": "1"}
    prefix = temp / "page"
    subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page), "-singlefile",
                    "-scale-to", "1800", "-png", str(path), str(prefix)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   timeout=60, check=True, env=env)
    image = prefix.with_suffix(".png")
    if image.stat().st_size > 20 * 1024**2:
        raise ValueError("render size limit")
    result = subprocess.run(["tesseract", str(image), "stdout", "-l", "por+eng", "--psm", "11"],
                            capture_output=True, timeout=90, check=True, env=env)
    if len(result.stdout) > 1024**2:
        raise ValueError("OCR text size limit")
    return result.stdout.decode("utf-8", errors="replace")


def fetch_original(remote: str, sha256: str, dest: Path) -> Path:
    """Transient, verified copy of an OneDrive original (the only durable copy)."""
    import hashlib
    subprocess.run(["rclone", "copyto", remote, str(dest), "--retries", "3"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600, check=True)
    digest = hashlib.sha256()
    with dest.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    if not sha256 or digest.hexdigest() != sha256:
        dest.unlink(missing_ok=True)
        raise ValueError("original checksum mismatch")
    return dest


def process_pending(state, store, *, extractor=extract_page, available_bytes=None, limit=3,
                    fetcher=fetch_original):
    state = Path(state)
    c = store.conn
    c.execute("CREATE TABLE IF NOT EXISTS pdf_ocr_jobs("
              "material_id TEXT,page INTEGER,attempts INTEGER NOT NULL DEFAULT 0,"
              "next_retry REAL NOT NULL DEFAULT 0,last_error TEXT,"
              "PRIMARY KEY(material_id,page))")
    if available_bytes is None:
        available_bytes = shutil.disk_usage(state).free
    if available_bytes < RESERVE_BYTES + 128 * 1024**2:
        return {"processed": 0, "errors": 0, "reason": "disk_reserve"}
    # Do not compete with unfinished privacy review even if invoked manually.
    if c.execute("SELECT COUNT(*) FROM pdf_pages p LEFT JOIN pdf_page_quality q "
                 "USING(material_id,page) WHERE q.page IS NULL OR q.policy_version!=?",
                 (PRIVACY_POLICY_VERSION,)).fetchone()[0]:
        return {"processed": 0, "errors": 0, "reason": "privacy_review_pending"}
    # 'ocr_needed' comes from the vector extractor (image page without text);
    # 'ocr_pending' from the privacy classifier. Both need visual OCR.
    rows = c.execute(
        "SELECT q.material_id,q.page,m.relative_path,COALESCE(j.attempts,0) "
        "FROM pdf_page_quality q JOIN materials m USING(material_id) "
        "LEFT JOIN pdf_ocr_jobs j USING(material_id,page) "
        "WHERE q.quality IN ('ocr_pending','ocr_needed') AND q.policy_version=? "
        "AND COALESCE(j.attempts,0)<3 AND COALESCE(j.next_retry,0)<=? "
        "ORDER BY q.material_id,q.page LIMIT ?",
        (PRIVACY_POLICY_VERSION, time.time(), max(1, min(limit, 25)))).fetchall()
    processed = errors = 0
    temp_root = state / "tmp" / "ocr"
    temp_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Recover only this worker's transient rasters/originals. index.lock is
    # exclusive for the whole unit lifetime, so no live peer can own these.
    for stale in list(temp_root.glob("page-*")) + list(temp_root.glob("orig-*")):
        if stale.is_dir() and not stale.is_symlink():
            shutil.rmtree(stale)
    fetched = {}
    originals = tempfile.mkdtemp(prefix="orig-", dir=temp_root)
    try:
        for mid, number, relative, attempts in rows:
            try:
                source = (state / (relative or "")).resolve()
                if not source.is_relative_to((state / "materials").resolve()):
                    raise ValueError("private source outside material tree")
                if not source.is_file():
                    # Originals live only on OneDrive: fetch a verified transient copy.
                    if mid not in fetched:
                        remote = c.execute(
                            "SELECT onedrive_path,byte_sha256 FROM material_originals "
                            "WHERE material_id=? AND onedrive_path LIKE 'onedrive:%' "
                            "AND byte_sha256 IS NOT NULL ORDER BY onedrive_path LIMIT 1", (mid,)).fetchone()
                        if not remote:
                            raise ValueError("private source unavailable")
                        fetched[mid] = fetcher(remote[0], remote[1], Path(originals) / f"{mid}.pdf")
                    source = fetched[mid]
                with tempfile.TemporaryDirectory(prefix="page-", dir=temp_root) as temp:
                    page = sanitize_page(extractor(source, number, Path(temp)))
                # OCR can miss visual PII. Its text is NEVER auto-approved.
                quality = "ocr_review" if page.text else ("privacy_review" if page.quality == "privacy_review" else "ocr_empty")
                with c:
                    c.execute("UPDATE pdf_pages SET text=? WHERE material_id=? AND page=?",
                              (page.text, mid, number))
                    c.execute("UPDATE pdf_page_quality SET quality=?,exposure='blocked',"
                              "extracted_chars=?,pii_redacted=?,updated_at=? WHERE material_id=? AND page=?",
                              (quality, len(page.text), int(page.pii_redacted),
                               time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), mid, number))
                    c.execute("INSERT OR REPLACE INTO pdf_ocr_jobs VALUES(?,?,?,?,?)",
                              (mid, number, attempts + 1, 0, None))
                processed += 1
            except Exception as exc:
                with c:
                    c.execute("INSERT OR REPLACE INTO pdf_ocr_jobs VALUES(?,?,?,?,?)",
                              (mid, number, attempts + 1, time.time() + 3600 * 2**attempts, type(exc).__name__))
                errors += 1
    finally:
        # The transient original never outlives the run.
        shutil.rmtree(originals, ignore_errors=True)
    return {"processed": processed, "errors": errors, "exposure": "blocked"}


def main():
    if not all(shutil.which(command) for command in ("pdftoppm", "tesseract")):
        print(json.dumps({"processed": 0, "reason": "ocr_dependencies_missing"}))
        return
    state = Path(os.environ.get("FO_STATE_ROOT", "/home/ubuntu/study-hub-state/federal-online"))
    store = FOStore(os.environ.get("STUDY_HUB_FO_DB", str(state / "hub.sqlite3")))
    try:
        print(json.dumps(process_pending(state, store)))
    finally:
        store.conn.close()


if __name__ == "__main__":
    main()
