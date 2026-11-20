import gzip
import importlib.util
import json
import sqlite3
from pathlib import Path

root = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location('pipeline_telemetry', root / 'ops/study-hub/pipeline_telemetry.py')
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def artifact(path, lesson, duration, elapsed, created, reused=0, chunks=2):
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {'lesson_id': lesson, 'version': 1, 'model': 'whisper-large-v3', 'duration_s': duration,
            'elapsed_s': elapsed, 'created_at': created, 'qa_policy_version': 4,
            'chunks': [{'reused': i < reused, 'segments': [{'text': 'SECRET'}]} for i in range(chunks)],
            'segments': [{'text': 'SECRET'}], 'qa': {'blockers': [{'kind': 'ngram_repetition', 'start': 5.0, 'end': 9.0}]}}
    path.write_bytes(gzip.compress(json.dumps(body).encode()))


def make_state(tmp_path, samples=6):
    state = tmp_path / 'state'
    state.mkdir()
    db = sqlite3.connect(state / 'hub.sqlite3')
    db.executescript('''CREATE TABLE lessons(lesson_id TEXT, subject TEXT, front TEXT, module TEXT, duration_s REAL, version INT, present INT);
        CREATE TABLE transcription_jobs(lesson_id TEXT, version INT, state TEXT);''')
    rows = [('q1', 'Biologia', None, None, 3600, 1, 1, 'queued'), ('q2', 'Inglês - Teoria', None, None, 7200, 1, 1, 'queued'),
            ('r1', 'Química', None, None, 1000, 1, 1, 'review'), ('l1', 'Física', None, None, 1800, 1, 1, 'leased')]
    for i in range(samples):
        rows.append((f'd{i}', 'História', None, None, 1200, 1, 1, 'done'))
    db.executemany('INSERT INTO lessons VALUES(?,?,?,?,?,?,?)', [r[:7] for r in rows])
    db.executemany('INSERT INTO transcription_jobs VALUES(?,1,?)', [(r[0], r[7]) for r in rows])
    db.commit(); db.close()
    for i in range(samples):
        artifact(state / f'transcripts/private/d{i}/v1.json.gz', f'd{i}', 1200, 1200 * (2.4 + i * .1), 100000 - i * 3600)
    artifact(state / 'transcripts/private/short/v1.json.gz', 'short', 120, 1000, 100000)
    artifact(state / 'transcripts/private/cached/v1.json.gz', 'cached', 1200, 100, 100000, reused=2)
    artifact(state / 'transcripts/review/r1/v1.json.gz', 'r1', 1000, 2600, 99000)
    artifact(state / 'transcripts/review/d0/v1.json.gz', 'd0', 1200, 3120, 99000)  # historical, now published
    (state / 'videos.json').write_text(json.dumps({'items': {'a': {'status': 'verified', 'size': 10, 'checked_at': 'x'},
        'b': {'status': 'existing_remote_verified', 'size': 5}, 'c': {'status': 'error', 'size': None}, 'd': {'status': 'unavailable'}}}))
    (state / 'onedrive-status.json').write_text(json.dumps({'updated_at': 99000, 'pdf_sync': 'verified', 'transcript_sync': 'failed',
        'transcript_files': 9, 'remote_videos': 2, 'remote_video_bytes': 15, 'inventory_sha256': 'private'}))
    return state


def test_comparable_pace_excludes_short_and_cached_and_computes_eta(tmp_path):
    state = make_state(tmp_path)
    result = module.build(state, now=100100, excluded=('Inglês', 'Espanhol'))
    pace = result['transcription']
    # Approved + full-inference review evidence; short pilot and cache reuse excluded.
    assert pace['comparable_samples'] == 8
    assert pace['median_processing_per_audio'] == 2.6
    assert pace['remaining_active_audio_s'] == 3600 + 1800
    assert pace['ignored_jobs'] == 1
    assert pace['eta_seconds'] == round(5400 * 2.6)
    assert pace['eta_low_seconds'] <= pace['eta_seconds'] <= pace['eta_high_seconds']
    assert pace['completed_24h'] == 8  # approved artifacts in window, including short/cached
    assert pace['audio_24h_s'] == 6 * 1200 + 120 + 1200


def test_eta_withheld_without_five_comparable_samples(tmp_path):
    result = module.build(make_state(tmp_path, samples=2), now=100100, excluded=())
    assert result['transcription']['eta_seconds'] is None
    assert result['transcription']['median_processing_per_audio'] is None


def test_exclusions_come_from_persisted_scheduler_preference(tmp_path):
    state = make_state(tmp_path)
    assert module.build(state, now=100100)['transcription']['ignored_jobs'] == 0
    db = sqlite3.connect(state / 'hub.sqlite3')
    db.execute('CREATE TABLE transcription_discipline_exclusions(discipline TEXT PRIMARY KEY,reason TEXT,created_at REAL)')
    db.execute("INSERT INTO transcription_discipline_exclusions VALUES('Inglês','owner',1)")
    db.commit(); db.close()
    pace = module.build(state, now=100100)['transcription']
    assert pace['ignored_jobs'] == 1 and pace['excluded_disciplines'] == ['Inglês']
    assert pace['remaining_active_audio_s'] == 3600 + 1800


