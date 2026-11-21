"""Deterministic recovery of canonical portal metadata for remote fallback lessons.

Remote OneDrive objects at legacy paths create fallback lesson identities whose
subject/module/title are derived from private folders. When the same portal media
already has a present canonical lesson, the fallback is a duplicate identity:

* unprotected fallbacks (no transcript, no leased/done/review job) are retired as
  verified aliases — the canonical lesson already covers the media with an
  available current source;
* protected fallbacks (validated/review transcript evidence) keep their identity
  and receive the canonical portal subject/front/module/title.

Links are established only from verified existing evidence: the legacy folder
hierarchy (the historical portal source_ref) plus the exact lesson title, matched
against the current per-course catalog with explicit, audited normalizations, then
resolved to a unique present portal lesson by (course_id, media_id). No title is
invented; anything that does not resolve uniquely is left untouched and reported.

Read-only ``plan``; transactional, reversible ``apply`` (preimage + ledger). No
download, no decode, no deletion, no identity/version change.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import unicodedata
from urllib.parse import urlsplit

from portal.fo_media_identity import canonical_media_url

POLICY_VERSION = 1
_HASH_FOLDER = re.compile(r"[0-9a-f]{16,32}")
_YEAR = re.compile(r"((?:19|20)\d{2}) - ((?:19|20)?\d{2})")
_SIMULADO = re.compile(r"(simulado \d+) - ")


def norm(value) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.casefold().split())


def course_key(url) -> str:
    parts = urlsplit(url or "").path.strip("/").split("/")
    if "produto-pacote" in parts and len(parts) > parts.index("produto-pacote") + 1:
        return parts[parts.index("produto-pacote") + 1]
    return canonical_media_url(url)


def path_source_ref(module: str) -> str:
    parts = [p for p in str(module or "").split(" > ") if not _HASH_FOLDER.fullmatch(p)]
    return " > ".join(parts[1:]) if len(parts) > 1 else ""


def _entry_titles(entry):
    return {norm(entry.get("titulo_original")), norm(entry.get("nome_real_aula"))} - {""}


def _title_variants(title: str):
    """Audited deterministic normalizations of the same source reference/title."""
    t = norm(title)
    yield "exact", t
    yield "year", _YEAR.sub(r"\1/\2", t)
    # single ' - ' -> ': ' separator rename (e.g. "Karl Popper - Introdução")
    positions = [m.start() for m in re.finditer(r" - ", t)]
    for pos in positions:
        yield "separator", t[:pos] + ": " + t[pos + 3:]


def match_catalog(entries, source_ref: str, title: str):
    """Return (media_id, tier, entry) for a unique match, else (None, reason, None)."""
    sr = norm(source_ref)
    # Audited source_ref renames: "Simulado N - " -> "Simulado N: ".
    sr_variants = {sr, _SIMULADO.sub(r"\1: ", sr)}
    same_ref = [e for e in entries if norm(e.get("source_ref")) in sr_variants]
    if not same_ref:
        return None, "no_source_ref_match", None
    # Tier 1: title match (exact / year-range / separator rename) under the source_ref.
    for tier, variant in _title_variants(title):
        hits = [e for e in same_ref if variant in _entry_titles(e)]
        ids = {str(e.get("media_id")) for e in hits if e.get("media_id")}
        if len(ids) == 1:
            return ids.pop(), tier, hits[0]
        if len(ids) > 1:
            return None, "ambiguous_title", None
    # Tier 2: portal renamed the title (same source_ref, unique prefix extension).
    t = norm(title)
    prefix = [e for e in same_ref
              if any(et.startswith(t) and et != t for et in _entry_titles(e))]
    ids = {str(e.get("media_id")) for e in prefix if e.get("media_id")}
    if len(ids) == 1:
        return ids.pop(), "title_updated", prefix[0]
    if len(ids) > 1:
        return None, "ambiguous_title_update", None
    return None, "no_title_match", None


def _digest(actions):
    return hashlib.sha256(json.dumps(actions, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _load_catalog(state: Path):
    # Keyed by the course URL's last path segment (the portal course slug), which
    # is what legacy remote folder names preserve. entry['course_url'] still gives
    # the produto-pacote course_key used to resolve the canonical DB lesson.
    catalog = {}
    root = state / "catalog/courses"
    if root.is_dir():
        for path in sorted(root.glob("*/aulas_index.json")):
            try:
                payload = json.loads(path.read_text())
            except (OSError, ValueError):
                continue
            url = payload.get("course_url") or ""
            slug = norm(urlsplit(url).path.rstrip("/").split("/")[-1])
            if slug:
                for entry in payload.get("aulas", []):
                    entry.setdefault("course_url", url)
                catalog.setdefault(slug, []).extend(payload.get("aulas", []))
    return catalog


def _protected(conn, lesson_id):
    if conn.execute("SELECT 1 FROM transcripts WHERE lesson_id=? LIMIT 1", (lesson_id,)).fetchone():
        return True
    return conn.execute("SELECT 1 FROM transcription_jobs WHERE lesson_id=? AND state IN ('leased','done','review') LIMIT 1",
                        (lesson_id,)).fetchone() is not None


def plan(state_root, db_path) -> dict:
    state = Path(state_root).resolve()
    catalog = _load_catalog(state)
    registry = {}
    try:
        for course in json.loads((state / "catalog/courses.json").read_text()).get("courses", []):
            registry[course_key(course.get("url"))] = course.get("title")
    except (OSError, ValueError, TypeError):
        pass
    actions, unresolved = [], []
    with closing(sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)) as c:
        c.row_factory = sqlite3.Row
        c.execute("BEGIN")
        remotes = [dict(r) for r in c.execute(
            "SELECT * FROM lessons WHERE present=1 AND course_id LIKE 'remote:%' ORDER BY lesson_id")]
        for remote in remotes:
            lid = remote["lesson_id"]
            source = c.execute("SELECT * FROM lesson_video_sources WHERE lesson_id=?", (lid,)).fetchone()
            slug = norm(remote["course_id"].removeprefix("remote:")).replace(" ", "-")
            entries = catalog.get(slug, [])
            sr = path_source_ref(remote["module"])
            media_id, tier, entry = match_catalog(entries, sr, remote["title"])
            base = {"lesson_id": lid, "remote_course_id": remote["course_id"],
                    "remote_title": remote["title"], "path_source_ref": sr,
                    "remote_media_id": remote["media_id"], "version": remote["version"],
                    "source_available": source["available"] if source else None}
            if media_id is None or entry is None:
                unresolved.append({**base, "reason": tier})
                continue
            canonical = [dict(r) for r in c.execute(
                "SELECT * FROM lessons WHERE course_id=? AND media_id=? AND present=1",
                (course_key(entry.get("course_url")), media_id))]
            if len(canonical) != 1:
                unresolved.append({**base, "reason": "canonical_not_unique", "media_id": media_id,
                                   "candidates": [x["lesson_id"] for x in canonical]})
                continue
            canon = canonical[0]
            csource = c.execute("SELECT * FROM lesson_video_sources WHERE lesson_id=?", (canon["lesson_id"],)).fetchone()
            canon_available = bool(csource and csource["available"] == 1
                                   and str(csource["revision"]) == str(canon["version"])
                                   and csource["remote_path"])
            protected = _protected(c, lid)
            if not protected and not canon_available:
                unresolved.append({**base, "reason": "canonical_source_unavailable", "media_id": media_id,
                                   "canonical_lesson_id": canon["lesson_id"]})
                continue
            action = "backfill_protected" if protected else "retire_alias"
            actions.append({
                **base, "action": action, "match_tier": tier, "media_id": media_id,
                "canonical_lesson_id": canon["lesson_id"], "canonical_course_id": canon["course_id"],
                "course_title": registry.get(canon["course_id"]),
                "canonical": {k: canon[k] for k in ("subject", "front", "module", "title")},
                "canonical_source_available": canon_available,
                "preimage": {k: remote[k] for k in ("subject", "front", "module", "title")},
                "evidence": {"matched_source_ref": entry.get("source_ref"),
                             "matched_title": entry.get("titulo_original") or entry.get("nome_real_aula"),
                             "matched_media_id": media_id, "tier": tier,
                             "canonical_present": True, "canonical_source_available": canon_available,
                             "protected": protected}})
    actions.sort(key=lambda x: x["lesson_id"])
    return {"schema_version": 1, "observed_at": datetime.now(timezone.utc).isoformat(),
            "policy_version": POLICY_VERSION, "read_only": True,
            "counts": {"remote_present": len(remotes), "actions": len(actions),
                       "retire_alias": sum(a["action"] == "retire_alias" for a in actions),
                       "backfill_protected": sum(a["action"] == "backfill_protected" for a in actions),
                       "unresolved": len(unresolved),
                       "by_tier": dict(Counter(a["match_tier"] for a in actions)),
                       "unresolved_reasons": dict(Counter(u["reason"] for u in unresolved))},
            "actions": actions, "unresolved": unresolved, "plan_sha256": _digest(actions)}


def apply(state_root, db_path, expected: dict) -> dict:
    actions = expected.get("actions", [])
    digest = expected.get("plan_sha256")
    if expected.get("schema_version") != 1 or _digest(actions) != digest:
        raise ValueError("invalid plan checksum or schema")
    with closing(sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=rw", uri=True, timeout=15)) as c:
        c.row_factory = sqlite3.Row
        try:
            c.execute("BEGIN IMMEDIATE")
            c.execute("""CREATE TABLE IF NOT EXISTS lesson_metadata_recovery(
                lesson_id TEXT PRIMARY KEY, remote_course_id TEXT, canonical_lesson_id TEXT,
                canonical_course_id TEXT, course_title TEXT, subject TEXT, front TEXT, module TEXT,
                title TEXT, media_id TEXT, action TEXT NOT NULL, evidence_json TEXT NOT NULL,
                preimage_json TEXT NOT NULL, plan_sha256 TEXT NOT NULL,
                policy_version INTEGER NOT NULL DEFAULT 1, recovered_at TEXT NOT NULL)""")
            at = datetime.now(timezone.utc).isoformat()
            retired = backfilled = skipped = 0
            for action in actions:
                lid = action["lesson_id"]
                existing = c.execute("SELECT * FROM lesson_metadata_recovery WHERE lesson_id=?", (lid,)).fetchone()
                if existing and existing["plan_sha256"] == digest:
                    skipped += 1
                    continue
                remote = c.execute("SELECT * FROM lessons WHERE lesson_id=?", (lid,)).fetchone()
                canon = c.execute("SELECT * FROM lessons WHERE lesson_id=? AND present=1",
                                  (action["canonical_lesson_id"],)).fetchone()
                if remote is None or canon is None or not remote["present"]:
                    raise ValueError(f"stale identity during apply: {lid}")
                if _protected(c, lid) != action["evidence"]["protected"]:
                    raise ValueError(f"protection changed during apply: {lid}")
                if action["action"] == "retire_alias":
                    csource = c.execute("SELECT * FROM lesson_video_sources WHERE lesson_id=?",
                                        (action["canonical_lesson_id"],)).fetchone()
                    if not (csource and csource["available"] == 1
                            and str(csource["revision"]) == str(canon["version"]) and csource["remote_path"]):
                        raise ValueError(f"canonical source no longer available: {lid}")
                    c.execute("UPDATE lessons SET present=0 WHERE lesson_id=? AND present=1", (lid,))
                    c.execute("UPDATE lesson_video_sources SET available=0 WHERE lesson_id=?", (lid,))
                    c.execute("UPDATE transcription_jobs SET state='superseded' WHERE lesson_id=? AND state='queued'", (lid,))
                    retired += 1
                else:
                    fields = action["canonical"]
                    c.execute("UPDATE lessons SET subject=?,front=?,module=?,title=? WHERE lesson_id=?",
                              (fields["subject"], fields["front"], fields["module"], fields["title"], lid))
                    backfilled += 1
                c.execute("INSERT OR REPLACE INTO lesson_metadata_recovery VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (lid, action["remote_course_id"], action["canonical_lesson_id"],
                           action["canonical_course_id"], action["course_title"],
                           action["canonical"]["subject"], action["canonical"]["front"],
                           action["canonical"]["module"], action["canonical"]["title"], action["media_id"],
                           action["action"], json.dumps(action["evidence"], sort_keys=True),
                           json.dumps(action["preimage"], sort_keys=True), digest, POLICY_VERSION, at))
            c.commit()
            return {"retired": retired, "backfilled": backfilled, "already_applied": skipped,
                    "plan_sha256": digest}
        except BaseException:
            c.rollback()
            raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-root", required=True, type=Path)
    parser.add_argument("--db", type=Path)
    parser.add_argument("--apply-plan", type=Path)
    args = parser.parse_args(argv)
    db = args.db or args.state_root / "hub.sqlite3"
    if args.apply_plan:
        result = apply(args.state_root, db, json.loads(args.apply_plan.read_text()))
    else:
        result = plan(args.state_root, db)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
