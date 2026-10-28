"""Synthetic source-version fixtures only; no private corpus access."""
import hashlib
import json

from fo_hub.pdf_integrity import integrity_snapshot
from fo_hub.pdf_privacy import PRIVACY_POLICY_VERSION
from fo_hub.store import FOStore


def seed(tmp_path):
    store = FOStore(tmp_path / 'hub.sqlite3')
    alias = tmp_path / 'alias.pdf'
    alias.write_bytes(b'%PDF-new')
    new_sha = hashlib.sha256(alias.read_bytes()).hexdigest()
    for mid, sha in [('old', '0' * 64), ('new', new_sha)]:
        store.upsert_material(dict(material_id=mid, title=mid, sha256=sha,
                                   relative_path='alias.pdf'))
        store.set_pdf_pages(mid, ['Equação científica: E = mc².'])
        store.conn.execute('INSERT INTO pdf_page_quality VALUES(?,?,?,?,?,?,?,?)',
                           (mid, 1, 'text', 'text_only', 30, 0, 'now', PRIVACY_POLICY_VERSION))
    store.conn.commit()
    return store


def test_reused_alias_keeps_cached_identity_but_not_false_original(tmp_path):
    store = seed(tmp_path)
    rows = [dict(r) for r in store.conn.execute('SELECT * FROM materials')]
    snapshot = integrity_snapshot(tmp_path, rows, max_paths=1)
    assert store.record_pdf_source_snapshot(snapshot) == 2
    old = store.get_pdf_text('old')
    assert old['source'] is None
    assert old['version'] == '0' * 64
    assert old['text_provenance'] == 'indexed_snapshot'
    assert old['pages'][0]['text'] == 'Equação científica: E = mc².'
    assert old['source_observation']['status'] == 'historical_source_unavailable'
    assert old['source_observation']['observed_at'] == snapshot['observed_at']
    assert old['source_observation']['current_bytes_guaranteed'] is False
    new = store.get_pdf_text('new')
    assert new['source_observation']['status'] == 'verified'
    assert new['source_observation']['meaning'] == 'verified_at_observation'
    assert new['source'] is None
    listing = store.search_materials()
    assert {r['material_id']: r['source_observation']['status'] for r in listing} == {
        'new': 'verified', 'old': 'historical_source_unavailable'}
    public = json.dumps([old, new, listing])
    assert 'alias.pdf' not in public
    assert str(tmp_path) not in public
    store.conn.close()


def test_legacy_readonly_never_hashes_and_does_not_invent_source(tmp_path, monkeypatch):
    import fo_hub.pdf_integrity as integrity
    store = seed(tmp_path)
    store.conn.execute('DROP TABLE pdf_source_observations')
    store.conn.commit()
    store.conn.close()
    monkeypatch.setattr(integrity, '_digest', lambda _: (_ for _ in ()).throw(AssertionError('hot-path hash')))
    ro = FOStore(tmp_path / 'hub.sqlite3', readonly=True)
    assert ro.get_pdf_text('old')['source_observation']['status'] == 'not_observed'
    assert ro.get_pdf_text('old')['source_observation']['observed_at'] is None
    assert ro.get_pdf_text('old')['source'] is None
    assert ro.search_materials()[0]['source_observation']['status'] == 'not_observed'
    assert ro.get_pdf_text('absent') is None
    ro.conn.close()


def test_rejects_stale_identity_and_atomic_batch(tmp_path):
    import pytest
    store = seed(tmp_path)
    rows = [dict(r) for r in store.conn.execute('SELECT * FROM materials')]
    snapshot = integrity_snapshot(tmp_path, rows, max_paths=1)
    snapshot['materials']['new']['expected_sha256'] = 'f' * 64
    with pytest.raises(ValueError, match='identity'):
        store.record_pdf_source_snapshot(snapshot)
    assert store.conn.execute('SELECT COUNT(*) FROM pdf_source_observations').fetchone()[0] == 0
    snapshot = integrity_snapshot(tmp_path, rows, max_paths=1)
    store.record_pdf_source_snapshot(snapshot)
    store.conn.execute("UPDATE materials SET sha256=? WHERE material_id='new'", ('e' * 64,))
    store.conn.commit()
    assert store.get_pdf_text('new')['source_observation']['status'] == 'not_observed'
    store.conn.close()


def test_bounded_explicit_cli_refresh(tmp_path, capsys):
    from fo_hub.pdf_integrity import main
    store = seed(tmp_path)
    store.conn.close()
    assert main(['--db', str(tmp_path / 'hub.sqlite3'), '--state-root', str(tmp_path),
                 '--material-id', 'old', '--material-id', 'new', '--max-paths', '1', '--refresh']) == 0
    output = json.loads(capsys.readouterr().out)
    assert output['hashed_paths'] == 1
    assert output['recorded_materials'] == 2
    assert 'alias.pdf' not in json.dumps(output)
    ro = FOStore(tmp_path / 'hub.sqlite3', readonly=True)
    assert ro.get_pdf_text('old')['source_observation']['status'] == 'historical_source_unavailable'
    ro.conn.close()


