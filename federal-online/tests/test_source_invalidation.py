"""Remote metadata invalidation uses fixture files and SQLite only."""
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fo_hub.ingest import ingest, canonical
from fo_hub.store import FOStore


@pytest.fixture
def source(tmp_path):
    state = tmp_path / 'state'
    (state / 'catalog').mkdir(parents=True)
    aula = {'media_id': '42', 'course_url': 'https://portal/produto-pacote/course/2027',
            'video_stream_url': 'https://cdn/video', 'duracao_segundos': 100, 'status': 'ok'}
    remote = {'Path': 'Course/Aula.mp4', 'ID': 'id1', 'Size': 99, 'ModTime': '2026-01-01T00:00:00Z'}
    db = tmp_path / 'hub.sqlite3'

    def run():
        (state / 'catalog/aulas_index.json').write_text(json.dumps({'aulas': [aula]}))
        (state / 'catalog/video_upload_manifest.json').write_text(json.dumps({'items': [{
            'video_stream_url': aula['video_stream_url'],
            'remote_path': 'onedrive:Federal Online/' + remote['Path']}]}))
        (state / 'remote-videos.json').write_text(json.dumps([remote]))
        return ingest(state, db, index_pdfs=False)

    return state, db, aula, remote, run


def verified(state, aula, remote):
    key = hashlib.sha256((canonical(aula['course_url']) + '|42').encode()).hexdigest()[:24]
    revision = hashlib.sha256(json.dumps([canonical(aula['video_stream_url']), aula['duracao_segundos']]).encode()).hexdigest()[:16]
    (state / 'videos.json').write_text(json.dumps({'items': {key: {
        'status': 'verified', 'revision': revision, 'size': 99,
        'remote_path': 'onedrive:Federal Online/' + remote['Path']}}}))


def test_verified_record_uses_matching_inventory_metadata(source):
    state, db, aula, remote, run = source
    verified(state, aula, remote)
    run()
    remote['ModTime'] = 'changed'
    run()
    assert FOStore(db).get_lesson(FOStore(db).list_lessons()[0]['lesson_id'])['version'] == 2


def test_disappeared_inventory_source_is_unavailable(source):
    state, db, _, _, run = source
    run()
    (state / 'remote-videos.json').write_text('[]')
    ingest(state, db, index_pdfs=False)
    assert FOStore(db).conn.execute('SELECT available FROM lesson_video_sources').fetchone()[0] == 0


@pytest.mark.parametrize('field', ['ModTime', 'ID'])
def test_remote_only_change_invalidates_same_lesson(source, field):
    state, db, _, remote, _ = source
    def run():
        (state / 'remote-videos.json').write_text(json.dumps([remote]))
        ingest(state, db, index_pdfs=False)
    run()
    remote[field] = 'changed'
    run()
    assert FOStore(db).conn.execute('SELECT version FROM lessons').fetchone()[0] == 2


@pytest.mark.parametrize('field,value', [('ID', 'id2'), ('Size', 101), ('ModTime', '2026-02-01T00:00:00Z')])
def test_known_remote_change_advances_version_once(source, field, value):
    _, db, _, remote, run = source
    run()
    remote[field] = value
    run()
    run()
    c = FOStore(db).conn
    assert c.execute('SELECT version FROM lessons').fetchone()[0] == 2
    assert [tuple(r) for r in c.execute('SELECT version,state FROM transcription_jobs ORDER BY version')] == [(1, 'superseded'), (2, 'queued')]
    assert tuple(c.execute('SELECT revision,available FROM lesson_video_sources').fetchone()) == ('2', 1)


def test_baseline_missing_modtime_does_not_erase_known_identity(source):
    _, db, _, remote, run = source
    run()
    original = remote.pop('ModTime')
    run()
    c = FOStore(db).conn
    assert c.execute('SELECT version FROM lessons').fetchone()[0] == 1
    metadata = json.loads(c.execute('SELECT metadata FROM lesson_source_observations').fetchone()[0])
    assert metadata['ModTime'] == original
    remote['ModTime'] = 'changed'
    run()
    assert c.execute('SELECT version FROM lessons').fetchone()[0] == 2


