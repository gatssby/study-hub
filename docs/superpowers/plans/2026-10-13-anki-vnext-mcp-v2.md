# Anki vNext MCP v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver an isolated localhost-only Streamable HTTP MCP v2 that translates approved Anki MCP tools to the API v2, including unit/protocol tests, VPS deployment, and the one authorized end-to-end write verification.

**Architecture:** `services/anki-mcp-v2` contains a small standard-library HTTP client, a service layer that maps MCP tool arguments to API v2 requests, and an MCP server on `127.0.0.1:8771`. It consumes the existing API token from systemd's `EnvironmentFile`, reaches only `http://127.0.0.1:8770/v2`, and contains no Anki collection/sync/legacy domain behavior.

**Tech Stack:** Python 3.13 for the MCP service, `mcp==2.2.0`, standard-library `urllib`, pytest, systemd, SSH/rsync deployment.

**Spec:** `docs/superpowers/specs/2026-10-13-anki-vnext-mcp-v2-design.md`

## Global Constraints

- Create only `services/anki-mcp-v2/` implementation/deployment/docs/tests plus narrowly necessary project documentation.
- Preserve all IDs as strings in MCP schemas, HTTP paths, bodies, and output.
- Production MCP API base URL is exactly `http://127.0.0.1:8770`; no target may use port `8767` or `27701`.
- Do not import `anki`, access SQLite, collection files, media directories, snapshots, or legacy JSON data.
- Do not provide an MCP sync tool or invoke `/v2/sync`.
- Deploy only to `/home/ubuntu/anki-vnext/mcp/` and bind only `127.0.0.1:8771`.
- Do not alter legacy MCP, API, service, nginx, DNS, OAuth, mTLS, Plugin, cronograma, or FO.
- The production write authorization is exactly one call through `anki_update_note` on note `1791823645036`, updating only `Back` to `<pre><code>MCP_V2_PATCH_OK_20261013</code></pre>` and adding only `anki_gpt_v2_mcp_written`.
- The independent verification uses only FULL_DOWNLOAD and destroys the temporary collection afterward.

## Review Focus

- API IDs that look numeric but must remain strings, including large Anki IDs beyond JavaScript-safe integer range.
- API failure bodies that are malformed, absent, or contain unsafe internals; MCP must return a stable sanitized error.
- A write timeout after the API may have started sync; MCP must report timeout without retrying automatically.
- Any route/configuration attempt to reach legacy `:8767`, sync `:27701`, a collection path, or external API address must fail before a network call.
- Streamable HTTP server startup must not bind a public address, and systemd must never print the API bearer token.

---

## File Structure

```text
services/anki-mcp-v2/
  anki_mcp_v2/
    __init__.py          # package version only
    __main__.py          # localhost-only process entry point
    client.py            # typed API v2 HTTP request/response adapter
    errors.py            # sanitized MCP-facing error model
    service.py           # one-to-one tool-to-API mapping
    server.py            # MCP tool declarations and Streamable HTTP startup
  tests/
    conftest.py          # fake HTTP v2 API server and fixtures
    test_client.py       # HTTP/auth/timeout/error/config tests
    test_service.py      # mapping, IDs, payload, absence-of-sync tests
    test_protocol.py     # MCP tool schemas and Streamable HTTP client test
    test_deploy_contract.py # unit/deploy configuration safety assertions
  deploy/
    anki-vnext-mcp.service
    deploy.sh
  requirements.txt
  README.md
```

### Task 1: HTTP client and sanitized error boundary

**Files:**
- Create: `services/anki-mcp-v2/anki_mcp_v2/__init__.py`
- Create: `services/anki-mcp-v2/anki_mcp_v2/errors.py`
- Create: `services/anki-mcp-v2/anki_mcp_v2/client.py`
- Create: `services/anki-mcp-v2/tests/conftest.py`
- Create: `services/anki-mcp-v2/tests/test_client.py`
- Create: `services/anki-mcp-v2/requirements.txt`

