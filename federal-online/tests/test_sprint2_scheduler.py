"""Sprint 2: exact persistent discipline exclusion, phase telemetry, review audit.

Synthetic only: no ASR, no network, no real media.
"""
import gzip
import json

import pytest

from fo_hub.worker import Worker, atomic_json, main, worker_status
from test_scheduler import worker, discipline


def test_exclusion_allowlist_is_exact(tmp_path):
    w = worker(tmp_path, ['Biologia'])
    for bad in ('ingles', 'Inglês ', 'Biologia', 'Espanhol I', ''):
        with pytest.raises(ValueError):
            w.exclude_discipline(bad, 'owner')
    w.exclude_discipline('Inglês', 'owner request')
    w.exclude_discipline('Espanhol', 'owner request')
    w.exclude_discipline('Espanhol', 'again')  # idempotent
    assert sorted(w.excluded_disciplines()) == ['Espanhol', 'Inglês']


def test_excluded_disciplines_never_leased_and_jobs_preserved(tmp_path):
    w = worker(tmp_path, ['Espanhol'] * 2 + ['Inglês'] * 2 + ['Biologia', 'Física'])
    before = [tuple(r) for r in w.c.execute('SELECT lesson_id,version,state,attempts,max_attempts,created_at,last_error FROM transcription_jobs ORDER BY lesson_id')]
    w.exclude_discipline('Inglês', 'owner')
    w.exclude_discipline('Espanhol', 'owner')
    got = []
    while (job := w.lease()) is not None:
        got.append(discipline(w, job))
    assert sorted(got) == ['Biologia', 'Física']
    rows = {r[0]: r for r in w.c.execute('SELECT lesson_id,version,state,attempts,max_attempts,created_at,last_error FROM transcription_jobs')}
    for b in before:
        subject = w.store.get_lesson(b[0])['subject']
        if subject in ('Inglês', 'Espanhol'):
            assert tuple(rows[b[0]]) == b  # untouched: queued, attempts, metadata
    assert w.c.execute("SELECT COUNT(*) FROM transcription_jobs WHERE state='done'").fetchone()[0] == 0


def test_exclusion_persists_across_restart_and_cursor_skips(tmp_path):
    w = worker(tmp_path, ['Biologia', 'Espanhol', 'Física'])
    w.exclude_discipline('Espanhol', 'owner')
    assert discipline(w, w.lease()) == 'Biologia'
    w2 = Worker(w.cfg, store=w.store)
    assert discipline(w2, w2.lease()) == 'Física'
    assert w2.lease() is None


def test_include_restores_eligibility(tmp_path):
    w = worker(tmp_path, ['Inglês'])
    w.exclude_discipline('Inglês', 'owner')
    assert w.lease() is None
    w.include_discipline('Inglês')
    assert discipline(w, w.lease()) == 'Inglês'


def test_running_excluded_job_not_interrupted(tmp_path):
    w = worker(tmp_path, ['Espanhol', 'Biologia'])
    job = w.lease()
    assert discipline(w, job) == 'Biologia' or discipline(w, job) == 'Espanhol'
    w.exclude_discipline('Espanhol', 'owner')
    assert w.c.execute("SELECT COUNT(*) FROM transcription_jobs WHERE state='leased'").fetchone()[0] == 1


def test_status_reports_exclusions_and_next_discipline_readonly(tmp_path, monkeypatch, capsys):
    w = worker(tmp_path, ['Espanhol', 'Inglês', 'Biologia'])
    w.exclude_discipline('Espanhol', 'owner'); w.exclude_discipline('Inglês', 'owner')
    status = worker_status(w.cfg)
    assert status['next_discipline'] == 'Biologia'
    assert status['excluded_disciplines'] == {'Espanhol': {'queued': 1}, 'Inglês': {'queued': 1}}


def test_cli_exclude_requires_exact_name(tmp_path, monkeypatch, capsys):
    w = worker(tmp_path, ['Biologia'])
    monkeypatch.setenv('STUDY_HUB_FO_DB', str(w.cfg.db)); monkeypatch.setenv('FO_STATE_ROOT', str(tmp_path))
    assert main(['--exclude-discipline', 'ingles']) == 2
    assert main(['--exclude-discipline', 'Inglês']) == 0
    assert 'Inglês' in json.loads(capsys.readouterr().out.strip().splitlines()[-1])['excluded']