def test_catalog_revision_does_not_double_bump_and_preserves_active_lease(source):
    _, db, aula, remote, run = source
    run()
    c = FOStore(db).conn
    with c:
        c.execute("UPDATE transcription_jobs SET state='leased',lease_owner='worker',lease_until=9999999999")
    aula['duracao_segundos'] = 200
    remote['ModTime'] = 'changed'
    run()
    assert c.execute('SELECT version FROM lessons').fetchone()[0] == 2
    assert tuple(c.execute('SELECT state,lease_owner,lease_until FROM transcription_jobs WHERE version=1').fetchone()) == ('leased', 'worker', 9999999999)
    assert c.execute('SELECT state FROM transcription_jobs WHERE version=2').fetchone()[0] == 'queued'


def test_verified_upload_does_not_regress_to_stale_inventory(source):
    state, db, aula, remote, run = source
    verified(state, aula, remote)
    run()
    remote.update(Size=12, ID='stale', ModTime='stale')
    run()
    c = FOStore(db).conn
    assert tuple(c.execute('SELECT size,revision FROM lesson_video_sources').fetchone()) == (99, '1')
    metadata = json.loads(c.execute('SELECT metadata FROM lesson_source_observations').fetchone()[0])
    assert metadata['ID'] == 'id1'


@pytest.mark.parametrize('capture,proof,expected_version,expected_size', [
    (2000, True, 2, 101), (500, True, 1, 99), (2000, False, 1, 99),
    (float('nan'), True, 1, 99), ('2000', True, 1, 99), (True, True, 1, 99)])
def test_verified_upload_inventory_chronology(source, capture, proof, expected_version, expected_size):
    state, db, aula, remote, run = source
    verified(state, aula, remote)
    payload = json.loads((state / 'videos.json').read_text())
    next(iter(payload['items'].values()))['checked_at'] = 1000
    (state / 'videos.json').write_text(json.dumps(payload))
    run()
    store = FOStore(db)
    original = store.list_lessons()[0]
    store.sync_lessons([{**original, 'course_id': 'persisted-alias'}], authoritative=False)
    alias = next(x for x in store.list_lessons() if x['course_id'] == 'persisted-alias')
    with store.conn:
        store.conn.execute('INSERT INTO lesson_video_sources SELECT ?,remote_path,revision,size,available,checked_at '
                           'FROM lesson_video_sources WHERE lesson_id=?', (alias['lesson_id'], original['lesson_id']))
        store.conn.execute('INSERT INTO lesson_source_observations SELECT ?,remote_path,metadata,version,checked_at '
                           'FROM lesson_source_observations WHERE lesson_id=?', (alias['lesson_id'], original['lesson_id']))
    remote.update(Size=101, ID='replacement', ModTime='later')
    (state / 'remote-videos.json').write_text(json.dumps([remote]))
    os.utime(state / 'remote-videos.json', (3000, 3000))  # completion alone proves nothing
    (state / 'onedrive-status.json').write_text(json.dumps({
        'inventory_started_at': capture,
        'inventory_sha256': hashlib.sha256((state / 'remote-videos.json').read_bytes()).hexdigest() if proof else 'mismatch'}))
    ingest(state, db, index_pdfs=False)
    ingest(state, db, index_pdfs=False)
    c = FOStore(db).conn
    assert [r[0] for r in c.execute('SELECT version FROM lessons')] == [expected_version] * 2
    assert [r[0] for r in c.execute('SELECT size FROM lesson_video_sources')] == [expected_size] * 2
    assert c.execute('SELECT count(*) FROM lessons').fetchone()[0] == 2
    assert c.execute("SELECT count(*) FROM lesson_revisions WHERE change_kind='media_changed'").fetchone()[0] == 2 * (expected_version - 1)


