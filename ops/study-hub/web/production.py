"""Read-only VPS dashboard and library; run under the dedicated Gunicorn unit.

No SSH, FO producers, credentials, review artifacts, media or producer commands.
"""
from __future__ import annotations

from contextlib import closing
from http import HTTPStatus
import json
import os
from pathlib import Path
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
from urllib.request import urlopen

import observer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pipeline_telemetry  # noqa: E402  (pure reader; no FO producer imports)
from storage_telemetry import storage_warning  # noqa: E402
import library  # noqa: E402  (after the FO discipline mapper sets the import path)

STATE = Path('/home/ubuntu/study-hub-state/federal-online')
MAX_INPUT = 1024 * 1024
MAX_PAYLOAD = 16384
COLLECTION_TIMEOUT = 12
OPTIONAL_TELEMETRY_TIMEOUT = 5


def read_database(path):
    deadline = time.monotonic() + 2
    with closing(sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True, timeout=.25)) as db:
        db.execute('PRAGMA query_only=ON')
        db.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
        db.execute('BEGIN')
        rows = db.execute('''SELECT CASE
            WHEN l.lesson_id IS NULL OR l.present != 1 OR j.version != l.version
                 OR j.state IN ('stale','superseded') THEN 'archived'
            WHEN j.state = 'ignored' THEN 'ignored' ELSE 'active' END AS scope,
            j.state, COUNT(*) FROM transcription_jobs j
            LEFT JOIN lessons l ON j.lesson_id=l.lesson_id GROUP BY scope,j.state''').fetchall()
        scopes = dict.fromkeys(('active', 'archived', 'ignored'), 0)
        jobs = dict.fromkeys(('done', 'queued', 'review', 'leased', 'failed'), 0)
        for scope, state, n in rows:
            scopes[scope] += n
            if scope == 'active' and state in jobs:
                jobs[state] += n
        active = [{'progress': row[0]} for row in db.execute('''SELECT j.progress
            FROM transcription_jobs j JOIN lessons l ON j.lesson_id=l.lesson_id
            WHERE l.present=1 AND j.version=l.version AND j.state='leased' LIMIT 2''')]
        sources = db.execute('''SELECT COUNT(*) FROM lesson_video_sources s
            JOIN lessons l ON s.lesson_id=l.lesson_id WHERE s.available=1 AND l.present=1''').fetchone()[0]
        last_validated_at = db.execute('''SELECT MAX(unixepoch(t.created_at)) FROM transcripts t
            JOIN lessons l USING (lesson_id, version)
            WHERE l.present=1 AND t.corpus='generated_v2'
              AND CASE WHEN json_valid(t.qa_json) THEN json_type(t.qa_json,'$.passed')='true' ELSE 0 END
              AND EXISTS (SELECT 1 FROM lesson_video_sources s WHERE s.lesson_id=l.lesson_id
                  AND s.available=1 AND s.revision=CAST(l.version AS TEXT) AND s.remote_path IS NOT NULL)''').fetchone()[0]
    return {'queue_scope': scopes, 'active': active, 'available_sources': sources,
            'current_jobs': jobs, 'last_validated_at': last_validated_at}


def materials_state(service, timer):
    active = observer.state(service.get('ActiveState'))
    result = service.get('Result')
    if active == 'failed' or (active == 'inactive' and result not in (None, '', 'success')):
        return 'failed'
    if active != 'inactive':
        return active
    if result != 'success' or not timer.get('ActiveState') or not timer.get('UnitFileState'):
        return 'unknown'
    if timer['ActiveState'] == 'failed':
        return 'failed'
    return 'scheduled' if timer['ActiveState'] == 'active' and timer['UnitFileState'] == 'enabled' else 'inactive'