def test_status_without_exclusion_table_is_null_safe(tmp_path):
    w = worker(tmp_path, ['Biologia'])
    with w.c: w.c.execute('DROP TABLE transcription_discipline_exclusions')
    status = worker_status(w.cfg)
    assert status['excluded_disciplines'] is None
    assert status['phase'] == []


# ---------- phase telemetry ----------

def test_phase_telemetry_recorded_and_status_exposes_it(tmp_path):
    w = worker(tmp_path, ['Biologia'])
    job = w.lease()
    w.record_phase(job, 'decoding', chunk_index=1, chunk_total=4)
    status = worker_status(w.cfg)
    (p,) = status['phase']
    assert p['phase'] == 'decoding' and p['chunk_index'] == 1 and p['chunk_total'] == 4
    assert p['lesson_id'] == job['lesson_id'] and p['discipline'] == 'Biologia'
    assert isinstance(p['phase_started_at'], float)
    with pytest.raises(ValueError):
        w.record_phase(job, 'bogus')


def test_phase_telemetry_failure_never_breaks_job(tmp_path):
    w = worker(tmp_path, ['Biologia'])
    job = w.lease()
    with w.c: w.c.execute('DROP TABLE transcription_job_phases')
    w.record_phase(job, 'downloading')  # must not raise


def test_pipeline_emits_phases_with_fake_runner(tmp_path):
    from test_scheduler import fake_runner
    w = worker(tmp_path, ['Biologia'])
    seen = []
    orig = w.record_phase
    w.record_phase = lambda job, phase, **k: (seen.append(phase), orig(job, phase, **k))
    calls = []; w.runner = fake_runner(w, calls)
    assert w.run_once()['state'] == 'validated'
    for phase in ('downloading', 'hashing', 'probing', 'decoding', 'stitching', 'qa', 'publishing', 'finished'):
        assert phase in seen
    assert seen.index('downloading') < seen.index('decoding') < seen.index('qa') < seen.index('finished')
    assert worker_status(w.cfg)['phase'] == []  # only leased jobs are reported


# ---------- evidence-only review audit ----------

SECRET = 'TEXTO-PRIVADO-NAO-IMPRIMIR'


def test_review_audit_is_allowlisted_and_readonly(tmp_path):
    from fo_hub.worker import review_audit
    w = worker(tmp_path, ['Espanhol'])
    lesson = w.c.execute('SELECT lesson_id FROM lessons').fetchone()[0]
    with w.c: w.c.execute("UPDATE transcription_jobs SET state='review'")
    flags = [{'kind': 'mixed_language_configuration_unverified', 'severity': 'blocking', 'start': 0, 'end': 30},
             {'kind': 'non_monotonic', 'severity': 'warning', 'idx': 0, 'text': SECRET}]
    artifact = {'lesson_id': lesson, 'version': 1, 'qa_policy_version': 4, 'duration_s': 30.0,
                'source_sha256': 'a' * 64,
                'qa': {'passed': False, 'flags': flags, 'blockers': [flags[0]], 'warnings': [flags[1]],
                       'segments': [{'text': SECRET}], 'metrics': {'segments': 1, 'words': 3, 'note': SECRET}},
                'segments': [{'start': 0, 'end': 30, 'text': SECRET}],
                'chunks': [{'raw': SECRET, 'decoding': {'stderr': SECRET}, 'reused': False}]}
    path = tmp_path / 'transcripts/review' / lesson / 'v1.json.gz'
    atomic_json(path, artifact)
    before = path.read_bytes()
    report = review_audit(w.cfg)
    text = json.dumps(report)
    assert SECRET not in text
    (item,) = report['reviews']
    assert item['discipline'] == 'Espanhol'
    assert item['blocker_kinds'] == {'mixed_language_configuration_unverified': 1}
    assert item['warning_kinds'] == {'non_monotonic': 1}
    assert item['artifact_sha256'] and item['reassessment_receipts'] == 0
    assert item['metrics'] == {'segments': 1, 'words': 3}
    assert item['excluded_discipline'] is False
    assert report['inference_executed'] is False and report['mutations'] == 0
    assert path.read_bytes() == before


def test_review_audit_missing_artifact_is_null_not_zero(tmp_path):
    from fo_hub.worker import review_audit
    w = worker(tmp_path, ['Biologia'])
    with w.c: w.c.execute("UPDATE transcription_jobs SET state='review'")
    (item,) = review_audit(w.cfg)['reviews']
    assert item['artifact_present'] is False and item['blocker_kinds'] is None and item['metrics'] is None
