"""Content identity for Federal Online PDFs.

Every portal download stamps a personalised watermark (name + CPF) as an extra,
last page content stream drawn under a dedicated ExtGState named ``/GS-<digits>``.
Byte SHA-256 therefore changes on every download even when the academic content
is identical. ``content_sha256`` hashes every page stream and XObject except a
stream that is provably that watermark:

* the page declares an ExtGState whose name matches ``/GS-<digits>`` exactly;
* the stream activates that graphics state (``/GS-n gs``);
* it is the last content stream of the page;
* it paints only text (no XObjects, images or path painting).

Anything else is kept, so an academic edit always changes the identity. Pages
without such a stream are counted as ``unmarked_pages`` (never guessed).
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from pypdf.generic import ArrayObject, NameObject

IDENTITY_VERSION = 1
_MARKER = re.compile(r'/GS-\d+')
_PAINT = re.compile(rb'(?:^|\s)(?:Do|BI|re|f\*?|S|s|B\*?|b\*?|sh)(?:\s|$)')


def _streams(page) -> list:
    contents = page.get('/Contents')
    if contents is None:
        return []
    contents = contents.get_object()
    if isinstance(contents, ArrayObject):
        return [s.get_object() for s in contents]
    return [contents]


def _marker_names(page) -> list[str]:
    resources = page.get('/Resources')
    resources = resources.get_object() if resources is not None else {}
    states = resources.get('/ExtGState') if resources else None
    states = states.get_object() if states is not None else {}
    return [str(k) for k in states if _MARKER.fullmatch(str(k))]


def watermark_stream_index(page) -> int | None:
    names = _marker_names(page)
    streams = _streams(page)
    if not names or not streams:
        return None
    data = streams[-1].get_data()
    if not any(re.search(re.escape(n.encode()) + rb'\s+gs\b', data) for n in names):
        return None
    if _PAINT.search(data) or not re.search(rb'T[Jj]', data):
        return None
    return len(streams) - 1


def strip_watermark_streams(page) -> int:
    """Remove the proven watermark stream from an in-memory page. Returns 0/1."""
    idx = watermark_stream_index(page)
    if idx is None:
        return 0
    streams = page['/Contents'].get_object()
    if isinstance(streams, ArrayObject):
        kept = ArrayObject([ref for i, ref in enumerate(streams) if i != idx])
        page[NameObject('/Contents')] = kept
    else:
        page[NameObject('/Contents')] = ArrayObject()
    return 1


def _xobject_digest(resources: Any, h, depth: int = 0) -> None:
    if resources is None or depth > 4:
        return
    resources = resources.get_object()
    xobjects = resources.get('/XObject')
    if xobjects is None:
        return
    xobjects = xobjects.get_object()
    for name in sorted(xobjects):
        obj = xobjects[name].get_object()
        h.update(str(name).encode())
        try:
            h.update(hashlib.sha256(obj.get_data()).digest())
        except Exception:  # undecodable filters: fall back to raw bytes
            h.update(hashlib.sha256(getattr(obj, '_data', b'') or b'').digest())
        _xobject_digest(obj.get('/Resources'), h, depth + 1)


def content_identity(path: str | Path) -> dict:
    path = Path(path)
    raw = hashlib.sha256()
    with path.open('rb') as handle:
        head = handle.read(1024)
        raw.update(head)
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            raw.update(block)
    if b'%PDF-' not in head:
        raise ValueError('not a PDF (missing %PDF- header)')
    reader = PdfReader(str(path))
    content = hashlib.sha256(b'fo-pdf-content-v%d' % IDENTITY_VERSION)
    marked = 0
    pages = len(reader.pages)
    for number, page in enumerate(reader.pages):
        content.update(b'page%d' % number)
        box = page.mediabox
        content.update(repr([float(x) for x in box]).encode())
        skip = watermark_stream_index(page)
        marked += skip is not None
        for i, stream in enumerate(_streams(page)):
            if i == skip:
                continue
            content.update(hashlib.sha256(stream.get_data()).digest())
        _xobject_digest(page.get('/Resources'), content)
    return {'sha256': raw.hexdigest(), 'content_sha256': content.hexdigest(),
            'identity_version': IDENTITY_VERSION, 'size': path.stat().st_size,
            'pages': pages, 'watermark_pages': marked, 'unmarked_pages': pages - marked}
