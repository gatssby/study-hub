import pytest
from test_pdf_identity import _pdf


@pytest.mark.parametrize('body', [b'CPF: 000.000.000-00', b'Nome: Isaac Newton explica a gravidade'])
def test_unproven_identity_fields_block_without_redaction(tmp_path, body):
    from fo_hub.pdf_extract import extract_document
    path = tmp_path / 'unmarked.pdf'
    path.write_bytes(_pdf(body, None))
    page = extract_document(path, material_meta={})['pages'][0]
    assert page['quality'] == 'blocked'
    assert 'watermark_unproven' in page['flags']
    assert page['text'] == page['markdown'] == ''
    assert page['blocks'] == []


def test_residual_identity_blocks_marked_page(tmp_path):
    from fo_hub.pdf_extract import extract_document
    path = tmp_path / 'residual.pdf'
    path.write_bytes(_pdf(b'Nome: Isaac Newton', b'Fake 00000000000'))
    page = extract_document(path, material_meta={})['pages'][0]
    assert page['quality'] == 'blocked'
    assert 'residual_pii' in page['flags']
    assert not page['text']


def positioned_pdf(tmp_path, runs, image=False):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject, NumberObject
    writer = PdfWriter()
    page = writer.add_blank_page(600, 800)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
    resources = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
    def literal(text):
        return text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    data = b'\n'.join(f'BT /F1 {size} Tf 1 0 0 1 {x} {y} Tm ({literal(text)}) Tj ET'.encode() for x, y, size, text in runs)
    if image:
        obj = DecodedStreamObject()
        obj.set_data(b'\x00')
        obj.update({NameObject('/Type'): NameObject('/XObject'), NameObject('/Subtype'): NameObject('/Image'), NameObject('/Width'): NumberObject(1), NameObject('/Height'): NumberObject(1), NameObject('/BitsPerComponent'): NumberObject(8), NameObject('/ColorSpace'): NameObject('/DeviceGray')})
        resources[NameObject('/XObject')] = DictionaryObject({NameObject('/Im1'): writer._add_object(obj)})
        data += b'\nq 10 0 0 10 50 50 cm /Im1 Do /Im1 Do Q'
    stream = DecodedStreamObject()
    stream.set_data(data)
    page[NameObject('/Resources')] = resources
    page[NameObject('/Contents')] = writer._add_object(stream)
    path = tmp_path / 'positions.pdf'
    writer.write(path)
    return path


def test_clear_columns_read_left_then_right(tmp_path):
    from fo_hub.pdf_extract import extract_document
    path = positioned_pdf(tmp_path, [(40, 700, 12, 'Left first'), (350, 700, 12, 'Right first'), (40, 670, 12, 'Left second'), (350, 670, 12, 'Right second')])
    page = extract_document(path, material_meta={})['pages'][0]
    assert page['columns'] == 2
    assert page['text'].index('Left second') < page['text'].index('Right first')


def test_headings_questions_alternatives_and_formulas_preserved(tmp_path):
    from fo_hub.pdf_extract import extract_document
    path = positioned_pdf(tmp_path, [(40, 740, 24, 'BIOLOGIA'), (40, 700, 12, '1. Qual a formula?'), (40, 680, 12, 'a) H2O'), (40, 660, 12, '(B) CO2'), (40, 640, 12, 'Figura 3. Celula')])
    page = extract_document(path, material_meta={})['pages'][0]
    assert page['markdown'].startswith('# BIOLOGIA')
    assert '\n1. Qual' in page['markdown'] and '\na) H2O' in page['markdown'] and '\n(B) CO2' in page['markdown']
    assert {'heading', 'question', 'alternative', 'caption'} <= {b['kind'] for b in page['blocks']}
    assert page['figures']['references'] == ['Figura 3']


def test_small_images_are_counted_per_invocation_and_need_ocr(tmp_path):
    from fo_hub.pdf_extract import extract_document
    page = extract_document(positioned_pdf(tmp_path, [], image=True), material_meta={})['pages'][0]
    assert page['quality'] == 'ocr_needed'
    assert page['figures']['count'] == 2
    assert len(page['formula_candidates']) == 2


