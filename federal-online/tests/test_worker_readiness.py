"""Preparation regressions: synthetic data, injected commands, no real ASR."""
import hashlib
import fcntl
import gzip
import json
import threading
import time
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_worker import setup
from fo_hub.worker import Config, Worker, gate


def ready(tmp_path, duration=30):
    store, lesson, cfg = setup(tmp_path)
    Worker(cfg, store)
    with store.conn:
        store.conn.execute('update lessons set duration_s=?', (duration,))
        store.conn.execute('insert into lesson_video_sources values(?,?,?,?,?,?)',
                           (lesson['lesson_id'], 'onedrive:Federal Online/a.mp4', '1', 9, 1, 'now'))
    return store, lesson, cfg


def fake_runner(cfg, calls, fail_at=None):
    def run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[0] == 'rclone':
            Path(cmd[3]).write_bytes(b'fakevideo')
        elif cmd[0] == 'ffprobe':
            return SimpleNamespace(stdout=json.dumps({'format': {'duration': '30'}}), stderr='')
        elif cmd[0] == 'ffmpeg' and cmd[-1].endswith('.wav'):
            Path(cmd[-1]).write_bytes(b'fakewav')
        elif cmd[0] == str(cfg.binary):
            if fail_at is not None and sum(c[0] == str(cfg.binary) for c in calls) == fail_at:
                raise TimeoutError('synthetic interrupted inference')
            Path(cmd[cmd.index('-of') + 1] + '.json').write_text(json.dumps({
                'transcription': [{'offsets': {'from': 0, 'to': 30000},
                                   'text': 'Conteúdo científico legítimo.'}]}))
        return SimpleNamespace(stdout='', stderr='')
    return run


def test_gate_checks_expected_model_digest(tmp_path):
    _, _, cfg = setup(tmp_path)
    cfg.binary.write_text('fake binary'); cfg.binary.chmod(0o755)
    cfg.model.write_bytes(b'model')
    cfg.auth.write_text('I AUTHORIZE FO TRANSCRIPTION ON VPS'); cfg.marker.touch()
    cfg.model_sha256 = '0' * 64
    result = gate(cfg, {'TRANSCRIPTION_ENABLED': 'true'}, platform='linux')
    assert not result['allowed']
    assert 'model SHA-256 mismatch' in result['reasons']
    cfg.model_sha256 = hashlib.sha256(b'model').hexdigest()
    assert gate(cfg, {'TRANSCRIPTION_ENABLED': 'true'}, platform='linux')['allowed']


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -1])
def test_parse_rejects_nonfinite_or_negative_offsets(value):
    from fo_hub.worker import parse_whisper
    with pytest.raises(ValueError):
        parse_whisper({'transcription': [{'offsets': {'from': value, 'to': 1000}, 'text': 'fala'}]})


def test_lease_does_not_reprocess_published_version_after_crash(tmp_path):
    store, lesson, cfg = ready(tmp_path)
    store.add_transcript(lesson['lesson_id'], 1, [{'start': 0, 'end': 30, 'text': 'já validado'}],
                         'whisper-large-v3', 'generated_v2', True, {'passed': True})
    worker = Worker(cfg, store, gate_fn=lambda: {'allowed': True})
    assert worker.lease() is None
    assert store.conn.execute('select state from transcription_jobs').fetchone()[0] == 'done'


def test_private_evidence_public_segments_and_full_configuration(tmp_path):
    store, lesson, cfg = ready(tmp_path)
    calls = []
    worker = Worker(cfg, store, runner=fake_runner(cfg, calls),
                    gate_fn=lambda: {'allowed': True}, free_bytes=lambda: 20 * 1024**3)
    assert worker.run_once()['state'] == 'validated'
    public = json.loads((tmp_path / 'transcripts/generated_v2' / lesson['lesson_id'] / 'v1.json').read_text())
    assert public['segments'][0]['text'] == 'Conteúdo científico legítimo.'
    assert 'chunks' not in public and 'model_path' not in public
    private = json.loads(gzip.decompress((tmp_path / 'transcripts/private' / lesson['lesson_id'] / 'v1.json.gz').read_bytes()))
    assert private['chunks'][0]['raw']['transcription']
    assert private['source_sha256'] == hashlib.sha256(b'fakevideo').hexdigest()
    assert private['parameters']['no_speech_threshold'] == 0.6
    cmd = next(c for c in calls if c[0] == str(cfg.binary))
    assert '-ojf' in cmd and '-nth' in cmd and '--vad' not in cmd


def test_invalid_duration_is_bounded_before_chunks(tmp_path):
    store, lesson, cfg = ready(tmp_path)
    calls = []
    base = fake_runner(cfg, calls)
    def run(cmd, **kwargs):
        if cmd[0] == 'ffprobe':
            return SimpleNamespace(stdout=json.dumps({'format': {'duration': 'NaN'}}), stderr='')
        return base(cmd, **kwargs)
    worker = Worker(cfg, store, runner=run, gate_fn=lambda: {'allowed': True}, free_bytes=lambda: 20*1024**3)
    assert worker.run_once()['state'] == 'retry'
    assert not any(c[0] == str(cfg.binary) for c in calls)


