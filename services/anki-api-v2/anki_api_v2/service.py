"""Collection operations. Every method runs on the collection owner thread.

Write policy: sync before -> validate on fresh state -> apply -> confirm card set
unchanged (undo otherwise) -> sync after. A write is reported as success only
after the sync server has accepted the sync that follows it.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from anki.collection import Collection, SearchNode
from anki.errors import AnkiException, NotFoundError, SearchError
from anki.notes import NoteId
from anki.notes_pb2 import NoteFieldsCheckResponse as FieldsCheck

from anki_api_v2 import __version__
from anki_api_v2.domain import note_revision, parse_id, str_id
from anki_api_v2.errors import ApiError
from anki_api_v2.media import extract_media_refs, media_dir_for
from anki_api_v2.schemas import (
    MAX_DECK_NAME_CHARS,
    MAX_DELETE_NOTES,
    MAX_FIELD_CHARS,
    MAX_MOVE_CARDS,
    CreateNoteRequest,
    DeleteNotesRequest,
    MoveCardsRequest,
    PatchNoteRequest,
    RenameDeckRequest,
)
from anki_api_v2.sync import SyncManager, iso

API_VERSION = __version__
MAX_DECK_LIMIT = 200
MAX_SEARCH_LIMIT = 100
MAX_TAG_OP_NOTES = 2000
DEFAULT_DECK_ID = 1
SYNC_OK = {"before": "ok", "after": "ok"}

_str_id = str_id


def _parse_id(raw: str, code: str) -> int:
    return parse_id(raw, code)


def _unconfirmed(exc: ApiError) -> ApiError:
    return exc.with_details(local_change_applied=True, server_confirmed=False)


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
        return self._note_view(col, note)

    def _note_view(self, col: Collection, note) -> dict[str, Any]:
        nt = note.note_type() or {}
        card_ids = sorted(int(c) for c in note.card_ids())
        dids = sorted({int(col.get_card(c).did) for c in card_ids})
        return {
            "note_id": _str_id(note.id),
            "note_type": {"id": _str_id(nt.get("id", 0)), "name": nt.get("name", "")},
            "fields": [{"name": k, "value": v} for k, v in note.items()],
            "tags": list(note.tags),
            "card_ids": [_str_id(c) for c in card_ids],
            "deck_ids": [_str_id(d) for d in dids],
            "deck_names": [col.decks.name(d) for d in dids],
            "revision": note_revision(note, card_ids),
            "mod": int(note.mod),
            "usn": int(note.usn),
            "media": extract_media_refs(list(note.items()), self._media_dir),
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
        self._check_revision(note, req.expected_revision)
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
            raise _unconfirmed(exc) from exc

        return {
            "note_id": _str_id(nid),
            "updated_fields": sorted(req.fields),
            "added_tags": sorted(tags_after - tags_before),
            "removed_tags": sorted(tags_before - tags_after),
            "revision": note_revision(reloaded, [int(c) for c in reloaded.card_ids()]),
            "sync": dict(SYNC_OK),
        }

    @staticmethod
    def _check_revision(note, expected: str | None) -> None:
        if expected is None:
            return
        current = note_revision(note, [int(c) for c in note.card_ids()])
        if current != expected:
            raise ApiError(
                409,
                "stale_revision",
                "the note changed since it was read; read it again before writing",
                details={"current_revision": current, "expected_revision": expected},
            )

    # ---- note types (read-only) -----------------------------------------------

    def list_note_types(self, col: Collection) -> dict[str, Any]:
        items = []
        for row in sorted(col.models.all_use_counts(), key=lambda r: r.name.lower()):
            nt = col.models.get(row.id)
            if nt is None:
                continue
            items.append(self._note_type_summary(nt, int(row.use_count)))
        return {"total": len(items), "items": items}

    def get_note_type(self, col: Collection, raw_id: str) -> dict[str, Any]:
        ntid = _parse_id(raw_id, "invalid_id")
        nt = col.models.get(ntid)
        if nt is None:
            raise ApiError(404, "note_type_not_found", "note type does not exist")
        summary = self._note_type_summary(nt, int(col.models.use_count(nt)))
        fields = nt["flds"]
        return {
            **summary,
            "fields": [{"name": f["name"], "ord": int(f["ord"])} for f in fields],
            "templates": [
                {
                    "name": t["name"],
                    "ord": int(t["ord"]),
                    "question_format": t["qfmt"],
                    "answer_format": t["afmt"],
                }
                for t in nt["tmpls"]
            ],
            "sort_field": fields[int(nt.get("sortf", 0))]["name"],
            "duplicate_check_field": fields[0]["name"],
        }

    @staticmethod
    def _note_type_summary(nt: Any, note_count: int) -> dict[str, Any]:
        return {
            "id": _str_id(nt["id"]),
            "name": nt["name"],
            "kind": "cloze" if int(nt.get("type", 0)) == 1 else "standard",
            "field_names": [f["name"] for f in nt["flds"]],
            "template_names": [t["name"] for t in nt["tmpls"]],
            "note_count": note_count,
        }

    # ---- shared write helpers ---------------------------------------------------

    def _begin_write(self, col: Collection) -> None:
        self._sync.sync_before_write(col)  # raises ApiError (incl. full_sync_required)
        self._sync.pace_for_write()

    def _finish_change(self, col: Collection) -> None:
        try:
            self._sync.sync_after_change(col)
        except ApiError as exc:
            raise _unconfirmed(exc) from exc

    def _resolve_deck(self, col: Collection, raw: str, *, allow_filtered: bool = False):
        did = col.decks.id_for_name(raw)
        if did is None and raw.isascii() and raw.isdigit() and col.decks.name_if_exists(int(raw)):
            did = int(raw)
        if did is None:
            raise ApiError(404, "deck_not_found", "deck does not exist")
        if not allow_filtered and col.decks.is_filtered(did):
            raise ApiError(409, "deck_is_filtered", "filtered decks cannot be written to")
        return int(did), col.decks.name(did)

    # ---- create note ---------------------------------------------------------------

    def create_note(self, col: Collection, req: CreateNoteRequest) -> dict[str, Any]:
        for name, value in req.fields.items():
            if len(value) > MAX_FIELD_CHARS:
                raise ApiError(
                    413, "payload_too_large", f"field '{name}' exceeds {MAX_FIELD_CHARS} characters"
                )
        self._begin_write(col)

        deck_id, deck_name = self._resolve_deck(col, req.deck)
        nt = col.models.by_name(req.note_type)
        if nt is None and req.note_type.isascii() and req.note_type.isdigit():
            nt = col.models.get(int(req.note_type))
        if nt is None:
            raise ApiError(404, "note_type_not_found", "note type does not exist")
        known = {f["name"] for f in nt["flds"]}
        for name in req.fields:
            if name not in known:
                raise ApiError(
                    422, "invalid_field", f"field '{name}' does not exist on note type '{nt['name']}'"
                )

        note = col.new_note(nt)
        for name, value in req.fields.items():
            note[name] = value
        note.tags = list(dict.fromkeys(req.tags))
        problem = note.fields_check()
        if problem == FieldsCheck.EMPTY:
            raise ApiError(422, "empty_note", "the first field must not be empty")
        if problem in (
            FieldsCheck.MISSING_CLOZE,
            FieldsCheck.NOTETYPE_NOT_CLOZE,
            FieldsCheck.FIELD_NOT_CLOZE,
        ):
            raise ApiError(422, "invalid_cloze", "cloze text is missing or not valid for this type")
        if problem == FieldsCheck.DUPLICATE and not req.allow_duplicate:
            raise ApiError(
                409,
                "duplicate_note",
                "a note of this type with the same first field already exists",
            )

        col.add_note(note, deck_id)
        nid = int(note.id)
        created = col.get_note(NoteId(nid))
        card_ids = sorted(int(c) for c in created.card_ids())
        if not card_ids:
            col.undo()
            raise ApiError(422, "no_cards", "the note type would generate no cards for this note")
        try:
            self._sync.sync_after_write(col, nid, expect_change=True)
        except ApiError as exc:
            raise _unconfirmed(exc) from exc
        return {
            "note_id": _str_id(nid),
            "card_ids": [_str_id(c) for c in card_ids],
            "deck_id": _str_id(deck_id),
            "deck_name": deck_name,
            "note_type": {"id": _str_id(nt["id"]), "name": nt["name"]},
            "revision": note_revision(created, card_ids),
            "sync": dict(SYNC_OK),
        }

    # ---- delete notes ----------------------------------------------------------------

    def delete_notes(self, col: Collection, req: DeleteNotesRequest) -> dict[str, Any]:
        if len(req.notes) > MAX_DELETE_NOTES:
            raise ApiError(422, "too_many_notes", f"at most {MAX_DELETE_NOTES} notes per request")
        parsed = []
        for item in req.notes:
            nid = _parse_id(item.note_id, "invalid_id")
            cards = {_parse_id(c, "invalid_id") for c in item.expected_card_ids}
            parsed.append((nid, cards, item.expected_revision))
        if len({p[0] for p in parsed}) != len(parsed):
            raise ApiError(422, "duplicate_ids", "the same note id appears more than once")

        self._begin_write(col)

        # Verify EVERY note before deleting ANY: the batch is all or nothing.
        plan: list[tuple[int, list[int]]] = []
        for nid, expected_cards, expected_rev in parsed:
            note = self._load_note(col, nid)
            actual_cards = sorted(int(c) for c in note.card_ids())
            if set(actual_cards) != expected_cards:
                raise ApiError(
                    409,
                    "card_ids_mismatch",
                    "the note's cards are not the expected ones; read the note again",
                    details={
                        "note_id": _str_id(nid),
                        "actual_card_ids": [_str_id(c) for c in actual_cards],
                    },
                )
            self._check_revision(note, expected_rev)
            plan.append((nid, actual_cards))

        result = col.remove_notes([NoteId(nid) for nid, _ in plan])
        survivors = [nid for nid, _ in plan if _note_exists(col, nid)]
        # Anki reports the number of CARDS removed, which is the number we verified above.
        if int(result.count) != sum(len(cards) for _, cards in plan) or survivors:
            col.undo()
            raise ApiError(409, "delete_not_applied", "the delete did not apply as expected")
        self._finish_change(col)
        return {
            "deleted": [
                {"note_id": _str_id(nid), "card_ids": [_str_id(c) for c in cards]}
                for nid, cards in plan
            ],
            "sync": dict(SYNC_OK),
        }

    # ---- tags -------------------------------------------------------------------------

    def list_tags(
        self, col: Collection, prefix: str | None, limit: int, offset: int
    ) -> dict[str, Any]:
        tags = sorted(col.tags.all(), key=lambda t: (t.lower(), t))
        if prefix:
            tags = [t for t in tags if t.lower().startswith(prefix.lower())]
        page = tags[offset : offset + limit]
        return {
            "total": len(tags),
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(page) < len(tags),
            "items": page,
        }

    def rename_tag(self, col: Collection, req) -> dict[str, Any]:
        _check_tag_name(req.old, "old")
        _check_tag_name(req.new, "new")
        if req.old.lower() == req.new.lower():
            raise ApiError(422, "invalid_request", "old and new tag names are the same")
        if not req.dry_run and req.expected_note_count is None:
            raise ApiError(
                422, "expected_count_required", "expected_note_count is required (use dry_run first)"
            )
        count = self._tag_precheck(col, req.old, req.dry_run, req.expected_note_count)
        if req.dry_run:
            return {
                "old": req.old,
                "new": req.new,
                "affected_note_count": count,
                "dry_run": True,
                "sync": None,
            }
        applied = col.tags.rename(req.old, req.new)
        if int(applied.count) != count:
            col.undo()
            raise ApiError(409, "stale_count", "the affected note count changed; retry")
        self._finish_change(col)
        return {
            "old": req.old,
            "new": req.new,
            "affected_note_count": count,
            "dry_run": False,
            "sync": dict(SYNC_OK),
        }

    def delete_tag(self, col: Collection, req) -> dict[str, Any]:
        _check_tag_name(req.tag, "tag")
        if not req.dry_run and req.expected_note_count is None:
            raise ApiError(
                422, "expected_count_required", "expected_note_count is required (use dry_run first)"
            )
        count = self._tag_precheck(col, req.tag, req.dry_run, req.expected_note_count)
        if req.dry_run:
            return {"tag": req.tag, "affected_note_count": count, "dry_run": True, "sync": None}
        applied = col.tags.remove(req.tag)
        if int(applied.count) != count:
            col.undo()
            raise ApiError(409, "stale_count", "the affected note count changed; retry")
        self._finish_change(col)
        return {
            "tag": req.tag,
            "affected_note_count": count,
            "dry_run": False,
            "sync": dict(SYNC_OK),
        }

    def _tag_precheck(
        self, col: Collection, tag: str, dry_run: bool, expected: int | None
    ) -> int:
        if dry_run:
            self._sync.ensure_fresh(col)
        else:
            self._begin_write(col)
        low = tag.lower()
        if not any(t.lower() == low or t.lower().startswith(low + "::") for t in col.tags.all()):
            raise ApiError(404, "tag_not_found", "tag does not exist")
        count = len(col.find_notes(col.build_search_string(SearchNode(tag=tag))))
        if dry_run:
            return count
        if expected != count:
            raise ApiError(
                409,
                "stale_count",
                "the number of affected notes differs from expected_note_count",
                details={"affected_note_count": count},
            )
        if count > MAX_TAG_OP_NOTES:
            raise ApiError(
                413,
                "too_many_notes",
                f"a tag operation may touch at most {MAX_TAG_OP_NOTES} notes",
                details={"affected_note_count": count},
            )
        return count

    # ---- decks ----------------------------------------------------------------------

    def create_deck(self, col: Collection, name: str) -> tuple[dict[str, Any], bool]:
        _check_deck_name(name)
        self._begin_write(col)
        existing = col.decks.id_for_name(name)
        if existing is not None:
            if col.decks.is_filtered(existing):
                raise ApiError(409, "deck_is_filtered", "a filtered deck has this name")
            return (
                {"deck_id": _str_id(existing), "name": col.decks.name(existing), "created": False,
                 "sync": None},
                False,
            )
        try:
            created = col.decks.add_normal_deck_with_name(name)
        except AnkiException as exc:
            raise ApiError(422, "invalid_deck_name", "Anki rejected this deck name") from exc
        if col.decks.name(created.id) != name:
            col.undo()
            raise ApiError(422, "invalid_deck_name", "Anki would store a different name")
        self._finish_change(col)
        return (
            {"deck_id": _str_id(created.id), "name": name, "created": True, "sync": dict(SYNC_OK)},
            True,
        )

    def rename_deck(self, col: Collection, raw_id: str, req: RenameDeckRequest) -> dict[str, Any]:
        did = _parse_id(raw_id, "invalid_id")
        _check_deck_name(req.name)
        self._begin_write(col)
        old = self._existing_deck(col, did, req.expected_name)
        if req.name.lower() != old.lower():
            clash = col.decks.id_for_name(req.name)
            if clash is not None:
                raise ApiError(409, "deck_exists", "a deck with the target name already exists")
        if req.name.lower().startswith(old.lower() + "::"):
            raise ApiError(422, "invalid_deck_move", "a deck cannot be moved inside itself")
        changed = req.name != old
        if changed:
            try:
                col.decks.rename(did, req.name)
            except AnkiException as exc:
                raise ApiError(422, "invalid_deck_name", "Anki rejected this deck name") from exc
            if col.decks.name(did) != req.name:
                col.undo()
                raise ApiError(409, "deck_exists", "Anki would store a different name")
        try:
            self._sync.sync_after_change(col, expect_change=changed)
        except ApiError as exc:
            raise _unconfirmed(exc) from exc
        return {"deck_id": _str_id(did), "old_name": old, "name": req.name, "sync": dict(SYNC_OK)}

    def delete_deck(self, col: Collection, raw_id: str, expected_name: str) -> dict[str, Any]:
        did = _parse_id(raw_id, "invalid_id")
        self._begin_write(col)
        name = self._existing_deck(col, did, None)
        cards = max(
            len(col.find_cards(col.build_search_string(SearchNode(deck=name)))),
            int(col.decks.card_count(did, include_subdecks=True)),
        )
        if expected_name != name:
            raise ApiError(
                409, "stale_deck", "the deck name differs from expected_name",
                details={"name": name},
            )
        if cards:
            raise ApiError(
                409,
                "deck_not_empty",
                "only empty decks can be deleted; cards are never moved or deleted implicitly",
                details={"card_count": cards},
            )
        if len(col.decks.deck_and_child_ids(did)) > 1:
            raise ApiError(409, "deck_has_subdecks", "delete or move the subdecks first")
        total_before = int(col.card_count())
        col.decks.remove([did])
        if col.decks.name_if_exists(did) is not None or int(col.card_count()) != total_before:
            col.undo()
            raise ApiError(409, "delete_not_applied", "the delete did not apply as expected")
        self._finish_change(col)
        return {
            "deck_id": _str_id(did),
            "name": name,
            "deleted": True,
            "card_count": 0,
            "sync": dict(SYNC_OK),
        }

    def _existing_deck(self, col: Collection, did: int, expected_name: str | None) -> str:
        name = col.decks.name_if_exists(did)
        if name is None:
            raise ApiError(404, "deck_not_found", "deck does not exist")
        if did == DEFAULT_DECK_ID:
            raise ApiError(409, "deck_protected", "the Default deck cannot be renamed or deleted")
        if col.decks.is_filtered(did):
            raise ApiError(409, "deck_is_filtered", "filtered decks are not managed here")
        if expected_name is not None and expected_name != name:
            raise ApiError(
                409, "stale_deck", "the deck name differs from expected_name", details={"name": name}
            )
        return name

    # ---- move cards ---------------------------------------------------------------------

    def move_cards(self, col: Collection, req: MoveCardsRequest) -> dict[str, Any]:
        ids = [_parse_id(c, "invalid_id") for c in req.card_ids]
        if len(ids) > MAX_MOVE_CARDS:
            raise ApiError(422, "too_many_cards", f"at most {MAX_MOVE_CARDS} cards per request")
        if len(set(ids)) != len(ids):
            raise ApiError(422, "duplicate_ids", "the same card id appears more than once")
        self._begin_write(col)

        target_id, target_name = self._resolve_deck(col, req.target_deck)
        cards = []
        for cid in ids:
            try:
                cards.append(col.get_card(cid))
            except NotFoundError as exc:
                raise ApiError(
                    404, "card_not_found", "card does not exist", details={"card_id": _str_id(cid)}
                ) from exc
        for card in cards:
            if int(card.odid) != 0:
                raise ApiError(
                    409,
                    "card_in_filtered_deck",
                    "cards currently in a filtered deck are not moved",
                    details={"card_id": _str_id(card.id)},
                )
        before = {int(c.id): (int(c.did), _schedule(c)) for c in cards}
        names = {d: col.decks.name(d) for d in {v[0] for v in before.values()} | {target_id}}
        to_move = [cid for cid, (did, _) in before.items() if did != target_id]

        if to_move:
            applied = col.set_deck(to_move, target_id)
            bad = [
                cid
                for cid in to_move
                if int(col.get_card(cid).did) != target_id
                or _schedule(col.get_card(cid)) != before[cid][1]
            ]
            if int(applied.count) != len(to_move) or bad:
                col.undo()
                raise ApiError(409, "move_not_applied", "the move did not apply as expected")
            self._finish_change(col)
        items = [
            {
                "card_id": _str_id(cid),
                "old_deck_id": _str_id(did),
                "old_deck_name": names[did],
                "new_deck_id": _str_id(target_id),
                "new_deck_name": target_name,
                "moved": cid in to_move,
            }
            for cid, (did, _) in before.items()
        ]
        return {
            "target_deck": {"deck_id": _str_id(target_id), "name": target_name},
            "moved": len(to_move),
            "unchanged": len(before) - len(to_move),
            "items": items,
            "sync": dict(SYNC_OK) if to_move else None,
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


def _note_exists(col: Collection, nid: int) -> bool:
    try:
        col.get_note(NoteId(nid))
    except NotFoundError:
        return False
    return True


def _schedule(card) -> tuple:
    """Everything that makes up scheduling/review state; a move must leave it untouched."""
    return (
        int(card.type),
        int(card.queue),
        int(card.due),
        int(card.ivl),
        int(card.factor),
        int(card.reps),
        int(card.lapses),
        int(card.left),
        int(card.odue),
        int(card.odid),
        repr(card.memory_state),
        int(card.flags),
    )


def _check_tag_name(tag: str, label: str) -> None:
    if tag != tag.strip() or tag.startswith("::") or tag.endswith("::") or "::::" in tag:
        raise ApiError(422, "invalid_tag", f"'{label}' is not a valid tag name")
    if any(not part for part in tag.split("::")):
        raise ApiError(422, "invalid_tag", f"'{label}' is not a valid tag name")


def _check_deck_name(name: str) -> None:
    parts = name.split("::")
    bad = (
        not name
        or len(name) > MAX_DECK_NAME_CHARS
        or any(not p.strip() or p != p.strip() for p in parts)
        or any(ord(ch) < 32 or ord(ch) == 127 for ch in name)
    )
    if bad:
        raise ApiError(
            422,
            "invalid_deck_name",
            "deck names are '::' separated, non-blank parts without outer spaces or control characters",
        )
