import importlib.util
import json
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parents[1] / 'ops/study-hub'))
spec = importlib.util.spec_from_file_location('health_telemetry', Path(__file__).parents[1] / 'ops/study-hub/health_telemetry.py')
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

NOW = 1_800_000_000.0


def healthy(**overrides):
    base = {'now': NOW, 'transcription_service': 'active', 'transcription_result': 'success',
            'breaker_open': False, 'leased': 1, 'phase_age_s': 60.0, 'last_finished_age_s': 3600.0,
            'eligible_queued': 100, 'materials_active': 'inactive', 'materials_result': 'success',
            'onedrive_age_s': 600.0, 'pdf_sync': 'verified', 'transcript_sync': 'verified',
            'free_bytes': 10 * 1024**3, 'reserve_bytes': 5 * 1024**3, 'growth_bytes_per_day': None,
            'active_deferrals': 0, 'persistent_deferrals': 0}
    base.update(overrides)
    return base


def test_healthy_pipeline_has_no_alerts():
    result = module.assess(healthy())
    assert result['alerts'] == []
    assert result['observed_at'] == NOW
    assert result['materials_fail_streak'] == 0


def test_unknown_observations_never_fabricate_alerts():
    result = module.assess({'now': NOW})
    assert result['alerts'] == []
    assert result['breaker_open'] is None


def test_open_breaker_alerts_even_while_service_looks_active():
    assert module.assess(healthy(breaker_open=True))['alerts'] == ['breaker_open']


def test_stalled_lease_distinguishes_long_decoder_chunks():
    assert module.assess(healthy(phase_age_s=1800.0))['alerts'] == []  # normal chunk
    assert module.assess(healthy(phase_age_s=7300.0))['alerts'] == ['transcription_stalled']
    assert module.assess(healthy(leased=0, phase_age_s=7300.0))['alerts'] == []


def test_not_progressing_requires_eligible_work_and_stale_completion():
    assert module.assess(healthy(leased=0, last_finished_age_s=7 * 3600.0))['alerts'] == ['transcription_not_progressing']
    assert module.assess(healthy(leased=0, last_finished_age_s=3600.0))['alerts'] == []
    assert module.assess(healthy(leased=0, eligible_queued=0, last_finished_age_s=7 * 3600.0))['alerts'] == []
    assert module.assess(healthy(leased=0, last_finished_age_s=None))['alerts'] == []


def test_failed_and_stopped_services_are_distinct():
    assert module.assess(healthy(transcription_service='failed'))['alerts'] == ['transcription_failed']
    assert module.assess(healthy(transcription_service='inactive', transcription_result='exit-code'))['alerts'] == ['transcription_stopped']
    assert module.assess(healthy(transcription_service='inactive', transcription_result='success'))['alerts'] == []


def test_materials_alert_requires_repeated_failures_and_resets_on_success():
    failed = healthy(materials_active='inactive', materials_result='exit-code')
    first = module.assess(failed)
    assert first['materials_fail_streak'] == 1 and first['alerts'] == []
    second = module.assess(failed, previous=first)
    assert second['materials_fail_streak'] == 2 and second['alerts'] == ['materials_failed']
    assert module.assess(healthy(), previous=second)['materials_fail_streak'] == 0
    assert module.assess(healthy(materials_active='failed'))['materials_fail_streak'] == 1


def test_onedrive_staleness_and_sync_failure():
    assert module.assess(healthy(onedrive_age_s=4 * 3600.0))['alerts'] == ['onedrive_stale']
    assert module.assess(healthy(onedrive_age_s=None))['alerts'] == []
    assert module.assess(healthy(pdf_sync='failed'))['alerts'] == ['onedrive_sync_failed']


def test_storage_warnings_are_reused_not_reinvented():
    assert module.assess(healthy(free_bytes=4 * 1024**3))['alerts'] == ['low_reserve']
    assert module.assess(healthy(growth_bytes_per_day=2 * 1024**3))['alerts'] == ['growth_risk']


def test_only_persistent_deferrals_alert():
    assert module.assess(healthy(active_deferrals=13))['alerts'] == []
    assert module.assess(healthy(active_deferrals=13, persistent_deferrals=2))['alerts'] == ['source_deferrals_persistent']


