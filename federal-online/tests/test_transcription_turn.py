import fcntl
from types import SimpleNamespace

import pytest

from fo_hub import acoustic_review, worker


def test_worker_keeps_lock_through_job_and_review_but_releases_before_sleep(tmp_path, monkeypatch):
    cfg = SimpleNamespace(state=tmp_path)
    monkeypatch.setattr(worker.Config, 'from_env', lambda: cfg)
    monkeypatch.setattr(worker, 'gate', lambda cfg: {'allowed': True})
    monkeypatch.setattr(worker, 'preflight', lambda cfg: {'ready': True})
    seen = []

    def owns_lock(step):
        with pytest.raises(acoustic_review.Blocked, match='whisper_owns_transcription_lock'):
            with acoustic_review.whisper_lock(cfg):
                pytest.fail('review overlapped the worker')
        seen.append(step)

    class Worker:
        def __init__(self, cfg):
            pass

        def recover(self):
            owns_lock('recover')

        def review_pass(self):
            owns_lock('review_pass')
            return {'processed': 0}

        def run_once(self, lesson_id):
            if 'sleep' in seen:
                return {'state': 'breaker_open'}
            owns_lock('job')
            return {'state': 'idle'}

    def sleep(_):
        with acoustic_review.whisper_lock(cfg):
            seen.append('sleep')

    monkeypatch.setattr(worker, 'Worker', Worker)
    monkeypatch.setattr(worker.time, 'sleep', sleep)
    assert worker.main(['--run', '--loop']) == 5
    assert seen == ['recover', 'review_pass', 'job', 'review_pass', 'sleep']


def test_waiting_reviewer_gets_next_boundary_without_claiming_any_lease(tmp_path, monkeypatch):
    cfg = SimpleNamespace(state=tmp_path)
    locks = tmp_path / 'locks'
    locks.mkdir()
    path = locks / 'transcription.lock'
    with worker.transcription_turn(locks) as admitted:
        assert admitted
    with path.open('a+') as original:
        fcntl.flock(original, fcntl.LOCK_EX | fcntl.LOCK_NB)
        seen = []

        def idle(_):
            # The reviewer already holds the request lock, but cannot begin
            # work until the old job naturally gives up the decoder lock.
            with worker.transcription_turn(locks) as admitted:
                assert not admitted
            fcntl.flock(original, fcntl.LOCK_UN)
            seen.append('waited')

        monkeypatch.setattr(acoustic_review.time, 'sleep', idle)
        with acoustic_review.whisper_lock(cfg, wait=2):
            with worker.transcription_turn(locks) as admitted:
                assert not admitted
            seen.append('reviewing')
    with worker.transcription_turn(locks) as admitted:
        assert admitted
    assert seen == ['waited', 'reviewing']


def test_timed_out_request_releases_its_turn(tmp_path, monkeypatch):
    cfg = SimpleNamespace(state=tmp_path)
    locks = tmp_path / 'locks'
    locks.mkdir()
    ticks = iter([0, 2])
    monkeypatch.setattr(acoustic_review.time, 'monotonic', lambda: next(ticks))
    with worker.transcription_turn(locks) as admitted:
        assert admitted
        with pytest.raises(acoustic_review.Blocked, match='whisper_owns_transcription_lock'):
            with acoustic_review.whisper_lock(cfg, wait=1):
                pytest.fail('review overlapped the worker')
        with (locks / 'acoustic-review.turn').open('a+') as request:
            fcntl.flock(request, fcntl.LOCK_EX | fcntl.LOCK_NB)
