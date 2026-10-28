import pytest
import gzip
import json
import sqlite3
import stat

from test_pdf_identity import _pdf
from fo_hub.pdf_extract import extract_document
from fo_hub.store import FOStore


def test_build_idempotent_content_collapses_originals_and_serves_safely(tmp_path):
    from fo_hub.pdf_index import build
    source = tmp_path / 'a.pdf'
    source.write_bytes(_pdf(b'Conteudo academico integro para estudo.', b'Pessoa Fake 00000000000'))
    doc = extract_document(source, material_meta={'title': 'Aula', 'course_id': 'course-a', 'relative_path': None, 'onedrive_path': 'a.pdf'})
    other = dict(doc, material_meta={**doc['material_meta'], 'course_id': 'course-b', 'onedrive_path': 'b.pdf'})
    generation, db = tmp_path / 'generation', tmp_path / 'index.db'
    build(generation, db, iter([doc, other]))
    build(generation, db, iter([doc, other]))
    with sqlite3.connect(db) as conn:
        assert conn.execute('select count(*) from materials').fetchone()[0] == 1
        assert conn.execute('select count(*) from material_originals').fetchone()[0] == 2
        assert conn.execute('select count(*) from pdf_pages').fetchone()[0] == 2
        assert conn.execute('select sha256 from materials').fetchone()[0] == doc['identity']['content_sha256']
    folder = generation / 'pdf' / doc['material_id']
    assert (folder / 'document.md').read_text() == doc['markdown']
    assert json.loads(gzip.decompress((folder / 'pages.json.gz').read_bytes())) == doc['pages']
    assert stat.S_IMODE(folder.stat().st_mode) == 0o700
    for file in folder.iterdir():
        assert stat.S_IMODE(file.stat().st_mode) == 0o600
    store = FOStore(db, readonly=True)
    assert store.get_pdf_text(doc['material_id'])['pages'][0]['text'] == doc['pages'][0]['text']
    store.conn.close()


def test_builder_rejects_unsafe_artifacts(tmp_path):
    from fo_hub.pdf_index import build
    source = tmp_path / 'unsafe.pdf'
    source.write_bytes(_pdf(b'Nome: Isaac Newton', None))
    doc = extract_document(source, material_meta={})
    doc['pages'][0]['markdown'] = 'Nome: Isaac Newton'
    with pytest.raises(ValueError, match='unsafe'):
        build(tmp_path / 'gen', tmp_path / 'index.db', [doc])
    assert not list((tmp_path / 'gen').rglob('document.md'))


def test_blocked_page_never_served_or_written_as_markdown(tmp_path):
    from fo_hub.pdf_index import build
    source = tmp_path / 'blocked.pdf'
    source.write_bytes(_pdf(b'Nome: Isaac Newton', None))
    doc = extract_document(source, material_meta={})
    db = tmp_path / 'index.db'
    build(tmp_path / 'gen', db, [doc])
    store = FOStore(db, readonly=True)
    page = store.get_pdf_text(doc['material_id'])['pages'][0]
    assert page['text'] == '' and page['exposure'] == 'blocked'
    store.conn.close()
