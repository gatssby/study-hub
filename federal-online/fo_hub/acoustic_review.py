"""Manual, evidence-only Parakeet pilot. Never updates the queue or publishes."""

import argparse
import fcntl
import gzip
import hashlib
import json
import math
import os
import re
import resource
import shutil
import signal
import sqlite3
import subprocess
import tempfile
import time
import unicodedata
import wave
from contextlib import ExitStack, closing, contextmanager
from copy import deepcopy
from dataclasses import dataclass
from difflib import SequenceMatcher
from io import BytesIO
from pathlib import Path

from .scheduler import EXCLUDABLE_DISCIPLINES, discipline
from .store import ACCEPTED_CORPUS, FOStore
from .transcription import QA_POLICY_VERSION, classify_qa
from .window_benchmark import run_process_group
from .worker import RESERVE, Config, file_sha256, gate

RATE = 16000
HEADROOM = 2**30
WORK_BYTES = 8 * 2**20
MAX_WINDOWS = 12
MAX_WAIT_SECONDS = 120
MAX_SCHEDULED_WAIT_SECONDS = 7200
MIN_AVAILABLE_RAM = 8 * 2**30
MODEL_MEMORY_MAX = 3 * 2**30
SCHEMA = 1
TIMESTAMP_FLAGS = {'bad_timestamp', 'non_monotonic', 'boundary_timestamp_drift'}
REPETITION_FLAGS = {'acoustic_repetition_unconfirmed', 'duplicate_segment', 'ngram_repetition',
                    'token_repetition', 'phrase_repetition'}
MODEL_MANIFEST = (Path(__file__).resolve().parents[1] / 'transcription' /
                  'parakeet-runtime' / 'manifest.json')


class Blocked(RuntimeError):
    """A stable public reason code, never a path, transcript or stderr."""


@dataclass(frozen=True)
class Window:
    start: float
    end: float
    target_start: float
    target_end: float
    kind: str


def plan_windows(duration, blockers, segments=()):
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('invalid duration')
    windows = []
    for flag in blockers:
        if not isinstance(flag, dict) or not isinstance(flag.get('kind'), str):
            raise Blocked('malformed_review_window_evidence')
        idx = flag.get('idx')
        row = segments[idx] if type(idx) is int and 0 <= idx < len(segments) else {}
        if not isinstance(row, dict):
            raise Blocked('malformed_review_window_evidence')
        raw_start, raw_end = flag.get('start', row.get('start')), flag.get('end', row.get('end'))
        if raw_start is None or raw_end is None:
            continue
        try:
            start, end = float(raw_start), float(raw_end)
        except (ValueError, TypeError):
            continue
        if not 0 <= start <= end <= duration:
            continue
        while True:
            stop = min(start + 20, end)
            window = Window(max(0, start - 3), min(duration, stop + 3), start, stop,
                            flag['kind'])
            if window not in windows:
                windows.append(window)
                if len(windows) > MAX_WINDOWS:
                    raise Blocked('window_budget_exceeded')
            if stop == end:
                break
            start = stop
    return windows


def map_vad(offset, count, parts):
    result = []
    previous = 0
    for start, end in parts:
        if not previous <= start < end <= count:
            raise ValueError('invalid VAD intervals')
        result.append([offset + start / RATE, offset + end / RATE])
        previous = end
    return result


def classify(window, speech, silence):
    start, end = window.target_start, window.target_end
    if (window.kind == 'text_during_measured_silence' and end - start >= .25
            and any(a <= start < end <= b for a, b in silence)
            and not any(a < end + .15 and b > start - .15 for a, b in speech)):
        return 'speech_generated_during_measured_silence'
    if window.kind == 'text_during_measured_silence' or window.kind in REPETITION_FLAGS:
        return 'inconclusive_disagreement'
    if window.kind in TIMESTAMP_FLAGS:
        return 'invalid_timestamps' if window.kind == 'bad_timestamp' else 'inconclusive_disagreement'
    return 'insufficient_source_evidence'


