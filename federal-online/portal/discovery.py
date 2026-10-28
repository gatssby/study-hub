"""Structural portal discovery, never a fixed course/category allowlist."""
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
import os
import shutil
import hashlib
import json
import csv
import io
import tempfile
import errno


def _pdf_hash(path):
    """Bounded reads; no document size cap and no whole-file buffering."""
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        before = os.fstat(handle.fileno())
        if handle.read(5) != b'%PDF-':
            raise ValueError('invalid_pdf_magic')
        handle.seek(0)
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
        after = os.fstat(handle.fileno())
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise ValueError('pdf_changed_during_hash')
    return digest.hexdigest()


def _sync_dir(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _durable_mkdir(path):
    missing = []
    current = path
    while not current.exists():
        missing.append(current)
        current = current.parent
    for directory in reversed(missing):
        directory.mkdir(exist_ok=True)
        _sync_dir(directory.parent)


def _atomic_metadata(path, data):
    _durable_mkdir(path.parent)
    fd, name = tempfile.mkstemp(prefix='.publication-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
        _sync_dir(path.parent)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _publish_pdf(source, destination, digest):
    """Link owned staging without clobber; EXDEV alone needs a budgeted copy."""
    _durable_mkdir(destination.parent)
    temporary = None
    candidate = source
    try:
        with source.open('rb') as handle:
            os.fsync(handle.fileno())
        try:
            os.link(candidate, destination)
        except OSError as exc:
            if exc.errno == errno.EXDEV:
                if shutil.disk_usage(destination.parent).free - source.stat().st_size < 4 * 1024**3:
                    raise OSError('pdf_copy_reserve') from exc
                fd, name = tempfile.mkstemp(prefix='.publication-', dir=destination.parent)
                temporary = Path(name)
                with os.fdopen(fd, 'wb') as out, source.open('rb') as inp:
                    while chunk := inp.read(1024 * 1024):
                        if shutil.disk_usage(destination.parent).free - len(chunk) < 4 * 1024**3:
                            raise OSError('pdf_copy_reserve')
                        out.write(chunk)
                    out.flush()
                    os.fsync(out.fileno())
                if _pdf_hash(temporary) != digest:
                    raise ValueError('pdf_copy_hash_mismatch')
                try:
                    os.link(temporary, destination)
                except FileExistsError:
                    if _pdf_hash(destination) != digest:
                        raise ValueError('pdf_publication_collision')
            elif exc.errno == errno.EEXIST:
                if _pdf_hash(destination) != digest:
                    raise ValueError('pdf_publication_collision')
            else:
                raise
        if _pdf_hash(destination) != digest:
            raise ValueError('pdf_publication_hash_mismatch')
        _sync_dir(destination.parent)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

ORIGIN = 'https://www.federalonline.com.br'


def catalog_navigation_links(links):
    found=[]
    for link in links:
        parts=urlsplit(urljoin(ORIGIN,link.get('href','')))
        if parts.hostname not in ('www.federalonline.com.br','federalonline.com.br'):continue
        if parts.path.rstrip('/')!='/portal/cursos' and not parts.path.startswith('/portal/curso/'):continue
        url=urlunsplit(('https','www.federalonline.com.br',parts.path.rstrip('/'),'',''))
        if url not in found:found.append(url)
    return found


def course_links(links):
    found = {}
    for link in links:
        parts = urlsplit(urljoin(ORIGIN, link.get('href', '')))
        if parts.hostname not in ('www.federalonline.com.br', 'federalonline.com.br'):
            continue
        if not parts.path.startswith('/portal/curso-aula/'):
            continue
        url = urlunsplit(('https', 'www.federalonline.com.br', parts.path.rstrip('/'), '', ''))
        found.setdefault(url, {'url': url, 'title': link.get('text', '').strip()})
    return list(found.values())


def _reject_publication_symlinks(path):
    # Do not resolve first: resolution erases the evidence we must reject.
    path = Path(path)
    if not path.is_absolute():
        path = Path.cwd() / path
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('publication_symlink')


def merge_materials(build: Path, final: Path):
    """Plan then publish immutable PDF names, metadata last; retain builds on error.

    Caller serializes producers with the materials-publication lock. Only this
    invocation's owned staging is removed, and only after complete publication.
    Both legacy promotion wrappers use this same boundary.
    """
    build, final = Path(build), Path(final)
    _reject_publication_symlinks(build)
    _reject_publication_symlinks(final)
    if build.resolve() == final.resolve() or build.resolve() in final.resolve().parents or final.resolve() in build.resolve().parents:
        raise ValueError('publication_roots_overlap')
    files = sorted(p for p in build.rglob('*') if p.is_file())
    for source in files:
        _reject_publication_symlinks(final / source.relative_to(build))
    if any(not (final / p.relative_to(build)).resolve().is_relative_to(final.resolve()) for p in files):
        raise ValueError('publication_path_escape')
    if any(p.is_symlink() for p in build.rglob('*')):
        raise ValueError('publication_symlink')
    plans = {}
    for source in files:
        if source.suffix.lower() != '.pdf':
            continue
        relative = source.relative_to(build)
        digest = _pdf_hash(source)
        destination = final / relative
        if destination.exists() and _pdf_hash(destination) != digest:
            stem = destination.stem.encode('utf-8')[:120].decode('utf-8', errors='ignore')
            destination = destination.with_name(f'{stem}--{digest}.pdf')
        _reject_publication_symlinks(destination)
        if destination.exists() and _pdf_hash(destination) != digest:
            raise ValueError('versioned_pdf_collision')
        if not destination.resolve().is_relative_to(final.resolve()):
            raise ValueError('publication_path_escape')
        plans[str(relative)] = (source, destination, digest)

    # Resolve every new manifest identity before changing any destination.
    metadata = {}
    for source in files:
        if source.name != 'manifest.json':
            continue
        payload = json.loads(source.read_text(encoding='utf-8'))
        prior_path = final / source.relative_to(build)
        prior = json.loads(prior_path.read_text(encoding='utf-8')) if prior_path.exists() else {}
        merged = {(i.get('relative_path') or i.get('target_key'), i.get('sha256', '')): i
                  for i in prior.get('items', [])}
        for original in payload['items']:
            item = dict(original)
            relative = item.get('relative_path')
            if item.get('status') == 'ok' and relative:
                rel = Path(relative)
                if rel.is_absolute() or '..' in rel.parts:
                    raise ValueError('manifest_path_escape')
                plan = plans.get(str(rel))
                if plan:
                    _, destination, digest = plan
                else:
                    destination = final / rel
                    _reject_publication_symlinks(destination)
                    if not destination.resolve().is_relative_to(final.resolve()):
                        raise ValueError('manifest_path_escape')
                    digest = _pdf_hash(destination)
                    expected = item.get('sha256')
                    if expected and digest != expected:
                        # Cleanup may already have removed staging after a
                        # collision published the full-SHA version. Require its
                        # durable manifest identity, not merely a guessed name.
                        candidates = [i for i in prior.get('items', [])
                                      if i.get('sha256') == expected
                                      and i.get('file_name') == item.get('file_name')]
                        for candidate in candidates:
                            path = final / candidate['relative_path']
                            _reject_publication_symlinks(path)
                            if not path.resolve().is_relative_to(final.resolve()):
                                raise ValueError('manifest_path_escape')
                            if _pdf_hash(path) == expected:
                                destination, digest = path, expected
                                break
                if item.get('sha256') and item['sha256'] != digest:
                    raise ValueError('manifest_pdf_hash_mismatch')
                item['sha256'] = digest
                item['relative_path'] = str(destination.relative_to(final))
                # file_name remains the original academic filename.
            merged[(item.get('relative_path') or item.get('target_key'), item.get('sha256', ''))] = item
        payload['items'] = list(merged.values())
        payload['count'] = len(payload['items'])
        payload['success_count'] = sum(i.get('status') == 'ok' for i in payload['items'])
        payload['error_count'] = payload['count'] - payload['success_count']
        metadata[source] = (json.dumps(payload, ensure_ascii=False, indent=2) + '\n').encode()
        tsv = source.with_suffix('.tsv')
        if tsv.exists():
            columns = tsv.read_text(encoding='utf-8').splitlines()[0].split('\t')
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=columns, delimiter='\t', extrasaction='ignore')
            writer.writeheader()
            writer.writerows(payload['items'])
            metadata[tsv] = output.getvalue().encode()
    # Durability precedes metadata visibility, even when only a subset succeeds.
    for source, destination, digest in plans.values():
        _publish_pdf(source, destination, digest)
    for source in files:
        if source.suffix.lower() == '.pdf':
            continue
        data = metadata[source] if source in metadata else source.read_bytes()
        _atomic_metadata(final / source.relative_to(build), data)
    # Keep the root runtime recovery marker until every staged PDF name has
    # gone. An unlink failure must never expose a hardlinked inode to download.
    for source in sorted(files, key=lambda p: (p.name == 'manifest.json', p == build / 'manifest.json')):
        source.unlink()
    for directory in sorted((p for p in build.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        directory.rmdir()
    build.rmdir()
