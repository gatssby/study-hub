"""Bounded operational health snapshot; read-only, sanitized, no cleanup.

Runs after the hourly storage sample under the same oneshot unit. Alerts are
state-based (the current condition), so repetition cannot spam: consumers show
the current alert set, never a notification stream. Unknown observations stay
null and never fabricate health. No lesson IDs, paths, URLs or errors escape.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time

from storage_telemetry import storage_warning

STALL_S = 2 * 3600          # a 10-min chunk decodes ~26 min; 2 h without progress is stalled
IDLE_S = 6 * 3600           # eligible work, no lease and no recent completion
ONEDRIVE_STALE_S = 3 * 3600  # hourly producer; one missed cycle plus margin
DEFERRAL_PERSIST_S = 7 * 86400
MATERIALS_FAIL_STREAK = 2
MAX_RECEIPT_BYTES = 65536


def assess(obs, *, previous=None):
    """Pure alert classification over already-observed scalars."""
    now = obs['now']
    alerts = []
    service, result = obs.get('transcription_service'), obs.get('transcription_result')
    if service == 'failed':
        alerts.append('transcription_failed')
    elif service == 'inactive' and result not in (None, '', 'success'):
        alerts.append('transcription_stopped')
    if obs.get('breaker_open') is True:
        alerts.append('breaker_open')
    if obs.get('leased') and obs.get('phase_age_s') is not None and obs['phase_age_s'] > STALL_S:
        alerts.append('transcription_stalled')
    if (not obs.get('leased') and (obs.get('eligible_queued') or 0) > 0 and service == 'active'
            and obs.get('last_finished_age_s') is not None and obs['last_finished_age_s'] > IDLE_S):
        alerts.append('transcription_not_progressing')
    materials_failed = obs.get('materials_active') == 'failed' or (
        obs.get('materials_active') == 'inactive' and obs.get('materials_result') not in (None, '', 'success'))
    streak = ((previous or {}).get('materials_fail_streak') or 0) + 1 if materials_failed else 0
    if streak >= MATERIALS_FAIL_STREAK:
        alerts.append('materials_failed')
    if obs.get('onedrive_age_s') is not None and obs['onedrive_age_s'] > ONEDRIVE_STALE_S:
        alerts.append('onedrive_stale')
    if 'failed' in (obs.get('pdf_sync'), obs.get('transcript_sync')):
        alerts.append('onedrive_sync_failed')
    free, reserve = obs.get('free_bytes'), obs.get('reserve_bytes')
    if free is not None and reserve is not None:
        warning = storage_warning(free, reserve, obs.get('growth_bytes_per_day'))
        if warning:
            alerts.append(warning)
    if (obs.get('persistent_deferrals') or 0) > 0:
        alerts.append('source_deferrals_persistent')
    snapshot = {k: obs.get(k) for k in (
        'transcription_service', 'transcription_result', 'breaker_open', 'leased', 'phase_age_s',
        'last_finished_age_s', 'eligible_queued', 'materials_active', 'materials_result',
        'onedrive_age_s', 'pdf_sync', 'transcript_sync', 'free_bytes', 'reserve_bytes',
        'growth_bytes_per_day', 'active_deferrals', 'persistent_deferrals')}
    snapshot.update(observed_at=now, alerts=sorted(set(alerts)), materials_fail_streak=streak)
    return snapshot


def _database(state, now):
    fields = {'breaker_open': None, 'leased': None, 'phase_age_s': None,
              'last_finished_age_s': None, 'eligible_queued': None,
              'active_deferrals': None, 'persistent_deferrals': None}
    try:
        connection = sqlite3.connect(f'file:{state}/hub.sqlite3?mode=ro', uri=True, timeout=1)
    except sqlite3.Error:
        return fields
    try:
        connection.execute('pragma query_only=on')
        deadline = time.monotonic() + 3
        connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'transcription_breaker' in tables:
            fields['breaker_open'] = bool(connection.execute(
                'SELECT EXISTS(SELECT 1 FROM transcription_breaker WHERE opened_at IS NOT NULL)').fetchone()[0])
        if 'transcription_jobs' in tables:
            fields['leased'] = connection.execute("SELECT COUNT(*) FROM transcription_jobs WHERE state='leased'").fetchone()[0]
            phase_at = None
            if 'transcription_job_phases' in tables:
                phase_at = connection.execute(
                    "SELECT MIN(p.updated_at) FROM transcription_job_phases p JOIN transcription_jobs j "
                    "ON j.lesson_id=p.lesson_id AND j.version=p.version AND j.state='leased'").fetchone()[0]
                finished = connection.execute(
                    "SELECT MAX(phase_started_at) FROM transcription_job_phases WHERE phase='finished'").fetchone()[0]
                if finished is not None:
                    fields['last_finished_age_s'] = max(0.0, now - finished)
            if phase_at is None and fields['leased']:
                phase_at = connection.execute(
                    "SELECT MIN(CAST(updated_at AS REAL)) FROM transcription_jobs WHERE state='leased'").fetchone()[0]
            if phase_at is not None:
                fields['phase_age_s'] = max(0.0, now - phase_at)
            if {'lessons', 'lesson_video_sources'} <= tables:
                retry = 'COALESCE(j.retry_at,0)' if 'retry_at' in {r[1] for r in connection.execute('PRAGMA table_info(transcription_jobs)')} else '0'
                fields['eligible_queued'] = connection.execute(
                    f"SELECT COUNT(*) FROM transcription_jobs j JOIN lessons l ON l.lesson_id=j.lesson_id AND l.version=j.version "
                    f"JOIN lesson_video_sources s ON s.lesson_id=j.lesson_id WHERE j.state='queued' AND {retry}<=? "
                    "AND j.attempts<j.max_attempts AND l.present=1 AND s.available=1 AND s.revision=CAST(j.version AS TEXT) "
                    "AND s.remote_path IS NOT NULL", (now,)).fetchone()[0]
        if 'transcription_source_deferrals' in tables:
            active, persistent = connection.execute(
                'SELECT COUNT(*), COALESCE(SUM(CASE WHEN observed_at<? THEN 1 ELSE 0 END),0) '
                'FROM transcription_source_deferrals WHERE retry_after>?',
                (now - DEFERRAL_PERSIST_S, now)).fetchone()
            fields['active_deferrals'], fields['persistent_deferrals'] = active, persistent
    except sqlite3.Error:
        return {k: None for k in fields}
    finally:
        connection.close()
    return fields


def _units(runner):
    fields = {'transcription_service': None, 'transcription_result': None,
              'materials_active': None, 'materials_result': None}
    try:
        result = runner(['systemctl', 'show', '--property=Id,ActiveState,Result',
                         'study-hub-fo-transcription.service', 'study-hub-fo-materials.service'],
                        capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.SubprocessError):
        return fields
    by_id = {}
    for block in (result.stdout or '').split('\n\n'):
        entry = dict(line.split('=', 1) for line in block.splitlines() if '=' in line)
        if 'Id' in entry:
            by_id[entry['Id']] = entry
    transcription = by_id.get('study-hub-fo-transcription.service', {})
    materials = by_id.get('study-hub-fo-materials.service', {})
    fields['transcription_service'] = transcription.get('ActiveState') or None
    fields['transcription_result'] = transcription.get('Result') or None
    fields['materials_active'] = materials.get('ActiveState') or None
    fields['materials_result'] = materials.get('Result') or None
    return fields


def _receipt(path):
    try:
        with path.open('rb') as handle:
            body = handle.read(MAX_RECEIPT_BYTES + 1)
        if len(body) > MAX_RECEIPT_BYTES:
            return {}
        data = json.loads(body)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def observe(state, *, now=None, runner=subprocess.run, available_bytes=None):
    state = Path(state)
    now = time.time() if now is None else now
    obs = {'now': now, **_database(state, now), **_units(runner)}
    onedrive = _receipt(state / 'onedrive-status.json')
    updated = onedrive.get('updated_at')
    obs['onedrive_age_s'] = max(0.0, now - updated) if type(updated) in (int, float) and updated >= 0 else None
    obs['pdf_sync'] = onedrive.get('pdf_sync') if onedrive.get('pdf_sync') in ('verified', 'failed', 'absent', 'not_generated') else None
    obs['transcript_sync'] = onedrive.get('transcript_sync') if onedrive.get('transcript_sync') in ('verified', 'failed', 'absent', 'not_generated') else None
    storage = _receipt(state / 'telemetry/storage.json')
    obs['free_bytes'] = shutil.disk_usage(state).free if available_bytes is None else available_bytes
    obs['reserve_bytes'] = storage.get('whisper_reserve_bytes') if type(storage.get('whisper_reserve_bytes')) is int else None
    growth = storage.get('growth_bytes_per_day')
    obs['growth_bytes_per_day'] = growth if type(growth) in (int, float) else None
    destination = state / 'telemetry'
    destination.mkdir(mode=0o700, exist_ok=True)
    with (destination / 'health.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        previous = _receipt(destination / 'health.json')
        snapshot = assess(obs, previous=previous)
        temporary = destination / 'health.json.tmp'
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(snapshot, stream, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination / 'health.json')
    return snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-root', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = observe(args.state_root)
    except Exception as exc:
        print(json.dumps({'error': type(exc).__name__}))
        raise SystemExit(1) from None
    print(json.dumps(result, allow_nan=False))


if __name__ == '__main__':
    main()