def compare_text(whisper, parakeet):
    """Lexical triage only: two ASR outputs are not verified speech."""
    def words(text):
        return re.findall(r'\w+', unicodedata.normalize('NFC', text).casefold())

    reference = words(' '.join(row['text'] for row in whisper))
    hypothesis = words(parakeet or '')
    if parakeet is None:
        return {'agreement': 'parakeet_skipped_no_vad_speech'}
    if not reference and hypothesis:
        return {'agreement': 'possible_missing_transcription'}
    if not hypothesis:
        return {'agreement': 'empty_parakeet_output'}
    return {'agreement': 'same_normalized_text' if hypothesis == reference else 'different_text',
            'lexical_similarity': SequenceMatcher(None, reference, hypothesis, autojunk=False).ratio()}


def source_identity(artifact, lesson_id, source, version, excluded):
    if discipline(source) in EXCLUDABLE_DISCIPLINES | excluded:
        raise Blocked('excluded_discipline')
    remote = source['remote_path']
    if (not source['present'] or not source['available'] or source['state'] != 'review'
            or source['version'] != version or source['revision'] != str(version)
            or not isinstance(remote, str) or not remote.startswith('onedrive:Federal Online/')
            or '..' in Path(remote).parts or not source['size'] or source['size'] <= 0):
        raise Blocked('source_not_current_review')
    expected = {'lesson_id': lesson_id, 'version': version, 'corpus': ACCEPTED_CORPUS,
                'source_revision': str(version), 'source_size': source['size'],
                'source_remote_path': remote}
    if any(artifact.get(k) != v for k, v in expected.items()):
        raise Blocked('review_source_identity_mismatch')
    digest = artifact.get('source_sha256')
    duration = float(artifact['duration_s'])
    if not isinstance(digest, str) or not re.fullmatch('[a-f0-9]{64}', digest) or not 0 < duration <= 86400:
        raise Blocked('insufficient_source_evidence')
    return digest, duration


def storage_required(largest, temporary):
    if largest < 0 or temporary < 0:
        raise ValueError('negative storage budget')
    return RESERVE + largest + 100 * 2**20 + HEADROOM + temporary


def require_storage(free, largest, temporary):
    if free < storage_required(largest, temporary):
        raise Blocked('storage_reserve')


def limits_ok(cpu, memory, swap):
    try:
        quota, period = map(int, cpu.split())
        return 0 < quota * 2 <= period and 0 < int(memory) <= MODEL_MEMORY_MAX and int(swap) == 0
    except ValueError:
        return False


def require_limits():
    try:
        cg = Path('/sys/fs/cgroup') / next(
            line.split('::', 1)[1].lstrip('/') for line in Path('/proc/self/cgroup').read_text().splitlines()
            if line.startswith('0::'))
        bounds = [(cg / name).read_text().strip()
                  for name in ('cpu.max', 'memory.max', 'memory.swap.max')]
        if os.nice(0) < 10 or not limits_ok(*bounds):
            raise Blocked('missing_cpu_memory_or_priority_limits')
        io = subprocess.run(['ionice', '-p', str(os.getpid())], check=True,
                            capture_output=True, text=True, timeout=2)
        if io.stdout.strip() != 'idle':
            raise Blocked('missing_io_priority')
    except (OSError, StopIteration, subprocess.SubprocessError):
        raise Blocked('cannot_verify_process_limits') from None