def collect_local(state=STATE):
    # Adapted from fo_monitor.REMOTE_SCRIPT: fixed loopback API + read-only SQL.
    # The remote snippet itself selects titles; this collector deliberately does not.
    raw = {}
    with urlopen('http://127.0.0.1:8780/fo/sync-status', timeout=3) as response:
        body = response.read(MAX_INPUT + 1)
        if len(body) > MAX_INPUT:
            raise observer.Unavailable()
        raw['status'] = json.loads(body)
    raw.update(read_database(state / 'hub.sqlite3'))
    raw['status'] = {**observer.mapping(raw['status']), 'transcription_jobs': raw.pop('current_jobs')}
    units = ['study-hub-fo-' + name + ('.service' if name == 'transcription' else '.timer')
             for name in observer.SERVICES]
    materials_unit = 'study-hub-fo-materials.service'
    result = subprocess.run(['systemctl', 'show', '--property=Id,ActiveState,Result,UnitFileState',
                             *units, materials_unit],
                            capture_output=True, text=True, timeout=3, check=False)
    by_id = {}
    for block in result.stdout.split('\n\n'):
        fields = dict(line.split('=', 1) for line in block.splitlines() if '=' in line)
        if 'Id' in fields:
            by_id[fields['Id']] = fields
    raw['units'] = {name: by_id.get(unit, {}).get('ActiveState')
                    for name, unit in zip(observer.SERVICES, units)}
    raw['units']['materials'] = materials_state(by_id.get(materials_unit, {}),
                                               by_id.get('study-hub-fo-materials.timer', {}))
    for key, receipt in (('onedrive_receipt', state / 'onedrive-status.json'),
                         ('storage_receipt', state / 'telemetry/storage.json'),
                         ('health_receipt', state / 'telemetry/health.json')):
        try:
            with receipt.open('rb') as handle:
                body = handle.read(65537)
            if len(body) <= 65536:
                raw[key] = json.loads(body)
        except (OSError, ValueError):
            pass
    collect_pipeline(raw, state)
    usage = shutil.disk_usage(state)
    raw.update(disk_free=usage.free, disk_total=usage.total)
    receipt = observer.mapping(raw.get('storage_receipt'))
    reserve = observer.count(receipt.get('whisper_reserve_bytes'))
    if reserve is not None:
        receipt['warning'] = storage_warning(usage.free, reserve, observer.finite(receipt.get('growth_bytes_per_day')))
    return raw


def collect_pipeline(raw, state):
    # Only called in the single-threaded --collect child. Keep the essential
    # dashboard available if historical artifact decoding outgrows its budget.
    def deadline(_signum, _frame):
        raise RuntimeError('optional telemetry deadline')

    db = state / 'hub.sqlite3'
    handler = signal.signal(signal.SIGALRM, deadline)
    try:
        signal.setitimer(signal.ITIMER_REAL, OPTIONAL_TELEMETRY_TIMEOUT)
        raw['pipeline'] = pipeline_telemetry.build(state)
    except Exception:
        raw['pipeline'] = {}  # unknown stays null; never fabricated
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, handler)
    try:
        if raw['pipeline']:
            ignored = raw['pipeline']['transcription']['ignored_jobs']
        else:
            _, ignored, *_ = pipeline_telemetry._queue(db, None)
        scope = raw['queue_scope']
        # Ignored = queued/leased jobs of owner-excluded disciplines (preserved, not done).
        scope['active'], scope['ignored'] = scope['active'] - ignored, scope['ignored'] + ignored
        raw['status']['transcription_jobs']['queued'] -= ignored
    except Exception:
        # Without the exclusion count, don't label all queued jobs eligible.
        raw['queue_scope'].update(active=None, ignored=None)
        raw['status']['transcription_jobs']['queued'] = None


def fetch_local():
    # Dedicated child: hard wall-clock cutoff, no unbounded API/SQLite work in a
    # request worker, only already-projected scalar output crosses this boundary.
    result = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--collect'],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            timeout=COLLECTION_TIMEOUT, check=False)
    if result.returncode or len(result.stdout) > MAX_PAYLOAD:
        raise observer.Unavailable()
    return json.loads(result.stdout)


