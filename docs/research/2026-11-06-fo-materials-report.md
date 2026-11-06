# FO materials — read-only diagnosis and transitional wrapper

Observation: 2026-11-06 22:53–22:58 UTC. No deployment, commit, service changes,
production database writes, generation rebuild, corpus deletion or backup deletion.
No PDF text/PII or remote object names are included in evidence.

## Findings

- `study-hub-fo-materials.service`: `Result=signal`, `ExecMainCode=2`,
  `ExecMainStatus=15` (SIGTERM). Last journal shows the interrupted download on
  2026-10-28 followed by `Stopped ...`. This demonstrates termination, **not OOM**;
  the actor/reason for the stop cannot be recovered from these observations.
- Unit starts `flock -n .../locks/materials.lock ... python portal/runtime.py materials`,
  has 2 GiB memory cap, 12-hour start timeout and 15-minute restart delay.
  The existing pipeline is not a bounded acquisition/upload/index transaction.
- Production DB: 7,818 pages; policy 5. 7,274 released pages were re-sanitized
  one at a time against deployed `sanitize_page`: **zero changed or blocked**, no
  missing quality rows. 544 pages remain blocked: 523 `ocr_review`, one
  `ocr_empty`, 20 `blocked`. The 523 stored OCR texts are nonempty but still blocked;
  presence of text is explicitly **not** approval. Audit changes no classifications.
- Residual staging: one 15,451,322-byte PDF, SHA256
  `003404871ac5da94e45da70ba4b331d1553958e9cff829784ca6600e5e9bc9de`;
  three separate 15-byte synthetic-looking PDF residuals (same SHA256, provenance
  not established). These are observations, not cleanup authorization.
- Private OneDrive PDF inventory: 512 files, 3,124,950,718 bytes; all expose
  QuickXor metadata. Three remote files match the large residual's size but
  **none matches its QuickXor**. Both sides use 40-character hex hashes, so this
  is not a base64/hex comparison artifact. No remote full PDF was downloaded.
  The residual therefore lacks demonstrated equivalent remote coverage.
- Pre-catalog backup: 15 files, 643,436,898 bytes. Every file was streamed through
  SHA256; metadata/opaque handles/hashes are recorded. The largest file is
  639,631,360 bytes. Remote PDF coverage does not establish equivalent coverage
  for this backup. Retain it intact. Hashes are temporal observations, not an
  application-consistent live database backup certification.

## Implemented, not activated

`federal-online/fo_hub/materials_ops.py` is an opt-in operations wrapper:

1. Explicit JSON allowlist of published PDF paths, no portal traversal or downloads.
2. Nonblocking exclusive existing `materials.lock` and `materials-publication.lock`.
3. Private mode-0700 owned temporary tree, separate copied inodes, streaming SHA256,
   source stability check, PDF magic, 256 MiB default batch budget, 4 GiB disk reserve.
   Reject traversal, symlinked paths, hidden staging, duplicate and empty selections.
4. Optional explicitly authorized upload only to the existing private originals
   namespace. `rclone copy --immutable` refuses changed existing remote objects;
   `rclone check --one-way --download` verifies bytes against the stable snapshot.
   No remote sync/delete command; byte check streams remote bytes without retaining
   full remote PDFs on disk. This option was **not run against production**.
5. Separate mode-0600 JSONL sanitized text index, from a read-only SQLite transaction.
   Only current-policy `text/low_text + text_only`, rechecked by sanitizer, can pass.
   OCR/review/stale/missing classifications stay excluded. No arbitrary titles,
   paths or metadata; document identifiers are opaque hashes. Reject unsafe released
   text before index publication. New output only, atomic no-clobber publication.
6. Cleanup only this invocation's temporary snapshot after full pipeline success;
   failed copy/check/index retains snapshot and private hash receipt. Never clean
   original sources, legacy staging, backup or remote objects. Returns aggregate
   receipt digest and counters, not source paths/text.

This is a **transitional upload/export wrapper**, not a replacement downloader,
not ingestion of new PDF pages, not original-PDF pixel/metadata sanitization,
and not promotion of `g20261029a`. The active-generation database routing must be
reviewed by the deployment coordinator before use: wrapper reads the explicitly
selected state root's `hub.sqlite3` only. An index export is not a production DB
migration. Existing `portal/runtime.py`, `ingest.py`, worker and Anki were untouched.

## Verified locally

```
PYTHONPATH=federal-online services/anki-mcp-v2/.venv/bin/python -m pytest federal-online/tests -q
501 passed in 6.29s
```

Includes actual installed rclone `copy` + `check --download` against a synthetic
local endpoint; production destination is replaced only by the test adapter.
Other tests cover retained failed snapshots, no overwrite/inode/mtime changes,
backup preservation, privacy rejection, blocked OCR exclusion, policy mismatch,
path rejection, symlink rejection, disk budget and output no-clobber.
CLI `python -m fo_hub.materials_ops --help` also exercised.
Initial test invocation required `PYTHONPATH=federal-online`; the documented
command above is the verified invocation. A guessed nonexistent test path was
corrected by running the complete existing suite.

## Safe next steps / blockers

- Coordinator must keep legacy materials writer stopped until its no-clobber
  recovery contract is deployed/verified. Wrapper locks do not freeze independent
  legacy writers that ignore the publication lock.
- There is currently no validated bounded downloader entrypoint in this module.
  Use the separately owned producer workstream; do not invoke the legacy full
  collector through an arbitrary command hook.
- Do not delete the large staging PDF: size matches are disproven as hash matches.
  Recover manifest identity/provenance, then promote no-clobber under the existing
  lock through the separately owned producer path. Preserve differing versions.
- Do not delete 15-byte remnants on appearance alone; bind provenance/ownership
  before any proposed cleanup. No cleanup implementation targets them.
- Do not remove pre-catalog backup without explicit approval, stable database
  backup validation and byte-equivalent independent retention proof.
- A production upload byte readback, activation of this wrapper and production
  ingestion remain coordinator tasks, not claimed complete by synthetic testing.

## Evidence

- `2026-11-06-fo-materials-audit.json`: residual metadata, PDF hashes and quality groups.
- `2026-11-06-fo-materials-privacy-remote.json`: streamed privacy audit, backup file
  metadata/SHA256s, remote inventory aggregate/digest.
- `2026-11-06-fo-materials-coverage.json`: negative large-staging QuickXor coverage.
