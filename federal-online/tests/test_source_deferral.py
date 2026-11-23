"""Known unavailable resources back off without stopping healthy work."""
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace



def assert_deferred(case, reason):
    result = case.worker.run_once()
    assert (result['state'], result['reason']) == ('queued', reason)
    row = case.store.conn.execute('SELECT state,attempts,last_error FROM transcription_jobs').fetchone()
    assert tuple(row) == ('queued', 0, reason)
    row = case.store.conn.execute('SELECT lesson_id,version,remote_path,size,reason,retry_after,observed_at '
                                  'FROM transcription_source_deferrals').fetchone()
    assert tuple(row)[:5] == (case.lesson_id, 1, 'onedrive:Federal Online/a.mp4', 9, reason)
    assert row['retry_after'] > row['observed_at']
    assert case.worker.run_once() == {'state': 'idle'}
    assert case.store.get_transcript(case.lesson_id) is None
    assert not list(case.worker.roots()[0].iterdir())


def test_missing_remote_object_is_deferred_without_attempt_exhaustion(mvp_case):
    calls = []

    def missing(cmd, **kwargs):
        calls.append(cmd)
        raise subprocess.CalledProcessError(4, cmd, stderr='object not found')

    case = mvp_case(runner=missing)
    assert_deferred(case, 'remote_object_not_found')
    assert [c[0] for c in calls] == ['rclone']
    status = case.store.sync_status()
    assert status['sources']['eligible'] == 0
    assert status['transcription_deferrals'] == {'total': 1, 'by_reason': {'remote_object_not_found': 1}}
    # A newly observed exact source identity is immediately eligible, not hidden by old backoff.
    with case.store.conn:
        case.store.conn.execute("UPDATE lesson_video_sources SET remote_path='onedrive:Federal Online/new.mp4'")
    job = case.queue.lease('remap-check')
    assert (job['lesson_id'], job['remote_path']) == (case.lesson_id, 'onedrive:Federal Online/new.mp4')


def test_authentication_error_remains_real_failure_not_unavailability(mvp_case):
    def denied(cmd, **kwargs):
        raise subprocess.CalledProcessError(4, cmd, stderr='401 Unauthorized: token expired')

    case = mvp_case(runner=denied)
    result = case.worker.run_once()
    assert (result['state'], result['reason']) == ('queued', 'source_authentication_failed')
    assert case.store.conn.execute('SELECT COUNT(*) FROM transcription_source_deferrals').fetchone()[0] == 0
    assert case.store.get_transcript(case.lesson_id) is None
    assert case.store.conn.execute('SELECT attempts FROM transcription_jobs').fetchone()[0] == 1


def test_short_transfer_is_isolated_and_not_retried_in_same_cycle(mvp_case):
    calls = []

    def short(cmd, **kwargs):
        calls.append(cmd)
        Path(cmd[3]).write_bytes(b'x')
        return SimpleNamespace(stdout='', stderr='')

    case = mvp_case(runner=short)
    assert_deferred(case, 'source_download_size_mismatch')
    assert len(calls) == 1
    assert calls[0][4:6] == ['--retries', '1']


def test_rclone_rejected_transfer_is_isolated(mvp_case):
    def corrupt(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd, stderr='Failed to copy: corrupted on transfer: sizes differ src(OneDrive root) 9 vs dst(Local file system) 585')

    assert_deferred(mvp_case(runner=corrupt), 'source_download_size_mismatch')


def test_incompatible_duration_is_deferred_before_decoder_and_recoverable(mvp_case):
    calls = []

    def run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[:2] == ['rclone', 'copyto']:
            Path(cmd[3]).write_bytes(b'fakevideo')
        elif cmd[:2] == ['rclone', 'hashsum']:
            return SimpleNamespace(stdout=f'{case.source_quickxor}  {Path(cmd[3]).name}\n', stderr='')
        elif cmd[0] == 'ffprobe':
            return SimpleNamespace(stdout=json.dumps({'streams': [{'index': 0}],
                                                       'format': {'duration': '10'}}), stderr='')
        else:
            raise AssertionError('must not decode an incompatible source')
        return SimpleNamespace(stdout='', stderr='')

    case = mvp_case(runner=run)
    assert_deferred(case, 'source_duration_mismatch')
    assert [c[0] for c in calls] == ['rclone', 'rclone', 'ffprobe']
    retry_after = case.store.conn.execute('SELECT retry_after FROM transcription_source_deferrals').fetchone()[0]
    assert case.queue.lease('after-backoff', now=retry_after + 1)['lesson_id'] == case.lesson_id
