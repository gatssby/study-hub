"""Private, non-publishable projections for source-audio adjudication."""
from copy import deepcopy
import math
import re

from .stitching import stitch_chunks
from .transcription import classify_qa, qa_segments
from .worker import normalize_final_padding, parse_whisper, reconcile_silent_gaps

SCHEMA = 1


def _overlap_candidate(artifact, windows):
    duration, segments, qa = (artifact[k] for k in ('duration_s', 'segments', 'qa'))
    blockers = qa['blockers']
    if len(blockers) != 1 or (blockers[0]['kind'], blockers[0].get('origin')) != (
            'duplicate_segment', 'stitched_text'):
        return None
    idx = blockers[0]['idx']
    if not 0 < idx < len(segments):
        return None
    left, right = segments[idx - 1:idx + 1]
    if not left['text'] or left['text'] != right['text']:
        return None
    start, end = min(left['start'], right['start']), max(left['end'], right['end'])
    if max(left['start'], right['start']) >= min(left['end'], right['end']):
        return None
    evidence = next((w for w in windows if w['start'] <= max(0, start - 1)
                     and min(duration, end + 1) <= w['end']
                     and re.fullmatch('[0-9a-f]{64}', w.get('pcm_sha256', ''))
                     and math.isclose(w['audio_seconds'], w['end'] - w['start'], abs_tol=.002)), None)
    if evidence is None:
        return None

    chunks = artifact['chunks']
    raw_chunks = [{**c, 'segments': parse_whisper(c['raw'], c['offset_s'])} for c in chunks]
    replay, replay_segments, _ = normalize_final_padding(
        raw_chunks, stitch_chunks(raw_chunks)['segments'], duration)
    if replay_segments != segments or replay != chunks:
        return None
    positions = [[(i, j) for i, c in enumerate(chunks) for j, row in enumerate(c['segments'])
                  if row == target] for target in (left, right)]
    if any(len(found) != 1 for found in positions):
        return None
    (li, lj), (ri, rj) = (p[0] for p in positions)
    if ri != li + 1 or rj != 0 or lj != len(chunks[li]['segments']) - 1:
        return None
    a, b = chunks[li], chunks[ri]
    if (start < max(a['offset_s'], b['offset_s'])
            or end > min(a['offset_s'] + a['duration_s'], b['offset_s'] + b['duration_s'])
            or a['raw']['transcription'][lj]['text'] != b['raw']['transcription'][rj]['text']):
        return None
    original_stitch = stitch_chunks(chunks)
    projected_chunks = list(chunks)
    projected_chunks[ri] = {**b, 'segments': b['segments'][1:]}
    projected = stitch_chunks(projected_chunks)
    proposed = segments[:idx] + segments[idx + 1:]
    if projected['segments'] != proposed:
        return None
    if (projected['flags'] != [f for f in original_stitch['flags']
                               if not (f['chunk_idx'] == ri and f['kind'] == 'ambiguous_overlap')]
            or [d for d in projected['decisions'] if d['chunk_idx'] != ri]
            != [d for d in original_stitch['decisions'] if d['chunk_idx'] != ri]
            or any(d['chunk_idx'] == ri for d in projected['decisions'])):
        return None

    fresh = qa_segments(proposed, duration)
    reconcile_silent_gaps(fresh, proposed, projected_chunks, duration)
    fresh['flags'] = [{**f, 'origin': 'stitched_text'} for f in fresh['flags']]
    fresh['flags'].extend({**f, 'origin': 'stitching'} for f in projected['flags'])
    fresh['observations'] = deepcopy(qa.get('observations', []))
    for observation in fresh['observations']:
        if observation.get('idx') == idx:
            return None
        if observation.get('idx', -1) > idx:
            observation['idx'] -= 1
    for flag in deepcopy(qa['flags']):
        origin = flag.get('origin')
        if origin == 'stitching' and flag.get('chunk_idx') == ri and flag['kind'] == 'ambiguous_overlap':
            continue
        if origin == 'stitched_text':
            if flag.get('idx') == idx:
                if flag['kind'] not in {'duplicate_segment', 'non_monotonic'}:
                    return None
                continue
            if flag.get('idx', -1) > idx:
                flag['idx'] -= 1
        if not any(all(f.get(k) == v for k, v in flag.items() if k not in {'severity', 'policy_reason'})
                   for f in fresh['flags']):
            fresh['flags'].append(flag)
    verdict = classify_qa(fresh, proposed, duration)
    return {'schema': SCHEMA, 'kind': 'adjacent_chunk_overlap_duplicate',
            'excluded_stitched_index': idx, 'raw_rows': [[li, lj], [ri, rj]],
            'audio': {k: evidence[k] for k in ('start', 'end', 'pcm_sha256')},
            'qa': {'policy': verdict['policy_version'], 'passed': verdict['passed'],
                   'blocker_kinds': [f['kind'] for f in verdict['blockers']]},
            'acoustic_status': 'requires_independent_listening', 'publishable': False}


def overlap_candidate(artifact, windows):
    """Require exact decoder provenance and one-row restitch; never clear acoustic review."""
    try:
        return _overlap_candidate(artifact, windows)
    except (KeyError, TypeError, ValueError, IndexError, OverflowError):
        return None
