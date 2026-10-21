# Anki MCP v2

Local-only Streamable HTTP MCP adapter for Anki GPT API v2.

```text
MCP client -> http://127.0.0.1:8771/mcp -> http://127.0.0.1:8770/v2 -> API v2
```

The service is intentionally thin. It never imports Anki, opens the collection, reads SQLite/media/snapshots, invokes the sync server, calls the legacy API, or exposes an MCP sync tool.

## Tools

- `anki_health`
- `anki_list_decks`
- `anki_search_notes`
- `anki_search_cards`
- `anki_get_note`
- `anki_get_card`
- `anki_update_note`
- `anki_get_media` (returns a real MCP `ImageContent`: png, jpeg, webp, gif, max 8 MiB, bytes
  verified against the MIME; svg/audio/other -> `unsupported_media_type`)
- `anki_list_note_types`, `anki_get_note_type` (read-only)
- `anki_create_note`
- `anki_delete_notes` (max 10; needs note_id + expected_card_ids + expected_revision)
- `anki_list_tags`, `anki_rename_tag`, `anki_delete_tag` (removes the tag only; `dry_run` first)
- `anki_create_deck`, `anki_rename_deck`, `anki_delete_deck` (empty decks only)
- `anki_move_cards` (max 200)

`anki_get_note` returns `revision` and a structured `media` list; the model calls
`anki_get_media` only for the images it needs. Tools carry read-only/destructive annotations.

All note/card/deck IDs remain strings.

### Optional Study Hub tools

With `STUDY_HUB_FO_TOOLS=true` at MCP startup, the same `/mcp` endpoint also
advertises seven read-only FO tools, preserving all 19 Anki tools:

- `fo_list_lessons`, `fo_get_lesson`
- `fo_search_materials`, `fo_get_pdf_text`
- `fo_search_transcripts`, `fo_get_transcript`
- `fo_get_sync_status`

The combined toolset contains 26 tools (nine write, 17 read). FO calls use the
separate loopback FO API; they do not modify the Anki collection, trigger sync,
download/index materials, or start ASR. PDF exposure remains governed by the FO
API's privacy guards. Existing transcripts may be unavailable while ASR is disabled.

## Local development

```bash
python3.13 -m venv services/anki-mcp-v2/.venv
services/anki-mcp-v2/.venv/bin/pip install -r services/anki-mcp-v2/requirements-dev.txt
services/anki-mcp-v2/.venv/bin/python -m pytest services/anki-mcp-v2/tests -q
```

Runtime requires `ANKI_API_TOKEN`. Production starts only with API v2 at `http://127.0.0.1:8770`; it binds Streamable HTTP to `127.0.0.1:8771/mcp`.

## Deploy

```bash
services/anki-mcp-v2/deploy/deploy.sh
```

Deployment is restricted to `/home/ubuntu/anki-vnext/mcp/` and `anki-vnext-mcp.service`. It loads the existing API token through the API service environment file without copying or logging it.

## Private ChatGPT Plugin tunnel

`deploy/deploy_tunnel.sh` installs the current official Linux ARM64 OpenAI
`tunnel-client` release only after checking `SHA256SUMS.txt`, initializes the
`anki-vnext` profile against `http://127.0.0.1:8771/mcp`, runs its doctor, and
installs `anki-vnext-mcp-tunnel.service`.

The VPS-only `/etc/anki-vnext-mcp-tunnel.env` must already be `root:root` mode
`0600` and contain the control-plane credential plus tunnel ID. Neither secret
is stored in the repository, printed, or passed as a CLI argument. The tunnel
is outbound-only; it never exposes API v2 or MCP v2 publicly.

No public endpoint, nginx configuration, DNS, OAuth, mTLS, or packaged Plugin
implementation is included. The private ChatGPT connection is managed in ChatGPT,
separately from this service's deployment.

### Refresh the installed custom Plugin after tool changes

MCP `tools/list` and the tool metadata stored in a ChatGPT custom connection are
different checkpoints. A healthy `anki_health` does not prove that ChatGPT has
rescanned newly registered `fo_*` tools. Changing an OpenAPI file or restarting a
healthy tunnel is not the remedy for stale ChatGPT tool discovery.

1. Verify the actual MCP endpoint with `STUDY_HUB_FO_TOOLS=true .venv/bin/python
   deploy/smoke.py` from the deployed MCP directory. It must accept exactly the
   combined toolset and pass both read-only health/status calls.
2. Inspect the live tunnel's loopback `/api/status` (normally port 8080), selecting
   only `mcp_server_url`, the `main` channel address, and tunnel identity. Confirm
   that this is the endpoint just tested. Do not print credentials or raw profiles.
   `/readyz` checks readiness; `/health/mcp` can report `not_observed` for HTTP
   transport and is not evidence that the server exposes zero tools.
3. In ChatGPT desktop: Settings -> Plugins -> Anki GPT vNext -> Refresh tools.
   The same custom-connection refresh is available through ChatGPT Plugins.
   Preserve the installed app, tunnel and authentication; do not uninstall or
   recreate a working connection just to rediscover tools.
4. Read back View details -> Apps -> Anki GPT vNext. Confirm **26 tools (9 write,
   17 read)**, rather than the old **19 tools (9 write, 10 read)**.
5. Start a new conversation, select `@Anki GPT vNext`, and request
   `fo_get_sync_status`, then `fo_list_lessons` with `limit=1`. These are read-only;
   do not test integration with an Anki write or by starting transcription.

The installed connection inspected on 2026-10-21 was a private development app:
Refresh tools was sufficient, with no reconnection or server restart. A managed
workspace may instead require an administrator's action refresh/approval; follow
the actual workspace UI rather than treating it as this private app.

Official references (checked 2026-10-21):

- https://developers.openai.com/plugins/deploy/connect-chatgpt
- https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt
