from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'portal'))
import runtime  # noqa: E402
import fo_collect_aulas_index as collector  # noqa: E402


@dataclass
class Config:
    course_url: str = ''
    storage_state_file: Path | None = None


def session_fixture(monkeypatch, tmp_path, total, *, seed=0, limit=None, fail_second=False, errors=None):
    session = runtime.BrowserSession.__new__(runtime.BrowserSession)
    session.base_config = Config()
    session.paths = SimpleNamespace(storage_state=tmp_path / 'session.json')
    session.args = SimpleNamespace(limit=limit)
    session.logger = SimpleNamespace(log=lambda _: None)
    session._save_session = lambda: None
    durable = [{'media_id': str(i)} for i in range(seed)]
    calls = []

    def load(*args, **kwargs):
        return (list(durable) if kwargs['resume_enabled'] else []), set()

    def collect(args, config, logger, checkpoint):
        calls.append((args.limit, args.no_resume))
        if fail_second and len(calls) == 2:
            raise RuntimeError('synthetic browser failure after durable batch')
        if args.no_resume:
            durable.clear()
        target = total if args.limit is None else min(total, args.limit)
        durable.extend({'media_id': str(i)} for i in range(len(durable), target))
        return collector.CollectedEntries(list(durable), traversal_errors=errors(len(calls)) if errors else ['unresolved branch'])

    monkeypatch.setattr(collector, 'load_checkpoint', load)
    monkeypatch.setattr(collector, 'collect_index', collect)
    return session, calls, durable


@pytest.mark.parametrize('total, limits', [(450, [200, 400, 600]), (400, [200, 400, 600]), (0, [200])])
def test_unlimited_course_recycles_browser_after_bounded_new_progress(monkeypatch, tmp_path, total, limits):
    session, calls, durable = session_fixture(monkeypatch, tmp_path, total)
    result = session.collect_course({'url': 'https://portal.invalid/course'}, tmp_path / 'checkpoint.json', True)
    assert calls == [(n, False) for n in limits]
    assert len(result) == len(durable) == total
    assert len({x['media_id'] for x in result}) == total
    assert result.traversal_errors == ['unresolved branch']


def test_browser_recycling_preserves_earlier_traversal_uncertainty(monkeypatch, tmp_path):
    session, calls, _ = session_fixture(monkeypatch, tmp_path, 220, errors=lambda n: ['earlier branch'] if n == 1 else [])
    result = session.collect_course({'url': 'https://portal.invalid/course'}, tmp_path / 'checkpoint.json', True)
    assert calls == [(200, False), (400, False)]
    assert result.traversal_errors == ['earlier branch']


def test_resume_budget_counts_only_new_progress_not_old_checkpoint(monkeypatch, tmp_path):
    session, calls, _ = session_fixture(monkeypatch, tmp_path, 1070, seed=1012)
    result = session.collect_course({'url': 'https://portal.invalid/course'}, tmp_path / 'checkpoint.json', True)
    assert calls == [(1212, False)]
    assert len(result) == 1070


def test_fresh_first_batch_resumes_its_own_checkpoint_after_rotation(monkeypatch, tmp_path):
    session, calls, _ = session_fixture(monkeypatch, tmp_path, 220, seed=1000)
    result = session.collect_course({'url': 'https://portal.invalid/course'}, tmp_path / 'checkpoint.json', False)
    assert calls == [(200, True), (400, False)]
    assert len(result) == 220


def test_explicit_caller_limit_is_not_reinterpreted_as_complete_course(monkeypatch, tmp_path):
    session, calls, _ = session_fixture(monkeypatch, tmp_path, 450, limit=7)
    result = session.collect_course({'url': 'https://portal.invalid/course'}, tmp_path / 'checkpoint.json', True)
    assert calls == [(7, False)]
    assert len(result) == 7


def test_failed_later_browser_batch_does_not_return_partial_success(monkeypatch, tmp_path):
    session, calls, durable = session_fixture(monkeypatch, tmp_path, 450, fail_second=True)
    with pytest.raises(RuntimeError, match='synthetic browser failure'):
        session.collect_course({'url': 'https://portal.invalid/course'}, tmp_path / 'checkpoint.json', True)
    assert len(durable) == 200
    assert calls == [(200, False), (400, False)]
