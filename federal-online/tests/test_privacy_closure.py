"""Synthetic privacy regressions; never copy production identifiers here."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fo_hub.api import create_app
from fo_hub.pdf_privacy import sanitize_page
from fo_hub.store import FOStore


@pytest.mark.parametrize("exposure,quality,version", [
    ("text_only", "text", 1), ("text_only", "text", 2),
    ("unexpected", "text", 3), ("text_only", "unknown", 3),
    ("blocked", "text", 3),
])
def test_api_fails_closed_for_stale_or_unknown_review(tmp_path, exposure, quality, version):
    db = tmp_path / "hub.db"
    store = FOStore(db)
    store.upsert_material({"material_id": "m", "title": "Synthetic"})
    store.set_pdf_pages("m", ["untrusted synthetic text"])
    with store.conn:
        store.conn.execute("INSERT INTO pdf_page_quality VALUES(?,?,?,?,?,?,?,?)",
                           ("m", 1, quality, exposure, 24, 0, "now", version))
    result = TestClient(create_app(db)).get("/fo/materials/m/pdf-text").json()
    assert result["pages"][0]["text"] == ""
    assert result["pages"][0]["exposure"] == "blocked"


@pytest.mark.parametrize("identifier", ["529.982.247-25", "52998224725", "529.982.\n247-25"])
def test_repeated_unlabelled_watermark_name_is_removed(identifier):
    watermark = f"PESSOA FICTICIA {identifier} "
    page = sanitize_page("Conteudo didatico sobre celulas e tecidos.\n" + watermark * 5)
    assert "PESSOA FICTICIA" not in page.text
    assert "529" not in page.text
    assert "celulas" in page.text
    assert page.exposure == "text_only"


def test_single_unlabelled_identity_is_blocked_not_assumed_safe():
    page = sanitize_page("Conteudo didatico.\nPESSOA FICTICIA 52998224725")
    assert page.exposure == "blocked"
    assert page.text == ""


def test_invalid_labelled_cpf_does_not_exempt_an_unredacted_name():
    text = 'Conteudo da aula de direito constitucional.\nCPF: 111.222.333-44\nNome: PESSOA FICTICIA'
    page = sanitize_page(text)
    assert 'PESSOA FICTICIA' not in page.text
    assert 'constitucional' in page.text


def test_redaction_on_one_label_never_exempts_another_label():
    page = sanitize_page('Aula didatica.\nCPF: [DADO REMOVIDO]\nNome: PESSOA FICTICIA')
    assert 'PESSOA FICTICIA' not in page.text


def test_previously_redacted_v2_text_gets_name_review_without_pdf_reextraction():
    text = "Conteudo didatico preservado.\n" + "PESSOA FICTICIA [IDENTIFICADOR REMOVIDO] " * 5
    page = sanitize_page(text)
    assert page.exposure == "text_only"
    assert "PESSOA FICTICIA" not in page.text
    assert "didatico" in page.text


def test_quality_row_does_not_allow_unsanitized_identifier(tmp_path):
    db = tmp_path / "hub.db"
    store = FOStore(db)
    store.upsert_material({"material_id": "m"})
    store.set_pdf_pages("m", ["PESSOA FICTICIA 52998224725"])
    with store.conn:
        store.conn.execute("INSERT INTO pdf_page_quality VALUES(?,?,?,?,?,?,?,?)",
                           ("m", 1, "text", "text_only", 24, 0, "now", 3))
    result = TestClient(create_app(db)).get("/fo/materials/m/pdf-text").json()
    assert result["pages"][0]["text"] == ""
    assert result["pages"][0]["exposure"] == "blocked"


@pytest.mark.parametrize("text", [
    "Os valores didaticos sao 12345678901 e 11111111111, sem CPF valido.",
    "O documento historico descreve o aluno e a funcao do titular.",
    "A palavra nome indica uma classe gramatical neste exemplo didatico.",
])
def test_educational_numbers_and_generic_words_are_preserved(text):
    assert sanitize_page(text).text == text
