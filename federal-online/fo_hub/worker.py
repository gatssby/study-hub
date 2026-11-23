"""Single VPS worker for revision-bound Whisper large-v3 transcription."""
from __future__ import annotations

import argparse
from contextlib import closing, contextmanager
from dataclasses import dataclass
import fcntl
from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid
import wave

from .store import FOStore, TranscriptRejected, mvp_reset_applied
from .onedrive import QUICKXOR_TYPE, normalize_quickxor, rclone_quickxor
from .transcript_qa import assess
from .transcription import (AUTH_PHRASE, DEFAULT_AUTH_FILE, DEFAULT_PLATFORM_MARKER,
                            LeaseLost, SOURCE_FIELDS, TranscriptionQueue, db_worker_lock)

CHUNK_SECONDS = 600
OVERLAP_SECONDS = 2
CHUNK_TIMEOUT = 45 * 60
RESERVE = 4 * 1024**3
WORK_BYTES = 100 * 1024**2
MODEL_SHA256 = '64d182b440b98d5203c4f9bd541544d84c605196c4f7b845dfa11fb23594d1e2'
WHISPER_FLAGS = ('-l', 'pt', '-t', '3', '-bs', '5', '-bo', '5', '-mc', '0', '-tp', '0',
                 '-tpi', '0', '-nth', '0.6', '-et', '2.4', '-lpt', '-1', '-ng', '-ojf', '-nf')


@dataclass(frozen=True)
class Config:
    state: Path
    db: Path
    binary: Path
    model: Path
    auth: Path = Path(DEFAULT_AUTH_FILE)
    marker: Path = Path(DEFAULT_PLATFORM_MARKER)

    @classmethod
    def from_env(cls):
        state = Path(os.environ.get('FO_STATE_ROOT', '/home/ubuntu/study-hub-state/federal-online'))
        model_dir = Path('/home/ubuntu/study-hub-models')
        return cls(state, Path(os.environ.get('STUDY_HUB_FO_DB', str(state / 'hub.sqlite3'))),
                   Path(os.environ.get('WHISPER_CPP_BIN', str(model_dir / 'whisper.cpp/build/bin/whisper-cli'))),
                   Path(os.environ.get('WHISPER_MODEL', str(model_dir / 'ggml-large-v3.bin'))),
                   Path(os.environ.get('STUDY_HUB_FO_TRANSCRIPTION_AUTH', DEFAULT_AUTH_FILE)),
                   Path(os.environ.get('STUDY_HUB_FO_PLATFORM_MARKER', DEFAULT_PLATFORM_MARKER)))


