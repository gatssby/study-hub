"""Conservative stitching of absolute-time ASR chunks; never runs inference."""
from __future__ import annotations

from copy import deepcopy
import re
import unicodedata

_WORD = re.compile(r"[+−-]?\d+(?:[.,]\d+)?|\w[\w\u0300-\u036f]*|[=<>±×÷%+−-]", re.UNICODE)


def _tokens(text):
    return [(unicodedata.normalize("NFC", m.group()).casefold(), m.start(), m.end())
            for m in _WORD.finditer(text)]


def stitch_chunks(chunks):
    """Return ``segments``, ``flags`` and auditable boundary ``decisions``.

    Input chunks have offset_s, duration_s and absolute-time segments. Input is
    never mutated. Exact normalized suffix/prefix matches are merged using the
    original segment envelope, NOT estimated token timestamps. Ambiguous text
    remains verbatim and is flagged. Output order is input order, not a sort.
    """
    output, flags, decisions = [], [], []
    previous = None
    for index, chunk in enumerate(chunks):
        incoming = deepcopy(chunk["segments"])
        if previous is not None and output and incoming:
            overlap_start = max(previous["offset_s"], chunk["offset_s"])
            overlap_end = min(previous["offset_s"] + previous["duration_s"],
                              chunk["offset_s"] + chunk["duration_s"])
            if overlap_start < overlap_end:
                left = []
                for pos in range(len(output) - 1, -1, -1):
                    s = output[pos]
                    if not (s["start"] < overlap_end and s["end"] > overlap_start):
                        break
                    left.insert(0, pos)
                right = []
                for pos, s in enumerate(incoming):
                    if not (s["start"] < overlap_end and s["end"] > overlap_start):
                        break
                    right.append(pos)
                lt = [(token, pos) for pos in left for token in _tokens(output[pos]["text"])]
                rt = [(token, pos) for pos in right for token in _tokens(incoming[pos]["text"])]
                matches = [n for n in range(1, min(len(lt), len(rt)) + 1)
                           if [t[0][0] for t in lt[-n:]] == [t[0][0] for t in rt[:n]]]
                n = max(matches, default=0)
                left_matched = output[lt[-n][1]:] if n else [output[left[-1]]] if left else []
                right_matched = incoming[:rt[n - 1][1] + 1] if n else incoming[:1]
                temporal_match = bool(left_matched and right_matched and
                    max(min(s["start"] for s in left_matched),
                        min(s["start"] for s in right_matched)) <
                    min(max(s["end"] for s in left_matched),
                        max(s["end"] for s in right_matched)))
                if not temporal_match:
                    # Textual boundary evidence must not disappear merely because
                    # decoder times drifted outside the known acoustic overlap.
                    # Do not merge disjoint envelopes: a repeated utterance can be
                    # legitimate. Preserve both and ask for review only when the
                    # edge phrase matches but at least one time envelope misses
                    # the shared window. Disjoint utterances *inside* that window
                    # retain their original timing without a false duplicate flag.
                    edge_left = [t[0] for t in _tokens(output[-1]["text"])]
                    edge_right = [t[0] for t in _tokens(incoming[0]["text"])]
                    edge_n = max((count for count in range(3, min(len(edge_left), len(edge_right)) + 1)
                                  if edge_left[-count:] == edge_right[:count]
                                  and len(set(edge_right[:count])) >= 3), default=0)
                    edges_share_window = all(s["start"] < overlap_end and s["end"] > overlap_start
                                             for s in (output[-1], incoming[0]))
                    if edge_n and not edges_share_window:
                        flags.append({"chunk_idx": index, "kind": "boundary_timestamp_drift",
                                      "start": min(overlap_start, output[-1]["start"], incoming[0]["start"]),
                                      "end": max(overlap_end, output[-1]["end"], incoming[0]["end"]),
                                      "matched_tokens": edge_n})
                        decisions.append({"chunk_idx": index, "action": "retain_drift_ambiguity",
                                          "matched_tokens": edge_n})
                    output.extend(incoming)
                    previous = chunk
                    continue
                if n >= 3 and len({t[0][0] for t in rt[:n]}) >= 3 and len(matches) == 1:
                    first, last = lt[-n][1], rt[n - 1][1]
                    originals = output[first:] + incoming[:last + 1]
                    prefix = " ".join(s["text"].strip() for s in output[first:])
                    tail = incoming[last]["text"][rt[n - 1][0][2]:]
                    # Punctuation belongs to the already retained duplicate phrase.
                    tail = re.sub(r"^[\s,.;:!?]+", "", tail)
                    merged = deepcopy(output[first])
                    merged.update(start=min(s["start"] for s in originals),
                                  end=max(s["end"] for s in originals),
                                  text=prefix + (" " + tail if tail else ""))
                    output[first:] = [merged]
                    incoming = incoming[last + 1:]
                    decisions.append({"chunk_idx": index, "action": "merge_overlap",
                                      "matched_tokens": n, "left_segment_idx": first,
                                      "right_segment_count": last + 1,
                                      "timestamp_policy": "original_segment_envelope"})
                elif left and right:
                    flags.append({"chunk_idx": index, "kind": "ambiguous_overlap",
                                  "start": overlap_start, "end": overlap_end,
                                  "matched_tokens": n})
                    decisions.append({"chunk_idx": index, "action": "retain_ambiguous",
                                      "matched_tokens": n})
        output.extend(incoming)
        previous = chunk
    return {"segments": output, "flags": flags, "decisions": decisions}