def test_new_revision_during_inference_never_publishes(tmp_path):
    store, lesson, cfg = ready(tmp_path)
    calls = []
    base = fake_runner(cfg, calls)
    def run(cmd, **kwargs):
        result = base(cmd, **kwargs)
        if cmd[0] == str(cfg.binary):
            with store.conn:
                store.conn.execute('update lessons set version=2')
        return result
    worker = Worker(cfg, store, runner=run, gate_fn=lambda: {'allowed': True}, free_bytes=lambda: 20*1024**3)
    assert worker.run_once()['state'] == 'superseded'
    assert store.get_transcript(lesson['lesson_id']) is None
    assert not (tmp_path/'transcripts/generated_v2').exists()


def test_worker_leases_are_recovered_without_touching_other_owners(tmp_path):
    store, lesson, cfg = ready(tmp_path)
    worker = Worker(cfg, store, gate_fn=lambda: {'allowed': True})
    worker.lease()
    worker.recover()
    row = store.conn.execute('select * from transcription_jobs').fetchone()
    assert row['state'] == 'queued' and row['attempts'] == 1 and row['lease_owner'] is None
    with store.conn:
        store.conn.execute("update transcription_jobs set state='leased',lease_owner='external-worker'")
    worker.recover()
    assert store.conn.execute('select lease_owner from transcription_jobs').fetchone()[0] == 'external-worker'


def test_chunk_checkpoint_survives_failed_later_chunk(tmp_path):
    store, lesson, cfg = ready(tmp_path)
    cfg.chunk_s = 16
    cfg.overlap_s = 2
    calls = []
    base = fake_runner(cfg, calls, fail_at=2)
    def run(cmd, **kwargs):
        result = base(cmd, **kwargs)
        if cmd[0] == str(cfg.binary):
            Path(cmd[cmd.index('-of') + 1] + '.json').write_text(json.dumps({
                'transcription': [{'offsets': {'from': 0, 'to': 16000}, 'text': 'fala técnica'}]}))
        return result
    worker = Worker(cfg, store, runner=run, gate_fn=lambda: {'allowed': True}, free_bytes=lambda: 20*1024**3)
    assert worker.run_once()['state'] == 'retry'
    with store.conn:
        store.conn.execute('update transcription_jobs set retry_at=0')
    calls2 = []
    worker.runner = fake_runner(cfg, calls2)
    worker.run_once()
    assert sum(c[0] == str(cfg.binary) for c in calls2) == 1
    assert list((tmp_path/'transcripts/evidence').rglob('*.json.gz'))


