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


def test_empty_native_catalog_needs_structural_evidence(tmp_path):
    args = ns(tmp_path, 'catalog')
    proof = {'verified_no_native_video': True, 'media_type_counts': {'D': 4, 'U': 5, 'A': 2},
             'unknown_items': 0, 'scope': 'native_portal_video_items_only'}
    result = collector.CollectedEntries([], empty_evidence=proof)
    assert runtime.catalog(args, discover=lambda: [C26], collect=lambda *a: result, log=lambda _: None) == 0
    course = json.loads(runtime.Paths(tmp_path).courses_json.read_text())['courses'][0]
    assert course['status'] == 'ok'
    assert course['last_summary']['empty_verified'] is True


def test_skipped_branch_cannot_claim_full_course_success(tmp_path):
    args = ns(tmp_path, 'catalog')
    rows = collector.CollectedEntries([entry(C26, 'ok', 'one')],
                                      traversal_errors=[{'phase':'expand_card','error_type':'TimeoutError'}])
    assert runtime.catalog(args, discover=lambda: [C26], collect=lambda *a: rows, log=lambda _: None) == 1
    course = json.loads(runtime.Paths(tmp_path).courses_json.read_text())['courses'][0]
    assert course['status'] == 'incomplete'
    assert 'last_ok_at' not in course
    assert course['last_summary']['traversal_errors'] == 1


@pytest.mark.parametrize('failure', ['limited', 'traversal', 'item_error'])
def test_nonempty_partial_preserves_known_good_entries_without_faking_observation(tmp_path, failure):
    paths = runtime.Paths(tmp_path)
    course = {**C26, 'course_id': runtime.course_id_for(C26['url'])}
    old = [entry(course, 'ok', item) for item in ('one', 'two')]
    for row in old:
        row['video_stream_url'] = 'https://example.test/' + row['item_id'] + '.m3u8'
    runtime.run_catalog_course(course, paths, lambda *a: old, 'incremental')
    current = entry(course, 'error' if failure == 'item_error' else 'ok', 'one')
    if failure != 'item_error': current['video_stream_url'] = old[0]['video_stream_url']
    rows = collector.CollectedEntries([current], traversal_errors=[{'phase':'expand_card'}] if failure == 'traversal' else [])
    summary = runtime.run_catalog_course(course, paths, lambda *a: rows, 'incremental', limited=failure == 'limited')
    payload = json.loads((paths.course_dir(course['course_id'])/'aulas_index.json').read_text())
    assert summary['total'] == 1
    assert summary['retained_previous'] == (2 if failure == 'item_error' else 1)
    assert summary['status_counts'].get('error', 0) == int(failure == 'item_error')
    by_item = {r['item_id']:r for r in payload['aulas']}
    assert set(by_item) == {'one','two'}
    assert by_item['two']['catalog_observation'] == 'retained_previous_not_observed'
    assert by_item['two']['video_stream_url'] == old[1]['video_stream_url']
    if failure == 'item_error':
        assert by_item['one']['video_stream_url'] == old[0]['video_stream_url']
        assert payload['collection_evidence']['pending_errors'][0]['item_id'] == 'one'
    # A later complete observation is authoritative for the published artifact,
    # not an ever-growing union; historical rows remain in the SQLite store.
    runtime.run_catalog_course(course, paths, lambda *a: [old[0]], 'incremental')
    assert len(json.loads((paths.course_dir(course['course_id'])/'aulas_index.json').read_text())['aulas']) == 1


def test_empty_live_collection_with_checkpoint_errors_cannot_replace_good_catalog(tmp_path):
    paths = runtime.Paths(tmp_path)
    course = {**C26, 'course_id':runtime.course_id_for(C26['url'])}
    runtime.run_catalog_course(course, paths, lambda *a:[entry(course,'ok',item) for item in ('one','two')], 'incremental')
    cp = paths.course_dir(course['course_id'])/'checkpoint.json'
    collector.write_checkpoint(cp, course_url=course['url'], path_filters=[], entries=[entry(course,'error','one')],
                               seen_keys=set(), logger=runtime._Log(lambda _:None))
    before = cp.read_bytes()
    summary = runtime.run_catalog_course(course, paths, lambda *a:[], 'incremental')
    published = json.loads((cp.parent/'aulas_index.json').read_text())
    assert summary['status_counts'] == {'error':1}
    assert {row['item_id'] for row in published['aulas']} == {'one','two'}
    assert all(row['catalog_observation'] == 'retained_previous_not_observed' for row in published['aulas'])
    assert cp.read_bytes() == before

