"""Only synthetic identities; never copy private PDF watermark values here."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fo_hub.pdf_privacy import sanitize_page


def test_student_identity_label_without_cpf_is_blocked():
    page = sanitize_page('Aluno: Pessoa Sintetica\nConteudo didatico de biologia.')
    assert page.exposure == 'blocked'
    assert page.text == ''


def test_student_identity_label_with_cpf_is_redacted():
    page = sanitize_page('Aluno: Pessoa Sintetica\nCPF: 123.456.789-00\nBiologia celular.')
    assert 'Pessoa Sintetica' not in page.text
    assert page.exposure == 'text_only'


def test_unpunctuated_cpf_watermark_is_blocked():
    page = sanitize_page('CPF 123.456.789-00\nConteudo didatico sem identificacao adicional.')
    assert page.exposure == 'blocked'
    assert page.text == ''


def test_empty_name_label_does_not_eat_next_line():
    page = sanitize_page('Nome:\nCPF: 123.456.789-00\nConteudo didatico de biologia.')
    assert page.exposure == 'blocked'


def test_cpf_as_teaching_topic_is_not_an_identity_label():
    page = sanitize_page('O CPF e um cadastro de pessoas fisicas usado no Brasil.')
    assert page.exposure == 'text_only'
