import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fo_hub.transcription import qa_segments


def seg(start, end, text):
    return {"start": start, "end": end, "text": text}


def chunk(offset, duration, *segments):
    return {"offset_s": offset, "duration_s": duration, "segments": list(segments)}


def test_stitches_normalized_boundary_without_inventing_token_times():
    from fo_hub.stitching import stitch_chunks
    chunks = [chunk(0, 600, seg(596, 600, "Explique a função renal.")),
              chunk(598, 600, seg(598, 603, "A função renal, controla água."))]
    original = copy.deepcopy(chunks)
    result = stitch_chunks(chunks)
    assert chunks == original
    assert result["segments"] == [seg(596, 603, "Explique a função renal. controla água.")]
    assert result["flags"] == []
    assert result["decisions"][0]["action"] == "merge_overlap"
    assert result["decisions"][0]["matched_tokens"] == 3


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_qa_rejects_nonfinite_timestamps_without_poisoning_coverage(value):
    result = qa_segments([seg(0, value, "conteúdo"), seg(1, 2, "normal")])
    assert any(f["kind"] == "bad_timestamp" for f in result["flags"])
    assert result["metrics"]["covered_until_s"] == 2


def test_qa_flags_repeated_phrases_not_only_single_tokens():
    text = "a função renal " * 5
    result = qa_segments([seg(0, 5, text)])
    assert "ngram_repetition" in {f["kind"] for f in result["flags"]}
    assert result["segments"][0]["text"] == text


def test_qa_silence_is_informational_not_failed_content():
    result = qa_segments([seg(30, 31, "fala legítima")], duration_s=90)
    assert result["passed"]
    assert {f["kind"] for f in result["flags"]} == {"silence_gap"}


def test_temporally_disjoint_repeated_phrase_is_preserved():
    from fo_hub.stitching import stitch_chunks
    chunks = [chunk(0, 600, seg(598, 598.5, "a função renal")),
              chunk(598, 600, seg(599, 600, "a função renal"))]
    result = stitch_chunks(chunks)
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
    from fo_hub.stitching import stitch_chunks
    chunks = [chunk(0, 600, seg(597, 600, left)),
              chunk(598, 600, seg(598, 603, right))]
    result = stitch_chunks(chunks)
    assert result["segments"] == chunks[0]["segments"] + chunks[1]["segments"]
    assert result["flags"][0]["kind"] == "ambiguous_overlap"
    assert result["decisions"][0]["action"] == "retain_ambiguous"


def test_overlap_across_segment_boundaries_preserves_continuation():
    from fo_hub.stitching import stitch_chunks
    chunks = [chunk(0, 600, seg(596, 599, "Explique a função"), seg(599, 600, "renal")),
              chunk(598, 600, seg(598, 599, "a função"),
                    seg(599, 603, "renal controla água"), seg(603, 604, "Depois."))]
    result = stitch_chunks(chunks)
    assert result["segments"] == [seg(596, 603, "Explique a função renal controla água"),
                                   seg(603, 604, "Depois.")]
    assert qa_segments(result["segments"])["passed"]


def test_no_acoustic_overlap_does_not_deduplicate_text():
    from fo_hub.stitching import stitch_chunks
    chunks = [chunk(0, 600, seg(597, 600, "a função renal")),
              chunk(600, 600, seg(600, 603, "a função renal"))]
    result = stitch_chunks(chunks)
    assert len(result["segments"]) == 2
    assert result["flags"] == []
    assert stitch_chunks([]) == {"segments": [], "flags": [], "decisions": []}


def test_qa_rejects_nonfinite_start():
    result = qa_segments([seg(float("nan"), 5, "palavras")])
    assert not result["passed"]
    assert result["metrics"]["covered_until_s"] == 0


def test_unicode_normalization_preserves_original_character_offsets():
    import unicodedata
    from fo_hub.stitching import stitch_chunks
    right = unicodedata.normalize("NFD", "a função renal controla água")
    result = stitch_chunks([chunk(0, 600, seg(596, 600, "a função renal")),
                            chunk(598, 600, seg(598, 603, right))])
    assert result["segments"] == [seg(596, 603, "a função renal " +
                                                    unicodedata.normalize("NFD", "controla água"))]


