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
- `anki_get_media` (image media only)

All note/card/deck IDs remain strings.

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

No public endpoint, nginx configuration, DNS, OAuth, mTLS, ChatGPT configuration, or Plugin implementation is included.
