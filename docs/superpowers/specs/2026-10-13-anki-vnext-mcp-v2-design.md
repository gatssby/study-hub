# Anki vNext MCP v2 Design

## Goal

Create an isolated, thin MCP v2 service that translates a small stable set of MCP tools into authenticated calls to the existing Anki GPT API v2. The service must let a local MCP client read and perform the one controlled note update through the API v2 without touching the legacy MCP, legacy API, service collection, sync protocol, SQLite, snapshots, or media filesystem.

## Approved scope

This design implements phases A–F through a localhost deployment only:

- create and test `services/anki-mcp-v2/`;
- deploy it independently to `/home/ubuntu/anki-vnext/mcp/`;
- bind it only to `127.0.0.1:8771` using Streamable HTTP;
- perform the specified read-only integration checks, one controlled write through the new MCP tool, and an independent full-download confirmation;
- preserve the legacy MCP and `127.0.0.1:8767` unchanged.

The following are explicitly deferred by the approval on October 13, 2026:

- public nginx route;
- DNS record creation;
- TLS certificate issuance;
- OAuth 2.1, mTLS, or any external MCP authentication configuration;
- ChatGPT custom-app configuration and end-to-end execution by the real ChatGPT client;
- any Plugin work.

## Existing system boundary

```text
Local MCP client
  -> Anki MCP v2, Streamable HTTP, 127.0.0.1:8771
  -> HTTP Bearer, http://127.0.0.1:8770/v2
  -> Anki GPT API v2
  -> Service Collection
  -> official Sync Server, 127.0.0.1:27701
  -> Mac and iPhone
```

`anki-vnext-api.service` remains the only process that owns the Service Collection. The MCP never imports `anki`, opens `collection.anki2`, accesses SQLite, reads `collection.media`, calls the sync server, or implements sync/card-set/path-safety/field-validation logic.

The legacy path remains separate and unchanged:

```text
Legacy local stdio MCP -> legacy public API -> 127.0.0.1:8767
```

## Isolation and deployment

Create a dedicated branch, `feat/anki-vnext-mcp-v2`, from the current API v2 branch state. Do not include pre-existing working-tree modifications or unrelated untracked files.

Create the new service:

```text
services/anki-mcp-v2/
  anki_mcp_v2/
    __init__.py
    client.py
    errors.py
    service.py
    server.py
    __main__.py
  deploy/
    anki-vnext-mcp.service
    deploy.sh
  tests/
  requirements.txt
  README.md
```

Deploy code only to `/home/ubuntu/anki-vnext/mcp/`. The unit is named `anki-vnext-mcp.service` and runs as `ubuntu`. It binds `127.0.0.1:8771`; no public listener is created.

The unit imports the existing API token directly via:

```ini
EnvironmentFile=/home/ubuntu/anki-vnext/api/api.env
```

It may additionally load a non-secret MCP configuration file from its own deployment directory. It does not copy, print, parse manually, or commit the API token. Service code reads `ANKI_API_TOKEN` from the environment and sends it only in `Authorization: Bearer <token>` requests to `http://127.0.0.1:8770`.

Production startup rejects an API base URL other than exactly `http://127.0.0.1:8770`, so the MCP cannot accidentally reach the legacy API or an external endpoint.

## MCP transport and tools

Use the installed MCP Python SDK's Streamable HTTP transport. The service has no Anki domain state and no local audit/snapshot/queue implementation.

Expose exactly these tools:

| Tool | API v2 mapping | Contract |
|---|---|---|
| `anki_health()` | `GET /v2/health` | Returns API health unchanged except for MCP transport metadata. |
| `anki_list_decks(root?, limit?, offset?)` | `GET /v2/decks` | Preserves API page fields and string deck IDs. |
| `anki_search_notes(query, limit?, offset?)` | `POST /v2/search` with `kind="notes"` | Uses native Anki query syntax through the API. |
| `anki_search_cards(query, limit?, offset?)` | `POST /v2/search` with `kind="cards"` | Uses native Anki query syntax through the API. |
| `anki_get_note(note_id: str)` | `GET /v2/notes/{note_id}` | Keeps note, card, and deck IDs as strings. |
| `anki_get_card(card_id: str)` | `GET /v2/cards/{card_id}` | Keeps card, note, and deck IDs as strings. |
| `anki_update_note(note_id: str, fields?, add_tags?, remove_tags?)` | `PATCH /v2/notes/{note_id}` | Passes the body through without duplicating API v2 validation or sync behavior. |
| `anki_get_media(filename: str)` | `GET /v2/media/{filename}` | Returns MCP image content for image media; non-image media returns a sanitized unsupported-media error rather than a direct API URL. |

There is intentionally no `anki_sync` tool. Reads and writes already use the API v2 sync policy, and the MCP must not own or trigger implicit media synchronization. An API v2 explicit sync endpoint is not needed for the approved local GPT/MCP capability set.