def test_eta_excludes_unknown_duration_jobs_but_reports_them(tmp_path):
    state = make_state(tmp_path)
    db = sqlite3.connect(state / 'hub.sqlite3')
    db.execute("INSERT INTO lessons VALUES('u','Física',NULL,NULL,NULL,1,1)")
    db.execute("INSERT INTO transcription_jobs VALUES('u',1,'queued')")
    db.commit(); db.close()
    pace = module.build(state, now=100100, excluded=('Inglês',))['transcription']
    assert pace['unknown_duration_jobs'] == 1
    assert pace['eta_seconds'] is not None


def test_downloads_and_reviews_are_scalar_and_never_leak_text_or_ids(tmp_path):
    result = module.build(make_state(tmp_path), now=100100, excluded=())
    text = json.dumps(result)
    assert 'SECRET' not in text and 'private' not in text and 'r1' not in text
    assert result['videos'] == {'verified': 2, 'error': 1, 'unavailable': 1, 'other': 0, 'verified_bytes': 15}
    assert result['onedrive']['transcript_sync'] == 'failed'
    assert result['reviews'] == [{'discipline': 'Química', 'severity': 'grave', 'reasons': {'ngram_repetition': 1},
                                  'intervals': [[5.0, 9.0]], 'state': 'review'}]


def test_review_severity_totals_and_reassessment_outcomes_are_aggregate(tmp_path):
    state = make_state(tmp_path)
    db = sqlite3.connect(state / 'hub.sqlite3')
    db.execute('CREATE TABLE transcription_review_log(lesson_id TEXT, version INTEGER, input_sha256 TEXT,'
               ' policy_version INTEGER, outcome TEXT, detail TEXT, attempts INTEGER, at REAL,'
               ' PRIMARY KEY(lesson_id, version))')
    db.executemany('INSERT INTO transcription_review_log VALUES(?,?,?,?,?,?,?,?)', [
        ('r1', 1, 'a', 4, 'review', None, 1, 1), ('x1', 1, 'b', 4, 'validated', None, 1, 1),
        ('x2', 1, 'c', 4, 'error', 'ValueError', 3, 1), ('x3', 1, 'd', 4, 'already_validated', None, 1, 1)])
    db.commit(); db.close()
    result = module.build(state, now=100100, excluded=())
    assert result['review_counts'] == {'total': 1, 'grave': 1, 'leve': 0, 'desconhecida': 0}
    assert result['reassessment'] == {'validated': 1, 'review': 1, 'error': 1}
    text = json.dumps(result)
    assert 'x1' not in text and 'x2' not in text and 'already_validated' not in text


def test_missing_reassessment_log_is_unknown_not_zero(tmp_path):
    result = module.build(make_state(tmp_path), now=100100, excluded=())
    assert result['reassessment'] is None
    assert result['review_counts']['total'] == 1


def test_warm_artifact_cache_avoids_redecoding_unchanged_artifacts(tmp_path):
    import os
    state = make_state(tmp_path)
    assert module.refresh_artifact_cache(state, now=100000) == 10
    assert (state / 'telemetry/pipeline-artifacts.json').is_file()
    for path in (state / 'transcripts').rglob('v*.json.gz'):
        stat = path.stat()
        # Same size and mtime, different bytes: only a cache hit can explain
        # surviving summaries, because re-reading these bytes would fail.
        path.write_bytes(b'x' * stat.st_size)
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    result = module.build(state, now=100100, excluded=())
    assert result['transcription']['comparable_samples'] == 8
    assert result['review_counts'] == {'total': 1, 'grave': 1, 'leve': 0, 'desconhecida': 0}
    assert 'corrupted' not in json.dumps(result)


def test_changed_artifact_identity_is_reparsed_despite_warm_cache(tmp_path):
    state = make_state(tmp_path)
    module.refresh_artifact_cache(state, now=100000)
    path = state / 'transcripts/review/r1/v1.json.gz'
    body = {'lesson_id': 'r1', 'version': 1, 'duration_s': 1000, 'elapsed_s': 2600, 'created_at': 99000,
            'chunks': [{'reused': False}, {'reused': False}, {'reused': False}],
            'qa': {'blockers': []}}
    path.write_bytes(gzip.compress(json.dumps(body).encode()))
    result = module.build(state, now=100100, excluded=())
    assert result['reviews'][0]['severity'] == 'leve'  # new content, not the cached grave summary
    assert result['review_counts']['grave'] == 0 and result['review_counts']['leve'] == 1


def test_stale_or_mismatched_cache_falls_back_to_full_parse(tmp_path):
    state = make_state(tmp_path)
    module.refresh_artifact_cache(state, now=100000)
    for path in (state / 'transcripts').rglob('v*.json.gz'):
        path.write_bytes(b'corrupted')
    stale = module.build(state, now=100000 + module.CACHE_MAX_AGE_S + 1, excluded=())
    assert stale['transcription']['comparable_samples'] == 0
    assert stale['review_counts']['total'] == 0
