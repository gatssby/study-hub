"""Synthetic regressions for the observed DLX authorization-path rotation."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'portal'))

HOST = 'https://example.map.azionedge.net'
ASSET = 'synthetic-asset_01'
BASE = f'{HOST}/dlx/{ASSET}/master.m3u8'
TOKEN = '12345678-1234-1234-1234-123456789abc'
ROTATED = f'{HOST}/{TOKEN}/dlx/{ASSET}/master.m3u8?v=synthetic'


def test_rotating_dlx_locator_preserves_store_and_download_revision(tmp_path):
    from fo_hub.store import FOStore
    from video_runtime import revision

    row = dict(course_id='course', media_id='42', title='Lesson',
               media_type='video', video_url=BASE, duration_s=100)
    store = FOStore(tmp_path / 'hub.db')
    store.sync_lessons([row])
    result = store.sync_lessons([dict(row, title='Renamed', video_url=ROTATED)])
    assert result['media_changed'] == 0
    assert result['renamed'] == 1
    assert store.conn.execute('SELECT version FROM lessons').fetchone()[0] == 1
    download = {'video_stream_url': BASE, 'duracao_segundos': 100}
    assert revision(download) == revision(dict(download, video_stream_url=ROTATED))
    store.conn.close()


@pytest.mark.parametrize('changed', [
    ROTATED.replace(ASSET, 'different-asset'),
    ROTATED.replace('example.map.azionedge.net', 'different.map.azionedge.net'),
    ROTATED.replace('/dlx/', '/other/'),
    ROTATED.replace(TOKEN, 'not-an-authorized-uuid-shape'),
    ROTATED.replace('master.m3u8', 'other.m3u8'),
    ROTATED.replace('example.map.azionedge.net', 'example.map.azionedge.net.evil'),
])
def test_unproven_locator_changes_remain_distinct(changed):
    from fo_hub.ingest import canonical
    assert canonical(BASE) != canonical(changed)


def test_url_rotation_keeps_original_mapping_without_remote_fallback(tmp_path):
    from fo_hub.ingest import ingest
    from fo_hub.store import FOStore

    state = tmp_path / 'state'
    (state / 'catalog').mkdir(parents=True)
    row = {'media_id': '42', 'item_id': 'item-42',
           'course_url': 'https://www.federalonline.com.br/portal/curso-aula/produto-pacote/course/2027',
           'nome_real_aula': 'Lesson', 'video_stream_url': BASE,
           'duracao_segundos': 100, 'status': 'ok'}
    index = state / 'catalog/aulas_index.json'
    index.write_text(json.dumps({'aulas': [row]}))
    remote = 'Course/Subject/Lesson.mp4'
    (state / 'catalog/video_upload_manifest.json').write_text(json.dumps({'items': [
        {'video_stream_url': BASE, 'remote_path': 'onedrive:Federal Online/' + remote,
         'local_file_size_bytes': 99, 'duration_seconds': 100}]}))
    (state / 'remote-videos.json').write_text(json.dumps([
        {'Path': remote, 'Size': 99, 'ID': 'synthetic-object', 'ModTime': '2026-01-01'}]))
    db = tmp_path / 'hub.db'
    ingest(state, db, index_pdfs=False)
    index.write_text(json.dumps({'aulas': [dict(row, video_stream_url=ROTATED)]}))
    ingest(state, db, index_pdfs=False)
    ingest(state, db, index_pdfs=False)
    store = FOStore(db)
    assert store.conn.execute('SELECT COUNT(*) FROM lessons').fetchone()[0] == 1
    assert store.conn.execute('SELECT version FROM lessons').fetchone()[0] == 1
    assert store.conn.execute('SELECT available FROM lesson_video_sources').fetchone()[0] == 1
    assert [tuple(r) for r in store.conn.execute('SELECT version,state FROM transcription_jobs')] == [(1, 'queued')]
    store.conn.close()


@pytest.mark.parametrize('protected', ['leased', 'done', 'review', 'transcript'])
def test_remote_alias_protected_evidence_survives_canonical_discovery(tmp_path, protected):
    from fo_hub.ingest import ingest
    from fo_hub.store import FOStore

    state = tmp_path / 'state'
    (state / 'catalog').mkdir(parents=True)
    remote = 'Course/Lesson.mp4'
    (state / 'remote-videos.json').write_text(json.dumps([
        {'Path': remote, 'Size': 99, 'ID': 'synthetic-object'}]))
    db = tmp_path / 'hub.db'
    ingest(state, db, index_pdfs=False)
    store = FOStore(db)
    alias = store.conn.execute('SELECT lesson_id FROM lessons').fetchone()[0]
    with store.conn:
        if protected == 'transcript':
            store.conn.execute('INSERT INTO transcripts VALUES(?,?,?,?,?,?)',
                               (alias, 1, 'synthetic', 'generated_v2', '{}', 'synthetic'))
        else:
            store.conn.execute('UPDATE transcription_jobs SET state=? WHERE lesson_id=?',
                               (protected, alias))
    store.conn.close()
    row = {'media_id': '42', 'course_url': 'https://www.federalonline.com.br/portal/curso-aula/produto-pacote/course/2027',
           'video_stream_url': BASE, 'duracao_segundos': 100, 'status': 'ok'}
    (state / 'catalog/aulas_index.json').write_text(json.dumps({'aulas': [row]}))
    (state / 'catalog/video_upload_manifest.json').write_text(json.dumps({'items': [
        {'video_stream_url': BASE, 'remote_path': 'onedrive:Federal Online/' + remote,
         'local_file_size_bytes': 99, 'duration_seconds': 100}]}))
    ingest(state, db, index_pdfs=False)
    store = FOStore(db)
    assert store.get_lesson(alias)['present'] == 1
    assert store.conn.execute('SELECT available FROM lesson_video_sources WHERE lesson_id=?', (alias,)).fetchone()[0] == 1
    store.conn.close()
