"""Opt-in bounded materials producer; never publishes originals into materials/."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
from types import SimpleNamespace

from .materials_ops import locked, snapshot
from .pdf_privacy import PRIVACY_POLICY_VERSION, sanitize_page
from .store import FOStore


def run_cycle(state, producer, *, runner=subprocess.run, max_bytes=256 * 1024**2,
              max_files=1, max_pages=1000, reserve=4 * 1024**3, on_success=None):
    """Producer writes only invocation-owned files. Failures retain them for recovery.

    Budgets constrain accepted output; producer/network limits are independent.
    Only newly seen hashes are indexed; existing OCR/privacy decisions are untouched.
    """
    state = Path(state)
    if any(p.is_symlink() for p in (state, *state.parents)):
        raise ValueError('state symlink rejected')
    if min(max_bytes, max_files, max_pages) <= 0 or reserve < 0:
        raise ValueError('invalid budget')
    work = state / 'tmp'
    work.mkdir(parents=True, mode=0o700, exist_ok=True)
    if work.is_symlink():
        raise ValueError('temporary root symlink rejected')
    with locked(state / 'locks/materials.lock'), locked(state / 'locks/materials-publication.lock'), locked(state / 'locks/index.lock'):
        if any(work.glob('materials-cycle-*')):
            raise ValueError('pending materials cycle requires recovery')
        if shutil.disk_usage(work).free < reserve + 2 * max_bytes:
            raise ValueError('disk reserve')
        owned = Path(tempfile.mkdtemp(prefix='materials-cycle-', dir=work))
        acquired = owned / 'acquired'
        acquired.mkdir(mode=0o700)
        items = producer(acquired)
        if not items and on_success is not None:
            on_success([])
            shutil.rmtree(owned)
            return {'files': 0, 'pages': 0, 'byte_verified': False, 'cleanup': True}
        if not items or len(items) > max_files:
            raise ValueError('file budget or empty producer')
        selected = [item['relative_path'] for item in items]
        staging = owned / 'snapshot'
        staging.mkdir(mode=0o700)
        receipt = snapshot(acquired, selected, staging, max_bytes=max_bytes, reserve=reserve)
        # Remote names are full content hashes; titles/aliases cannot overwrite versions.
        objects = owned / 'objects'
        objects.mkdir(mode=0o700)
        for item in receipt:
            os.link(staging / item['path'], objects / (item['sha256'] + '.pdf')) if not (objects / (item['sha256'] + '.pdf')).exists() else None
        (owned / 'receipt.json').write_text(json.dumps({'files': receipt, 'items': items}))
        remote = 'onedrive:Federal Online PDFs/objects/sha256'
        for command in (
            ['rclone', 'copy', str(objects), remote, '--immutable', '--checksum', '--transfers', '1', '--retries', '2'],
            ['rclone', 'check', str(objects), remote, '--one-way', '--download', '--checkers', '1', '--retries', '2'],
        ):
            runner(command, check=True, capture_output=True, text=True, timeout=1800)
        from pypdf import PdfReader
        pages = []
        for entry, meta in zip(receipt, items):
            reader = PdfReader(objects / (entry['sha256'] + '.pdf'))
            if len(reader.pages) + len(pages) > max_pages:
                raise ValueError('page budget')
            for number, page in enumerate(reader.pages, 1):
                pages.append((entry['sha256'], number, sanitize_page(page.extract_text() or '')))
        store = FOStore(state / 'hub.sqlite3')
        try:
            c = store.conn
            c.execute('CREATE TABLE IF NOT EXISTS pdf_page_quality(material_id TEXT,page INTEGER,quality TEXT,exposure TEXT,extracted_chars INTEGER,pii_redacted INTEGER,updated_at TEXT,policy_version INTEGER,PRIMARY KEY(material_id,page))')
            with c:
                for entry, meta in zip(receipt, items):
                    mid = 'pdf_' + entry['sha256'][:24]
                    # Never replace provenance or quality for an existing indexed hash.
                    if c.execute('SELECT 1 FROM materials WHERE material_id=?', (mid,)).fetchone():
                        continue
                    cols = ('material_id','subject','front','module','title','material_type','relative_path','sha256')
                    values = (mid, meta.get('output_subject') or meta.get('portal_subject'), meta.get('portal_subject'), meta.get('group'), Path(meta.get('file_name') or entry['path']).stem, meta.get('material_type'), None, entry['sha256'])
                    c.execute(f"INSERT INTO materials({','.join(cols)}) VALUES({','.join('?' for _ in cols)})", values)
                    for digest, number, page in pages:
                        if digest != entry['sha256']:
                            continue
                        c.execute('INSERT INTO pdf_pages(material_id,page,text) VALUES(?,?,?)', (mid, number, page.text))
                        c.execute("INSERT INTO pdf_page_quality VALUES(?,?,?,?,?,?,datetime('now'),?)", (mid, number, page.quality, page.exposure, len(page.text), int(page.pii_redacted), PRIVACY_POLICY_VERSION))
        finally:
            store.conn.close()
        if on_success is not None:
            on_success(receipt)
        shutil.rmtree(owned)
        return {'files': len(items), 'pages': len(pages), 'byte_verified': True, 'cleanup': True}


class Rotation:
    """Fair observation cursor; absence never deletes historical identities.

    IDs describe observed portal metadata, not a portal-guaranteed immutable ID.
    Every row is downloaded again on later passes: metadata equality is not byte
    equality. Content hashes deduplicate indexing and preserve remote versions.
    """

    def __init__(self, path):
        self.path = Path(path)
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {
            'schema': 1, 'sequence': 0, 'branches': {}, 'rows': {}}
        if self.state.get('schema') != 1:
            raise ValueError('unsupported rotation checkpoint')
        self.branch_id = None
        self.row_id = None
        self.source_url = None

    @staticmethod
    def identity(parts):
        import hashlib
        return hashlib.sha256(json.dumps(parts, ensure_ascii=False).encode()).hexdigest()

    def branch(self, options):
        branches = {}
        for course in options:
            for discipline in course['disciplines']:
                key = self.identity([course['value'], discipline['value']])
                branches[key] = {'course_value': course['value'], 'course_label': course['label'],
                                 'discipline': discipline['label'], 'discipline_value': discipline['value']}
        if not branches:
            raise ValueError('no observed material disciplines; coverage unknown')
        self.branch_id = min(branches, key=lambda key: (
            self.state['branches'].get(key, {}).get('checked', 0), key))
        self.branch_meta = branches[self.branch_id]
        return self.branch_meta

    def row(self, rows):
        observed = {}
        duplicates = {}
        for row in rows:
            base = [self.branch_id, row.title_text, row.subject_text, row.material_type, row.raw_date]
            semantic = self.identity(base)
            ordinal = duplicates.get(semantic, 0)
            duplicates[semantic] = ordinal + 1
            key = self.identity(base + [ordinal])
            observed[key] = row
        if not observed:
            self.row_id = None
            return None
        self.row_id = min(observed, key=lambda key: (
            self.state['rows'].get(key, {}).get('checked', 0), key))
        row = observed[self.row_id]
        self.row_meta = {'title': row.title_text, 'subject': row.subject_text,
                         'material_type': row.material_type, 'raw_date': row.raw_date}
        return row

    def commit(self, receipt):
        # Called only inside the acquisition lock, after byte check and DB commit.
        self.state['sequence'] += 1
        sequence = self.state['sequence']
        self.state['branches'][self.branch_id] = {**self.branch_meta, 'checked': sequence}
        if self.row_id is not None:
            entry = self.state['rows'].setdefault(self.row_id, {'hashes': []})
            entry.update(self.row_meta)
            entry['checked'] = sequence
            entry['branch_id'] = self.branch_id
            from datetime import datetime, timezone
            for item in receipt:
                entry.setdefault('versions', {})[item['sha256']] = {
                    'source_url': self.source_url, 'observed_at': datetime.now(timezone.utc).isoformat(),
                    'remote': 'onedrive:Federal Online PDFs/objects/sha256/' + item['sha256'] + '.pdf'}
                if item['sha256'] not in entry['hashes']:
                    entry['hashes'].append(item['sha256'])
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        with temporary.open('w') as handle:
            json.dump(self.state, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.path)
        fd = os.open(self.path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def collect_one(args, root, *, rotation=None):
    """Observe dynamic options and acquire at most one fairly selected row."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'portal'))
    from runtime import BrowserSession, Paths
    import fo_sync_materials_from_portal_materiais as mat
    session = BrowserSession(SimpleNamespace(command='materials', state_root=args.state,
        env_file=args.env_file, headed=False), Paths(args.state), print)
    page = None
    try:
        branch = rotation.branch(session.discover_material_options()) if rotation is not None else vars(args)
        discipline = branch['discipline']
        page = mat.open_authenticated_materials_page(session.context, session.mat_config, session.logger)
        session._save_session()
        mat.apply_filters_for_subject(page, session.mat_config, session.logger, discipline,
                                      branch['course_value'], branch['course_label'])
        rows = mat.collect_material_rows(page, session.logger, discipline, include_slides=True)
        if rotation is not None:
            row = rotation.row(rows)
            if row is None:
                return []
        else:
            if args.row < 0 or args.row >= len(rows):
                raise ValueError('selected row unavailable')
            row = rows[args.row]
        destination = root / 'selected.pdf'
        source = mat.download_material_row(page, session.mat_config, session.logger, discipline, row, destination)
        if rotation is not None:
            rotation.source_url = source
        return [{'relative_path': destination.name, 'file_name': row.title_text or mat.filename_for_row(discipline, row.material_type),
                 'portal_subject': discipline, 'material_type': row.material_type, 'source_url': source,
                 'course_value': branch['course_value'], 'discipline_value': branch.get('discipline_value'),
                 'observation_id': rotation.row_id if rotation is not None else None}]
    finally:
        if page is not None:
            page.close()
        session.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state', type=Path, required=True)
    p.add_argument('--env-file', type=Path, required=True)
    p.add_argument('--course-value')
    p.add_argument('--course-label')
    p.add_argument('--discipline')
    p.add_argument('--row', type=int)
    p.add_argument('--upload', action='store_true', required=True)
    args = p.parse_args()
    explicit = [args.course_value, args.course_label, args.discipline, args.row]
    if any(value is not None for value in explicit):
        if any(value is None for value in explicit):
            p.error('explicit single-row mode needs all four selection arguments')
        result = run_cycle(args.state, lambda root: collect_one(args, root))
    else:
        holder = {}
        def producer(root):
            # Load only after run_cycle owns the lock; never reuse a stale cursor.
            holder['rotation'] = Rotation(args.state / 'materials-rotation.json')
            return collect_one(args, root, rotation=holder['rotation'])
        result = run_cycle(args.state, producer,
                           on_success=lambda receipt: holder['rotation'].commit(receipt))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
