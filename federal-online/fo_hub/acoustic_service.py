"""One scheduled evidence-only review using the primary worker's decoder turn."""

import argparse
import ctypes
import fcntl
import json
import math
import os
import re
import shutil
import signal
import stat
import tempfile
import time
import zlib
from contextlib import closing
from pathlib import Path

from . import acoustic_review as ar
from .scheduler import EXCLUDABLE_DISCIPLINES, discipline
from .store import FOStore
from .worker import Config, file_sha256, gate

WORK_PREFIX = 'scheduled-work-'
RETRY_DELAY_S = 24 * 60 * 60
FOCAL_HEAD_START_S = 24 * 60 * 60
FINAL_REASONS = {'remote_source_bytes_changed', 'unverified_source_audio_timeline',
                 'invalid_parakeet_timestamps', 'audio_window_length_mismatch', 'audio_window_truncated'}
FOCAL_FLAGS = {'acoustic_repetition_unconfirmed', 'duplicate_segment', 'text_during_measured_silence'}


class AttemptBudget:
    """Two pre-inference reservations per fingerprint, even across a hard kill."""

    def __init__(self, root):
        self.root = root

    def path(self, key):
        if not re.fullmatch('[a-f0-9]{64}', key):
            raise ValueError('invalid evidence key')
        return self.root / (key + '.json')

    def read(self, key):
        path = self.path(key)
        try:
            info = path.lstat()
        except FileNotFoundError:
            return 0, 0
        if (not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600 or
                info.st_uid != os.getuid() or info.st_size > 512):
            raise ar.Blocked('untrusted_attempt_receipt')
        data = json.loads(path.read_text())
        if (type(data['attempts']) is not int or data['attempts'] not in (1, 2) or
                not math.isfinite(data['retry_at'])):
            raise ar.Blocked('untrusted_attempt_receipt')
        return data['attempts'], data['retry_at']

    def allows(self, key, *, now):
        attempts, after = self.read(key)
        return attempts < 2 and now >= after

    def reserve(self, key, *, now):
        attempts, after = self.read(key)
        if attempts >= 2 or now < after:
            raise ar.Blocked('review_attempt_budget')
        self.write(key, attempts + 1, now + RETRY_DELAY_S)

    def retire(self, key):
        self.write(key, 2, 0)

    def write(self, key, attempts, retry_at):
        path = self.path(key)
        with tempfile.NamedTemporaryFile(dir=self.root, prefix='.attempt-', delete=False) as stream:
            temp = Path(stream.name)
            try:
                stream.write(json.dumps({'attempts': attempts, 'retry_at': retry_at}).encode())
                stream.flush()
                os.fsync(stream.fileno())
                os.replace(temp, path)
                with ar.dir_fd(self.root) as fd:
                    os.fsync(fd)
            finally:
                temp.unlink(missing_ok=True)


def private_dir(path):
    path.mkdir(mode=0o700, exist_ok=True)
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or
            stat.S_IMODE(info.st_mode) != 0o700):
        raise ar.Blocked('private_review_directory_required')
    return path


def clean_work(root):
    """Only under the decoder lock, remove owned disposable scheduled scratch."""
    for folder in root.glob(WORK_PREFIX + '*'):
        info = folder.lstat()
        if (not re.fullmatch(WORK_PREFIX + '[a-z0-9_]{8}', folder.name) or
                not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or
                stat.S_IMODE(info.st_mode) != 0o700):
            raise ar.Blocked('untrusted_scheduled_work')
        for file in folder.iterdir():
            info = file.lstat()
            if (file.name not in {'source.mp4', 'window.wav'} or not stat.S_ISREG(info.st_mode) or
                    info.st_uid != os.getuid() or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) & 0o077):
                raise ar.Blocked('untrusted_scheduled_work')
        shutil.rmtree(folder)


def has_primary_leader(cfg):
    path = cfg.state / 'locks/transcription-worker.lock'
    try:
        with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return True
    except FileNotFoundError:
        pass
    return False