@pytest.mark.parametrize("left,right", [
    (seg(8, 10, "cai para -5 graus hoje"), seg(12, 14, "cai para -5 graus hoje")),
    (seg(6, 8, "então cai para -5 graus hoje"), seg(8, 11, "cai para -5 graus hoje e depois sobe")),
])
def test_repeated_boundary_with_timestamp_drift_is_preserved_for_review(left, right):
    from fo_hub.stitching import stitch_chunks
    chunks = [chunk(0, 10, left), chunk(8, 10, right)]
    original = copy.deepcopy(chunks)
    result = stitch_chunks(chunks)
    assert chunks == original
    assert result["segments"] == [left, right]
    assert result["flags"][0]["kind"] == "boundary_timestamp_drift"
    assert result["flags"][0]["matched_tokens"] == 5
    assert result["decisions"][0]["action"] == "retain_drift_ambiguity"


def test_boundary_drift_does_not_invent_duplicate_match_or_change_scientific_sign():
    from fo_hub.stitching import stitch_chunks
    result = stitch_chunks([chunk(0, 10, seg(8, 10, "cai para -5 graus hoje")),
                            chunk(8, 10, seg(12, 14, "cai para 5 graus hoje"))])
    assert len(result["segments"]) == 2
    assert not result["flags"]


def test_truncated_leading_word_at_chunk_start_merges_real_bioquimica_boundary():
    """Regression: fo_135c415d8080927f 1794-1796 s. The right chunk starts mid
    'queratina' and decodes the fragment as 'proteína'; isolated re-decode of
    1793.4-1796.1 hears the sentence once. The full left word is retained."""
    from fo_hub.stitching import stitch_chunks
    left = seg(1793.52, 1796.0, "a queratina do cabelo é uma proteína.")
    right = seg(1794.0, 1800.76, "proteína do cabelo é uma proteína né então o colágeno é uma proteína agora tem algumas")
    chunks = [chunk(1196, 600, seg(1790.0, 1793.42, "mas os anticorpos são proteínas,"), left),
              chunk(1794, 354.284, right, seg(1800.76, 1806.66, "proteínas que são mais especiais"))]
    original = copy.deepcopy(chunks)
    result = stitch_chunks(chunks)
    assert chunks == original
    assert result["flags"] == []
    merged = result["segments"][1]
    assert merged["start"] == 1793.52 and merged["end"] == 1800.76
    assert merged["text"].startswith("a queratina do cabelo é uma proteína.")
    assert merged["text"].count("cabelo") == 1 and "colágeno" in merged["text"]
    decision = result["decisions"][0]
    assert decision["action"] == "merge_overlap" and decision["matched_tokens"] == 5
    assert decision["skipped_leading_token"] == "proteína"
    assert decision["left_counterpart_token"] == "queratina"
    assert qa_segments(result["segments"])["passed"]


@pytest.mark.parametrize("right_start,right_text", [
    # Not at the chunk start: a real word, never skipped.
    (1795.0, "proteína do cabelo é uma proteína né"),
    # Remainder too short to be unequivocal.
    (1794.0, "proteína uma proteína né então"),
    # Remainder repeats: ambiguous alignment.
    (1794.0, "x é é é é né"),
])
def test_leading_token_skip_requires_chunk_start_and_unequivocal_remainder(right_start, right_text):
    from fo_hub.stitching import stitch_chunks
    left_text = "a queratina do cabelo é uma proteína" if "x" not in right_text else "a é é é é"
    chunks = [chunk(1196, 600, seg(1793.52, 1796.0, left_text)),
              chunk(1794, 354.284, seg(right_start, 1800.76, right_text))]
    result = stitch_chunks(chunks)
    assert result["segments"] == chunks[0]["segments"] + chunks[1]["segments"]
    assert all("skipped_leading_token" not in d for d in result["decisions"])


@pytest.mark.parametrize("lead", ["não", "nunca", "42", "insulina"])
def test_conflicting_leading_word_is_never_skipped(lead):
    """Review finding: skipping must require a truncation echo, so a negation
    or unrelated word at a chunk start can never be silently dropped."""
    from fo_hub.stitching import stitch_chunks
    left = chunk(0, 10, seg(8.0, 10.0, "A glicose aumenta a pressão arterial."))
    right = chunk(8, 10, seg(8.0, 12.0, f"{lead} aumenta a pressão arterial. Agora seguimos."))
    out = stitch_chunks([left, right])
    text = " ".join(s["text"] for s in out["segments"])
    assert lead in text
    assert any(f["kind"] == "ambiguous_overlap" for f in out["flags"])
    assert not any(d.get("skipped_leading_token") for d in out["decisions"])
