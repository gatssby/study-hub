"""MVP partial availability; synthetic catalog fixtures, no network."""
import json
from datetime import datetime, timedelta, timezone

import pytest
from test_catalog_partial import C26, collector, entry, runtime
from test_dynamic_runtime import C27, ns


def read_registry(root):
    return json.loads(runtime.Paths(root).courses_json.read_text())


def test_isolated_empty_is_persisted_warning_and_not_immediate_retry(tmp_path):
    calls = []
    def collect(course, cp, resume):
        calls.append(course['url'])
        return [] if course['url'] == C26['url'] else [entry(course, 'ok', 'one')]
    args = ns(tmp_path, 'catalog')
    assert runtime.catalog(args, discover=lambda: [C26, C27], collect=collect, log=lambda _: None) == 0
    reg = read_registry(tmp_path)
    warning = next(c for c in reg['courses'] if c['url'] == C26['url'])
    assert warning['status'] == 'incomplete'
    assert warning['warning']['code'] == 'empty_unverified'
    assert warning['last_summary']['empty_verified'] is False
    assert 'last_ok_at' not in warning
    assert reg['last_attempt']['status'] == 'partial'
    calls.clear()
    assert runtime.catalog(args, discover=lambda: [C26, C27], collect=collect, log=lambda _: None) == 0
    assert calls == []
    persisted = next(c for c in read_registry(tmp_path)['courses'] if c['url'] == C26['url'])
    assert persisted['warning'] == warning['warning']
    assert read_registry(tmp_path)['last_attempt']['status'] == 'partial'
    assert not runtime.courses_due(reg, 'incremental', datetime.now(timezone.utc))
    assert len(runtime.courses_due(reg, 'incremental', datetime.now(timezone.utc) + timedelta(hours=7))) == 2
    # Directed operator smoke/recovery deliberately bypasses the warning cooldown.
    assert runtime.courses_due(reg, 'incremental', datetime.now(timezone.utc), '2026') == [warning]


def test_partial_success_recovers_warning_without_rewriting_identity(tmp_path):
    def collect(course, cp, resume):
        if course['url'] == C26['url']:
            return collector.CollectedEntries([], traversal_errors=[{'phase': 'expand_card'}])
        return [entry(course, 'ok', 'one')]
    assert runtime.catalog(ns(tmp_path, 'catalog'), discover=lambda: [C26, C27], collect=collect, log=lambda _: None) == 0
    before = next(c for c in read_registry(tmp_path)['courses'] if c['url'] == C26['url'])
    assert before['warning']['code'] == 'incomplete_traversal'
    assert runtime.catalog(ns(tmp_path, 'catalog', course_filter='2026'), discover=lambda: [C26, C27],
                           collect=lambda c, *a: [entry(c, 'ok', 'one')], log=lambda _: None) == 0
    after = next(c for c in read_registry(tmp_path)['courses'] if c['url'] == C26['url'])
    assert (after['course_id'], after['url'], after['first_seen']) == (before['course_id'], before['url'], before['first_seen'])
    assert after['warning'] is None and after['status'] == 'ok'


@pytest.mark.parametrize('error', [RuntimeError('Login expired'), OSError('disk full'), ValueError('corrupt state')])
def test_systemic_or_unknown_errors_still_fail_with_other_success(tmp_path, error):
    def collect(course, *a):
        if course['url'] == C26['url']:
            raise error
        return [entry(course, 'ok', 'one')]
    assert runtime.catalog(ns(tmp_path, 'catalog'), discover=lambda: [C26, C27], collect=collect, log=lambda _: None) == 1


def test_generalized_incompleteness_still_fails(tmp_path):
    assert runtime.catalog(ns(tmp_path, 'catalog'), discover=lambda: [C26, C27],
                           collect=lambda *a: [], log=lambda _: None) == 1
    assert read_registry(tmp_path)['last_attempt']['status'] == 'failed'
    # Backoff must not turn a generalized outage green on a no-op invocation.
    assert runtime.catalog(ns(tmp_path, 'catalog'), discover=lambda: [C26, C27],
                           collect=lambda *a: pytest.fail('cooldown ignored'), log=lambda _: None) == 1


@pytest.mark.parametrize('status', [403, 404, 410])
def test_unavailable_course_is_warning_and_preserves_published_bytes(tmp_path, status):
    course = {**C26, 'course_id': runtime.course_id_for(C26['url'])}
    paths = runtime.Paths(tmp_path)
    runtime.run_catalog_course(course, paths, lambda *a: [entry(course, 'ok', 'old')], 'incremental')
    artifact = paths.course_dir(course['course_id']) / 'aulas_index.json'
    before = artifact.read_bytes()
    def collect(c, *a):
        if c['url'] == C26['url']:
            raise collector.CourseUnavailable(status)
        return [entry(c, 'ok', 'one')]
    assert runtime.catalog(ns(tmp_path, 'catalog'), discover=lambda: [C26, C27], collect=collect, log=lambda _: None) == 0
    warning = next(c for c in read_registry(tmp_path)['courses'] if c['url'] == C26['url'])
    assert warning['status'] == 'incomplete' and warning['warning']['code'] == 'course_unavailable'
    assert artifact.read_bytes() == before