def select(cfg, root, budget, now):
    with closing(FOStore(cfg.db, readonly=True).conn) as db:
        db.execute('BEGIN')
        excluded = EXCLUDABLE_DISCIPLINES | {r[0] for r in db.execute(
            'SELECT discipline FROM transcription_discipline_exclusions')}
        largest = db.execute('SELECT COALESCE(MAX(size),0) FROM lesson_video_sources WHERE available=1').fetchone()[0]
        rows = db.execute('SELECT l.lesson_id,l.version,l.present,l.subject,l.front,l.module,'
                          'CAST(j.updated_at AS REAL) AS queued_at,'
                          's.revision,s.size,s.available,s.remote_path,j.state FROM lessons l '
                          'JOIN lesson_video_sources s USING(lesson_id) JOIN transcription_jobs j '
                          'ON j.lesson_id=l.lesson_id AND j.version=l.version '
                          "WHERE j.state='review' AND l.present=1 AND s.available=1 "
                          'AND s.revision=CAST(l.version AS TEXT) ORDER BY queued_at,l.lesson_id').fetchall()
    model_hash = file_sha256(ar.MODEL_MANIFEST)
    free = shutil.disk_usage(cfg.state).free
    best = None
    for row in rows:
        source = dict(row)
        lesson, version = row['lesson_id'], row['version']
        if not re.fullmatch(r'fo_[a-f0-9]{16}', lesson) or discipline(source) in excluded:
            continue
        try:
            ar.require_storage(free, largest, source['size'] + ar.WORK_BYTES)
            review, digest, duration, original_hash, qa_hash = ar.verified_input(cfg, lesson, version, source, excluded)
            key = ar.evidence_key(lesson, version, digest, original_hash, qa_hash, model_hash)
            receipt = root / f'{lesson}-v{version}-{key}.json.gz'
            if receipt.exists() or receipt.is_symlink() or not budget.allows(key, now=now):
                continue
            windows = ar.plan_windows(duration, review['qa']['blockers'], review['segments'])
        except (ar.Blocked, OSError, ValueError, TypeError, KeyError, EOFError, zlib.error):
            continue
        if windows:
            focal = all(w.kind in FOCAL_FLAGS for w in windows)
            score = (row['queued_at'] or 0) - (FOCAL_HEAD_START_S if focal else 0)
            contender = score, lesson, version, key
            if best is None or contender < best:
                best = contender
    return best[1:] if best is not None else None


class Readiness:
    """Separate a bounded wait for Whisper from the hard active runtime cap."""

    def __init__(self):
        if not os.environ.get('NOTIFY_SOCKET'):
            raise ar.Blocked('missing_systemd_notify_socket')
        self.lib = ctypes.CDLL('libsystemd.so.0')
        self.lib.sd_notify.argtypes = [ctypes.c_int, ctypes.c_char_p]
        self.lib.sd_notify_barrier.argtypes = [ctypes.c_int, ctypes.c_uint64]
        self.sent = False

    def __call__(self):
        if not self.sent:
            if self.lib.sd_notify(0, b'READY=1') <= 0 or self.lib.sd_notify_barrier(0, 3_000_000) < 0:
                raise ar.Blocked('systemd_ready_not_verified')
            self.sent = True


def scheduled_turn(cfg, runtime, ready):
    ar.require_limits()
    if not has_primary_leader(cfg):
        return {'state': 'not_admitted'}
    root = private_dir(cfg.state / 'transcripts/acoustic-review')
    budget = AttemptBudget(private_dir(root / 'scheduled-attempts'))
    admitted = gate(cfg)['allowed']
    candidate = select(cfg, root, budget, time.time()) if admitted else None

    def on_acquired():
        ready()
        clean_work(root)
        if not has_primary_leader(cfg):
            raise ar.Blocked('primary_leader_lost')

    if candidate is None:
        if next(root.glob(WORK_PREFIX + '*'), None) is not None:
            with ar.whisper_lock(cfg, wait=ar.MAX_SCHEDULED_WAIT_SECONDS):
                on_acquired()
        return {'state': 'no_eligible_evidence' if admitted else 'not_admitted'}
    lesson, version, key = candidate
    try:
        result = ar.review(cfg, runtime, lesson, version, wait=ar.MAX_SCHEDULED_WAIT_SECONDS,
                           ready=on_acquired, reserve=lambda k: budget.reserve(k, now=time.time()),
                           expected_key=key, work_prefix=WORK_PREFIX)
    except ar.Blocked as exc:
        if str(exc) in FINAL_REASONS:
            budget.retire(key)
        raise
    return {**result, 'lesson_id': lesson, 'version': version}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', required=True, type=Path)
    args = parser.parse_args(argv)
    os.umask(0o077)

    def interrupted(*_):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupted)
    try:
        ready = Readiness()
        try:
            result = scheduled_turn(Config.from_env(), args.runtime, ready)
        except ar.Blocked as exc:
            result = {'state': 'deferred', 'reason': str(exc)}
        ready()  # A clean skip is a successful service invocation, not a failed start.
        print(json.dumps(result), flush=True)
        return 0
    except KeyboardInterrupt:
        print('{"state":"interrupted"}', flush=True)
        return 130
    except Exception as exc:
        print(json.dumps({'state': 'failed', 'error_type': type(exc).__name__}), flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
