"""Known unavailable resources back off without stopping healthy work."""
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fo_hub.worker import Worker
from test_worker import setup


def worker_with_source(tmp_path, runner):
    store, lesson, cfg = setup(tmp_path)
    worker = Worker(cfg, store=store, runner=runner, gate_fn=lambda: {'allowed': True},
                    free_bytes=lambda: 20*1024**3)
    store.conn.execute('INSERT INTO lesson_video_sources VALUES(?,?,?,?,?,?)',
                       (lesson['lesson_id'], 'onedrive:Federal Online/a.mp4', '1', 9, 1, 'now'))
    store.conn.commit()
    return worker, store, lesson


def test_missing_remote_object_is_deferred_without_attempt_exhaustion_or_breaker(tmp_path):
    calls = []
    def missing(cmd, **kwargs):
        calls.append(cmd)
        raise subprocess.CalledProcessError(4, cmd, stderr='object not found')
    worker, store, lesson = worker_with_source(tmp_path, missing)
    assert worker.run_once()['state'] == 'deferred_source'
    row = store.conn.execute('SELECT state,attempts,last_error FROM transcription_jobs').fetchone()
    assert tuple(row) == ('queued', 0, 'remote_object_not_found')
    assert store.conn.execute('SELECT reason FROM transcription_source_deferrals').fetchone()[0] == 'remote_object_not_found'
    assert worker.run_once()['state'] == 'idle'
    assert len(calls) == 1
    from fo_hub.worker import worker_status
    assert worker_status(worker.cfg)['next_discipline'] is None
    status=store.sync_status()
    assert status['sources']['eligible']==0
    assert status['transcription_deferrals']=={'total':1,'by_reason':{'remote_object_not_found':1}}
    assert store.conn.execute('SELECT COUNT(*) FROM transcription_breaker WHERE opened_at IS NOT NULL').fetchone()[0] == 0
    # A newly observed source identity is immediately eligible, not hidden by the old backoff.
    store.conn.execute("UPDATE lesson_video_sources SET remote_path='onedrive:Federal Online/new.mp4'")
    store.conn.commit()
    assert worker.lease()['lesson_id'] == lesson['lesson_id']


def test_authentication_error_remains_real_failure_not_unavailability(tmp_path):
    def denied(cmd, **kwargs):
        raise subprocess.CalledProcessError(4, cmd, stderr='401 Unauthorized: token expired')
    worker, store, lesson = worker_with_source(tmp_path, denied)
    assert worker.run_once()['state'] == 'retry'
    assert store.conn.execute('SELECT attempts FROM transcription_jobs').fetchone()[0] == 1
    assert store.conn.execute('SELECT COUNT(*) FROM transcription_source_deferrals').fetchone()[0] == 0
    assert store.conn.execute('SELECT consecutive_failures FROM transcription_breaker').fetchone()[0] == 1


def test_incompatible_duration_is_deferred_before_decoder_and_recoverable(tmp_path):
    calls = []
    def run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[0] == 'rclone':
            Path(cmd[3]).write_bytes(b'fakevideo')
        elif cmd[0] == 'ffprobe':
            return SimpleNamespace(stdout=json.dumps({'format': {'duration': '10'}}), stderr='')
        else:
            raise AssertionError('must not decode an incompatible source')
        return SimpleNamespace(stdout='', stderr='')
    worker, store, lesson = worker_with_source(tmp_path, run)
    assert worker.run_once()['state'] == 'deferred_source'
    assert store.conn.execute('SELECT reason FROM transcription_source_deferrals').fetchone()[0] == 'source_duration_mismatch'
    assert worker.run_once()['state'] == 'idle'
    assert not list((tmp_path/'tmp/transcription').glob('*'))
