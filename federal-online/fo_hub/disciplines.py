"""Discipline normalisation for round-robin scheduling.

Catalog subjects are heterogeneous ("Biologia I", "Aulas Gerais" + front
"Física", "Aprofundamento - Extras" + module path). We map each lesson to one
canonical discipline using whole-word, accent-insensitive matching on subject,
then front, then module path. Unknown groups become "Outros" instead of being
guessed into an academic discipline.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Mapping

# Order matters only for ties inside one field; first match wins per field.
_ACADEMIC = (
    ('Biologia', ('biologia',)),
    ('Física', ('fisica',)),
    ('Química', ('quimica',)),
    ('Matemática', ('matematica',)),
    ('Literatura', ('literatura',)),
    ('Português', ('portugues',)),
    ('Redação', ('redacao',)),
    ('História', ('historia',)),
    ('Geografia', ('geografia',)),
    ('Filosofia', ('filosofia',)),
    ('Sociologia', ('sociologia',)),
    ('Inglês', ('ingles',)),
    ('Espanhol', ('espanhol',)),
)
_STUDY = ('metodo', 'metodos de estudo', 'anki', 'flashcards', 'pomodoro', 'cornell', 'feynman',
          'caderno de erros', 'diario dos aprovados', 'dicas finais')
_SIMULADOS = ('simulado', 'simuladao', 'mini simulados')
_GENERIC = ('aulas gerais', 'aulas', 'aprofundamento', 'conteudos extras', 'especificas',
            'disciplinas opcionais', 'resolucao de provas')


def _norm(value: Any) -> str:
    text = unicodedata.normalize('NFKD', str(value or '')).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', text.lower()).strip()


def _has(text: str, token: str) -> bool:
    return re.search(r'(?<![a-z])' + re.escape(token) + r'(?![a-z])', text) is not None


def _academic(text: str) -> str | None:
    for name, tokens in _ACADEMIC:
        if any(_has(text, t) for t in tokens):
            return name
    return None


def discipline_for(subject: Any, front: Any = None, module: Any = None) -> str:
    s, f, m = _norm(subject), _norm(front), _norm(module)
    if 'ciencias basica' in s:
        return 'Ciências Básicas'
    for field in (s, f):
        hit = _academic(field)
        if hit:
            return hit
    for field in (s, f, m):
        if any(_has(field, t) for t in _SIMULADOS):
            return 'Simulados'
    for field in (s, f, m):
        if any(_has(field, t) for t in _STUDY):
            return 'Métodos de Estudo'
    # Generic containers: only then trust the module path segments.
    for part in m.split('>'):
        hit = _academic(part.strip())
        if hit:
            return hit
    if s in _GENERIC or not s:
        return 'Outros'
    return 'Outros'


_ROMAN = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5}


def pedagogical_key(row: Mapping[str, Any]) -> tuple:
    """Stable catalog order: level (I/II/III), numbered lessons, extras, title."""
    subject = _norm(row.get('subject'))
    level_match = re.search(r'(?<![a-z])(iii|ii|iv|v|i)$', subject)
    level = _ROMAN[level_match.group(1)] if level_match else 0
    title = _norm(row.get('title'))
    order = row.get('ordem')
    number = re.match(r'aula\s*(\d+)', title)
    if isinstance(order, int):
        seq = (0, order)
    elif number:
        seq = (0, int(number.group(1)))
    else:
        seq = (1, 0)
    module = _norm(row.get('module'))
    # Same lesson slot: theory first, then its exercise resolution.
    kind = 1 if _has(module, 'exercicios') or _has(subject, 'exercicios') else 0
    track = re.sub(r'\b(teoria|exercicios)\b', '', module).strip(' ->')
    return (level, track, seq, kind, title, str(row.get('lesson_id') or ''))
