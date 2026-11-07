"""Unpublished collector builds must never mint lessons/download candidates."""
import json
import sys
from pathlib import Path
import pytest
from fo_hub.ingest import ingest
from fo_hub.store import FOStore
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'portal'))
import video_runtime


@pytest.mark.parametrize('root_name', ['catalog', 'catalogs'])
@pytest.mark.parametrize('stage_name', ['.build_aulas_index_123', 'course/.build_aulas_index_456'])
def test_catalog_readers_ignore_unpublished_trees(tmp_path, monkeypatch, root_name, stage_name):
    state = tmp_path / 'state'
    stage = state / root_name / stage_name
    stage.mkdir(parents=True)
    row = {'media_id':'42','item_id':'stable','course_url':'https://example.test/produto-pacote/course',
           'status':'ok','video_stream_url':'https://example.test/video.m3u8','duracao_segundos':100}
    (stage/'aulas_index.json').write_text(json.dumps({'aulas':[row]}))
    monkeypatch.setattr(video_runtime, 'STATE', state)
    db = state / 'test.sqlite3'
    ingest(state, db, index_pdfs=False)
    c = FOStore(db, readonly=True).conn
    try:
        assert c.execute('SELECT count(*) FROM lessons').fetchone()[0] == 0
    finally:
        c.close()
    assert video_runtime.rows_from_catalog() == []
    published = state / root_name / 'published'
    stage.rename(published)
    ingest(state, db, index_pdfs=False)
    c = FOStore(db, readonly=True).conn
    try:
        assert c.execute('SELECT count(*) FROM lessons').fetchone()[0] == 1
    finally:
        c.close()
    assert len(video_runtime.rows_from_catalog()) == 1


@pytest.mark.parametrize('root_name', ['catalog', 'catalogs'])
def test_retained_previous_rows_are_not_new_observations(tmp_path, monkeypatch, root_name):
    state = tmp_path/'state';published = state/root_name/'published';published.mkdir(parents=True)
    row = {'media_id':'42','item_id':'stable','course_url':'https://example.test/produto-pacote/course',
           'status':'ok','video_stream_url':'https://example.test/video.m3u8','duracao_segundos':100,
           'catalog_observation':'retained_previous_not_observed'}
    (published/'aulas_index.json').write_text(json.dumps({'aulas':[row]}))
    monkeypatch.setattr(video_runtime, 'STATE', state)
    db=state/'test.sqlite3';ingest(state,db,index_pdfs=False)
    c=FOStore(db,readonly=True).conn
    try:assert c.execute('SELECT count(*) FROM lessons').fetchone()[0] == 0
    finally:c.close()
    assert video_runtime.rows_from_catalog() == []
