# Canonical FO transcription queue, guarded publication, and reset.
from __future__ import annotations

import argparse
from contextlib import closing, contextmanager
import fcntl
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import sys
import time
from typing import Sequence
import uuid

from .disciplines import discipline_for, pedagogical_key
from .onedrive import QUICKXOR_TYPE, normalize_quickxor, rclone_quickxor
from .store import (ACCEPTED_CORPUS, FOStore, TRANSCRIPT_MVP_SCHEMA, TranscriptRejected,
                    _now, mvp_reset_applied, table_names)

AUTH_PHRASE = 'I AUTHORIZE FO TRANSCRIPTION ON VPS'
DEFAULT_AUTH_FILE = '/etc/study-hub/fo-transcription.authorized'
DEFAULT_PLATFORM_MARKER = '/etc/study-hub/fo-vps.marker'
LEASE_SECONDS = 7 * 86400
SOURCE_BACKOFF_SECONDS = 6 * 3600
SOURCE_PREFIX = 'onedrive:Federal Online/'
SOURCE_FIELDS = ('revision', 'remote_path', 'size')
TRANSCRIPT_SOURCE_ERRORS = {'remote_object_not_found', 'source_duration_mismatch',
                            'source_download_size_mismatch'}
RESET_TABLES = ('transcript_segments', 'transcript_source_bindings', 'transcripts',
                'transcription_job_bindings', 'transcription_jobs', 'focused_reviews',
                'transcription_rr_cursor', 'transcription_breaker',
                'transcription_job_phases', 'transcription_review_log')
RESET_WRITE_TABLES = {*RESET_TABLES, 'transcription_mvp_reset'}


class LeaseLost(RuntimeError):
    pass


@contextmanager
def _write(conn):
    with conn:
        conn.execute('BEGIN IMMEDIATE')
        yield


