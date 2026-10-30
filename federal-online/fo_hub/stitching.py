"""Conservative stitching of absolute-time ASR chunks; never runs inference."""
from __future__ import annotations

from copy import deepcopy
import re
import unicodedata

_WORD = re.compile(r"[+−-]?\d+(?:[.,]\d+)?|\w[\w\u0300-\u036f]*|[=<>±×÷%+−-]", re.UNICODE)


def _tokens(text):
    return [(unicodedata.normalize("NFC", m.group()).casefold(), m.start(), m.end())
            for m in _WORD.finditer(text)]


_NEVER_SKIP = {"não", "nao", "nem", "nunca", "jamais", "sem", "tampouco", "nenhum", "nenhuma"}


def _fold(token):
    return "".join(c for c in unicodedata.normalize("NFD", token) if not unicodedata.combining(c))


def _truncation_echo(skipped, counterpart):
    """True only when ``skipped`` plausibly mis-hears the tail of ``counterpart``.

    A chunk cut mid-word yields only the word's ending ("-tina" of
    "queratina" heard as "proteína"): require a shared accent-folded ending of
    at least three letters. Negations/quantifiers are never skippable, and
    numbers/operators never match, so conflicting content stays flagged.
    """
    if skipped in _NEVER_SKIP or not skipped.isalpha() or not counterpart.isalpha():
        return False
    a, b = _fold(skipped), _fold(counterpart)
    common = 0
    while common < min(len(a), len(b)) and a[-1 - common] == b[-1 - common]:
        common += 1
    return common >= 3


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
                skipped = left_counterpart = None
                if n < 3 and right and len(rt) > 1 and abs(incoming[0]["start"] - chunk["offset_s"]) <= 0.3:
                    # A chunk starting mid-word decodes a truncated first token
                    # ("-tina" -> "proteína"). Skip exactly that one token only
                    # when the remainder is an unambiguous >=3-token match.
                    lead = [n2 for n2 in range(1, min(len(lt), len(rt) - 1) + 1)
                            if [t[0][0] for t in lt[-n2:]] == [t[0][0] for t in rt[1:n2 + 1]]]
                    n2 = max(lead, default=0)
                    # The left chunk must hold a token right before the matched
                    # suffix: that is the complete word the truncated token echoes.
                    if (n2 >= 3 and len(lt) > n2 and len(lead) == 1
                            and len({t[0][0] for t in rt[1:n2 + 1]}) >= 3
                            and _truncation_echo(rt[0][0][0], lt[-n2 - 1][0][0])):
                        left_counterpart = lt[-n2 - 1][0][0]
                        skipped, rt, n, matches = rt[0], rt[1:], n2, [n2]
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
                    if skipped is not None:
                        # Auditable: the truncated duplicate token inside the
                        # acoustic overlap; the left chunk retains the full word.
                        decisions[-1]["skipped_leading_token"] = skipped[0][0]
                        decisions[-1]["left_counterpart_token"] = left_counterpart
                elif left and right:
                    flags.append({"chunk_idx": index, "kind": "ambiguous_overlap",
                                  "start": overlap_start, "end": overlap_end,
                                  "matched_tokens": n})
                    decisions.append({"chunk_idx": index, "action": "retain_ambiguous",
                                      "matched_tokens": n})
        output.extend(incoming)
        previous = chunk
    return {"segments": output, "flags": flags, "decisions": decisions}
