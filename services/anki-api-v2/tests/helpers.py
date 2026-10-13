"""Synthetic Anki collections for tests. Never points at production data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from anki.collection import Collection

TEST_TOKEN = "t" * 40
SYNTHETIC_MEDIA_NAME = "imagem 1.jpg"
SYNTHETIC_MEDIA_BYTES = b"\xff\xd8\xff\xe0synthetic-jpeg"


@dataclass(frozen=True)
class Fixture:
    path: Path
    basic_note_id: str
    cloze_note_id: str
    reversed_note_id: str
    endo_deck_id: str
    cardio_deck_id: str
    default_deck_id: str


def build_synthetic_collection(path: Path) -> Fixture:
    col = Collection(str(path))
    try:
        basic = col.models.by_name("Basic")
        cloze = col.models.by_name("Cloze")
        reversed_model = col.models.by_name("Basic (and reversed card)")
        endo = col.decks.id("Medicina::Endocrino")
        cardio = col.decks.id("Medicina::Cardio")
        default = col.decks.id("Default")

        basic_note = col.new_note(basic)
        basic_note["Front"] = "Tireoide?"
        basic_note["Back"] = "TSH"
        basic_note.tags = ["endo", "alpha"]
        col.add_note(basic_note, endo)

        cloze_note = col.new_note(cloze)
        cloze_note["Text"] = "Fase {{c1::A}}"
        cloze_note["Back Extra"] = ""
        col.add_note(cloze_note, cardio)

        reversed_note = col.new_note(reversed_model)
        reversed_note["Front"] = "Pergunta"
        reversed_note["Back"] = "Resposta"
        col.add_note(reversed_note, endo)

        col.media.write_data(SYNTHETIC_MEDIA_NAME, SYNTHETIC_MEDIA_BYTES)

        return Fixture(
            path=path,
            basic_note_id=str(basic_note.id),
            cloze_note_id=str(cloze_note.id),
            reversed_note_id=str(reversed_note.id),
            endo_deck_id=str(endo),
            cardio_deck_id=str(cardio),
            default_deck_id=str(default),
        )
    finally:
        col.close()
