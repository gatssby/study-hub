"""Collection operations. Every method runs on the collection owner thread.

Write policy: sync before -> validate on fresh state -> apply -> confirm card set
unchanged (undo otherwise) -> sync after. A write is reported as success only
after the sync server has accepted the sync that follows it.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from anki.collection import Collection
from anki.errors import NotFoundError, SearchError
from anki.notes import NoteId

from anki_api_v2 import __version__
from anki_api_v2.errors import ApiError
from anki_api_v2.media import media_dir_for
from anki_api_v2.schemas import MAX_FIELD_CHARS, PatchNoteRequest
from anki_api_v2.sync import SyncManager, iso

API_VERSION = __version__
MAX_DECK_LIMIT = 200
MAX_SEARCH_LIMIT = 100


def _str_id(value: int) -> str:
    return str(int(value))


def _parse_id(raw: str, code: str) -> int:
    if not raw.isdigit() or len(raw) > 20:
        raise ApiError(422, code, "id must be a positive integer string")
    value = int(raw)
    if value <= 0:
        raise ApiError(422, code, "id must be a positive integer string")
    return value


class CollectionService:
    def __init__(self, *, sync: SyncManager, collection_path: Path) -> None:
        self._sync = sync
        self._media_dir = media_dir_for(collection_path)
        self._collection_path = collection_path

    # ---- health -------------------------------------------------------

    def health(self, col: Collection) -> dict[str, Any]:
        self._sync.refresh_media(col)
        decks = len(col.decks.all_names_and_ids(include_filtered=True))
        sync_state = self._sync.sync_state
        degraded = sync_state in {"error", "pending", "full_sync_required"}
        return {
            "status": "degraded" if degraded else "ok",
            "api_version": API_VERSION,
            "anki_version": _anki_version(),
            "collection_open": True,
            "notes": int(col.note_count()),
            "cards": int(col.card_count()),
            "decks": decks,
            "media_count": _count_media_files(self._media_dir),
            "sync_state": sync_state,
            "last_collection_sync_at": iso(self._sync.last_collection_sync_at),
            "last_media_sync_at": iso(self._sync.last_media_sync_at),
            "media_sync": {
                "state": self._sync.media_state,
                "last_success_at": iso(self._sync.last_media_sync_at),
            },
        }

    # ---- sync endpoint ------------------------------------------------

    def sync_now(self, col: Collection, media: bool) -> dict[str, Any]:
        name = self._sync.sync_collection(col)
        result: dict[str, Any] = {
            "collection": name,
            "media": None,
            "last_collection_sync_at": iso(self._sync.last_collection_sync_at),
        }
        if media:
            result["media"] = self._sync.start_media(col)
        return result

    # ---- decks --------------------------------------------------------

    def list_decks(
        self, col: Collection, root: str | None = None, limit: int = 50, offset: int = 0
    ) -> dict[str, Any]:
        rows = sorted(col.decks.all_names_and_ids(include_filtered=True), key=lambda d: d.name)
        if root:
            rows = [d for d in rows if d.name == root or d.name.startswith(root + "::")]
        total = len(rows)
        page = rows[offset : offset + limit]
        items = [
            {
                "deck_id": _str_id(d.id),
                "name": d.name,
                "card_count": int(col.decks.card_count(d.id, include_subdecks=False)),
                "is_filtered": bool(col.decks.is_filtered(d.id)),
            }
            for d in page
        ]
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(page) < total,
            "items": items,
        }

    # ---- notes / cards ------------------------------------------------

    def get_note(self, col: Collection, note_id_raw: str) -> dict[str, Any]:
        nid = _parse_id(note_id_raw, "invalid_id")
        note = self._load_note(col, nid)
        nt = note.note_type() or {}
        card_ids = list(note.card_ids())
        deck_ids = sorted({_str_id(col.get_card(c).did) for c in card_ids})
        return {
            "note_id": _str_id(note.id),
            "note_type": {"id": _str_id(nt.get("id", 0)), "name": nt.get("name", "")},
            "fields": [{"name": k, "value": v} for k, v in note.items()],
            "tags": list(note.tags),
            "card_ids": [_str_id(c) for c in card_ids],
            "deck_ids": deck_ids,
        }

    def get_card(self, col: Collection, card_id_raw: str) -> dict[str, Any]:
        cid = _parse_id(card_id_raw, "invalid_id")
        try:
            card = col.get_card(cid)
        except NotFoundError as exc:
            raise ApiError(404, "card_not_found", "card does not exist") from exc
        note = card.note()
        nt = card.note_type()
        return {
            "card_id": _str_id(card.id),
            "note_id": _str_id(note.id),
            "deck_id": _str_id(card.did),
            "deck_name": col.decks.name(card.did),
            "template_name": card.template()["name"],
            "ord": int(card.ord),
            "note_type": {"id": _str_id(nt.get("id", 0)), "name": nt.get("name", "")},
            "question": card.question(),
            "answer": card.answer(),
        }

    def search(
        self, col: Collection, query: str, kind: str, limit: int, offset: int
    ) -> dict[str, Any]:
        try:
            if kind == "notes":
                ids = sorted(int(i) for i in col.find_notes(query))
            else:
                ids = sorted(int(i) for i in col.find_cards(query))
        except SearchError as exc:
            raise ApiError(422, "invalid_search", "search query is not valid Anki syntax") from exc
        total = len(ids)
        page = ids[offset : offset + limit]
        if kind == "notes":
            items = [{"note_id": _str_id(i)} for i in page]
        else:
            items = []
            for cid in page:
                card = col.get_card(cid)
                items.append(
                    {
                        "card_id": _str_id(cid),
                        "note_id": _str_id(card.nid),
                        "deck_id": _str_id(card.did),
                    }
                )
        return {
            "query": query,
            "kind": kind,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(page) < total,
            "items": items,
        }

    # ---- writes -------------------------------------------------------

    def patch_note(
        self, col: Collection, note_id_raw: str, req: PatchNoteRequest
    ) -> dict[str, Any]:
        nid = _parse_id(note_id_raw, "invalid_id")
        self._validate_patch(col, nid, req)  # fail fast, before any network I/O

        self._sync.sync_before_write(col)  # raises ApiError if the server cannot take a sync first
        self._sync.pace_for_write()  # change must land in a later second than the sync above

        # Re-validate on the state that results from the sync we just did.
        self._validate_patch(col, nid, req)
        note = col.get_note(NoteId(nid))
        cards_before = {int(c) for c in note.card_ids()}
        tags_before = set(note.tags)
        fields_before = dict(note.items())

        for name, value in req.fields.items():
            note[name] = value
        for tag in req.remove_tags:
            note.remove_tag(tag)
        for tag in req.add_tags:
            note.add_tag(tag)
        col.update_note(note)

        cards_after = {int(c) for c in col.card_ids_of_note(NoteId(nid))}
        if cards_after != cards_before:
            # Undo the local change immediately; nothing is sent to the server.
            col.undo()
            raise ApiError(
                409,
                "card_set_change_blocked",
                "change would create or delete cards; this endpoint never does that",
            )

        reloaded = col.get_note(NoteId(nid))
        tags_after = set(reloaded.tags)
        # A request that changes nothing sends nothing, so there is nothing to confirm.
        changed = dict(reloaded.items()) != fields_before or tags_after != tags_before
        try:
            self._sync.sync_after_write(col, nid, expect_change=changed)
        except ApiError as exc:
            raise exc.with_details(local_change_applied=True, server_confirmed=False)

        return {
            "note_id": _str_id(nid),
            "updated_fields": sorted(req.fields),
            "added_tags": sorted(tags_after - tags_before),
            "removed_tags": sorted(tags_before - tags_after),
            "sync": {"before": "ok", "after": "ok"},
        }

    def _validate_patch(self, col: Collection, nid: int, req: PatchNoteRequest) -> None:
        note = self._load_note(col, nid)
        known = set(note.keys())
        for name, value in req.fields.items():
            if name not in known:
                raise ApiError(422, "invalid_field", f"field '{name}' does not exist on this note")
            if len(value) > MAX_FIELD_CHARS:
                raise ApiError(
                    413,
                    "payload_too_large",
                    f"field '{name}' exceeds {MAX_FIELD_CHARS} characters",
                )

    def _load_note(self, col: Collection, nid: int):
        try:
            return col.get_note(NoteId(nid))
        except NotFoundError as exc:
            raise ApiError(404, "note_not_found", "note does not exist") from exc


def _anki_version() -> str:
    from anki import buildinfo

    return str(buildinfo.version)


def _count_media_files(media_dir: Path) -> int:
    try:
        with os.scandir(media_dir) as entries:
            return sum(
                1
                for e in entries
                if e.is_file(follow_symlinks=False) and not e.name.startswith(".")
            )
    except FileNotFoundError:
        return 0
