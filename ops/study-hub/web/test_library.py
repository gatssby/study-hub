import json
import sqlite3
import time
from contextlib import closing

from production import DashboardApplication
from fo_hub.store import SCHEMA


CASES = (
    ('approved', 'video', 'done', 2, 2, 'generated_v2', '{"passed":true}', 'validated'),
    ('queued', 'video', 'queued', 2, 2, None, None, 'queued'),
    ('processing', 'video', 'leased', 2, 2, None, None, 'processing'),
    ('expired', 'video', 'leased', 2, 2, None, None, 'queued'),
    ('review', 'video', 'review', 2, 2, 'generated_v2', '{"passed":false}', 'review'),
    ('unavailable', 'video', 'queued', 2, None, None, None, 'unavailable'),
    ('unreleased', 'not_launched', 'done', 2, 2, 'generated_v2', '{"passed":true}', 'not_released'),
    ('stale', 'video', 'done', 1, 2, 'generated_v2', '{"passed":true}', 'unavailable'),
    ('old_source', 'video', 'done', 2, 1, 'generated_v2', '{"passed":true}', 'unavailable'),
    ('wrong_corpus', 'video', 'done', 2, 2, 'legacy', '{"passed":true}', 'unavailable'),
    ('numeric', 'video', 'done', 2, 2, 'generated_v2', '{"passed":1}', 'unavailable'),
    ('malformed', 'video', 'done', 2, 2, 'generated_v2', 'invalid', 'unavailable'),
    ('missing', 'video', 'done', 2, 2, 'generated_v2', '{"passed":true}', None),
    ('remote', 'video', 'done', 2, 2, 'generated_v2', '{"passed":true}', 'validated'),
    ('excluded', 'video', 'queued', 2, 2, None, None, 'unavailable'),
    ('failed', 'video', 'failed', 2, 2, None, None, 'unavailable'),
    ('empty', 'video', 'done', 2, 2, 'generated_v2', '{"passed":true}', 'unavailable'),
    ('missing_path', 'video', 'done', 2, 2, 'generated_v2', '{"passed":true}', 'unavailable'),
    ('private_relative', 'video', 'done', 2, 2, None, None, 'unavailable'),
    ('exhausted', 'video', 'leased', 2, 2, None, None, 'unavailable'),
    ('review_with_approval', 'video', 'review', 2, 2, 'generated_v2', '{"passed":true}', 'review'),
)
IDS = {case[0]: f'fo_{i:016x}' for i, case in enumerate(CASES)}