@pytest.mark.parametrize('name', ['courses.json', 'aulas_index.json', 'checkpoint.json'])
def test_corruption_never_replaced_with_partial_success(tmp_path, name):
    paths = runtime.Paths(tmp_path)
    course = {**C26, 'course_id': runtime.course_id_for(C26['url'])}
    target = paths.courses_json if name == 'courses.json' else paths.course_dir(course['course_id']) / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('{broken')
    def run():
        return runtime.catalog(ns(tmp_path, 'catalog'), discover=lambda: [C26, C27],
                               collect=lambda c, *a: [entry(c, 'ok', 'one')], log=lambda _: None)
    try:
        assert run() == 1
    except ValueError:
        pass
    assert target.read_text() == '{broken'


@pytest.mark.parametrize('name,key', [('courses.json', 'courses'), ('aulas_index.json', 'aulas')])
def test_valid_json_with_invalid_catalog_shape_is_not_reset(tmp_path, name, key):
    paths = runtime.Paths(tmp_path)
    course = {**C26, 'course_id': runtime.course_id_for(C26['url'])}
    target = paths.courses_json if name == 'courses.json' else paths.course_dir(course['course_id']) / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({key: 'not rows'}))
    before = target.read_bytes()
    try:
        assert runtime.catalog(ns(tmp_path, 'catalog'), discover=lambda: [C26, C27],
                               collect=lambda c, *a: [entry(c, 'ok', 'one')], log=lambda _: None) == 1
    except (ValueError, TypeError):
        pass
    assert target.read_bytes() == before


def test_fatal_item_error_after_warning_is_not_suppressed_by_old_cooldown(tmp_path):
    runtime.catalog(ns(tmp_path, 'catalog'), discover=lambda: [C26, C27],
                    collect=lambda c, *a: [] if c['url'] == C26['url'] else [entry(c, 'ok', 'one')], log=lambda _: None)
    assert runtime.catalog(ns(tmp_path, 'catalog', course_filter='2026'), discover=lambda: [C26, C27],
                           collect=lambda c, *a: [entry(c, 'error', 'bad')], log=lambda _: None) == 1
    failed = next(c for c in read_registry(tmp_path)['courses'] if c['url'] == C26['url'])
    assert failed['warning'] is None
    assert runtime.courses_due({'courses': [failed]}, 'incremental', datetime.now(timezone.utc)) == [failed]


@pytest.mark.parametrize('status,login,expected', [
    (403, False, collector.CourseUnavailable), (404, False, collector.CourseUnavailable),
    (410, False, collector.CourseUnavailable), (401, False, RuntimeError),
    (503, False, RuntimeError), (404, True, RuntimeError),
])
def test_navigation_classifies_only_explicit_non_login_course_unavailability(monkeypatch, status, login, expected):
    from types import SimpleNamespace
    navigations = []
    page = SimpleNamespace(goto=lambda *a, **k: navigations.append(True) or SimpleNamespace(status=status))
    config = SimpleNamespace(course_url=C26['url'], nav_timeout_ms=10, email=None, password=None)
    monkeypatch.setattr(collector, 'page_requires_login', lambda p: login)
    with pytest.raises(expected) as exc:
        collector.open_course_page_for_collection(page, config, runtime._Log(lambda _: None), 'test')
    assert isinstance(exc.value, collector.CourseUnavailable) == (not login and status in (403, 404, 410))
    assert len(navigations) == 1


def test_verified_native_empty_is_informational_warning_not_incomplete(tmp_path):
    proof = {'verified_no_native_video': True, 'scope': 'native_portal_video_items_only'}
    assert runtime.catalog(ns(tmp_path, 'catalog'), discover=lambda: [C26],
                           collect=lambda *a: collector.CollectedEntries([], empty_evidence=proof), log=lambda _: None) == 0
    course = read_registry(tmp_path)['courses'][0]
    assert course['status'] == 'ok' and course['last_summary']['empty_verified'] is True
    assert course['warning']['code'] == 'empty_verified'
    assert course['warning']['severity'] == 'info'


def test_new_forbidden_response_cannot_use_cached_peer_as_auth_proof(tmp_path):
    args = ns(tmp_path, 'catalog')
    runtime.catalog(args, discover=lambda: [C26, C27],
                    collect=lambda c, *a: [entry(c, 'ok', 'one')], log=lambda _: None)
    args.course_filter = '2026'
    args.mode = 'weekly'
    def forbidden(*a):
        raise collector.CourseUnavailable(403)
    assert runtime.catalog(args, discover=lambda: [C26, C27], collect=forbidden, log=lambda _: None) == 1
    args.mode = 'incremental'
    args.course_filter = ''
    assert runtime.catalog(args, discover=lambda: [C26, C27],
                           collect=lambda *a: pytest.fail('cooldown ignored'), log=lambda _: None) == 1


def test_majority_unavailable_fails_despite_one_accessible_course(tmp_path):
    third = {**C27, 'url': C27['url'] + '-third'}
    assert runtime.catalog(ns(tmp_path, 'catalog'), discover=lambda: [C26, C27, third],
                           collect=lambda c, *a: [entry(c, 'ok', 'one')] if c['url'] == third['url'] else [],
                           log=lambda _: None) == 1
