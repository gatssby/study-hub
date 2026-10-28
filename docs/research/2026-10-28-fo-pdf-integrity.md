# FO PDF identity/version integrity — 2026-10-28

## Evidence and root cause

Read-only VPS observation at **2026-10-28T04:37:36Z**: 3,147 materials, 508 distinct stored paths; 419 paths have multiple expected SHA-256 values, covering 3,058 material rows. A deterministic bounded sample of the first 64 multi-SHA paths hashed each current physical alias once: **305,255,765 bytes**, 64 matching material identities / 2,740 cached pages, and **426 mismatching identities / 18,149 cached pages**. No unreadable or unstable paths were reported. This is a collision-biased sample, not an estimate of global mismatch prevalence. No PDF parsing, DB writes, source copies, content/title/path logging, deploy or ASR operations occurred. Audit ran under a transient unit capped at CPUQuota=50%, MemoryMax=512M, RuntimeMaxSec=600; it exited 0.

The supplied preceding recovery evidence is distinct from this audit: 227 quarantined pages targeted 205 materials; 36 materials / 40 pages were recovered privately from matching originals; **169 materials / 187 pages** were refused because the current alias hash differs from the stored identity. Three probes found the actual hash belongs to another indexed material. These recovery counts were supplied by the parent, not independently remeasured here. It is 187, not 189, affected target pages.

`fo_hub/ingest.py:245–274` derives identity from actual PDF SHA (`pdf_` plus its first 24 hex characters), upserts the current alias, and keeps previous rows/pages. Reusing a filename with new bytes therefore leaves historical cached text correctly keyed to its old hash, but its stored alias now resolves to a different version. Cached text is not proof original bytes still exist. A mismatch does not prove loss everywhere: another verified alias/object may hold the expected hash.

## Producer investigation

`portal/discovery.py:34–42` promotes staging files using `os.replace`, including same-named destinations; both material promotion entrypoints delegate to it. This promotion preserves existing hardlinked inodes, **but this alone is not a proof of all future writers**. Downloader paths also use `write_bytes` and rename; external maintenance and later refactors are not constrained by the merge helper. Consequently the helper deliberately copies bytes into a new inode rather than hardlinking the producer alias. Only its own completed temporary is linked for atomic no-clobber publication. No producer was changed.

## Proposed opt-in contracts (not wired)

`integrity_snapshot(state_root, material_rows, max_paths=64)`:

- Input rows expose only material_id, relative_path and the full expected sha256. Caller supplies a consistent read-only SQLite result and owns refresh/caching.
- Resolve and deduplicate aliases; hash each observed path once with bounded chunks and before/after metadata checks. Reject absolute/out-of-root aliases and malformed SHA values.
- Return timestamp, hashed-path count and per-material expected/actual hashes plus status: `verified`, `historical_source_unavailable` (observed mismatch), `source_unavailable`, `not_observed`, `invalid_identity` or `invalid_path`. Never include source names, paths or PDF/text content.
- This is a **cached observation**, not a live source guarantee. Unobserved entries fail closed. Budget counts attempted unique aliases; failed reads still consume it. It is a path-count budget, not a byte/time limit: execution must retain resource/time bounds.
- Keep cached historical extraction/citation identity unchanged. API integration should label historical source unavailable rather than linking a newer PDF as that historical version. Snapshot status is orthogonal to privacy/academic quality; `verified` grants no publication permission.

`preserve_version(source, private_root, expected_sha256, reserve_bytes=4 GiB, max_bytes=512 MiB)`:

- Dedicated local private root must be mode 0700, outside material/OneDrive publication trees; PDF names are full SHA only. No DB writes, aliases, remote copies or manifest changes.
- Copy into an owned temporary, check PDF magic and SHA, fsync, mode 0444, then atomic no-clobber publication at `<sha>.pdf`. Remove only that call's owned temporary. Never overwrite/delete source or an existing version. Verify and reuse an existing matching object; reject corrupt/conflicting objects rather than repairing silently.
- Repeated identical versions reuse one object. A later in-place write of the producer alias cannot change the saved object. Filesystem permissions are operational immutability, not security against owner/root.
- Enforce size/free-space limits before and during copy. Caller must serialize storage-budget/publication operations using the existing lock; checks cannot reserve disk against unrelated writers. Default 512 MiB cap is configurable and may refuse larger legitimate PDFs. Reusing an existing verified object needs no copy budget.
- Bytes are hashed after copying; any copied identity mismatch is refused, never relabelled under the historical SHA. This is minimal PDF framing/byte integrity validation, not structural or privacy certification.

## Parent integration/deployment gates

1. Review contract; add caller/store integration separately, preserving full expected SHA and all historical cached text. No schema or serving behavior changes are in this commit.
2. Build/cache a bounded integrity observation outside request hot paths; expose status/time, not private paths. Never interpret not_observed as verified. Refresh explicitly after publication and reverify bytes before use.
3. Preserve each newly acquired version **before its old alias can be replaced**, under the materials publication lock, then commit aliases/manifests/checkpoints. Ingest-only preservation is too late if producer already replaced the old alias. Optionally recover expected historical hashes from other verified aliases first; absence in this sample is not universal absence.
4. Use a dedicated private local SHA store excluded explicitly from OneDrive selection; do not auto-publish originals. Do not bulk copy the existing corpus until disk sizing/authorization. Keep minimum 4 GiB reserve.
5. Only after separate review deploy exact committed files with hash verification and a small gated pilot. This task performed **no deploy**, production writes, mass copies or service restarts.

## Verification

Synthetic stdlib byte fixtures, not real document contents. Red demonstrated missing snapshot module, then missing preservation function; green exercised deduplication, alias replacement isolation, cached observation semantics, historical mismatch, unsafe/missing/budgeted aliases, invalid identity, copy budgets and corrupt existing-object refusal. Full local suite: `PYTHONPATH=federal-online services/anki-mcp-v2/.venv/bin/python -m pytest federal-online/tests -q` → **366 passed in 4.94s**. Bare invocation requires PYTHONPATH because fo_hub is not installed in this interpreter. No actual PDFs were copied by the new helper on VPS.
