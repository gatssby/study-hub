"""Opt-in private PDF byte identity helpers; no DB or publication side effects.

Snapshots are caller-owned observations, never proof that a mutable alias still
has those bytes. Historical cached text retains its original SHA identity.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import time
import shutil
import tempfile


def preserve_version(source, private_root, expected_sha256, *,
                     reserve_bytes=4 * 1024**3, max_bytes=512 * 1024**2):
    """Copy verified bytes once into a dedicated private SHA-addressed store.

    Never link a mutable producer inode. Never overwrite an existing version.
    Caller must hold its publication/storage-budget lock; 0444 is an operational
    immutability convention, not protection against the owning user/root.
    """
    if not isinstance(expected_sha256, str) or not re.fullmatch('[0-9a-f]{64}', expected_sha256):
        raise ValueError('invalid SHA-256')
    if reserve_bytes < 0 or max_bytes < 5:
        raise ValueError('invalid storage budget')
    source = Path(source)
    root = Path(private_root)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.is_symlink() or root.stat().st_mode & 0o077:
        raise ValueError('private root must be mode 0700')
    destination = root / (expected_sha256 + '.pdf')
    if destination.is_symlink():
        raise ValueError('unsafe version object')
    if destination.exists():
        if _digest(destination) != expected_sha256:
            raise ValueError('corrupt existing version')
        return destination
    size = source.stat().st_size
    if size > max_bytes or shutil.disk_usage(root).free < reserve_bytes + size:
        raise ValueError('insufficient copy budget')
    fd, temporary_name = tempfile.mkstemp(prefix='.pending-', dir=root)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, 'wb') as target, source.open('rb') as original:
            total = 0
            for chunk in iter(lambda: original.read(1024 * 1024), b''):
                total += len(chunk)
                if total > max_bytes or shutil.disk_usage(root).free < reserve_bytes + len(chunk):
                    raise ValueError('copy budget exhausted')
                target.write(chunk)
            target.flush()
            os.fsync(target.fileno())
        if _digest(temporary) != expected_sha256:
            raise ValueError('source SHA mismatch')
        temporary.chmod(0o444)
        try:
            # Link only the owned completed temporary, never the producer file.
            os.link(temporary, destination)
        except FileExistsError:
            if destination.is_symlink() or _digest(destination) != expected_sha256:
                raise ValueError('conflicting version object')
        directory = os.open(root, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return destination
    finally:
        temporary.unlink(missing_ok=True)


def _digest(path):
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        if stream.read(5) != b'%PDF-':
            raise ValueError('invalid PDF magic')
        stream.seek(0)
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
        after = os.fstat(stream.fileno())
    current = path.stat()
    signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if signature(before) != signature(after) or signature(after) != signature(current):
        raise ValueError('source changed during observation')
    return digest.hexdigest()


def integrity_snapshot(root, materials, *, max_paths=64):
    """Hash at most max_paths unique aliases once; return no source paths/text.

    Unobserved rows fail closed. Caller supplies rows from one read-only DB
    snapshot, caches this returned object, and explicitly refreshes it later.
    """
    if max_paths < 0:
        raise ValueError('negative path budget')
    root = Path(root).resolve()
    observations = {}
    output = {}
    hashed = 0
    for row in materials:
        relative = row.get('relative_path')
        expected = row.get('sha256')
        actual = None
        status = 'invalid_identity'
        if isinstance(expected, str) and re.fullmatch('[0-9a-f]{64}', expected):
            try:
                path = (root / relative).resolve()
                if Path(relative).is_absolute() or not path.is_relative_to(root):
                    raise ValueError('unsafe alias')
                if path not in observations:
                    if len(observations) >= max_paths:
                        observations[path] = ('not_observed', None)
                    else:
                        try:
                            actual = _digest(path)
                            hashed += 1
                            observations[path] = ('observed', actual)
                        except (OSError, ValueError):
                            observations[path] = ('source_unavailable', None)
                status, actual = observations[path]
                if status == 'observed':
                    status = 'verified' if actual == expected else 'historical_source_unavailable'
            except (TypeError, ValueError):
                status = 'invalid_path'
        output[row['material_id']] = dict(status=status, expected_sha256=expected,
                                          actual_sha256=actual)
    return dict(observed_at=time.time(), hashed_paths=hashed, materials=output)


def main(argv=None):
    """Explicit bounded observer. Not called by API or routine ingestion."""
    import argparse
    import json
    import sqlite3
    from collections import Counter
    from .store import FOStore

    parser = argparse.ArgumentParser(description='Observe selected PDF aliases; no current-byte guarantee')
    parser.add_argument('--db', required=True)
    parser.add_argument('--state-root', required=True)
    parser.add_argument('--material-id', action='append', required=True)
    parser.add_argument('--max-paths', type=int, default=64)
    parser.add_argument('--refresh', action='store_true', required=True,
                        help='Explicitly authorize bounded observation and cached status update')
    args = parser.parse_args(argv)
    ids = list(dict.fromkeys(args.material_id))
    if not 0 <= args.max_paths <= 512 or not 1 <= len(ids) <= 512:
        parser.error('path/material budget must be between 0/1 and 512')
    # Read-only first: a typo must never create an empty database.
    try:
        store = FOStore(args.db, readonly=True)
        try:
            with store.conn:
                store.conn.execute('BEGIN')
                rows = [dict(row) for row in store.conn.execute(
                    'SELECT material_id,sha256,relative_path FROM materials WHERE material_id IN ('
                    + ','.join('?' for _ in ids) + ') ORDER BY material_id', ids)]
        finally:
            store.conn.close()
        if len(rows) != len(ids):
            parser.error('selection contains unknown material IDs')
        snapshot = integrity_snapshot(args.state_root, rows, max_paths=args.max_paths)
        store = FOStore(args.db)
        try:
            recorded = store.record_pdf_source_snapshot(snapshot)
        finally:
            store.conn.close()
    except (OSError, ValueError, sqlite3.Error):
        parser.error('observation failed; no source paths or private diagnostics exposed')
    print(json.dumps(dict(observed_at=snapshot['observed_at'],
                          hashed_paths=snapshot['hashed_paths'], recorded_materials=recorded,
                          statuses=dict(Counter(row['status'] for row in snapshot['materials'].values())),
                          current_bytes_guaranteed=False), sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