def test_pending_review_enters_after_committed_chunk_before_next_decode(tmp_path):
    from fo_hub import acoustic_review, worker as runtime

    store, lesson, cfg = ready(tmp_path)
    cfg.chunk_s = 16
    cfg.overlap_s = 2
    locks = tmp_path / 'locks'
    locks.mkdir()
    calls = []
    base = fake_runner(cfg, calls)
    reviewed = []

    def review():
        with acoustic_review.whisper_lock(cfg, wait=3):
            from fo_hub.store import FOStore
            with closing(FOStore(cfg.db, readonly=True).conn) as db:
                row = db.execute('SELECT state,lease_owner,progress FROM transcription_jobs').fetchone()
                checkpoint, = (tmp_path/'transcripts/evidence').rglob('0.000-16.000.json.gz')
                record = json.loads(gzip.decompress(checkpoint.read_bytes()))
                runtime.validate_checkpoint(record, record['source_sha256'], record['fingerprint'], 0, 16)
                reviewed.append((tuple(row), sum(c[0] == str(cfg.binary) for c in calls)))

    errors = []

    def review_checked():
        try:
            review()
        except Exception as exc:
            errors.append(str(exc))

    reviewer = threading.Thread(target=review_checked)

    def run(cmd, **kwargs):
        if cmd[0] == str(cfg.binary):
            assert len(kwargs['pass_fds']) == 1
            if not reviewer.ident:
                reviewer.start()
                with (locks / 'acoustic-review.turn').open('rb+') as request:
                    deadline = time.monotonic() + 2
                    while True:
                        try:
                            fcntl.flock(request, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        except BlockingIOError:
                            break
                        fcntl.flock(request, fcntl.LOCK_UN)
                        assert time.monotonic() < deadline
                        time.sleep(.01)
            result = base(cmd, **kwargs)
            Path(cmd[cmd.index('-of') + 1] + '.json').write_text(json.dumps({
                'transcription': [{'offsets': {'from': 0, 'to': 16000}, 'text': 'fala técnica'}]}))
            return result
        return base(cmd, **kwargs)

    primary = Worker(cfg, store, runner=run, gate_fn=lambda: {'allowed': True}, free_bytes=lambda: 20*1024**3)
    with runtime.transcription_turn(locks) as turn:
        assert turn
        primary.decoder_turn = turn
        primary.run_once(lesson['lesson_id'])
    reviewer.join(4)
    assert not reviewer.is_alive()
    assert not errors
    assert reviewed == [(('leased', primary.owner, 16/30), 1)]
    assert sum(c[0] == str(cfg.binary) for c in calls) == 2


def test_identical_video_bytes_reuse_asr_but_retain_lesson_identity(tmp_path):
    from fo_hub.transcription import TranscriptionQueue
    store, lesson, cfg = ready(tmp_path)
    calls = []
    worker = Worker(cfg, store, runner=fake_runner(cfg, calls), gate_fn=lambda: {'allowed': True}, free_bytes=lambda: 20*1024**3)
    assert worker.run_once()['state'] == 'validated'
    store.sync_lessons([{'course_id':'other', 'media_id':'same', 'title':'Outra aula', 'duration_s':30}])
    other = next(l for l in store.list_lessons() if l['lesson_id'] != lesson['lesson_id'])
    TranscriptionQueue(store).enqueue(other['lesson_id'], 1)
    with store.conn:
        store.conn.execute('insert into lesson_video_sources values(?,?,?,?,?,?)',
                           (other['lesson_id'], 'onedrive:Federal Online/b.mp4', '1', 9, 1, 'now'))
    assert worker.run_once()['state'] == 'validated'
    assert sum(c[0] == str(cfg.binary) for c in calls) == 1
    assert store.get_transcript(other['lesson_id'])['lesson_id'] == other['lesson_id']
    assert sum(c[0] == 'rclone' for c in calls) == 2  # hash, never size/title, proves identity


def test_explicit_pilot_id_cannot_consume_another_lesson(tmp_path):
    store, lesson, cfg = ready(tmp_path)
    worker = Worker(cfg, store, gate_fn=lambda: {'allowed': True})
    assert worker.run_once(lesson_id='fo_not_in_queue')['state'] == 'idle'
    assert store.conn.execute('select attempts from transcription_jobs').fetchone()[0] == 0


def test_measured_silent_tail_is_not_an_ambiguous_missing_transcript(tmp_path):
    store, lesson, cfg = ready(tmp_path)
    calls = []
    base = fake_runner(cfg, calls)
    def run(cmd, **kwargs):
        result = base(cmd, **kwargs)
        if cmd[0] == str(cfg.binary):
            Path(cmd[cmd.index('-of')+1]+'.json').write_text(json.dumps({'transcription':[
                {'offsets':{'from':0,'to':2000},'text':'A célula tem núcleo.'}]}))
        if cmd[0] == 'ffmpeg' and cmd[-1] == '-':
            result.stderr = 'silence_start: 2\nsilence_end: 30'
        return result
    worker = Worker(cfg, store, runner=run, gate_fn=lambda:{'allowed':True}, free_bytes=lambda:20*1024**3)
    assert worker.run_once()['state'] == 'validated'
    private = json.loads(gzip.decompress((tmp_path/'transcripts/private'/lesson['lesson_id']/'v1.json.gz').read_bytes()))
    assert private['qa']['observations'][0]['kind'] == 'measured_silence_gap'


def test_persistent_disk_pressure_does_not_exhaust_job_attempts(tmp_path):
    store, _, cfg = ready(tmp_path)
    worker = Worker(cfg, store, gate_fn=lambda:{'allowed':True}, free_bytes=lambda:1)
    for _ in range(5):
        assert worker.run_once()['state'] == 'paused_storage'
    assert store.conn.execute('select attempts from transcription_jobs').fetchone()[0] == 0


def test_run_refuses_preflight_failure_before_leasing(tmp_path, monkeypatch, capsys):
    from fo_hub import worker
    store, _, cfg = ready(tmp_path)
    monkeypatch.setattr(worker.Config, 'from_env', lambda:cfg)
    monkeypatch.setattr(worker, 'gate', lambda c:{'allowed':True})
    monkeypatch.setattr(worker, 'preflight', lambda c:{'ready':False,'problems':['synthetic missing dependency']})
    monkeypatch.setattr(worker.Worker, 'run_once', lambda *a,**kw:pytest.fail('failed preflight reached execution'))
    assert worker.main(['--run','--once']) == 3
    assert store.conn.execute('select attempts from transcription_jobs').fetchone()[0] == 0


def test_raw_evidence_is_losslessly_compressed_and_not_public(tmp_path):
    import gzip
    store, lesson, cfg = ready(tmp_path)
    worker = Worker(cfg, store, runner=fake_runner(cfg, []), gate_fn=lambda:{'allowed':True}, free_bytes=lambda:20*1024**3)
    assert worker.run_once()['state'] == 'validated'
    private = tmp_path/'transcripts/private'/lesson['lesson_id']/'v1.json.gz'
    payload = json.loads(gzip.decompress(private.read_bytes()))
    assert payload['chunks'][0]['raw']['transcription'][0]['text'] == 'Conteúdo científico legítimo.'
    checkpoint = next((tmp_path/'transcripts/evidence').rglob('0.000-30.000.json.gz'))
    assert json.loads(gzip.decompress(checkpoint.read_bytes()))['raw'] == payload['chunks'][0]['raw']