**Interfaces:**
- Produces `ApiV2Client(base_url: str, token: str, read_timeout_seconds: float = 10, write_timeout_seconds: float = 45)`.
- Produces `get_json(path: str, query: Mapping[str, str | int] | None = None) -> dict[str, object]`, `post_json(path: str, payload: dict[str, object]) -> dict[str, object]`, `patch_json(path: str, payload: dict[str, object]) -> dict[str, object]`, and `get_binary(path: str) -> BinaryResponse`.
- Produces `McpApiError(code: str, message: str, status: int | None, details: dict[str, object] | None)` with a JSON-safe `as_payload()` method.
- Consumes no Anki modules and no collection paths.

- [ ] **Step 1: Write the failing client contract tests**

```python
def test_get_note_uses_bearer_and_preserves_large_string_id(fake_api):
    client = ApiV2Client(fake_api.url, "fixture-token")

    result = client.get_json("/v2/notes/1791823645036")

    assert result["note_id"] == "1791823645036"
    request = fake_api.requests[-1]
    assert request.method == "GET"
    assert request.path == "/v2/notes/1791823645036"
    assert request.authorization == "Bearer fixture-token"


def test_client_rejects_any_base_url_except_local_v2():
    with pytest.raises(ValueError, match="127.0.0.1:8770"):
        ApiV2Client("http://127.0.0.1:8767", "fixture-token")
```

Also add parameterized tests for 401, 404, 409 `full_sync_required`, 422, 502 `sync_failed`, 503 `collection_busy`, malformed error JSON, connection failure, and timeout. Each must assert a stable `McpApiError` without a traceback or token.

- [ ] **Step 2: Run the client tests to verify RED**

Run: `services/anki-mcp/.venv/bin/python -m pytest services/anki-mcp-v2/tests/test_client.py -q`

Expected: FAIL during collection because `anki_mcp_v2` does not exist.

- [ ] **Step 3: Implement the minimal error model and HTTP client**

```python
@dataclass(frozen=True)
class McpApiError(RuntimeError):
    code: str
    message: str
    status: int | None = None
    details: dict[str, object] | None = None

    def as_payload(self) -> dict[str, object]:
        error: dict[str, object] = {"code": self.code, "message": self.message}
        if self.status is not None:
            error["status"] = self.status
        if self.details:
            error["details"] = self.details
        return {"error": error}
```

Use `urllib.request.Request` and `urlopen`. Require the exact production base URL by default, use `Authorization: Bearer`, select timeout by HTTP method, decode only JSON objects, and map only safe `error` fields returned by API v2.

- [ ] **Step 4: Run client tests to verify GREEN**

Run: `services/anki-mcp/.venv/bin/python -m pytest services/anki-mcp-v2/tests/test_client.py -q`

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

```bash
git add services/anki-mcp-v2
git commit -m "feat: add Anki MCP v2 API client"
```

### Task 2: Thin service mapping and approved tool contracts

**Files:**
- Create: `services/anki-mcp-v2/anki_mcp_v2/service.py`
- Create: `services/anki-mcp-v2/tests/test_service.py`
- Modify: `services/anki-mcp-v2/tests/conftest.py`

**Interfaces:**
- Consumes `ApiV2Client` and `McpApiError` from Task 1.
- Produces `AnkiMcpV2Service` with `health`, `list_decks`, `search_notes`, `search_cards`, `get_note`, `get_card`, `update_note`, and `get_media` methods.
- `search_notes` always posts `{"kind": "notes"}`; `search_cards` always posts `{"kind": "cards"}`.
- `update_note` sends only keys explicitly received from its MCP tool and does not validate Anki fields/tags locally.

- [ ] **Step 1: Write the failing service mapping tests**

```python
def test_update_note_passes_string_id_and_exact_payload(fake_client):
    service = AnkiMcpV2Service(fake_client)

    result = service.update_note(
        "1791823645036",
        fields={"Back": "<pre><code>MCP_V2_PATCH_OK_20261013</code></pre>"},
        add_tags=["anki_gpt_v2_mcp_written"],
        remove_tags=None,
    )

    assert result["note_id"] == "1791823645036"
    assert fake_client.calls == [
        (
            "PATCH",
            "/v2/notes/1791823645036",
            {"fields": {"Back": "<pre><code>MCP_V2_PATCH_OK_20261013</code></pre>"}, "add_tags": ["anki_gpt_v2_mcp_written"]},
        )
    ]


def test_search_cards_maps_only_to_api_v2_cards_kind(fake_client):
    AnkiMcpV2Service(fake_client).search_cards("tag:anki_gpt_v2_e2e")
    assert fake_client.calls[-1] == (
        "POST", "/v2/search", {"query": "tag:anki_gpt_v2_e2e", "kind": "cards", "limit": 50, "offset": 0}
    )
```

