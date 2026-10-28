"""Synthetic counterexamples from independent review; no real identity data."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fo_hub.pdf_privacy import sanitize_page, sanitize_text


@pytest.mark.parametrize('label', ['Nome', 'Nome completo', 'Aluno', 'Titular', 'Proprietário'])
@pytest.mark.parametrize('prefix', ['CPF: 123.456.789-00', 'Exemplo literal [DADO REMOVIDO]'])
def test_ambiguous_name_field_preserves_academic_line_and_blocks(label, prefix):
    academic = f'{label}: Isaac Newton; F = m*a; 9,81 m/s²'
    source = prefix + '\n' + academic + '\nConservação da energia.'
    cleaned, _ = sanitize_text(source)
    assert academic in cleaned  # Blocking must not destroy the saved academic content.
    page = sanitize_page(source)
    assert page.exposure == 'blocked'
    assert page.text == ''


def test_multiline_identity_never_gets_partially_redacted_and_released():
    source = 'Aluno: Pessoa\nSintetica Inventada\nCPF: 123.456.789-00\nBiologia celular.'
    cleaned, _ = sanitize_text(source)
    assert 'Aluno: Pessoa\nSintetica Inventada' in cleaned
    assert sanitize_page(source).exposure == 'blocked'


def test_ambiguous_cpf_line_does_not_consume_academic_numbers_or_operators():
    source = 'CPF: 1234 9.81 / 2 - 17\nEnunciado de exercício.'
    cleaned, _ = sanitize_text(source)
    assert source == cleaned
    assert sanitize_page(source).exposure == 'blocked'


@pytest.mark.parametrize('label', ['Aluno', 'Nome', 'Titular', 'Proprietário'])
def test_fullwidth_colon_identity_is_blocked_without_text_deletion(label):
    source = f'{label}： Pessoa Sintetica\nConteúdo acadêmico suficiente.'
    assert sanitize_text(source)[0] == source
    assert sanitize_page(source).exposure == 'blocked'


def test_legacy_redacted_name_marker_is_not_proof_of_lossless_redaction():
    source = 'Nome: [DADO REMOVIDO]\nLinha seguinte pode ser continuação da identidade.'
    assert sanitize_text(source)[0] == source
    assert sanitize_page(source).exposure == 'blocked'
