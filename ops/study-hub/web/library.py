"""Bounded, read-only study catalog and approved transcript projection."""
from __future__ import annotations

from collections import Counter
from contextlib import closing
import json
import math
import re
import sqlite3
import time
from urllib.parse import urlsplit

from fo_hub.disciplines import discipline_for
from fo_hub.store import FOStore
from types import SimpleNamespace
from portal.fo_media_identity import canonical_media_url

LESSON_ID = re.compile(r'fo_[0-9a-f]{16}')
MAX_LESSONS = 5000
MAX_CATALOG_BYTES = 3 * 1024 * 1024
MAX_TRANSCRIPT_BYTES = 256 * 1024
MAX_SEGMENTS = 2000
MAX_REGISTRY_BYTES = 1024 * 1024

# Read job state and approval from the same snapshot as the current catalog row.
# Test approval using the same corpus, strict JSON boolean, and source guard as
# the producer's current transcript API; never open review or media files.
_CATALOG = '''SELECT l.lesson_id, l.course_id, substr(l.subject,1,1025) AS subject,
    substr(l.front,1,1025) AS front, substr(l.module,1,1025) AS module,
    substr(l.title,1,1025) AS title, l.media_type, l.duration_s, l.version,
    j.state AS job_state, j.lease_until, j.attempts, j.max_attempts,
    (s.available=1 AND s.revision=CAST(l.version AS TEXT) AND s.remote_path IS NOT NULL) AS has_source,
    ({approval} AND EXISTS (SELECT 1 FROM transcript_segments seg
            WHERE seg.lesson_id=l.lesson_id AND seg.version=l.version)) AS approved
    FROM lessons l LEFT JOIN transcription_jobs j USING (lesson_id, version)
    LEFT JOIN lesson_video_sources s USING (lesson_id)
    LEFT JOIN transcripts t USING (lesson_id, version)
    WHERE l.present=1'''


def transcript_current_join(db):
    # Use the exact schema-aware serving gate, including rollout compatibility.
    return FOStore._CURRENT.fget(SimpleNamespace(conn=db))


def transcript_approval(db):
    current = transcript_current_join(db).replace(' l ', ' current_l ').replace('l.', 'current_l.')
    return ("EXISTS (SELECT 1 FROM transcripts t " + current +
            " WHERE t.lesson_id=s.lesson_id AND t.version=CAST(s.revision AS INTEGER))")


# Privacy guard. Source paths carry backslashes, a scheme/drive, a leading slash,
# a media/file extension, or repeated '/' separators; those stay masked. Subject,
# front and module never legitimately contain '/' (verified against the live
# catalog: zero single-slash values), so any slash there is masked. A lesson TITLE
# may carry one academic slash — year ranges "2023/2024" and terms such as
# "oxidação/redução" / "Realismo/Naturalismo" — but an all-caps/underscore path
# fragment ("INTERNAL/PRIVATE_FOLDER") is still masked.
_PATH_EXTENSION = re.compile(
    r'\.(mp4|m4v|mkv|avi|mov|webm|mp3|wav|pdf|docx?|xlsx?|pptx?|txt|json|gz|zip)\b', re.I)


def _label(value, fallback, *, module=False, allow_slash=False):
    if not isinstance(value, str) or len(value) > 1024:
        return fallback
    folded = value.casefold()
    if ('\\' in value or 'onedrive:' in folded or '://' in folded or ':\\' in folded
            or value.startswith('/') or _PATH_EXTENSION.search(value) or re.match(r'^[a-z]:', folded)):
        return fallback
    if '/' in value:
        if not allow_slash or value.count('/') >= 2 or '_' in value:
            return fallback
        left, right = value.split('/', 1)
        lt = left.split()[-1] if left.split() else ''
        rt = right.split()[0] if right.split() else ''
        if (lt.isascii() and lt.isupper() and len(lt) >= 2) or (rt.isascii() and rt.isupper() and len(rt) >= 2):
            return fallback
    # The collector joins portal headings with " > "; expose only the module name.
    if module:
        value = value.rsplit(' > ', 1)[-1]
    return ' '.join(value.split())[:240] or fallback


def _courses(state, course_ids, remote_to_portal):
    labels = {}
    try:
        with (state / 'catalog/courses.json').open('rb') as handle:
            raw = handle.read(MAX_REGISTRY_BYTES + 1)
        if len(raw) <= MAX_REGISTRY_BYTES:
            registry = json.loads(raw)
            for course in registry.get('courses', []) if isinstance(registry, dict) else []:
                if not isinstance(course, dict) or not isinstance(course.get('url'), str):
                    continue
                url = course['url']
                try:
                    parts = urlsplit(url).path.strip('/').split('/')
                    key = (parts[parts.index('produto-pacote') + 1] if 'produto-pacote' in parts[:-1]
                           else canonical_media_url(url))
                except ValueError:
                    continue
                if (label := _label(course.get('title'), None)) and key in course_ids:
                    labels[key] = label
    except (OSError, ValueError, TypeError):
        pass  # No title registry: browse using neutral course labels.
    # Never fall back to raw course keys (which may themselves be source paths).
    counts = Counter(labels.values())
    final = {key: labels[key] if key in labels and counts[labels[key]] == 1
             else f'{labels.get(key, "Curso sem título")} ({i})'
             for i, key in enumerate(sorted(course_ids), 1)}
    # A recovered remote course is an alias of its canonical portal course: inherit
    # that course's final label so the frontend groups them together, not apart.
    for key in course_ids:
        if key.casefold().startswith('remote:') and key in remote_to_portal:
            portal = remote_to_portal[key]
            if portal in final:
                final[key] = final[portal]
    return final