def _db(state):
    db = sqlite3.connect(state / 'hub.sqlite3')
    db.executescript('''
        CREATE TABLE lessons(lesson_id TEXT PRIMARY KEY, version INTEGER, present INTEGER);
        CREATE TABLE transcription_jobs(lesson_id TEXT, version INTEGER, state TEXT, attempts INTEGER DEFAULT 0,
            max_attempts INTEGER DEFAULT 3, retry_at REAL DEFAULT 0, updated_at TEXT, PRIMARY KEY(lesson_id, version));
        CREATE TABLE lesson_video_sources(lesson_id TEXT PRIMARY KEY, remote_path TEXT, revision TEXT, size INTEGER, available INTEGER);
        CREATE TABLE transcription_breaker(fingerprint TEXT PRIMARY KEY, opened_at REAL);
        CREATE TABLE transcription_job_phases(lesson_id TEXT, version INTEGER, phase TEXT, phase_started_at REAL, updated_at REAL);
        CREATE TABLE transcription_source_deferrals(lesson_id TEXT, version INTEGER, retry_after REAL, observed_at REAL);
    ''')
    db.execute("INSERT INTO lessons VALUES('fo_a',1,1)")
    db.execute("INSERT INTO lesson_video_sources VALUES('fo_a','onedrive:Federal Online/a.mp4','1',9,1)")
    db.commit()
    return db


def test_observe_reads_real_sqlite_and_persists_sanitized_snapshot(tmp_path):
    state = tmp_path / 'state'
    state.mkdir()
    db = _db(state)
    db.execute("INSERT INTO transcription_jobs VALUES('fo_a',1,'leased',1,3,0,?)", (str(NOW - 7300),))
    db.execute("INSERT INTO transcription_job_phases VALUES('fo_a',1,'decoding',?,?)", (NOW - 7300, NOW - 7300))
    db.execute("INSERT INTO transcription_job_phases VALUES('fo_b',1,'finished',?,?)", (NOW - 3600, NOW - 3600))
    db.execute("INSERT INTO transcription_breaker VALUES('fp',NULL)")
    db.execute("INSERT INTO transcription_source_deferrals VALUES('fo_c',1,?,?)", (NOW + 86400, NOW - 8 * 86400))
    db.execute("INSERT INTO transcription_jobs VALUES('fo_d',1,'queued',0,3,0,'0')")
    db.execute("INSERT INTO lessons VALUES('fo_d',1,1)")
    db.execute("INSERT INTO lesson_video_sources VALUES('fo_d','onedrive:Federal Online/d.mp4','1',9,1)")
    db.commit(); db.close()
    (state / 'onedrive-status.json').write_text(json.dumps({'updated_at': NOW - 600, 'pdf_sync': 'verified', 'transcript_sync': 'verified'}))
    units = SimpleNamespace(stdout='Id=study-hub-fo-transcription.service\nActiveState=active\nResult=success\n\n'
                                   'Id=study-hub-fo-materials.service\nActiveState=inactive\nResult=success\n',
                            stderr='', returncode=0)
    result = module.observe(state, now=NOW, runner=lambda *a, **k: units, available_bytes=10 * 1024**3)
    assert result['breaker_open'] is False
    assert result['leased'] == 1
    assert result['phase_age_s'] == 7300.0
    assert result['last_finished_age_s'] == 3600.0
    assert result['eligible_queued'] == 1
    assert result['active_deferrals'] == 1 and result['persistent_deferrals'] == 1
    assert result['alerts'] == ['source_deferrals_persistent', 'transcription_stalled']
    assert result['transcription_service'] == 'active'
    persisted = json.loads((state / 'telemetry/health.json').read_text())
    assert persisted == result
    assert 'fo_a' not in json.dumps(persisted)  # no lesson IDs or paths escape


def test_observe_missing_database_is_unknown_not_healthy(tmp_path):
    state = tmp_path / 'state'
    state.mkdir()
    units = SimpleNamespace(stdout='', stderr='', returncode=1)
    result = module.observe(state, now=NOW, runner=lambda *a, **k: units, available_bytes=10 * 1024**3)
    assert result['breaker_open'] is None and result['leased'] is None
    assert result['alerts'] == []
    assert (state / 'telemetry/health.json').exists()