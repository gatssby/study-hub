from copy import deepcopy

from fo_hub.acoustic_candidate import overlap_candidate
from fo_hub.stitching import stitch_chunks
from fo_hub.transcription import classify_qa, qa_segments
from fo_hub.worker import parse_whisper


def artifact(repeated_start=600):
    def chunk(offset, duration, rows):
        raw = {'transcription': [{'offsets': {'from': start, 'to': end}, 'text': text}
                                 for start, end, text in rows]}
        return {'offset_s': offset, 'duration_s': duration, 'raw': raw,
                'segments': parse_whisper(raw, offset), 'silence': []}
    chunks = [chunk(0, 20, [(0, 10000, 'fala inicial'), (18600, 19200, 'exemplo')]),
              chunk(18, 12, [(repeated_start, repeated_start + 600, 'exemplo'),
                             (2000, 12000, 'outra fala')])]
    stitched = stitch_chunks(chunks)
    segments = stitched['segments']
    qa = qa_segments(segments, 30)
    for flag in qa['flags']:
        flag['origin'] = 'stitched_text'
    qa['flags'].extend({**f, 'origin': 'stitching'} for f in stitched['flags'])
    return {'chunks': chunks, 'segments': segments, 'duration_s': 30,
            'qa': classify_qa(qa, segments, 30)}


def test_private_candidate_is_an_exact_drop_but_agreement_does_not_clear_it():
    art = artifact(620)
    before = deepcopy(art)
    windows = [{'start': 15., 'end': 22., 'audio_seconds': 7., 'pcm_sha256': 'f' * 64,
                'classification': 'inconclusive_disagreement'}]
    candidate = overlap_candidate(art, windows)
    assert candidate is not None
    assert candidate['excluded_stitched_index'] == 2
    assert candidate['qa']['passed']
    assert candidate['acoustic_status'] == 'requires_independent_listening'
    assert art == before


def test_no_candidate_without_source_window_or_for_disjoint_repetitions():
    assert overlap_candidate(artifact(620), []) is None
    assert overlap_candidate(artifact(1300), [{'start': 15., 'end': 22., 'audio_seconds': 7.,
                                              'pcm_sha256': 'f' * 64}]) is None


def test_candidate_protects_other_blockers_and_requires_exact_raw_provenance():
    windows = [{'start': 15., 'end': 22., 'audio_seconds': 7., 'pcm_sha256': 'f' * 64}]
    art = artifact(620)
    art['chunks'][1]['raw']['transcription'][0]['text'] = ' exemplo'
    assert overlap_candidate(art, windows) is None
    art = artifact(620)
    art['qa']['blockers'].append({'kind': 'language_mismatch'})
    assert overlap_candidate(art, windows) is None
