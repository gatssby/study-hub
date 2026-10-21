from __future__ import annotations

import asyncio
import os
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
        fo_enabled = os.environ.get('STUDY_HUB_FO_TOOLS', 'false').lower() == 'true'
        if fo_enabled:
            required |= {'fo_list_lessons', 'fo_get_lesson', 'fo_search_materials', 'fo_get_pdf_text',
                         'fo_search_transcripts', 'fo_get_transcript', 'fo_get_sync_status'}
        if names != required:
            raise RuntimeError(f"unexpected MCP tools: {sorted(names)}")
        result = await client.call_tool("anki_health", {})
        if result.is_error:
            raise RuntimeError("anki_health returned an MCP error")
        if fo_enabled:
            result = await client.call_tool('fo_get_sync_status', {})
            if result.is_error:
                raise RuntimeError('fo_get_sync_status returned an MCP error')
    print("MCP_STREAMABLE_HTTP_SMOKE_OK")


if __name__ == "__main__":
    asyncio.run(run(sys.argv[1] if len(sys.argv) == 2 else "http://127.0.0.1:8771/mcp"))