Include tests asserting no service method calls `/v2/sync`, references `8767`, parses IDs to integers, or accesses a filesystem/collection interface.

- [ ] **Step 2: Run service tests to verify RED**

Run: `services/anki-mcp/.venv/bin/python -m pytest services/anki-mcp-v2/tests/test_service.py -q`

Expected: FAIL because `AnkiMcpV2Service` does not exist.

- [ ] **Step 3: Implement the minimal mapping service**

```python
class AnkiMcpV2Service:
    def search_notes(self, query: str, limit: int = 50, offset: int = 0) -> dict[str, object]:
        return self._client.post_json(
            "/v2/search", {"query": query, "kind": "notes", "limit": limit, "offset": offset}
        )
```

Make every other method a direct route/body translation. Add only generic MCP transport limits for media response size and conversion to image content; let API v2 decide all domain validation.

- [ ] **Step 4: Run service tests to verify GREEN**

Run: `services/anki-mcp/.venv/bin/python -m pytest services/anki-mcp-v2/tests/test_service.py -q`

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

```bash
git add services/anki-mcp-v2
git commit -m "feat: add Anki MCP v2 tool mappings"
```

### Task 3: Streamable HTTP MCP server and protocol tests

**Files:**
- Create: `services/anki-mcp-v2/anki_mcp_v2/server.py`
- Create: `services/anki-mcp-v2/anki_mcp_v2/__main__.py`
- Create: `services/anki-mcp-v2/tests/test_protocol.py`
- Modify: `services/anki-mcp-v2/anki_mcp_v2/service.py`

**Interfaces:**
- Consumes `AnkiMcpV2Service` from Task 2.
- Produces an MCP server with exactly eight named tools and a `main()` that runs `transport="streamable-http"` with host `127.0.0.1`, port `8771` by default.
- Tool errors are MCP error results containing `McpApiError.as_payload()`; tool code does not expose Python tracebacks.

- [ ] **Step 1: Write failing protocol/schema tests**

```python
async def test_mcp_exposes_only_approved_tool_schemas():
    async with Client(server_module.mcp) as client:
        tools = await client.list_tools()

    assert {tool.name for tool in tools.tools} == {
        "anki_health", "anki_list_decks", "anki_search_notes", "anki_search_cards",
        "anki_get_note", "anki_get_card", "anki_update_note", "anki_get_media",
    }
    note_tool = next(tool for tool in tools.tools if tool.name == "anki_get_note")
    assert note_tool.inputSchema["properties"]["note_id"]["type"] == "string"
```

Add a Streamable HTTP integration test using `mcp.client.streamable_http.streamable_http_client` against a process/server on a free loopback port. Assert initialization, tool listing, a health call, error content for API 503, and absence of `anki_sync`.

- [ ] **Step 2: Run protocol tests to verify RED**

Run: `services/anki-mcp/.venv/bin/python -m pytest services/anki-mcp-v2/tests/test_protocol.py -q`

Expected: FAIL because no MCP server exists.

- [ ] **Step 3: Implement tools and localhost-only startup**

```python
@mcp.tool()
def anki_get_note(note_id: str) -> dict[str, object]:
    """Fetch one Anki note by its string note ID through API v2."""
    return get_service().get_note(note_id)


def main() -> None:
    mcp.run(transport="streamable-http", host="127.0.0.1", port=_port_from_env())
```

Use only the approved tools. Construct service state from `ANKI_API_TOKEN`; reject missing token or non-loopback/non-8770 API URL. Return actual MCP `ImageContent` for image media after API retrieval; return a sanitized MCP error for non-image media.

- [ ] **Step 4: Run protocol tests to verify GREEN**

Run: `services/anki-mcp/.venv/bin/python -m pytest services/anki-mcp-v2/tests/test_protocol.py -q`

Expected: PASS.

- [ ] **Step 5: Commit Task 3**

