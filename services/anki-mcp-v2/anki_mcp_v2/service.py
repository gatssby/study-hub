from __future__ import annotations

from typing import Any
from urllib.parse import quote

from .client import ApiV2Client, BinaryResponse, MAX_MEDIA_BYTES


class AnkiMcpV2Service:
    """One-to-one MCP-to-API v2 translations with no Anki domain logic."""

    def __init__(self, client: ApiV2Client) -> None:
        self._client = client

    def health(self) -> dict[str, Any]:
        return self._client.get_json("/v2/health")

    def list_decks(
        self, *, root: str | None = None, limit: int = 50, offset: int = 0
    ) -> dict[str, Any]:
        query: dict[str, str | int] = {"limit": limit, "offset": offset}
        if root is not None:
            query["root"] = root
        return self._client.get_json("/v2/decks", query)

    def search_notes(self, query: str, *, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        return self._search(query, kind="notes", limit=limit, offset=offset)

    def search_cards(self, query: str, *, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        return self._search(query, kind="cards", limit=limit, offset=offset)

    def get_note(self, note_id: str) -> dict[str, Any]:
        return self._client.get_json("/v2/notes/" + quote(note_id, safe=""))

    def get_card(self, card_id: str) -> dict[str, Any]:
        return self._client.get_json("/v2/cards/" + quote(card_id, safe=""))

    def update_note(
        self,
        note_id: str,
        *,
        fields: dict[str, str] | None = None,
        add_tags: list[str] | None = None,
        remove_tags: list[str] | None = None,
        expected_revision: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if fields is not None:
            payload["fields"] = fields
        if add_tags is not None:
            payload["add_tags"] = add_tags
        if remove_tags is not None:
            payload["remove_tags"] = remove_tags
        if expected_revision is not None:
            payload["expected_revision"] = expected_revision
        return self._client.patch_json("/v2/notes/" + quote(note_id, safe=""), payload)

    def get_media(self, filename: str) -> BinaryResponse:
        return self._client.get_binary("/v2/media/" + quote(filename, safe=""), max_bytes=MAX_MEDIA_BYTES)

    # ---- note types (read-only) ------------------------------------------------------

    def list_note_types(self) -> dict[str, Any]:
        return self._client.get_json("/v2/note-types")

    def get_note_type(self, note_type_id: str) -> dict[str, Any]:
        return self._client.get_json("/v2/note-types/" + quote(note_type_id, safe=""))

    # ---- notes: create / delete ---------------------------------------------------------

    def create_note(
        self,
        *,
        deck: str,
        note_type: str,
        fields: dict[str, str],
        tags: list[str] | None = None,
        allow_duplicate: bool | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"deck": deck, "note_type": note_type, "fields": fields}
        if tags is not None:
            payload["tags"] = tags
        if allow_duplicate is not None:
            payload["allow_duplicate"] = allow_duplicate
        return self._client.post_json("/v2/notes", payload, write=True)

    def delete_notes(self, notes: list[dict[str, Any]]) -> dict[str, Any]:
        return self._client.post_json("/v2/notes/delete", {"notes": notes}, write=True)

    # ---- tags ----------------------------------------------------------------------------

    def list_tags(
        self, *, prefix: str | None = None, limit: int = 100, offset: int = 0
    ) -> dict[str, Any]:
        query: dict[str, str | int] = {"limit": limit, "offset": offset}
        if prefix is not None:
            query["prefix"] = prefix
        return self._client.get_json("/v2/tags", query)

    def rename_tag(
        self,
        old: str,
        new: str,
        *,
        expected_note_count: int | None = None,
        dry_run: bool | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"old": old, "new": new}
        _optional(payload, expected_note_count=expected_note_count, dry_run=dry_run)
        return self._client.post_json("/v2/tags/rename", payload, write=True)

    def delete_tag(
        self,
        tag: str,
        *,
        expected_note_count: int | None = None,
        dry_run: bool | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"tag": tag}
        _optional(payload, expected_note_count=expected_note_count, dry_run=dry_run)
        return self._client.post_json("/v2/tags/delete", payload, write=True)

    # ---- decks ---------------------------------------------------------------------------

    def create_deck(self, name: str) -> dict[str, Any]:
        return self._client.post_json("/v2/decks", {"name": name}, write=True)

    def rename_deck(
        self, deck_id: str, name: str, *, expected_name: str | None = None
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": name}
        _optional(payload, expected_name=expected_name)
        return self._client.patch_json("/v2/decks/" + quote(deck_id, safe=""), payload)

    def delete_deck(self, deck_id: str, *, expected_name: str) -> dict[str, Any]:
        return self._client.delete_json(
            "/v2/decks/" + quote(deck_id, safe=""), {"expected_name": expected_name}
        )

    # ---- cards ---------------------------------------------------------------------------

    def move_cards(self, card_ids: list[str], target_deck: str) -> dict[str, Any]:
        return self._client.post_json(
            "/v2/cards/move", {"card_ids": card_ids, "target_deck": target_deck}, write=True
        )

    def _search(self, query: str, *, kind: str, limit: int, offset: int) -> dict[str, Any]:
        return self._client.post_json(
            "/v2/search",
            {"query": query, "kind": kind, "limit": limit, "offset": offset},
        )


def _optional(payload: dict[str, Any], **values: Any) -> None:
    for key, value in values.items():
        if value is not None:
            payload[key] = value