@contextmanager
def db_worker_lock(db):
    database = db.resolve(strict=True)
    if database.stat().st_nlink != 1:
        raise ValueError('database has multiple hard links')
    fd = os.open(database.with_name(database.name + '.transcription.lock'),
                 os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield fd
    finally:
        os.close(fd)


def _install_queue_schema(conn):
    for statement in TRANSCRIPT_MVP_SCHEMA:
        conn.execute(statement)
    if 'retry_at' not in {r[1] for r in conn.execute('PRAGMA table_info(transcription_jobs)')}:
        conn.execute('ALTER TABLE transcription_jobs ADD COLUMN retry_at REAL')
    conn.execute('''CREATE TABLE IF NOT EXISTS transcription_job_bindings(
        lesson_id TEXT NOT NULL, version INTEGER NOT NULL, revision TEXT NOT NULL,
        remote_path TEXT NOT NULL, size INTEGER NOT NULL, lease_token TEXT,
        PRIMARY KEY(lesson_id,version))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS transcription_source_deferrals(
        lesson_id TEXT,version INTEGER,remote_path TEXT,size INTEGER,reason TEXT,
        retry_after REAL,observed_at REAL,PRIMARY KEY(lesson_id,version))''')


def valid_source(path, size):
    if not isinstance(path, str) or not path.startswith(SOURCE_PREFIX):
        return False
    relative = path[len(SOURCE_PREFIX):]
    return (type(size) is int and size > 0 and not re.search(r'[\\\x00-\x1f\x7f]', relative)
            and all(part not in ('', '.', '..') for part in relative.split('/')))


def _identity(row):
    return tuple(row[k] for k in SOURCE_FIELDS)


def _key(row):
    return row['lesson_id'], row['version']


def _eligible_sources(conn):
    '''Current verified, non-duplicate, non-excluded remote-backed lessons.'''
    tables = table_names(conn)
    columns = {r[1] for r in conn.execute('PRAGMA table_info(lesson_video_sources)')}
    if not {'lesson_id', 'available', *SOURCE_FIELDS} <= columns:
        return {}
    excluded = {r[0] for r in conn.execute('SELECT discipline FROM transcription_discipline_exclusions')} \
        if 'transcription_discipline_exclusions' in tables else set()
    rows = [dict(row) for row in conn.execute('''
        SELECT l.lesson_id,l.version,l.course_id,l.subject,l.front,l.module,l.title,l.item_id,
               l.duration_s,s.revision,s.remote_path,s.size
        FROM lessons l JOIN lesson_video_sources s USING(lesson_id)
        WHERE l.present=1 AND l.media_type='video' AND s.available=1
          AND s.revision=CAST(l.version AS TEXT) AND s.size>0
        ORDER BY l.first_seen,l.lesson_id''') if valid_source(row['remote_path'], row['size'])]
    # A verified portal identity owns its path even if its discipline is excluded.
    # Protected historical provisional aliases retain metadata, never a second job.
    claimed = {r['remote_path'] for r in rows if not r['course_id'].startswith('remote:')}
    eligible = {}
    for row in rows:
        row['discipline'] = discipline_for(row['subject'], row['front'], row['module'])
        if row['discipline'] in excluded:
            continue
        if row['course_id'].startswith('remote:'):
            if row['remote_path'] in claimed:
                continue
            claimed.add(row['remote_path'])
        eligible[_key(row)] = row
    return eligible


def _seed_job(conn, key, max_attempts):
    stamp = _now()
    return conn.execute('''INSERT OR IGNORE INTO transcription_jobs(lesson_id,version,state,
        max_attempts,created_at,updated_at) VALUES(?,?,'queued',?,?,?)''',
                        (*key, max_attempts, stamp, stamp)).rowcount


def _bind_job(conn, key, source, token=None):
    conn.execute('INSERT OR REPLACE INTO transcription_job_bindings VALUES(?,?,?,?,?,?)',
                 (*key, *_identity(source), token))


def _ready_job(conn, key):
    conn.execute('''UPDATE transcription_jobs SET state='queued',attempts=0,lease_owner=NULL,
        lease_until=NULL,progress=0,last_error=NULL,retry_at=NULL,updated_at=?
        WHERE lesson_id=? AND version=?''', (_now(), *key))


class TranscriptionQueue:
    def __init__(self, store: FOStore, max_attempts: int = 3):
        self.store = store
        self.c = store.conn
        self.max_attempts = max_attempts
        with _write(self.c):
            _install_queue_schema(self.c)

    def enqueue(self, lesson_id: str, version: int) -> bool:
        # Historical indexers can register pending jobs before reset.
        with _write(self.c):
            if mvp_reset_applied(self.c):
                key = lesson_id, version
                sources = _eligible_sources(self.c)
                return key in sources and bool(self._reconcile({key: sources[key]}, scoped=True))
            return bool(_seed_job(self.c, (lesson_id, version), self.max_attempts))

    def _reconcile(self, sources, *, scoped=False):
        mvp = mvp_reset_applied(self.c)
        jobs = {_key(row): row for row in self.c.execute('''
            SELECT j.lesson_id,j.version,j.state,b.remote_path,b.revision,b.size,
                   l.present,l.version AS current_version
            FROM transcription_jobs j LEFT JOIN lessons l USING(lesson_id)
            LEFT JOIN transcription_job_bindings b USING(lesson_id,version)''')}
        if not scoped:
            for key, job in jobs.items():
                if key in sources or job['state'] not in ('queued', 'leased'):
                    continue
                if mvp or not job['present'] or job['current_version'] != job['version']:
                    self.c.execute('''UPDATE transcription_jobs SET state='superseded',progress=0,
                        lease_owner=NULL,lease_until=NULL,retry_at=NULL,updated_at=?
                        WHERE lesson_id=? AND version=?''', (_now(), *key))
        seeded = 0
        for key, source in sources.items():
            job = jobs.get(key)
            if job is None:
                seeded += _seed_job(self.c, key, self.max_attempts)
                _bind_job(self.c, key, source)
                continue
            changed = job['revision'] is not None and _identity(job) != _identity(source)
            if changed or job['state'] == 'superseded':
                if changed:
                    # An observed remap permanently invalidates the old derivative.
                    self.c.execute('DELETE FROM transcript_source_bindings WHERE lesson_id=? AND version=?', key)
                _ready_job(self.c, key)
                _bind_job(self.c, key, source)
                seeded += 1
            elif job['revision'] is None and job['state'] != 'leased':
                _bind_job(self.c, key, source)
        return seeded

    def reconcile(self) -> int:
        with _write(self.c):
            return self._reconcile(_eligible_sources(self.c))

    def _recover(self, now=None):
        where = '' if now is None else ' AND (lease_until IS NULL OR lease_until<=?)'
        return self.c.execute('''UPDATE transcription_jobs SET state='queued',progress=0,
            lease_owner=NULL,lease_until=NULL,retry_at=NULL,updated_at=? WHERE state='leased' ''' + where,
                              (_now(),) if now is None else (_now(), now)).rowcount

    def recover(self) -> int:
        '''Return abandoned leases without consuming attempts. Caller holds worker lock.'''
        with _write(self.c):
            return self._recover()

    def lease(self, owner, *, lesson_id=None, max_source_bytes=None, now=None) -> dict | None:
        if not owner:
            raise ValueError('lease owner required')
        with _write(self.c):
            now = time.time() if now is None else now
            self._recover(now)
            sources = _eligible_sources(self.c)
            self._reconcile(sources)
            busy = {r[0] for r in self.c.execute('''SELECT b.remote_path FROM transcription_job_bindings b
                JOIN transcription_jobs j USING(lesson_id,version) WHERE j.state='leased' ''')}
            deferred = {tuple(r) for r in self.c.execute('''SELECT lesson_id,version,remote_path,size
                FROM transcription_source_deferrals WHERE retry_after>?''', (now,))}
            jobs = []
            for row in self.c.execute('''SELECT * FROM transcription_jobs WHERE state='queued'
                AND attempts<max_attempts AND COALESCE(retry_at,0)<=?''', (now,)):
                source = sources.get(_key(row))
                if (source is None or (lesson_id is not None and source['lesson_id'] != lesson_id)
                        or (max_source_bytes is not None and source['size'] > max_source_bytes)
                        or source['remote_path'] in busy
                        or (*_key(row), source['remote_path'], source['size']) in deferred):
                    continue
                jobs.append({**dict(row), **source})
            if not jobs:
                return None
            job = min(jobs, key=lambda r: (r['created_at'] or '', pedagogical_key(r)))
            token = uuid.uuid4().hex
            _bind_job(self.c, _key(job), job, token)
            self.c.execute('''UPDATE transcription_jobs SET state='leased',lease_owner=?,lease_until=?,
                progress=0,updated_at=? WHERE lesson_id=? AND version=?''',
                           (owner, now + LEASE_SECONDS, _now(), *_key(job)))
            return {**job, 'state': 'leased', 'lease_owner': owner, 'lease_token': token,
                    'lease_until': now + LEASE_SECONDS, 'progress': 0}

    def _owned(self, job, owner, now):
        row = self.c.execute('''SELECT j.*,b.lease_token,b.revision,b.remote_path,b.size
            FROM transcription_jobs j JOIN transcription_job_bindings b USING(lesson_id,version)
            WHERE j.lesson_id=? AND j.version=? AND j.state='leased' AND j.lease_owner=?
              AND b.lease_token=? AND j.lease_until>?''',
                             (*_key(job), owner, job.get('lease_token'), now)).fetchone()
        if row is None:
            raise LeaseLost(f'no current lease for {job["lesson_id"]}@{job["version"]}')
        return row

    def progress(self, job, owner, fraction) -> None:
        with _write(self.c):
            now = time.time()
            self._owned(job, owner, now)
            self.c.execute('''UPDATE transcription_jobs SET progress=MAX(progress,?),lease_until=?,updated_at=?
                WHERE lesson_id=? AND version=?''',
                           (max(0.0, min(1.0, fraction)), now + LEASE_SECONDS, _now(), *_key(job)))

    def check_source(self, job, owner) -> None:
        held = self._owned(job, owner, time.time())
        current = self.c.execute('''SELECT src.revision,src.remote_path,src.size
            FROM lessons l JOIN lesson_video_sources src USING(lesson_id)
            WHERE l.lesson_id=? AND l.version=? AND l.present=1 AND l.media_type='video'
              AND src.available=1''', _key(job)).fetchone()
        if current is None or _identity(current) != _identity(held) or _identity(job) != _identity(held):
            raise TranscriptRejected('source changed during transcription')

    def fail(self, job, owner, reason, *, defer=False, stale=False) -> str:
        with _write(self.c):
            now = time.time()
            held = self._owned(job, owner, now)
            current = _eligible_sources(self.c).get(_key(job))
            if stale or current is None or _identity(current) != _identity(held):
                state, attempts, retry_at = 'superseded', held['attempts'], None
            elif defer:
                state, attempts, retry_at = 'queued', held['attempts'], now + SOURCE_BACKOFF_SECONDS
                if reason in TRANSCRIPT_SOURCE_ERRORS:
                    # Never overwrite live, identity-matching source-ingest evidence.
                    self.c.execute('''INSERT INTO transcription_source_deferrals VALUES(?,?,?,?,?,?,?)
                        ON CONFLICT(lesson_id,version) DO UPDATE SET remote_path=excluded.remote_path,
                        size=excluded.size,reason=excluded.reason,retry_after=excluded.retry_after,
                        observed_at=excluded.observed_at
                        WHERE transcription_source_deferrals.retry_after<=excluded.observed_at
                           OR transcription_source_deferrals.remote_path IS NOT excluded.remote_path
                           OR transcription_source_deferrals.size IS NOT excluded.size''',
                                   (*_key(job), held['remote_path'], held['size'], reason, retry_at, now))
            else:
                attempts = held['attempts'] + 1
                state = 'failed' if attempts >= held['max_attempts'] else 'queued'
                retry_at = now + min(3600, 60 * (2 ** (attempts - 1))) if state == 'queued' else None
            self.c.execute('''UPDATE transcription_jobs SET state=?,attempts=?,lease_owner=NULL,lease_until=NULL,
                progress=0,last_error=?,retry_at=?,updated_at=? WHERE lesson_id=? AND version=?''',
                           (state, attempts, reason, retry_at, _now(), *_key(job)))
            return state

    def finish(self, job, owner, segments, qa, source) -> None:
        if qa.get('passed') is not True or qa.get('blockers') or not segments:
            raise TranscriptRejected('approved, non-empty transcript required')
        with _write(self.c):
            held = self._owned(job, owner, time.time())
            current = _eligible_sources(self.c).get(_key(job))
            if (current is None or _identity(current) != _identity(held)
                    or tuple(source.get(k) for k in SOURCE_FIELDS) != _identity(held)):
                raise TranscriptRejected('source changed before publication')
            last_start = 0
            for row in segments:
                start, end, text = (row.get('start'), row.get('end'), row.get('text'))
                if (type(start) not in (int, float) or type(end) not in (int, float)
                        or not math.isfinite(start) or not math.isfinite(end)
                        or not last_start <= start < end
                        or ('duration_s' in qa and end > qa['duration_s'] + 1e-9)
                        or not isinstance(text, str) or not any(char.isalnum() for char in text)):
                    raise TranscriptRejected('invalid transcript segment')
                last_start = start
            self.store._write_transcript(*_key(job), segments, 'whisper-large-v3', ACCEPTED_CORPUS, qa)
            self.c.execute('INSERT OR REPLACE INTO transcript_source_bindings VALUES(?,?,?,?,?)',
                           (*_key(job), *_identity(held)))
            self.c.execute('''UPDATE transcription_jobs SET state='done',progress=1,lease_owner=NULL,
                lease_until=NULL,last_error=NULL,retry_at=NULL,updated_at=? WHERE lesson_id=? AND version=?''',
                           (_now(), *_key(job)))

    def review(self, job, owner, qa) -> str:
        reasons = sorted({row['kind'] for row in qa['blockers']})
        if qa.get('passed') is not False or not reasons:
            raise ValueError('review requires a material blocker')
        with _write(self.c):
            held = self._owned(job, owner, time.time())
            key = _key(job)
            current = _eligible_sources(self.c).get(key)
            state = 'review' if current is not None and _identity(current) == _identity(held) else 'superseded'
            for table in ('transcript_segments', 'transcripts', 'transcript_source_bindings'):
                self.c.execute(f'DELETE FROM {table} WHERE lesson_id=? AND version=?', key)
            self.c.execute('''UPDATE transcription_jobs SET state=?,progress=0,lease_owner=NULL,
                lease_until=NULL,retry_at=NULL,last_error=?,updated_at=? WHERE lesson_id=? AND version=?''',
                           (state, ','.join(reasons) if state == 'review' else 'source_changed', _now(), *key))
        return state

    def retry(self, lesson_id) -> bool:
        with _write(self.c):
            sources = {key: row for key, row in _eligible_sources(self.c).items() if key[0] == lesson_id}
            if not sources:
                return False
            self._reconcile(sources, scoped=True)
            key, source = next(iter(sources.items()))
            state = self.c.execute('SELECT state FROM transcription_jobs WHERE lesson_id=? AND version=?', key).fetchone()[0]
            if state not in ('failed', 'queued', 'review'):
                return False
            _ready_job(self.c, key)
            _bind_job(self.c, key, source)
            return True

    def counts(self) -> dict:
        return {r[0]: r[1] for r in self.c.execute('SELECT state,COUNT(*) FROM transcription_jobs GROUP BY state')}


def _reset_plan(conn):
    tables = table_names(conn)
    required = {'lessons', 'lesson_video_sources', 'transcripts', 'transcript_segments',
                'transcription_jobs'}
    if not required <= tables:
        raise ValueError('expected an existing FO DB with a video source registry')
    if not {'lesson_id', 'available', *SOURCE_FIELDS} <= {
            r[1] for r in conn.execute('PRAGMA table_info(lesson_video_sources)')}:
        raise ValueError('incomplete video source registry')
    if any(r[0] in RESET_WRITE_TABLES for r in conn.execute(
            "SELECT tbl_name FROM sqlite_master WHERE type='trigger'")):
        raise ValueError('reset tables have unexpected triggers')
    sources = _eligible_sources(conn)
    counts = {table: conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
              for table in RESET_TABLES if table in tables}
    return sources, counts


def _inventory_bindings(conn, sources, inventory):
    """Prepare exact current observations; never infer a path or remap a lesson."""
    started, finished = inventory['started_at'], inventory['finished_at']
    now = time.time()
    if not (now - 3600 <= started <= finished <= now + 5):
        raise ValueError('invalid or expired inventory window')
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type='trigger' "
                    "AND tbl_name='lesson_source_observations'").fetchone():
        raise ValueError('unexpected source observation trigger')
    by_path = {}
    for item in inventory['rows']:
        path = SOURCE_PREFIX + item['Path']
        if path in by_path or not valid_source(path, item['Size']):
            raise ValueError('invalid or duplicate inventory path')
        by_path[path] = item
    updates, unverified = [], 0
    for (lid, version), source in sources.items():
        path = source['remote_path']
        listed = by_path.get(path, {})
        proof = rclone_quickxor(listed.get('Hashes'))
        row = conn.execute('''SELECT metadata FROM lesson_source_observations
            WHERE lesson_id=? AND remote_path=? AND version=?''', (lid, path, version)).fetchone()
        old = json.loads(row[0]) if row else {}
        if (proof is None or not isinstance(old, dict) or type(old.get('Size')) is not int
                or old['Size'] != source['size'] or listed['Size'] != source['size']
                or not all(isinstance(old.get(k), str) and old[k] and old[k] == listed.get(k)
                           for k in ('ID', 'ModTime'))
                or (QUICKXOR_TYPE in old and normalize_quickxor(old[QUICKXOR_TYPE]) != proof)):
            unverified += 1
            continue
        if QUICKXOR_TYPE not in old:
            old[QUICKXOR_TYPE] = proof
            updates.append((json.dumps(old, sort_keys=True), str(finished), lid, path, version))
    return updates, unverified


