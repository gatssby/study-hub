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
        return BinaryResponse(b"image-bytes", "image/png")


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
            assert names == {
                "anki_health",
                "anki_list_decks",
                "anki_search_notes",
                "anki_search_cards",
                "anki_get_note",
                "anki_get_card",
                "anki_update_note",
                "anki_get_media",
            }
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
