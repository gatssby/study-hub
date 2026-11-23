"""Deterministic FO publication QA from a single decode and measured quiet."""
from __future__ import annotations

from bisect import bisect_right
from collections.abc import Mapping, Sequence
import math
from typing import Any, TypeGuard

from .repetition import repetition_candidates
from .stitching import stitch_chunks

_EPS = 1e-9  # arithmetic only, not timestamp or sample tolerance
_AUDIO_DURATION_TOLERANCE_S = 0.05  # container/audio frame tail and extraction rounding
_SILENCE_EDGE_S = 0.05  # do not assert silence from uncertain detector edges
_GAP_AGGREGATE_TOLERANCE_S = 0.5  # ignore small timestamp seams, not whole seconds
_GAP_WARN_S = 8.0
_GAP_BLOCK_S = 20.0  # retain the established 20 s bound for unsupported gaps
_LOCAL_OVERLAP_S = 2.5


def _number(value):
    if type(value) in (int, float):
        try:
            if math.isfinite(value):
                return float(value)
        except OverflowError:
            pass
    return None


def _array(value: object) -> TypeGuard[list[Any] | tuple[Any, ...]]:
    return isinstance(value, (list, tuple))


def _merge(intervals):
    merged = []
    for start, end in sorted(intervals):
        if end <= start:
            continue
        if merged and start <= merged[-1][1] + _EPS:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def _subtract(intervals, covered):
    """Subtract two sorted, disjoint unions in time order."""
    pos = 0
    for start, end in intervals:
        while pos < len(covered) and covered[pos][1] <= start + _EPS:
            pos += 1
        while pos < len(covered) and covered[pos][0] < end - _EPS:
            left, right = covered[pos]
            if left > start + _EPS:
                yield start, left
            start = max(start, right)
            if start >= end - _EPS:
                break
            pos += 1
        if end > start + _EPS:
            yield start, end


def _quiet_intervals(value, offset, actual, bound):
    if not _array(value):
        return None
    quiet = []
    for pair in value:
        if not _array(pair) or len(pair) != 2:
            return None
        left, right = map(_number, pair)
        if left is None or right is None or not 0 <= left < right <= actual + _EPS:
            return None
        quiet.append((offset + left, min(offset + right, bound)))
    return _merge(quiet)


def _raw_matches(raw, rows, offset):
    transcription = raw.get('transcription') if isinstance(raw, Mapping) else None
    if not _array(transcription) or len(transcription) != len(rows):
        return False
    for record, row in zip(transcription, rows):
        if not isinstance(record, Mapping) or not isinstance(row, Mapping):
            return False
        offsets, text = record.get('offsets'), record.get('text')
        if not isinstance(offsets, Mapping) or not isinstance(text, str):
            return False
        start, end = _number(offsets.get('from')), _number(offsets.get('to'))
        if (start is None or end is None or start < 0 or end < start
                or row.get('start') != offset + start / 1000
                or row.get('end') != offset + end / 1000 or row.get('text') != text.strip()):
            return False
    return True


def _padding_end(start, end, bound, duration):
    # Match the known ~30 s whisper.cpp final-row signature, rather than
    # treating an arbitrary timestamp beyond the audio as truncatable.
    return (start < bound and end > max(bound, duration) + 1
            and abs((end - start) - 30.0) <= 0.5
            and abs(bound - duration) <= _AUDIO_DURATION_TOLERANCE_S + _EPS)


def _contains(intervals, start, end):
    # The latest interval starting no later than the row is the only possible
    # match, because intervals were merged into a disjoint union.
    pos = bisect_right(intervals, (start + _EPS, math.inf)) - 1
    return pos >= 0 and end <= intervals[pos][1] + _EPS


def _overlaps(rows):
    covered_end = 0.0
    for i, row in enumerate(rows):
        overlap = min(row['end'], covered_end) - row['start']
        if overlap > 0.05 + _EPS:
            yield {'kind': 'non_monotonic', 'idx': i, 'start': row['start'],
                   'end': min(row['end'], covered_end), 'overlap_s': overlap}
        covered_end = max(covered_end, row['end'])


def _repeat_pairs(rows):
    pairs = [i for i in range(1, len(rows))
             if rows[i]['text'].strip().casefold() == rows[i - 1]['text'].strip().casefold()]
    isolated = len(pairs) <= 3 and all(b != a + 1 for a, b in zip(pairs, pairs[1:]))
    for i in pairs:
        left, right = rows[i - 1:i + 1]
        gap = right['start'] - left['end']
        yield i, isolated and 0 <= gap <= 20 and all(
            r['end'] - r['start'] <= 5 and len(r['text'].split()) <= 12 for r in (left, right))


