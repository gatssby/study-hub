# Federal Online corpus rebuild

This is an operator-controlled, receipt-backed migration, **not** an unattended
production job. Local synthetic tests never contact OneDrive. No automatic
service stop/start is performed. Rehearse on a disposable state copy first.

## Prerequisites and integration boundary

Run from the repository root with `PYTHONPATH=federal-online:ops/study-hub`.
Production Python is `/home/ubuntu/study-hub-venv/bin/python`; it must have the
existing FO dependencies installed, including the PDF identity dependency.
`rclone` must already be authenticated. Allowed remote namespaces are exactly
`onedrive:Federal Online`, `onedrive:Federal Online PDFs` (including its
`_quarantine` child), and `onedrive:Study Hub/federal-online`.
No purge/directory-delete command is implemented.

The default builder lazily calls:

* `fo_hub.ingest.ingest(generation_dir, generation_dir / 'hub.sqlite3', index_pdfs=False)`
* `fo_hub.pdf_index.build(generation_dir, plan)`

The latter is an integration contract: the PDF builder must use absolute local
original paths and content hashes in `plan['actions']`, register provenance, and
populate `materials`/PDF pages in that database. It must not mutate active state.
Validate that interface against the concurrent PDF-index implementation before
production use. The orchestrator accepts injected builder, identity, Rclone,
unit-state checker and catalog runner for local rehearsals.

## Commands

Set an explicit generation and keep it fixed throughout the migration:

```sh
export PYTHONPATH=federal-online:ops/study-hub
PY=/home/ubuntu/study-hub-venv/bin/python
SCRIPT=ops/study-hub/rebuild_fo_corpus.py
STATE=/home/ubuntu/study-hub-state/federal-online
G=g202610280001
$PY "$SCRIPT" plan --state-root "$STATE" --generation "$G"
$PY "$SCRIPT" plan --state-root "$STATE" --generation "$G" --execute
$PY "$SCRIPT" stage --state-root "$STATE" --generation "$G"
$PY "$SCRIPT" stage --state-root "$STATE" --generation "$G" --execute \
  --rate-limit-s 0.5 --max-transfer-bytes 3221225472
$PY "$SCRIPT" resume --state-root "$STATE" --generation "$G"
$PY "$SCRIPT" resume --state-root "$STATE" --generation "$G" --execute
$PY "$SCRIPT" verify --state-root "$STATE" --generation "$G"
$PY "$SCRIPT" verify --state-root "$STATE" --generation "$G" --execute
$PY "$SCRIPT" status --state-root "$STATE" --generation "$G"
$PY "$SCRIPT" cutover --state-root "$STATE" --generation "$G"
$PY "$SCRIPT" cutover --state-root "$STATE" --generation "$G" --execute
$PY "$SCRIPT" cleanup --state-root "$STATE" --generation "$G"
$PY "$SCRIPT" cleanup --state-root "$STATE" --generation "$G" --execute
```

Without `--execute`, only generation-local planning/journal/lock files may be
written. `plan` and `status` still perform read-only remote inventory requests;
plan hashes PDFs locally and caches path/size/mtime-bound identities. Never
regenerate a plan once execution has begun: receipts bind its checksum.

Stop the five `study-hub-fo-{catalog,materials,videos,index,transcription}` units
before executing stage/cutover/cleanup. These operations refuse active units or
an indeterminate systemctl result. The operator must also quiesce API database
readers/writers before cutover and restart the API afterwards; the script does
not enforce API quiescence. SQLite WAL checkpointing is not a substitute for
preventing concurrent writes. Do not cut over a live API.

Stage verifies byte identity with size plus pure-Python QuickXorHash, records
checksum-bound per-file receipts, and does not overwrite changed originals.
Resume re-lists remote objects and skips only valid, still-matching receipts.
`--limit` bounds new actions; `--max-transfer-bytes` bounds upload bytes per run.
`--refresh-catalog` explicitly opts in to the portal catalog command against
the isolated generation directory. Remote PDFs with no local exemplar are
inventoried, not automatically downloaded or indexed.

Verify checks registered original coverage, material/content collisions,
explicit lost lesson IDs, queued-source coverage, and read-only plugin queries.
It writes `verify.json`; divergence yields a nonzero CLI exit. The PDF smoke
check samples up to three materials. Verification binds the plan and database
bytes. It does not prove extraction quality beyond the plugin's own privacy gate.

Cutover checkpoints WAL, renames the old DB to `previous-hub.sqlite3`, then
renames the staged DB into place. A durable intent supports rerunning after
an interrupted rename. Keep all services quiesced until recovery finishes.
If cutover reports ambiguity, preserve all files and investigate; do not
manually overwrite either database. Success is recorded in
`rebuild/active-generation.json`.

## Rollback

While services/API remain quiesced:

```sh
$PY "$SCRIPT" cutover --state-root "$STATE" --generation "$G" --rollback
$PY "$SCRIPT" cutover --state-root "$STATE" --generation "$G" --rollback --execute
```

The previous DB is restored, and the replaced DB is retained as
`rolled-forward-hub.sqlite3`. Restart services only after checking the active
DB and plugin endpoints. Rollback does not remove remote originals.

## Cleanup and conservative retention

Cleanup requires the active-generation marker. Local PDFs are deleted only with
a checksum-valid drop receipt, fresh matching remote size/QuickXor, unchanged
local SHA-256, and safe non-symlink path. `protect_unique` entries are retained
even after upload; a later reviewed generation can establish remote reuse.
`protected.json` lists pending/protected originals.

Scratch cleanup is limited to old, unlocked `tmp/videos`, `playwright-*`, and
`preparation-tests-*` trees. Lock-file presence conservatively prevents deletion.
Old generations containing PDF/DB files, symlinks or lock files are retained to
avoid destroying a sole exemplar; other old generations are removed except
active/previous. Logs larger than 50 MiB are copied to `.retired` and truncated;
only one retired copy per log is retained. This needs temporary free space.

Previous DB deletion is opt-in and defaults to seven-day retention:

```sh
$PY "$SCRIPT" cleanup --state-root "$STATE" --generation "$G" --execute --drop-previous-db
# Explicit emergency override, after independent backup:
$PY "$SCRIPT" cleanup --state-root "$STATE" --generation "$G" --execute \
  --drop-previous-db --force-drop-previous
```

Video deduplication is **off by default**. `cleanup --execute --dedupe-videos`
downloads both candidate and keeper into state/tmp, requires equal SHA-256,
rechecks both remote metadata, and deletes only the candidate object. It reserves
2 GiB plus both object sizes. This is potentially expensive; reconcile source
aliases before enabling it. Duplicate remote paths are not automatically
rewritten in the database, so do not enable this if lessons reference candidates.

## Local verification

```sh
PYTHONPATH=federal-online:ops/study-hub \
  services/anki-mcp-v2/.venv/bin/python -m pytest federal-online/tests -q
```

The synthetic suite covers guarded paths, lock exclusion, checksummed receipts,
dry runs, uploads/resume/corruption, remote changes, protected cleanup, lost
lessons/material-ID collision, cutover interruption/idempotence/rollback,
plan mismatch, active-unit refusal and conservative generation retention.
