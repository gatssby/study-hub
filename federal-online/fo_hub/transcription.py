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
            flags.append({"idx": i, "kind": "non_monotonic",
                          "overlap_s": round(prev_end - start, 6)})
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


QA_POLICY_VERSION = 4


def classify_qa(qa: dict, segments: Sequence[Mapping[str, Any]], duration_s: float) -> dict:
    """Assign risk without editing speech or timestamps; unknown checks block.

    Small boundary defects (<=2.5s each, <=1%/5s total) and at most three
    isolated short, nonoverlapping didactic repeats are MVP warnings. These
    are operational tolerances, not an acoustic accuracy measurement.
    Unexplained coverage gaps must first be reconciled with measured silence.
    """
    import math

    budget = max(5.0, duration_s * 0.01)
    previous_end = 0.0
    overlap_total = 0.0
    repeat_pairs = []
    for i, row in enumerate(segments):
        start, end = float(row['start']), float(row['end'])
        if math.isfinite(start) and math.isfinite(end) and end >= start >= 0:
            if i:
                overlap_total += max(0.0, previous_end - start)
            previous_end = max(previous_end, end)
        if i and str(row.get('text', '')).strip().casefold() == str(segments[i-1].get('text', '')).strip().casefold():
            repeat_pairs.append(i)
    isolated_repeats = bool(repeat_pairs) and len(repeat_pairs) <= 3
    for i in repeat_pairs:
        row, prev = segments[i], segments[i-1]
        isolated_repeats = isolated_repeats and (
            i-1 not in repeat_pairs and i+1 not in repeat_pairs
            and 0 <= float(row['start']) - float(prev['end']) <= 20
            and float(row['end']) - float(row['start']) <= 5
            and float(prev['end']) - float(prev['start']) <= 5
            and 0 < len(_WORD.findall(str(row.get('text', '')))) <= 12)
    boundary_intervals = sorted({(float(f['start']), float(f['end'])) for f in qa['flags']
                                if f['kind'] in {'ambiguous_overlap', 'boundary_timestamp_drift'}
                                and 'start' in f and 'end' in f})
    boundary_total = sum(max(0.0, end-start) for start, end in boundary_intervals)
    # A failed independent check of an entire phrase is stronger evidence than
    # a text-only repetition candidate; retain it for review. Single scientific
    # words cannot be reliably located by these short windows.
    for observation in qa.get('observations', []):
        if (observation.get('kind') == 'acoustic_repetition_check'
                and observation.get('confirmed') is False
                and len(_WORD.findall(str(observation.get('phrase', '')))) >= 3):
            flag = {'kind': 'acoustic_repetition_unconfirmed', 'idx': observation['idx']}
            if not any(f['kind'] == flag['kind'] and f.get('idx') == flag['idx'] for f in qa['flags']):
                qa['flags'].append(flag)
    warnings, blockers = [], []
    for flag in qa['flags']:
        kind = flag['kind']
        warning = False
        reason = 'substantial_or_unverified_defect'
        if kind == 'non_monotonic':
            overlap = flag.get('overlap_s')
            if overlap is None and flag.get('origin') != 'decoder':
                i = int(flag.get('idx', -1))
                if 0 < i < len(segments):
                    overlap = max(float(s['end']) for s in segments[:i]) - float(segments[i]['start'])
            warning = overlap is not None and 0 <= overlap <= 2.5 and overlap_total <= budget
            reason = 'bounded_timestamp_overlap' if warning else 'significant_timestamp_overlap'
        elif kind in {'ambiguous_overlap', 'boundary_timestamp_drift'}:
            span = float(flag.get('end', math.inf)) - float(flag.get('start', 0))
            warning = 0 <= span <= 2.5 and boundary_total <= budget and overlap_total <= budget
            reason = 'bounded_preserved_boundary' if warning else 'significant_boundary_uncertainty'
        elif kind == 'duplicate_segment':
            warning = isolated_repeats
            reason = 'isolated_didactic_repeat_candidate' if warning else 'systematic_or_long_repetition'
        flag.update(severity='warning' if warning else 'blocking', policy_reason=reason)
        (warnings if warning else blockers).append(dict(flag))
    qa.update(passed=not blockers, warnings=warnings, blockers=blockers,
              policy_version=QA_POLICY_VERSION)
    qa.setdefault('metrics', {}).update(flag_count=len(qa['flags']), warning_count=len(warnings),
                                       blocker_count=len(blockers), overlap_total_s=overlap_total,
                                       boundary_total_s=boundary_total, local_defect_budget_s=budget)
    return qa


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
