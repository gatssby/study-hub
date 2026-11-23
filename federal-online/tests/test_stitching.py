import copy
import sys
import unicodedata
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fo_hub.stitching import stitch_chunks


def stitch(chunks):
    return stitch_chunks(chunks, exact=True)


def seg(start, end, text):
    return {"start": start, "end": end, "text": text}


def chunk(offset, duration, *segments):
    return {"offset_s": offset, "duration_s": duration, "segments": list(segments)}


def test_stitches_normalized_boundary_without_inventing_token_times():
    chunks = [chunk(0, 600, seg(596, 600, "Explique a função renal.")),
              chunk(598, 600, seg(598, 603, "A função renal, controla água."))]
    original = copy.deepcopy(chunks)
    result = stitch(chunks)
    assert chunks == original
    assert result["segments"] == [seg(596, 603, "Explique a função renal. controla água.")]
    assert result["flags"] == []
    assert result["decisions"][0]["action"] == "merge_overlap"
    assert result["decisions"][0]["matched_tokens"] == 3


def test_temporally_disjoint_repeated_phrase_is_preserved():
    chunks = [chunk(0, 600, seg(598, 598.5, "a função renal")),
              chunk(598, 600, seg(599, 600, "a função renal"))]
    result = stitch(chunks)
    assert len(result["segments"]) == 2
    assert result["flags"] == []


@pytest.mark.parametrize("left,right", [
    ("sim", "sim continua"),
    ("sim sim sim", "sim sim sim continua"),
    ("um dois três um dois três", "um dois três um dois três continua"),
    ("a função renal", "a função cardíaca"),
    ("a função", "renal controla água"),
])
def test_ambiguous_overlap_retains_every_word(left, right):
    chunks = [chunk(0, 600, seg(597, 600, left)),
              chunk(598, 600, seg(598, 603, right))]
    result = stitch(chunks)
    assert result["segments"] == chunks[0]["segments"] + chunks[1]["segments"]
    assert result["flags"][0]["kind"] == "ambiguous_overlap"
    assert result["decisions"][0]["action"] == "retain_ambiguous"


def test_overlap_across_segment_boundaries_preserves_continuation():
    chunks = [chunk(0, 600, seg(596, 599, "Explique a função"), seg(599, 600, "renal")),
              chunk(598, 600, seg(598, 599, "a função"),
                    seg(599, 603, "renal controla água"), seg(603, 604, "Depois."))]
    result = stitch(chunks)
    assert result["segments"] == [seg(596, 603, "Explique a função renal controla água"),
                                   seg(603, 604, "Depois.")]


def test_no_acoustic_overlap_does_not_deduplicate_text():
    chunks = [chunk(0, 600, seg(597, 600, "a função renal")),
              chunk(600, 600, seg(600, 603, "a função renal"))]
    result = stitch(chunks)
    assert len(result["segments"]) == 2
    assert result["flags"] == []
    assert stitch([]) == {"segments": [], "flags": [], "decisions": []}


def test_unicode_normalization_preserves_original_character_offsets():
    right = unicodedata.normalize("NFD", "a função renal controla água")
    result = stitch([chunk(0, 600, seg(596, 600, "a função renal")),
                     chunk(598, 600, seg(598, 603, right))])
    assert result["segments"] == [seg(596, 603, "a função renal " +
                                   unicodedata.normalize("NFD", "controla água"))]


@pytest.mark.parametrize("left,right", [
    (seg(8, 10, "cai para -5 graus hoje"), seg(12, 14, "cai para -5 graus hoje")),
    (seg(6, 8, "então cai para -5 graus hoje"), seg(8, 11, "cai para -5 graus hoje e depois sobe")),
])
def test_repeated_boundary_with_timestamp_drift_is_preserved_for_review(left, right):
    chunks = [chunk(0, 10, left), chunk(8, 10, right)]
    original = copy.deepcopy(chunks)
    result = stitch(chunks)
    assert chunks == original
    assert result["segments"] == [left, right]
    assert result["flags"][0]["kind"] == "boundary_timestamp_drift"
    assert result["flags"][0]["matched_tokens"] == 5
    assert result["decisions"][0]["action"] == "retain_drift_ambiguity"


def test_boundary_drift_does_not_invent_duplicate_match_or_change_scientific_sign():
    chunks = [chunk(0, 10, seg(8, 10, "cai para -5 graus hoje")),
              chunk(8, 10, seg(12, 14, "cai para 5 graus hoje"))]
    result = stitch(chunks)
    assert result["segments"] == chunks[0]["segments"] + chunks[1]["segments"]
    assert not result["flags"]


def test_similar_leading_word_at_chunk_start_is_not_guessed_away():
    left = seg(1793.52, 1796.0, "a queratina do cabelo é uma proteína.")
    right = seg(1794.0, 1800.76, "proteína do cabelo é uma proteína né então o colágeno é uma proteína agora tem algumas")
    chunks = [chunk(1196, 600, seg(1790.0, 1793.42, "mas os anticorpos são proteínas,"), left),
              chunk(1794, 354.284, right, seg(1800.76, 1806.66, "proteínas que são mais especiais"))]
    original = copy.deepcopy(chunks)
    result = stitch(chunks)
    assert chunks == original
    assert result["segments"] == chunks[0]["segments"] + chunks[1]["segments"]
    assert result["flags"][0]["kind"] == "ambiguous_overlap"
    assert result["decisions"][0]["action"] == "retain_ambiguous"


@pytest.mark.parametrize("lead", ["não", "nunca", "42", "insulina"])
def test_conflicting_leading_word_is_never_skipped(lead):
    left = chunk(0, 10, seg(8.0, 10.0, "A glicose aumenta a pressão arterial."))
    right = chunk(8, 10, seg(8.0, 12.0, f"{lead} aumenta a pressão arterial. Agora seguimos."))
    out = stitch([left, right])
    assert out["segments"] == left["segments"] + right["segments"]
    assert any(f["kind"] == "ambiguous_overlap" for f in out["flags"])
