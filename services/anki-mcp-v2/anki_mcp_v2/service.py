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
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if fields is not None:
            payload["fields"] = fields
        if add_tags is not None:
            payload["add_tags"] = add_tags
        if remove_tags is not None:
            payload["remove_tags"] = remove_tags
        return self._client.patch_json("/v2/notes/" + quote(note_id, safe=""), payload)

    def get_media(self, filename: str) -> BinaryResponse:
        return self._client.get_binary("/v2/media/" + quote(filename, safe=""), max_bytes=MAX_MEDIA_BYTES)

    def _search(self, query: str, *, kind: str, limit: int, offset: int) -> dict[str, Any]:
        return self._client.post_json(
            "/v2/search",
            {"query": query, "kind": kind, "limit": limit, "offset": offset},
        )