@pytest.mark.parametrize('field,value', [('ID', 'id2'), ('Size', 101), ('ModTime', 'later')])
def test_persisted_catalog_aliases_are_observed_without_rediscovery(source, field, value):
    state, db, _, remote, run = source
    run()
    store = FOStore(db)
    original = store.list_lessons()[0]
    store.sync_lessons([{**original, 'course_id': 'other-course'}], authoritative=False)
    alias = next(x for x in store.list_lessons() if x['course_id'] == 'other-course')
    c = store.conn
    with c:
        c.execute('INSERT INTO lesson_video_sources SELECT ?,remote_path,revision,size,available,checked_at '
                  'FROM lesson_video_sources WHERE lesson_id=?', (alias['lesson_id'], original['lesson_id']))
        c.execute('DELETE FROM lesson_source_observations')  # pre-observation DB migration baseline
    (state / 'catalog/aulas_index.json').write_text('{"aulas": []}')
    ingest(state, db, index_pdfs=False)
    assert c.execute('SELECT count(*) FROM lesson_source_observations').fetchone()[0] == 2
    assert c.execute('SELECT count(*) FROM lessons').fetchone()[0] == 2
    for lesson in (original, alias):
        store.add_transcript(lesson['lesson_id'], 1, [{'start': 0, 'end': 1, 'text': 'approved'}],
                             model='fixture', corpus='generated_v2', validated=True)
    with c:
        c.execute("UPDATE transcription_jobs SET state='leased',lease_owner='worker',lease_until=9999999999 WHERE lesson_id=?",
                  (alias['lesson_id'],))
    remote[field] = value
    (state / 'remote-videos.json').write_text(json.dumps([remote]))
    ingest(state, db, index_pdfs=False)
    ingest(state, db, index_pdfs=False)
    assert [r[0] for r in c.execute('SELECT version FROM lessons')] == [2, 2]
    assert c.execute('SELECT count(*) FROM lessons').fetchone()[0] == 2
    assert c.execute("SELECT count(*) FROM lesson_revisions WHERE change_kind='media_changed'").fetchone()[0] == 2
    assert tuple(c.execute('SELECT state,lease_owner,lease_until FROM transcription_jobs WHERE lesson_id=? AND version=1',
                           (alias['lesson_id'],)).fetchone()) == ('leased', 'worker', 9999999999)
    assert c.execute("SELECT count(*) FROM transcription_jobs WHERE version=2 AND state='queued'").fetchone()[0] == 2
    assert store.get_transcript(original['lesson_id']) is None


@pytest.mark.parametrize('blocked', [None, 'missing', 'old_revision', 'retired_fallback'])
def test_persisted_mapping_reappearance_does_not_resurrect_retired_identity(source, blocked):
    state, db, _, remote, run = source
    if blocked == 'retired_fallback':
        (state / 'remote-videos.json').write_text(json.dumps([remote]))
        ingest(state, db, index_pdfs=False)
    else:
        run()
    c = FOStore(db).conn
    lid = c.execute('SELECT lesson_id FROM lessons').fetchone()[0]
    (state / 'catalog/aulas_index.json').write_text('{"aulas": []}')
    (state / 'remote-videos.json').write_text('[]')
    ingest(state, db, index_pdfs=False)
    assert c.execute('SELECT available FROM lesson_video_sources').fetchone()[0] == 0
    with c:
        if blocked in ('missing', 'retired_fallback'):
            c.execute('UPDATE lessons SET present=0')
        elif blocked == 'old_revision':
            c.execute('UPDATE lessons SET version=2')
    (state / 'remote-videos.json').write_text(json.dumps([remote]))
    ingest(state, db, index_pdfs=False)
    assert c.execute('SELECT count(*) FROM lessons').fetchone()[0] == 1
    assert c.execute('SELECT available FROM lesson_video_sources WHERE lesson_id=?', (lid,)).fetchone()[0] == int(blocked is None)
    if blocked in ('missing', 'retired_fallback'):
        assert c.execute('SELECT present FROM lessons').fetchone()[0] == 0


@pytest.mark.parametrize('proof', ['{', '[]', 'null'])
def test_invalid_inventory_proof_preserves_verified_upload(source, proof):
    state, db, aula, remote, run = source
    verified(state, aula, remote)
    run()
    remote.update(Size=12, ID='untrusted')
    (state / 'remote-videos.json').write_text(json.dumps([remote]))
    (state / 'onedrive-status.json').write_text(proof)
    ingest(state, db, index_pdfs=False)
    assert FOStore(db).conn.execute('SELECT version FROM lessons').fetchone()[0] == 1


def test_remote_fallback_respects_verified_path_precedence(source):
    state, db, aula, remote, _ = source
    verified(state, aula, remote)
    (state / 'remote-videos.json').write_text(json.dumps([remote]))
    ingest(state, db, index_pdfs=False)
    remote.update(Size=12, ID='stale', ModTime='stale')
    (state / 'remote-videos.json').write_text(json.dumps([remote]))
    ingest(state, db, index_pdfs=False)
    c = FOStore(db).conn
    assert tuple(c.execute('SELECT version,size FROM lessons JOIN lesson_video_sources USING(lesson_id)').fetchone()) == (1, 99)


def test_size_only_metadata_cannot_detect_same_size_replacement(source):
    _, db, _, remote, run = source
    remote.pop('ID')
    remote.pop('ModTime')
    run()
    run()
    assert FOStore(db).conn.execute('SELECT version FROM lessons').fetchone()[0] == 1