def test_ambiguous_columns_keep_original_order(tmp_path):
    from fo_hub.pdf_extract import extract_document
    path = positioned_pdf(tmp_path, [(40, 700, 12, 'A very long academic sentence ' * 4), (350, 700, 12, 'Right first'), (40, 670, 12, 'Left second'), (350, 670, 12, 'Right second')])
    page = extract_document(path, material_meta={})['pages'][0]
    assert page['columns'] == 1
    assert 'reading_order_uncertain' in page['flags']
    assert page['text'].index('Right first') < page['text'].index('Left second')


def test_large_images_not_flagged_as_formula(tmp_path):
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NameObject, NumberObject
    from fo_hub.pdf_extract import extract_document
    path = positioned_pdf(tmp_path, [], image=True)
    reader = PdfReader(path)
    image = reader.pages[0]['/Resources']['/XObject']['/Im1'].get_object()
    image[NameObject('/Width')] = NumberObject(1200)
    writer = PdfWriter()
    writer.add_page(reader.pages[0])
    path = tmp_path / 'large.pdf'
    writer.write(path)
    page = extract_document(path, material_meta={})['pages'][0]
    assert page['figures']['count'] == 2
    assert page['formula_candidates'] == []


def test_watermark_free_document(tmp_path):
    from fo_hub.pdf_extract import extract_document
    path = tmp_path / 'source.pdf'
    path.write_bytes(_pdf(b'Mitose e meiose: conteudo academico preservado.', b'Pessoa Ficticia 000.000.000-00'))
    doc = extract_document(path, material_meta={'title': 'Biologia'})
    assert doc['material_id'] == 'pdf_' + doc['identity']['content_sha256'][:24]
    assert '<!-- page 1 -->' in doc['markdown']
    for page in doc['pages']:
        assert page['watermark_removed'] and not page['unmarked']
        assert page['quality'] == 'text'
        assert 'Mitose' in page['text'] and 'Ficticia' not in page['text']
        assert page['blocks'][0]['bbox_approx']


def test_same_baseline_fragments_form_one_line(tmp_path):
    from fo_hub.pdf_extract import extract_document
    path = positioned_pdf(tmp_path, [(40, 700, 12, 'Velocidade'), (115, 700, 12, 'media'), (40, 680, 12, 'proxima linha')])
    page = extract_document(path, material_meta={})['pages'][0]
    assert page['text'].splitlines() == ['Velocidade media', 'proxima linha']


def test_indented_single_column_is_not_flagged_uncertain(tmp_path):
    from fo_hub.pdf_extract import extract_document
    path = positioned_pdf(tmp_path, [(40, 700, 12, 'Paragrafo um'), (60, 680, 12, 'recuo'), (80, 660, 12, 'mais recuo'), (40, 640, 12, 'fim')])
    page = extract_document(path, material_meta={})['pages'][0]
    assert page['columns'] == 1
    assert 'reading_order_uncertain' not in page['flags']


def test_decomposed_accents_are_normalized_not_blocked(tmp_path, monkeypatch):
    import unicodedata
    from pypdf import PageObject
    from fo_hub.pdf_extract import extract_document
    path = positioned_pdf(tmp_path, [(40, 700, 12, 'placeholder')])
    decomposed = 'Acu\u0301car e reac\u0327o\u0303es quimicas da celula'
    def fake(self, *a, visitor_text=None, **k):
        visitor_text(decomposed, [1, 0, 0, 1, 0, 0], [1, 0, 0, 1, 40, 700], {}, 12)
        return decomposed
    monkeypatch.setattr(PageObject, 'extract_text', fake)
    page = extract_document(path, material_meta={})['pages'][0]
    assert page['quality'] == 'text'
    assert 'residual_pii' not in page['flags']
    assert page['text'] == unicodedata.normalize('NFC', decomposed)
