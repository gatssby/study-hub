"""Synthetic repetition probes, not acoustic labels or human gold."""
import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fo_hub.transcription import qa_segments


def segment(text, start=0, end=5):
    return {'start': start, 'end': end, 'text': text}


@pytest.mark.parametrize('phrase', [
    'a célula',
    'o núcleo controla a expressão genética',
    'a primeira fase do desenvolvimento embrionário apresenta uma sequência de divisões celulares',
])
def test_three_consecutive_ngrams_are_reviewed_without_deleting_text(phrase):
    rows=[segment((phrase+'; ')*3)]
    original=copy.deepcopy(rows)
    result=qa_segments(rows)
    assert not result['passed']
    assert any(f['kind']=='ngram_repetition' for f in result['flags'])
    assert result['segments']==original
    assert rows==original


def test_loop_split_across_decoder_segments_and_minute_is_not_missed():
    rows=[segment('o ciclo celular o',58,59),segment('ciclo celular o ciclo',59,60),
          segment('celular continua',60,62)]
    result=qa_segments(rows)
    assert not result['passed']
    assert result['metrics']['repetition']['candidate_tokens']==9
    assert result['metrics']['repetition']['total_tokens']==10
    assert result['metrics']['repetition']['ratio']==0.9
    assert {r['minute'] for r in result['metrics']['repetition']['by_minute']}=={0,1}
    assert sum(r['candidate_tokens'] for r in result['metrics']['repetition']['by_minute'])==9


@pytest.mark.parametrize('text', [
    'A célula a célula a célula a célula a célula',
    'a função renal regula o equilíbrio de água e sais minerais '*50,
])
def test_word_and_long_phrase_loops_are_candidates_not_confirmed_hallucination(text):
    result=qa_segments([segment(text)])
    assert not result['passed']
    assert result['metrics']['repetition']['candidate_tokens']>0
    assert result['metrics']['repetition']['classification']=='requires_acoustic_review'
    assert result['segments'][0]['text']==text


@pytest.mark.parametrize('text', [
    'Eu, eu acho que a célula... então, a célula se divide.',
    'Primeiro prófase; depois metáfase; depois anáfase; por fim telófase.',
    'x = -5; x = +5; x = 5; α² + β₂ = γ.',
    'A primeira divisão começa quando... mas vamos voltar à figura.',
    '',
])
def test_hesitations_science_symbols_and_incomplete_speech_are_preserved(text):
    result=qa_segments([segment(text)])
    assert result['passed']
    assert result['segments'][0]['text']==text


def test_genuine_repetitive_enumeration_is_not_silently_corrected():
    text='um para cada célula; um para cada célula; um para cada célula'
    result=qa_segments([segment(text)])
    assert not result['passed']  # ambiguity requires acoustic review, not removal
    assert result['segments'][0]['text']==text


def test_silence_and_music_cannot_be_diagnosed_from_text_only():
    result=qa_segments([segment('Música seguida de fala sobre biologia.',30,35)],60)
    assert result['passed']
    assert not any('hallucination' in f['kind'] for f in result['flags'])


def test_sparse_utterances_are_not_joined_into_an_artificial_loop():
    result=qa_segments([segment('a célula divide',0,2),segment('a célula divide',60,62),
                        segment('a célula divide',120,122)])
    assert result['metrics']['repetition']['candidate_tokens']==0


def test_repetition_spanning_600_second_boundary_is_retained_for_review():
    rows=[segment('a célula se divide a célula',596,600),
          segment('se divide a célula se divide',600,605)]
    result=qa_segments(rows)
    assert not result['passed']
    assert result['metrics']['repetition']['candidate_tokens']==12
    assert result['segments']==rows
