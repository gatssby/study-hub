"""Scalar pipeline telemetry from existing receipts/artifacts; never infers or writes.

Pace uses persisted ``elapsed_s`` (total job wall time) over ``duration_s``. Short
pilots (<5 min) and cache-assisted runs are excluded from comparable samples.
No transcript text, lesson IDs, paths, URLs or errors leave this module.
"""
from __future__ import annotations

import gzip
import json
import math
from pathlib import Path
import sqlite3
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'federal-online'))
from fo_hub.disciplines import discipline_for  # noqa: E402

MIN_SAMPLES = 5
MIN_DURATION_S = 300
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024
MAX_ARTIFACTS = 4000
SYNC_STATES = ('verified', 'failed', 'absent', 'not_generated')


def _number(value):
    return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def _artifacts(folder: Path):
    if not folder.is_dir():
        return
    for path in sorted(folder.glob('*/v*.json.gz'))[:MAX_ARTIFACTS]:
        if '.qa-v' in path.name or path.is_symlink() or path.stat().st_size > MAX_ARTIFACT_BYTES:
            continue
        try:
            body = json.loads(gzip.decompress(path.read_bytes()))
        except (OSError, EOFError, ValueError):
            continue
        if isinstance(body, dict):
            yield body


def _summary(body):
    chunks = body.get('chunks') if isinstance(body.get('chunks'), list) else []
    return {'lesson_id': body.get('lesson_id'), 'duration': _number(body.get('duration_s')),
            'elapsed': _number(body.get('elapsed_s')), 'created': _number(body.get('created_at')),
            'chunks': len(chunks), 'reused': sum(1 for c in chunks if isinstance(c, dict) and c.get('reused') is True),
            'blockers': (body.get('qa') or {}).get('blockers') if isinstance(body.get('qa'), dict) else None}


def _comparable(item):
    return (item['duration'] and item['elapsed'] and item['duration'] >= MIN_DURATION_S and item['reused'] == 0)


def _quantile(values, q):
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    low, high = math.floor(position), math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _queue(db: Path, excluded):
    deadline = time.monotonic() + 3
    connection = sqlite3.connect(f'file:{db}?mode=ro', uri=True, timeout=.5)
    try:
        connection.execute('PRAGMA query_only=ON')
        connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if excluded is None:
            excluded = frozenset(r[0] for r in connection.execute(
                'SELECT discipline FROM transcription_discipline_exclusions')) if 'transcription_discipline_exclusions' in tables else frozenset()
        rows = connection.execute('''SELECT j.state, l.subject, l.front, l.module, l.duration_s, l.lesson_id
            FROM transcription_jobs j JOIN lessons l ON l.lesson_id=j.lesson_id
            WHERE l.present=1 AND j.version=l.version''').fetchall()
    finally:
        connection.close()
    remaining = ignored = 0
    unknown_duration = 0
    disciplines, states = {}, {}
    for state, subject, front, module, duration, lesson in rows:
        name = discipline_for(subject, front, module)
        disciplines[lesson], states[lesson] = name, state
        if state not in ('queued', 'leased'):
            continue
        if name in excluded and state == 'queued':
            ignored += 1  # an already-leased lesson finishes and still counts as active work
        elif _number(duration):
            remaining += duration
        else:
            unknown_duration += 1
    return remaining, ignored, unknown_duration, disciplines, states, sorted(excluded)


def build(state: Path, *, now: float | None = None, excluded=None) -> dict:
    """``excluded=None`` reads the scheduler's persisted exclusion preference."""
    now = time.time() if now is None else now
    excluded = None if excluded is None else frozenset(excluded)
    remaining, ignored, unknown_duration, disciplines, states, excluded = _queue(state / 'hub.sqlite3', excluded)
    approved = [_summary(b) for b in _artifacts(state / 'transcripts/private')]
    reviewed = [_summary(b) for b in _artifacts(state / 'transcripts/review')]
    ratios = [i['elapsed'] / i['duration'] for i in approved + reviewed if _comparable(i)]
    recent = [i for i in approved if i['created'] and now - 86400 <= i['created'] <= now]
    median = eta = low = high = None
    if len(ratios) >= MIN_SAMPLES:
        median = round(statistics.median(ratios), 4)
        # Jobs without catalog duration are reported separately, not guessed.
        eta = round(remaining * median)
        low, high = round(remaining * _quantile(ratios, .25)), round(remaining * _quantile(ratios, .75))
    reviews = []
    for item in reviewed:
        if states.get(item['lesson_id']) != 'review':
            continue  # historical artifact superseded by publication/new version
        blockers = item['blockers'] if isinstance(item['blockers'], list) else None
        kinds, intervals = {}, []
        for flag in blockers or ():
            if isinstance(flag, dict) and isinstance(flag.get('kind'), str):
                kinds[flag['kind'][:40]] = kinds.get(flag['kind'][:40], 0) + 1
                start, end = _number(flag.get('start')), _number(flag.get('end'))
                if start is not None and end is not None and len(intervals) < 8:
                    intervals.append([round(start, 1), round(end, 1)])
        reviews.append({'discipline': disciplines.get(item['lesson_id'], 'Outros'),
                        'severity': 'grave' if kinds else ('desconhecida' if blockers is None else 'leve'),
                        'reasons': kinds, 'intervals': intervals, 'state': 'review'})
    videos = {'verified': 0, 'error': 0, 'unavailable': 0, 'other': 0, 'verified_bytes': 0}
    try:
        items = json.loads((state / 'videos.json').read_bytes()[:16 * 1024 * 1024]).get('items', {})
    except (OSError, ValueError, AttributeError):
        items = None
    if isinstance(items, dict):
        for entry in items.values():
            status = entry.get('status') if isinstance(entry, dict) else None
            key = 'verified' if status in ('verified', 'existing_remote_verified') else status if status in ('error', 'unavailable') else 'other'
            videos[key] += 1
            if key == 'verified' and type(entry.get('size')) is int:
                videos['verified_bytes'] += entry['size']
    else:
        videos = None
    try:
        receipt = json.loads((state / 'onedrive-status.json').read_bytes()[:65536])
    except (OSError, ValueError):
        receipt = {}
    receipt = receipt if isinstance(receipt, dict) else {}
    onedrive = {key: receipt.get(key) if receipt.get(key) in SYNC_STATES else 'unknown' for key in ('pdf_sync', 'transcript_sync')}
    onedrive.update({key: _number(receipt.get(key)) for key in ('updated_at', 'transcript_files', 'remote_videos', 'remote_video_bytes')})
    return {'observed_at': now,
            'transcription': {'comparable_samples': len(ratios), 'median_processing_per_audio': median,
                              'remaining_active_audio_s': round(remaining), 'unknown_duration_jobs': unknown_duration,
                              'ignored_jobs': ignored, 'excluded_disciplines': excluded, 'eta_seconds': eta, 'eta_low_seconds': low, 'eta_high_seconds': high,
                              'completed_24h': len(recent), 'audio_24h_s': round(sum(i['duration'] or 0 for i in recent))},
            'videos': videos, 'onedrive': onedrive, 'reviews': reviews[:20]}


if __name__ == '__main__':
    print(json.dumps(build(Path(sys.argv[1])), allow_nan=False))
