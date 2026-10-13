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

    def post_json(self, path, payload, *, write=False):
        self.calls.append(("POST", path, payload))
        return {"path": path, "payload": payload}

    def patch_json(self, path, payload):
        self.calls.append(("PATCH", path, payload))
        return {"note_id": "1791823645036", "sync": {"before": "ok", "after": "ok"}}

    def delete_json(self, path, query=None):
        self.calls.append(("DELETE", path, query))
        return {"path": path, "query": query}

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
    assert client.calls == [("BINARY", "/v2/media/diagram.png", 8 * 1024 * 1024)]


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
    service.list_note_types()
    service.get_note_type("1")
    service.create_note(deck="D", note_type="Basic", fields={"Front": "x"})
    service.delete_notes([{"note_id": "1", "expected_card_ids": ["2"], "expected_revision": "r1-" + "0" * 32}])
    service.list_tags()
    service.rename_tag("a", "b", expected_note_count=1)
    service.delete_tag("a", expected_note_count=1)
    service.create_deck("A::B")
    service.rename_deck("1", "C")
    service.delete_deck("1", expected_name="C")
    service.move_cards(["1"], "D")

    serialized_calls = repr(client.calls)
    assert "/v2/sync" not in serialized_calls
    assert "8767" not in serialized_calls


def test_update_note_forwards_expected_revision():
    client = FakeClient()
    AnkiMcpV2Service(client).update_note(
        "1", fields={"Back": "x"}, expected_revision="r1-" + "a" * 32
    )
    assert client.calls[0][2] == {"fields": {"Back": "x"}, "expected_revision": "r1-" + "a" * 32}


def test_note_type_reads_map_to_read_only_routes():
    client = FakeClient()
    service = AnkiMcpV2Service(client)
    service.list_note_types()
    service.get_note_type("1791823645001")
    assert client.calls == [
        ("GET", "/v2/note-types", None),
        ("GET", "/v2/note-types/1791823645001", None),
    ]


def test_create_note_sends_only_explicit_values():
    client = FakeClient()
    AnkiMcpV2Service(client).create_note(
        deck="#UFPR", note_type="Enhanced Basic", fields={"Front": "f"}, tags=["t"]
    )
    assert client.calls == [
        (
            "POST",
            "/v2/notes",
            {"deck": "#UFPR", "note_type": "Enhanced Basic", "fields": {"Front": "f"}, "tags": ["t"]},
        )
    ]
    client.calls.clear()
    AnkiMcpV2Service(client).create_note(
        deck="d", note_type="Basic", fields={"Front": "f"}, allow_duplicate=True
    )
    assert client.calls[0][2]["allow_duplicate"] is True and "tags" not in client.calls[0][2]


def test_delete_notes_forwards_the_protection_fields_untouched():
    client = FakeClient()
    notes = [
        {"note_id": "1", "expected_card_ids": ["2", "3"], "expected_revision": "r1-" + "b" * 32}
    ]
    AnkiMcpV2Service(client).delete_notes(notes)
    assert client.calls == [("POST", "/v2/notes/delete", {"notes": notes})]


def test_tag_operations_map_one_to_one():
    client = FakeClient()
    service = AnkiMcpV2Service(client)
    service.list_tags(prefix="en", limit=5, offset=2)
    service.rename_tag("a", "b", expected_note_count=3)
    service.rename_tag("a", "b", dry_run=True)
    service.delete_tag("a", expected_note_count=3)
    service.delete_tag("a", dry_run=True)
    assert client.calls == [
        ("GET", "/v2/tags", {"limit": 5, "offset": 2, "prefix": "en"}),
        ("POST", "/v2/tags/rename", {"old": "a", "new": "b", "expected_note_count": 3}),
        ("POST", "/v2/tags/rename", {"old": "a", "new": "b", "dry_run": True}),
        ("POST", "/v2/tags/delete", {"tag": "a", "expected_note_count": 3}),
        ("POST", "/v2/tags/delete", {"tag": "a", "dry_run": True}),
    ]


def test_deck_operations_map_one_to_one_and_quote_ids():
    client = FakeClient()
    service = AnkiMcpV2Service(client)
    service.create_deck("A::B")
    service.rename_deck("12", "C::D", expected_name="A::B")
    service.delete_deck("12", expected_name="C::D")
    service.delete_deck("1/../2", expected_name="x")
    assert client.calls == [
        ("POST", "/v2/decks", {"name": "A::B"}),
        ("PATCH", "/v2/decks/12", {"name": "C::D", "expected_name": "A::B"}),
        ("DELETE", "/v2/decks/12", {"expected_name": "C::D"}),
        ("DELETE", "/v2/decks/1%2F..%2F2", {"expected_name": "x"}),
    ]


def test_move_cards_maps_to_the_move_route():
    client = FakeClient()
    AnkiMcpV2Service(client).move_cards(["1", "2"], "Medicina::Cardio")
    assert client.calls == [
        ("POST", "/v2/cards/move", {"card_ids": ["1", "2"], "target_deck": "Medicina::Cardio"})
    ]
