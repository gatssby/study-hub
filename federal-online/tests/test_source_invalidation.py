"""Remote metadata invalidation uses fixture files and SQLite only."""
import hashlib
import json
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


def test_size_only_metadata_cannot_detect_same_size_replacement(source):
    _, db, _, remote, run = source
    remote.pop('ID')
    remote.pop('ModTime')
    run()
    run()
    assert FOStore(db).conn.execute('SELECT version FROM lessons').fetchone()[0] == 1
