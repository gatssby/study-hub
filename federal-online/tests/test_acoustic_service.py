import fcntl
import hashlib
import os
import signal
import subprocess
import sys
import time
import zlib
from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from fo_hub import acoustic_review as ar
from fo_hub.worker import atomic_json
from test_review_reassessment import fixture


def test_review_wait_is_bounded_but_can_reserve_a_long_whisper_turn(tmp_path):
    cfg = SimpleNamespace(state=tmp_path)
    locks = tmp_path / 'locks'
    locks.mkdir()
    for name in ('acoustic-review.turn', 'transcription.lock'):
        (locks / name).touch()
    with ar.whisper_lock(cfg, wait=48*60) as lock_fd:
        assert os.fstat(lock_fd).st_ino == (locks / 'transcription.lock').stat().st_ino
    with pytest.raises(ValueError):
        with ar.whisper_lock(cfg, wait=48*60+1):
            pass


def test_hard_killed_reviewer_cannot_release_decoder_lock_while_child_runs(tmp_path):
    if sys.platform != 'linux':
        pytest.skip('Linux flock open-file-description semantics')
    lock = tmp_path / 'transcription.lock'
    lock.touch()
    ready = tmp_path / 'child'
    parent = subprocess.Popen([sys.executable, '-c', '''
import fcntl, sys
from fo_hub.window_benchmark import run_process_group
with open(sys.argv[1], 'rb+') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    run_process_group([sys.executable, '-c',
        'import os,pathlib,sys,time; pathlib.Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(5)',
        sys.argv[2]], timeout=10, pass_fds=(lock.fileno(),))
''', str(lock), str(ready)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    child = None
    try:
        deadline = time.monotonic() + 5
        while not ready.exists() and parent.poll() is None and time.monotonic() < deadline:
            time.sleep(.02)
        assert ready.exists(), 'the command never acquired its inherited decoder lock'
        child = int(ready.read_text())
        parent.kill()
        parent.wait(timeout=2)
        with lock.open('rb+') as other:
            with pytest.raises(BlockingIOError):
                fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.kill(child, signal.SIGKILL)
            deadline = time.monotonic() + 2
            while True:
                try:
                    fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    assert time.monotonic() < deadline
                    time.sleep(.02)
    finally:
        if parent.poll() is None:
            parent.kill()
            parent.wait(timeout=2)
        if child is not None:
            try:
                os.kill(child, signal.SIGKILL)
            except ProcessLookupError:
                pass


def test_retry_budget_survives_interruption_and_is_evidence_scoped(tmp_path):
    from fo_hub.acoustic_service import AttemptBudget

    key, changed = 'a' * 64, 'b' * 64
    budget = AttemptBudget(tmp_path)
    assert budget.allows(key, now=100)
    budget.reserve(key, now=100)
    resumed = AttemptBudget(tmp_path)
    assert not resumed.allows(key, now=101)
    assert resumed.allows(changed, now=101)
    assert resumed.allows(key, now=86501)
    resumed.reserve(key, now=86501)
    assert not AttemptBudget(tmp_path).allows(key, now=10**7)
    assert (tmp_path / (key + '.json')).stat().st_mode & 0o777 == 0o600


def test_scheduled_recovery_cleans_only_its_verified_disposable_files(tmp_path):
    from fo_hub.acoustic_service import clean_work

    scheduled = tmp_path / 'scheduled-work-abcd1234'
    scheduled.mkdir(mode=0o700)
    (scheduled / 'source.mp4').touch(mode=0o600)
    (scheduled / 'window.wav').touch(mode=0o600)
    pilot = tmp_path / 'work-legacy'
    pilot.mkdir(mode=0o700)
    (pilot / 'source.mp4').touch()
    clean_work(tmp_path)
    assert not scheduled.exists()
    assert (pilot / 'source.mp4').exists()
    suspicious = tmp_path / 'scheduled-work-abcd9876'
    suspicious.mkdir(mode=0o700)
    (suspicious / 'source.mp4').symlink_to(pilot / 'source.mp4')
    with pytest.raises(ar.Blocked, match='untrusted_scheduled_work'):
        clean_work(tmp_path)
    assert (pilot / 'source.mp4').exists()


def test_discovery_is_read_only_and_skips_reviewed_or_stale_evidence(tmp_path, monkeypatch):
    from fo_hub.acoustic_service import AttemptBudget, select

    worker, store, lesson, original, artifact = fixture(tmp_path)
    monkeypatch.setattr(ar.shutil, 'disk_usage', lambda _: SimpleNamespace(free=10 * 2**30))
    root = tmp_path / 'acoustic-review'
    root.mkdir(mode=0o700)
    budget = AttemptBudget(root)
    current_qa = original.with_name(f'v1.qa-v{ar.QA_POLICY_VERSION}.json.gz')
    artifact.update(qa_policy_version=ar.QA_POLICY_VERSION,
                    reassessment={'input_sha256': hashlib.sha256(original.read_bytes()).hexdigest()},
                    qa={'passed': False, 'blockers': [{'kind': 'text_during_measured_silence', 'start': 6, 'end': 7}]})
    atomic_json(current_qa, artifact)
    original_bytes = original.read_bytes()
    decision = select(worker.cfg, root, budget, now=100)
    assert decision is not None
    lesson_id, version, key = decision
    assert (lesson_id, version) == (lesson['lesson_id'], 1)
    ar.write_receipt(root / f'{lesson_id}-v1-{key}.json.gz', {'fingerprint': key, 'published': False})
    assert select(worker.cfg, root, budget, now=100) is None
    with store.conn:
        store.conn.execute("UPDATE lesson_video_sources SET revision='2'")
    atomic_json(current_qa, {**artifact, 'changed': True})
    assert select(worker.cfg, root, budget, now=100) is None
    assert original.read_bytes() == original_bytes
    assert store.get_transcript(lesson_id) is None
    assert store.conn.execute('SELECT state, attempts FROM transcription_jobs').fetchone()[:] == ('review', 1)


@pytest.mark.parametrize('case', ['corrupt_gzip', 'malformed_blockers', 'does_not_fit', 'older_fallback'])
def test_discovery_cannot_be_starved_by_a_higher_priority_lesson(tmp_path, monkeypatch, case):
    from fo_hub.acoustic_service import AttemptBudget, select

    worker, store, lesson, _, artifact = fixture(tmp_path)
    good = lesson['lesson_id']
    bad = 'fo_' + '0' * 16
    db = store.conn
    with db:
        for table in ('lessons', 'lesson_video_sources', 'transcription_jobs'):
            cols = [r[1] for r in db.execute(f'PRAGMA table_info({table})')]
            db.execute(f'INSERT INTO {table} ({",".join(cols)}) SELECT '
                       + ','.join('?' if c == 'lesson_id' else c for c in cols)
                       + f' FROM {table} WHERE lesson_id=?', (bad, good))
        db.execute('UPDATE transcription_jobs SET updated_at=? WHERE lesson_id=?',
                   (300_000 if case == 'older_fallback' else 10, bad))
        db.execute('UPDATE transcription_jobs SET updated_at=20 WHERE lesson_id=?', (good,))
        if case == 'does_not_fit':
            db.execute('UPDATE lesson_video_sources SET size=900 WHERE lesson_id=?', (bad,))
    monkeypatch.setattr(ar.shutil, 'disk_usage', lambda _: SimpleNamespace(
        free=ar.storage_required(900, 9 + ar.WORK_BYTES)))

    def input_for(_cfg, lesson_id, *_):
        if lesson_id == bad and case == 'corrupt_gzip':
            raise zlib.error('corrupt gzip')
        kind = 'acoustic_repetition_unconfirmed' if lesson_id == bad else 'ngram_repetition'
        flags = [None] if lesson_id == bad and case == 'malformed_blockers' else [
            {'kind': kind, 'start': 6, 'end': 7}]
        return ({**artifact, 'qa': {'blockers': flags}},
                'a' * 64, 30, 'b' * 64, 'c' * 64)

    monkeypatch.setattr(ar, 'verified_input', input_for)
    selected = select(worker.cfg, tmp_path, AttemptBudget(tmp_path), now=400_000)
    assert selected is not None and selected[0] == good


def test_scheduled_cleanup_runs_even_without_an_eligible_job(tmp_path, monkeypatch):
    from fo_hub import acoustic_service as service

    root = tmp_path / 'transcripts/acoustic-review'
    root.mkdir(parents=True, mode=0o700)
    orphan = root / 'scheduled-work-abcd1234'
    orphan.mkdir(mode=0o700)
    (orphan / 'source.mp4').touch(mode=0o600)
    monkeypatch.setattr(ar, 'require_limits', lambda: None)
    monkeypatch.setattr(service, 'gate', lambda _: {'allowed': True})
    monkeypatch.setattr(service, 'has_primary_leader', lambda _: True)
    monkeypatch.setattr(service, 'select', lambda *_: None)
    events = []
    monkeypatch.setattr(ar, 'whisper_lock', lambda *_args, **_kwargs: nullcontext(1))
    cfg = SimpleNamespace(state=tmp_path)
    assert service.scheduled_turn(cfg, None, lambda: events.append('ready')) == {'state': 'no_eligible_evidence'}
    assert events == ['ready']
    assert not orphan.exists()


@pytest.mark.parametrize(('case', 'reason', 'expected'), [
    ('runtime', 'bad_runtime', []),
    ('model_revokes', 'transcription_not_authorized', []),
    ('download_revokes', 'transcription_not_authorized', ['reserve', 'download']),
    ('extract_revokes', 'transcription_not_authorized', ['reserve', 'download', 'probe', 'extract']),
    ('extract_changes_source', 'evidence_changed_during_review', ['reserve', 'download', 'probe', 'extract']),
])
def test_attempt_and_each_heavy_step_are_fenced(tmp_path, monkeypatch, case, reason, expected):
    worker, _, lesson, _, artifact = fixture(tmp_path)
    artifact['qa'] = {'blockers': [{'kind': 'text_during_measured_silence', 'start': 6, 'end': 7}]}
    source = {'size': 9, 'remote_path': 'onedrive:Federal Online/a.mp4', 'subject': 'Biologia',
              'front': None, 'module': None}
    authorized = True
    calls = []

    def step(name):
        nonlocal authorized
        calls.append(name)
        if case == name + '_revokes':
            authorized = False
        if case == name + '_changes_source':
            source['remote_path'] = 'changed'

    def load(_):
        nonlocal authorized
        if case == 'runtime':
            raise ar.Blocked('bad_runtime')
        if case == 'model_revokes':
            authorized = False
        return None, None

    def download(args, **_kwargs):
        args[3].write_bytes(b'fakevideo')
        step('download')

    def extract(_video, audio, *_args, **_kwargs):
        step('extract')
        audio.touch()
        return b''

    monkeypatch.setattr(ar, 'gate', lambda _: {'allowed': authorized})
    monkeypatch.setattr(ar, 'require_limits', lambda: None)
    monkeypatch.setattr(ar, 'require_spare_capacity', lambda: None)
    monkeypatch.setattr(ar, 'require_storage', lambda *_: None)
    monkeypatch.setattr(ar, 'whisper_lock', lambda *_args, **_kwargs: nullcontext(1))
    monkeypatch.setattr(ar, 'snapshot', lambda *_: (dict(source), set(), 9))
    monkeypatch.setattr(ar, 'verified_input', lambda *_: (artifact, artifact['source_sha256'], 30, '', ''))
    monkeypatch.setattr(ar, 'verify_runtime', lambda _: None)
    monkeypatch.setattr(ar, 'load_models', load)
    monkeypatch.setattr(ar, 'run_process_group', download)
    monkeypatch.setattr(ar, 'probe_video', lambda *_args, **_kwargs: step('probe'))
    monkeypatch.setattr(ar, 'extract', extract)
    monkeypatch.setattr(ar, 'analyze_pcm', lambda *_: pytest.fail('must not launch inference'))
    with pytest.raises(ar.Blocked, match=reason):
        ar.review(worker.cfg, tmp_path, lesson['lesson_id'], 1, reserve=lambda _: step('reserve'))
    assert calls == expected
    assert not list((tmp_path / 'transcripts/acoustic-review').glob('*'))