class ProjectedCache(observer.SnapshotCache):
    def __init__(self):
        # Child already projects. SnapshotCache still validates/projects a new
        # object via this explicit inverse scalar envelope, never passthrough.
        super().__init__(fetch=self._fetch)

    @staticmethod
    def _fetch():
        p = fetch_local()
        return {'status': {'transcription_jobs': {**p['transcription'], 'leased': p['transcription']['processing']},
                           'materials_total': p['pdf']['materials'], 'pdf_pages_total': p['pdf']['pages'],
                           'pdf_privacy': {'released_pages': p['pdf']['released'], 'blocked_pages': p['pdf']['blocked']},
                           'components': {'index': {'summary': {'source_videos': p['video']['indexed_objects']}}},
                           'sources': {'pending': p['video']['pending_sources']}},
                'active': [{'progress': p['transcription']['current_progress']}],
                'last_validated_at': p['transcription'].get('last_validated_at'),
                'queue_scope': p['queue_scope'], 'units': p['services'],
                'storage_receipt': {**p['storage'], 'observed_at': p['storage']['sample_observed_at']},
                'health_receipt': p['health'],
                'onedrive_receipt': p['onedrive'],
                'pipeline': {'transcription': p['pace'], 'videos': p['downloads'], 'reviews': p['reviews'],
                             'review_counts': p['review_counts'], 'reassessment': p['reassessment'],
                             'onedrive': {**p['onedrive'], 'updated_at': p['onedrive']['last_observed_at']}},
                'available_sources': p['video']['available_sources'],
                'disk_free': p['storage']['free_bytes'], 'disk_total': p['storage']['total_bytes']}


class DashboardApplication:
    def __init__(self, cache=None, *, state=STATE):
        self.cache = cache if cache is not None else ProjectedCache()
        self.state = state

    def __call__(self, environ, start_response):
        code, body = 200, b''
        limit = MAX_PAYLOAD
        path = environ.get('PATH_INFO', '')
        lesson_id = path.removeprefix('/api/lessons/') if path.startswith('/api/lessons/') else ''
        is_detail = bool(library.LESSON_ID.fullmatch(lesson_id))
        origin = environ.get('HTTP_ORIGIN')
        if (environ.get('HTTP_HOST') != 'localhost'
                or (origin is not None and origin != 'https://study.gatssby.com.br')
                or environ.get('HTTP_SEC_FETCH_SITE') == 'cross-site'):
            code = 403
        elif environ.get('REQUEST_METHOD') != 'GET':
            code = 405
        elif ((path not in ('/api/dashboard', '/api/library') and not is_detail)
              or environ.get('RAW_URI', path).split('?', 1)[0] != path):
            code = 404
        elif (environ.get('QUERY_STRING') or environ.get('CONTENT_LENGTH', '') not in ('', '0')
              or environ.get('HTTP_TRANSFER_ENCODING')):
            code = 400
        else:
            try:
                if path == '/api/dashboard':
                    payload = self.cache.get()
                else:
                    limit = 2 * library.MAX_TRANSCRIPT_BYTES if is_detail else library.MAX_CATALOG_BYTES
                    payload = library.read(self.state, lesson_id if is_detail else None)
                    if payload is None:
                        code = 404
                if payload is not None:
                    body = json.dumps(payload, allow_nan=False, ensure_ascii=False, separators=(',', ':')).encode()
                    if len(body) > limit:
                        code = 503
            except Exception:
                code = 503
        if code != 200:
            error = 'observation_unavailable' if code == 503 else HTTPStatus(code).phrase.lower().replace(' ', '_')
            body = json.dumps({'error': error}, separators=(',', ':')).encode()
        start_response(f'{code} {HTTPStatus(code).phrase}', [
            ('Content-Type', 'application/json; charset=utf-8'), ('Content-Length', str(len(body))),
            ('Cache-Control', 'private, no-store'), ('X-Content-Type-Options', 'nosniff')])
        return [body if environ.get('REQUEST_METHOD') != 'HEAD' else b'']


application = DashboardApplication()

if __name__ == '__main__':
    if sys.argv[1:] != ['--collect']:
        raise SystemExit(2)
    try:
        print(json.dumps(observer.project(collect_local()), allow_nan=False, separators=(',', ':')))
    except Exception:
        # No traceback, request targets, producer stderr, credentials or text.
        raise SystemExit(1) from None
