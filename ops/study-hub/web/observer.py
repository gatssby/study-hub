#!/usr/bin/env python3
"""Observador local: somente projeção escalar allowlisted, sem persistência."""
from __future__ import annotations

from datetime import datetime, timezone
import math
import json
import sys
import time
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def fetch_snapshot():
    # Reutiliza exclusivamente a coleta já existente; nunca imprime o bruto.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from fo_monitor import fetch
    return fetch('oracle-vps', timeout=25)


class Unavailable(Exception):
    pass


class SnapshotCache:
    def __init__(self, fetch=fetch_snapshot, clock=time.monotonic):
        self.fetch = fetch
        self.clock = clock
        self.next_poll = float('-inf')
        self.snapshot = None
        self.lock = threading.Lock()

    def get(self):
        with self.lock:
            if self.clock() >= self.next_poll:
                self.snapshot = None
                try:
                    raw = self.fetch()
                    if not isinstance(raw, dict) or not raw:
                        raise Unavailable()
                    self.snapshot = project(raw)
                except Exception:
                    # Não registra stderr, URLs, nomes ou exceções da coleta.
                    self.snapshot = None
                finally:
                    self.next_poll = self.clock() + 20
            if self.snapshot is None:
                raise Unavailable() from None
            return self.snapshot


HOSTS = frozenset(('127.0.0.1:3401', 'localhost:3401'))
ORIGINS = frozenset('http://' + host + ':' + str(port)
                    for host in ('127.0.0.1', 'localhost') for port in (3400, 3401))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def parse_request(self):
        valid = super().parse_request()
        if valid:
            # BaseHTTPRequestHandler normaliza //; preservar o alvo original.
            self.path = self.requestline.split()[1]
        return valid

    def respond(self, code, payload):
        body = json.dumps(payload, allow_nan=False, separators=(',', ':')).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def do_GET(self):
        hosts = self.headers.get_all('Host', [])
        origins = self.headers.get_all('Origin', [])
        if (len(hosts) != 1 or hosts[0] not in HOSTS or len(origins) > 1
                or (origins and origins[0] not in ORIGINS)
                or self.headers.get('Sec-Fetch-Site') == 'cross-site'):
            return self.respond(403, {'error': 'forbidden'})
        if self.path != '/api/dashboard':
            return self.respond(404, {'error': 'not_found'})
        if self.headers.get('Transfer-Encoding') or self.headers.get('Content-Length', '0') != '0':
            return self.respond(400, {'error': 'invalid_request'})
        try:
            payload = self.server.cache.get()
        except Unavailable:
            return self.respond(503, {'error': 'observation_unavailable'})
        self.respond(200, payload)

    def __getattr__(self, name):
        if name.startswith('do_'):
            return lambda: self.respond(405, {'error': 'method_not_allowed'})
        raise AttributeError(name)


def make_server(cache=None, port=3401):
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.cache = cache if cache is not None else SnapshotCache()
    return server


def main():
    server = make_server()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


SERVICES = ('transcription', 'catalog', 'materials', 'videos', 'index', 'onedrive', 'ocr')
STATES = frozenset(('active', 'inactive', 'failed', 'activating', 'deactivating', 'reloading', 'unknown'))


def mapping(value):
    return value if isinstance(value, dict) else {}


def count(value):
    if type(value) is int and value >= 0:
        return value
    if type(value) is float and math.isfinite(value) and value >= 0 and value.is_integer():
        return int(value)
    return None


def state(value):
    return value if isinstance(value, str) and value in STATES else 'unknown'


def project(raw):
    raw = mapping(raw)
    status = mapping(raw.get('status'))
    jobs = mapping(status.get('transcription_jobs'))
    pdf = mapping(status.get('pdf_privacy'))
    components = mapping(status.get('components'))
    index = mapping(mapping(components.get('index')).get('summary'))
    units = mapping(raw.get('units'))
    progress = None
    active = raw.get('active')
    if isinstance(active, list):
        for item in active:
            value = mapping(item).get('progress')
            if type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1:
                progress = value
                break
    return {
        'observed_at': datetime.now(timezone.utc).isoformat(),
        'transcription': {**{key: count(jobs.get(key)) for key in ('done', 'queued', 'review')},
                          'processing': count(jobs.get('leased', jobs.get('processing'))),
                          'current_progress': progress},
        'pdf': {'materials': count(status.get('materials_total')), 'pages': count(status.get('pdf_pages_total')),
                'released': count(pdf.get('released_pages')), 'blocked': count(pdf.get('blocked_pages'))},
        'video': {'available_sources': count(raw.get('available_sources')),
                  'indexed_objects': count(index.get('source_videos')),
                  'pending_sources': count(mapping(status.get('sources')).get('pending'))},
        'services': {name: state(units.get(name)) for name in SERVICES},
        'storage': {'free_bytes': count(raw.get('disk_free')), 'total_bytes': count(raw.get('disk_total'))},
        'onedrive': {'state': state(units.get('onedrive')), 'last_observed_at': None},
        'transfer': {'state': 'not_instrumented'},
    }


if __name__ == '__main__':
    main()
