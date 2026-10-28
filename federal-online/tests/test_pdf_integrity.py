import hashlib

import os
import pytest

from fo_hub.pdf_integrity import integrity_snapshot


def test_freeze_deduplicates_and_survives_in_place_alias_change(tmp_path):
    from fo_hub.pdf_integrity import preserve_version
    source = tmp_path / 'alias.pdf'
    source.write_bytes(b'%PDF-original')
    expected = hashlib.sha256(b'%PDF-original').hexdigest()
    cache = tmp_path / 'private'
    frozen = preserve_version(source, cache, expected, reserve_bytes=0)
    assert frozen == preserve_version(source, cache, expected, reserve_bytes=0)
    assert len(list(cache.glob('*.pdf'))) == 1
    assert os.stat(source).st_ino != os.stat(frozen).st_ino
    assert cache.stat().st_mode & 0o777 == 0o700
    source.write_bytes(b'%PDF-replaced')
    assert frozen.read_bytes() == b'%PDF-original'
    with pytest.raises(ValueError):
        preserve_version(source, cache, '1' * 64, reserve_bytes=0)
    assert len(list(cache.glob('*.pdf'))) == 1



def test_snapshot_fails_closed_for_unobserved_missing_and_unsafe(tmp_path):
    source = tmp_path / 'ok.pdf'
    source.write_bytes(b'%PDF-ok')
    expected = hashlib.sha256(b'%PDF-ok').hexdigest()
    rows = [dict(material_id=key, relative_path=path, sha256=sha)
            for key, path, sha in [('bad', '../outside.pdf', expected),
                                   ('invalid', 'ok.pdf', expected.upper()),
                                   ('missing', 'absent.pdf', expected),
                                   ('budget', 'ok.pdf', expected)]]
    result = integrity_snapshot(tmp_path, rows, max_paths=1)['materials']
    assert result['bad']['status'] == 'invalid_path'
    assert result['invalid']['status'] == 'invalid_identity'
    assert result['missing']['status'] == 'source_unavailable'
    assert result['budget']['status'] == 'not_observed'


def test_freeze_rejects_budget_corruption_and_invalid_identity(tmp_path):
    from fo_hub.pdf_integrity import preserve_version
    source = tmp_path / 'alias.pdf'
    source.write_bytes(b'%PDF-original')
    sha = hashlib.sha256(b'%PDF-original').hexdigest()
    cache = tmp_path / 'private'
    for options in [dict(max_bytes=5), dict(reserve_bytes=10**30)]:
        with pytest.raises(ValueError):
            preserve_version(source, cache, sha, **options)
    with pytest.raises(ValueError):
        preserve_version(source, cache, sha.upper(), reserve_bytes=0)
    assert list(cache.iterdir()) == []
    frozen = preserve_version(source, cache, sha, reserve_bytes=0)
    frozen.chmod(0o600)
    frozen.write_bytes(b'%PDF-corrupt')
    with pytest.raises(ValueError):
        preserve_version(source, cache, sha, reserve_bytes=0)
    assert frozen.read_bytes() == b'%PDF-corrupt'  # never silently repair/overwrite


def test_snapshot_hashes_one_path_and_distinguishes_historical(tmp_path):
    source = tmp_path / 'source.pdf'
    source.write_bytes(b'%PDF-new')
    actual = hashlib.sha256(b'%PDF-new').hexdigest()
    rows = [dict(material_id='old', relative_path='source.pdf', sha256='0' * 64),
            dict(material_id='new', relative_path='source.pdf', sha256=actual)]
    result = integrity_snapshot(tmp_path, rows, max_paths=1)
    assert result['hashed_paths'] == 1
    assert result['materials']['old']['status'] == 'historical_source_unavailable'
    assert result['materials']['new']['status'] == 'verified'
    source.write_bytes(b'%PDF-changed')
    assert result['materials']['new']['status'] == 'verified'  # observation, not live guarantee
