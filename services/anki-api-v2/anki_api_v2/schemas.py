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
MAX_DELETE_NOTES = 10
MAX_MOVE_CARDS = 200
MAX_DECK_NAME_CHARS = 200
REVISION_RE = r"^r1-[0-9a-f]{32}$"

Tag = Annotated[str, StringConstraints(pattern=r"^[^\s\x00-\x1f]{1,100}$")]
# Global tag operations act on every note: no wildcards (`*`), which Anki treats as patterns.
GlobalTag = Annotated[str, StringConstraints(pattern=r"^[^\s\x00-\x1f*]{1,100}$")]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NoteTypeOut(BaseModel):
    id: str
    name: str


class FieldOut(BaseModel):
    name: str
    value: str


class MediaRefOut(BaseModel):
    filename: str
    field: str
    kind: Literal["image", "sound"]
    mime_type: str | None
    exists: bool
    size_bytes: int | None
    viewable: bool = Field(description="True when anki_get_media can return it as an image.")


class NoteOut(BaseModel):
    note_id: str
    note_type: NoteTypeOut
    fields: list[FieldOut]
    tags: list[str]
    card_ids: list[str]
    deck_ids: list[str]
    deck_names: list[str]
    revision: str = Field(description="Pass back as expected_revision to detect lost updates.")
    mod: int
    usn: int
    media: list[MediaRefOut]


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
    expected_revision: str | None = Field(default=None, pattern=REVISION_RE)

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
    revision: str
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


# ---- note types (read-only) ---------------------------------------------------------


class NoteTypeSummary(BaseModel):
    id: str
    name: str
    kind: Literal["standard", "cloze"]
    field_names: list[str]
    template_names: list[str]
    note_count: int


class NoteTypePage(BaseModel):
    total: int
    items: list[NoteTypeSummary]


class NoteTypeFieldOut(BaseModel):
    name: str
    ord: int


class NoteTypeTemplateOut(BaseModel):
    name: str
    ord: int
    question_format: str
    answer_format: str


class NoteTypeDetail(NoteTypeSummary):
    fields: list[NoteTypeFieldOut]
    templates: list[NoteTypeTemplateOut]
    sort_field: str
    duplicate_check_field: str


# ---- notes: create / delete --------------------------------------------------------


class CreateNoteRequest(_Strict):
    deck: str = Field(min_length=1, max_length=MAX_DECK_NAME_CHARS, description="Name or id.")
    note_type: str = Field(min_length=1, max_length=200, description="Name or id.")
    fields: dict[str, str] = Field(max_length=MAX_FIELDS)
    tags: list[Tag] = Field(default_factory=list, max_length=MAX_TAGS)
    allow_duplicate: bool = False


class CreateNoteResult(BaseModel):
    note_id: str
    card_ids: list[str]
    deck_id: str
    deck_name: str
    note_type: NoteTypeOut
    revision: str
    sync: PatchSyncState


class DeleteNoteItem(_Strict):
    note_id: str
    expected_card_ids: list[str] = Field(min_length=1, max_length=100)
    expected_revision: str = Field(pattern=REVISION_RE)


class DeleteNotesRequest(_Strict):
    notes: list[DeleteNoteItem] = Field(min_length=1, max_length=MAX_DELETE_NOTES)


class DeletedNote(BaseModel):
    note_id: str
    card_ids: list[str]


class DeleteNotesResult(BaseModel):
    deleted: list[DeletedNote]
    sync: PatchSyncState


# ---- tags -----------------------------------------------------------------------------


class TagPage(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool
    items: list[str]


class TagRenameRequest(_Strict):
    old: GlobalTag
    new: GlobalTag
    expected_note_count: int | None = Field(default=None, ge=0)
    dry_run: bool = False


class TagDeleteRequest(_Strict):
    tag: GlobalTag
    expected_note_count: int | None = Field(default=None, ge=0)
    dry_run: bool = False


class TagOpResult(BaseModel):
    affected_note_count: int
    dry_run: bool
    sync: PatchSyncState | None = None


class TagRenameResult(TagOpResult):
    old: str
    new: str


class TagDeleteResult(TagOpResult):
    tag: str


# ---- decks ---------------------------------------------------------------------------


class CreateDeckRequest(_Strict):
    name: str = Field(min_length=1, max_length=MAX_DECK_NAME_CHARS)


class CreateDeckResult(BaseModel):
    deck_id: str
    name: str
    created: bool
    sync: PatchSyncState | None = None


class RenameDeckRequest(_Strict):
    name: str = Field(min_length=1, max_length=MAX_DECK_NAME_CHARS)
    expected_name: str | None = Field(default=None, max_length=MAX_DECK_NAME_CHARS)


class RenameDeckResult(BaseModel):
    deck_id: str
    old_name: str
    name: str
    sync: PatchSyncState


class DeleteDeckResult(BaseModel):
    deck_id: str
    name: str
    deleted: bool
    card_count: int
    sync: PatchSyncState


# ---- cards: move -----------------------------------------------------------------------


class MoveCardsRequest(_Strict):
    card_ids: list[str] = Field(min_length=1)
    target_deck: str = Field(min_length=1, max_length=MAX_DECK_NAME_CHARS, description="Name or id.")


class MovedCard(BaseModel):
    card_id: str
    old_deck_id: str
    old_deck_name: str
    new_deck_id: str
    new_deck_name: str
    moved: bool


class DeckRef(BaseModel):
    deck_id: str
    name: str


class MoveCardsResult(BaseModel):
    target_deck: DeckRef
    moved: int
    unchanged: int
    items: list[MovedCard]
    sync: PatchSyncState | None