def assess(chunks: Sequence[Mapping], duration_s: float, *, chunk_s: float,
           overlap_s: float) -> tuple[list[dict], dict]:
    """Return ordered transcript rows and a JSON-safe QA report; never mutate evidence.

    Chunks are in decoding order with absolute segment times, actual WAV
    duration in seconds (16 kHz samples / 16000), and relative near-digital
    silence intervals. An optional original whisper.cpp ``raw`` payload must
    match its segment projection and is required for a final-end correction.
    Absence of quiet evidence is not evidence of speech or a quality score.
    Rejected output is for review only; the unmodified chunks retain raw evidence.
    """
    blockers, warnings = [], []
    working, prepared, quiet_all, nonquiet_all = [], [], [], []
    correction = None
    duration, size, overlap = map(_number, (duration_s, chunk_s, overlap_s))
    if duration is None or duration <= 0:
        blockers.append({'kind': 'invalid_duration'})
    if size is None or overlap is None or not 0 <= overlap < size:
        blockers.append({'kind': 'invalid_chunk_configuration'})
    if not _array(chunks):
        blockers.append({'kind': 'invalid_chunks'})
    if blockers or duration is None or size is None or overlap is None or not _array(chunks):
        return [], _report(blockers, warnings, correction, [])

    expected = 0.0
    for ci, source in enumerate(chunks):
        if not isinstance(source, Mapping):
            blockers.append({'kind': 'invalid_chunk', 'chunk_idx': ci})
            break
        offset, length, actual = (_number(source.get(key)) for key in
                                  ('offset_s', 'duration_s', 'audio_duration_s'))
        planned = min(size, duration - expected)
        if (offset is None or length is None or offset < 0 or length <= 0
                or planned <= 0 or abs(offset - expected) > _EPS or abs(length - planned) > _EPS):
            blockers.append({'kind': 'invalid_chunk_layout', 'chunk_idx': ci, 'expected_offset_s': expected})
            break
        final = expected + planned >= duration - _EPS
        expected = duration if final else expected + (size - overlap)
        if actual is None or actual <= 0:
            blockers.append({'kind': 'invalid_audio_duration', 'chunk_idx': ci})
            continue
        deficit = length - actual
        if abs(deficit) > _AUDIO_DURATION_TOLERANCE_S + _EPS:
            blockers.append({'kind': 'truncated_audio' if deficit > 0 else 'unexpected_audio_length',
                             'chunk_idx': ci, 'expected_s': length, 'measured_s': actual})
        bound = min(duration, offset + length, offset + actual)
        quiet = _quiet_intervals(source.get('silence'), offset, actual, bound)
        if quiet is None:
            blockers.append({'kind': 'invalid_silence', 'chunk_idx': ci})
            quiet = []
        quiet_all.extend(quiet)
        nonquiet_all.extend(_subtract([(offset, bound)], quiet))

        incoming = source.get('segments')
        if not _array(incoming):
            blockers.append({'kind': 'invalid_segments', 'chunk_idx': ci})
            incoming = []
        raw_verified = 'raw' in source and _raw_matches(source['raw'], incoming, offset)
        if 'raw' in source and not raw_verified:
            blockers.append({'kind': 'invalid_raw_transcript', 'chunk_idx': ci})
        rows = []
        last_start = offset
        for ri, row in enumerate(incoming):
            location = {'chunk_idx': ci, 'idx': ri}
            text = row.get('text') if isinstance(row, Mapping) else None
            if not isinstance(text, str) or not text.strip() or not any(c.isalnum() for c in text):
                blockers.append({'kind': 'invalid_segment', **location})
                continue
            start, end = (_number(row.get(key)) for key in ('start', 'end'))
            if (start is None or end is None or not 0 <= offset <= start < end
                    or start < last_start or start >= bound):
                blockers.append({'kind': 'bad_timestamp', **location})
                continue
            last_start = start
            if end > bound + _EPS:
                if (final and ci == len(chunks) - 1 and ri == len(incoming) - 1 and raw_verified
                        and len(rows) == ri and abs(deficit) <= _AUDIO_DURATION_TOLERANCE_S + _EPS
                        and _padding_end(start, end, bound, duration)):
                    correction = {'kind': 'timestamp_correction', 'chunk_idx': ci, 'local_idx': ri,
                                  'raw_end': end, 'corrected_end': bound, 'bound': bound,
                                  'source': 'final_decoder_padding'}
                    end = bound
                else:
                    blockers.append({'kind': 'bad_timestamp', **location, 'start': start, 'end': end,
                                     'bound': bound})
                    continue
            rows.append({'start': start, 'end': end, 'text': text})
            prepared.append((location, rows[-1], quiet))
        working.append({'offset_s': offset, 'duration_s': bound - offset, 'segments': rows})
        blockers.extend({**f, 'chunk_idx': ci, 'origin': 'decoder'}
                        for f in repetition_candidates(rows)['flags'])

    if expected < duration - _EPS:
        blockers.append({'kind': 'missing_chunk', 'expected_offset_s': expected})
    quiet = list(_subtract(_merge(quiet_all), _merge(nonquiet_all)))
    last_sample = max((c['offset_s'] + c['duration_s'] for c in working), default=0.0)
    reliable_quiet = [(left if left <= _EPS else left + _SILENCE_EDGE_S,
                       right if right >= last_sample - _EPS else right - _SILENCE_EDGE_S)
                      for left, right in quiet if right - left >= 0.5]
    for location, row, local_quiet in prepared:
        start, end = row['start'], row['end']
        # Two recordings of the same time must agree. Incomplete containment,
        # conflicting recordings, and edge-only evidence cannot prove a contradiction.
        if _contains(reliable_quiet, start, end):
            blockers.append({'kind': 'text_during_measured_silence', **location, 'start': start, 'end': end})
        elif _contains(local_quiet, start, end):
            warnings.append({'kind': 'uncertain_silence_overlap', **location, 'start': start, 'end': end})

    stitched = stitch_chunks(working, exact=True)
    segments = sorted(stitched['segments'], key=lambda row: row['start'])
    flags = stitched['flags']
    budget = max(5.0, duration * 0.01)
    overlaps = list(_overlaps(segments))
    # A merge must not hide a decoder's own substantial timestamp overlap.
    for ci, chunk in enumerate(working):
        local = list(_overlaps(chunk['segments']))
        local_total = sum(f['overlap_s'] for f in local)
        blockers.extend({**f, 'chunk_idx': ci, 'origin': 'decoder'} for f in local
                        if f['overlap_s'] > _LOCAL_OVERLAP_S or local_total > budget)
    overlap_total = sum(flag['overlap_s'] for flag in overlaps)
    boundary_total = sum(flag['end'] - flag['start'] for flag in flags)
    for flag in flags + overlaps:
        span = flag.get('overlap_s', flag['end'] - flag['start'])
        target = (warnings if span <= _LOCAL_OVERLAP_S and overlap_total <= budget
                  and boundary_total <= budget else blockers)
        target.append(flag)
    for i, isolated in _repeat_pairs(segments):
        (warnings if isolated else blockers).append({'kind': 'duplicate_segment', 'idx': i})
    if stitched['decisions']:
        blockers.extend({**f, 'origin': 'stitched_text'} for f in repetition_candidates(segments)['flags'])
    elif len(working) > 1:
        # True loops can cross a seam even without a stitch decision.
        for flag in repetition_candidates(segments)['flags']:
            if not any(flag['start'] >= c['offset_s'] and flag['end'] <= c['offset_s'] + c['duration_s']
                       for c in working):
                blockers.append({**flag, 'origin': 'stitched_text'})

    if not segments:
        blockers.append({'kind': 'empty_output'})
    covered = _merge((row['start'], row['end']) for row in segments)
    evidence = _merge(covered + quiet)
    unsupported = list(_subtract([(0.0, duration)], evidence))
    counted = [end - start for start, end in unsupported if end - start > _GAP_AGGREGATE_TOLERANCE_S + _EPS]
    total = math.fsum(counted)
    limit = max(40.0, duration * 0.05)
    if total > limit + _EPS:
        blockers.append({'kind': 'unsupported_coverage_total', 'total_s': total,
                         'gap_count': len(counted), 'limit_s': limit})
    for start, end in unsupported:
        gap = end - start
        if gap >= _GAP_WARN_S:
            material = gap > _GAP_BLOCK_S or (gap >= 15 and gap >= duration * 0.5)
            target = blockers if material else warnings
            target.append({'kind': 'unsupported_coverage_gap', 'start': start, 'end': end, 'gap_s': gap})

    return segments, _report(blockers, warnings, correction, segments,
                             overlap_total_s=overlap_total, boundary_total_s=boundary_total,
                             unsupported_coverage_s=sum(end - start for start, end in unsupported),
                             measured_quiet_s=sum(end - start for start, end in quiet),
                             stitched_boundaries=sum(d['action'] == 'merge_overlap' for d in stitched['decisions']))


def _report(blockers, warnings, correction, segments, **metrics):
    return {'passed': not blockers,
            'outcome': ('REVIEW_REQUIRED' if blockers else 'APPROVED_WITH_WARNING' if warnings else 'APPROVED'),
            'blockers': blockers, 'warnings': warnings, 'correction': correction,
            'metrics': {'segments': len(segments), 'words': sum(len(r['text'].split()) for r in segments),
                        'warning_count': len(warnings), 'blocker_count': len(blockers), **metrics}}