def require_spare_capacity():
    available = next(int(line.split()[1]) * 1024 for line in Path('/proc/meminfo').read_text().splitlines()
                     if line.startswith('MemAvailable:'))
    if available < MIN_AVAILABLE_RAM:
        raise Blocked('insufficient_available_ram')

    def sample():
        values = [int(v) for v in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
        return sum(values), values[3]

    t1, i1 = sample()
    time.sleep(2)
    t2, i2 = sample()
    # On the four-OCPU VPS this leaves at least one full OCPU idle before a 0.5-OCPU review.
    if t2 <= t1 or (i2 - i1) / (t2 - t1) < .25:
        raise Blocked('insufficient_idle_cpu')


@contextmanager
def whisper_lock(cfg, *, wait=0):
    if not 0 <= wait <= MAX_SCHEDULED_WAIT_SECONDS:
        raise ValueError('invalid wait limit')
    path = cfg.state / 'locks/transcription.lock'
    with ExitStack() as stack:
        turn = None
        try:
            lock = stack.enter_context(os.fdopen(os.open(path, os.O_RDWR | os.O_NOFOLLOW), 'rb+'))
            if wait:
                # Only a worker that has started with the cooperative loop can honor a request.
                turn = stack.enter_context(os.fdopen(os.open(path.with_name('acoustic-review.turn'),
                                                            os.O_RDWR | os.O_NOFOLLOW), 'rb+'))
        except OSError:
            raise Blocked('whisper_lock_unavailable') from None
        if turn is not None:
            try:
                fcntl.flock(turn, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Blocked('another_acoustic_review_requested') from None
        deadline = time.monotonic() + wait
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise Blocked('whisper_owns_transcription_lock') from None
                time.sleep(min(1, remaining))
        # Preserve the fence when systemd kills Python before its command.
        yield lock.fileno()


def write_receipt(path, result):
    with tempfile.NamedTemporaryFile(prefix='.result-', dir=path.parent, delete=False) as handle:
        temp = Path(handle.name)
        try:
            handle.write(gzip.compress(json.dumps(result, ensure_ascii=False, allow_nan=False).encode(), mtime=0))
            handle.flush()
            os.fsync(handle.fileno())
            os.link(temp, path)  # Atomic no-clobber; partial results are never visible.
            with dir_fd(path.parent) as fd:
                os.fsync(fd)
        finally:
            temp.unlink(missing_ok=True)


@contextmanager
def dir_fd(path):
    fd = os.open(path, os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        yield fd
    finally:
        os.close(fd)


def read_receipt(path, fingerprint):
    if path.is_symlink() or path.stat().st_mode & 0o077:
        raise Blocked('untrusted_receipt')
    with gzip.open(path, 'rt') as stream:
        result = json.load(stream)
    if result['fingerprint'] != fingerprint or result['published'] is not False:
        raise Blocked('untrusted_receipt')
    return result


def recheck_unchanged(qa, segments, duration):
    return classify_qa(deepcopy(qa), segments, duration)


def read_review(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 16 * 2**20:
        raise Blocked('missing_or_untrusted_review_artifact')
    raw = path.read_bytes()
    with gzip.GzipFile(fileobj=BytesIO(raw)) as stream:
        decoded = stream.read(64 * 2**20 + 1)
    if len(decoded) > 64 * 2**20:
        raise Blocked('oversize_review_artifact')
    return json.loads(decoded), hashlib.sha256(raw).hexdigest()


def snapshot(cfg, lesson_id, version):
    with closing(FOStore(cfg.db, readonly=True).conn) as db:
        db.execute('BEGIN')
        source = db.execute('SELECT l.version,l.present,l.subject,l.front,l.module,s.revision,s.size,'
                            's.available,s.remote_path,j.state FROM lessons l '
                            'JOIN lesson_video_sources s USING(lesson_id) JOIN transcription_jobs j '
                            'ON j.lesson_id=l.lesson_id AND j.version=l.version '
                            'WHERE l.lesson_id=? AND j.version=?', (lesson_id, version)).fetchone()
        if source is None:
            raise Blocked('source_not_current_review')
        excluded = {r[0] for r in db.execute('SELECT discipline FROM transcription_discipline_exclusions')}
        largest = db.execute('SELECT COALESCE(MAX(size),0) FROM lesson_video_sources WHERE available=1').fetchone()[0]
        if db.execute("SELECT 1 FROM transcription_jobs WHERE state='leased' LIMIT 1").fetchone():
            raise Blocked('whisper_lease_present')
    return dict(source), excluded, largest


def verified_input(cfg, lesson_id, version, source, excluded):
    base = cfg.state / 'transcripts/review' / lesson_id
    original, original_hash = read_review(base / f'v{version}.json.gz')
    latest, receipt_hash = read_review(base / f'v{version}.qa-v{QA_POLICY_VERSION}.json.gz')
    digest, duration = source_identity(original, lesson_id, source, version, excluded)
    if (source_identity(latest, lesson_id, source, version, excluded) != (digest, duration)
            or latest['reassessment']['input_sha256'] != original_hash
            or latest['qa_policy_version'] != QA_POLICY_VERSION or latest['qa']['passed'] is not False
            or not latest['qa']['blockers']):
        raise Blocked('current_qa_receipt_mismatch')
    return latest, digest, duration, original_hash, receipt_hash


def load_models(models):
    import onnx_asr
    import onnxruntime as rt

    options = rt.SessionOptions()
    options.intra_op_num_threads = options.inter_op_num_threads = 1
    options.execution_mode = rt.ExecutionMode.ORT_SEQUENTIAL
    kwargs = {'path': models, 'sess_options': options, 'providers': ['CPUExecutionProvider']}
    asr = onnx_asr.load_model('nemo-conformer-tdt', quantization='int8', **kwargs).with_timestamps()
    return asr, onnx_asr.load_vad('silero', **kwargs)


def verify_runtime(runtime):
    from importlib.metadata import version

    manifest = json.loads(MODEL_MANIFEST.read_text())
    for name, pin in manifest['pip'].items():
        if version(name) != pin:
            raise Blocked('runtime_version_mismatch')
    for asset in manifest['files']:
        path = runtime / 'models' / asset['name']
        if (path.is_symlink() or path.stat().st_size != asset['bytes']
                or file_sha256(path) != asset['sha256']):
            raise Blocked('runtime_model_integrity_failure')


def probe_video(video, duration, *, pass_fds=()):
    probe = run_process_group(['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries',
                               'format=start_time,duration:stream=start_time', '-of', 'json', video],
                              timeout=20, pass_fds=pass_fds)
    meta = json.loads(probe.stdout)
    if (not abs(float(meta['format']['duration']) - duration) <= .05
            or not abs(float(meta['format']['start_time'])) <= .03
            or len(meta['streams']) != 1 or not abs(float(meta['streams'][0]['start_time'])) <= .03):
        raise Blocked('unverified_source_audio_timeline')


def extract(video, audio, window, *, pass_fds=()):
    run_process_group(['ffmpeg', '-v', 'error', '-nostdin', '-threads', '1', '-ss', f'{window.start:.6f}',
                       '-i', video, '-map', '0:a:0', '-t', f'{window.end - window.start:.6f}',
                       '-ar', str(RATE), '-ac', '1', '-c:a', 'pcm_s16le', '-threads', '1', '-y', audio],
                      timeout=25, pass_fds=pass_fds)
    with wave.open(str(audio), 'rb') as stream:
        frames = stream.getnframes()
        if ((stream.getframerate(), stream.getnchannels(), stream.getsampwidth()) != (RATE, 1, 2)
                or abs(frames / RATE - (window.end - window.start)) > .05):
            raise Blocked('audio_window_length_mismatch')
        pcm = stream.readframes(frames)
    if len(pcm) != frames * 2:
        raise Blocked('audio_window_truncated')
    return pcm


def analyze_pcm(pcm, offset, asr, vad):
    import numpy as np

    waveform = np.frombuffer(pcm, dtype='<i2').astype(np.float32) / 32768
    if not .04 <= len(waveform) / RATE <= 27:
        raise Blocked('unsupported_audio_window_length')
    started = time.monotonic()
    intervals, = vad.segment_batch(waveform[None, :], np.array([len(waveform)], dtype=np.int64), RATE)
    speech = map_vad(offset, len(waveform), intervals)
    vad_seconds = time.monotonic() - started
    started = time.monotonic()
    result = asr.recognize(waveform, sample_rate=RATE) if speech else None
    timestamps = None if result is None or result.timestamps is None else [
        offset + float(t) for t in result.timestamps]
    if timestamps is not None and any(not offset <= t <= offset + len(waveform) / RATE + .1 for t in timestamps):
        raise Blocked('invalid_parakeet_timestamps')
    return {'speech': speech, 'parakeet': result.text if result is not None else None,
            'parakeet_token_times_s': timestamps, 'parakeet_tokens': result.tokens if result is not None else None,
            'vad_seconds': vad_seconds, 'asr_seconds': time.monotonic() - started if result is not None else 0,
            'audio_seconds': len(waveform) / RATE, 'pcm_sha256': hashlib.sha256(pcm).hexdigest()}


def evidence_key(lesson_id, version, digest, original_hash, receipt_hash, model_hash):
    return hashlib.sha256(json.dumps([SCHEMA, lesson_id, version, digest, original_hash,
                                      receipt_hash, model_hash, QA_POLICY_VERSION]).encode()).hexdigest()


def review(cfg, runtime, lesson_id, version, *, wait=0, ready=None, reserve=None,
           expected_key=None, work_prefix='work-'):
    # Gate in this order: a held Whisper lock precludes even model loading or downloads.
    if wait:
        require_limits()
    with whisper_lock(cfg, wait=wait) as lock_fd:
        if ready is not None:
            ready()
        command_fds = (lock_fd,)
        started = time.monotonic()
        require_limits()
        require_spare_capacity()
        if not gate(cfg)['allowed']:
            raise Blocked('transcription_not_authorized')
        source, excluded, largest = snapshot(cfg, lesson_id, version)
        art, digest, duration, original_hash, receipt_hash = verified_input(cfg, lesson_id, version, source, excluded)
        blockers = art['qa']['blockers']
        windows = plan_windows(duration, blockers, art['segments'])
        model_hash = file_sha256(MODEL_MANIFEST)
        fingerprint = evidence_key(lesson_id, version, digest, original_hash, receipt_hash, model_hash)
        if expected_key is not None and fingerprint != expected_key:
            raise Blocked('evidence_changed_before_review')
        require_storage(shutil.disk_usage(cfg.state).free, largest, source['size'] + WORK_BYTES)
        root = cfg.state / 'transcripts/acoustic-review'
        root.mkdir(mode=0o700, exist_ok=True)
        if root.is_symlink() or root.stat().st_mode & 0o077:
            raise Blocked('private_review_directory_required')
        receipt = root / f'{lesson_id}-v{version}-{fingerprint}.json.gz'
        if receipt.exists() or receipt.is_symlink():
            read_receipt(receipt, fingerprint)
            return {'state': 'unchanged_evidence', 'windows': 0}
        result = {'fingerprint': fingerprint, 'schema': SCHEMA, 'lesson_id': lesson_id, 'version': version,
                  'source_sha256': digest, 'duration_s': duration, 'original_sha256': original_hash,
                  'qa_receipt_sha256': receipt_hash, 'runtime_manifest_sha256': model_hash,
                  'published': False, 'correction': None, 'windows': [],
                  'initial_blockers': blockers, 'peak_temporary_bytes': 0}
        measured = [(chunk['offset_s'] + a, chunk['offset_s'] + b)
                    for chunk in art['chunks'] for a, b in chunk.get('silence', [])]

        def require_current(*, check_artifact=False):
            if not gate(cfg)['allowed']:
                raise Blocked('transcription_not_authorized')
            latest, current_excluded, current_largest = snapshot(cfg, lesson_id, version)
            if latest != source or discipline(latest) in EXCLUDABLE_DISCIPLINES | current_excluded:
                raise Blocked('evidence_changed_during_review')
            if check_artifact and verified_input(cfg, lesson_id, version, latest, current_excluded)[1:] != (
                    digest, duration, original_hash, receipt_hash):
                raise Blocked('evidence_changed_during_review')
            return current_largest

        if windows:
            verify_runtime(runtime)
            require_current()
            asr, vad = load_models(runtime / 'models')
            # A uniquely named private scratch directory. No cross-job reads or cache writes.
            with tempfile.TemporaryDirectory(prefix=work_prefix, dir=root) as folder:
                video, audio = Path(folder) / 'source.mp4', Path(folder) / 'window.wav'
                largest = require_current(check_artifact=True)
                require_storage(shutil.disk_usage(cfg.state).free, largest, source['size'] + WORK_BYTES)
                if reserve is not None:
                    reserve(fingerprint)
                run_process_group(['rclone', 'copyto', source['remote_path'], video, '--retries', '1',
                                   '--low-level-retries', '1', '--transfers', '1', '--checkers', '1', '--inplace',
                                   '--max-transfer', f"{source['size']}B", '--cutoff-mode', 'HARD'],
                                  timeout=130, pass_fds=command_fds)
                if video.stat().st_size != source['size'] or file_sha256(video) != digest:
                    raise Blocked('remote_source_bytes_changed')
                result['peak_temporary_bytes'] = video.stat().st_size
                require_current()
                probe_video(video, duration, pass_fds=command_fds)
                findings = {}
                for window in windows:
                    bounds = (window.start, window.end)
                    if bounds not in findings:
                        largest = require_current()
                        require_storage(shutil.disk_usage(cfg.state).free, largest, WORK_BYTES)
                        pcm = extract(video, audio, window, pass_fds=command_fds)
                        result['peak_temporary_bytes'] = max(result['peak_temporary_bytes'],
                                                            video.stat().st_size + audio.stat().st_size)
                        audio.unlink()
                        require_current()
                        findings[bounds] = analyze_pcm(pcm, window.start, asr, vad)
                    finding = findings[bounds]
                    whisper = [row for row in art['segments']
                               if row['start'] <= window.end and row['end'] >= window.start]
                    silence = [(a, b) for a, b in measured if a < window.end and b > window.start]
                    result['windows'].append({**vars(window), **finding, 'whisper': whisper,
                                              'comparison': compare_text(whisper, finding['parakeet']),
                                              'existing_measured_silence': silence,
                                              'classification': classify(window, finding['speech'], silence)})
                result['inference_totals'] = {k: sum(f[k] for f in findings.values()) for k in
                                              ('audio_seconds', 'asr_seconds', 'vad_seconds')}
        result['classification'] = ('invalid_timestamps' if not windows and
                                    any(f['kind'] in TIMESTAMP_FLAGS for f in blockers)
                                    else 'insufficient_source_evidence' if not windows
                                    else 'requires_acoustic_adjudication')
        qa = recheck_unchanged(art['qa'], art['segments'], duration)
        result['qa'] = {'policy': QA_POLICY_VERSION, 'passed': qa['passed'],
                        'blocker_kinds': [flag['kind'] for flag in qa['blockers']]}
        require_current(check_artifact=True)
        usage = resource.getrusage(resource.RUSAGE_SELF)
        children = resource.getrusage(resource.RUSAGE_CHILDREN)
        result['resource_use'] = {'elapsed_seconds': time.monotonic() - started,
                                  'cpu_seconds': usage.ru_utime + usage.ru_stime +
                                  children.ru_utime + children.ru_stime,
                                  'process_peak_rss_kib': usage.ru_maxrss,
                                  'largest_child_peak_rss_kib': children.ru_maxrss}
        write_receipt(receipt, result)
        return {'state': 'review_retained', 'windows': len(result['windows']), 'published': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--lesson-id', required=True)
    parser.add_argument('--version', type=int, required=True)
    parser.add_argument('--wait-for-whisper', type=int, choices=range(MAX_WAIT_SECONDS + 1),
                        metavar=f'SEC (0–{MAX_WAIT_SECONDS})', default=0)
    args = parser.parse_args(argv)
    if not re.fullmatch(r'fo_[0-9a-f]{16}', args.lesson_id) or args.version < 1:
        parser.error('invalid lesson ID or version')
    os.umask(0o077)

    def interrupted(*_):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupted)
    try:
        result = review(Config.from_env(), args.runtime, args.lesson_id, args.version, wait=args.wait_for_whisper)
    except Blocked as exc:
        print(json.dumps({'state': 'deferred', 'reason': str(exc)}))
        return 4
    except KeyboardInterrupt:
        print(json.dumps({'state': 'interrupted'}))
        return 130
    except Exception as exc:
        # ffmpeg, rclone, model or JSON errors may include private paths/text.
        print(json.dumps({'state': 'failed', 'error_type': type(exc).__name__}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
