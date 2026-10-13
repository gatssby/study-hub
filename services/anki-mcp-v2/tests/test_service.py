from __future__ import annotations

import sys
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from anki_mcp_v2.client import BinaryResponse
from anki_mcp_v2.service import AnkiMcpV2Service


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, object]] = []

    def get_json(self, path, query=None):
        self.calls.append(("GET", path, query))
        return {"path": path, "query": query}

    def post_json(self, path, payload):
        self.calls.append(("POST", path, payload))
        return {"path": path, "payload": payload}

    def patch_json(self, path, payload):
        self.calls.append(("PATCH", path, payload))
        return {"note_id": "1791823645036", "sync": {"before": "ok", "after": "ok"}}

    def get_binary(self, path, *, max_bytes):
        self.calls.append(("BINARY", path, max_bytes))
        return BinaryResponse(b"png-data", "image/png")


def test_list_decks_maps_root_limit_and_offset_without_transforming_ids():
    client = FakeClient()

    result = AnkiMcpV2Service(client).list_decks(root="UFPR", limit=10, offset=20)

    assert result == {"path": "/v2/decks", "query": {"root": "UFPR", "limit": 10, "offset": 20}}
    assert client.calls == [("GET", "/v2/decks", {"root": "UFPR", "limit": 10, "offset": 20})]


def test_search_notes_and_cards_map_only_to_api_v2_kind():
    client = FakeClient()
    service = AnkiMcpV2Service(client)

    notes = service.search_notes("tag:anki_gpt_v2_e2e", limit=3, offset=4)
    cards = service.search_cards("tag:anki_gpt_v2_e2e", limit=5, offset=6)

    assert notes["payload"] == {
        "query": "tag:anki_gpt_v2_e2e",
        "kind": "notes",
        "limit": 3,
        "offset": 4,
    }
    assert cards["payload"] == {
        "query": "tag:anki_gpt_v2_e2e",
        "kind": "cards",
        "limit": 5,
        "offset": 6,
    }


def test_get_note_and_card_preserve_large_ids_as_strings():
    client = FakeClient()
    service = AnkiMcpV2Service(client)

    service.get_note("1791823645036")
    service.get_card("1791823645037")

    assert client.calls == [
        ("GET", "/v2/notes/1791823645036", None),
        ("GET", "/v2/cards/1791823645037", None),
    ]


def test_update_note_passes_only_the_explicit_payload_values():
    client = FakeClient()

    result = AnkiMcpV2Service(client).update_note(
        "1791823645036",
        fields={"Back": "<pre><code>MCP_V2_PATCH_OK_20261013</code></pre>"},
        add_tags=["anki_gpt_v2_mcp_written"],
        remove_tags=None,
    )

    assert result["note_id"] == "1791823645036"
    assert client.calls == [
        (
            "PATCH",
            "/v2/notes/1791823645036",
            {
                "fields": {"Back": "<pre><code>MCP_V2_PATCH_OK_20261013</code></pre>"},
                "add_tags": ["anki_gpt_v2_mcp_written"],
            },
        )
    ]


def test_media_is_retrieved_only_from_api_v2_media_route():
    client = FakeClient()

    media = AnkiMcpV2Service(client).get_media("diagram.png")

    assert media.content_type == "image/png"
    assert client.calls == [("BINARY", "/v2/media/diagram.png", 20 * 1024 * 1024)]


def test_approved_service_methods_never_call_sync_or_legacy_port():
    client = FakeClient()
    service = AnkiMcpV2Service(client)

    service.health()
    service.list_decks()
    service.search_notes("tag:x")
    service.search_cards("tag:x")
    service.get_note("1791823645036")
    service.get_card("1791823645037")
    service.update_note("1791823645036", fields={"Back": "x"})
    service.get_media("diagram.png")

    serialized_calls = repr(client.calls)
    assert "/v2/sync" not in serialized_calls
    assert "8767" not in serialized_calls
