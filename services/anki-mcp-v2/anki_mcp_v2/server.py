from __future__ import annotations

import base64
import json
import os
from typing import Annotated, Any, Callable, TypeVar

from mcp.server import MCPServer
from mcp.types import CallToolResult, ImageContent, TextContent, ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field

from .client import ApiV2Client, PRODUCTION_API_BASE_URL
from .errors import McpApiError
from .service import AnkiMcpV2Service

mcp = MCPServer(
    "Anki GPT MCP v2",
    version="0.1.0",
    instructions=(
        "A thin MCP adapter over Anki GPT API v2. IDs are strings. "
        "The API owns collection access, validation, writes, and sync behavior. "
        "Read a note (anki_get_note) before changing or deleting it and pass back its "
        "revision. Notes list their images under `media`; call anki_get_media only for the "
        "images you need to see."
    ),
)
_service: AnkiMcpV2Service | None = None
T = TypeVar("T")


READ = ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False)
WRITE = ToolAnnotations(
    read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False
)
WRITE_IDEMPOTENT = ToolAnnotations(
    read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False
)
DESTRUCTIVE = ToolAnnotations(
    read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False
)



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


@mcp.tool(annotations=READ)
def anki_health() -> Any:
    """Read Anki GPT API v2 health and sync status without performing a sync."""
    return _tool_result(lambda: get_service().health())


@mcp.tool(annotations=READ)
def anki_list_decks(
    root: str | None = None, limit: int = 50, offset: int = 0
) -> Any:
    """List Anki decks through API v2. Deck IDs remain strings."""
    return _tool_result(lambda: get_service().list_decks(root=root, limit=limit, offset=offset))


@mcp.tool(annotations=READ)
def anki_search_notes(
    query: str, limit: int = 50, offset: int = 0
) -> Any:
    """Search notes using native Anki query syntax through API v2."""
    return _tool_result(lambda: get_service().search_notes(query, limit=limit, offset=offset))


@mcp.tool(annotations=READ)
def anki_search_cards(
    query: str, limit: int = 50, offset: int = 0
) -> Any:
    """Search cards using native Anki query syntax through API v2."""
    return _tool_result(lambda: get_service().search_cards(query, limit=limit, offset=offset))


@mcp.tool(annotations=READ)
def anki_get_note(note_id: str) -> Any:
    """Get a single Anki note by its string note ID through API v2."""
    return _tool_result(lambda: get_service().get_note(note_id))


@mcp.tool(annotations=READ)
def anki_get_card(card_id: str) -> Any:
    """Get a single Anki card by its string card ID through API v2."""
    return _tool_result(lambda: get_service().get_card(card_id))


IMAGE_SIGNATURES = {
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/gif": (b"GIF87a", b"GIF89a"),
}
SUPPORTED_IMAGES = "image/png, image/jpeg, image/webp, image/gif"
REVISION_HELP = "Pass the `revision` returned by anki_get_note as expected_revision."


class DeleteNoteItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note_id: str
    expected_card_ids: list[str] = Field(
        min_length=1, max_length=100, description="Every card id of the note, as read just now."
    )
    expected_revision: str = Field(description="`revision` from anki_get_note, unchanged.")


def _is_real_image(content_type: str, data: bytes) -> bool:
    if content_type == "image/webp":
        return data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    return any(data.startswith(sig) for sig in IMAGE_SIGNATURES.get(content_type, ()))


@mcp.tool(annotations=READ)
def anki_get_media(filename: str) -> Any:
    """See one image used by a note, as a real image (not text).

    Take `filename` from the `media` list of anki_get_note (entries with viewable=true).
    Only png, jpeg, webp and gif up to 8 MiB are returned; audio, svg and other files
    return an explicit unsupported_media_type error. Call it only for images you need.
    """

    def media() -> list[ImageContent] | CallToolResult:
        response = get_service().get_media(filename)
        if response.content_type not in SUPPORTED_IMAGES.split(", ") or not _is_real_image(
            response.content_type, response.data
        ):
            return _error_result(
                McpApiError(
                    "unsupported_media_type",
                    f"only {SUPPORTED_IMAGES} images can be viewed",
                )
            )
        return [
            ImageContent(
                type="image",
                data=base64.b64encode(response.data).decode("ascii"),
                mime_type=response.content_type,
            )
        ]

    return _tool_result(media)


@mcp.tool(annotations=WRITE)
def anki_update_note(
    note_id: str,
    fields: dict[str, str] | None = None,
    add_tags: list[str] | None = None,
    remove_tags: list[str] | None = None,
    expected_revision: str | None = None,
) -> Any:
    """Update fields and/or add/remove tags of one note. Never changes its cards.

    Always pass expected_revision (the `revision` from anki_get_note): if the note changed
    since you read it the call fails with stale_revision and nothing is written.
    """
    return _tool_result(
        lambda: get_service().update_note(
            note_id,
            fields=fields,
            add_tags=add_tags,
            remove_tags=remove_tags,
            expected_revision=expected_revision,
        )
    )


