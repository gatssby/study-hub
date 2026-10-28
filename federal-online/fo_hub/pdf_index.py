"""Build private per-document artifacts and the next generation PDF index.

Convention: materials.sha256 is the *content identity*, not a byte digest, so
existing citation.version readers identify academic content across downloads.
meta.json documents this explicitly. Byte hashes belong to material_originals.
Input is an iterable of extract_document dictionaries; at most one document is
held at once. Commits batch every 32 documents (never across all input pages).
Artifacts use private same-directory temp files followed by atomic replacement;
publication of the generation itself remains the caller's responsibility.
"""
from __future__ import annotations

import gzip
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile

from .pdf_privacy import PRIVACY_POLICY_VERSION, sanitize_page
from .store import SCHEMA, _now

_EXTRA_SCHEMA = """
CREATE TABLE IF NOT EXISTS material_originals(
 material_id TEXT NOT NULL, course_id TEXT, relative_path TEXT,
 onedrive_path TEXT NOT NULL, byte_sha256 TEXT, quickxor TEXT, size INTEGER,
 observed_at TEXT, PRIMARY KEY(material_id,onedrive_path));
CREATE TABLE IF NOT EXISTS pdf_page_structure(
 material_id TEXT NOT NULL,page INTEGER NOT NULL,markdown TEXT NOT NULL,
 blocks_json TEXT NOT NULL,flags_json TEXT NOT NULL,PRIMARY KEY(material_id,page));
"""


def _private_dir(path):
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.chmod(0o700)


def _atomic(path, data):
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def build(generation_dir, db_path, documents_iter):
    """Consume extracted documents, upserting pages and private provenance."""
    root, db_path = Path(generation_dir), Path(db_path)
    _private_dir(root)
    _private_dir(root / 'pdf')
    db_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(db_path, os.O_CREAT | os.O_RDWR, 0o600)
    os.close(fd)
    db_path.chmod(0o600)
    conn = sqlite3.connect(db_path)
    counts = {'documents': 0, 'pages': 0}
    try:
        conn.executescript(SCHEMA + _EXTRA_SCHEMA)
        for doc in documents_iter:
            identity, meta = doc['identity'], doc.get('material_meta', {})
            mid = doc['material_id']
            if not re.fullmatch(r'pdf_[0-9a-f]{24}', mid) or mid != 'pdf_' + identity['content_sha256'][:24]:
                raise ValueError('invalid content material identity')
            for page in doc['pages']:
                released = page['quality'] in {'text', 'low_text'}
                if not released and (page['text'] or page['markdown'] or page['blocks'] or page['formula_candidates'] or page['figures']['references']):
                    # OCR-needed pages may carry safe vector text and image hints.
                    if page['quality'] != 'ocr_needed':
                        raise ValueError('unsafe blocked page artifact')
                for value in [page['text'], page['markdown']] + [b['text'] for b in page['blocks']]:
                    checked = sanitize_page(value)
                    if value and (checked.text != value or checked.exposure != 'text_only'):
                        raise ValueError('unsafe page artifact')
            expected_markdown = '\n\n'.join(f"<!-- page {p['page']} -->\n\n{p['markdown']}" for p in doc['pages'])
            if doc['markdown'] != expected_markdown:
                raise ValueError('unsafe inconsistent document artifact')
            at = _now()
            folder = root / 'pdf' / mid
            _private_dir(folder)
            conn.execute('INSERT INTO materials VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(material_id) DO UPDATE SET updated_at=excluded.updated_at',
                         (mid, meta.get('lesson_id'), meta.get('subject'), meta.get('front'), meta.get('module'), meta.get('title'), 'pdf', meta.get('relative_path'), identity['content_sha256'], at))
            original_path = meta.get('onedrive_path') or meta.get('relative_path') or ''
            conn.execute('INSERT OR REPLACE INTO material_originals VALUES(?,?,?,?,?,?,?,?)',
                         (mid, meta.get('course_id'), meta.get('relative_path'), original_path,
                          identity['sha256'], meta.get('quickxor'), identity.get('size'), meta.get('observed_at') or at))
            for table in ('pdf_pages', 'pdf_page_quality', 'pdf_page_structure'):
                conn.execute(f'DELETE FROM {table} WHERE material_id=?', (mid,))
            for page in doc['pages']:
                checked = sanitize_page(page['text'])
                allowed = page['quality'] in {'text', 'low_text'} and checked.exposure == 'text_only' and checked.text == page['text']
                conn.execute('INSERT INTO pdf_pages VALUES(?,?,?)', (mid, page['page'], page['text'] if allowed else ''))
                conn.execute('INSERT INTO pdf_page_quality VALUES(?,?,?,?,?,?,?,?)',
                             (mid, page['page'], page['quality'], 'text_only' if allowed else 'blocked', len(page['text']), 0, at, PRIVACY_POLICY_VERSION))
                conn.execute('INSERT INTO pdf_page_structure VALUES(?,?,?,?,?)',
                             (mid, page['page'], page['markdown'], json.dumps(page['blocks'], ensure_ascii=False), json.dumps(page['flags'])))
            _atomic(folder / 'document.md', doc['markdown'].encode())
            _atomic(folder / 'pages.json.gz', gzip.compress(json.dumps(doc['pages'], ensure_ascii=False).encode(), mtime=0))
            artifact_meta = dict(material_id=mid, identity=identity, material_meta=meta,
                                 citation_version=identity['content_sha256'],
                                 materials_sha256_semantics='content_identity_not_byte_sha256',
                                 privacy_policy_version=PRIVACY_POLICY_VERSION)
            _atomic(folder / 'meta.json', json.dumps(artifact_meta, ensure_ascii=False).encode())
            counts['documents'] += 1
            counts['pages'] += len(doc['pages'])
            if counts['documents'] % 32 == 0:
                conn.commit()
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()
    return counts
