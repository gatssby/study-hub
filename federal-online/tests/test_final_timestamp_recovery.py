"""Evidence-bound final-timestamp recovery: clamp synthetic decoder padding only."""
import gzip
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fo_hub.worker import Worker, atomic_json, parse_whisper, normalize_final_padding, resolved_timestamp_flags
from fo_hub.stitching import stitch_chunks
from fo_hub.transcription import qa_segments, QA_POLICY_VERSION
from fo_hub.store import ACCEPTED_CORPUS
from test_worker import setup


def _worker(tmp_path):
    store, lesson, cfg = setup(tmp_path)
    worker = Worker(cfg, store=store, gate_fn=lambda: {'allowed': True},
                    runner=lambda *a, **k: pytest.fail('recovery must not decode/download'))
    source = 'onedrive:Federal Online/a.mp4'
    store.conn.execute('INSERT INTO lesson_video_sources VALUES(?,?,?,?,?,?)',
                       (lesson['lesson_id'], source, '1', 9, 1, 'now'))
    store.conn.execute("UPDATE transcription_jobs SET state='review',attempts=1")
    store.conn.commit()
    return worker, store, lesson, source


def _artifact(lesson, source, raw, duration):
    segments = parse_whisper(raw)
    chunks = [{'offset_s': 0, 'duration_s': duration, 'raw': raw, 'segments': segments, 'silence': []}]
    return {'lesson_id': lesson['lesson_id'], 'version': 1, 'corpus': ACCEPTED_CORPUS,
            'model': 'whisper-large-v3', 'source_sha256': hashlib.sha256(b'fakevideo').hexdigest(),
            'source_size': 9, 'source_revision': '1', 'source_remote_path': source,
            'duration_s': duration, 'qa_policy_version': 4, 'qa': qa_segments(segments, duration),
            'segments': segments, 'chunks': chunks}


def _save(tmp_path, lesson, artifact):
    path = tmp_path / 'transcripts/review' / lesson['lesson_id'] / 'v1.json.gz'
    atomic_json(path, artifact)
    return path


PADDED_RAW = {'transcription': [
    {'offsets': {'from': 0, 'to': 15000}, 'text': 'Primeira explicação.'},
    {'offsets': {'from': 14800, 'to': 45000}, 'text': 'Continuação.'}]}  # end 45s > 30s audio


def test_padding_only_review_is_recovered_and_published(tmp_path):
    worker, store, lesson, source = _worker(tmp_path)
    artifact = _artifact(lesson, source, PADDED_RAW, 30)
    assert any(f['kind'] == 'bad_timestamp' for f in artifact['qa']['flags'])
    path = _save(tmp_path, lesson, artifact)
    before = path.read_bytes()
    result = worker.reassess_review(lesson['lesson_id'])
    assert result['state'] == 'validated'
    assert path.read_bytes() == before  # original evidence immutable
    transcript = store.get_transcript(lesson['lesson_id'])
    segs = transcript['segments']
    assert segs[-1]['end'] == 30 and segs[-1]['text'] == 'Continuação.'  # clamped, text intact
    assert {k: segs[0][k] for k in ('start', 'end', 'text')} == {'start': 0.0, 'end': 15.0, 'text': 'Primeira explicação.'}
    assert not transcript['qa']['blockers']
    obs = [o for o in transcript['qa'].get('observations', []) if o['kind'] == 'timestamp_correction']
    assert obs and obs[0]['raw_end'] == 45.0 and obs[0]['corrected_end'] == 30
    assert obs[0]['resolved_flags'] and all(f['kind'] == 'bad_timestamp' for f in obs[0]['resolved_flags'])
    assert store.conn.execute('SELECT state FROM transcription_jobs').fetchone()[0] == 'done'
    assert result['input_sha256'] == hashlib.sha256(before).hexdigest()


