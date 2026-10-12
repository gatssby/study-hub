"""Public HTTP contract. IDs are always strings in JSON."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

MAX_FIELDS = 50
MAX_TAGS = 50
MAX_FIELD_CHARS = 20_000
MAX_QUERY_CHARS = 1_000

Tag = Annotated[str, StringConstraints(pattern=r"^[^\s\x00-\x1f]{1,100}$")]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NoteTypeOut(BaseModel):
    id: str
    name: str


class FieldOut(BaseModel):
    name: str
    value: str


class NoteOut(BaseModel):
    note_id: str
    note_type: NoteTypeOut
    fields: list[FieldOut]
    tags: list[str]
    card_ids: list[str]
    deck_ids: list[str]


class CardOut(BaseModel):
    card_id: str
    note_id: str
    deck_id: str
    deck_name: str
    template_name: str
    ord: int
    note_type: NoteTypeOut
    question: str = Field(description="Rendered question HTML, as Anki renders it.")
    answer: str = Field(description="Rendered answer HTML, as Anki renders it.")


class DeckOut(BaseModel):
    deck_id: str
    name: str
    card_count: int
    is_filtered: bool


class DeckPage(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool
    items: list[DeckOut]


class SearchRequest(_Strict):
    query: str = Field(min_length=1, max_length=MAX_QUERY_CHARS)
    kind: Literal["notes", "cards"]
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=1_000_000)

    @field_validator("query")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("query must not be blank")
        return stripped


class SearchPage(BaseModel):
    query: str
    kind: Literal["notes", "cards"]
    total: int
    limit: int
    offset: int
    has_more: bool
    items: list[dict[str, str]]


class PatchNoteRequest(_Strict):
    fields: dict[str, str] = Field(default_factory=dict, max_length=MAX_FIELDS)
    add_tags: list[Tag] = Field(default_factory=list, max_length=MAX_TAGS)
    remove_tags: list[Tag] = Field(default_factory=list, max_length=MAX_TAGS)

    @model_validator(mode="after")
    def _non_empty_and_consistent(self) -> PatchNoteRequest:
        if not (self.fields or self.add_tags or self.remove_tags):
            raise ValueError("payload is empty")
        if set(self.add_tags) & set(self.remove_tags):
            raise ValueError("the same tag cannot be added and removed")
        return self


class PatchSyncState(BaseModel):
    before: str
    after: str


class PatchNoteResult(BaseModel):
    note_id: str
    updated_fields: list[str]
    added_tags: list[str]
    removed_tags: list[str]
    sync: PatchSyncState


class SyncRequest(_Strict):
    media: bool = False


class SyncResult(BaseModel):
    collection: str
    media: str | None = None
    last_collection_sync_at: str | None = None


class MediaSyncOut(BaseModel):
    state: str
    last_success_at: str | None = None


class HealthOut(BaseModel):
    status: str
    api_version: str
    anki_version: str
    collection_open: bool
    notes: int
    cards: int
    decks: int
    media_count: int
    sync_state: str
    last_collection_sync_at: str | None
    last_media_sync_at: str | None
    media_sync: MediaSyncOut