```bash
git add services/anki-mcp-v2
git commit -m "feat: serve Anki MCP v2 over Streamable HTTP"
```

### Task 4: Local deployment artifacts and documentation

**Files:**
- Create: `services/anki-mcp-v2/deploy/anki-vnext-mcp.service`
- Create: `services/anki-mcp-v2/deploy/deploy.sh`
- Create: `services/anki-mcp-v2/tests/test_deploy_contract.py`
- Create: `services/anki-mcp-v2/README.md`

**Interfaces:**
- Consumes module entry point from Task 3.
- Produces a systemd unit running as `ubuntu`, bound only to loopback and importing `/home/ubuntu/anki-vnext/api/api.env` without copying its token.
- Produces an idempotent deploy script limited to `/home/ubuntu/anki-vnext/mcp/` and `anki-vnext-mcp.service`.

- [ ] **Step 1: Write failing deployment contract tests**

```python
def test_systemd_unit_is_localhost_only_and_reuses_api_env():
    unit = UNIT_PATH.read_text()

    assert "EnvironmentFile=/home/ubuntu/anki-vnext/api/api.env" in unit
    assert "ExecStart=/home/ubuntu/anki-vnext/mcp/.venv/bin/python -m anki_mcp_v2" in unit
    assert "NoNewPrivileges=true" in unit
    assert "127.0.0.1" in unit
    assert "8767" not in unit


def test_deploy_script_never_touches_legacy_nginx_or_dns():
    script = DEPLOY_PATH.read_text()
    for forbidden in ("8767", "nginx", "certbot", "dns", "collection.anki2"):
        assert forbidden not in script.lower()
```

- [ ] **Step 2: Run deployment tests to verify RED**

Run: `services/anki-mcp/.venv/bin/python -m pytest services/anki-mcp-v2/tests/test_deploy_contract.py -q`

Expected: FAIL because deployment files do not exist.

- [ ] **Step 3: Implement unit, deploy script, and README**

```ini
[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/anki-vnext/mcp/src
EnvironmentFile=/home/ubuntu/anki-vnext/api/api.env
Environment=ANKI_MCP_V2_HOST=127.0.0.1
Environment=ANKI_MCP_V2_PORT=8771
ExecStart=/home/ubuntu/anki-vnext/mcp/.venv/bin/python -m anki_mcp_v2
NoNewPrivileges=true
PrivateTmp=true
```

The deploy script runs the focused test suite, rsyncs only package/deploy/requirements/README, installs the unit, restarts it, verifies MCP/API-v2/sync service state, and invokes a localhost Streamable HTTP smoke script without logging any token. Legacy process verification remains a separate read-only operational check in Task 6, so the deploy artifact has no dependency on legacy port details.

- [ ] **Step 4: Run deployment tests to verify GREEN**

Run: `services/anki-mcp/.venv/bin/python -m pytest services/anki-mcp-v2/tests/test_deploy_contract.py -q`

Expected: PASS.

- [ ] **Step 5: Commit Task 4**

```bash
git add services/anki-mcp-v2
git commit -m "feat: add isolated Anki MCP v2 deployment"
```

### Task 5: Full local test suite and code-quality verification

**Files:**
- Modify only as required by failing tests in `services/anki-mcp-v2/`.

**Interfaces:**
- Consumes all Tasks 1–4.
- Produces a passing, locally executable MCP v2 suite with no dependencies on the legacy MCP test modules.

- [ ] **Step 1: Run the complete MCP v2 suite**

Run: `services/anki-mcp/.venv/bin/python -m pytest services/anki-mcp-v2/tests -q`

Expected: PASS with zero failures.

- [ ] **Step 2: Run static boundary checks**

Run:

```bash
python3 -m compileall -q services/anki-mcp-v2/anki_mcp_v2
python3 - <<'PY'
from pathlib import Path

root = Path("services/anki-mcp-v2/anki_mcp_v2")
forbidden = ("8767", "sqlite", "collection.anki2", "from anki", "import anki", "/v2/sync")
matches = [
    (path, needle)
    for path in root.rglob("*.py")
    for needle in forbidden
    if needle in path.read_text(encoding="utf-8").lower()
]
assert not matches, matches
PY
```

Expected: exit 0 and no forbidden production dependency.

