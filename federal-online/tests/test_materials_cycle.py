import subprocess
import json
from pathlib import Path

import pytest
from pypdf import PdfWriter

from fo_hub import materials_cycle
from fo_hub.store import FOStore


def producer(root):
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with (root / 'one.pdf').open('wb') as handle:
        writer.write(handle)
    return [{'relative_path': 'one.pdf', 'portal_subject': 'Synthetic'}]


def test_cycle_uploads_before_index_and_cleans_only_invocation(tmp_path):
    legacy = tmp_path / 'materials'
    legacy.mkdir()
    (legacy / 'preserve.pdf').write_bytes(b'preserve')
    events = []
    def runner(argv, **kw):
        events.append(argv[1])
        assert '--immutable' in argv if argv[1] == 'copy' else '--download' in argv
        assert not (tmp_path / 'hub.sqlite3').exists()
    result = materials_cycle.run_cycle(tmp_path, producer, runner=runner, reserve=0)
    assert events == ['copy', 'check']
    assert result['cleanup'] and result['files'] == 1
    assert not list((tmp_path / 'tmp').glob('materials-cycle-*'))
    assert (legacy / 'preserve.pdf').read_bytes() == b'preserve'
    store = FOStore(tmp_path / 'hub.sqlite3')
    assert store.conn.execute('SELECT count(*) FROM pdf_pages').fetchone()[0] == 1
    assert store.conn.execute('SELECT exposure FROM pdf_page_quality').fetchone()[0] == 'blocked'
    store.conn.close()


def test_failed_upload_keeps_original_and_no_index(tmp_path):
    def runner(argv, **kw):
        raise subprocess.CalledProcessError(1, argv)
    with pytest.raises(subprocess.CalledProcessError):
        materials_cycle.run_cycle(tmp_path, producer, runner=runner, reserve=0)
    assert list((tmp_path / 'tmp').glob('materials-cycle-*/acquired/one.pdf'))
    assert not (tmp_path / 'hub.sqlite3').exists()


def test_real_local_rclone_and_repeat_preserves_blocked(tmp_path):
    import shutil
    if shutil.which('rclone') is None:
        pytest.skip('rclone not installed')
    remote = tmp_path / 'remote'
    def runner(argv, **kw):
        argv = [str(remote) if x == 'onedrive:Federal Online PDFs/objects/sha256' else x for x in argv]
        return subprocess.run(argv, **kw)
    materials_cycle.run_cycle(tmp_path, producer, runner=runner, reserve=0)
    store = FOStore(tmp_path / 'hub.sqlite3')
    with store.conn:
        store.conn.execute("UPDATE pdf_page_quality SET quality='ocr_review', exposure='blocked'")
    store.conn.close()
    materials_cycle.run_cycle(tmp_path, producer, runner=runner, reserve=0)
    store = FOStore(tmp_path / 'hub.sqlite3')
    assert store.conn.execute('SELECT quality FROM pdf_page_quality').fetchone()[0] == 'ocr_review'
    assert store.conn.execute('SELECT count(*) FROM pdf_pages').fetchone()[0] == 1
    store.conn.close()
    assert len(list(remote.glob('*.pdf'))) == 1


def test_retained_failure_blocks_new_acquisition(tmp_path):
    pending = tmp_path / 'tmp/materials-cycle-pending'
    pending.mkdir(parents=True)
    called = []
    with pytest.raises(ValueError, match='pending'):
        materials_cycle.run_cycle(tmp_path, lambda root: called.append(root), reserve=0)
    assert called == []


def test_checkpoint_only_after_verified_index(tmp_path):
    events = []
    def commit(receipt):
        store = FOStore(tmp_path / 'hub.sqlite3')
        assert store.conn.execute('SELECT count(*) FROM materials').fetchone()[0] == 1
        store.conn.close()
        events.append(receipt[0]['sha256'])
    materials_cycle.run_cycle(tmp_path, producer, runner=lambda *a, **k: None,
                              reserve=0, on_success=commit)
    assert len(events) == 1


def test_empty_observation_advances_without_upload(tmp_path):
    events = []
    result = materials_cycle.run_cycle(tmp_path, lambda root: [], reserve=0,
        runner=lambda *a, **k: pytest.fail('empty branch uploads nothing'),
        on_success=lambda receipt: events.append(receipt))
    assert events == [[]]
    assert result['files'] == 0
    assert not list((tmp_path / 'tmp').glob('materials-cycle-*'))


def test_failed_upload_does_not_advance_checkpoint(tmp_path):
    events = []
    def fail(*a, **k):
        raise RuntimeError('upload failure')
    with pytest.raises(RuntimeError):
        materials_cycle.run_cycle(tmp_path, producer, runner=fail, reserve=0,
                                  on_success=lambda receipt: events.append(receipt))
    assert not events


def test_budget_rejects_before_upload(tmp_path):
    with pytest.raises(ValueError, match='budget'):
        materials_cycle.run_cycle(tmp_path, producer, max_bytes=1, reserve=0)
    assert not (tmp_path / 'hub.sqlite3').exists()
