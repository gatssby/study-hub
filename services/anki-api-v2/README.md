# Anki GPT API v2

HTTP API that reads and writes the VPS Service Collection through the official
`anki==26.9.3` library, and keeps it in sync with the self-hosted Anki Sync Server.

Status: implemented and tested locally. Deployed to the VPS on loopback only
(`127.0.0.1:8770`). Not exposed publicly. No DNS or nginx.

## Architecture

```
ChatGPT / future plugin (not built yet)
        |
Anki GPT API v2   (127.0.0.1:8770, one uvicorn worker)
        |  single owner thread
Service Collection  /home/ubuntu/anki-vnext/service/collection.anki2
        |  official sync protocol, localhost
Anki Sync Server    (127.0.0.1:27701) -> https://anki.gatssby.com.br/ -> Mac / iPhone
```

The API does not use AnkiConnect, the GUI, direct SQL, the legacy JSON indexes, or the
legacy snapshots. Every data access goes through the public `anki` API (`get_note`,
`update_note`, `find_notes`, `note.usn`, `sync_collection`). Test code alone uses SQL
(`col.db`) to simulate the server accepting a change.

## Ownership and locking (decision)

Chosen: one dedicated thread owns the `Collection` (`anki_api_v2/actor.py`).

- Every collection operation is a job executed on that thread, FIFO. No Collection
  object is shared across threads, and there is no per-request open/close.
- Cross-process: an exclusive `flock` on `service/collection.lock`, the same file
  `service_sync.py` already uses. A second owner fails fast, so the legacy script
  cannot open the collection while the API runs.
- Queue wait is bounded (`ANKI_API_QUEUE_TIMEOUT_SECONDS`, default 5 s). A job that
  does not start in time is cancelled and returns 503 `collection_busy`. A started job
  always runs to completion, so a write is never reported busy while it might still apply.
- Why not open/close per request: each open costs latency, and it would still need the
  same lock to stop two processes writing. The actor gives the same safety with less
  overhead.
- The unit runs `workers=1`. Multiple workers would mean multiple processes owning the file.

## Sync strategy

Collection sync (`anki_api_v2/sync.py`):

- Reads: sync only when the last successful sync is older than
  `ANKI_API_FRESHNESS_TTL_SECONDS` (default 30 s), or when a write is pending. Media is never synced by reads.
- Writes: sync-before, validate, apply, check the card set, sync-after, confirm.
  A write returns success only after the sync-after has been accepted and the note's
  `usn` shows the server took it.
- Full sync: never chosen. `FULL_SYNC`, `FULL_DOWNLOAD` or `FULL_UPLOAD` returns 409
  `full_sync_required` and changes nothing.
- Media sync: separate. `POST /v2/sync` with `{"media": true}` starts it (202). Health
  reports its state. It is never triggered by reads or writes.

Measured behaviour that shapes the write path (anki 26.09.3 + official sync server):

- Anki detects changes at one-second resolution. A change in the same second as the
  previous sync is not uploaded, yet the sync still returns `NO_CHANGES`. Measured:
  back-to-back writes lost data in 4 of 6 runs. The API waits for the next second before writing.
- `NO_CHANGES` is not proof of delivery. The API checks each changed note's `usn`
  (`-1` = not yet taken by the server). If it is still `-1` after sync-after, the write
  returns 502 `sync_failed` with `reason: change_not_detected`, and health reports `pending`.
- A pending change is retried by the next write or sync, and is cleared only when the
  note's `usn` shows it was taken. A `NO_CHANGES` sync does not clear it.

## Endpoints (all under `/v2`, bearer token required)

| Method | Path | Purpose |
|---|---|---|
| GET | /health | status, versions, counts, sync and media state. No secrets, no sync. |
| POST | /sync | explicit collection sync; body `{"media": true}` starts media sync (202) |
| GET | /decks | list decks; `root`, `limit` (1-200), `offset` |
| GET | /notes/{note_id} | fields, tags, note type, card ids, deck ids |
| GET | /cards/{card_id} | note, deck, template, rendered question and answer |
| POST | /search | `{"query", "kind": "notes"|"cards", "limit" (1-100), "offset"}`, native Anki syntax |
| PATCH | /notes/{note_id} | `{"fields", "add_tags", "remove_tags"}`. Empty payload, unknown field, card-set change and note-type change are rejected |
| GET | /media/{filename} | serves a plain file from `collection.media`, `nosniff`, CSP `default-src 'none'` |

