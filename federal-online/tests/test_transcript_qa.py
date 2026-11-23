"""Synthetic evidence only: no decoder, media, I/O or network."""
from copy import deepcopy
import json

import pytest


def row(start, end, text):
    return {'start': start, 'end': end, 'text': text}


def chunk(offset, length, *segments, silence=(), actual=None, raw=False) -> dict:
    result: dict = dict(offset_s=offset, duration_s=length, segments=list(segments),
                  audio_duration_s=length if actual is None else actual, silence=list(silence))
    if raw:
        result['raw'] = {'transcription': [
            {'offsets': {'from': round((s['start'] - offset) * 1000),
                         'to': round((s['end'] - offset) * 1000)}, 'text': ' ' + s['text']}
            for s in segments]}
    return result


def assess(chunks, duration):
    from fo_hub import transcript_qa
    return transcript_qa.assess(chunks, duration, chunk_s=600, overlap_s=2)


def kinds(qa, level):
    return {entry['kind'] for entry in qa[level]}


def test_same_timed_overlap_only_is_merged_without_mutating_evidence():
    left = row(596, 600, 'Explique a função renal.')
    right = row(598, 603, 'A função renal, controla água.')
    right['tokens'] = [{'id': 123}]
    chunks = [chunk(0, 600, left, silence=[(0, 596)]), chunk(598, 5, right)]
    original = deepcopy(chunks)
    expected = [row(596, 603, 'Explique a função renal. controla água.')]
    result, qa = assess(chunks, 603)
    assert result == expected
    assert chunks == original
    assert assess(chunks, 603) == (result, qa)
    assert qa['outcome'] == 'APPROVED' and qa['passed'] is True
    assert qa['metrics']['segments'] == 1
    json.dumps(qa, allow_nan=False)


@pytest.mark.parametrize('left,right', [
    ('a queratina do cabelo é uma proteína', 'proteína do cabelo é uma proteína, então'),
    ('a razão x/y é constante', 'x*y é constante neste caso'),
    ('a razão x:y é constante', 'x y é constante neste caso'),
    ('o termo x! é inteiro', 'x é inteiro neste caso'),
    ('a lista x,y é ordenada', 'x y é ordenada neste caso'),
    ('vamos considerar uma função f', 'uma função f(x) neste caso'),
    ('o valor cai para −5 graus', 'cai para 5 graus neste caso'),
])
def test_uncertain_boundary_preserves_conflicting_content(left, right):
    a, b = row(597, 600, left), row(598, 603, right)
    result, qa = assess([chunk(0, 600, a, silence=[(0, 597)]), chunk(598, 5, b)], 603)
    assert result == [a, b]
    assert qa['outcome'] == 'APPROVED_WITH_WARNING' and qa['passed'] is True
    assert 'ambiguous_overlap' in kinds(qa, 'warnings')


def test_disjoint_utterances_with_same_words_are_not_deduplicated():
    a = row(598, 598.5, 'a função renal')
    b = row(599, 600, 'a função renal')
    result, qa = assess([chunk(0, 600, a, silence=[(0, 598)]),
                         chunk(598, 3, b, silence=[(2, 3)])], 601)
    assert result == [a, b]
    assert qa['passed']


