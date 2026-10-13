from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from mcp import Client

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

import anki_mcp_v2.server as server_module
from anki_mcp_v2.client import BinaryResponse
from anki_mcp_v2.errors import McpApiError


class FakeService:
    def health(self):
        return {"status": "ok", "sync_state": "ok"}

    def list_decks(self, **kwargs):
        return {"items": [], **kwargs}

    def search_notes(self, query, **kwargs):
        return {"query": query, "kind": "notes", **kwargs}

    def search_cards(self, query, **kwargs):
        return {"query": query, "kind": "cards", **kwargs}

    def get_note(self, note_id):
        return {"note_id": note_id, "card_ids": ["1791823645037"]}

    def get_card(self, card_id):
        return {"card_id": card_id, "note_id": "1791823645036"}

    def update_note(self, note_id, **kwargs):
        return {"note_id": note_id, **kwargs}

    def get_media(self, filename):
        if filename in MEDIA:
            if isinstance(MEDIA[filename], Exception):
                raise MEDIA[filename]
            return MEDIA[filename]
        return BinaryResponse(PNG, "image/png")

    def list_note_types(self):
        return {"total": 1, "items": [{"id": "1", "name": "Basic"}]}

    def get_note_type(self, note_type_id):
        return {"id": note_type_id, "name": "Basic"}

    def create_note(self, **kwargs):
        # The real service omits arguments the model did not pass; mirror that here.
        return {"note_id": "9", "card_ids": ["10"], **{k: v for k, v in kwargs.items() if v is not None}}

    def delete_notes(self, notes):
        return {"deleted": notes}

    def list_tags(self, **kwargs):
        return {"items": [], **kwargs}

    def rename_tag(self, old, new, **kwargs):
        return {"old": old, "new": new, **kwargs}

    def delete_tag(self, tag, **kwargs):
        return {"tag": tag, **{k: v for k, v in kwargs.items() if v is not None}}

    def create_deck(self, name):
        return {"name": name}

    def rename_deck(self, deck_id, name, **kwargs):
        return {"deck_id": deck_id, "name": name, **kwargs}

    def delete_deck(self, deck_id, **kwargs):
        return {"deck_id": deck_id, **kwargs}

    def move_cards(self, card_ids, target_deck):
        return {"card_ids": card_ids, "target_deck": target_deck}


EXPECTED_TOOLS = {
    "anki_health",
    "anki_list_decks",
    "anki_search_notes",
    "anki_search_cards",
    "anki_get_note",
    "anki_get_card",
    "anki_update_note",
    "anki_get_media",
    "anki_list_note_types",
    "anki_get_note_type",
    "anki_create_note",
    "anki_delete_notes",
    "anki_list_tags",
    "anki_rename_tag",
    "anki_delete_tag",
    "anki_create_deck",
    "anki_rename_deck",
    "anki_delete_deck",
    "anki_move_cards",
}
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
MEDIA = {
    "a.png": BinaryResponse(PNG, "image/png"),
    "a.jpg": BinaryResponse(b"\xff\xd8\xff\xe0jpeg", "image/jpeg"),
    "a.webp": BinaryResponse(b"RIFF\x00\x00\x00\x00WEBPVP8 ", "image/webp"),
    "a.gif": BinaryResponse(b"GIF89a....", "image/gif"),
    "a.svg": BinaryResponse(b"<svg/>", "image/svg+xml"),
    "a.mp3": BinaryResponse(b"ID3", "audio/mpeg"),
    "a.bin": BinaryResponse(b"\x00\x01", "application/octet-stream"),
    "big.png": McpApiError("anki_api_response_too_large", "Anki API response is too large"),
}


class BusyService(FakeService):
    def health(self):
        raise McpApiError("collection_busy", "collection is busy; retry shortly", status=503)


def test_mcp_exposes_only_approved_tools_and_string_id_schemas():
    previous = server_module._service
    server_module._service = FakeService()

    async def exercise():
        async with Client(server_module.mcp) as client:
            tools = await client.list_tools()
            names = {tool.name for tool in tools.tools}
            assert names == EXPECTED_TOOLS
            note_tool = next(tool for tool in tools.tools if tool.name == "anki_get_note")
            card_tool = next(tool for tool in tools.tools if tool.name == "anki_get_card")
            assert note_tool.input_schema["properties"]["note_id"]["type"] == "string"
            assert card_tool.input_schema["properties"]["card_id"]["type"] == "string"
            result = await client.call_tool("anki_get_note", {"note_id": "1791823645036"})
            assert json.loads(result.content[0].text)["note_id"] == "1791823645036"

    try:
        asyncio.run(exercise())
    finally:
        server_module._service = previous


