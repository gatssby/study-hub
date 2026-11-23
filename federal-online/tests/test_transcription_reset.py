import fcntl
import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

from fo_hub.ingest import ingest, observe_video_source
from fo_hub.store import ACCEPTED_CORPUS, FOStore, TranscriptRejected, lesson_id_for
from fo_hub.transcription import LeaseLost, TranscriptionQueue, db_worker_lock, valid_source


PREFIX = 'onedrive:Federal Online/'
TEXT = [{'start': 0, 'end': 1, 'text': 'texto aprovado'}]


def add_video(store, media, *, course='portal', subject='Direito', path=None,
              revision='1', size=12, available=1):
    lid = lesson_id_for(course, media, None)
    store.sync_lessons([dict(course_id=course, media_id=media, subject=subject,
                             title=media, media_type='video')])
    with store.conn:
        store.conn.execute('INSERT INTO lesson_video_sources VALUES(?,?,?,?,?,?)',
                           (lid, path or PREFIX + f'{media}.mp4', revision, size, available, 'same'))
        store.conn.execute('INSERT INTO lesson_source_observations VALUES(?,?,?,?,?)',
                           (lid, path or PREFIX + f'{media}.mp4', json.dumps({'Size': size, 'ID': 'fixture',
                            'ModTime': 'known'}), 1, 'same'))
    return lid


@pytest.fixture
def case(tmp_path):
    store = FOStore(tmp_path / 'hub.sqlite3')
    store.conn.executescript('''
        CREATE TABLE lesson_video_sources(lesson_id TEXT PRIMARY KEY, remote_path TEXT,
            revision TEXT, size INTEGER, available INTEGER, checked_at TEXT);
        CREATE TABLE lesson_source_observations(lesson_id TEXT,remote_path TEXT,metadata TEXT,
            version INTEGER,checked_at TEXT,PRIMARY KEY(lesson_id,remote_path));
        CREATE TABLE transcription_discipline_exclusions(discipline TEXT PRIMARY KEY);
        INSERT INTO transcription_discipline_exclusions VALUES ('Inglês'), ('Espanhol');
        CREATE TABLE transcription_source_deferrals(lesson_id TEXT, version INTEGER,
            remote_path TEXT, size INTEGER, reason TEXT, retry_after REAL, observed_at REAL,
            PRIMARY KEY(lesson_id,version));
        CREATE TABLE transcription_review_log(sample TEXT);
        INSERT INTO transcription_review_log VALUES ('old derivative');
        CREATE TABLE unrelated(sample TEXT);
        INSERT INTO unrelated VALUES ('never delete');
        INSERT INTO pdf_pages VALUES ('sample', 1, 'pdf preserved');
    ''')
    return store, tmp_path


def run_reset(store, state, *args, rows=None):
    if rows is None:
        rows = [{'Path': path.removeprefix(PREFIX), 'Size': size, 'ID': 'fixture', 'ModTime': 'known',
                 'Hashes': {'quickxor': 'a'*40}} for path, size in store.conn.execute(
                    'SELECT DISTINCT remote_path,size FROM lesson_video_sources') if valid_source(path, size)]
    inventory = state / 'reset-inventory.json'
    inventory.write_text(json.dumps({'rows': rows, 'started_at': time.time(), 'finished_at': time.time()}))
    return subprocess.run([sys.executable, '-m', 'fo_hub.transcription', '--reset',
                           '--db', str(store.path), '--state-root', str(state), '--inventory', str(inventory),
                           *args],
                          cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True)


