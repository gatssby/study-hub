from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from .errors import McpApiError

PRODUCTION_API_BASE_URL = "http://127.0.0.1:8770"
DEFAULT_READ_TIMEOUT_SECONDS = 10.0
DEFAULT_WRITE_TIMEOUT_SECONDS = 45.0
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_MEDIA_BYTES = 20 * 1024 * 1024

_DEFAULT_CODES = {
    401: "unauthorized",
    404: "not_found",
    409: "conflict",
    422: "invalid_request",
    502: "sync_failed",
    503: "collection_busy",
}


@dataclass(frozen=True)
class BinaryResponse:
    data: bytes
    content_type: str


class ApiV2Client:
    """Authenticated HTTP translation layer for the local Anki API v2."""

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        read_timeout_seconds: float = DEFAULT_READ_TIMEOUT_SECONDS,
        write_timeout_seconds: float = DEFAULT_WRITE_TIMEOUT_SECONDS,
    ) -> None:
        if base_url != PRODUCTION_API_BASE_URL:
            raise ValueError(f"ANKI_MCP_V2_API_URL must be exactly {PRODUCTION_API_BASE_URL}")
        if not isinstance(token, str) or not token.strip():
            raise ValueError("ANKI_API_TOKEN is required")
        if read_timeout_seconds <= 0 or write_timeout_seconds <= 0:
            raise ValueError("timeouts must be positive")
        self._base_url = base_url
        self._token = token.strip()
        self._read_timeout_seconds = float(read_timeout_seconds)
        self._write_timeout_seconds = float(write_timeout_seconds)

    def get_json(self, path: str, query: dict[str, str | int] | None = None) -> dict[str, Any]:
        return self._json_request("GET", path, query=query, timeout=self._read_timeout_seconds)

    def post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._json_request(
            "POST", path, payload=payload, timeout=self._read_timeout_seconds
        )

    def patch_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._json_request(
            "PATCH", path, payload=payload, timeout=self._write_timeout_seconds
        )

    def get_binary(self, path: str, *, max_bytes: int = MAX_MEDIA_BYTES) -> BinaryResponse:
        data, content_type = self._request(
            "GET", path, timeout=self._read_timeout_seconds, max_bytes=max_bytes
        )
        return BinaryResponse(data=data, content_type=content_type)

    def _json_request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, str | int] | None = None,
        payload: dict[str, Any] | None = None,
        timeout: float,
    ) -> dict[str, Any]:
        data, content_type = self._request(
            method,
            path,
            query=query,
            payload=payload,
            timeout=timeout,
            max_bytes=MAX_JSON_BYTES,
        )
        if content_type != "application/json":
            raise McpApiError("anki_api_protocol_error", "Anki API returned an unexpected content type")
        try:
            value = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise McpApiError("anki_api_protocol_error", "Anki API returned invalid JSON") from exc
        if not isinstance(value, dict):
            raise McpApiError("anki_api_protocol_error", "Anki API returned an invalid JSON shape")
        return value

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, str | int] | None = None,
        payload: dict[str, Any] | None = None,
        timeout: float,
        max_bytes: int,
    ) -> tuple[bytes, str]:
        url = self._url(path, query)
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._token}",
            "User-Agent": "anki-mcp-v2/0.1",
        }
        body = None
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=timeout) as response:
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > max_bytes:
                    raise McpApiError("anki_api_response_too_large", "Anki API response is too large")
                data = response.read(max_bytes + 1)
                if len(data) > max_bytes:
                    raise McpApiError("anki_api_response_too_large", "Anki API response is too large")
                return data, response.headers.get_content_type()
        except HTTPError as exc:
            raise self._http_error(exc) from None
        except (TimeoutError, socket.timeout) as exc:
            raise McpApiError("anki_api_timeout", "Anki API request timed out") from exc
        except URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                raise McpApiError("anki_api_timeout", "Anki API request timed out") from exc
            raise McpApiError("anki_api_unavailable", "Anki API is unavailable") from exc

    def _url(self, path: str, query: dict[str, str | int] | None) -> str:
        if not path.startswith("/v2/") or path == "/v2/sync":
            raise ValueError("API path must be an allowed API v2 route")
        if "?" in path or "#" in path:
            raise ValueError("API path must not include query or fragment")
        url = self._base_url + path
        if query:
            url += "?" + urlencode(query)
        return url

    @staticmethod
    def _http_error(exc: HTTPError) -> McpApiError:
        payload: dict[str, Any] | None = None
        try:
            raw = exc.read(64 * 1024)
            decoded = json.loads(raw.decode("utf-8"))
            if isinstance(decoded, dict) and isinstance(decoded.get("error"), dict):
                payload = decoded["error"]
        except Exception:
            payload = None

        code = _DEFAULT_CODES.get(exc.code, "anki_api_http_error")
        message = "Anki API request failed"
        details: dict[str, Any] | None = None
        if payload:
            if isinstance(payload.get("code"), str) and payload["code"]:
                code = payload["code"]
            if isinstance(payload.get("message"), str) and payload["message"]:
                message = payload["message"]
            if isinstance(payload.get("details"), dict):
                details = payload["details"]
        return McpApiError(code, message, status=exc.code, details=details)