All public MCP ID parameters are `str`. The MCP does not coerce them to integers; the API v2 is responsible for its own ID validation and conversion.

## HTTP client and errors

Implement a focused HTTP client using only HTTP/JSON translation:

- base URL: exactly `http://127.0.0.1:8770` in production;
- Authorization header: `Bearer <ANKI_API_TOKEN>`;
- reads use a finite short timeout (10 seconds);
- updates use a finite write timeout (45 seconds) to allow the API's pacing and sync-before/sync-after flow;
- media uses a bounded response size and follows only its API route;
- no calls to port 8767, port 27701, SQLite, collection files, snapshot files, or legacy endpoints.

For a structured API error body, MCP returns a sanitized structured error result:

```json
{
  "error": {
    "code": "full_sync_required",
    "status": 409,
    "message": "safe API message",
    "details": {}
  }
}
```

The adapter preserves API codes and safe API details. It maps transport failures to stable MCP-local codes:

| Condition | MCP error code |
|---|---|
| HTTP 401 | `unauthorized` |
| HTTP 404 | API-provided `note_not_found`, `card_not_found`, `media_not_found`, or `not_found` |
| HTTP 409 with full-sync response | `full_sync_required` |
| HTTP 422 | API-provided validation code, normally `invalid_request` or `invalid_field` |
| HTTP 502 with sync response | `sync_failed` |
| HTTP 503 | `collection_busy` |
| client timeout | `anki_api_timeout` |
| connection/DNS failure | `anki_api_unavailable` |
| malformed/unexpected API response | `anki_api_protocol_error` |

No exception stack trace, token, request authorization header, filesystem path, or raw internal error body is returned to the MCP caller.

## Testing

Tests are written before implementation and use a local fake API for unit/protocol coverage. They must prove:

- MCP tool discovery and exact tool schemas;
- IDs remain strings in input, paths, payloads, and responses;
- route, query, method, JSON body, and `Authorization: Bearer` mapping;
- update payload passthrough for fields and incremental tag changes;
- structured mappings for timeout, 401, 404, 409 `full_sync_required`, 422, 502 `sync_failed`, and 503 `collection_busy`;
- no HTTP target can use port 8767;
- no production import or runtime access to `anki`, SQLite, collection paths, snapshot/JSON legacy data, or sync-server endpoints;
- Streamable HTTP MCP initialization/tool call locally.

Integration checks run only after the localhost unit is deployed and use the real VPS API v2:

1. health;
2. list decks;
3. search the provided test note by `ANKI_GPT_V2_E2E_TEST_20261012`;
4. get note `1791823645036`;
5. get card `1791823645037`.

Exactly one controlled write is then made through `anki_update_note`, and only after baseline confirmation through the same MCP:

```text
note_id: 1791823645036
card_id: 1791823645037
Front: unchanged
Back before: <pre><code>API_V2_PATCH_OK_20261012</code></pre>
Back after:  <pre><code>MCP_V2_PATCH_OK_20261013</code></pre>
add_tags: ["anki_gpt_v2_mcp_written"]
```

After that one update, re-read the note and API health via the MCP. Create an independent temporary Anki collection, perform only a full download from the official sync server, verify the expected Back, tags, and card ID, then remove the temporary collection. Never full upload. No subsequent writes occur.

## Local deployment acceptance criteria

The deploy script must:

1. run the MCP unit tests first;
2. upload only MCP v2 source, requirements, and the systemd unit to `/home/ubuntu/anki-vnext/mcp/`;
3. create an isolated virtual environment;
4. install the pinned MCP dependency set;
5. install/restart `anki-vnext-mcp.service`;
6. verify the process listens only on `127.0.0.1:8771`;
7. perform an MCP Streamable HTTP handshake/tool listing and a health call through localhost;
8. verify `anki-vnext-api.service` and `anki-vnext-sync.service` remain active;
9. verify the legacy process on `127.0.0.1:8767` remains running;
10. inspect MCP and API logs without exposing secrets.

## Deferred public exposure

No nginx site, DNS change, certificate, public URL, OAuth configuration, mTLS configuration, or ChatGPT configuration is created in this implementation cycle.

When explicitly resumed, the intended isolated external route is:

```text
https://anki-mcp-v2.gatssby.com.br/mcp
```

The intended DNS record is:

```text
A  anki-mcp-v2.gatssby.com.br  137.131.191.66
```

The external phase must be designed separately around a user-approved OAuth 2.1 identity provider and compatible ChatGPT connection configuration. It must not expose `:8770`, alter `anki.gatssby.com.br`, alter the legacy nip.io endpoint, or remove legacy MCP tools.

## Non-goals

- Plugin implementation;
- legacy MCP/API removal, modification, shutdown, migration, or endpoint replacement;
- cronograma/FO changes;
- direct collection or sync-server access from MCP;
- automatic sync/media sync behavior in MCP;
- public endpoint exposure in this cycle.
