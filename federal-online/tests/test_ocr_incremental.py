"""OCR is bounded, incremental, and never automatically privacy-approved."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fo_hub.pdf_privacy import PRIVACY_POLICY_VERSION, sanitize_page
from fo_hub.store import FOStore


def test_watermark_only_page_requires_visual_ocr():
    page = sanitize_page("PESSOA FICTICIA 52998224725 " * 5)
    assert page.quality == "ocr_pending"
    assert page.text == ""


def seed(tmp_path):
    state = tmp_path / "state"
    (state / "materials").mkdir(parents=True)
    (state / "materials/a.pdf").write_bytes(b"%PDF-synthetic")
    store = FOStore(state / "hub.sqlite3")
    store.upsert_material({"material_id": "m", "relative_path": "materials/a.pdf"})
    store.set_pdf_pages("m", [""])
    with store.conn:
        store.conn.execute("INSERT INTO pdf_page_quality VALUES(?,?,?,?,?,?,?,?)",
                           ("m", 1, "ocr_pending", "blocked", 0, 0, "now", PRIVACY_POLICY_VERSION))
    return state, store


def test_ocr_keeps_visual_output_blocked_and_does_not_repeat_completed_page(tmp_path):
    from fo_hub.ocr import process_pending
    state, store = seed(tmp_path)
    calls = []
    def extract(path, page, temp):
        calls.append(page)
        return "Texto didatico reconhecido em imagem sintetica."
    result = process_pending(state, store, extractor=extract, available_bytes=10**10)
    assert result["processed"] == 1
    page = store.get_pdf_text("m")["pages"][0]
    assert page["quality"] == "ocr_review"
    assert page["text"] == ""
    process_pending(state, store, extractor=extract, available_bytes=10**10)
    assert calls == [1]


def test_ocr_does_not_work_below_disk_reserve(tmp_path):
    from fo_hub.ocr import process_pending
    state, store = seed(tmp_path)
    def forbidden(*args):
        raise AssertionError("must not extract")
    assert process_pending(state, store, extractor=forbidden, available_bytes=1)["reason"] == "disk_reserve"


def test_ocr_failure_records_only_exception_type_and_backs_off(tmp_path):
    from fo_hub.ocr import process_pending
    state, store = seed(tmp_path)
    calls = []
    def failure(*args):
        calls.append(1)
        raise ValueError("sensitive synthetic context must not be stored")
    process_pending(state, store, extractor=failure, available_bytes=10**10)
    process_pending(state, store, extractor=failure, available_bytes=10**10)
    assert calls == [1]
    row = store.conn.execute("SELECT attempts,last_error FROM pdf_ocr_jobs").fetchone()
    assert tuple(row) == (1, "ValueError")


def test_ocr_rejects_source_outside_private_material_tree(tmp_path):
    from fo_hub.ocr import process_pending
    state, store = seed(tmp_path)
    with store.conn:
        store.conn.execute("UPDATE materials SET relative_path='../outside.pdf'")
    def forbidden(*args):
        raise AssertionError("must not extract")
    result = process_pending(state, store, extractor=forbidden, available_bytes=10**10)
    assert result["errors"] == 1


def seed_remote(tmp_path, quality="ocr_needed"):
    """Production shape: the local original was removed after OneDrive receipt."""
    state, store = seed(tmp_path)
    (state / "materials/a.pdf").unlink()
    with store.conn:
        store.conn.execute("UPDATE pdf_page_quality SET quality=?", (quality,))
        store.conn.execute("CREATE TABLE IF NOT EXISTS material_originals(material_id TEXT NOT NULL,course_id TEXT,"
                           "relative_path TEXT,onedrive_path TEXT NOT NULL,byte_sha256 TEXT,quickxor TEXT,size INTEGER,"
                           "observed_at TEXT,PRIMARY KEY(material_id,onedrive_path))")
        store.conn.execute("INSERT INTO material_originals VALUES('m','c','materials/a.pdf',"
                           "'onedrive:Federal Online PDFs/a.pdf','abc',NULL,1,'now')")
    return state, store


def test_ocr_needed_page_uses_verified_transient_onedrive_original(tmp_path):
    from fo_hub.ocr import process_pending
    state, store = seed_remote(tmp_path)
    fetched, seen = [], []
    def fetch(remote, sha, dest):
        fetched.append((remote, sha))
        dest.write_bytes(b"%PDF-synthetic")
        return dest
    def extract(path, page, temp):
        seen.append(path)
        assert path.is_file()
        return "Texto didatico reconhecido em imagem sintetica."
    result = process_pending(state, store, extractor=extract, fetcher=fetch, available_bytes=10**10)
    assert result["processed"] == 1 and fetched == [("onedrive:Federal Online PDFs/a.pdf", "abc")]
    assert store.get_pdf_text("m")["pages"][0]["quality"] == "ocr_review"
    # Original only on OneDrive: the transient copy is gone, nothing under materials/.
    assert not seen[0].exists()
    assert not list((state / "tmp/ocr").iterdir())
    assert not (state / "materials/a.pdf").exists()


def test_ocr_failed_fetch_backs_off_without_local_copy(tmp_path):
    from fo_hub.ocr import process_pending
    state, store = seed_remote(tmp_path)
    def bad(remote, sha, dest):
        dest.write_bytes(b"tampered")
        raise ValueError("original checksum mismatch")
    def forbidden(*args):
        raise AssertionError("must not extract")
    result = process_pending(state, store, extractor=forbidden, fetcher=bad, available_bytes=10**10)
    assert result["errors"] == 1
    assert tuple(store.conn.execute("SELECT attempts,last_error FROM pdf_ocr_jobs").fetchone()) == (1, "ValueError")
    assert not list((state / "tmp/ocr").iterdir())