@pytest.mark.parametrize('defect,reason', [
    ('missing_chunk', 'missing_chunk'), ('wrong_offset', 'invalid_chunk_layout'),
    ('short_wav', 'truncated_audio'), ('missing_wav_length', 'invalid_audio_duration'),
    ('malformed_silence', 'invalid_silence'), ('blank', 'invalid_segment'),
    ('not_text', 'invalid_segment'), ('zero_width', 'bad_timestamp'),
    ('negative', 'bad_timestamp'), ('nan', 'bad_timestamp'),
    ('regressing', 'bad_timestamp'), ('out_of_chunk', 'bad_timestamp'),
    ('empty', 'empty_output'),
])
def test_structural_evidence_fails_closed(defect, reason):
    chunks = [chunk(0, 600, row(1, 2, 'primeira'), silence=[(2, 599)]),
              chunk(598, 10, row(600, 608, 'segunda'))]
    first, second = chunks
    if defect == 'missing_chunk':
        chunks.pop()
    elif defect == 'wrong_offset':
        second['offset_s'] = 599
    elif defect == 'short_wav':
        second['audio_duration_s'] = 7
    elif defect == 'missing_wav_length':
        del second['audio_duration_s']
    elif defect == 'malformed_silence':
        second['silence'] = [(0, 11)]
    elif defect == 'blank':
        second['segments'][0]['text'] = '  '
    elif defect == 'not_text':
        second['segments'][0]['text'] = 123
    elif defect == 'zero_width':
        second['segments'][0]['end'] = 600
    elif defect == 'negative':
        first['segments'][0]['start'] = -0.001
    elif defect == 'nan':
        first['segments'][0]['start'] = float('nan')
    elif defect == 'regressing':
        first['segments'].append(row(0.9, 1.1, 'fora de ordem'))
    elif defect == 'out_of_chunk':
        second['segments'][0]['start'] = 597.999
    elif defect == 'empty':
        first['segments'] = second['segments'] = []
    _, qa = assess(chunks, 608)
    assert qa['outcome'] == 'REVIEW_REQUIRED' and qa['passed'] is False
    assert reason in kinds(qa, 'blockers')
    json.dumps(qa, allow_nan=False)


def test_padding_clamp_requires_the_final_raw_row_and_measured_wav_bound():
    chunks = [chunk(0, 30, row(0, 15, 'Primeira explicação.'),
                    row(14.8, 45, 'Continuação.'), raw=True)]
    original = deepcopy(chunks)
    result, qa = assess(chunks, 30)
    assert chunks == original
    assert result == [row(0, 15, 'Primeira explicação.'), row(14.8, 30, 'Continuação.')]
    assert qa['passed']
    correction = qa['correction']
    assert correction['kind'] == 'timestamp_correction'
    assert (correction['raw_end'], correction['corrected_end']) == (45, 30)


@pytest.mark.parametrize('variant', ['unverified', 'mismatched_raw', 'truncated', 'start_at_bound',
                                     'not_30s_padding', 'small_overrun', 'earlier_overrun'])
def test_other_out_of_bounds_timestamps_are_not_clamped(variant):
    second = row(15, 45, 'Continuação.')
    first = chunk(0, 30, row(0, 15, 'Primeira explicação.'), second, raw=True)
    if variant == 'unverified':
        del first['raw']
    elif variant == 'mismatched_raw':
        first['raw']['transcription'][-1]['text'] = 'Frase diferente.'
    elif variant == 'truncated':
        first['audio_duration_s'] = 29
    elif variant == 'start_at_bound':
        second.update(start=30, end=60)
        first['raw']['transcription'][-1]['offsets'].update({'from': 30000, 'to': 60000})
    elif variant in ('not_30s_padding', 'small_overrun'):
        second['end'] = 42 if variant == 'not_30s_padding' else 30.1
        first['raw']['transcription'][-1]['offsets']['to'] = round(second['end'] * 1000)
    else:
        first['segments'][0]['end'] = 30.001
        first['raw']['transcription'][0]['offsets']['to'] = 30001
    _, qa = assess([first], 30)
    assert qa['outcome'] == 'REVIEW_REQUIRED'
    assert 'bad_timestamp' in kinds(qa, 'blockers')
    if variant != 'earlier_overrun':
        assert qa['correction'] is None


def test_raw_schema_cannot_hide_a_decoder_row_behind_a_valid_projection():
    a = chunk(0, 5, row(0, 5, 'texto normal'), raw=True)
    a['raw']['transcription'].append({'offsets': {'from': 5000, 'to': 9000}, 'text': 'erro'})
    _, qa = assess([a], 5)
    assert 'invalid_raw_transcript' in kinds(qa, 'blockers')


def test_confirmed_quiet_conflict_is_detected_on_original_rows_before_merging():
    a = row(597, 599.5, 'A função renal')
    b = row(598.2, 599.4, 'A função renal')
    c = row(600, 603, 'Como prosseguimos')
    _, qa = assess([chunk(0, 600, a, silence=[(0, 599.7)]),
                    chunk(598, 5, b, c, silence=[(0, 1.7)])], 603)
    assert 'text_during_measured_silence' in kinds(qa, 'warnings')


