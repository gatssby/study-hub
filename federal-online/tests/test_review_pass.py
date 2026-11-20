"""Bounded automatic review pass: evidence-only, deterministic skips, cooldowns.

No subprocess may run: the pass reuses saved artifacts exactly like
``reassess_review`` and never downloads or decodes.
"""
import gzip
import hashlib
import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fo_hub.worker import Worker, atomic_json, parse_whisper
from fo_hub.transcription import qa_segments, QA_POLICY_VERSION, TranscriptionQueue
from fo_hub.store import ACCEPTED_CORPUS
from test_worker import setup

RECOVERABLE = [(0, 15000, 'Primeira explicação.'), (14800, 30000, 'Continuação.')]
BLOCKING = [(0, 15000, 'Primeira explicação.'), (10000, 30000, 'Continuação.')]


def make_worker(tmp_path, store):
    from fo_hub.worker import Config
    cfg = Config(state=tmp_path, db=tmp_path/'hub.db', binary=tmp_path/'whisper-cli',
                 model=tmp_path/'large-v3.bin', auth=tmp_path/'auth', marker=tmp_path/'marker')
    return Worker(cfg, store=store, gate_fn=lambda: {'allowed': True},
                  runner=lambda *a, **k: pytest.fail('review pass must not decode/download'))


def write_review(store, tmp_path, lesson, rows, duration=30):
    """Persist a current-version review job with intact saved inference."""
    lid = lesson['lesson_id']
    source = 'onedrive:Federal Online/' + lid + '.mp4'
    store.conn.execute('INSERT OR REPLACE INTO lesson_video_sources VALUES(?,?,?,?,?,?)',
                       (lid, source, str(lesson['version']), 9, 1, 'now'))
    store.conn.execute("UPDATE transcription_jobs SET state='review',attempts=1,updated_at=? "
                       'WHERE lesson_id=? AND version=?', (str(time.time()), lid, lesson['version']))
    store.conn.commit()
    raw = {'transcription': [{'offsets': {'from': a, 'to': b}, 'text': t} for a, b, t in rows]}
    segments = parse_whisper(raw)
    artifact = {'lesson_id': lid, 'version': lesson['version'], 'corpus': ACCEPTED_CORPUS,
                'model': 'whisper-large-v3', 'source_sha256': hashlib.sha256(b'fakevideo').hexdigest(),
                'source_size': 9, 'source_revision': str(lesson['version']), 'source_remote_path': source,
                'duration_s': duration, 'qa_policy_version': 3, 'qa': qa_segments(segments, duration),
                'segments': segments, 'chunks': [{'offset_s': 0, 'duration_s': duration,
                  'raw': raw, 'segments': segments, 'silence': []}]}
    path = tmp_path/'transcripts/review'/lid/f"v{lesson['version']}.json.gz"
    atomic_json(path, artifact)
    return path


def add_lesson(store, media_id, subject=None):
    store.sync_lessons([{'course_id': 'c', 'media_id': media_id, 'title': 'Aula ' + media_id,
                         'media_type': 'video', 'duration_s': 30, 'subject': subject}])
    lesson = next(l for l in store.list_lessons(limit=1000) if l['media_id'] == media_id)
    TranscriptionQueue(store).enqueue(lesson['lesson_id'], 1)
    return lesson


def log_row(store, lid, version=1):
    return store.conn.execute('SELECT * FROM transcription_review_log WHERE lesson_id=? AND version=?',
                              (lid, version)).fetchone()


def test_pass_publishes_recoverable_review_and_records_outcome(tmp_path):
    store, lesson, cfg = setup(tmp_path)
    worker = make_worker(tmp_path, store)
    path = write_review(store, tmp_path, lesson, RECOVERABLE)
    before = path.read_bytes()
    result = worker.review_pass()
    assert result['processed'] == [{'lesson_id': lesson['lesson_id'], 'version': 1, 'outcome': 'validated'}]
    assert path.read_bytes() == before  # original review stays immutable
    assert store.get_transcript(lesson['lesson_id']) is not None
    assert store.conn.execute('SELECT state FROM transcription_jobs').fetchone()[0] == 'done'
    row = log_row(store, lesson['lesson_id'])
    assert row['outcome'] == 'validated'
    assert row['input_sha256'] == hashlib.sha256(before).hexdigest()
    assert row['policy_version'] == QA_POLICY_VERSION
    assert worker.review_pass()['processed'] == []  # nothing left to reassess


def test_unchanged_blocking_review_is_reassessed_once_then_skipped(tmp_path):
    store, lesson, cfg = setup(tmp_path)
    worker = make_worker(tmp_path, store)
    write_review(store, tmp_path, lesson, BLOCKING)
    assert worker.review_pass()['processed'] == [
        {'lesson_id': lesson['lesson_id'], 'version': 1, 'outcome': 'review'}]
    receipt = tmp_path/'transcripts/review'/lesson['lesson_id']/f'v1.qa-v{QA_POLICY_VERSION}.json.gz'
    assert receipt.is_file()
    snapshot = (receipt.stat().st_mtime_ns, receipt.read_bytes())
    assert store.conn.execute('SELECT state FROM transcription_jobs').fetchone()[0] == 'review'
    assert store.get_transcript(lesson['lesson_id']) is None
    assert worker.review_pass()['processed'] == []
    assert (receipt.stat().st_mtime_ns, receipt.read_bytes()) == snapshot
    assert log_row(store, lesson['lesson_id'])['attempts'] == 1


