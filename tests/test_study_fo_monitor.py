import importlib.util
import json
import sqlite3
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location('fo_monitor', Path(__file__).parents[1] / 'ops/study-hub/fo_monitor.py')
assert spec is not None and spec.loader is not None
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


def test_remote_probe_queries_primary_units_and_distinguishes_review_versions(tmp_path, monkeypatch, capsys):
    database = tmp_path / 'hub.sqlite3'
    db = sqlite3.connect(database)
    db.executescript('''
        CREATE TABLE lessons(lesson_id TEXT, version INT, present INT, title TEXT, subject TEXT);
        CREATE TABLE lesson_video_sources(lesson_id TEXT, available INT, size INT);
        CREATE TABLE transcription_jobs(lesson_id TEXT, version INT, progress REAL, state TEXT, updated_at REAL, lease_until REAL);
        INSERT INTO lessons VALUES ('a', 2, 1, 'Lesson', 'Subject'), ('b', 1, 0, 'Removed', 'Subject');
        INSERT INTO lesson_video_sources VALUES ('a', 1, 12), ('b', 1, 13);
        INSERT INTO transcription_jobs VALUES ('a', 1, 0, 'review', 1, NULL), ('a', 2, 0, 'review', 2, NULL),
                                              ('b', 1, 0, 'review', 1, NULL);
    ''')
    db.close()
    before = database.read_bytes()
    monkeypatch.setattr('urllib.request.urlopen', lambda *args, **kwargs: BytesIO(b'{}'))
    calls = []

    def runner(command, **kwargs):
        calls.append(command[:3])
        return SimpleNamespace(stdout='active\n' if command[1] == 'is-active' else 'Result=success\n')

    monkeypatch.setattr(monitor.subprocess, 'run', runner)
    script = monitor.REMOTE_SCRIPT.replace("Path('/home/ubuntu/study-hub-state/federal-online')", f'Path({str(tmp_path)!r})')
    exec(compile(script, '<fo-monitor-remote>', 'exec'), {})
    result = json.loads(capsys.readouterr().out)
    assert result['available_sources'] == 1
    assert result['reviews'] == {'all_jobs': 3, 'all_lessons': 2, 'current_jobs': 1}
    assert result['resources'] == {'whisper': {'Result': 'success'}}
    assert set(result['units']) == {'transcription', 'catalog', 'materials', 'videos', 'index', 'onedrive', 'ocr'}
    assert calls == [['systemctl', 'is-active', 'study-hub-fo-transcription.service'],
                     *[['systemctl', 'is-active', f'study-hub-fo-{name}.timer']
                       for name in ('catalog', 'materials', 'videos', 'index', 'onedrive', 'ocr')],
                     ['systemctl', 'show', 'study-hub-fo-transcription.service']]
    assert 'acoustic' not in result
    assert database.read_bytes() == before


def test_render_distinguishes_current_and_historical_reviews_and_ignores_retired_sidecar():
    snapshot = {
        'time_utc': '2026-11-22T17:55:00+00:00', 'status': {},
        'available_sources': 7, 'units': {'transcription': 'active', 'acoustic-review': 'active'},
        'disk_free': 8 * 2**30, 'disk_total': 20 * 2**30,
        'queue': {'done': 1, 'queued': 3, 'leased': 1, 'review': 2, 'superseded': 0},
        'reviews': {'all_jobs': 4, 'all_lessons': 3, 'current_jobs': 2},
        'canonical_lessons': 7, 'stale_leases': 0,
        'resources': {'whisper': {'CPUUsageNSec': '1000000000'}, 'parakeet': {}},
        'acoustic': {'current_receipts': 1, 'receipts': 2, 'inconclusive': 1,
                     'seconds_audio': 40.0, 'seconds_inference': 12.0,
                     'mean_wait_seconds': 600.0, 'waiting': True, 'state': 'activating',
                     'last_success': '2026-11-22T17:00:00+00:00', 'published': 0},
        'decoder_budget_margin': 2 * 2**30,
    }
    report = monitor.render(snapshot)
    assert '4 jobs / 3 aulas; 2 revisões atuais' in report
    assert 'whisper: CPU acumulada 1.0 s' in report
    for retired in ('Parakeet', 'parakeet', 'acoustic-review', 'aguardando turno'):
        assert retired not in report
    assert '2.0 GiB acima da reserva' in report


def test_health_check_does_not_alert_on_an_ordinary_long_decoder_turn():
    assert monitor.health_issues({
        'status': {'TRANSCRIPTION_ENABLED': True}, 'queue': {'queued': 2800, 'leased': 1},
        'active': [{}], 'stale_leases': 0, 'decoder_budget_margin': 10 * 2**30,
        'units': {'transcription': 'active', 'acoustic-review': 'active'},
        'resources': {'parakeet': {'ActiveState': 'activating', 'Result': 'success'}},
        'acoustic': {'unreadable': 0},
    }) == []


def test_health_check_reports_actionable_failures_without_lecture_details():
    assert set(monitor.health_issues({
        'status': {'TRANSCRIPTION_ENABLED': True}, 'queue': {'queued': 2800},
        'active': [{'title': 'Private A'}, {'title': 'Private B'}],
        'stale_leases': 1, 'decoder_budget_margin': -1,
        'units': {'transcription': 'failed', 'acoustic-review': 'failed'},
        'resources': {'parakeet': {'ActiveState': 'failed', 'Result': 'timeout'}},
        'acoustic': {'unreadable': 1},
    })) == {'stale_transcription_lease', 'multiple_transcription_leases', 'decoder_storage_reserve',
            'whisper_service_failed'}
