"""Small pure helpers shared by the read and editorial services."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Sequence

from anki.notes import Note

from anki_api_v2.errors import ApiError

REVISION_PREFIX = "r1-"
REVISION_PATTERN = r"^r1-[0-9a-f]{32}$"


def str_id(value: int) -> str:
    return str(int(value))


def parse_id(raw: str, code: str = "invalid_id") -> int:
    # isascii(): str.isdigit() is also true for full-width and other Unicode digits.
    if not raw.isascii() or not raw.isdigit() or len(raw) > 20:
        raise ApiError(422, code, "id must be a positive integer string")
    value = int(raw)
    if value <= 0:
        raise ApiError(422, code, "id must be a positive integer string")
    return value


def parse_ids(raws: Iterable[str]) -> list[int]:
    return [parse_id(raw) for raw in raws]


def note_revision(note: Note, card_ids: Sequence[int]) -> str:
    """Stable content fingerprint used as an optimistic-concurrency token.

    Content based on purpose: `usn` also changes when a sync merely carries the note, and
    `mod` has one-second resolution. Deck placement and scheduling are NOT part of it, so
    moving a card never invalidates a note's revision. The card set is part of it, so a
    delete is guarded against a changed set of derived cards.
    """
    payload = [
        int(note.id),
        int(note.mid),
        [[name, value] for name, value in note.items()],
        sorted(note.tags),
        sorted(int(c) for c in card_ids),
    ]
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return REVISION_PREFIX + digest[:32]
