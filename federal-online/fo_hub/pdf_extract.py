"""Conservative structured PDF extraction; coordinates are origins, not glyph boxes.

No OCR, formula reconstruction, or speculative table conversion is performed.
Blocked pages retain no text in any output representation.
"""
from __future__ import annotations

import re
import unicodedata
from statistics import median

from pypdf import PdfReader

from .pdf_identity import content_identity, strip_watermark_streams
from .pdf_privacy import CPF_RE, NAME_FIELD_RE, UNRESOLVED_CPF_RE, sanitize_page


def _join_lines(runs):
    """Merge consecutive stream-order fragments on one baseline; never reorder."""
    lines = []
    for run in runs:
        prev = lines[-1] if lines else None
        if prev and '\n' not in prev['text'] and '\n' not in run['text']:
            size = max(prev['size'], run['size'], 1.0)
            x, y = run['bbox_approx'][:2]
            end = prev['bbox_approx'][2]
            if abs(y - prev['bbox_approx'][1]) <= size * .5 and -size <= x - end <= size * 3:
                prev['text'] += ' ' + run['text']
                prev['bbox_approx'][2] = x + len(run['text']) * run['size'] * .5
                continue
        x = run['bbox_approx'][0]
        lines.append(dict(run, bbox_approx=[x, run['bbox_approx'][1],
                                            x + len(run['text']) * run['size'] * .5, run['bbox_approx'][1]]))
    runs[:] = lines


def _order(runs, width):
    """Require repeated origins AND a conservative estimated clear gutter."""
    xs = sorted(set(r['bbox_approx'][0] for r in runs))
    gaps = [(b - a, (a + b) / 2) for a, b in zip(xs, xs[1:])]
    if not gaps:
        return 1, []
    gap, split = max(gaps)
    if gap < width * .22:
        return 1, []
    left = [r for r in runs if r['bbox_approx'][0] < split]
    right = [r for r in runs if r['bbox_approx'][0] >= split]
    clear = (len(left) >= 2 and len(right) >= 2 and
             max(r['bbox_approx'][0] + max(map(len, r['text'].splitlines())) * r['size'] * .65 for r in left)
             < min(r['bbox_approx'][0] for r in right) - width * .04)
    if not clear:
        return 1, ['reading_order_uncertain']
    runs[:] = sorted(left, key=lambda r: -r['bbox_approx'][1]) + sorted(right, key=lambda r: -r['bbox_approx'][1])
    return 2, []


def _structure(runs):
    base = median([r['size'] for r in runs]) if runs else 12
    blocks, lines = [], []
    for run in runs:
        for text in run['text'].splitlines():
            text = text.strip()
            if not text:
                continue
            kind = 'paragraph'
            if re.match(r'^\d+[.)]\s', text):
                kind = 'question'
            elif re.match(r'^(?:[a-e]\)|\([A-E]\))\s', text):
                kind = 'alternative'
            elif re.match(r'^(?:Figura|Tabela)\s+\d+[.:]', text, re.I):
                kind = 'caption'
            elif re.match(r'^Figura\s+\d+', text, re.I):
                kind = 'figure_ref'
            elif run['size'] >= base * 1.4 and len(text) < 120:
                kind = 'heading'
            elif re.search(r'symbol|math|cmmi|cmsy', run['font'], re.I):
                kind = 'formula_candidate'
            blocks.append(dict(kind=kind, text=text, bbox_approx=run['bbox_approx']))
            lines.append(('# ' if kind == 'heading' else '') + text)
    return blocks, '\n'.join(lines)


def _images(page):
    """Count actual image Do invocations, including repeated and nested Forms."""
    from pypdf.generic import ContentStream
    result = []

    def walk(content, resources, depth=0):
        if content is None or depth > 16:
            return
        resources = resources.get_object() if resources is not None else {}
        objects = resources.get('/XObject', {})
        objects = objects.get_object() if hasattr(objects, 'get_object') else objects
        for operands, op in ContentStream(content, page.pdf).operations:
            if op != b'Do' or not operands or operands[0] not in objects:
                continue
            obj = objects[operands[0]].get_object()
            if obj.get('/Subtype') == '/Image':
                result.append(dict(kind='image', small_image=int(obj.get('/Width', 0)) <= 256 and int(obj.get('/Height', 0)) <= 256,
                                   bbox_approx=None))
            elif obj.get('/Subtype') == '/Form':
                walk(obj, obj.get('/Resources', resources), depth + 1)
    walk(page.get_contents(), page.get('/Resources'))
    return result


def extract_document(path, *, material_meta):
    identity = content_identity(path)
    pages = []
    for number, page in enumerate(PdfReader(path).pages, 1):
        removed = bool(strip_watermark_streams(page))
        runs = []

        def visit(text, cm, tm, font, size):
            if text.strip():
                x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
                y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
                runs.append({'text': unicodedata.normalize('NFC', text.strip()), 'bbox_approx': [x, y, x, y],
                             'size': float(size), 'font': str((font or {}).get('/BaseFont', ''))})

        page.extract_text(visitor_text=visit)
        _join_lines(runs)
        columns, order_flags = _order(runs, float(page.mediabox.width))
        blocks, markdown = _structure(runs)
        text = '\n'.join(r['text'] for r in runs).strip()
        images = _images(page)
        formulas = [image for image in images if image['small_image']] + [dict(kind='math_font', text=r['text'], bbox_approx=r['bbox_approx'])
                             for r in runs if re.search(r'symbol|math|cmmi|cmsy', r['font'], re.I)]
        figures = {'count': len(images), 'references': re.findall(r'\bFigura\s+\d+', text, re.I)}
        flags = order_flags
        quality = 'ocr_needed' if len(text) < 40 and images else ('text' if len(text) >= 24 else 'low_text')
        checked = sanitize_page(text)
        if not removed and any(pattern.search(text) for pattern in (CPF_RE, NAME_FIELD_RE, UNRESOLVED_CPF_RE)):
            flags.append('watermark_unproven')
        if text and (checked.text != text or checked.exposure != 'text_only'):
            flags.append('residual_pii')
        if any(flag in flags for flag in ('watermark_unproven', 'residual_pii')):
            quality, text, markdown, blocks, formulas = 'blocked', '', '', [], []
            figures['references'] = []
        pages.append(dict(page=number, text=text, markdown=markdown, blocks=blocks,
                          figures=figures, formula_candidates=formulas,
                          columns=columns, quality=quality,
                          flags=flags, watermark_removed=removed, unmarked=not removed))
    return dict(material_id='pdf_' + identity['content_sha256'][:24], identity=identity,
                material_meta=dict(material_meta), pages=pages,
                markdown='\n\n'.join(f"<!-- page {p['page']} -->\n\n{p['markdown']}" for p in pages))