def test_chunk_edge_quiet_that_conflicts_with_other_recording_is_not_proof():
    a = row(596, 599.7, 'Primeira explicação')
    b = row(598.2, 599.4, 'Outra explicação')
    c = row(600, 603, 'Como prosseguimos')
    _, qa = assess([chunk(0, 600, a, silence=[(0, 596)]),
                    chunk(598, 5, b, c, silence=[(0, 1.7)])], 603)
    assert qa['passed']
    assert 'text_during_measured_silence' not in kinds(qa, 'blockers')
    assert 'uncertain_silence_overlap' in kinds(qa, 'warnings')


def test_gaps_use_supported_quiet_not_raw_wall_time_or_speech_inference():
    a, b = row(0, 2, 'introdução'), row(30, 35, 'continuação')
    result, qa = assess([chunk(0, 35, a, b, silence=[(2, 30)])], 35)
    assert result == [a, b] and qa['outcome'] == 'APPROVED'
    _, qa = assess([chunk(0, 35, a, b, silence=[(3, 19)])], 35)
    assert qa['outcome'] == 'APPROVED_WITH_WARNING'
    assert 'unsupported_coverage_gap' in kinds(qa, 'warnings')
    _, qa = assess([chunk(0, 35, a, b)], 35)
    assert 'unsupported_coverage_gap' in kinds(qa, 'blockers')


def test_many_unsupported_gaps_below_the_single_gap_warning_require_review():
    rows = [row(i * 8, i * 8 + 1, f'Registro {i}') for i in range(75)]
    result, qa = assess([chunk(0, 600, *rows)], 600)
    assert result == rows
    assert qa['outcome'] == 'REVIEW_REQUIRED'
    assert qa['blockers'] == [{'kind': 'unsupported_coverage_total', 'total_s': 525.0,
                               'gap_count': 75, 'limit_s': 40.0}]
    assert qa['metrics']['unsupported_coverage_s'] == 525.0


def test_aggregate_excludes_quiet_and_allows_small_timestamp_seams():
    rows = [row(i * 6, i * 6 + 5.5, f'Registro {i}') for i in range(100)]
    _, qa = assess([chunk(0, 600, *rows)], 600)
    assert qa['metrics']['unsupported_coverage_s'] == 50.0
    assert qa['outcome'] == 'APPROVED'

    rows = [row(i * 8, i * 8 + 1, f'Registro {i}') for i in range(75)]
    quiet = [(i * 8 + 1, (i + 1) * 8) for i in range(70)]
    _, qa = assess([chunk(0, 600, *rows, silence=quiet)], 600)
    assert qa['metrics']['unsupported_coverage_s'] == 35.0
    assert qa['outcome'] == 'APPROVED'


def test_silent_chunk_does_not_require_invented_transcript_rows():
    speech = row(600, 608, 'A aula começa aqui')
    result, qa = assess([chunk(0, 600, silence=[(0, 600)]),
                         chunk(598, 10, speech, silence=[(0, 2)])], 608)
    assert result == [speech] and qa['outcome'] == 'APPROVED'


def test_small_didactic_repetition_is_preserved_but_severe_loop_blocks():
    phrase = 'a função renal'
    once, twice = row(0, 3, phrase), row(3, 6, phrase)
    result, qa = assess([chunk(0, 6, once, twice)], 6)
    assert result == [once, twice] and qa['outcome'] == 'APPROVED_WITH_WARNING'
    longer = [row(i * 3, i * 3 + 3, phrase) for i in range(5)]
    result, qa = assess([chunk(0, 15, *longer)], 15)
    assert result == longer and qa['outcome'] == 'APPROVED_WITH_WARNING'
    assert 'ngram_repetition' in kinds(qa, 'warnings')

    # A sustained decoder loop is a real blocker, not a normal oral repetition.
    severe = [row(i * 3, i * 3 + 3, phrase) for i in range(20)]
    result, qa = assess([chunk(0, 60, *severe)], 60)
    assert result == severe and qa['outcome'] == 'REVIEW_REQUIRED'
    assert 'ngram_repetition' in kinds(qa, 'blockers')