def _reset_db(db: Path, state: Path, apply: bool, inventory=None) -> dict:
    uri = db.resolve(strict=True).as_uri() + ('?mode=rw' if apply else '?mode=ro')
    with closing(sqlite3.connect(uri, uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        if not apply:
            with conn:
                conn.execute('BEGIN')
                sources, counts = _reset_plan(conn)
                report = {'applied': False, 'already_reset': mvp_reset_applied(conn),
                          'delete_rows': counts, 'queue_seed': len(sources), 'corpus': ACCEPTED_CORPUS}
                if inventory is not None:
                    updates, unverified = _inventory_bindings(conn, sources, inventory)
                    report.update(hash_bindings=len(updates), unverified_sources=unverified)
                return report
        locks = state / 'locks'
        locks.mkdir(mode=0o700, exist_ok=True)
        with os.fdopen(os.open(locks / 'transcription-worker.lock',
                               os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600), 'rb+') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ValueError('transcription worker lock held; stop transcription units first') from exc
            with db_worker_lock(db), _write(conn):
                if mvp_reset_applied(conn):
                    raise ValueError('MVP reset was already applied')
                sources, counts = _reset_plan(conn)
                updates = []
                if inventory is not None:
                    updates, unverified = _inventory_bindings(conn, sources, inventory)
                    if unverified:
                        raise ValueError(f'{unverified} eligible sources lack matching fresh inventory proof')
                _install_queue_schema(conn)
                for table in counts:
                    conn.execute(f'DELETE FROM {table}')
                if inventory is not None:
                    changed = conn.executemany('''UPDATE lesson_source_observations SET metadata=?,checked_at=?
                        WHERE lesson_id=? AND remote_path=? AND version=?''', updates)
                    if changed.rowcount != len(updates):
                        raise ValueError('exact source observation update failed')
                for key, source in sources.items():
                    _seed_job(conn, key, 3)
                    _bind_job(conn, key, source)
                conn.execute('INSERT INTO transcription_mvp_reset VALUES(1,?)', (_now(),))
                report = {'applied': True, 'delete_rows': counts,
                          'queue_seed': len(sources), 'corpus': ACCEPTED_CORPUS}
                if inventory is not None:
                    report.update(hash_bindings=len(updates), unverified_sources=0)
                return report


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog='fo-transcription-reset',
                                description='Preview or apply the one-time FO SQLite transcript reset.')
    p.add_argument('--reset', action='store_true', required=True)
    p.add_argument('--db', type=Path, required=True, help='Existing FO SQLite database.')
    p.add_argument('--inventory', type=Path, help='Fresh read-only OneDrive QuickXor inventory for the reset.')
    p.add_argument('--state-root', type=Path,
                   help='Worker state root for the shared lock (defaults to FO_STATE_ROOT or DB directory).')
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true', help='Preview only (default).')
    mode.add_argument('--confirm-reset', action='store_true',
                      help='Authorize destructive reset; stop transcription units before using this flag.')
    a = p.parse_args(argv)
    try:
        state = a.state_root or Path(os.environ.get('FO_STATE_ROOT') or a.db.resolve().parent)
        inventory = json.loads(a.inventory.read_bytes()) if a.inventory else None
        if a.confirm_reset and inventory is None:
            raise ValueError('--confirm-reset requires --inventory')
        print(json.dumps(_reset_db(a.db, state, a.confirm_reset, inventory)))
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError) as exc:
        print(f'reset refused: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
