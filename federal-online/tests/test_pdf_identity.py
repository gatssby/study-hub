"""Content identity of portal PDFs ignores only the per-download watermark stream.

Synthetic fixtures only: the watermark text below is fake.
"""
import io

from pypdf import PdfWriter
from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, NameObject, NumberObject

from fo_hub.pdf_identity import content_identity, strip_watermark_streams


def _pdf(body: bytes, watermark: bytes | None, gs_name: str = '/GS-9750469207', pages: int = 2) -> bytes:
    w = PdfWriter()
    for i in range(pages):
        page = w.add_blank_page(width=300, height=300)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                                 NameObject('/Subtype'): NameObject('/Type1'),
                                 NameObject('/BaseFont'): NameObject('/Helvetica')})
        resources = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): w._add_object(font)})})
        streams = []
        s = DecodedStreamObject()
        s.set_data(b'BT /F1 12 Tf 20 250 Td (' + body + b' p%d) Tj ET' % i)
        streams.append(w._add_object(s))
        if watermark is not None:
            gs = DictionaryObject({NameObject('/Type'): NameObject('/ExtGState'),
                                   NameObject('/ca'): NumberObject(0)})
            resources[NameObject('/ExtGState')] = DictionaryObject({NameObject(gs_name): w._add_object(gs)})
            m = DecodedStreamObject()
            m.set_data(b'q ' + gs_name.encode() + b' gs BT /F1 30 Tf 0.5 0.86 -0.86 0.5 50 50 Tm ('
                       + watermark + b') Tj ET Q')
            streams.append(w._add_object(m))
        page[NameObject('/Resources')] = resources
        page[NameObject('/Contents')] = ArrayObject(streams)
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


def _write(tmp_path, name, data):
    p = tmp_path / name
    p.write_bytes(data)
    return p


def test_watermark_only_difference_keeps_content_identity(tmp_path):
    a = _write(tmp_path, 'a.pdf', _pdf(b'Mitose e meiose', b'Fulano Teste 00000000000'))
    b = _write(tmp_path, 'b.pdf', _pdf(b'Mitose e meiose', b'Beltrana Ficticia 11111111111'))
    ia, ib = content_identity(a), content_identity(b)
    assert ia['sha256'] != ib['sha256']
    assert ia['content_sha256'] == ib['content_sha256']
    assert ia['pages'] == 2 and ia['watermark_pages'] == 2 and ia['unmarked_pages'] == 0


def test_body_difference_changes_content_identity(tmp_path):
    a = _write(tmp_path, 'a.pdf', _pdf(b'Mitose e meiose', b'Fulano Teste 00000000000'))
    b = _write(tmp_path, 'b.pdf', _pdf(b'Mitose e meiose revisada', b'Fulano Teste 00000000000'))
    assert content_identity(a)['content_sha256'] != content_identity(b)['content_sha256']


def test_unmarked_pdf_is_hashed_whole_and_reported(tmp_path):
    a = _write(tmp_path, 'a.pdf', _pdf(b'Sem marca', None))
    ident = content_identity(a)
    assert ident['watermark_pages'] == 0 and ident['unmarked_pages'] == 2
    assert len(ident['content_sha256']) == 64


def test_marker_name_must_be_exact_pattern(tmp_path):
    # A legitimate graphics state with another name is academic content, not watermark.
    a = _write(tmp_path, 'a.pdf', _pdf(b'Corpo', b'texto legitimo A', gs_name='/GS6'))
    b = _write(tmp_path, 'b.pdf', _pdf(b'Corpo', b'texto legitimo B', gs_name='/GS6'))
    assert content_identity(a)['content_sha256'] != content_identity(b)['content_sha256']
    assert content_identity(a)['watermark_pages'] == 0


def test_strip_removes_only_watermark_stream_text(tmp_path):
    from pypdf import PdfReader
    a = _write(tmp_path, 'a.pdf', _pdf(b'Mitose e meiose', b'Fulano Teste 00000000000'))
    reader = PdfReader(a)
    removed = strip_watermark_streams(reader.pages[0])
    text = reader.pages[0].extract_text()
    assert removed == 1
    assert 'Mitose e meiose' in text and 'Fulano' not in text and '0000' not in text


def test_not_a_pdf_is_rejected(tmp_path):
    p = _write(tmp_path, 'x.pdf', b'<html>login expired</html>')
    try:
        content_identity(p)
    except ValueError as exc:
        assert 'PDF' in str(exc)
    else:
        raise AssertionError('non-PDF accepted')
