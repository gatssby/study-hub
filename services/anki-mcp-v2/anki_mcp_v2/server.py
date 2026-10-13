from __future__ import annotations

import base64
import json
import os
from typing import Any, Callable, TypeVar

from mcp.server import MCPServer
from mcp.types import CallToolResult, ImageContent, TextContent

from .client import ApiV2Client, PRODUCTION_API_BASE_URL
from .errors import McpApiError
from .service import AnkiMcpV2Service

mcp = MCPServer(
    "Anki GPT MCP v2",
    version="0.1.0",
    instructions=(
        "A thin MCP adapter over Anki GPT API v2. IDs are strings. "
        "The API owns collection access, validation, writes, and sync behavior."
    ),
)
_service: AnkiMcpV2Service | None = None
T = TypeVar("T")


def get_service() -> AnkiMcpV2Service:
    global _service
    if _service is None:
        token = os.environ.get("ANKI_API_TOKEN", "")
        api_url = os.environ.get("ANKI_MCP_V2_API_URL", PRODUCTION_API_BASE_URL)
        _service = AnkiMcpV2Service(ApiV2Client(api_url, token))
    return _service


def _tool_result(call: Callable[[], T]) -> T | CallToolResult:
    try:
        return call()
    except McpApiError as exc:
        return _error_result(exc)
    except Exception:
        return _error_result(McpApiError("mcp_internal_error", "MCP request failed"))


def _error_result(error: McpApiError) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(error.as_payload(), ensure_ascii=False))],
        is_error=True,
    )


@mcp.tool()
def anki_health() -> Any:
    """Read Anki GPT API v2 health and sync status without performing a sync."""
    return _tool_result(lambda: get_service().health())


@mcp.tool()
def anki_list_decks(
    root: str | None = None, limit: int = 50, offset: int = 0
) -> Any:
    """List Anki decks through API v2. Deck IDs remain strings."""
    return _tool_result(lambda: get_service().list_decks(root=root, limit=limit, offset=offset))


@mcp.tool()
def anki_search_notes(
    query: str, limit: int = 50, offset: int = 0
) -> Any:
    """Search notes using native Anki query syntax through API v2."""
    return _tool_result(lambda: get_service().search_notes(query, limit=limit, offset=offset))


@mcp.tool()
def anki_search_cards(
    query: str, limit: int = 50, offset: int = 0
) -> Any:
    """Search cards using native Anki query syntax through API v2."""
    return _tool_result(lambda: get_service().search_cards(query, limit=limit, offset=offset))


@mcp.tool()
def anki_get_note(note_id: str) -> Any:
    """Get a single Anki note by its string note ID through API v2."""
    return _tool_result(lambda: get_service().get_note(note_id))


@mcp.tool()
def anki_get_card(card_id: str) -> Any:
    """Get a single Anki card by its string card ID through API v2."""
    return _tool_result(lambda: get_service().get_card(card_id))


@mcp.tool()
def anki_update_note(
    note_id: str,
    fields: dict[str, str] | None = None,
    add_tags: list[str] | None = None,
    remove_tags: list[str] | None = None,
) -> Any:
    """Update allowed fields or tags through API v2; the API owns validation and sync."""
    return _tool_result(
        lambda: get_service().update_note(
            note_id, fields=fields, add_tags=add_tags, remove_tags=remove_tags
        )
    )


@mcp.tool()
def anki_get_media(filename: str) -> Any:
    """Fetch one API-v2 image as MCP image content; non-image media is not exposed as a URL."""

    def media() -> list[ImageContent] | CallToolResult:
        response = get_service().get_media(filename)
        if not response.content_type.startswith("image/"):
            return _error_result(
                McpApiError("unsupported_media_type", "MCP media tool supports image media only")
            )
        return [
            ImageContent(
                type="image",
                data=base64.b64encode(response.data).decode("ascii"),
                mime_type=response.content_type,
            )
        ]

    return _tool_result(media)


def main() -> None:
    host = os.environ.get("ANKI_MCP_V2_HOST", "127.0.0.1")
    if host != "127.0.0.1":
        raise SystemExit("ANKI_MCP_V2_HOST must be 127.0.0.1")
    try:
        port = int(os.environ.get("ANKI_MCP_V2_PORT", "8771"))
    except ValueError as exc:
        raise SystemExit("ANKI_MCP_V2_PORT must be an integer") from exc
    if not 1 <= port <= 65535:
        raise SystemExit("ANKI_MCP_V2_PORT must be between 1 and 65535")
    if not os.environ.get("ANKI_API_TOKEN", "").strip():
        raise SystemExit("ANKI_API_TOKEN is required")
    mcp.run(
        transport="streamable-http",
        host=host,
        port=port,
        streamable_http_path="/mcp",
    )
