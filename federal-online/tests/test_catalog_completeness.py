"""False completeness must not publish a successful course timestamp."""
import json
import pytest
from test_catalog_partial import C26, collector, entry, runtime
from test_dynamic_runtime import ns


@pytest.mark.parametrize('limited', [False, True])
def test_empty_or_limited_catalog_does_not_claim_complete(tmp_path, limited):
    args = ns(tmp_path, 'catalog')
    args.limit = 1 if limited else None
    cid = runtime.course_id_for(C26['url'])
    paths = runtime.Paths(tmp_path)
    paths.catalog.mkdir()
    old = '2026-10-01T00:00:00+00:00'
    paths.courses_json.write_text(json.dumps({'courses': [{**C26, 'course_id': cid, 'status': 'error', 'last_ok_at': old}]}))
    def collect(course, checkpoint, resume):
        rows = [entry(course, 'ok', 'one')] if limited else []
        collector.write_checkpoint(checkpoint, course_url=course['url'], path_filters=[], entries=rows,
                                   seen_keys=set(), logger=runtime._Log(lambda _: None))
        return rows
    assert runtime.catalog(args, discover=lambda: [C26], collect=collect, log=lambda _: None) == 1
    course = json.loads(paths.courses_json.read_text())['courses'][0]
    assert course['status'] == 'incomplete'
    assert course['last_ok_at'] == old
    assert (paths.course_dir(cid) / 'checkpoint.json').exists()


def test_empty_observation_preserves_nonempty_publication(tmp_path):
    paths = runtime.Paths(tmp_path)
    course = {**C26, 'course_id': runtime.course_id_for(C26['url'])}
    runtime.run_catalog_course(course, paths, lambda *a: [entry(course, 'ok', 'one')], 'incremental')
    out = paths.course_dir(course['course_id']) / 'aulas_index.json'
    before = out.read_bytes()
    summary = runtime.run_catalog_course(course, paths, lambda *a: [], 'incremental')
    assert summary['total'] == 0
    assert out.read_bytes() == before


def test_auth_expired_discovery_does_not_mutate_registry(tmp_path):
    paths = runtime.Paths(tmp_path)
    paths.catalog.mkdir()
    paths.courses_json.write_text(json.dumps({'courses': [{**C26, 'course_id': runtime.course_id_for(C26['url']), 'status':'ok'}]}))
    before = paths.courses_json.read_bytes()
    def expired():
        raise RuntimeError('Login expired during course discovery; registry unchanged')
    with pytest.raises(RuntimeError, match='Login expired'):
        runtime.catalog(ns(tmp_path, 'catalog'), discover=expired, collect=lambda *a: [], log=lambda _: None)
    assert paths.courses_json.read_bytes() == before


def test_auth_expired_course_does_not_advance_last_ok_or_remove_checkpoint(tmp_path):
    paths = runtime.Paths(tmp_path)
    course = {**C26, 'course_id': runtime.course_id_for(C26['url'])}
    cp = paths.course_dir(course['course_id']) / 'checkpoint.json'
    cp.parent.mkdir(parents=True)
    cp.write_text('durable synthetic checkpoint')
    old = '2026-10-01T00:00:00+00:00'
    paths.courses_json.write_text(json.dumps({'courses': [{**course, 'status':'error', 'last_ok_at':old}]}))
    def expired(*args):
        raise RuntimeError('Login expired')
    assert runtime.catalog(ns(tmp_path, 'catalog'), discover=lambda: [C26], collect=expired, log=lambda _:None) == 1
    after = json.loads(paths.courses_json.read_text())['courses'][0]
    assert after['status'] == 'error' and after['last_ok_at'] == old
    assert cp.read_text() == 'durable synthetic checkpoint'

