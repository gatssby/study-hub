# FO PDF publication without original overwrite — 2026-10-28

## Decision and boundary

The original is the existing published PDF path/inode, not a replaceable alias. A **version** is newly acquired PDF bytes identified by their full SHA-256. A **manifest observation** binds academic metadata to one version/path; `file_name` remains the academic filename, not the storage version filename.

`portal/discovery.py::merge_materials(build, final)` is the shared publication boundary used by the active materials runtime and both existing legacy wrappers (`promote_raw_dir`, `promote_output_dir`). No legacy collector/queue was recreated. No store, ingestion, integrity helper, worker, benchmark, pilot or catalog behavior was changed.

### Publication contract

1. Before publication, enumerate owned staging, reject symlinks/path escapes/overlapping roots, hash staged PDFs using 1 MiB chunks, and resolve all new manifest observations. A supplied SHA that differs from actual bytes aborts before publication. Missing legacy SHA is populated from observed bytes, never inferred from metadata. Previous manifest rows are retained without relabelling historical SHA values.
2. If the same relative path has identical bytes, reuse the existing PDF without modifying its inode or mtime. If bytes differ, preserve the existing PDF unchanged and select `<stem>--<full-sha256>.pdf` (stem bounded in UTF-8 bytes). Verify an existing version path and reuse it; a conflicting/corrupt version path fails closed, never repairs/overwrites evidence.
3. Publish owned staging with atomic no-clobber links. On the normal same-filesystem build/final layout, this adds no PDF byte copy or private CAS object. After publication, only redundant owned staging names are unlinked. The opt-in private preservation helper is not called.
4. EXDEV alone takes a bounded streaming copy into an owned destination temporary, validates its SHA, fsyncs it, then publishes no-clobber. Check a 4 GiB free-space reserve before and throughout that copy; no arbitrary maximum PDF size is imposed. This is a guard, not a disk reservation against unrelated writers.
5. Fsync PDFs and affected directory entries before atomically publishing metadata. Merge JSON rows by versioned relative path and expected SHA; retain old observations, preserve `file_name`, rewrite new `relative_path`, and regenerate accompanying TSV from the same rows. Only after the whole generation publishes is staging removed. JSON/TSV are individually atomic, not a multi-file transaction: an interrupted metadata publication can leave one older view, but every newly visible PDF reference already has durable bytes.
6. Runtime holds the existing exclusive `materials-publication.lock` across staged manifest writing and promotion, then updates checkpoint success. OneDrive's existing shared-lock interval remains compatible. Failed publication keeps its build and never advances that job/checkpoint or uploads. On retry, runtime finishes a pending staged manifest generation before any download can reuse its staging names. A source referenced by already-published hardlinks must not be rewritten in place.

The former runtime premerge by relative path was removed from the active flow: it would replace the old observation before versioned paths were resolved. Its fallback now stages only the new observations; the shared boundary owns history merging. Both legacy wrappers automatically receive the same no-clobber/versioned behavior, but callers of that low-level boundary remain responsible for serializing concurrent generations.

## Verification

Initial RED: the collision regression demonstrated `%PDF-new` replacing `%PDF-old` at `lesson.pdf` in the original implementation. GREEN covers collision/history hashes and academic names, repeated version dedup, unchanged original inode/mtime, PDF and metadata fault injection with retained staging and retry, mismatched manifest refusal before publication, both legacy wrappers, matching JSON/TSV paths, upload callback seeing both originals and versions, runtime checkpoint/upload failure gating and pending-generation-first recovery, EXDEV reserve refusal and streamed publication, and a no-clobber race retaining foreign evidence/source.

Final command:

```text
PYTHONPATH=federal-online services/anki-mcp-v2/.venv/bin/python -m pytest federal-online/tests -q
388 passed in 4.97s
```

Owned-path `git diff --check` passed. One intermediate full run exposed an unrelated concurrent `invalid_identity` source-observation failure; a later full run passed after the other agent's changes. Tests use explicitly synthetic, small PDF-framed bytes and callback/fault injection; they are filesystem/publication evidence, not academic PDF quality, real OneDrive verification, or structural PDF validation. No real PDFs were opened/copied, no mass copy/upload, no VPS operation and no deployment occurred.

## Risks / separate gates

- This prevents future producer overwrites; it cannot recover bytes lost before this change or make an existing mismatched historical observation verified. Historical cached text/identity is not reassigned to the currently available PDF.
- Filesystem links/permissions do not protect against an unrelated owner/root writer mutating published inodes. Owned staging and serialized producers are prerequisites. Runtime retries pending publication before downloading; direct legacy callers must obey the same contract.
- Additive upload now sees unchanged originals plus distinct new version names. Actual remote inventory/byte agreement and existing remote-name drift remain separate pre-deployment gates; no remote guarantee is inferred from the mocked upload boundary.
- Metadata can be partially updated after a crash, but PDF-before-manifest ordering and retained staging make it safe/retryable. No checkpoint claims a completed failed generation. External readers must keep using the publication lock to observe a complete generation.
- Real PDF validity, privacy/academic extraction correctness, production disk sizing and host crash testing were not evaluated by these synthetic regressions.
