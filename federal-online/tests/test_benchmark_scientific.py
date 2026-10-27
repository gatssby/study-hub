"""Synthetic scientific-value regressions; never model quality evidence."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fo_hub.benchmark import normalize, score


def test_sign_changes_are_not_erased_by_scoring_normalization():
    assert score('a temperatura é -5 graus', 'a temperatura é 5 graus')['wer'] > 0
    assert score('a temperatura é -5 graus', 'a temperatura é +5 graus')['cer'] > 0


def test_inequality_changes_are_scored():
    assert score('pH < 7', 'pH > 7')['wer'] > 0


def test_numeric_spelling_and_accents_are_preserved():
    assert normalize('AÇÃO: 1,5 mol; -2 °C.') == 'ação 1,5 mol -2 c'