def test_reset_allowlist_reseeds_exact_sources_preserves_catalogue_and_shared_state(case):
    store, state = case
    lid = add_video(store, 'ok')
    alias = add_video(store, 'alias', course='remote:archive', path=PREFIX + 'ok.mp4')
    add_video(store, 'english', subject='Inglês - Teoria')
    add_video(store, 'spanish', subject='Espanhol')
    add_video(store, 'badpath', path=PREFIX + 'bad/../badpath.mp4')
    add_video(store, 'missing', available=0)
    add_video(store, 'wrong-revision', revision='2')
    add_video(store, 'empty', size=0)
    with store.conn:
        store.conn.executemany('INSERT INTO transcription_jobs(lesson_id,version,state) VALUES (?,?,?)',
                               [(lid, 1, 'done'), (lid, 2, 'review'), (alias, 1, 'leased')])
        store.conn.execute('INSERT INTO transcription_source_deferrals VALUES(?,?,?,?,?,?,?)',
                           (lid, 1, PREFIX + 'ok.mp4', 12, 'hls_404', 99999999999, 99))
    store.add_transcript(lid, 1, TEXT, 'old', 'generated_v2', True)
    preserved = ('lessons', 'lesson_revisions', 'lesson_video_sources', 'pdf_pages', 'unrelated',
                 'transcription_source_deferrals', 'transcription_discipline_exclusions')
    before = {table: store.conn.execute(f'SELECT * FROM {table}').fetchall() for table in preserved}
    dry = run_reset(store, state)
    assert dry.returncode == 0, dry.stderr
    assert json.loads(dry.stdout)['applied'] is False
    assert store.get_transcript(lid)
    applied = run_reset(store, state, '--confirm-reset')
    assert applied.returncode == 0, applied.stderr
    assert json.loads(applied.stdout)['applied'] is True
    assert json.loads(applied.stdout)['hash_bindings'] == 1
    assert json.loads(store.conn.execute('SELECT metadata FROM lesson_source_observations '
                                         'WHERE lesson_id=?', (lid,)).fetchone()[0])['QuickXorHash'] == 'a'*40
    assert all(before[t] == store.conn.execute(f'SELECT * FROM {t}').fetchall() for t in preserved)
    assert [tuple(r) for r in store.conn.execute('SELECT lesson_id,version,state,attempts FROM transcription_jobs')] == [(lid, 1, 'queued', 0)]
    for table in ('transcripts', 'transcript_segments', 'transcription_review_log'):
        assert store.conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == 0
    assert store.get_transcript(lid) is None
    assert TranscriptionQueue(store).lease('worker') is None  # shared deferral still active
    with pytest.raises(TranscriptRejected):
        store.add_transcript(lid, 1, TEXT, 'old', 'generated_v2', True)
    assert store.conn.execute('PRAGMA quick_check').fetchone()[0] == 'ok'


