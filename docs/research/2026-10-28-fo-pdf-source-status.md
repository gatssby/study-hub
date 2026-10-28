# FO PDF source status — 2026-10-28

## Delivered locally; no deployment

The store now exposes cached, identity-bound `source_observation` in both material search and PDF text responses. The API already forwards these store dictionaries, so no endpoint or API handler changes were necessary.

- Preserve material IDs, expected SHA-256, cached pages, page citations and all existing privacy gates.
- `text_provenance=indexed_snapshot` means cached extraction, not text freshly extracted from the currently named file.
- `source=null` for every PDF text response. Search retains the `relative_path` key but returns null. Original paths and signed source URLs are never alternatives to privacy-approved text.
- `source_reason` explains why mutable aliases cannot identify historical bytes. `source_observation` supplies status, observed Unix UTC timestamp, expected/actual SHA, `meaning`, and `current_bytes_guaranteed=false`.
- `verified` means **verified_at_observation**, never that an alias still has those bytes. A later filesystem replacement does not alter the cached observation until explicit refresh.
- `historical_source_unavailable` means the observed alias mismatched the historical expected SHA; it does not prove that historical bytes are absent everywhere.
- Other statuses: `source_unavailable`, `not_observed`, `invalid_identity`, `invalid_path`. An unobserved selection can carry a refresh timestamp without asserting its bytes were read.

## Persistence and compatibility

Writable store initialization additively creates `pdf_source_observations`. Read-only legacy DBs without that table return `not_observed`, no timestamp, and no fabricated source. API readers never hash or inspect source files. Persistence checks material ID plus exact expected SHA inside a write transaction, validates state/hash consistency and feasible hashed-path counts, rejects older observations, and rolls back an entire inconsistent batch. A changed expected SHA cannot reuse an earlier proof.

No ingestion identity reassignment, transient-error filtering change, automatic corpus sweep or policy promotion is included. Existing blocked/OCR/privacy decisions remain in force. Byte verification is not academic correctness, formula fidelity, pixel sanitization, metadata sanitization or permission to distribute originals.

## Explicit bounded operator command

From `federal-online`, after separately authorized deployment and approved resource/publication planning:

```sh
/path/to/python -m fo_hub.pdf_integrity \
  --db /approved/state/hub.sqlite3 \
  --state-root /approved/state \
  --material-id APPROVED_MATERIAL_ID \
  --material-id ANOTHER_APPROVED_MATERIAL_ID \
  --max-paths 64 --refresh
```

This is documentation, not an executed production command. Select real IDs privately; do not paste source paths or signed URLs into reports.

The CLI requires explicit IDs and `--refresh`; default unique-path budget is 64, hard cap 512 paths and 512 distinct selected materials. Zero paths is allowed and records fail-closed unobserved statuses. It reads an existing DB read-only before observation (missing DB cannot be created), refuses unknown IDs, hashes a shared alias once using the existing helper, then persists only the selected identity-bound observations. Output is aggregate counts plus timestamp, no source paths/text. The command does not locate alternative archived originals, sanitize PDFs or download anything. Path-count limits are not byte/time limits: operators still need external CPU/memory/time controls and a conservative selected batch for large files. Coordinate observation with producers operationally; a cached observation never guarantees live aliases.

## Verification

Synthetic fixtures only. TDD failures observed for missing persistence, missing CLI, missing invalid-identity persistence and impossible hash counts; then implemented and reran. Regression coverage includes historical/new identities sharing an alias, preserved allowed cached text, HTTP responses after alias replacement, missing legacy table without hashing, stale expected SHA rejection, atomic batch rollback, invalid/missing paths, bounded/unknown/missing-DB CLI rejection, and zero-budget behavior.

Executed from repository root:

```sh
PYTHONPATH=federal-online services/anki-mcp-v2/.venv/bin/python -m pytest \
  federal-online/tests services/anki-mcp-v2/tests -q
```

Final result: **444 passed in 5.63s** in the shared worktree at verification time. `git diff --check` passed for owned implementation/test paths. An earlier suite run encountered a concurrently edited materials-publication test failure; the final complete rerun passed. No portal/runtime edits were made by this task. No VPS access, production observation, private corpus extraction, service restart or deployment occurred.