def test_excluded_discipline_reviews_are_preserved_without_reassessment(tmp_path):
    store, lesson, cfg = setup(tmp_path)
    worker = make_worker(tmp_path, store)
    store.conn.execute("UPDATE lessons SET subject='Inglês' WHERE lesson_id=?", (lesson['lesson_id'],))
    store.conn.commit()
    worker.exclude_discipline('Inglês', 'owner_authorized_exact_exclusion')
    write_review(store, tmp_path, store.get_lesson(lesson['lesson_id']), RECOVERABLE)
    assert worker.review_pass()['processed'] == []
    assert log_row(store, lesson['lesson_id']) is None
    assert not (tmp_path/'transcripts/review'/lesson['lesson_id']/f'v1.qa-v{QA_POLICY_VERSION}.json.gz').exists()
    assert store.conn.execute('SELECT state FROM transcription_jobs').fetchone()[0] == 'review'


def test_missing_artifact_errors_back_off_and_stop_after_attempt_limit(tmp_path):
    store, lesson, cfg = setup(tmp_path)
    worker = make_worker(tmp_path, store)
    store.conn.execute('INSERT OR REPLACE INTO lesson_video_sources VALUES(?,?,?,?,?,?)',
                       (lesson['lesson_id'], 'onedrive:Federal Online/a.mp4', '1', 9, 1, 'now'))
    store.conn.execute("UPDATE transcription_jobs SET state='review',attempts=1")
    store.conn.commit()
    first = worker.review_pass(now=1000.0)['processed']
    assert first == [{'lesson_id': lesson['lesson_id'], 'version': 1,
                      'outcome': 'error', 'detail': 'FileNotFoundError'}]
    assert log_row(store, lesson['lesson_id'])['attempts'] == 1
    assert worker.review_pass(now=1000.0 + 3600)['processed'] == []  # cooldown
    assert worker.review_pass(now=1000.0 + 86401)['processed'][0]['outcome'] == 'error'
    assert log_row(store, lesson['lesson_id'])['attempts'] == 2
    assert worker.review_pass(now=1000.0 + 2 * 86402)['processed'][0]['outcome'] == 'error'
    assert log_row(store, lesson['lesson_id'])['attempts'] == 3
    assert worker.review_pass(now=1000.0 + 3 * 86403)['processed'] == []  # attempt limit
    assert store.conn.execute('SELECT state FROM transcription_jobs').fetchone()[0] == 'review'


def test_policy_upgrade_reprocesses_an_unchanged_blocking_review(tmp_path):
    store, lesson, cfg = setup(tmp_path)
    worker = make_worker(tmp_path, store)
    write_review(store, tmp_path, lesson, BLOCKING)
    worker.review_pass()
    store.conn.execute('UPDATE transcription_review_log SET policy_version=? WHERE lesson_id=?',
                       (QA_POLICY_VERSION - 1, lesson['lesson_id']))
    store.conn.commit()
    assert worker.review_pass()['processed'][0]['outcome'] == 'review'
    assert log_row(store, lesson['lesson_id'])['policy_version'] == QA_POLICY_VERSION


def test_changed_input_identity_reprocesses_a_review(tmp_path):
    store, lesson, cfg = setup(tmp_path)
    worker = make_worker(tmp_path, store)
    write_review(store, tmp_path, lesson, BLOCKING)
    worker.review_pass()
    store.conn.execute("UPDATE transcription_review_log SET input_sha256=? WHERE lesson_id=?",
                       ('0' * 64, lesson['lesson_id']))
    store.conn.commit()
    assert worker.review_pass()['processed'][0]['outcome'] == 'review'
    assert log_row(store, lesson['lesson_id'])['input_sha256'] != '0' * 64


def test_pass_respects_its_budget_and_resumes_next_pass(tmp_path):
    store, lesson, cfg = setup(tmp_path)
    worker = make_worker(tmp_path, store)
    write_review(store, tmp_path, lesson, RECOVERABLE)
    others = [add_lesson(store, 'm2'), add_lesson(store, 'm3')]
    for other in others:
        write_review(store, tmp_path, other, RECOVERABLE)
    first = worker.review_pass(limit=2)['processed']
    assert len(first) == 2 and all(r['outcome'] == 'validated' for r in first)
    remaining = store.conn.execute("SELECT COUNT(*) FROM transcription_jobs WHERE state='review'").fetchone()[0]
    assert remaining == 1
    second = worker.review_pass(limit=2)['processed']
    assert len(second) == 1 and second[0]['outcome'] == 'validated'
    assert store.conn.execute("SELECT COUNT(*) FROM transcription_jobs WHERE state='review'").fetchone()[0] == 0


def test_pass_never_changes_the_circuit_breaker(tmp_path):
    store, lesson, cfg = setup(tmp_path)
    worker = make_worker(tmp_path, store)
    store.conn.execute('INSERT INTO transcription_breaker VALUES(?,?,?,?,?)',
                       ('fp', 0, 4, None, None))
    store.conn.commit()
    write_review(store, tmp_path, lesson, RECOVERABLE)
    assert worker.review_pass()['processed'][0]['outcome'] == 'validated'
    row = store.conn.execute('SELECT * FROM transcription_breaker WHERE fingerprint="fp"').fetchone()
    assert tuple(row) == ('fp', 0, 4, None, None)


def test_superseded_review_versions_are_not_selected(tmp_path):
    store, lesson, cfg = setup(tmp_path)
    worker = make_worker(tmp_path, store)
    write_review(store, tmp_path, lesson, RECOVERABLE)
    # A media change advances the lesson version; the old review is historical.
    store.sync_lessons([{'course_id': 'c', 'media_id': 'm', 'title': 'Aula',
                         'media_type': 'video', 'duration_s': 45}])
    assert store.get_lesson(lesson['lesson_id'])['version'] == 2
    assert worker.review_pass()['processed'] == []
    assert log_row(store, lesson['lesson_id']) is None