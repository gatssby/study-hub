"""Risk-based MVP QA: retain imperfect speech, reject substantial corruption."""
import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fo_hub.transcription import qa_segments


def assess(segments, duration=600, extra=()):
    from fo_hub.transcription import classify_qa
    report = qa_segments(segments, duration)
    report['flags'].extend(extra)
    classify_qa(report, segments, duration)
    return report


def test_isolated_small_overlap_and_boundary_ambiguity_publish_unchanged():
    rows = [{'start': 0, 'end': 300, 'text': 'conteúdo anterior'},
            {'start': 299.8, 'end': 600, 'text': 'conteúdo seguinte'}]
    original = copy.deepcopy(rows)
    report = assess(rows, extra=[{'kind': 'ambiguous_overlap', 'start': 299, 'end': 301}])
    assert report['passed']
    assert report['blockers'] == []
    assert {f['kind'] for f in report['warnings']} == {'non_monotonic', 'ambiguous_overlap'}
    assert rows == original and report['segments'] == original
    assert all(f['severity'] == 'warning' for f in report['flags'])


def test_isolated_didactic_duplicate_is_warning_not_text_removal():
    rows = [{'start': 0, 'end': 1, 'text': 'Glicerídeo.'},
            {'start': 9, 'end': 10, 'text': 'Glicerídeo.'},
            {'start': 10, 'end': 30, 'text': 'Óleo e gordura.'}]
    report = assess(rows, duration=30)
    assert report['passed'] and report['warnings'][0]['kind'] == 'duplicate_segment'
    assert report['segments'] == rows


@pytest.mark.parametrize('extra', [
    {'kind': 'unknown_future_check'},
    {'kind': 'language_mismatch'},
    {'kind': 'text_during_measured_silence', 'start': 0, 'end': 50},
    {'kind': 'ambiguous_overlap', 'start': 0, 'end': 60},
    {'kind': 'boundary_timestamp_drift', 'start': 0, 'end': 70},
])
def test_substantial_or_unknown_defects_stay_blocked(extra):
    report = assess([{'start': 0, 'end': 600, 'text': 'conteúdo'}], extra=[extra])
    assert not report['passed'] and report['blockers']


def test_large_timestamp_regression_stays_review():
    rows = [{'start': 0, 'end': 80, 'text': 'primeira explicação'},
            {'start': 20, 'end': 600, 'text': 'segunda explicação'}]
    report = assess(rows)
    assert not report['passed']
    assert any(f['kind'] == 'non_monotonic' for f in report['blockers'])


def test_many_tiny_overlaps_cannot_hide_general_timestamp_corruption():
    rows = [{'start': i * 2, 'end': i * 2 + 3, 'text': f'frase número {i}'} for i in range(60)]
    report = assess(rows, duration=121)
    assert not report['passed']
    assert any(f['kind'] == 'non_monotonic' for f in report['blockers'])


def test_artificial_long_loop_remains_review_without_deleting_a_word():
    rows = [{'start': 0, 'end': 60, 'text': 'a função renal ' * 30}]
    report = assess(rows, duration=60)
    assert not report['passed']
    assert any(f['kind'] == 'ngram_repetition' for f in report['blockers'])
    assert report['segments'] == rows


def test_unexplained_missing_speech_gap_is_blocking_in_final_pipeline():
    report = assess([{'start': 0, 'end': 2, 'text': 'início'},
                     {'start': 500, 'end': 600, 'text': 'fim'}])
    assert not report['passed']
    assert any(f['kind'] == 'silence_gap' for f in report['blockers'])


def test_invalid_timestamp_stays_blocking():
    report = assess([{'start': 4, 'end': 1, 'text': 'texto'}])
    assert not report['passed']
    assert any(f['kind'] == 'bad_timestamp' for f in report['blockers'])


@pytest.mark.parametrize('subject,expected', [('Biologia', 'validated'), ('Espanhol - Teoria', 'review')])
def test_pipeline_publishes_small_overlap_with_persisted_warnings(tmp_path, subject, expected):
    import gzip
    import json
    from types import SimpleNamespace
    from test_worker import setup
    from fo_hub.worker import Worker

    store, lesson, cfg = setup(tmp_path)
    store.conn.execute('UPDATE lessons SET subject=?,front=?,module=?', (subject, subject, subject))
    store.conn.commit()
    def run(cmd, **kwargs):
        if cmd[0] == 'rclone':
            Path(cmd[3]).write_bytes(b'fakevideo')
        elif cmd[0] == 'ffprobe':
            return SimpleNamespace(stdout=json.dumps({'format': {'duration': '30'}}), stderr='')
        elif cmd[0] == 'ffmpeg' and cmd[-1].endswith('.wav'):
            Path(cmd[-1]).write_bytes(b'fakewav')
        elif cmd[0] == str(cfg.binary):
            Path(cmd[cmd.index('-of')+1]+'.json').write_text(json.dumps({'transcription': [
                {'offsets': {'from': 0, 'to': 15000}, 'text': 'Primeira explicação.'},
                {'offsets': {'from': 14800, 'to': 30000}, 'text': 'Continuação legítima.'}]}))
        return SimpleNamespace(stdout='', stderr='')
    worker = Worker(cfg, store=store, runner=run, gate_fn=lambda: {'allowed': True},
                    free_bytes=lambda: 20*1024**3)
    store.conn.execute('INSERT INTO lesson_video_sources VALUES(?,?,?,?,?,?)',
                       (lesson['lesson_id'], 'onedrive:Federal Online/a.mp4', '1', 9, 1, 'now'))
    store.conn.commit()
    assert worker.run_once()['state'] == expected
    transcript = store.get_transcript(lesson['lesson_id'])
    if expected == 'review':
        assert transcript is None
        private = json.loads(gzip.decompress((tmp_path/'transcripts/review'/lesson['lesson_id']/'v1.json.gz').read_bytes()))
        assert any(f['kind'] == 'mixed_language_configuration_unverified' for f in private['qa']['blockers'])
        return
    assert transcript['qa']['warnings'] and not transcript['qa']['blockers']
    public = json.loads((tmp_path/'transcripts/generated_v2'/lesson['lesson_id']/'v1.json').read_text())
    assert set(public) == {'lesson_id', 'version', 'corpus', 'qa', 'segments'}
    private = json.loads(gzip.decompress((tmp_path/'transcripts/private'/lesson['lesson_id']/'v1.json.gz').read_bytes()))
    assert private['qa_policy_version'] == 4
    assert private['segments'] == public['segments']
