"""Publication contracts using small synthetic PDF bytes; no real corpus IO."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'portal'))
import discovery


def test_version_destination_symlink_rejected_before_publication(tmp_path):
    final, build = tmp_path / 'final', tmp_path / '.build'
    seed(final, b'%PDF-old')
    new = seed(build, b'%PDF-new')
    original = final / 'original.pdf'
    original.write_bytes(b'%PDF-new')
    state = original.stat()
    (final / f"lesson--{new['sha256']}.pdf").symlink_to(original)
    manifest = (final / 'manifest.json').read_bytes()
    with pytest.raises(ValueError, match='publication_symlink'):
        discovery.merge_materials(build, final)
    assert (final / 'manifest.json').read_bytes() == manifest
    assert original.read_bytes() == b'%PDF-new'
    assert (original.stat().st_ino, original.stat().st_mtime_ns) == (state.st_ino, state.st_mtime_ns)
    assert (build / 'lesson.pdf').exists()


def test_runtime_recovers_legacy_markerless_hardlink_before_download(tmp_path):
    import os
    import runtime
    from types import SimpleNamespace
    final = tmp_path / 'materials/course'
    build = tmp_path / 'materials/.build_course'
    seed(final, b'%PDF-published')
    build.mkdir()
    os.link(final / 'lesson.pdf', build / 'lesson.pdf')
    before = (final / 'lesson.pdf').stat()
    def process(job, staging, entries):
        assert not (staging / 'lesson.pdf').exists(), 'published hardlink reaches downloader'
        entries.append(seed(staging, b'%PDF-new'))
    args = SimpleNamespace(state_root=tmp_path, mode='weekly', course_filter='', upload=False)
    options = [{'value': '1', 'label': 'Course', 'disciplines': [{'label': 'Science'}]}]
    assert runtime.materials(args, discover_options=lambda: options, process=process,
                             write_manifest=lambda *a: None) == 0
    assert (final / 'lesson.pdf').read_bytes() == b'%PDF-published'
    after = (final / 'lesson.pdf').stat()
    assert (before.st_ino, before.st_mtime_ns) == (after.st_ino, after.st_mtime_ns)


@pytest.mark.parametrize('location', ['build', 'build_parent', 'final', 'final_parent'])
def test_symlink_roots_and_ancestors_rejected_without_side_effect(tmp_path, location):
    originals = tmp_path / 'originals'
    seed(originals, b'%PDF-original')
    before = {p.name: (p.read_bytes(), p.stat().st_ino, p.stat().st_mtime_ns) for p in originals.iterdir()}
    link = tmp_path / 'link'
    link.symlink_to(originals, target_is_directory=True)
    build, final = tmp_path / '.build', tmp_path / 'final'
    if location == 'build':
        build = link
    elif location == 'build_parent':
        seed(originals / 'nested', b'%PDF-original')
        build = link / 'nested'
    elif location == 'final':
        final = link
    else:
        final = link / 'nested'
    if not location.startswith('build'):
        seed(build, b'%PDF-new')
    with pytest.raises(ValueError, match='publication_symlink'):
        discovery.merge_materials(build, final)
    for name, state in before.items():
        p = originals / name
        assert (p.read_bytes(), p.stat().st_ino, p.stat().st_mtime_ns) == state
    if location == 'final_parent':
        assert not (originals / 'nested').exists()
    if location == 'build_parent':
        assert (originals / 'nested/lesson.pdf').read_bytes() == b'%PDF-original'
        assert (originals / 'nested/manifest.json').exists()


def test_cleanup_pdf_failure_keeps_runtime_recovery_marker(tmp_path, monkeypatch):
    final, build = tmp_path / 'final', tmp_path / '.build'
    seed(final, b'%PDF-old')
    new = seed(build / 'subject', b'%PDF-new')
    (build / 'subject/manifest.json').unlink()
    (build / 'manifest.json').write_text(json.dumps({'items': [dict(new, relative_path='subject/lesson.pdf')]}))
    real = Path.unlink
    def fail_pdf(path, *args, **kwargs):
        if path == build / 'subject/lesson.pdf':
            raise OSError('cleanup interrupted')
        return real(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'unlink', fail_pdf)
    with pytest.raises(OSError, match='cleanup interrupted'):
        discovery.merge_materials(build, final)
    assert (build / 'manifest.json').exists()
    monkeypatch.setattr(Path, 'unlink', real)
    discovery.merge_materials(build, final)
    assert not build.exists()


def test_cleanup_manifest_failure_recovers_version_without_staged_pdf(tmp_path, monkeypatch):
    final, build = tmp_path / 'final', tmp_path / '.build'
    old = seed(final, b'%PDF-old')
    new = seed(build, b'%PDF-new')
    real = Path.unlink
    def fail_manifest(path, *args, **kwargs):
        if path == build / 'manifest.json':
            raise OSError('cleanup interrupted')
        return real(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'unlink', fail_manifest)
    with pytest.raises(OSError):
        discovery.merge_materials(build, final)
    # Also represents interruption after staged PDF removal, regardless of order.
    real(build / 'lesson.pdf', missing_ok=True)
    monkeypatch.setattr(Path, 'unlink', real)
    discovery.merge_materials(build, final)
    assert not build.exists()
    assert (final / 'lesson.pdf').read_bytes() == b'%PDF-old'
    assert {i['sha256'] for i in json.loads((final / 'manifest.json').read_text())['items']} == {old['sha256'], new['sha256']}


def seed(root, data):
    root.mkdir(parents=True, exist_ok=True)
    (root / 'lesson.pdf').write_bytes(data)
    item = dict(status='ok', file_name='lesson.pdf', relative_path='lesson.pdf',
                sha256=hashlib.sha256(data).hexdigest(), byte_size=len(data))
    (root / 'manifest.json').write_text(json.dumps(dict(items=[item], count=1)))
    return item


def test_collision_preserves_original_and_both_manifest_identities(tmp_path):
    final, build = tmp_path / 'final', tmp_path / '.build'
    old = seed(final, b'%PDF-old')
    before = (final / 'lesson.pdf').stat().st_mtime_ns
    new = seed(build, b'%PDF-new')
    discovery.merge_materials(build, final)
    assert (final / 'lesson.pdf').read_bytes() == b'%PDF-old'
    assert (final / 'lesson.pdf').stat().st_mtime_ns == before
    items = json.loads((final / 'manifest.json').read_text())['items']
    assert {i['sha256'] for i in items} == {old['sha256'], new['sha256']}
    for item in items:
        assert hashlib.sha256((final / item['relative_path']).read_bytes()).hexdigest() == item['sha256']
        assert item['file_name'] == 'lesson.pdf'
    assert (final / f"lesson--{new['sha256']}.pdf").exists()
    seed(build, b'%PDF-new')
    discovery.merge_materials(build, final)
    assert len(list(final.glob('*.pdf'))) == 2
    assert len(json.loads((final / 'manifest.json').read_text())['items']) == 2


def test_identical_reuses_inode_and_mtime_without_copy(tmp_path, monkeypatch):
    final, build = tmp_path / 'final', tmp_path / '.build'
    seed(final, b'%PDF-same')
    seed(build, b'%PDF-same')
    stat = (final / 'lesson.pdf').stat()
    monkeypatch.setattr(discovery.shutil, 'disk_usage', lambda *_: pytest.fail('no copy budget for same FS'))
    discovery.merge_materials(build, final)
    after = (final / 'lesson.pdf').stat()
    assert (stat.st_ino, stat.st_mtime_ns) == (after.st_ino, after.st_mtime_ns)
    assert len(list(final.glob('*.pdf'))) == 1


@pytest.mark.parametrize('phase', ['pdf', 'metadata'])
def test_failure_retains_build_and_retry_is_deduplicated(tmp_path, monkeypatch, phase):
    final, build = tmp_path / 'final', tmp_path / '.build'
    old = seed(final, b'%PDF-old')
    new = seed(build, b'%PDF-new')
    original_manifest = (final / 'manifest.json').read_bytes()
    target = '_publish_pdf' if phase == 'pdf' else '_atomic_metadata'
    real = getattr(discovery, target)
    def fail(*args):
        raise OSError('injected disk failure')
    monkeypatch.setattr(discovery, target, fail)
    with pytest.raises(OSError):
        discovery.merge_materials(build, final)
    assert (final / 'manifest.json').read_bytes() == original_manifest
    assert (build / 'lesson.pdf').read_bytes() == b'%PDF-new'
    assert (build / 'manifest.json').exists()
    assert (final / 'lesson.pdf').read_bytes() == b'%PDF-old'
    monkeypatch.setattr(discovery, target, real)
    discovery.merge_materials(build, final)
    assert not build.exists()
    items = json.loads((final / 'manifest.json').read_text())['items']
    assert {i['sha256'] for i in items} == {old['sha256'], new['sha256']}
    assert len(list(final.glob('*.pdf'))) == 2


def test_manifest_hash_mismatch_is_rejected_before_any_publication(tmp_path):
    final, build = tmp_path / 'final', tmp_path / '.build'
    seed(final, b'%PDF-old')
    seed(build, b'%PDF-new')
    payload = json.loads((build / 'manifest.json').read_text())
    payload['items'][0]['sha256'] = '0' * 64
    (build / 'manifest.json').write_text(json.dumps(payload))
    with pytest.raises(ValueError, match='manifest_pdf_hash_mismatch'):
        discovery.merge_materials(build, final)
    assert list(final.glob('*.pdf')) == [final / 'lesson.pdf']
    assert (build / 'lesson.pdf').exists()


@pytest.mark.parametrize('wrapper', ['raw', 'output'])
def test_legacy_wrappers_share_safe_version_promotion(tmp_path, wrapper):
    final, build = tmp_path / 'raw', tmp_path / '.build'
    seed(final, b'%PDF-old')
    seed(build, b'%PDF-new')
    if wrapper == 'raw':
        from fo_sync_materials import promote_raw_dir
        promote_raw_dir(tmp_path, build)
    else:
        from fo_sync_materials_from_portal_materiais import promote_output_dir
        promote_output_dir(tmp_path, build, final)
    assert (final / 'lesson.pdf').read_bytes() == b'%PDF-old'
    assert len(list(final.glob('*.pdf'))) == 2


def test_tsv_matches_json_version_paths(tmp_path):
    import csv
    final, build = tmp_path / 'final', tmp_path / '.build'
    seed(final, b'%PDF-old')
    seed(build, b'%PDF-new')
    (build / 'manifest.tsv').write_text('file_name\trelative_path\tsha256\n')
    discovery.merge_materials(build, final)
    with (final / 'manifest.tsv').open() as handle:
        rows = list(csv.DictReader(handle, delimiter='\t'))
    for row in rows:
        assert hashlib.sha256((final / row['relative_path']).read_bytes()).hexdigest() == row['sha256']
    assert len(rows) == 2


def test_runtime_upload_contains_original_and_new_version(tmp_path):
    import runtime
    from types import SimpleNamespace
    final = tmp_path / 'materials/course'
    old = seed(final, b'%PDF-old')
    args = SimpleNamespace(state_root=tmp_path, mode='weekly', course_filter='', upload=True)
    options = [{'value': '1', 'label': 'Course', 'disciplines': [{'label': 'Science'}]}]
    def process(job, build, entries):
        entries.append(seed(build, b'%PDF-new'))
    uploads = []
    def upload(root):
        items = json.loads((final / 'manifest.json').read_text())['items']
        assert (final / 'lesson.pdf').read_bytes() == b'%PDF-old'
        assert old['sha256'] in {i['sha256'] for i in items}
        assert len(list(final.glob('*.pdf'))) == 2
        assert not list(root.glob('.build_*'))
        uploads.append(root)
    assert runtime.materials(args, discover_options=lambda: options, process=process,
                             write_manifest=lambda *a: None, upload=upload) == 0
    assert uploads == [tmp_path / 'materials']


def test_cross_device_copy_refuses_below_reserve_without_losing_source(tmp_path, monkeypatch):
    import errno
    from types import SimpleNamespace
    final, build = tmp_path / 'final', tmp_path / '.build'
    seed(final, b'%PDF-old')
    seed(build, b'%PDF-new')
    def exdev(*args):
        raise OSError(errno.EXDEV, 'different filesystem')
    monkeypatch.setattr(discovery.os, 'link', exdev)
    monkeypatch.setattr(discovery.shutil, 'disk_usage', lambda *_: SimpleNamespace(free=4 * 1024**3))
    with pytest.raises(OSError, match='pdf_copy_reserve'):
        discovery.merge_materials(build, final)
    assert (final / 'lesson.pdf').read_bytes() == b'%PDF-old'
    assert (build / 'lesson.pdf').read_bytes() == b'%PDF-new'


def test_pdf_failure_never_exposes_new_manifest_and_runtime_retries_first(tmp_path, monkeypatch):
    import runtime
    from types import SimpleNamespace
    final = tmp_path / 'materials/course'
    build = tmp_path / 'materials/.build_course'
    seed(final, b'%PDF-old')
    seed(build, b'%PDF-pending')
    before = (final / 'manifest.json').read_bytes()
    real = discovery._publish_pdf
    monkeypatch.setattr(discovery, '_publish_pdf', lambda *a: (_ for _ in ()).throw(OSError('disk')))
    args = SimpleNamespace(state_root=tmp_path, mode='weekly', course_filter='', upload=True)
    options = [{'value': '1', 'label': 'Course', 'disciplines': [{'label': 'Science'}]}]
    assert runtime.materials(args, discover_options=lambda: options,
                             process=lambda *a: pytest.fail('must retry before new downloads'),
                             write_manifest=lambda *a: None,
                             upload=lambda *a: pytest.fail('failed generation cannot upload')) == 1
    assert (final / 'manifest.json').read_bytes() == before
    assert json.loads((tmp_path / 'materials/checkpoint.json').read_text())['done'] == []
    monkeypatch.setattr(discovery, '_publish_pdf', real)
    def process(job, staging, entries):
        assert not (staging / 'lesson.pdf').exists()
        assert len(list(final.glob('*.pdf'))) == 2
        entries.append(seed(staging, b'%PDF-latest'))
    assert runtime.materials(args, discover_options=lambda: options, process=process,
                             write_manifest=lambda *a: None, upload=lambda *a: None) == 0
    assert len(list(final.glob('*.pdf'))) == 3


def test_cross_device_copy_verifies_and_reuses_version(tmp_path, monkeypatch):
    import errno
    final, build = tmp_path / 'final', tmp_path / '.build'
    seed(final, b'%PDF-old')
    new = seed(build, b'%PDF-new')
    real_link = discovery.os.link
    def cross_device(source, destination):
        if Path(source).parent == build:
            raise OSError(errno.EXDEV, 'different filesystem')
        return real_link(source, destination)
    monkeypatch.setattr(discovery.os, 'link', cross_device)
    discovery.merge_materials(build, final)
    assert (final / f"lesson--{new['sha256']}.pdf").read_bytes() == b'%PDF-new'
    assert (final / 'lesson.pdf').read_bytes() == b'%PDF-old'
    assert not list(final.glob('.publication-*'))


def test_no_clobber_race_refuses_foreign_bytes_and_keeps_retry_source(tmp_path, monkeypatch):
    final, build = tmp_path / 'final', tmp_path / '.build'
    old = seed(final, b'%PDF-old')
    new = seed(build, b'%PDF-new')
    version = final / f"lesson--{new['sha256']}.pdf"
    real_link = discovery.os.link
    def race(source, destination):
        Path(destination).write_bytes(b'%PDF-foreign')
        return real_link(source, destination)
    monkeypatch.setattr(discovery.os, 'link', race)
    with pytest.raises(ValueError, match='pdf_publication_collision'):
        discovery.merge_materials(build, final)
    assert version.read_bytes() == b'%PDF-foreign'
    assert (final / 'lesson.pdf').read_bytes() == b'%PDF-old'
    assert (build / 'lesson.pdf').read_bytes() == b'%PDF-new'
    assert json.loads((final / 'manifest.json').read_text())['items'] == [old]
