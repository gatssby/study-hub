from __future__ import annotations

import asyncio
import sys

from mcp import Client
from mcp.client.streamable_http import streamable_http_client  # verifies installed transport support


async def run(url: str) -> None:
    if not callable(streamable_http_client):
        raise RuntimeError("Streamable HTTP client transport is unavailable")
    async with Client(url) as client:
        tools = await client.list_tools()
        names = {tool.name for tool in tools.tools}
        required = {
            "anki_health",
            "anki_list_decks",
            "anki_search_notes",
            "anki_search_cards",
            "anki_get_note",
            "anki_get_card",
            "anki_update_note",
            "anki_get_media",
        }
        if names != required:
            raise RuntimeError(f"unexpected MCP tools: {sorted(names)}")
        result = await client.call_tool("anki_health", {})
        if result.is_error:
            raise RuntimeError("anki_health returned an MCP error")
    print("MCP_STREAMABLE_HTTP_SMOKE_OK")


if __name__ == "__main__":
    asyncio.run(run(sys.argv[1] if len(sys.argv) == 2 else "http://127.0.0.1:8771/mcp"))