def test_invalid_identity_observation_retains_timestamp(tmp_path):
    store = seed(tmp_path)
    store.upsert_material(dict(material_id='invalid', sha256=None))
    snapshot = integrity_snapshot(tmp_path, [dict(material_id='invalid', sha256=None)], max_paths=0)
    assert store.record_pdf_source_snapshot(snapshot) == 1
    observed = store.get_pdf_text('invalid')['source_observation']
    assert observed['status'] == 'invalid_identity'
    assert observed['observed_at'] == snapshot['observed_at']
    store.conn.close()


def test_api_observation_cached_even_after_alias_changes(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from fo_hub.api import create_app
    import fo_hub.pdf_integrity as integrity
    store = seed(tmp_path)
    snapshot = integrity_snapshot(tmp_path, [dict(r) for r in store.conn.execute('SELECT * FROM materials')])
    store.record_pdf_source_snapshot(snapshot)
    store.conn.close()
    (tmp_path / 'alias.pdf').write_bytes(b'%PDF-third-version')
    monkeypatch.setattr(integrity, '_digest', lambda _: (_ for _ in ()).throw(AssertionError('hot-path hash')))
    with TestClient(create_app(tmp_path / 'hub.sqlite3')) as client:
        text = client.get('/fo/materials/new/pdf-text').json()
        assert text['source_observation']['status'] == 'verified'
        assert text['source_observation']['current_bytes_guaranteed'] is False
        assert text['source'] is None
        listing = client.get('/fo/materials').json()
        assert all(item['relative_path'] is None for item in listing['items'])
        assert client.get('/fo/materials/absent/pdf-text').status_code == 404


def test_cli_rejects_unbounded_unknown_and_missing_database(tmp_path, capsys):
    import pytest
    from fo_hub.pdf_integrity import main
    db = tmp_path / 'missing.sqlite3'
    base = ['--db', str(db), '--state-root', str(tmp_path), '--material-id', 'old', '--refresh']
    for extra in [[], ['--max-paths', '-1'], ['--max-paths', '513']]:
        with pytest.raises(SystemExit) as error:
            main(base + extra)
        assert error.value.code == 2
        assert not db.exists()
    store = seed(tmp_path)
    store.conn.close()
    base[1] = str(tmp_path / 'hub.sqlite3')
    with pytest.raises(SystemExit):
        main(base + ['--material-id', 'unknown'])
    ro = FOStore(tmp_path / 'hub.sqlite3', readonly=True)
    assert ro.conn.execute('SELECT COUNT(*) FROM pdf_source_observations').fetchone()[0] == 0
    ro.conn.close()
    assert 'alias.pdf' not in capsys.readouterr().err


def test_persisted_fail_closed_states_and_older_proof_rejected(tmp_path):
    import pytest
    store = seed(tmp_path)
    extra = [dict(material_id='missing', relative_path='missing.pdf', sha256='1' * 64),
             dict(material_id='unsafe', relative_path='../outside.pdf', sha256='2' * 64)]
    for row in extra:
        store.upsert_material(row)
    snapshot = integrity_snapshot(tmp_path, extra, max_paths=1)
    assert store.record_pdf_source_snapshot(snapshot) == 2
    assert store.get_pdf_text('missing')['source_observation']['status'] == 'source_unavailable'
    assert store.get_pdf_text('unsafe')['source_observation']['status'] == 'invalid_path'
    snapshot['observed_at'] -= 1
    with pytest.raises(ValueError, match='older'):
        store.record_pdf_source_snapshot(snapshot)
    rows = [dict(r) for r in store.conn.execute('SELECT * FROM materials')]
    zero = integrity_snapshot(tmp_path, rows, max_paths=0)
    store.record_pdf_source_snapshot(zero)
    assert store.get_pdf_text('new')['source_observation']['status'] == 'not_observed'
    assert store.get_pdf_text('new')['source_observation']['observed_at'] is not None
    store.conn.close()


def test_rejects_impossible_snapshot_hash_counts(tmp_path):
    import pytest
    store = seed(tmp_path)
    snapshot = integrity_snapshot(tmp_path, [dict(r) for r in store.conn.execute('SELECT * FROM materials')])
    snapshot['hashed_paths'] = 0
    with pytest.raises(ValueError, match='count'):
        store.record_pdf_source_snapshot(snapshot)
    assert store.conn.execute('SELECT COUNT(*) FROM pdf_source_observations').fetchone()[0] == 0
    store.conn.close()
