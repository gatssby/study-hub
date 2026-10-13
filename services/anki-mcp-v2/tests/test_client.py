from __future__ import annotations

import io
import json
import socket
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from anki_mcp_v2.client import ApiV2Client, PRODUCTION_API_BASE_URL
from anki_mcp_v2.errors import McpApiError


class JsonResponse:
    status = 200

    def __init__(self, value: dict[str, object]) -> None:
        self._data = json.dumps(value).encode("utf-8")
        self.headers = type(
            "Headers",
            (),
            {
                "get": lambda _self, key: str(len(self._data)) if key == "Content-Length" else None,
                "get_content_type": lambda _self: "application/json",
            },
        )()

    def __enter__(self) -> JsonResponse:
        return self

    def __exit__(self, *_args: object) -> bool:
        return False

    def read(self, _limit: int) -> bytes:
        return self._data


def test_get_note_uses_bearer_and_preserves_large_string_id(monkeypatch):
    observed: dict[str, object] = {}

    def fake_urlopen(request, *, timeout):
        observed["method"] = request.method
        observed["url"] = request.full_url
        observed["authorization"] = request.get_header("Authorization")
        observed["timeout"] = timeout
        return JsonResponse({"note_id": "1791823645036", "card_ids": ["1791823645037"]})

    monkeypatch.setattr("anki_mcp_v2.client.urlopen", fake_urlopen)
    client = ApiV2Client(PRODUCTION_API_BASE_URL, "fixture-token")

    result = client.get_json("/v2/notes/1791823645036")

    assert result["note_id"] == "1791823645036"
    assert result["card_ids"] == ["1791823645037"]
    assert observed == {
        "method": "GET",
        "url": "http://127.0.0.1:8770/v2/notes/1791823645036",
        "authorization": "Bearer fixture-token",
        "timeout": 10.0,
    }


@pytest.mark.parametrize(
    "base_url",
    [
        "http://127.0.0.1:8767",
        "https://anki.gatssby.com.br",
        "http://127.0.0.1:27701",
        "file:///tmp/anki-api",
    ],
)
def test_client_rejects_non_v2_production_target(base_url):
    with pytest.raises(ValueError, match="127.0.0.1:8770"):
        ApiV2Client(base_url, "fixture-token")


@pytest.mark.parametrize(
    ("status", "body", "expected_code"),
    [
        (401, {"error": {"code": "unauthorized", "message": "missing or invalid bearer token"}}, "unauthorized"),
        (404, {"error": {"code": "note_not_found", "message": "note does not exist"}}, "note_not_found"),
        (409, {"error": {"code": "full_sync_required", "message": "full sync required"}}, "full_sync_required"),
        (422, {"error": {"code": "invalid_request", "message": "invalid request"}}, "invalid_request"),
        (502, {"error": {"code": "sync_failed", "message": "sync failed"}}, "sync_failed"),
        (503, {"error": {"code": "collection_busy", "message": "retry shortly"}}, "collection_busy"),
    ],
)
def test_api_error_is_sanitized_and_structured(monkeypatch, status, body, expected_code):
    payload = json.dumps(body).encode("utf-8")

    def fake_urlopen(request, *, timeout):
        raise HTTPError(request.full_url, status, "fixture", {}, io.BytesIO(payload))

    monkeypatch.setattr("anki_mcp_v2.client.urlopen", fake_urlopen)

    with pytest.raises(McpApiError) as raised:
        ApiV2Client(PRODUCTION_API_BASE_URL, "fixture-token").get_json("/v2/health")

    error = raised.value
    assert error.code == expected_code
    assert error.status == status
    assert error.as_payload()["error"]["code"] == expected_code
    assert "fixture-token" not in str(error)


def test_timeout_is_stable_and_does_not_include_token(monkeypatch):
    def fake_urlopen(_request, *, timeout):
        raise socket.timeout("too slow")

    monkeypatch.setattr("anki_mcp_v2.client.urlopen", fake_urlopen)

    with pytest.raises(McpApiError) as raised:
        ApiV2Client(PRODUCTION_API_BASE_URL, "fixture-token").patch_json(
            "/v2/notes/1791823645036", {"fields": {"Back": "value"}}
        )

    assert raised.value.code == "anki_api_timeout"
    assert raised.value.status is None
    assert "fixture-token" not in str(raised.value)


def test_unreachable_api_is_stable(monkeypatch):
    def fake_urlopen(_request, *, timeout):
        raise URLError("connection refused")

    monkeypatch.setattr("anki_mcp_v2.client.urlopen", fake_urlopen)

    with pytest.raises(McpApiError) as raised:
        ApiV2Client(PRODUCTION_API_BASE_URL, "fixture-token").get_json("/v2/health")

    assert raised.value.code == "anki_api_unavailable"


def test_update_uses_write_timeout_and_exact_json_body(monkeypatch):
    observed: dict[str, object] = {}

    def fake_urlopen(request, *, timeout):
        observed["method"] = request.method
        observed["body"] = json.loads(request.data.decode("utf-8"))
        observed["timeout"] = timeout
        return JsonResponse({"note_id": "1791823645036", "sync": {"before": "ok", "after": "ok"}})

    monkeypatch.setattr("anki_mcp_v2.client.urlopen", fake_urlopen)
    client = ApiV2Client(PRODUCTION_API_BASE_URL, "fixture-token")

    result = client.patch_json(
        "/v2/notes/1791823645036",
        {
            "fields": {"Back": "<pre><code>MCP_V2_PATCH_OK_20261013</code></pre>"},
            "add_tags": ["anki_gpt_v2_mcp_written"],
        },
    )

    assert result["note_id"] == "1791823645036"
    assert observed == {
        "method": "PATCH",
        "body": {
            "fields": {"Back": "<pre><code>MCP_V2_PATCH_OK_20261013</code></pre>"},
            "add_tags": ["anki_gpt_v2_mcp_written"],
        },
        "timeout": 45.0,
    }