def seed(state):
    (state / 'catalog').mkdir()
    (state / 'catalog/courses.json').write_text(json.dumps({'courses': [{
        'url': 'https://example.test/portal/produto-pacote/portal-private-id/2027?secret=hidden',
        'title': 'Curso 2027', 'private': 'INTERNAL',
    }]}))
    with closing(sqlite3.connect(state / 'hub.sqlite3')) as db, db:
        db.executescript(SCHEMA + '''
            CREATE TABLE lesson_video_sources(lesson_id TEXT PRIMARY KEY, remote_path TEXT, revision TEXT,
                size INTEGER, available INTEGER, checked_at TEXT);
            CREATE TABLE transcription_discipline_exclusions(discipline TEXT PRIMARY KEY);
            INSERT INTO transcription_discipline_exclusions VALUES ('Inglês');''')
        for name, media, job, version, source, corpus, qa, _ in CASES:
            lid = IDS[name]
            private = name == 'remote'
            db.execute('''INSERT INTO lessons(lesson_id,course_id,media_id,item_id,subject,front,module,title,
                media_type,video_url,duration_s,version,present) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
                lid, 'remote:INTERNAL' if private else 'portal-private-id', 'PRIVATE_MEDIA', 'PRIVATE_ITEM',
                'INTERNAL_SUBJECT' if private else 'Inglês' if name == 'excluded' else 'Física I',
                'INTERNAL_FRONT', {
                    'remote': 'INTERNAL_MODULE', 'private_relative': 'INTERNAL/PRIVATE_FOLDER',
                    'approved': 'INTERNAL_GROUP > INTERNAL_FRONT > Mecânica',
                }.get(name, 'Mecânica'),
                'INTERNAL_FILENAME' if private else name, media, 'https://example.test/PRIVATE_VIDEO', 65.5, 2,
                int(name != 'missing'),
            ))
            db.execute('INSERT INTO transcription_jobs(lesson_id,version,state,lease_until,last_error) VALUES(?,?,?,?,?)',
                       (lid, 2, job, time.time() + (-120 if name in ('expired', 'exhausted') else 120), 'INTERNAL_ERROR'))
            if name == 'exhausted':
                db.execute('UPDATE transcription_jobs SET attempts=max_attempts WHERE lesson_id=?', (lid,))
            if source is not None:
                db.execute('INSERT INTO lesson_video_sources VALUES(?,?,?,?,?,?)',
                           (lid, None if name == 'missing_path' else 'onedrive:PRIVATE_PATH', str(source), 8, 1, None))
            if corpus:
                db.execute('INSERT INTO transcripts VALUES(?,?,?,?,?,?)', (lid, version, 'INTERNAL_MODEL', corpus, qa, None))
                if name != 'empty':
                    for idx, start, end in [(1, 2.125, 4), (0, 0, 2.125)]:
                        text = f'Texto aprovado {idx}' if name in ('approved', 'remote') else 'PRIVATE_TRANSCRIPT'
                        db.execute('INSERT INTO transcript_segments VALUES(?,?,?,?,?,?)', (lid, version, idx, start, end, text))
        db.execute('INSERT INTO transcript_segments VALUES(?,?,?,?,?,?)',
                   (IDS['approved'], 1, 0, 0, 1, 'PRIVATE_STALE'))


def request(app, path='/api/library', **overrides):
    env = {'REQUEST_METHOD': 'GET', 'PATH_INFO': path, 'RAW_URI': path, 'HTTP_HOST': 'localhost', **overrides}
    response = []
    body = b''.join(app(env, lambda s, h: response.append((int(s.split()[0]), dict(h)))))
    status, headers = response[0]
    assert headers['Cache-Control'] == 'private, no-store'
    assert headers['X-Content-Type-Options'] == 'nosniff'
    return status, json.loads(body)


def test_library_projects_present_lessons_and_exact_states(tmp_path):
    seed(tmp_path)
    before = (tmp_path / 'hub.sqlite3').read_bytes()
    code, payload = request(DashboardApplication(state=tmp_path))
    assert code == 200
    rows = {row['id']: row for row in payload['lessons']}
    assert {key: row['status'] for key, row in rows.items()} == {
        IDS[name]: state for name, *_, state in CASES if state is not None}
    assert rows[IDS['approved']] == {
        'id': IDS['approved'], 'course': 'Curso 2027', 'subject': 'Física I', 'module': 'Mecânica',
        'title': 'approved', 'status': 'validated', 'duration_s': 65.5,
    }
    assert rows[IDS['remote']]['title'].startswith('Aula ')
    assert rows[IDS['private_relative']]['module'] == 'Sem módulo'
    wire = json.dumps(payload)
    for secret in ('Texto aprovado', 'PRIVATE', 'INTERNAL', 'portal-private-id', 'onedrive:', 'https://'):
        assert secret not in wire
    assert (tmp_path / 'hub.sqlite3').read_bytes() == before


def test_only_current_available_approved_segments_are_released(tmp_path):
    seed(tmp_path)
    app = DashboardApplication(state=tmp_path)
    for name, *_, expected in CASES:
        code, body = request(app, f'/api/lessons/{IDS[name]}')
        assert not any(s in json.dumps(body) for s in ('PRIVATE', 'INTERNAL', 'portal-private-id', 'onedrive:'))
        if expected is None:
            assert (code, body) == (404, {'error': 'not_found'})
            continue
        assert code == 200 and body['lesson']['status'] == expected
        assert set(body) == {'lesson', 'segments'}
        assert body['segments'] == ([{'start_s': 0, 'end_s': 2.125, 'text': 'Texto aprovado 0'},
                                     {'start_s': 2.125, 'end_s': 4, 'text': 'Texto aprovado 1'}]
                                    if expected == 'validated' else [])


def test_library_routes_reject_and_missing_source_schema_fails_closed(tmp_path):
    seed(tmp_path)
    app = DashboardApplication(state=tmp_path)
    detail = f'/api/lessons/{IDS["approved"]}'
    for path, overrides, status in [
        (detail, {'REQUEST_METHOD': 'POST'}, 405), (detail, {'QUERY_STRING': 'x=1'}, 400),
        (detail, {'CONTENT_LENGTH': '1'}, 400), (detail, {'HTTP_TRANSFER_ENCODING': 'chunked'}, 400),
        (detail, {'HTTP_ORIGIN': 'https://elsewhere.test'}, 403), (detail, {'HTTP_SEC_FETCH_SITE': 'cross-site'}, 403),
        (detail, {'RAW_URI': detail.replace('fo_', '%66o_')}, 404), (detail + '/', {}, 404),
        ('/api/lessons/not-a-lesson', {}, 404), ('/api/private', {}, 404),
    ]:
        assert request(app, path, **overrides)[0] == status
    with closing(sqlite3.connect(tmp_path / 'hub.sqlite3')) as db, db:
        db.execute('DROP TABLE lesson_video_sources')
    for path in ('/api/library', detail):
        assert request(app, path) == (503, {'error': 'observation_unavailable'})


def test_oversized_or_corrupt_approved_segments_are_not_partially_returned(tmp_path):
    seed(tmp_path)
    app = DashboardApplication(state=tmp_path)
    detail = f'/api/lessons/{IDS["approved"]}'
    with closing(sqlite3.connect(tmp_path / 'hub.sqlite3')) as db, db:
        db.execute('UPDATE transcript_segments SET text=? WHERE lesson_id=? AND version=2',
                   ('x' * (256 * 1024), IDS['approved']))
    assert request(app, detail) == (503, {'error': 'observation_unavailable'})
    with closing(sqlite3.connect(tmp_path / 'hub.sqlite3')) as db, db:
        db.execute('UPDATE transcript_segments SET start=-1, text=? WHERE lesson_id=? AND version=2',
                   ('bad', IDS['approved']))
    assert request(app, detail) == (503, {'error': 'observation_unavailable'})


def test_academic_slash_titles_visible_but_paths_still_masked(tmp_path):
    seed(tmp_path)
    with closing(sqlite3.connect(tmp_path / 'hub.sqlite3')) as db, db:
        db.execute("UPDATE lessons SET title='Prova de 2023/2024' WHERE lesson_id=?", (IDS['approved'],))
        db.execute("UPDATE lessons SET title='Reação de oxidação/redução' WHERE lesson_id=?", (IDS['review'],))
        db.execute("UPDATE lessons SET title='curso/pasta/aula.mp4' WHERE lesson_id=?", (IDS['queued'],))
        db.execute("UPDATE lessons SET title='C:\\privado\\aula.mp4' WHERE lesson_id=?", (IDS['unavailable'],))
    app = DashboardApplication(state=tmp_path)
    rows = {r['id']: r for r in request(app, '/api/library')[1]['lessons']}
    assert rows[IDS['approved']]['title'] == 'Prova de 2023/2024'
    assert rows[IDS['review']]['title'] == 'Reação de oxidação/redução'
    assert rows[IDS['queued']]['title'] == 'Aula sem título'
    assert rows[IDS['unavailable']]['title'] == 'Aula sem título'


def test_recovered_remote_lessons_show_canonical_metadata_and_merge_course(tmp_path):
    seed(tmp_path)
    # A protected remote alias backfilled with canonical portal metadata + a recovery
    # record must project like a portal lesson and inherit the portal course label.
    with closing(sqlite3.connect(tmp_path / 'hub.sqlite3')) as db, db:
        db.execute("UPDATE lessons SET subject='Física', front='Física', module='Física > Vetores', "
                   "title='Vetores IV' WHERE lesson_id=?", (IDS['remote'],))
        db.execute("""CREATE TABLE lesson_metadata_recovery(
            lesson_id TEXT PRIMARY KEY, remote_course_id TEXT, canonical_lesson_id TEXT,
            canonical_course_id TEXT, course_title TEXT, subject TEXT, front TEXT, module TEXT,
            title TEXT, media_id TEXT, action TEXT NOT NULL, evidence_json TEXT NOT NULL,
            preimage_json TEXT NOT NULL, plan_sha256 TEXT NOT NULL,
            policy_version INTEGER NOT NULL DEFAULT 1, recovered_at TEXT NOT NULL)""")
        db.execute("INSERT INTO lesson_metadata_recovery VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (IDS['remote'], 'remote:INTERNAL', IDS['approved'], 'portal-private-id', 'Curso 2027',
                    'Física', 'Física', 'Física > Vetores', 'Vetores IV', '200', 'backfill_protected',
                    '{}', '{}', 'sha', 1, 'now'))
    app = DashboardApplication(state=tmp_path)
    rows = {r['id']: r for r in request(app, '/api/library')[1]['lessons']}
    recovered = rows[IDS['remote']]
    assert recovered['title'] == 'Vetores IV'
    assert recovered['subject'] == 'Física' and recovered['module'] == 'Vetores'
    # inherits the canonical portal course label (groups with it, not a neutral duplicate)
    assert recovered['course'] == rows[IDS['approved']]['course'] == 'Curso 2027'
    assert 'INTERNAL' not in json.dumps(recovered)