def test_mcp_returns_structured_error_content_without_traceback():
    previous = server_module._service
    server_module._service = BusyService()

    async def exercise():
        async with Client(server_module.mcp) as client:
            result = await client.call_tool("anki_health", {})
            assert result.is_error is True
            payload = json.loads(result.content[0].text)
            assert payload == {
                "error": {
                    "code": "collection_busy",
                    "message": "collection is busy; retry shortly",
                    "status": 503,
                }
            }
            assert "Traceback" not in result.content[0].text

    try:
        asyncio.run(exercise())
    finally:
        server_module._service = previous


def test_get_media_returns_mcp_image_content():
    previous = server_module._service
    server_module._service = FakeService()

    async def exercise():
        async with Client(server_module.mcp) as client:
            result = await client.call_tool("anki_get_media", {"filename": "diagram.png"})
            image = result.content[0]
            assert image.type == "image"
            assert image.mime_type == "image/png"

    try:
        asyncio.run(exercise())
    finally:
        server_module._service = previous


def test_main_starts_streamable_http_on_loopback(monkeypatch):
    observed = {}

    def fake_run(*, transport, **kwargs):
        observed["transport"] = transport
        observed.update(kwargs)

    monkeypatch.setattr(server_module.mcp, "run", fake_run)
    monkeypatch.setenv("ANKI_API_TOKEN", "fixture-token")
    monkeypatch.setenv("ANKI_MCP_V2_HOST", "127.0.0.1")
    monkeypatch.setenv("ANKI_MCP_V2_PORT", "18771")

    server_module.main()

    assert observed == {
        "transport": "streamable-http",
        "host": "127.0.0.1",
        "port": 18771,
        "streamable_http_path": "/mcp",
    }


