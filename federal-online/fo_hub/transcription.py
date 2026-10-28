"""FO transcription queue, fail-closed gate, blocked ASR adapter, and transcript QA.

SAFETY: No ASR inference is implemented here. ``BlockedASRAdapter`` always raises.
Even if every switch is on, ``check_gate`` reports "ASR adapter not implemented".
The worker CLI ``--check-only`` only reports gate/queue state; ``--run`` refuses
while the gate is closed (exit code 3) and never leases jobs.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from .store import FOStore
from .repetition import repetition_candidates

AUTH_PHRASE = "I AUTHORIZE FO TRANSCRIPTION ON VPS"
DEFAULT_AUTH_FILE = "/etc/study-hub/fo-transcription.authorized"
DEFAULT_PLATFORM_MARKER = "/etc/study-hub/fo-vps.marker"
ADAPTER_IMPLEMENTED = False


class TranscriptionBlocked(RuntimeError):
    pass


class LeaseLost(RuntimeError):
    pass


class BlockedASRAdapter:
    """Placeholder. Real inference is intentionally NOT implemented."""

    name = "blocked"

    def transcribe(self, media_path: Path) -> list[dict]:
        raise TranscriptionBlocked("ASR adapter not implemented; transcription is blocked")


def check_gate(env: Mapping[str, str] | None = None,
               platform_marker: str | os.PathLike | None = None,
               auth_file: str | os.PathLike | None = None,
               platform: str | None = None) -> dict:
    env = os.environ if env is None else env
    marker = Path(platform_marker or env.get("STUDY_HUB_FO_PLATFORM_MARKER",
                                              DEFAULT_PLATFORM_MARKER))
    auth = Path(auth_file or env.get("STUDY_HUB_FO_TRANSCRIPTION_AUTH", DEFAULT_AUTH_FILE))
    reasons = []
    if env.get("TRANSCRIPTION_ENABLED", "false").strip().lower() != "true":
        reasons.append("TRANSCRIPTION_ENABLED is not true")
    try:
        if auth.read_text().strip() != AUTH_PHRASE:
            reasons.append("authorization file content invalid")
    except OSError:
        reasons.append("authorization file missing")
    if not ((platform or sys.platform).startswith("linux") and marker.exists()):
        reasons.append("not running on VPS")
    if not ADAPTER_IMPLEMENTED:
        reasons.append("ASR adapter not implemented")
    return {"allowed": not reasons, "reasons": reasons, "state": "blocked" if reasons else "ready"}


class TranscriptionQueue:
    def __init__(self, store: FOStore, max_attempts: int = 3):
        self.c = store.conn
        self.max_attempts = max_attempts

    def enqueue(self, lesson_id: str, version: int) -> bool:
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self.c:
            cur = self.c.execute(
                "INSERT OR IGNORE INTO transcription_jobs(lesson_id,version,state,max_attempts,"
                "created_at,updated_at) VALUES(?,?,'queued',?,?,?)",
                (lesson_id, version, self.max_attempts, ts, ts))
        return cur.rowcount == 1

    def lease(self, owner: str, lease_s: float = 900, now: float | None = None) -> dict | None:
        now = time.time() if now is None else now
        with self.c:
            self.c.execute(  # recover expired leases
                "UPDATE transcription_jobs SET state=CASE WHEN attempts>=max_attempts "
                "THEN 'failed' ELSE 'queued' END, lease_owner=NULL, lease_until=NULL, "
                "last_error=COALESCE(last_error,'lease expired') "
                "WHERE state='leased' AND lease_until<?", (now,))
            row = self.c.execute(
                "SELECT lesson_id,version FROM transcription_jobs WHERE state='queued' "
                "ORDER BY created_at, lesson_id LIMIT 1").fetchone()
            if row is None:
                return None
            self.c.execute(
                "UPDATE transcription_jobs SET state='leased', lease_owner=?, lease_until=?, "
                "attempts=attempts+1 WHERE lesson_id=? AND version=?",
                (owner, now + lease_s, row[0], row[1]))
            r = self.c.execute("SELECT * FROM transcription_jobs WHERE lesson_id=? AND version=?",
                               tuple(row)).fetchone()
        return dict(r)

    def _owned(self, lesson_id: str, version: int, owner: str) -> None:
        r = self.c.execute("SELECT state,lease_owner FROM transcription_jobs WHERE lesson_id=? "
                           "AND version=?", (lesson_id, version)).fetchone()
        if r is None or r[0] != "leased" or r[1] != owner:
            raise LeaseLost(f"{owner} does not hold lease on {lesson_id}@{version}")

    def progress(self, lesson_id: str, version: int, owner: str, fraction: float) -> None:
        self._owned(lesson_id, version, owner)
        with self.c:
            self.c.execute("UPDATE transcription_jobs SET progress=? WHERE lesson_id=? AND "
                           "version=?", (max(0.0, min(1.0, fraction)), lesson_id, version))

    def fail(self, lesson_id: str, version: int, owner: str, error: str) -> None:
        self._owned(lesson_id, version, owner)
        with self.c:
            self.c.execute(
                "UPDATE transcription_jobs SET state=CASE WHEN attempts>=max_attempts "
                "THEN 'failed' ELSE 'queued' END, lease_owner=NULL, lease_until=NULL, "
                "last_error=? WHERE lesson_id=? AND version=?", (error, lesson_id, version))

    def complete(self, lesson_id: str, version: int, owner: str) -> None:
        self._owned(lesson_id, version, owner)
        with self.c:
            self.c.execute("UPDATE transcription_jobs SET state='done', progress=1, "
                           "lease_owner=NULL, lease_until=NULL WHERE lesson_id=? AND version=?",
                           (lesson_id, version))

    def counts(self) -> dict:
        return {r[0]: r[1] for r in self.c.execute(
            "SELECT state,COUNT(*) FROM transcription_jobs GROUP BY state")}


_WORD = re.compile(r"\w+", re.UNICODE)


def qa_segments(segments: Sequence[Mapping[str, Any]], duration_s: float | None = None,
                max_run: int = 4, silence_gap_s: float = 20.0) -> dict:
    """Flag, never remove, suspicious content; silence gaps are informational."""
    import math

    flags: list[dict] = []
    prev_end, prev_text, total_words = 0.0, None, 0
    for i, s in enumerate(segments):
        start, end, text = float(s["start"]), float(s["end"]), str(s.get("text", ""))
        finite = math.isfinite(start) and math.isfinite(end)
        if not finite or end < start or start < 0 or (duration_s is not None and end > duration_s + 1):
            flags.append({"idx": i, "kind": "bad_timestamp"})
        if i and start < prev_end - 0.05:
            flags.append({"idx": i, "kind": "non_monotonic"})
        if start - prev_end > silence_gap_s:
            flags.append({"idx": i, "kind": "silence_gap", "gap_s": round(start - prev_end, 2)})
        words = [w.lower() for w in _WORD.findall(text)]
        total_words += len(words)
        if prev_text is not None and text.strip() and text.strip().lower() == prev_text:
            flags.append({"idx": i, "kind": "duplicate_segment"})
        if finite and end >= start and start >= 0:
            prev_end = max(prev_end, end)
        prev_text = text.strip().lower()
    if duration_s and segments and duration_s - prev_end > silence_gap_s:
        flags.append({"idx": len(segments), "kind": "silence_gap",
                      "gap_s": round(duration_s - prev_end, 2)})
    repetition = repetition_candidates(segments,max_word_run=max_run,gap_s=silence_gap_s)
    flags.extend(repetition['flags'])
    metrics = {"segments": len(segments), "words": total_words,
               "repetition_ratio": repetition['metrics']['ratio'],
               "repetition": repetition['metrics'],
               "covered_until_s": prev_end, "flag_count": len(flags)}
    return {"passed": not any(f["kind"] != "silence_gap" for f in flags), "flags": flags, "metrics": metrics,
            "segments": [dict(s) for s in segments]}


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="fo-transcription-worker")
    p.add_argument("--db", default=None)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--check-only", action="store_true")
    g.add_argument("--run", action="store_true")
    a = p.parse_args(argv)
    store = FOStore(a.db) if a.db else FOStore.from_env()
    gate = check_gate()
    try:
        counts = TranscriptionQueue(store).counts()
    except sqlite3.Error as e:  # pragma: no cover
        counts = {"error": str(e)}
    print(json.dumps({"gate": gate, "queue": counts, "allowed": gate["allowed"]}))
    if a.check_only:
        return 0
    if not gate["allowed"]:
        print("refusing to run: gate closed", file=sys.stderr)
        return 3
    raise TranscriptionBlocked("ASR adapter not implemented")  # unreachable while blocked


if __name__ == "__main__":
    sys.exit(main())
