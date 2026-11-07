"""Read-only, URL-free FO catalog reconciliation. No media or DB mutations.

Run on the host owning state: python -m fo_hub.catalog_reconcile --state-root ...
Only exact persisted remote-path matches establish alias candidates; neither
matching titles nor object metadata proves byte identity or source eligibility.
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
from urllib.parse import urlsplit
from portal.fo_media_identity import canonical_media_url


def canonical(url):
    return canonical_media_url(url)


def course_key(url):
    parts = urlsplit(url or '').path.strip('/').split('/')
    return parts[parts.index('produto-pacote') + 1] if 'produto-pacote' in parts and len(parts) > parts.index('produto-pacote') + 1 else canonical(url)


FIELDS = ('lesson_id', 'course_id', 'media_id', 'item_id', 'media_type', 'present', 'version')


def public_course_id(value):
    return 'url-sha256:' + str(handle(value)) if '://' in str(value or '') else value


def public(row):
    result = {k: row.get(k) for k in FIELDS}
    result['course_id'] = public_course_id(result.get('course_id'))
    return result


def handle(value):
    return hashlib.sha256(str(value).encode()).hexdigest()[:24] if value else None


def entry_key(entry):
    # Match the collector's durable branch/item identity, not media ID alone.
    ref = ' '.join(str(entry.get('source_ref') or '').split())
    item = entry.get('item_id') or entry.get('media_id')
    return (ref, str(item)) if ref and item else None


def read(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def reconcile(state_root):
    state = Path(state_root).resolve()
    db = state / 'hub.sqlite3'
    with closing(sqlite3.connect(db.as_uri() + '?mode=ro', uri=True)) as c:
        c.row_factory = sqlite3.Row
        c.execute('BEGIN')  # consistent read snapshot, never instantiate FOStore
        lessons = [dict(r) for r in c.execute('SELECT * FROM lessons')]
        sources = {r['lesson_id']: dict(r) for r in c.execute('SELECT * FROM lesson_video_sources')}
        jobs = [dict(r) for r in c.execute('SELECT lesson_id,version,state FROM transcription_jobs')]
    inventory_path = state / 'remote-videos.json'
    inventory_bytes = inventory_path.read_bytes() if inventory_path.exists() else None
    inventory = {x['Path']: x for x in json.loads(inventory_bytes or b'[]')}
    by_path = defaultdict(list)
    for lesson in lessons:
        path = sources.get(lesson['lesson_id'], {}).get('remote_path')
        if path:
            by_path[path].append(lesson)
    missing = []
    for lesson in lessons:
        if lesson['present']:
            continue
        source = sources.get(lesson['lesson_id'], {})
        path = source.get('remote_path')
        matches = [x for x in by_path.get(path, []) if x['present'] and x['lesson_id'] != lesson['lesson_id']] if path else []
        observed = bool(path and path.removeprefix('onedrive:Federal Online/') in inventory)
        classification = ('retired_remote_alias_with_present_exact_path' if matches and lesson['course_id'].startswith('remote:')
                          else 'missing_with_present_exact_path' if matches
                          else 'missing_remote_object_still_observed' if observed
                          else 'missing_remote_object_not_in_inventory' if path and inventory_bytes is not None
                          else 'missing_without_inventory_proof' if path
                          else 'missing_without_source_mapping')
        missing.append({**public(lesson), 'classification': classification,
                        'path_handle': handle(path), 'remote_object_observed': observed,
                        'source_available': source.get('available'), 'source_revision': source.get('revision'),
                        'canonical_candidates': [{**public(x), 'source_available': sources[x['lesson_id']].get('available'),
                                                  'source_revision': sources[x['lesson_id']].get('revision'),
                                                  'current_source': str(sources[x['lesson_id']].get('revision')) == str(x['version'])}
                                                 for x in sorted(matches, key=lambda x: x['lesson_id'])]})
    registry = read(state / 'catalog/courses.json', {}).get('courses', [])
    course_urls = {course_key(x.get('url')): x.get('url') for x in registry}
    course_labels = {course_key(x.get('url')): x.get('title') for x in registry}
    video_state = read(state / 'videos.json', {}).get('items', {})
    manifests = read(state / 'catalog/video_upload_manifest.json', {}).get('items', [])
    active_jobs = {(j['lesson_id'], j['version']) for j in jobs if j['state'] == 'queued'}
    pending = []
    for lesson in lessons:
        source = sources.get(lesson['lesson_id'], {})
        if not lesson['present'] or (lesson['lesson_id'], lesson['version']) not in active_jobs:
            continue
        if source.get('available') and str(source.get('revision')) == str(lesson['version']):
            continue
        path = source.get('remote_path')
        key = hashlib.sha256((canonical(course_urls.get(lesson['course_id'])) + '|' + str(lesson['media_id'] or lesson['item_id'])).encode()).hexdigest()[:24]
        record = video_state.get(key, {})
        manifest_matches = [x for x in manifests if lesson.get('video_url') and canonical(x.get('video_stream_url')) == canonical(lesson['video_url'])]
        url_aliases = [public(x) for x in lessons if lesson.get('video_url') and x['present'] and x['lesson_id'] != lesson['lesson_id']
                       and canonical(x.get('video_url')) == canonical(lesson['video_url']) and sources.get(x['lesson_id'], {}).get('available')
                       and str(sources[x['lesson_id']].get('revision')) == str(x['version'])]
        pending.append({**public(lesson), 'course_title': course_labels.get(lesson['course_id']),
                        'collector_action': 'recapture_authenticated_stream' if not lesson.get('video_url') else 'inspect_existing_remote_and_duration_before_upload',
                        'video_state_status': record.get('status'),
                        'video_error_type': record.get('error_type') if str(record.get('error_type') or '').replace('_', '').isalnum() else None,
                        'manifest_matches': len(manifest_matches),
                        'manifest_durations_match': [x.get('duration_seconds') == lesson.get('duration_s') for x in manifest_matches],
                        'eligible_same_url_candidates': url_aliases,
                        'same_url_present_lesson_ids': sorted(x['lesson_id'] for x in lessons if lesson.get('video_url') and x['present'] and x['lesson_id'] != lesson['lesson_id'] and canonical(x.get('video_url')) == canonical(lesson['video_url'])),
                        'classification': 'source_revision_stale' if source and str(source.get('revision')) != str(lesson['version'])
                        else 'mapped_object_unavailable' if path else 'no_remote_mapping',
                        'has_video_url': bool(lesson.get('video_url')), 'path_handle': handle(path),
                        'source_available': source.get('available'), 'source_revision': source.get('revision')})
    catalogs = []
    current_entries = {}
    for path in sorted((state / 'catalog/courses').glob('*/aulas_index.json')):
        payload = read(path, {})
        entries = payload.get('aulas', [])
        evidence = payload.get('collection_evidence', {})
        cid = path.parent.name
        current_entries[cid] = [x for x in entries if x.get('catalog_observation') != 'retained_previous_not_observed'] + evidence.get('pending_errors', [])
        catalogs.append({'course_id': cid, 'db_course_id': public_course_id(course_key(payload.get('course_url'))), 'course_title': payload.get('course_title'), 'total': len(entries),
                         'status_counts': dict(Counter(x.get('status', 'unknown') for x in entries)),
                         'observed_total': evidence.get('observed_total', len(entries)),
                         'observed_status_counts': evidence.get('observed_status_counts', dict(Counter(x.get('status', 'unknown') for x in entries))),
                         'retained_previous': evidence.get('retained_previous', 0),
                         'traversal_errors': len(evidence.get('traversal_errors', [])),
                         'generated_at': payload.get('generated_at'),
                         'empty_classification': 'empty_catalog_not_live_verified' if not entries else None})
    historical = []
    historical_root = state / 'rebuild/g20261029a/catalog/courses'
    for path in sorted(historical_root.glob('*/aulas_index.json')):
        entries = read(path, {}).get('aulas', [])
        latest = defaultdict(list)
        for entry in current_entries.get(path.parent.name, []):
            if entry_key(entry):
                latest[entry_key(entry)].append(entry)
        seen = set()
        for entry in entries:
            if entry.get('status') != 'error':
                continue
            key = entry_key(entry)
            evidence_handle = handle(json.dumps(key)) if key else handle(json.dumps(entry, sort_keys=True))
            if evidence_handle in seen:
                continue
            seen.add(evidence_handle)
            outcomes = latest.get(key, []) if key else []
            statuses = sorted({x.get('status', 'unknown') for x in outcomes})
            historical.append({'course_id': path.parent.name, 'entry_handle': evidence_handle,
                               'media_id': entry.get('media_id'), 'item_id': entry.get('item_id'),
                               'current_statuses': statuses,
                               'classification': 'resolved_ok' if statuses == ['ok'] else 'resolved_not_launched' if statuses == ['not_launched']
                               else 'still_error' if statuses == ['error'] else 'ambiguous' if statuses else 'not_reobserved'})
    coverage = []
    for cid in sorted({x['course_id'] for x in lessons}):
        rows = [x for x in lessons if x['course_id'] == cid]
        coverage.append({'course_id': public_course_id(cid), 'course_title': course_labels.get(cid), 'total': len(rows),
                         'present': sum(bool(x['present']) for x in rows), 'missing': sum(not x['present'] for x in rows),
                         'present_media_types': dict(Counter(x['media_type'] for x in rows if x['present']))})
    nonvideo = []
    for lesson in lessons:
        if lesson['media_type'] not in ('error', 'not_launched', 'invalid_source'):
            continue
        candidates = [public(x) for x in lessons if x['present'] and x['course_id'] == lesson['course_id']
                      and lesson.get('item_id') and x.get('item_id') == lesson['item_id']
                      and x['lesson_id'] != lesson['lesson_id'] and x['media_type'] == 'video']
        nonvideo.append({**public(lesson), 'classification': 'legacy_error_with_present_exact_item_video' if lesson['media_type'] == 'error' and candidates
                         else 'legacy_error_requires_reobservation' if lesson['media_type'] == 'error'
                         else 'not_launched_with_present_exact_item_video' if candidates
                         else 'not_launched_or_invalid_without_video_replacement', 'present_exact_item_video_candidates': candidates})
    return {'schema_version': 1, 'observed_at': datetime.now(timezone.utc).isoformat(),
            'read_only': True, 'inventory_sha256': hashlib.sha256(inventory_bytes).hexdigest() if inventory_bytes is not None else None,
            'counts': {'total': len(lessons), 'present': sum(bool(x['present']) for x in lessons), 'missing': len(missing),
                       'pending_sources': len(pending), 'historical_error_identities': len(historical)},
            'coverage_by_db_course': coverage,
            'missing_by_course': dict(sorted(Counter(x['course_id'] for x in missing).items())),
            'missing_by_classification': dict(Counter(x['classification'] for x in missing)),
            'pending_by_course': dict(Counter(x['course_id'] for x in pending)),
            'historical_error_outcomes': dict(Counter(x['classification'] for x in historical)),
            'missing': sorted(missing, key=lambda x: (x['course_id'], x['lesson_id'])),
            'pending_sources': sorted(pending, key=lambda x: (x['course_id'], x['lesson_id'])),
            'historical_errors': historical, 'catalogs': catalogs,
            'nonvideo_observations': sorted(nonvideo, key=lambda x: (x['course_id'], x['lesson_id'])),
            'nonvideo_classifications': dict(Counter(x['classification'] for x in nonvideo)),
            'limitations': ['Exact path aliases are identity mappings, not a fresh byte hash or acoustic verification.',
                            'Inventory is persisted metadata, not a fresh OneDrive listing.',
                            'Zero collected entries does not establish zero available portal lessons.',
                            'SQLite snapshot and filesystem observations are not a cross-producer atomic snapshot.']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-root', required=True, type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(reconcile(args.state_root), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