def test_padding_plus_repetition_stays_in_review(tmp_path):
    worker, store, lesson, source = _worker(tmp_path)
    artifact = _artifact(lesson, source, PADDED_RAW, 30)
    path = _save(tmp_path, lesson, artifact)
    result = worker.reassess_review(lesson['lesson_id'],
                                    extra_flags=[{'kind': 'ngram_repetition', 'idx': 1, 'phrase': 'x y z'}])
    assert result['state'] == 'review'
    assert store.get_transcript(lesson['lesson_id']) is None
    reassessed = json.loads(gzip.decompress(Path(result['artifact']).read_bytes()))
    kinds = {f['kind'] for f in reassessed['qa']['blockers']}
    assert 'ngram_repetition' in kinds and 'bad_timestamp' not in kinds  # padding resolved, repetition retained
    assert any(o['kind'] == 'timestamp_correction' for o in reassessed['qa']['observations'])


def test_no_padding_defect_is_unchanged(tmp_path):
    worker, store, lesson, source = _worker(tmp_path)
    raw = {'transcription': [{'offsets': {'from': 0, 'to': 15000}, 'text': 'A.'},
                             {'offsets': {'from': 14800, 'to': 30000}, 'text': 'B.'}]}
    artifact = _artifact(lesson, source, raw, 30)
    path = _save(tmp_path, lesson, artifact)
    result = worker.reassess_review(lesson['lesson_id'])
    assert result['state'] == 'validated'
    reassessed = json.loads(gzip.decompress(Path(result['artifact']).read_bytes()))
    assert not any(o['kind'] == 'timestamp_correction' for o in reassessed['qa'].get('observations', []))
    assert reassessed['segments'][-1]['end'] == 30.0


def test_normalize_final_padding_unit():
    raw = PADDED_RAW
    segments = parse_whisper(raw)
    chunks = [{'offset_s': 0, 'duration_s': 30, 'raw': raw, 'segments': segments, 'silence': []}]
    nc, ns, corr = normalize_final_padding(chunks, segments, 30)
    assert corr and ns[-1]['end'] == 30 and nc[0]['segments'][-1]['end'] == 30
    assert segments[-1]['end'] == 45.0  # original untouched
    assert ns[-1]['text'] == segments[-1]['text']
    # no defect when end within bound
    ok = parse_whisper({'transcription': [{'offsets': {'from': 0, 'to': 29000}, 'text': 'A.'}]})
    c2 = [{'offset_s': 0, 'duration_s': 30, 'raw': {}, 'segments': ok, 'silence': []}]
    assert normalize_final_padding(c2, ok, 30)[2] is None
    # speech starting beyond audio is not corrected
    bad = parse_whisper({'transcription': [{'offsets': {'from': 31000, 'to': 61000}, 'text': 'A.'}]})
    c3 = [{'offset_s': 0, 'duration_s': 30, 'raw': {}, 'segments': bad, 'silence': []}]
    assert normalize_final_padding(c3, bad, 30)[2] is None


def test_resolved_timestamp_flags_keeps_earlier_defects():
    correction = {'idx': 5, 'chunk_idx': 1, 'local_idx': 2}
    qa = {'flags': [
        {'kind': 'bad_timestamp', 'idx': 5, 'origin': 'stitched_text'},
        {'kind': 'bad_timestamp', 'idx': 2, 'origin': 'decoder', 'chunk_idx': 1},
        {'kind': 'bad_timestamp', 'idx': 2, 'origin': 'decoder', 'chunk_idx': 0},  # earlier chunk: keep
        {'kind': 'bad_timestamp', 'idx': 3, 'origin': 'stitched_text'},  # earlier global: keep
        {'kind': 'ngram_repetition', 'idx': 5},  # repetition: keep
    ]}
    kept, resolved = resolved_timestamp_flags(qa, correction)
    assert len(resolved) == 2
    assert {(f['origin'], f['idx']) for f in resolved} == {('stitched_text', 5), ('decoder', 2)}
    assert len(kept) == 3
    assert QA_POLICY_VERSION == 5
