"""Read-only VPS WSGI dashboard; run under the dedicated Gunicorn unit.

No SSH, FO producer imports (only the pure discipline mapper), credentials, review artifacts, media or producer commands.
"""
from __future__ import annotations

from contextlib import closing
from http import HTTPStatus
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
from urllib.request import urlopen

import observer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pipeline_telemetry  # noqa: E402  (pure reader; no FO producer imports)

STATE = Path('/home/ubuntu/study-hub-state/federal-online')
MAX_INPUT = 1024 * 1024
MAX_PAYLOAD = 16384
COLLECTION_TIMEOUT = 12


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
    return {'queue_scope': scopes, 'active': active, 'available_sources': sources,
            'current_jobs': jobs}


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
    result = subprocess.run(['systemctl', 'show', '--property=Id,ActiveState', *units],
                            capture_output=True, text=True, timeout=3, check=False)
    raw['units'] = {}
    for block in result.stdout.split('\n\n'):
        fields = dict(line.split('=', 1) for line in block.splitlines() if '=' in line)
        for name, unit in zip(observer.SERVICES, units):
            if fields.get('Id') == unit:
                raw['units'][name] = fields.get('ActiveState')
    for key, receipt in (('onedrive_receipt', state / 'onedrive-status.json'),
                         ('storage_receipt', state / 'telemetry/storage.json')):
        try:
            with receipt.open('rb') as handle:
                body = handle.read(65537)
            if len(body) <= 65536:
                raw[key] = json.loads(body)
        except (OSError, ValueError):
            pass
    try:
        raw['pipeline'] = pipeline_telemetry.build(state)
        ignored = raw['pipeline']['transcription']['ignored_jobs']
        scope = raw['queue_scope']
        # Ignored = queued/leased jobs of owner-excluded disciplines (preserved, not done).
        scope['active'], scope['ignored'] = scope['active'] - ignored, scope['ignored'] + ignored
        raw['status']['transcription_jobs']['queued'] -= ignored
    except Exception:
        raw['pipeline'] = {}  # unknown stays null; never fabricated
    usage = shutil.disk_usage(state)
    raw.update(disk_free=usage.free, disk_total=usage.total)
    return raw


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
                'queue_scope': p['queue_scope'], 'units': p['services'],
                'storage_receipt': {**p['storage'], 'observed_at': p['storage']['sample_observed_at']},
                'onedrive_receipt': p['onedrive'],
                'pipeline': {'transcription': p['pace'], 'videos': p['downloads'], 'reviews': p['reviews'],
                             'onedrive': {**p['onedrive'], 'updated_at': p['onedrive']['last_observed_at']}},
                'available_sources': p['video']['available_sources'],
                'disk_free': p['storage']['free_bytes'], 'disk_total': p['storage']['total_bytes']}


class DashboardApplication:
    def __init__(self, cache=None):
        self.cache = cache if cache is not None else ProjectedCache()

    def __call__(self, environ, start_response):
        code, payload = 200, None
        origin = environ.get('HTTP_ORIGIN')
        if (environ.get('HTTP_HOST') != 'localhost'
                or (origin is not None and origin != 'https://study.gatssby.com.br')
                or environ.get('HTTP_SEC_FETCH_SITE') == 'cross-site'):
            code = 403
        elif environ.get('REQUEST_METHOD') != 'GET':
            code = 405
        elif (environ.get('PATH_INFO') != '/api/dashboard'
              or environ.get('RAW_URI', '/api/dashboard').split('?', 1)[0] != '/api/dashboard'):
            code = 404
        elif (environ.get('QUERY_STRING') or environ.get('CONTENT_LENGTH', '') not in ('', '0')
              or environ.get('HTTP_TRANSFER_ENCODING')):
            code = 400
        else:
            try:
                payload = self.cache.get()
            except Exception:
                code = 503
        if payload is None:
            payload = {'error': 'observation_unavailable' if code == 503 else HTTPStatus(code).phrase.lower().replace(' ', '_')}
        body = json.dumps(payload, allow_nan=False, separators=(',', ':')).encode()
        if len(body) > MAX_PAYLOAD:
            code, body = 503, b'{"error":"observation_unavailable"}'
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
