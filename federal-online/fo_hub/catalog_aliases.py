"""Two-phase retirement of failed observations, never of real video identities.

Only one present same-course/same-item video with a current available source can
replace an error observation. Keep every revision and all protected QA evidence.
No download, remote deletion, media equivalence claim or present=1 operation.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

from .catalog_reconcile import handle, public


def _digest(actions):
    return hashlib.sha256(json.dumps(actions, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _source(row):
    return {k: row.get(k) for k in ('revision', 'size', 'available')} | {'remote_handle': handle(row.get('remote_path'))}


def _plan(c):
    lessons = [dict(r) for r in c.execute('SELECT * FROM lessons')]
    sources = {r['lesson_id']: dict(r) for r in c.execute('SELECT * FROM lesson_video_sources')}
    protected = {r[0] for r in c.execute("SELECT lesson_id FROM transcription_jobs WHERE state IN ('leased','done','review')")}
    protected.update(r[0] for r in c.execute('SELECT lesson_id FROM transcripts'))
    candidates = defaultdict(list)
    for row in lessons:
        s = sources.get(row['lesson_id'], {})
        if (row['present'] and row['media_type'] == 'video' and row.get('item_id')
                and s.get('available') == 1 and str(s.get('revision')) == str(row['version'])
                and s.get('remote_path') and int(s.get('size') or 0) > 0):
            candidates[(row['course_id'], row['item_id'])].append(row)
    actions, blocked = [], []
    for row in lessons:
        if not row['present'] or row['media_type'] != 'error':
            continue
        s = sources.get(row['lesson_id'], {})
        matches = candidates.get((row['course_id'], row['item_id']), []) if row.get('item_id') else []
        reason = ('protected_evidence' if row['lesson_id'] in protected else
                  'error_has_available_source' if s.get('available') else
                  'canonical_not_unique_or_unavailable' if len(matches) != 1 else None)
        if reason:
            blocked.append({'lesson_id': row['lesson_id'], 'reason': reason})
        else:
            candidate = matches[0]
            actions.append({'alias': public(row), 'alias_source': _source(s),
                            'canonical': public(candidate), 'canonical_source': _source(sources[candidate['lesson_id']])})
    actions.sort(key=lambda x: x['alias']['lesson_id'])
    return {'schema_version': 1, 'observed_at': datetime.now(timezone.utc).isoformat(),
            'actions': actions, 'plan_sha256': _digest(actions),
            'blocked': sorted(blocked, key=lambda x: x['lesson_id']),
            'blocked_counts': dict(Counter(x['reason'] for x in blocked)),
            'scope': 'failed_observation_metadata_only_no_media_identity_merge'}


def plan(db):
    with closing(sqlite3.connect(Path(db).resolve().as_uri() + '?mode=ro', uri=True)) as c:
        c.row_factory = sqlite3.Row
        c.execute('BEGIN')
        return _plan(c)


def apply(db, expected):
    actions = expected.get('actions', [])
    digest = expected.get('plan_sha256')
    if expected.get('schema_version') != 1 or _digest(actions) != digest:
        raise ValueError('invalid plan checksum or schema')
    with closing(sqlite3.connect(Path(db).resolve().as_uri() + '?mode=rw', uri=True, timeout=10)) as c:
        c.row_factory = sqlite3.Row
        try:
            c.execute('BEGIN IMMEDIATE')
            has_ledger = c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='catalog_alias_retirements'").fetchone()
            if actions and has_ledger:
                old = {r['lesson_id']: dict(r) for r in c.execute('SELECT * FROM catalog_alias_retirements WHERE plan_sha256=?', (digest,))}
                ids = {x['alias']['lesson_id'] for x in actions}
                if set(old) == ids and all(c.execute('SELECT 1 FROM lessons WHERE lesson_id=? AND version=? AND present=0',
                        (x['alias']['lesson_id'], x['alias']['version'])).fetchone() for x in actions):
                    c.rollback()
                    return {'retired': 0, 'already_applied': True, 'plan_sha256': digest}
            current = _plan(c)
            if current['plan_sha256'] != digest:
                raise ValueError('stale alias plan; regenerate without changing any records')
            if not actions:
                c.rollback()
                return {'retired': 0, 'already_applied': False, 'plan_sha256': digest}
            c.execute('''CREATE TABLE IF NOT EXISTS catalog_alias_retirements(
                lesson_id TEXT NOT NULL, version INTEGER NOT NULL, canonical_lesson_id TEXT NOT NULL,
                plan_sha256 TEXT NOT NULL, evidence_json TEXT NOT NULL, retired_at TEXT NOT NULL,
                PRIMARY KEY(lesson_id,version))''')
            at = datetime.now(timezone.utc).isoformat()
            for action in actions:
                alias = action['alias']
                changed = c.execute("UPDATE lessons SET present=0 WHERE lesson_id=? AND version=? AND present=1 AND media_type='error'",
                                    (alias['lesson_id'], alias['version']))
                if changed.rowcount != 1:
                    raise ValueError('stale alias during atomic apply')
                c.execute('UPDATE lesson_video_sources SET available=0 WHERE lesson_id=?', (alias['lesson_id'],))
                c.execute("UPDATE transcription_jobs SET state='superseded' WHERE lesson_id=? AND state='queued'", (alias['lesson_id'],))
                c.execute('INSERT INTO catalog_alias_retirements VALUES(?,?,?,?,?,?)',
                          (alias['lesson_id'], alias['version'], action['canonical']['lesson_id'], digest,
                           json.dumps(action, sort_keys=True), at))
            c.commit()
            return {'retired': len(actions), 'already_applied': False, 'plan_sha256': digest}
        except BaseException:
            c.rollback()
            raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--apply-plan', type=Path)
    args = parser.parse_args(argv)
    result = apply(args.db, json.loads(args.apply_plan.read_text())) if args.apply_plan else plan(args.db)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