IDs are strings in JSON. Internally they are converted to `int` for the library.

Error body: `{"error": {"code", "message", "details"?}}`. Codes:
`unauthorized`, `invalid_request`, `invalid_id`, `note_not_found`, `card_not_found`,
`invalid_search`, `invalid_field`, `payload_too_large`, `card_set_change_blocked`,
`invalid_media_path`, `media_not_found`, `full_sync_required`, `sync_failed`,
`collection_busy`, `internal_error`. Tracebacks are logged on the server only.

Interactive docs: `/docs` and `/openapi.json` are available on the loopback port.

## Configuration

Environment variables (see `deploy/deploy.sh` for the VPS file, `api.env`, mode 600):

- `ANKI_API_TOKEN`: at least 32 chars, generated on the VPS, never committed.
- `ANKI_API_COLLECTION_PATH`: path to `collection.anki2`. Refused if the file is missing,
  so a typo can never create an empty collection.
- `ANKI_API_SYNC_CREDENTIALS_FILE`: existing `syncserver.env`, read in place, never copied.
- `ANKI_API_SYNC_ENDPOINT`: must be a loopback host.
- `ANKI_API_HOST` (loopback only), `ANKI_API_PORT` (default 8770).
- `ANKI_API_FRESHNESS_TTL_SECONDS`, `ANKI_API_QUEUE_TIMEOUT_SECONDS`, `ANKI_API_LOG_LEVEL`.

Logs contain method, path, status and duration. Query strings, card content and
secrets are never logged.

## Tests

```
cd services/anki-api-v2
.venv/bin/python -m pytest -q                 # 89 tests, includes 3 e2e
.venv/bin/python -m pytest -q -m "not e2e"    # no sync server needed
```

- `tests/test_e2e_sync.py` starts the real `python -m anki.syncserver` on a free port
  with synthetic temporary collections, and checks the official protocol end to end.
- The collection is real. Only the network transport and the clock are faked
  (`tests/fakes.py`). Write tests never touch the production collection.
- Mutation testing: 18 deliberate faults (sync-before, pacing, usn confirmation, path
  traversal, symlinks, flock, auth, card-set guard, undo, limits, traceback leak, busy
  queue, ID types, TTL, full-sync refusal) were each caught by at least one test.

## Deploy

`deploy/deploy.sh` runs the local tests, backs up the previous release on the VPS,
uploads code (no data), creates the venv with `anki==26.9.3` pinned, creates `api.env`
if missing, installs `deploy/anki-vnext-api.service`, and checks `/v2/health`.

The collection is never copied from the Mac. The VPS collection is used in place.
Before the first start, a backup of `collection.anki2` was taken under
`/home/ubuntu/anki-vnext/backups/pre-api-v2-*`.

## Commands

```
systemctl status anki-vnext-api.service
journalctl -u anki-vnext-api.service -n 100 --no-pager
sudo systemctl restart anki-vnext-api.service
ss -lntp | grep -E ':(8767|8770|27701)\b'
```

Token for manual calls (do not print it in shared logs):
`ssh oracle-vps 'sed -n "s/^ANKI_API_TOKEN=//p" /home/ubuntu/anki-vnext/api/api.env'`

## Known limits and open items

- Not exposed publicly. Public DNS, nginx and TLS are a later step.
- Only the Service Collection is served. The Mac and iPhone sync through the
  public server, and the API sees their changes on the next sync.
- Every read can trigger a collection sync when the TTL has expired. Latency is
  bounded by the localhost sync, not by the network.
- Media is read-only through the API. No media upload.
- Writes are limited to fields and tags. Creating, deleting or changing the note type
  is not supported.
- Only one `anki_api_v2` process must own the collection. Stopping the API releases the lock.
- Pacing waits at most 2 s. If it gives up, the usn check still prevents a false success,
  but the write may need a retry.