def test_reset_refuses_active_worker_lock(case):
    store, state = case
    add_video(store, 'ok')
    (state / 'locks').mkdir()
    with (state / 'locks' / 'transcription-worker.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = run_reset(store, state, '--confirm-reset')
    assert result.returncode != 0
    assert 'lock' in result.stderr.lower()
    assert store.conn.execute('SELECT COUNT(*) FROM transcription_jobs').fetchone()[0] == 0


def test_reset_refuses_same_db_worker_across_state_roots(case):
    store, state = case
    add_video(store, 'ok')
    with db_worker_lock(store.path):
        result = run_reset(store, state, '--confirm-reset')
    assert result.returncode != 0
    assert store.conn.execute('SELECT COUNT(*) FROM transcription_jobs').fetchone()[0] == 0


def test_reset_without_inventory_proof_keeps_legacy_rows(case):
    store, state = case
    lid = add_video(store, 'ok')
    store.add_transcript(lid, 1, TEXT, 'old', 'generated_v2', True)
    result = run_reset(store, state, '--confirm-reset', rows=[])
    assert result.returncode == 2 and 'lack matching fresh inventory proof' in result.stderr
    assert store.get_transcript(lid)


def test_reset_cannot_repeat_after_mvp_publication(case):
    store, state = case
    lid = add_video(store, 'ok')
    assert run_reset(store, state, '--confirm-reset').returncode == 0
    queue = TranscriptionQueue(store)
    job = queue.lease('worker')
    queue.finish(job, 'worker', TEXT, {'passed': True}, job)

    repeat = run_reset(store, state, '--confirm-reset')
    assert repeat.returncode != 0
    assert 'already applied' in repeat.stderr
    assert store.get_transcript(lid)
    assert queue.counts() == {'done': 1}


def test_malformed_reset_marker_cannot_silently_suppress_reset_receipt(case):
    store, state = case
    lid = add_video(store, 'ok')
    store.add_transcript(lid, 1, TEXT, 'old', 'generated_v2', True)
    store.conn.execute('CREATE TRIGGER ignore_reset BEFORE INSERT ON transcription_mvp_reset '
                       'BEGIN SELECT RAISE(IGNORE); END;')

    result = run_reset(store, state, '--confirm-reset')
    assert result.returncode != 0
    assert 'unexpected triggers' in result.stderr
    assert store.get_transcript(lid)


@pytest.mark.parametrize('field,value', [('remote_path', PREFIX+'different.mp4'), ('size', 13),
                                        ('revision', '2'), ('available', 0)])
def test_publish_and_serve_guard_source_identity(case, field, value):
    store, _ = case
    lid = add_video(store, 'ok')
    queue = TranscriptionQueue(store)
    job = queue.lease('worker')
    source = {'revision': '1', 'size': 12, 'remote_path': PREFIX+'ok.mp4'}
    other = sqlite3.connect(store.path)
    with other:
        other.execute(f'UPDATE lesson_video_sources SET {field}=?', (value,))
    with pytest.raises((LeaseLost, TranscriptRejected)):
        queue.finish(job, 'worker', TEXT, {'passed': True}, source)
    assert store.conn.execute('SELECT COUNT(*) FROM transcripts').fetchone()[0] == 0
    with other:
        other.execute('UPDATE lesson_video_sources SET revision=?,size=?,remote_path=?,available=1', tuple(source.values()))
    queue.finish(job, 'worker', TEXT, {'passed': True, 'warnings': [{'text': 'internal'}]}, source)
    assert ACCEPTED_CORPUS == 'whisper_mvp_v1'
    assert tuple(store.conn.execute('SELECT corpus,model FROM transcripts').fetchone()) == (ACCEPTED_CORPUS, 'whisper-large-v3')
    assert store.conn.execute('SELECT state FROM transcription_jobs').fetchone()[0] == 'done'
    api_store = FOStore(store.path, readonly=True)
    assert api_store.get_transcript(lid)['qa'] == {'passed': True}
    assert api_store.search_transcripts('aprovado')
    with other:
        other.execute(f'UPDATE lesson_video_sources SET {field}=?', (value,))
    assert api_store.get_transcript(lid) is None
    assert api_store.search_transcripts('aprovado') == []


def test_publication_rolls_back_if_job_completion_fails(case):
    store, _ = case
    lid = add_video(store, 'ok')
    queue = TranscriptionQueue(store)
    job = queue.lease('worker')
    store.conn.execute("CREATE TRIGGER test_abort BEFORE UPDATE ON transcription_jobs "
                       "WHEN NEW.state='done' BEGIN SELECT RAISE(ABORT,'injected failure'); END;")
    with pytest.raises(sqlite3.IntegrityError, match='injected failure'):
        queue.finish(job, 'worker', TEXT, {'passed': True}, job)
    assert store.get_transcript(lid) is None
    assert store.conn.execute('SELECT COUNT(*) FROM transcript_segments').fetchone()[0] == 0
    assert queue.counts() == {'leased': 1}


@pytest.mark.parametrize('path,size', [(PREFIX+'new.mp4', 12), (PREFIX+'ok.mp4', 13)])
def test_ingest_revision_changes_on_verified_path_or_size_remap(case, path, size):
    store, state = case
    lid = add_video(store, 'ok')
    assert run_reset(store, state, '--confirm-reset').returncode == 0
    queue = TranscriptionQueue(store)
    job = queue.lease('worker')
    queue.finish(job, 'worker', TEXT, {'passed': True}, job)
    observed = observe_video_source(store, lid, path, {'Size': size, 'QuickXorHash': 'c'*40})
    assert observed['version'] == 2
    assert store.get_transcript(lid) is None
    replacement = queue.lease('worker')
    assert replacement is not None
    assert (replacement['lesson_id'], replacement['version']) == (lid, 2)
    assert (replacement['remote_path'], replacement['size']) == (path, size)


def test_ingest_enqueues_new_and_restored_verified_source_only(case):
    store, state = case
    assert run_reset(store, state, '--confirm-reset').returncode == 0
    (state / 'catalog').mkdir()
    (state / 'catalog' / 'aulas_index.json').write_text(json.dumps({'aulas': [
        {'course_url': 'https://portal/produto-pacote/c', 'media_id': 'pending',
         'status': 'ok', 'nome_real_aula': 'Pending', 'video_stream_url': 'https://video/pending'},
    ]}))
    inventory = state / 'remote-videos.json'
    inventory.write_text('[{"Path":"course/subject/video.mp4","Size":12}]')
    ingest(state, store.path, index_pdfs=False)
    q = TranscriptionQueue(store)
    assert q.lease('worker') is None
    hashed_snapshot = json.dumps([{'Path': 'course/subject/video.mp4', 'Size': 12, 'QuickXorHash': 'c'*40}])
    inventory.write_text(hashed_snapshot)
    ingest(state, store.path, index_pdfs=False)
    job = q.lease('worker')
    assert job['remote_path'] == PREFIX+'course/subject/video.mp4'
    assert q.counts() == {'leased': 1}
    assert q.recover() == 1
    inventory.write_text('[]')
    ingest(state, store.path, index_pdfs=False)
    assert q.lease('worker') is None
    inventory.write_text(hashed_snapshot)
    ingest(state, store.path, index_pdfs=False)
    assert q.lease('worker')['lesson_id'] == job['lesson_id']