def _status(row, excluded, now):
    if row['media_type'] == 'not_launched':
        return 'not_released'
    if row['media_type'] != 'video':
        return 'unavailable'
    if row['job_state'] == 'review':
        return 'review'
    if not row['has_source']:
        return 'unavailable'
    if row['approved']:
        return 'validated'
    if row['job_state'] == 'leased' and row['lease_until'] is not None and row['lease_until'] > now:
        return 'processing'
    if (row['job_state'] in ('queued', 'leased')
            and row['attempts'] < row['max_attempts']
            and discipline_for(row['subject'], row['front'], row['module']) not in excluded):
        return 'queued'
    return 'unavailable'


def _number(value):
    return isinstance(value, (int, float)) and math.isfinite(value) and value >= 0


def _project(row, courses, excluded, now, recovered):
    lid = row['lesson_id']
    remote = row['course_id'].casefold().startswith('remote:')
    # Remote-only ingest derives its subject, module and title from private folders/files.
    # A verified recovery record means canonical portal metadata was backfilled into the
    # row; only still-unrecovered remote lessons keep neutral labels.
    masked = remote and lid not in recovered
    return {'id': lid, 'course': courses[row['course_id']],
            'subject': 'Sem disciplina' if masked else _label(row['subject'], 'Sem disciplina'),
            'module': 'Sem módulo' if masked else _label(row['module'], 'Sem módulo', module=True),
            'title': f'Aula {lid[-8:]}' if masked else _label(row['title'], 'Aula sem título', allow_slash=True),
            'status': _status(row, excluded, now),
            'duration_s': row['duration_s'] if _number(row['duration_s']) else None}


def _segments(db, row):
    key = (row['lesson_id'], row['version'])
    where = ' FROM transcript_segments WHERE lesson_id=? AND version=?'
    count, size = db.execute('SELECT count(*), sum(length(CAST(text AS BLOB)))' + where, key).fetchone()
    if not (0 < count <= MAX_SEGMENTS and size is not None and size <= MAX_TRANSCRIPT_BYTES):
        raise ValueError('transcript exceeds read budget')
    segments = []
    for start, end, text in db.execute('SELECT start, end, text' + where + ' ORDER BY idx', key):
        if not (_number(start) and _number(end) and start <= end and isinstance(text, str) and text.strip()):
            raise ValueError('invalid segment')
        segments.append({'start_s': start, 'end_s': end, 'text': text})
    return segments


def read(state, lesson_id=None):
    deadline = time.monotonic() + 2
    uri = (state / 'hub.sqlite3').resolve().as_uri() + '?mode=ro'
    with closing(sqlite3.connect(uri, uri=True, timeout=.25)) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        db.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
        db.execute('BEGIN')
        excluded = {r[0] for r in db.execute('SELECT discipline FROM transcription_discipline_exclusions')} if db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='transcription_discipline_exclusions'").fetchone() else set()
        recovered, remote_to_portal = set(), {}
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='lesson_metadata_recovery'").fetchone():
            for r in db.execute('SELECT lesson_id, remote_course_id, canonical_course_id, action FROM lesson_metadata_recovery'):
                if r['action'] == 'backfill_protected':
                    recovered.add(r['lesson_id'])
                if r['remote_course_id'] and r['canonical_course_id']:
                    remote_to_portal[r['remote_course_id']] = r['canonical_course_id']
        course_ids = {r[0] for r in db.execute('SELECT DISTINCT course_id FROM lessons WHERE present=1 LIMIT ?',
                                              (MAX_LESSONS + 1,))}
        if len(course_ids) > MAX_LESSONS:
            raise ValueError('course limit exceeded')
        courses = _courses(state, course_ids, remote_to_portal)
        now = time.time()
        catalog = _CATALOG.format(approval=transcript_approval(db))
        if lesson_id is not None:
            row = db.execute(catalog + ' AND l.lesson_id=?', (lesson_id,)).fetchone()
            if row is None:
                return None
            lesson = _project(row, courses, excluded, now, recovered)
            return {'lesson': lesson, 'segments': _segments(db, row) if lesson['status'] == 'validated' else []}
        rows = db.execute(catalog + ' ORDER BY l.lesson_id LIMIT ?', (MAX_LESSONS + 1,)).fetchall()
        if len(rows) > MAX_LESSONS:
            raise ValueError('lesson limit exceeded')
        return {'lessons': [_project(row, courses, excluded, now, recovered) for row in rows if LESSON_ID.fullmatch(row['lesson_id'])]}
