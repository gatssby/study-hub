import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('fo_monitor', Path(__file__).parents[1] / 'ops/study-hub/fo_monitor.py')
assert spec is not None and spec.loader is not None
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


def test_render_distinguishes_current_and_historical_reviews_and_turn_states():
    snapshot = {
        'time_utc': '2026-11-22T17:55:00+00:00', 'status': {},
        'available_sources': 7, 'units': {'transcription': 'active', 'acoustic-review': 'active'},
        'disk_free': 8 * 2**30, 'disk_total': 20 * 2**30,
        'queue': {'done': 1, 'queued': 3, 'leased': 1, 'review': 2, 'superseded': 0},
        'reviews': {'all_jobs': 4, 'all_lessons': 3, 'current_jobs': 2},
        'canonical_lessons': 7, 'stale_leases': 0,
        'acoustic': {'current_receipts': 1, 'receipts': 2, 'inconclusive': 1,
                     'seconds_audio': 40.0, 'seconds_inference': 12.0,
                     'mean_wait_seconds': 600.0, 'waiting': True, 'state': 'activating',
                     'last_success': '2026-11-22T17:00:00+00:00', 'published': 0},
        'decoder_budget_margin': 2 * 2**30,
    }
    report = monitor.render(snapshot)
    assert '4 jobs / 3 aulas; 2 revisões atuais' in report
    assert 'aguardando turno' in report
    assert '600.0 s' in report
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
        'units': {'transcription': 'failed', 'acoustic-review': 'active'},
        'resources': {'parakeet': {'ActiveState': 'failed', 'Result': 'timeout'}},
        'acoustic': {'unreadable': 1},
    })) == {'stale_transcription_lease', 'multiple_transcription_leases', 'decoder_storage_reserve',
            'whisper_service_failed', 'acoustic_service_failed', 'invalid_acoustic_receipt'}
