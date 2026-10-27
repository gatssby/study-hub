"""Durable SQLite store for the Federal Online (FO) content hub.

Lesson identity is derived from (course_id, media_id) — falling back to item_id
when media_id is absent — never from titles. Revisions distinguish renames
(title/metadata only) from media changes (video URL or duration). Items absent
from a sync are marked ``present=0``; nothing is ever deleted.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit, urlunsplit

from .pdf_privacy import PRIVACY_POLICY_VERSION, sanitize_page

DB_ENV = "STUDY_HUB_FO_DB"
DEFAULT_DB = "fo_hub.db"
ACCEPTED_CORPUS = "generated_v2"

SCHEMA = """
CREATE TABLE IF NOT EXISTS lessons(
  lesson_id TEXT PRIMARY KEY, course_id TEXT NOT NULL, media_id TEXT, item_id TEXT,
  subject TEXT, front TEXT, module TEXT, title TEXT, media_type TEXT,
  video_url TEXT, duration_s REAL, version INTEGER NOT NULL DEFAULT 1,
  present INTEGER NOT NULL DEFAULT 1, first_seen TEXT, last_seen TEXT);
CREATE TABLE IF NOT EXISTS lesson_revisions(
  id INTEGER PRIMARY KEY AUTOINCREMENT, lesson_id TEXT NOT NULL, version INTEGER NOT NULL,
  change_kind TEXT NOT NULL, title TEXT, video_url TEXT, duration_s REAL,
  run_id TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS materials(
  material_id TEXT PRIMARY KEY, lesson_id TEXT, subject TEXT, front TEXT, module TEXT,
  title TEXT, material_type TEXT, relative_path TEXT, sha256 TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS pdf_pages(
  material_id TEXT NOT NULL, page INTEGER NOT NULL, text TEXT NOT NULL,
  PRIMARY KEY(material_id, page));
CREATE TABLE IF NOT EXISTS pdf_page_quality(
  material_id TEXT NOT NULL, page INTEGER NOT NULL, quality TEXT NOT NULL,
  exposure TEXT NOT NULL, extracted_chars INTEGER NOT NULL DEFAULT 0,
  pii_redacted INTEGER NOT NULL DEFAULT 0, updated_at TEXT,
  policy_version INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY(material_id, page));
CREATE TABLE IF NOT EXISTS transcripts(
  lesson_id TEXT NOT NULL, version INTEGER NOT NULL, model TEXT, corpus TEXT NOT NULL,
  qa_json TEXT, created_at TEXT, PRIMARY KEY(lesson_id, version));
CREATE TABLE IF NOT EXISTS transcript_segments(
  lesson_id TEXT NOT NULL, version INTEGER NOT NULL, idx INTEGER NOT NULL,
  start REAL, end REAL, text TEXT, PRIMARY KEY(lesson_id, version, idx));
CREATE TABLE IF NOT EXISTS sync_runs(
  run_id TEXT PRIMARY KEY, at TEXT, created INTEGER, renamed INTEGER,
  media_changed INTEGER, unchanged INTEGER, missing INTEGER);
CREATE TABLE IF NOT EXISTS transcription_jobs(
  lesson_id TEXT NOT NULL, version INTEGER NOT NULL, state TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL DEFAULT 3,
  lease_owner TEXT, lease_until REAL, progress REAL NOT NULL DEFAULT 0,
  last_error TEXT, created_at TEXT, updated_at TEXT, PRIMARY KEY(lesson_id, version));
CREATE INDEX IF NOT EXISTS ix_mat_subject ON materials(subject);
CREATE INDEX IF NOT EXISTS ix_seg_lv ON transcript_segments(lesson_id, version);
"""


class TranscriptRejected(ValueError):
    """Raised when a transcript is not validated / not from the new corpus / stale."""


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def lesson_id_for(course_id: str, media_id: str | None, item_id: str | None) -> str:
    if not course_id or not (media_id or item_id):
        raise ValueError('course and stable media/item ID required')
    key = f"media:{media_id}" if media_id else f"item:{item_id}"
    digest = hashlib.sha256(f"{course_id}|{key}".encode()).hexdigest()[:16]
    return f"fo_{digest}"


def _like(v: str) -> str:
    return "%" + v.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


class FOStore:
    def __init__(self, path: str | os.PathLike, readonly: bool = False):
        self.path = Path(path)
        self.readonly = readonly
        if readonly:
            self.conn = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True,
                                        check_same_thread=False)
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(self.path, check_same_thread=False)
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.executescript(SCHEMA)
        self.conn.row_factory = sqlite3.Row

    @classmethod
    def from_env(cls, readonly: bool = False) -> "FOStore":
        return cls(os.environ.get(DB_ENV, DEFAULT_DB), readonly=readonly)

    # ---------- lessons ----------
    def sync_lessons(self, rows: Iterable[Mapping[str, Any]], *, authoritative: bool = False) -> dict:
        run_id, at = uuid.uuid4().hex, _now()
        counts = dict(created=0, renamed=0, media_changed=0, unchanged=0, missing=0)
        seen: set[str] = set()
        c = self.conn
        with c:
            for r in rows:
                lid = lesson_id_for(str(r["course_id"]), r.get("media_id"), r.get("item_id"))
                seen.add(lid)
                dur = float(r["duration_s"]) if r.get("duration_s") not in (None, "") else None
                f = {k: r.get(k) for k in ("subject", "front", "module", "title", "media_type")}
                old = c.execute("SELECT * FROM lessons WHERE lesson_id=?", (lid,)).fetchone()
                if old is None:
                    kind, ver = "created", 1
                    c.execute(
                        "INSERT INTO lessons VALUES(?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)",
                        (lid, r["course_id"], r.get("media_id"), r.get("item_id"), f["subject"],
                         f["front"], f["module"], f["title"], f["media_type"],
                         r.get("video_url"), dur, ver, at, at))
                else:
                    ver = old["version"]
                    def media_url(value):
                        parts = urlsplit(value or '')
                        return urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))
                    if media_url(old["video_url"]) != media_url(r.get("video_url")) or old["duration_s"] != dur:
                        kind, ver = "media_changed", ver + 1
                    elif any(old[k] != f[k] for k in f):
                        kind = "renamed"
                    else:
                        kind = "unchanged"
                    c.execute(
                        "UPDATE lessons SET subject=?,front=?,module=?,title=?,media_type=?,"
                        "video_url=?,duration_s=?,version=?,present=1,last_seen=?,item_id=? "
                        "WHERE lesson_id=?",
                        (f["subject"], f["front"], f["module"], f["title"], f["media_type"],
                         r.get("video_url"), dur, ver, at, r.get("item_id"), lid))
                counts[kind] += 1
                if kind != "unchanged":
                    c.execute(
                        "INSERT INTO lesson_revisions(lesson_id,version,change_kind,title,"
                        "video_url,duration_s,run_id,at) VALUES(?,?,?,?,?,?,?,?)",
                        (lid, ver, kind, f["title"], r.get("video_url"), dur, run_id, at))
            if authoritative and seen:
                courses = {c.execute('SELECT course_id FROM lessons WHERE lesson_id=?', (lid,)).fetchone()[0] for lid in seen}
                for lid, course in c.execute("SELECT lesson_id,course_id FROM lessons WHERE present=1").fetchall():
                    if course in courses and lid not in seen:
                        c.execute("UPDATE lessons SET present=0 WHERE lesson_id=?", (lid,))
                        counts["missing"] += 1
            c.execute("INSERT INTO sync_runs VALUES(?,?,?,?,?,?,?)",
                      (run_id, at, counts["created"], counts["renamed"],
                       counts["media_changed"], counts["unchanged"], counts["missing"]))
        return {**counts, "run_id": run_id}

    @staticmethod
    def _lesson(r: sqlite3.Row) -> dict:
        d = dict(r)
        d["present"] = bool(d["present"])
        d['citation'] = {'name': d['title'], 'id': d['lesson_id'], 'version': d['version'], 'updated_at': d['last_seen'], 'course': d['course_id'], 'hierarchy': d['module']}
        return d

    def list_lessons(self, subject: str | None = None, front: str | None = None,
                     module: str | None = None, title: str | None = None,
                     include_missing: bool = False, limit: int = 100,
                     offset: int = 0) -> list[dict]:
        where, args = self._filters(subject=subject, front=front, module=module, title=title)
        if not include_missing:
            where.append("present=1")
        sql = "SELECT * FROM lessons" + (" WHERE " + " AND ".join(where) if where else "")
        sql += " ORDER BY subject, module, title, lesson_id LIMIT ? OFFSET ?"
        return [self._lesson(r) for r in self.conn.execute(sql, (*args, limit, offset))]

    def get_lesson(self, lesson_id: str) -> dict | None:
        r = self.conn.execute("SELECT * FROM lessons WHERE lesson_id=?", (lesson_id,)).fetchone()
        if r is None:
            return None
        d = self._lesson(r)
        d["revisions"] = [dict(x) for x in self.conn.execute(
            "SELECT version,change_kind,title,video_url,duration_s,at FROM lesson_revisions "
            "WHERE lesson_id=? ORDER BY id", (lesson_id,))]
        return d

    # ---------- materials ----------
    @staticmethod
    def _filters(**kw: str | None) -> tuple[list[str], list[Any]]:
        where, args = [], []
        for col, val in kw.items():
            if val is None or val == "":
                continue
            if col == "title":
                where.append("title LIKE ? ESCAPE '\\' COLLATE NOCASE")
                args.append(_like(val))
            else:
                where.append(f"{col} = ? COLLATE NOCASE")  # col is from fixed kwarg names
                args.append(val)
        return where, args

    def upsert_material(self, m: Mapping[str, Any]) -> None:
        cols = ("material_id", "lesson_id", "subject", "front", "module", "title",
                "material_type", "relative_path", "sha256")
        with self.conn:
            self.conn.execute(
                f"INSERT INTO materials({','.join(cols)},updated_at) VALUES({','.join('?'*10)}) "
                "ON CONFLICT(material_id) DO UPDATE SET "
                + ",".join(f"{c}=excluded.{c}" for c in cols[1:])
                + ",updated_at=excluded.updated_at",
                (*[m.get(c) for c in cols], _now()))

    def search_materials(self, subject: str | None = None, front: str | None = None,
                         module: str | None = None, title: str | None = None,
                         material_type: str | None = None, limit: int = 50,
                         offset: int = 0) -> list[dict]:
        where, args = self._filters(subject=subject, front=front, module=module, title=title,
                                    material_type=material_type)
        sql = "SELECT * FROM materials" + (" WHERE " + " AND ".join(where) if where else "")
        sql += " ORDER BY subject, module, title, material_id LIMIT ? OFFSET ?"
        results = []
        for row in self.conn.execute(sql, (*args, limit, offset)):
            item = dict(row)
            item['citation'] = {'id': item['material_id'], 'name': item['title'],
                                'version': item['sha256'], 'updated_at': item['updated_at']}
            # A signed original URL would bypass PDF privacy protections. Its
            # provenance stays in the private ingestion manifest, not the Plugin.
            item['source_url'] = None
            item['source_access'] = 'private_original_not_exposed'
            results.append(item)
        return results

    def set_pdf_pages(self, material_id: str, pages: list[str]) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM pdf_page_quality WHERE material_id=?", (material_id,))
            self.conn.execute("DELETE FROM pdf_pages WHERE material_id=?", (material_id,))
            self.conn.executemany("INSERT INTO pdf_pages VALUES(?,?,?)",
                                  [(material_id, i + 1, t) for i, t in enumerate(pages)])

    def get_pdf_text(self, material_id: str, page_start: int = 1,
                     page_end: int | None = None) -> dict | None:
        m = self.conn.execute("SELECT title,sha256,relative_path,updated_at FROM materials WHERE material_id=?",
                              (material_id,)).fetchone()
        if m is None:
            return None
        total = self.conn.execute("SELECT COUNT(*) FROM pdf_pages WHERE material_id=?",
                                  (material_id,)).fetchone()[0]
        end = page_end if page_end is not None else total
        rows = self.conn.execute(
            "SELECT p.page,p.text,COALESCE(q.quality,'legacy_unreviewed'),"
            "COALESCE(q.exposure,'blocked'),COALESCE(q.policy_version,0) FROM pdf_pages p "
            "LEFT JOIN pdf_page_quality q ON q.material_id=p.material_id AND q.page=p.page "
            "WHERE p.material_id=? AND p.page BETWEEN ? AND ? "
            "ORDER BY p.page", (material_id, page_start, end))
        pages = []
        for p, text, quality, exposure, policy in rows:
            allowed = (policy == max(3, PRIVACY_POLICY_VERSION) and exposure == "text_only"
                       and quality in {"text", "low_text"})
            if allowed:
                checked = sanitize_page(text)
                allowed = checked.exposure == 'text_only' and checked.text == text
            pages.append({"page": p, "text": text if allowed else "",
                          "quality": quality if policy == PRIVACY_POLICY_VERSION else "legacy_unreviewed",
                          "exposure": "text_only" if allowed else "blocked",
                          "policy_version": policy,
                          "citation": f"{m['title']}, p. {p} [{material_id}#p{p}]"})
        return {"material_id": material_id, "title": m["title"], "page_count": total,
                "pages": pages, 'version': m['sha256'], 'source': m['relative_path'], 'updated_at': m['updated_at']}

    # ---------- transcripts ----------
    def add_transcript(self, lesson_id: str, version: int, segments: list[Mapping[str, Any]],
                       model: str, corpus: str, validated: bool,
                       qa: Mapping[str, Any] | None = None) -> None:
        if corpus != ACCEPTED_CORPUS:
            raise TranscriptRejected(f"corpus {corpus!r} not accepted (need {ACCEPTED_CORPUS})")
        if not validated or (qa is not None and qa.get('passed') is False):
            raise TranscriptRejected("transcript not validated")
        qa = {**(qa or {}), 'passed': True}
        les = self.get_lesson(lesson_id)
        if les is None or les["version"] != version:
            raise TranscriptRejected("lesson missing or version is not current")
        with self.conn:
            self.conn.execute("DELETE FROM transcript_segments WHERE lesson_id=? AND version=?",
                              (lesson_id, version))
            self.conn.execute("INSERT OR REPLACE INTO transcripts VALUES(?,?,?,?,?,?)",
                              (lesson_id, version, model, corpus, json.dumps(qa or {}), _now()))
            self.conn.executemany(
                "INSERT INTO transcript_segments VALUES(?,?,?,?,?,?)",
                [(lesson_id, version, i, s["start"], s["end"], s["text"])
                 for i, s in enumerate(segments)])

    @property
    def _CURRENT(self):
        # Read-only API instances must also work against the legacy schema.
        source_guard = ''
        if self.conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='lesson_video_sources'").fetchone():
            source_guard = (" AND EXISTS(SELECT 1 FROM lesson_video_sources src WHERE "
                            "src.lesson_id=l.lesson_id AND src.available=1 "
                            "AND src.revision=CAST(l.version AS TEXT) AND src.remote_path IS NOT NULL)")
        return ("JOIN lessons l ON l.lesson_id=t.lesson_id AND l.version=t.version "
                "AND l.present=1 AND t.corpus='" + ACCEPTED_CORPUS + "' "
                "AND CASE WHEN json_valid(t.qa_json) THEN "
                "json_type(t.qa_json,'$.passed')='true' ELSE 0 END" + source_guard)

    def get_transcript(self, lesson_id: str) -> dict | None:
        t = self.conn.execute(
            f"SELECT t.* FROM transcripts t {self._CURRENT} WHERE t.lesson_id=?",
            (lesson_id,)).fetchone()
        if t is None:
            return None
        segs = [dict(r) for r in self.conn.execute(
            "SELECT idx,start,end,text FROM transcript_segments WHERE lesson_id=? AND version=? "
            "ORDER BY idx", (lesson_id, t["version"]))]
        return {"lesson_id": lesson_id, "version": t["version"], "model": t["model"],
                "qa": json.loads(t["qa_json"] or "{}"), "segments": segs}

    def search_transcripts(self, query: str, subject: str | None = None,
                           limit: int = 50) -> list[dict]:
        sql = ("SELECT s.lesson_id,s.version,s.idx,s.start,s.end,s.text,l.title,l.subject "
               "FROM transcript_segments s JOIN transcripts t ON t.lesson_id=s.lesson_id "
               f"AND t.version=s.version {self._CURRENT} "
               "WHERE s.text LIKE ? ESCAPE '\\' COLLATE NOCASE")
        args: list[Any] = [_like(query)]
        if subject:
            sql += " AND l.subject = ? COLLATE NOCASE"
            args.append(subject)
        sql += " ORDER BY l.title, s.idx LIMIT ?"
        return [dict(r) for r in self.conn.execute(sql, (*args, limit))]

    # ---------- status ----------
    def sync_status(self) -> dict:
        q = lambda s: self.conn.execute(s).fetchone()[0]  # noqa: E731
        last = self.conn.execute("SELECT * FROM sync_runs ORDER BY at DESC, rowid DESC LIMIT 1"
                                 ).fetchone()
        jobs = {r[0]: r[1] for r in self.conn.execute(
            "SELECT state,COUNT(*) FROM transcription_jobs GROUP BY state")}
        aliases = {'leased': 'processing', 'done': 'validated', 'stale': 'superseded'}
        states = dict.fromkeys(('queued', 'processing', 'validated', 'review', 'failed', 'superseded'), 0)
        for state, count in jobs.items():
            normalized = aliases.get(state, state)
            if normalized in states:
                states[normalized] += count
        processing = self.conn.execute(
            "SELECT lease_until,progress FROM transcription_jobs WHERE state IN ('leased','processing')").fetchall()
        progress = {'stale_leases': sum(r['lease_until'] is not None and r['lease_until'] <= time.time() for r in processing),
                    'processing_progress': sum(r['progress'] or 0 for r in processing) / len(processing) if processing else 0,
                    'total': sum(jobs.values()), 'unknown_states': {k: v for k, v in jobs.items() if aliases.get(k, k) not in states}}
        quality = {r[0]: r[1] for r in self.conn.execute(
            "SELECT quality,COUNT(*) FROM pdf_page_quality GROUP BY quality")}
        privacy = self.conn.execute(
            "SELECT COUNT(*),"
            "SUM(CASE WHEN q.policy_version=? THEN 1 ELSE 0 END),"
            "SUM(CASE WHEN q.policy_version=2 THEN 1 ELSE 0 END),"
            "SUM(CASE WHEN q.policy_version=? AND q.exposure='text_only' "
            "AND q.quality IN ('text','low_text') THEN 1 ELSE 0 END),"
            "SUM(CASE WHEN q.page IS NULL OR q.policy_version!=? THEN 1 ELSE 0 END),"
            "SUM(CASE WHEN q.quality='ocr_pending' THEN 1 ELSE 0 END) "
            "FROM pdf_pages p LEFT JOIN pdf_page_quality q USING(material_id,page)",
            (PRIVACY_POLICY_VERSION, PRIVACY_POLICY_VERSION, PRIVACY_POLICY_VERSION)).fetchone()
        total, current, v2, released, unreviewed, ocr = [x or 0 for x in privacy]
        return {
            'TRANSCRIPTION_ENABLED': os.environ.get('TRANSCRIPTION_ENABLED', 'false').strip().lower() == 'true',
            "lessons_total": q("SELECT COUNT(*) FROM lessons"),
            "lessons_present": q("SELECT COUNT(*) FROM lessons WHERE present=1"),
            "lessons_missing": q("SELECT COUNT(*) FROM lessons WHERE present=0"),
            "materials_total": q("SELECT COUNT(*) FROM materials"),
            "pdf_pages_total": q("SELECT COUNT(*) FROM pdf_pages"),
            "pdf_page_quality": quality,
            "pdf_privacy": {"policy_version": PRIVACY_POLICY_VERSION,
                            "current_policy_pages": current, "v2_pages": v2,
                            "released_pages": released, "blocked_pages": total - released,
                            "unreviewed_pages": unreviewed, "ocr_pending_pages": ocr},
            "transcripts_validated": q(f"SELECT COUNT(*) FROM transcripts t {self._CURRENT}"),
            "transcription_jobs": jobs,
            "transcription_states": states,
            "transcription_progress": progress,
            "last_sync": dict(last) if last else None,
        }
