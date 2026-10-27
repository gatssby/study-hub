"""Regression coverage for speech/stability separation and input validation."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fo_hub.benchmark import main, score_batch
import json


@pytest.mark.parametrize('anchors', [None, {}, (), 'bad', [None], ['bad'], [1],
                                    [{'id': 1}], [{'id': []}], [{'id': ''}]])
def test_invalid_anchor_shapes_raise_value_error(anchors):
    if isinstance(anchors, list) and anchors and isinstance(anchors[0], dict):
        anchors[0].update(reference_start_s=0, reference_end_s=1,
                          hypothesis_start_s=0, hypothesis_end_s=1)
    record = dict(speech_record(), anchors=anchors)
    with pytest.raises(ValueError, match='anchor'):
        score_batch({'synthetic': True, 'records': [record]}, bootstrap_samples=10)


def test_cli_reports_non_object_anchor_cleanly(tmp_path, capsys):
    path = tmp_path / 'batch.json'
    path.write_text(json.dumps({'synthetic': True,
                               'records': [dict(speech_record(), anchors=[None])]}))
    with pytest.raises(SystemExit) as error:
        main(['score-batch', str(path)])
    assert error.value.code == 2
    assert 'anchor' in capsys.readouterr().err


@pytest.mark.parametrize('change', [{'reference': 'other'}, {'duration_s': 61},
                                    {'kind': 'full_lesson'}])
def test_same_segment_gold_duration_and_kind_must_match_between_configs(change):
    first = speech_record()
    second = dict(first, config_id='other', **change)
    with pytest.raises(ValueError, match='identical gold/duration/kind'):
        score_batch({'synthetic': True, 'records': [first, second]}, bootstrap_samples=10)


def speech_record():
    return {'segment_id': 'speech', 'config_id': 'c', 'kind': 'speech',
            'reference': 'cell', 'hypothesis': 'cell', 'duration_s': 60}


def test_full_lesson_gold_does_not_enter_speech_aggregates():
    payload = {'synthetic': True, 'glossary': ['cell'], 'records': [speech_record()]}
    expected = score_batch(payload, bootstrap_samples=20)['comparisons'][0]
    payload['records'].append({'segment_id': 'full', 'config_id': 'c',
                               'kind': 'full_lesson', 'reference': 'cell cell',
                               'hypothesis': 'wrong', 'duration_s': 3600})
    result = score_batch(payload, bootstrap_samples=20)
    summary = result['comparisons'][0]
    for metric in ('wer', 'cer', 'wer_ci95', 'cer_ci95', 'term_wer', 'term_recall'):
        assert summary[metric] == expected[metric], metric
    assert result['records'][-1]['wer'] == 1
    assert result['records'][-1]['term_recall'] == 0


def test_full_lesson_only_has_no_speech_aggregate():
    record = dict(speech_record(), kind='full_lesson')
    summary = score_batch({'synthetic': True, 'glossary': ['cell'], 'records': [record]},
                          bootstrap_samples=10)['comparisons'][0]
    for metric in ('wer', 'cer', 'wer_ci95', 'cer_ci95', 'term_wer', 'term_recall'):
        assert summary[metric] is None, metric