- [ ] **Step 3: Commit any final local-test correction**

```bash
git add services/anki-mcp-v2
git commit -m "test: verify Anki MCP v2 boundaries"
```

Only create this commit if Task 5 requires a code or test correction.

### Task 6: VPS localhost deployment and read-only integration

**Files:**
- Modify: only deployment files if real deployment exposes a defect, with a regression test first.

**Interfaces:**
- Consumes the deploy script and systemd unit from Task 4.
- Produces a running `anki-vnext-mcp.service` on `127.0.0.1:8771` and successful real read-only MCP calls to API v2.

- [ ] **Step 1: Run deployment script and verify service isolation**

Run: `services/anki-mcp-v2/deploy/deploy.sh`

Expected: tests pass; VPS path is `/home/ubuntu/anki-vnext/mcp/`; `anki-vnext-mcp.service` active; listener is exactly `127.0.0.1:8771`; API v2/sync/legacy remain active.

- [ ] **Step 2: Run read-only MCP integration through localhost Streamable HTTP**

Run a temporary client script through SSH that performs, in order:

```python
await client.call_tool("anki_health", {})
await client.call_tool("anki_list_decks", {"limit": 5, "offset": 0})
await client.call_tool("anki_search_notes", {"query": "ANKI_GPT_V2_E2E_TEST_20261012"})
await client.call_tool("anki_get_note", {"note_id": "1791823645036"})
await client.call_tool("anki_get_card", {"card_id": "1791823645037"})
```

Expected: responses come only through MCP v2, test-note IDs match, baseline Back is exactly `<pre><code>API_V2_PATCH_OK_20261012</code></pre>`, and baseline tags contain the two existing expected tags.

- [ ] **Step 3: Commit a regression fix if deployment/read-only checks expose one**

Write a failing local test first, fix only the v2 MCP service, rerun the suite, and commit with a focused message. If no defect exists, make no commit.

### Task 7: One authorized MCP write and independent sync confirmation

**Files:**
- Create only temporary scripts/collections outside the repository or in the MCP plan workspace; remove them before final reporting.

**Interfaces:**
- Consumes the deployed localhost MCP from Task 6.
- Produces exactly one API v2 write initiated by the `anki_update_note` MCP tool and an independent official-sync full download verification.

- [ ] **Step 1: Re-check write preconditions through MCP**

Use the new Streamable HTTP client only. Confirm API/sync/MCP health, note ID `1791823645036`, card ID `1791823645037`, unchanged Front, exact baseline Back, and current tags.

Expected: all baseline values match the approved write target. If any value differs, stop without writing and report the mismatch.

- [ ] **Step 2: Perform exactly one MCP tool write**

```python
await client.call_tool(
    "anki_update_note",
    {
        "note_id": "1791823645036",
        "fields": {"Back": "<pre><code>MCP_V2_PATCH_OK_20261013</code></pre>"},
        "add_tags": ["anki_gpt_v2_mcp_written"],
    },
)
```

Expected: API v2 reports confirmed sync-after success. Do not call this tool again, do not modify Front, do not remove any tag, and do not revert the note.

- [ ] **Step 3: Re-read via MCP and validate service state**

Use `anki_get_note` and `anki_health` through the same local MCP endpoint.

Expected: Back equals the approved new HTML, tags include `anki_gpt_v2_e2e`, `anki_gpt_v2_api_written`, and `anki_gpt_v2_mcp_written`; card ID remains `1791823645037`; API v2 sync state is healthy.

- [ ] **Step 4: Independently full-download temporary collection and destroy it**

Create a temporary Anki collection outside the production service path, set it to the official sync server, force only a `FULL_DOWNLOAD`, reopen it, and inspect note/card state with the official Anki library. Assert exact Back, required tags, and card ID. Close and delete the temporary collection and media directory. Never call full upload.

Expected: independent collection matches MCP/API readback and no temporary data remains.

- [ ] **Step 5: Final operational checks and commit integration harness only if retained**

Check `anki-vnext-mcp.service`, `anki-vnext-api.service`, `anki-vnext-sync.service`, and the legacy `:8767` process. Inspect logs with secrets redacted. Commit only intentional retained test/deployment improvements; never commit temporary integration artifacts or secrets.
