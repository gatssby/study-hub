"""Independent, read-only MCP adapter for the loopback FO API."""
from __future__ import annotations

import os
import json
from urllib.parse import urlsplit
from typing import Annotated, Any
from pydantic import Field

import httpx
from mcp.server import MCPServer
from mcp.types import CallToolResult, TextContent, ToolAnnotations

ID = Annotated[str, Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9_-]+$")]


def error(code: str, status: int | None = None) -> CallToolResult:
    payload: dict[str, Any] = {"code": code, "message": "FO read failed; inspect API availability or request parameters."}
    if status is not None:
        payload["status"] = status
    return CallToolResult(content=[TextContent(type="text", text=json.dumps({"error": payload}))], is_error=True)


class FOClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8780", *, http: httpx.Client | None = None):
        parsed = urlsplit(base_url)
        if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
                or parsed.username is not None or parsed.password is not None
                or parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
            raise ValueError("FO_API_URL must be a credential-free loopback HTTP origin")
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError("FO_API_URL port is invalid")
        self.base_url = base_url.rstrip("/")
        self.http = http

    def get(self, path: str, **params: Any) -> Any:
        params = {key: value for key, value in params.items() if value is not None}
        try:
            if self.http is not None:
                response = self.http.get(self.base_url + path, params=params,
                                         timeout=20, follow_redirects=False)
            else:
                with httpx.Client(timeout=20, trust_env=False, follow_redirects=False) as http:
                    response = http.get(self.base_url + path, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            return error({404: "fo_not_found", 422: "fo_invalid_request"}.get(status, "fo_api_error"), status)
        except httpx.RequestError:
            return error("fo_api_unavailable")
        except ValueError:
            return error("fo_invalid_response")


def create_server(client: FOClient | None = None) -> MCPServer:
    return register_tools(MCPServer("Federal Online (read-only)", version="0.1.0"), client)


def register_tools(server: MCPServer, client: FOClient | None = None) -> MCPServer:
    """Optional read-only integration; no Anki imports or collection access."""
    client = client or FOClient(os.environ.get("FO_API_URL", "http://127.0.0.1:8780"))
    read = ToolAnnotations(read_only_hint=True, destructive_hint=False,
                           idempotent_hint=True, open_world_hint=False)

    @server.tool(annotations=read)
    def fo_get_lesson(lesson_id: ID) -> Any:
        """Read one lesson; preserve source URLs, citations and observed dates."""
        return client.get("/fo/lessons/" + lesson_id)

    @server.tool(annotations=read)
    def fo_list_lessons(subject: str | None = None, front: str | None = None,
                        module: str | None = None, title: str | None = None,
                        include_missing: bool = False,
                        limit: Annotated[int, Field(ge=1, le=200)] = 50,
                        offset: Annotated[int, Field(ge=0)] = 0) -> Any:
        """List lessons and their source metadata; does not synchronize."""
        return client.get("/fo/lessons", subject=subject, front=front, module=module,
                          title=title, include_missing=include_missing, limit=limit, offset=offset)

    @server.tool(annotations=read)
    def fo_search_materials(subject: str | None = None, front: str | None = None,
                            module: str | None = None, title: str | None = None,
                            type: str | None = None,
                            limit: Annotated[int, Field(ge=1, le=200)] = 50,
                            offset: Annotated[int, Field(ge=0)] = 0) -> Any:
        """Find materials by metadata; returns original source citations and dates."""
        return client.get("/fo/materials", subject=subject, front=front, module=module,
                          title=title, type=type, limit=limit, offset=offset)

    @server.tool(annotations=read)
    def fo_get_pdf_text(material_id: ID, page_start: Annotated[int, Field(ge=1)] = 1,
                        page_end: Annotated[int | None, Field(ge=1)] = None) -> Any:
        """Read already indexed PDF text, including page-level citations; no OCR job."""
        if page_end is not None and page_end < page_start:
            return error("fo_invalid_request")
        return client.get("/fo/materials/" + material_id + "/pdf-text",
                          page_start=page_start, page_end=page_end)

    @server.tool(annotations=read)
    def fo_search_transcripts(q: Annotated[str, Field(min_length=2, max_length=200)],
                              subject: str | None = None,
                              limit: Annotated[int, Field(ge=1, le=200)] = 50) -> Any:
        """Search validated existing transcripts; never runs ASR."""
        return client.get("/fo/transcripts", q=q, subject=subject, limit=limit)

    @server.tool(annotations=read)
    def fo_get_transcript(lesson_id: ID) -> Any:
        """Read a validated transcript for the current lesson version; never runs ASR."""
        return client.get("/fo/transcripts/" + lesson_id)

    @server.tool(annotations=read)
    def fo_get_sync_status() -> Any:
        """Read existing sync status and timestamps; never initiates a sync."""
        return client.get("/fo/sync-status")

    return server


def main() -> None:
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