def test_streamable_http_process_allows_handshake_and_tool_listing():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    env = {
        **os.environ,
        "PYTHONPATH": str(SERVICE_ROOT),
        "ANKI_API_TOKEN": "fixture-token",
        "ANKI_MCP_V2_HOST": "127.0.0.1",
        "ANKI_MCP_V2_PORT": str(port),
    }
    process = subprocess.Popen(
        [sys.executable, "-m", "anki_mcp_v2"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    async def exercise():
        deadline = time.monotonic() + 10
        while True:
            try:
                async with Client(f"http://127.0.0.1:{port}/mcp") as client:
                    tools = await client.list_tools()
                    assert "anki_health" in {tool.name for tool in tools.tools}
                    return
            except Exception:
                if time.monotonic() >= deadline:
                    raise
                await asyncio.sleep(0.1)

    try:
        asyncio.run(exercise())
    finally:
        process.terminate()
        process.wait(timeout=10)


def _with_service(service, coro_fn):
    previous = server_module._service
    server_module._service = service

    async def exercise():
        async with Client(server_module.mcp) as client:
            return await coro_fn(client)

    try:
        return asyncio.run(exercise())
    finally:
        server_module._service = previous


def test_get_media_returns_one_image_content_with_the_exact_bytes_and_mime():
    import base64

    for name, mime in [
        ("a.png", "image/png"),
        ("a.jpg", "image/jpeg"),
        ("a.webp", "image/webp"),
        ("a.gif", "image/gif"),
    ]:

        async def call(client, name=name):
            return await client.call_tool("anki_get_media", {"filename": name})

        result = _with_service(FakeService(), call)
        assert result.is_error is not True
        assert len(result.content) == 1
        image = result.content[0]
        assert image.type == "image" and image.mime_type == mime
        assert base64.b64decode(image.data) == MEDIA[name].data
        assert not any(getattr(c, "type", "") == "text" for c in result.content)


def test_get_media_refuses_non_image_and_unsupported_image_types_explicitly():
    for name in ("a.svg", "a.mp3", "a.bin"):

        async def call(client, name=name):
            return await client.call_tool("anki_get_media", {"filename": name})

        result = _with_service(FakeService(), call)
        assert result.is_error is True
        payload = json.loads(result.content[0].text)
        assert payload["error"]["code"] == "unsupported_media_type"
        assert "image/png" in payload["error"]["message"]
        assert all(c.type == "text" for c in result.content)


def test_get_media_too_large_is_a_structured_error_not_an_exception():
    async def call(client):
        return await client.call_tool("anki_get_media", {"filename": "big.png"})

    result = _with_service(FakeService(), call)
    assert result.is_error is True
    assert json.loads(result.content[0].text)["error"]["code"] == "anki_api_response_too_large"


def test_get_media_rejects_when_mime_is_image_but_bytes_do_not_match():
    MEDIA["lie.png"] = BinaryResponse(b"<html>nope</html>", "image/png")
    try:

        async def call(client):
            return await client.call_tool("anki_get_media", {"filename": "lie.png"})

        result = _with_service(FakeService(), call)
        assert result.is_error is True
        assert json.loads(result.content[0].text)["error"]["code"] == "unsupported_media_type"
    finally:
        del MEDIA["lie.png"]


def test_tool_annotations_mark_reads_writes_and_destructive_tools():
    async def call(client):
        return {t.name: t.annotations for t in (await client.list_tools()).tools}

    ann = _with_service(FakeService(), call)
    reads = {
        "anki_health", "anki_list_decks", "anki_search_notes", "anki_search_cards",
        "anki_get_note", "anki_get_card", "anki_get_media", "anki_list_note_types",
        "anki_get_note_type", "anki_list_tags",
    }
    destructive = {"anki_delete_notes", "anki_delete_tag", "anki_delete_deck"}
    for name in reads:
        assert ann[name].read_only_hint is True, name
    for name in set(EXPECTED_TOOLS) - reads:
        assert ann[name].read_only_hint is False, name
        assert ann[name].destructive_hint is (name in destructive), name
    for name in EXPECTED_TOOLS:
        assert ann[name].open_world_hint is False, name


def test_new_tools_expose_string_ids_and_required_protection_inputs():
    async def call(client):
        return {t.name: t.input_schema for t in (await client.list_tools()).tools}

    schemas = _with_service(FakeService(), call)
    assert schemas["anki_get_note_type"]["properties"]["note_type_id"]["type"] == "string"
    assert schemas["anki_rename_deck"]["properties"]["deck_id"]["type"] == "string"
    assert set(schemas["anki_delete_deck"]["required"]) == {"deck_id", "expected_name"}
    assert set(schemas["anki_create_note"]["required"]) == {"deck", "note_type", "fields"}
    assert set(schemas["anki_move_cards"]["required"]) == {"card_ids", "target_deck"}
    assert schemas["anki_move_cards"]["properties"]["card_ids"]["items"]["type"] == "string"
    assert "expected_revision" in schemas["anki_update_note"]["properties"]
    items = schemas["anki_delete_notes"]["properties"]["notes"]
    assert items["type"] == "array" and items["minItems"] == 1 and items["maxItems"] == 10


def test_delete_notes_tool_rejects_items_missing_protections_before_the_service():
    class Boom(FakeService):
        def delete_notes(self, notes):
            raise AssertionError("must not reach the service")

    async def call(client):
        return await client.call_tool(
            "anki_delete_notes", {"notes": [{"note_id": "1", "expected_card_ids": ["2"]}]}
        )

    result = _with_service(Boom(), call)
    assert result.is_error is True


def test_new_tools_round_trip_to_the_service_with_only_explicit_arguments():
    async def call(client):
        out = {}
        out["create"] = await client.call_tool(
            "anki_create_note",
            {"deck": "#UFPR", "note_type": "Enhanced Basic", "fields": {"Front": "f"}},
        )
        out["move"] = await client.call_tool(
            "anki_move_cards", {"card_ids": ["1"], "target_deck": "D"}
        )
        out["del"] = await client.call_tool(
            "anki_delete_deck", {"deck_id": "5", "expected_name": "X"}
        )
        out["tag"] = await client.call_tool("anki_delete_tag", {"tag": "t", "dry_run": True})
        return out

    out = _with_service(FakeService(), call)
    assert json.loads(out["create"].content[0].text) == {
        "note_id": "9",
        "card_ids": ["10"],
        "deck": "#UFPR",
        "note_type": "Enhanced Basic",
        "fields": {"Front": "f"},
    }
    assert json.loads(out["move"].content[0].text)["target_deck"] == "D"
    assert json.loads(out["del"].content[0].text) == {"deck_id": "5", "expected_name": "X"}
    assert json.loads(out["tag"].content[0].text) == {"tag": "t", "dry_run": True}


def test_server_module_does_not_import_anki_or_touch_the_filesystem_or_legacy():
    import inspect

    import anki_mcp_v2.client as client_module
    import anki_mcp_v2.service as service_module

    for module in (server_module, client_module, service_module):
        text = inspect.getsource(module)
        import re

        assert not re.search(r"^\s*(import|from)\s+anki\b", text, re.MULTILINE)
        assert "sqlite" not in text.lower()
        assert "8767" not in text and "27701" not in text
