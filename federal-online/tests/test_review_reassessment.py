"""Reassess saved inference; no downloader/decoder, preserve original review."""
import gzip
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fo_hub.worker import Worker, atomic_json, parse_whisper
from fo_hub.transcription import qa_segments
from fo_hub.store import ACCEPTED_CORPUS
from test_worker import setup


def fixture(tmp_path):
    store, lesson, cfg = setup(tmp_path)
    worker = Worker(cfg, store=store, gate_fn=lambda: {'allowed': True},
                    runner=lambda *a, **k: pytest.fail('reassessment must not decode/download'))
    source = 'onedrive:Federal Online/a.mp4'
    store.conn.execute('INSERT INTO lesson_video_sources VALUES(?,?,?,?,?,?)',
                       (lesson['lesson_id'], source, '1', 9, 1, 'now'))
    store.conn.execute("UPDATE transcription_jobs SET state='review',attempts=1")
    store.conn.commit()
    raw = {'transcription': [
        {'offsets': {'from': 0, 'to': 15000}, 'text': 'Primeira explicação.'},
        {'offsets': {'from': 14800, 'to': 30000}, 'text': 'Continuação.'}]}
    segments = parse_whisper(raw)
    artifact = {'lesson_id': lesson['lesson_id'], 'version': 1, 'corpus': ACCEPTED_CORPUS,
                'model': 'whisper-large-v3', 'source_sha256': hashlib.sha256(b'fakevideo').hexdigest(),
                'source_size': 9, 'source_revision': '1', 'source_remote_path': source,
                'duration_s': 30, 'qa_policy_version': 3, 'qa': qa_segments(segments, 30),
                'segments': segments, 'chunks': [{'offset_s': 0, 'duration_s': 30,
                  'raw': raw, 'segments': segments, 'silence': []}]}
    path = tmp_path/'transcripts/review'/lesson['lesson_id']/'v1.json.gz'
    atomic_json(path, artifact)
    return worker, store, lesson, path, artifact


def test_saved_review_reassessed_and_published_without_asr_or_evidence_loss(tmp_path):
    worker, store, lesson, path, artifact = fixture(tmp_path)
    before = path.read_bytes()
    result = worker.reassess_review(lesson['lesson_id'])
    assert result['state'] == 'validated'
    assert path.read_bytes() == before
    transcript = store.get_transcript(lesson['lesson_id'])
    assert transcript['qa']['warnings'] and not transcript['qa']['blockers']
    assert [{k: r[k] for k in ('start', 'end', 'text')} for r in transcript['segments']] == artifact['segments']
    assert store.conn.execute('SELECT state,attempts FROM transcription_jobs').fetchone()[:] == ('done', 1)
    assert result['input_sha256'] == hashlib.sha256(before).hexdigest()
    assert worker.reassess_review(lesson['lesson_id'])['state'] == 'already_validated'


@pytest.mark.parametrize('corruption', ['source', 'segments', 'raw', 'corpus'])
def test_incompatible_or_changed_saved_artifact_never_published(tmp_path, corruption):
    worker, store, lesson, path, artifact = fixture(tmp_path)
    if corruption == 'source':
        store.conn.execute('UPDATE lesson_video_sources SET size=10'); store.conn.commit()
    elif corruption == 'segments':
        artifact['segments'][0]['text'] = 'changed final text'
    elif corruption == 'raw':
        artifact['chunks'][0]['raw']['transcription'][0]['text'] = 'changed raw'
    else:
        artifact['corpus'] = 'legacy'
    atomic_json(path, artifact)
    with pytest.raises((ValueError, RuntimeError)):
        worker.reassess_review(lesson['lesson_id'])
    assert store.get_transcript(lesson['lesson_id']) is None
    assert store.conn.execute('SELECT state FROM transcription_jobs').fetchone()[0] == 'review'


def test_additional_language_defect_keeps_saved_review_private(tmp_path):
    worker, store, lesson, path, artifact = fixture(tmp_path)
    result = worker.reassess_review(lesson['lesson_id'], extra_flags=[{'kind': 'language_mismatch'}])
    assert result['state'] == 'review'
    assert store.get_transcript(lesson['lesson_id']) is None
    assert path.is_file()
    reassessed = json.loads(gzip.decompress(Path(result['artifact']).read_bytes()))
    assert reassessed['qa']['blockers'][0]['kind'] == 'language_mismatch'
