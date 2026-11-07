"""OCR review triage is advisory, content-free and never approves pages."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fo_hub.ocr import triage_ocr_review

SYNTHETIC_CPF = "529.982.247-25"  # public test-valid CPF, not a person


def test_never_approves_and_returns_no_content():
    text = "Fotossíntese converte energia luminosa em energia química nas plantas verdes."
    result = triage_ocr_review(text)
    assert result["approved"] is False
    assert result["lane"] == "visual_check_text"
    assert "Fotoss" not in json.dumps(result)


def test_formulas_and_signed_numbers_are_preserved_as_math_lane():
    result = triage_ocr_review("v = v0 + a·t  ;  x = -5 + 3t^2  ;  Δs ≥ 0")
    assert result["lane"] == "visual_check_math"
    assert "math_or_numeric" in result["reasons"]


def test_identity_and_contact_hints_route_to_privacy():
    assert triage_ocr_review(f"Lista de física {SYNTHETIC_CPF} questão 3")["lane"] == "privacy_review"
    assert triage_ocr_review("Nome: Pessoa Ficticia\nQuestão 1")["lane"] == "privacy_review"
    assert triage_ocr_review("contato pessoa@example.com sobre a apostila")["lane"] == "privacy_review"
    # invalid CPF-shaped number still flags for human eyes, not auto-release
    assert triage_ocr_review("código 111.222.333-44 da prova")["lane"] == "privacy_review"


def test_empty_and_noisy_pages():
    assert triage_ocr_review("")["lane"] == "empty"
    assert triage_ocr_review("|| ~~ ;; .. ,,")["lane"] == "visual_check_noisy"