@mcp.tool(annotations=READ)
def anki_list_note_types() -> Any:
    """List note types (name, id, kind, field names in order, card template names)."""
    return _tool_result(lambda: get_service().list_note_types())


@mcp.tool(annotations=READ)
def anki_get_note_type(note_type_id: str) -> Any:
    """Get one note type: ordered fields, card templates, sort and duplicate-check field."""
    return _tool_result(lambda: get_service().get_note_type(note_type_id))


@mcp.tool(annotations=WRITE)
def anki_create_note(
    deck: str,
    note_type: str,
    fields: dict[str, str],
    tags: list[str] | None = None,
    allow_duplicate: bool | None = None,
) -> Any:
    """Create one note; Anki generates its cards from the note type templates.

    `deck` and `note_type` must already exist (name or id; see anki_list_decks and
    anki_list_note_types). `fields` keys must be exactly the note type's field names;
    unknown names are rejected. Returns note_id, card_ids and revision.
    """
    return _tool_result(
        lambda: get_service().create_note(
            deck=deck,
            note_type=note_type,
            fields=fields,
            tags=tags,
            allow_duplicate=allow_duplicate,
        )
    )


@mcp.tool(annotations=DESTRUCTIVE)
def anki_delete_notes(
    notes: Annotated[list[DeleteNoteItem], Field(min_length=1, max_length=10)],
) -> Any:
    """PERMANENTLY delete up to 10 notes and all their cards. Cannot be undone here.

    Only after the user explicitly asked for the deletion. Read each note first with
    anki_get_note and pass its note_id, ALL its card_ids and its revision. Any mismatch
    (cards or revision changed) refuses the whole batch and deletes nothing.
    """
    return _tool_result(
        lambda: get_service().delete_notes([item.model_dump() for item in notes])
    )


@mcp.tool(annotations=READ)
def anki_list_tags(prefix: str | None = None, limit: int = 100, offset: int = 0) -> Any:
    """List tags in the collection, optionally only those starting with `prefix`."""
    return _tool_result(lambda: get_service().list_tags(prefix=prefix, limit=limit, offset=offset))


@mcp.tool(annotations=WRITE)
def anki_rename_tag(
    old: str,
    new: str,
    expected_note_count: int | None = None,
    dry_run: bool | None = None,
) -> Any:
    """Rename a tag (and its `::` children) on every note in the collection.

    First call with dry_run=true to get affected_note_count, then repeat with
    expected_note_count set to it. Wildcards are not allowed. Renaming onto an existing tag merges them.
    """
    return _tool_result(
        lambda: get_service().rename_tag(
            old, new, expected_note_count=expected_note_count, dry_run=dry_run
        )
    )


@mcp.tool(annotations=DESTRUCTIVE)
def anki_delete_tag(
    tag: str,
    expected_note_count: int | None = None,
    dry_run: bool | None = None,
) -> Any:
    """Remove a tag (and its `::` children) from every note. Notes and cards are NOT deleted.

    First call with dry_run=true to get affected_note_count, then repeat with
    expected_note_count set to it. Not the same as deleting notes.
    """
    return _tool_result(
        lambda: get_service().delete_tag(
            tag, expected_note_count=expected_note_count, dry_run=dry_run
        )
    )


@mcp.tool(annotations=WRITE_IDEMPOTENT)
def anki_create_deck(name: str) -> Any:
    """Create a deck; use `Parent::Child` for hierarchy. Returns the existing deck if it exists."""
    return _tool_result(lambda: get_service().create_deck(name))


@mcp.tool(annotations=WRITE)
def anki_rename_deck(deck_id: str, name: str, expected_name: str | None = None) -> Any:
    """Rename (or reparent with `::`) a deck; its cards and subdecks follow.

    Fails if the target name exists. Pass the current name as expected_name to guard against races.
    """
    return _tool_result(
        lambda: get_service().rename_deck(deck_id, name, expected_name=expected_name)
    )


@mcp.tool(annotations=DESTRUCTIVE)
def anki_delete_deck(deck_id: str, expected_name: str) -> Any:
    """Delete an EMPTY deck. A deck with cards or subdecks is refused (card_count is reported).

    Cards are never moved or deleted implicitly; move them first with anki_move_cards.
    """
    return _tool_result(lambda: get_service().delete_deck(deck_id, expected_name=expected_name))


@mcp.tool(annotations=WRITE)
def anki_move_cards(card_ids: list[str], target_deck: str) -> Any:
    """Move up to 200 cards to an existing deck (name or id), all or nothing.

    Only the deck changes: scheduling, review history, fields and tags are untouched.
    """
    return _tool_result(lambda: get_service().move_cards(card_ids, target_deck))


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
    if os.environ.get('STUDY_HUB_FO_TOOLS', 'false').lower() == 'true':
        from fo_hub.mcp import register_tools
        register_tools(mcp)
    mcp.run(
        transport="streamable-http",
        host=host,
        port=port,
        streamable_http_path="/mcp",
    )
