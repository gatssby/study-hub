"""Opt-in transitional materials batch: private snapshot, byte check, safe index.

Does not run a portal collector, mutate a database, promote a generation, or
remove originals/backups. Caller must pause legacy writers before acquisition.
Only this invocation's temporary snapshot can be cleaned after full success.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile

from .pdf_privacy import PRIVACY_POLICY_VERSION, sanitize_page


@contextmanager
def locked(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def safe_path(root, relative):
    relative = Path(relative)
    if relative.is_absolute() or '..' in relative.parts or not relative.parts:
        raise ValueError('invalid selected path')
    path = root / relative
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('symlink rejected')
    if any(p.startswith('.') for p in relative.parts):
        raise ValueError('staging/private path rejected')
    if not path.is_file() or path.suffix.lower() != '.pdf':
        raise ValueError('selected PDF missing')
    return path


def snapshot(root, selected, destination, *, max_bytes=256 * 1024**2, reserve=4 * 1024**3):
    """Copy into owned inodes; verify source stability without trusting filenames."""
    selected = list(selected)
    if not selected or len(selected) != len(set(selected)):
        raise ValueError('empty or duplicate selection')
    sources = [(name, safe_path(root, name)) for name in selected]
    total = sum(p.stat().st_size for _, p in sources)
    if total > max_bytes or shutil.disk_usage(destination).free - total < reserve:
        raise ValueError('batch budget or disk reserve')
    receipt = []
    copied = 0
    for name, source in sources:
        before = source.stat()
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        h = hashlib.sha256()
        with source.open('rb') as inp, target.open('xb') as out:
            os.fchmod(out.fileno(), 0o600)
            if inp.read(5) != b'%PDF-':
                raise ValueError('invalid PDF magic')
            inp.seek(0)
            for chunk in iter(lambda: inp.read(1024 * 1024), b''):
                copied += len(chunk)
                if copied > total or copied > max_bytes:
                    raise ValueError('source grew beyond batch budget')
                h.update(chunk)
                out.write(chunk)
            out.flush()
            os.fsync(out.fileno())
        after = source.stat()
        identity = lambda st: (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
        if identity(before) != identity(after):
            raise ValueError('source changed during snapshot')
        receipt.append({'path': name, 'sha256': h.hexdigest(), 'bytes': before.st_size})
    return receipt


def sanitized_index(database, output, *, max_pages=100000):
    """Read-only DB snapshot; blocked/OCR review stays excluded, never upgraded."""
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError('index output must be new')
    counts = {'released': 0, 'excluded': 0, 'rejected': 0}
    conn = sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True)
    temporary = None
    try:
        conn.execute('BEGIN')
        fd, temporary = tempfile.mkstemp(prefix='.materials-index-', dir=output.parent)
        with os.fdopen(fd, 'w') as handle:
            query = '''SELECT p.material_id,p.page,p.text,q.quality,q.exposure,q.policy_version
                       FROM pdf_pages p LEFT JOIN pdf_page_quality q USING(material_id,page)
                       ORDER BY p.material_id,p.page'''
            for n, (mid, page, text, quality, exposure, version) in enumerate(conn.execute(query), 1):
                if n > max_pages:
                    raise ValueError('index page budget')
                if quality not in {'text', 'low_text'} or exposure != 'text_only' or version != PRIVACY_POLICY_VERSION:
                    counts['excluded'] += 1
                    continue
                checked = sanitize_page(text or '')
                if checked.text != (text or '') or checked.exposure != 'text_only':
                    counts['rejected'] += 1
                    continue
                # Hash DB identifiers too: no arbitrary metadata in public index.
                handle.write(json.dumps({'document': hashlib.sha256(str(mid).encode()).hexdigest(),
                                         'page': int(page), 'text': checked.text,
                                         'policy': PRIVACY_POLICY_VERSION}, ensure_ascii=False) + '\n')
                counts['released'] += 1
            handle.flush()
            os.fsync(handle.fileno())
        if counts['rejected']:
            raise ValueError('privacy audit rejected released pages')
        os.link(temporary, output)  # no clobber even if another writer raced
    finally:
        conn.close()
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)
    return counts


def run_batch(state, selected, index_output, *, upload=False, runner=subprocess.run,
              max_bytes=256 * 1024**2, reserve=4 * 1024**3):
    """No automatic download; consume an explicit, bounded published selection.

    rclone --download verifies bytes without retaining a remote media download.
    Originals upload only to the existing private originals namespace, NEVER a
    public sanitized derivative namespace. Failure retains the private snapshot.
    """
    state = Path(state)
    if any(p.is_symlink() for p in (state, *state.parents)):
        raise ValueError('state symlink rejected')
    work = state / 'tmp'
    work.mkdir(mode=0o700, parents=True, exist_ok=True)
    if work.is_symlink():
        raise ValueError('temporary root symlink rejected')
    with locked(state / 'locks/materials.lock'), locked(state / 'locks/materials-publication.lock'):
        owned = Path(tempfile.mkdtemp(prefix='materials-ops-', dir=work))
        pdfs = owned / 'pdfs'
        pdfs.mkdir(mode=0o700)
        receipt = snapshot(state / 'materials', selected, pdfs, max_bytes=max_bytes, reserve=reserve)
        receipt_path = owned / 'receipt.json'
        fd = os.open(receipt_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as handle:
            json.dump(receipt, handle)
            handle.flush()
            os.fsync(handle.fileno())
        receipt_sha256 = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
        result = {'files': len(receipt), 'bytes': sum(x['bytes'] for x in receipt),
                  'snapshot_receipt_sha256': receipt_sha256,
                  'uploaded': False, 'byte_verified': False, 'cleanup': False}
        if upload:
            remote = 'onedrive:Federal Online PDFs'
            for command in (
                ['rclone', 'copy', str(pdfs), remote, '--immutable', '--transfers', '1', '--retries', '2'],
                ['rclone', 'check', str(pdfs), remote, '--one-way', '--download', '--checkers', '1', '--retries', '2'],
            ):
                runner(command, check=True, capture_output=True, text=True, timeout=7200)
            result.update(uploaded=True, byte_verified=True)
        result['index'] = sanitized_index(state / 'hub.sqlite3', index_output)
        # The original corpus, staging, backups and unrelated temporary dirs
        # are never cleanup targets, including on failed upload/check/index.
        shutil.rmtree(owned)
        result['cleanup'] = True
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--selection', type=Path, required=True, help='JSON list of published relative PDF paths')
    parser.add_argument('--index-output', type=Path, required=True)
    parser.add_argument('--upload', action='store_true', help='explicit private originals upload authorization')
    args = parser.parse_args()
    selected = json.loads(args.selection.read_text())
    if not isinstance(selected, list) or any(not isinstance(x, str) for x in selected):
        parser.error('selection must be a JSON string list')
    print(json.dumps(run_batch(args.state, selected, args.index_output, upload=args.upload)))


if __name__ == '__main__':
    main()
