import json
from pathlib import Path
import sqlite3
import subprocess

import pytest

from fo_hub.materials_ops import run_batch, sanitized_index, snapshot
from fo_hub.pdf_privacy import PRIVACY_POLICY_VERSION


def setup_state(tmp_path):
    materials = tmp_path / 'materials'
    materials.mkdir()
    (materials / 'one.pdf').write_bytes(b'%PDF-synthetic')
    conn = sqlite3.connect(tmp_path / 'hub.sqlite3')
    conn.executescript('CREATE TABLE pdf_pages(material_id TEXT,page INTEGER,text TEXT); CREATE TABLE pdf_page_quality(material_id TEXT,page INTEGER,quality TEXT,exposure TEXT,policy_version INTEGER);')
    for page, quality, exposure, text, policy in (
        (1, 'text', 'text_only', 'Academic synthetic text', PRIVACY_POLICY_VERSION),
        (2, 'ocr_review', 'blocked', 'Review remains private', PRIVACY_POLICY_VERSION),
        (3, 'ocr_empty', 'blocked', '', PRIVACY_POLICY_VERSION),
        (4, 'text', 'text_only', 'Stale policy text', PRIVACY_POLICY_VERSION - 1),
    ):
        conn.execute('INSERT INTO pdf_pages VALUES(?,?,?)', ('synthetic', page, text))
        conn.execute('INSERT INTO pdf_page_quality VALUES(?,?,?,?,?)', ('synthetic', page, quality, exposure, policy))
    conn.commit()
    conn.close()
    return materials


def test_safe_batch_checks_bytes_then_cleans_only_owned(tmp_path):
    materials = setup_state(tmp_path)
    backup = tmp_path / 'pre-catalog'
    backup.mkdir()
    (backup / 'evidence').write_text('preserve')
    before = (materials / 'one.pdf').stat()
    calls = []
    def runner(argv, **kwargs):
        calls.append(argv)
        assert kwargs['check'] is True
        assert (Path(argv[2]) / 'one.pdf').read_bytes() == b'%PDF-synthetic'
    result = run_batch(tmp_path, ['one.pdf'], tmp_path / 'safe.jsonl', upload=True, runner=runner, reserve=0)
    assert result['byte_verified'] and result['cleanup']
    assert calls[0][1] == 'copy' and '--immutable' in calls[0]
    assert calls[1][1] == 'check' and '--download' in calls[1]
    assert result['index'] == {'released': 1, 'excluded': 3, 'rejected': 0}
    assert [json.loads(line)['page'] for line in (tmp_path / 'safe.jsonl').read_text().splitlines()] == [1]
    assert (tmp_path / 'safe.jsonl').stat().st_mode & 0o777 == 0o600
    assert before.st_ino == (materials / 'one.pdf').stat().st_ino
    assert before.st_mtime_ns == (materials / 'one.pdf').stat().st_mtime_ns
    assert (backup / 'evidence').read_text() == 'preserve'
    assert not list((tmp_path / 'tmp').glob('materials-ops-*'))


def test_failed_check_keeps_snapshot_no_index(tmp_path):
    setup_state(tmp_path)
    def runner(argv, **kwargs):
        if argv[1] == 'check':
            raise subprocess.CalledProcessError(1, argv)
    with pytest.raises(subprocess.CalledProcessError):
        run_batch(tmp_path, ['one.pdf'], tmp_path / 'safe.jsonl', upload=True, runner=runner, reserve=0)
    assert not (tmp_path / 'safe.jsonl').exists()
    assert len(list((tmp_path / 'tmp').glob('materials-ops-*/pdfs/one.pdf'))) == 1


@pytest.mark.parametrize('relative', ['../escape.pdf', '/escape.pdf', '.build_bad/file.pdf'])
def test_path_rejection(tmp_path, relative):
    materials = setup_state(tmp_path)
    with pytest.raises(ValueError):
        snapshot(materials, [relative], tmp_path, reserve=0)


def test_reject_symlink_and_budget(tmp_path):
    materials = setup_state(tmp_path)
    (materials / 'link.pdf').symlink_to(materials / 'one.pdf')
    with pytest.raises(ValueError):
        snapshot(materials, ['link.pdf'], tmp_path, reserve=0)
    with pytest.raises(ValueError):
        snapshot(materials, ['one.pdf'], tmp_path, max_bytes=1, reserve=0)


def test_unsafe_released_text_blocks_publication(tmp_path):
    setup_state(tmp_path)
    conn = sqlite3.connect(tmp_path / 'hub.sqlite3')
    conn.execute("UPDATE pdf_pages SET text='Nome: Pessoa Sintetica' WHERE page=1")
    conn.commit()
    conn.close()
    with pytest.raises(ValueError, match='privacy'):
        sanitized_index(tmp_path / 'hub.sqlite3', tmp_path / 'index.jsonl')
    assert not (tmp_path / 'index.jsonl').exists()


def test_real_rclone_local_byte_check(tmp_path):
    import shutil
    if shutil.which('rclone') is None:
        pytest.skip('rclone not installed')
    state = tmp_path / 'state'
    state.mkdir()
    setup_state(state)
    remote = tmp_path / 'synthetic-remote'
    commands = []
    def runner(argv, **kwargs):
        argv = [str(remote) if arg == 'onedrive:Federal Online PDFs' else arg for arg in argv]
        commands.append(argv[1])
        return subprocess.run(argv, **kwargs)
    result = run_batch(state, ['one.pdf'], tmp_path / 'real-index.jsonl', upload=True, runner=runner, reserve=0)
    assert result['byte_verified'] is True
    assert commands == ['copy', 'check']
    assert (remote / 'one.pdf').read_bytes() == b'%PDF-synthetic'


def test_index_no_clobber(tmp_path):
    setup_state(tmp_path)
    output = tmp_path / 'index.jsonl'
    output.write_text('existing')
    with pytest.raises(ValueError):
        sanitized_index(tmp_path / 'hub.sqlite3', output)
    assert output.read_text() == 'existing'