def test_reliable_quiet_at_the_measured_audio_edges_can_block_text():
    result, qa = assess([chunk(0, 10, row(0, 10, 'texto em silêncio'), silence=[(0, 10)])], 10)
    assert result == [row(0, 10, 'texto em silêncio')]
    assert 'text_during_measured_silence' in kinds(qa, 'blockers')


def test_small_frame_tail_does_not_make_valid_measured_quiet_invalid():
    _, qa = assess([chunk(0, 10, row(0, 5, 'introdução'),
                         actual=10.02, silence=[(5, 10.02)])], 10)
    assert qa['outcome'] == 'APPROVED'
    assert qa['metrics']['measured_quiet_s'] == 5


def test_losing_most_of_a_short_recording_without_quiet_requires_review():
    _, qa = assess([chunk(0, 19, row(0, 2, 'introdução'))], 19)
    assert 'unsupported_coverage_gap' in kinds(qa, 'blockers')


def test_cross_segment_match_does_not_merge_token_groups_with_disjoint_time():
    # Combined envelopes overlap, but "um dois" lies in different parts of
    # the shared window. Those words cannot safely be declared duplicates.
    a, b = row(597, 598.7, 'explicação um dois'), row(599.2, 600, 'três quatro')
    c = row(598.9, 603, 'um dois três quatro e cinco')
    result, qa = assess([chunk(0, 600, a, b, silence=[(0, 597)]), chunk(598, 5, c)], 603)
    assert result == [a, c, b]
    assert 'ambiguous_overlap' in kinds(qa, 'warnings')


def test_repeated_exact_phrase_in_a_boundary_row_makes_the_match_ambiguous():
    a = row(597, 600, 'a função renal a função renal')
    b = row(598, 603, 'a função renal, depois prosseguimos')
    result, qa = assess([chunk(0, 600, a, silence=[(0, 597)]), chunk(598, 5, b)], 603)
    assert result == [a, b]
    assert 'ambiguous_overlap' in kinds(qa, 'warnings')


def test_short_repetitions_and_ordinary_small_gaps_do_not_hide_lectures():
    rows = [row(i * 10, i * 10 + 9, f'Registro {i}: seguimos a explicação.') for i in range(60)]
    result, qa = assess([chunk(0, 600, *rows)], 600)
    assert result == rows
    assert qa['outcome'] == 'APPROVED_WITH_WARNING'
    assert 'unsupported_coverage_total' in kinds(qa, 'warnings')
    assert not qa['blockers']


def test_sustained_missing_coverage_remains_blocked():
    result, qa = assess([chunk(0, 600, row(0, 10, 'Início da explicação.'))], 600)
    assert result
    assert 'unsupported_coverage_total' in kinds(qa, 'blockers')
    assert 'unsupported_coverage_gap' in kinds(qa, 'blockers')


def test_minor_decoder_timestamp_rounding_is_not_a_content_failure():
    rows = [row(0, 5, 'Início da aula.'), row(5, 10.02, 'Fim do bloco.')]
    result, qa = assess([chunk(0, 10, *rows, raw=True)], 10)
    assert qa['passed'] and qa['outcome'] == 'APPROVED_WITH_WARNING'
    assert result[-1]['end'] == 10.0
    assert 'timestamp_rounding' in kinds(qa, 'warnings')
    _, qa = assess([chunk(0, 10, *rows, raw=False)], 10)
    assert 'bad_timestamp' in kinds(qa, 'blockers')


def test_small_text_during_measured_quiet_is_warning_but_long_text_blocks():
    _, short = assess([chunk(0, 3, row(0, 3, 'Explicação curta.'), silence=[(0, 3)])], 3)
    assert short['passed'] and 'text_during_measured_silence' in kinds(short, 'warnings')
    _, long = assess([chunk(0, 10, row(0, 10, 'Explicação longa.'), silence=[(0, 10)])], 10)
    assert not long['passed'] and 'text_during_measured_silence' in kinds(long, 'blockers')