def file_sha256(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


@lru_cache(maxsize=16)
def _digest(path, stat_key):
    return file_sha256(path)


def file_identity(path):
    s = path.stat()
    return _digest(path.resolve(), (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns))


def authorized(cfg):
    try:
        return (os.environ.get('TRANSCRIPTION_ENABLED', '').strip().lower() == 'true'
                and sys.platform.startswith('linux') and cfg.marker.is_file()
                and cfg.auth.read_text().strip() == AUTH_PHRASE)
    except OSError:
        return False


def encode(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode()


def digest(data):
    return hashlib.sha256(encode(data)).hexdigest()


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def private_dir(path):
    path.mkdir(mode=0o700, exist_ok=True)
    if path.is_symlink() or not path.is_dir() or path.stat().st_uid != os.geteuid():
        raise OSError('unsafe_worker_directory')
    return path


def atomic_json(path, identity, data):
    record = {'identity': identity, 'data': data}
    payload = encode({**record, 'sha256': digest(record)})
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.writing-')
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
        sync_dir(path.parent)
    finally:
        Path(name).unlink(missing_ok=True)


def load_checkpoint(path, identity):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as handle:
            record = json.loads(handle.read(8 * 1024**2))
        if (record.pop('sha256') == digest(record) and record['identity'] == identity
                and isinstance(record['data'], dict)):
            return record['data']
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        pass
    return None


@contextmanager
def leader_lock(state):
    path = private_dir(state / 'locks') / 'transcription-worker.lock'
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield fd
    finally:
        # Close, don't unlock: a surviving child still owns this file description.
        os.close(fd)


def parse_whisper(raw, offset):
    rows = raw['transcription']
    if not isinstance(rows, list):
        raise ValueError('invalid_decoder_output')
    segments = []
    for row in rows:
        start, end = (row['offsets'][k] for k in ('from', 'to'))
        if (not all(type(x) in (int, float) and math.isfinite(x) for x in (start, end))
                or not isinstance(row['text'], str)):
            raise ValueError('invalid_decoder_output')
        segments.append({'start': offset + start / 1000, 'end': offset + end / 1000,
                         'text': row['text'].strip()})
    return segments


def silence_intervals(log, duration):
    intervals, start = [], None
    for match in re.finditer(r'silence_(start|end):\s*([-+0-9.eE]+)', log):
        value = min(duration, max(0, float(match[2])))
        if match[1] == 'start':
            start = value
        elif start is not None:
            if value > start:
                intervals.append([start, value])
            start = None
    if start is not None and duration > start:
        intervals.append([start, duration])
    return intervals


def decoder_command(cfg, audio, prefix):
    return [cfg.binary, '-m', cfg.model, '-f', audio, *WHISPER_FLAGS, '-of', prefix]


class JobProblem(Exception):
    def __init__(self, reason, *, defer=False, review=False):
        super().__init__(reason)
        self.defer, self.review = defer, review


class Worker:
    def __init__(self, cfg, queue, lock_fd, *, runner=subprocess.run, check_auth=authorized):
        self.cfg, self.queue, self.lock_fd = cfg, queue, lock_fd
        self.runner, self.check_auth = runner, check_auth
        self.owner = f'fo-worker:{os.getpid()}:{uuid.uuid4().hex}'

    def command(self, args, timeout):
        return self.runner([str(a) for a in args], capture_output=True, check=True, text=True,
                           timeout=timeout, pass_fds=(self.lock_fd,))

    def require_auth(self):
        if not self.check_auth(self.cfg):
            raise PermissionError('transcription authorization revoked')

    def roots(self):
        state = private_dir(self.cfg.state / 'transcription-mvp')
        return private_dir(state / 'scratch'), private_dir(state / 'checkpoints')

    def recover(self):
        scratch, _ = self.roots()
        for path in scratch.iterdir():
            if (re.fullmatch(r'job-[a-z0-9_]{8}', path.name) and not path.is_symlink()
                    and path.is_dir() and path.stat().st_uid == os.geteuid()):
                shutil.rmtree(path)
        self.queue.recover()

    def extract(self, video, wav, offset, length):
        rate = 16000
        # Keep source PTS relative to the media origin across seeks (-copyts also
        # disables FFmpeg's gap repair). Check the exact trimmed samples before
        # rewriting timestamps for the WAV and relative silence measurements.
        max_samples = round(length * rate)
        result = self.command(['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'info', '-xerror',
                               '-nostats', '-threads', '1', '-filter_threads', '1', '-copyts', '-start_at_zero',
                               '-ss', f'{offset:.6f}', '-i', video, '-map', '0:a:0', '-vn', '-af',
                               f'aresample={rate}:ochl=mono:async=0,asettb=1/{rate},atrim=end_sample={max_samples},'
                               'ashowinfo,asetpts=N/SR/TB,silencedetect=n=-50dB:d=1', '-c:a', 'pcm_s16le', wav], 120)
        with wave.open(str(wav), 'rb') as handle:
            n = handle.getnframes()
            if (handle.getnchannels(), handle.getsampwidth(), handle.getframerate()) != (1, 2, rate):
                raise JobProblem('invalid_pcm_format', review=True)
            if n:
                handle.setpos(n - 1)
                if len(handle.readframes(1)) != 2:
                    raise JobProblem('truncated_pcm_file', review=True)

        # Integer PTS are in 1/16000 s ticks; printed pts_time loses precision.
        # Bound both local jumps and accumulated drift from the requested seek.
        first_tick = previous_end = round(offset * rate)
        tolerance = round(0.05 * rate)  # codec-frame seek rounding and resampling
        sample_count = 0
        for index, line in enumerate(re.finditer(r'(?m)^\[Parsed_ashowinfo_\d+ @ [^\]\r\n]+\] ([^\r\n]*)',
                                                 result.stderr)):
            frame = re.match(r'n:\s*(\d+)\s+pts:\s*(-?\d+)\s+.*\brate:\s*(\d+)\s+nb_samples:\s*(\d+)\b',
                             line[1])
            if frame is None:
                raise JobProblem('invalid_audio_pts_evidence', review=True)
            frame_index, pts, frame_rate, samples = map(int, frame.groups())
            if frame_index != index or frame_rate != rate or not 0 < samples <= max_samples - sample_count:
                raise JobProblem('invalid_audio_pts_evidence', review=True)
            if abs(pts - previous_end) > tolerance or abs(pts - first_tick - sample_count) > tolerance:
                raise JobProblem('audio_pts_discontinuity', review=True)
            sample_count += samples
            previous_end = pts + samples
        if not sample_count or sample_count != n:
            raise JobProblem('invalid_audio_pts_evidence', review=True)
        duration = n / rate
        return duration, silence_intervals(result.stderr, duration)

    def download(self, job, video):
        size = job['size']
        expected = None
        try:
            observation = self.queue.c.execute('''SELECT metadata FROM lesson_source_observations
                WHERE lesson_id=? AND remote_path=? AND version=?''',
                (job['lesson_id'], job['remote_path'], job['version'])).fetchone()
            metadata = json.loads(observation['metadata']) if observation else None
            if isinstance(metadata, dict) and metadata.get('Size') == size:
                expected = normalize_quickxor(metadata.get(QUICKXOR_TYPE))
        except (sqlite3.OperationalError, TypeError, ValueError):
            pass  # Old databases or invalid evidence must not authorize a download.
        if expected is None:
            raise JobProblem('source_hash_unavailable', defer=True)
        try:
            self.command(['rclone', 'copyto', job['remote_path'], video, '--retries', '1',
                          '--low-level-retries', '2', '--transfers', '1', '--max-transfer',
                          f'{size + 1024**2}B', '--cutoff-mode', 'HARD'], 900)
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or '').casefold()
            if any(x in detail for x in ('unauthorized', 'forbidden', 'invalid token', 'status code 401',
                                         'status code 403')):
                raise JobProblem('source_authentication_failed') from exc
            if any(x in detail for x in ('object not found', 'file not found', '404 not found')):
                raise JobProblem('remote_object_not_found', defer=True) from exc
            if 'sizes differ' in detail:
                raise JobProblem('source_download_size_mismatch', defer=True) from exc
            raise JobProblem('source_download_failed', defer=True) from exc
        except subprocess.TimeoutExpired as exc:
            raise JobProblem('source_download_timeout', defer=True) from exc
        if not video.is_file() or video.stat().st_size != size:
            raise JobProblem('source_download_size_mismatch', defer=True)
        try:
            result = self.command(['rclone', 'hashsum', QUICKXOR_TYPE, video, '--config', '/dev/null'], 900)
        except (OSError, subprocess.SubprocessError) as exc:
            raise JobProblem('source_download_hash_failed', defer=True) from exc
        match = re.fullmatch(r'([0-9a-fA-F]{40})  ' + re.escape(video.name) + r'\n?', result.stdout)
        if match is None:
            raise JobProblem('source_download_hash_failed', defer=True)
        if match[1].lower() != expected:
            raise JobProblem('source_download_hash_mismatch', defer=True)
        return expected

    def verify_remote(self, job, expected):
        try:
            result = self.command(['rclone', 'lsjson', job['remote_path'], '--stat', '--hash',
                                   '--hash-type', QUICKXOR_TYPE, '--retries', '1', '--low-level-retries', '2'], 90)
            remote = json.loads(result.stdout)
        except (subprocess.SubprocessError, ValueError) as exc:
            raise JobProblem('source_recheck_failed', defer=True) from exc
        if (not isinstance(remote, dict) or remote.get('IsDir') is not False
                or remote.get('Size') != job['size'] or rclone_quickxor(remote.get('Hashes')) != expected):
            raise JobProblem('source_changed_before_publication', defer=True)

    def probe(self, video, expected):
        try:
            result = self.command(['ffprobe', '-v', 'error', '-select_streams', 'a:0',
                                   '-show_entries', 'stream=index,start_time,duration:format=start_time,duration',
                                   '-of', 'json', video], 60)
            media = json.loads(result.stdout)
            duration = float(media['format']['duration'])
            audio, = media['streams']
            if not math.isfinite(duration) or not 0 < duration <= 86400:
                raise ValueError('invalid audio duration or stream')
            # A video track can slightly outlast its audio. Extraction separately
            # verifies PCM and PTS against the declared audio timeline.
            audio_end = duration
            if audio.get('duration') not in (None, 'N/A'):
                start = float(audio.get('start_time', '0')) - float(media['format'].get('start_time', '0'))
                audio_end = start + float(audio['duration'])
                if not math.isfinite(audio_end) or audio_end <= 0 or not math.isfinite(start):
                    raise ValueError('invalid audio timeline')
                if not -0.05 <= start <= 0.05 or abs(duration - audio_end) > 0.25:
                    raise JobProblem('source_audio_timeline_mismatch', review=True)
                audio_end = min(audio_end, duration)
        except (subprocess.SubprocessError, TypeError, KeyError, ValueError) as exc:
            raise JobProblem('source_audio_probe_failed', review=True) from exc
        if expected and abs(duration - float(expected)) > max(5, float(expected) * 0.05):
            raise JobProblem('source_duration_mismatch', defer=True)
        return audio_end

    def process(self, job, work, checkpoints):
        cfg = self.cfg
        started = time.monotonic()
        self.require_auth()
        self.queue.check_source(job, self.owner)
        video = work / 'source.mp4'
        quickxor = self.download(job, video)
        download_s = time.monotonic() - started
        processed = time.monotonic()
        source_sha = file_sha256(video)
        duration = self.probe(video, job['duration_s'])
        runtime = file_identity(cfg.binary)
        if file_identity(cfg.model) != MODEL_SHA256:
            raise PermissionError('model identity changed')
        signature = digest([3, runtime, MODEL_SHA256, WHISPER_FLAGS, CHUNK_SECONDS, OVERLAP_SECONDS])
        source = {k: job[k] for k in SOURCE_FIELDS}
        chunks = []
        reused = 0
        offset = 0.0
        while offset < duration:
            self.require_auth()
            self.queue.check_source(job, self.owner)
            if shutil.disk_usage(cfg.state).free < RESERVE + WORK_BYTES:
                raise JobProblem('storage_reserve_reached', defer=True)
            length = min(CHUNK_SECONDS, duration - offset)
            identity = [source, source_sha, signature, offset, length]
            checkpoint = checkpoints / f'{len(chunks)}.json'
            data = load_checkpoint(checkpoint, identity)
            if data is None:
                wav, prefix = work / 'chunk.wav', work / 'asr'
                try:
                    actual, quiet = self.extract(video, wav, offset, length)
                except (subprocess.CalledProcessError, wave.Error, EOFError) as exc:
                    raise JobProblem('source_audio_decode_failed', review=True) from exc
                raw = {'transcription': []}
                if actual > 0:
                    try:
                        self.require_auth()
                        self.command(decoder_command(cfg, wav, prefix), CHUNK_TIMEOUT)
                    except subprocess.SubprocessError as exc:
                        raise JobProblem('whisper_timeout' if isinstance(exc, subprocess.TimeoutExpired)
                                         else 'whisper_failed') from exc
                    try:
                        result = json.loads(prefix.with_suffix('.json').read_text())
                        rows = result['transcription']
                        if not isinstance(rows, list):
                            raise ValueError('invalid_decoder_output')
                        raw = {'transcription': [{'offsets': row['offsets'], 'text': row['text']} for row in rows]}
                        parse_whisper(raw, offset)
                    except (OSError, KeyError, TypeError, ValueError, OverflowError) as exc:
                        raise JobProblem('invalid_decoder_output', review=True) from exc
                data = {'audio_duration_s': actual, 'silence': quiet, 'raw': raw}
                atomic_json(checkpoint, identity, data)
                wav.unlink(missing_ok=True)
                prefix.with_suffix('.json').unlink(missing_ok=True)
            else:
                reused += 1
            chunks.append({**data, 'offset_s': offset, 'duration_s': length,
                           'segments': parse_whisper(data['raw'], offset)})
            self.queue.progress(job, self.owner, (offset + length) / duration)
            if offset + length >= duration:
                break
            offset += CHUNK_SECONDS - OVERLAP_SECONDS
        processing_s = time.monotonic() - processed
        began_qa = time.monotonic()
        segments, qa = assess(chunks, duration, chunk_s=CHUNK_SECONDS, overlap_s=OVERLAP_SECONDS)
        qa_s = time.monotonic() - began_qa
        qa.update(source_sha256=source_sha, decoder_sha256=runtime, duration_s=duration)
        self.require_auth()
        began_publish = time.monotonic()
        if qa['passed']:
            self.verify_remote(job, quickxor)
            self.queue.finish(job, self.owner, segments, qa, source)
            state = 'done'
        else:
            state = self.queue.review(job, self.owner, qa)
        publication_s = time.monotonic() - began_publish
        return {'state': state, 'outcome': qa['outcome'],
                'reasons': sorted({f['kind'] for f in qa['blockers'] or qa['warnings']}),
                'audio_s': round(duration, 3), 'download_s': round(download_s, 3),
                'processing_s': round(processing_s, 3), 'qa_s': round(qa_s, 3),
                'publication_s': round(publication_s, 3), 'reused_chunks': reused,
                'active_s_per_audio_s': round((time.monotonic() - started) / duration, 3)}

    def run_once(self, lesson_id=None):
        self.require_auth()
        free = shutil.disk_usage(self.cfg.state).free
        available = free - RESERVE - WORK_BYTES - 1024**2
        if available <= 0:
            return {'state': 'paused_storage'}
        job = self.queue.lease(self.owner, lesson_id=lesson_id, max_source_bytes=available)
        if job is None:
            return {'state': 'idle'}
        key = {k: job[k] for k in ('lesson_id', 'version')}
        scratch, root = self.roots()
        checkpoints = private_dir(root / digest(key))
        sync_dir(root)
        try:
            with tempfile.TemporaryDirectory(prefix='job-', dir=scratch) as work:
                result = self.process(job, Path(work), checkpoints)
        except LeaseLost:
            result = {'state': 'lease_lost'}
        except (TranscriptRejected, JobProblem) as exc:
            try:
                if isinstance(exc, TranscriptRejected):
                    result = {'state': self.queue.fail(job, self.owner, 'source_changed', stale=True)}
                elif exc.review:
                    state = self.queue.review(job, self.owner, {'passed': False, 'blockers': [{'kind': str(exc)}]})
                    result = {'state': state, 'outcome': 'REVIEW_REQUIRED', 'reason': str(exc)}
                else:
                    result = {'state': self.queue.fail(job, self.owner, str(exc), defer=exc.defer),
                              'reason': str(exc)}
            except LeaseLost:
                result = {'state': 'lease_lost'}
        if result['state'] in {'done', 'superseded'}:
            shutil.rmtree(checkpoints)
        return {**key, **result}


def status(cfg):
    with closing(FOStore(cfg.db, readonly=True).conn) as c:
        return {'reset_applied': mvp_reset_applied(c),
                'counts': dict(c.execute('SELECT state,count(*) FROM transcription_jobs GROUP BY state')),
                'leased': [dict(row) for row in c.execute('''SELECT lesson_id,version,progress,updated_at
                                                         FROM transcription_jobs WHERE state='leased' ''')],
                'free_bytes': shutil.disk_usage(cfg.state).free}


def preflight(cfg):
    state = status(cfg)
    if not os.access(cfg.binary, os.X_OK) or file_identity(cfg.model) != MODEL_SHA256:
        raise ValueError('Whisper executable or pinned model unavailable')
    if not all(shutil.which(name) for name in ('ffmpeg', 'ffprobe', 'rclone')):
        raise ValueError('FFmpeg, ffprobe or rclone unavailable')
    if state['free_bytes'] < RESERVE + WORK_BYTES:
        raise ValueError('insufficient storage reserve')
    return {**state, 'authorized': authorized(cfg), 'model_sha256': MODEL_SHA256,
            'decoder_sha256': file_identity(cfg.binary), 'inference_executed': False}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check-only', action='store_true')
    mode.add_argument('--status', action='store_true')
    mode.add_argument('--run', action='store_true')
    mode.add_argument('--retry', metavar='LESSON_ID')
    p.add_argument('--loop', action='store_true')
    p.add_argument('--lesson-id', action='append', help='Run only this lesson; repeat for a serial pilot')
    a = p.parse_args(argv)
    if (a.loop or a.lesson_id) and (not a.run or (a.loop and a.lesson_id)):
        p.error('--loop and --lesson-id require --run and cannot be combined')
    cfg = Config.from_env()
    try:
        if a.check_only or a.status:
            print(json.dumps(preflight(cfg) if a.check_only else status(cfg)))
            return 0
        if not authorized(cfg) or not preflight(cfg)['reset_applied']:
            print('transcription authorization and MVP reset required', file=sys.stderr)
            return 3
        if a.retry:
            store = FOStore(cfg.db)
            with closing(store.conn):
                return 0 if TranscriptionQueue(store).retry(a.retry) else 2
        with leader_lock(cfg.state), db_worker_lock(cfg.db) as fd:
            store = FOStore(cfg.db)
            with closing(store.conn):
                worker = Worker(cfg, TranscriptionQueue(store), fd)
                worker.recover()
                if not a.loop:
                    for lesson in a.lesson_id or (None,):
                        print(json.dumps(worker.run_once(lesson)), flush=True)
                    return 0
                last_state = None
                while True:
                    result = worker.run_once()
                    state = result['state']
                    if 'lesson_id' in result or state != last_state:
                        print(json.dumps(result), flush=True)
                    last_state = state
                    if state in ('idle', 'paused_storage'):
                        time.sleep(60)
    except BlockingIOError:
        print('transcription leader already holds the lock', file=sys.stderr)
        return 4
    except PermissionError:
        print('transcription authorization or model identity changed', file=sys.stderr)
        return 3
    except (OSError, sqlite3.Error, ValueError, LeaseLost, TranscriptRejected) as exc:
        print(f'transcription worker stopped: {type(exc).__name__}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
