# FO periodic materials — deployed and timer enabled, 07/11/2026

## Production acceptance

Commit 7b93b61 deployed with hashes checked. Two initial automatic selections
observed empty branches and advanced the durable cursor without upload. The third
manual invocation acquired a real PDF (32,590,808 bytes / 436 pages), verified the
full-SHA remote object, indexed policy v5 (435 text-only / one blocked), committed
cursor sequence 3 and removed its temporary originals. No persistent local alias.

After acceptance, the primary materials.timer was enabled/active. Its persistent
catch-up ran a fourth selection automatically: another real PDF (5,703,103 bytes /
203 text-only v5 pages), remote byte check, cursor sequence 4 and zero retained
temporary originals. The existing daily 04:45 UTC calendar remains; this is bounded
incremental rotation, not an assertion of complete or near-real-time coverage.

Final readback: 174 materials / 8,457 pages, 7,912 text-only and 545 blocked. The
historical 544 blocked pages were not released. The legacy producer was not started.
The statements below describe the design and the earlier acceptance prerequisites;
live receipts are linked from docs/research/2026-11-07-fo-mvp-activation.md.

## Producer and checkpoint

`fo_hub.materials_cycle` now defaults to automatic rotation. Every invocation calls
`BrowserSession.discover_material_options()` to rediscover the currently exposed
courses and disciplines. It selects the least recently successfully observed
branch, filters it, observes its current visible material rows and downloads the
least recently verified row, including PDF slides via an explicit row-adapter opt-in.
Legacy callers retain their slide-exclusion default. New branches/rows have priority. This acquires at
most ONE PDF per invocation (zero for an observed empty branch), not one fixed
row disguised as global collection. Finite stable observations are visited fairly
across successive invocations; there is no claim that one invocation completes
the corpus, that pagination not exposed by the existing adapter is covered, or
that continuously growing input can be completely covered by a finite schedule.

`state/materials-rotation.json` holds durable branch/row observation identities,
last-success sequence, metadata and every verified content hash with source URL,
remote object name and observation time. IDs use course/discipline option values
and row title/subject/type/date; duplicate semantic rows use occurrence ordinal.
These are observation IDs, NOT portal-guaranteed immutable document IDs. A
metadata edit creates another identity; old identities and byte versions remain.
Changing order of distinguishable rows does not change their IDs. Indistinguishable
duplicates cannot be uniquely attributed across reordering.

Each revisit downloads again: equal metadata does NOT establish equal bytes.
SHA256 deduplicates remote objects and new-hash indexing. Silent byte changes are
detected when their row is next revisited. No global completion counter or removal
is inferred from absent/transient observations. Failed discovery/download/upload/
indexing does not advance the cursor. An owned failure directory blocks later
acquisition; no automatic resume/deletion hides evidence. Cursor load and atomic
fsync/replace occur under the existing materials lock. Cursor advances only after
remote byte verification and SQLite commit. A crash before cleanup retains the
failure guard even if publication completed and requires operator reconciliation.

## Publication and budgets

Authenticated collector -> invocation-owned `tmp/materials-cycle-*` -> private
hash-verified snapshot -> `onedrive:Federal Online PDFs/objects/sha256/<SHA>.pdf`
using immutable checksum copy -> streaming remote byte check -> sanitized page
indexing -> durable cursor -> cleanup ONLY this invocation's temporary originals.
Existing indexed hashes/OCR decisions remain unchanged. No original is published
to persistent VPS `materials/`. Failed trees are retained privately, not retried
or erased automatically. Original PDF pixels/metadata are not privacy-sanitized;
new empty/image-only text remains blocked. Existing local-only OCR cannot process
these remote-only originals without a separately approved bounded path.

Budgets: one accepted file, 256 MiB, 1000 pages; free-space reserve 4 GiB plus two
maximum accepted batches. Native/fallback downloads may exceed accepted-output
bytes before rejection. PDF parsing memory is not bounded by page count. Cgroup
CPU100%/2G, task limit and timeout remain mandatory. Discovery enumerates all
course options per invocation; its duration is not bounded by the one-PDF count.
Locks: materials, materials-publication, index. No catalog/worker/QA code changes.

## Coordinated acceptance after commit/deploy

Deploy only reviewed committed mission paths and verify hashes first. The primary
`study-hub-fo-materials.service` now invokes automatic rotation with CPU100%,
MemoryMax=2G, TimeoutStartSec=75min and KillMode=control-group. It has no outer
flock (the module owns that same lock) and no Restart. Its existing timer file and
calendar are unchanged. No separate cycle timer/service is needed or installed.
Do NOT enable the timer before live acceptance and operator review. Do not touch
the independent ASR pilot or its 300%/12G settings.

After committed deployment, run ONE manual primary service invocation, retaining
private stdout/journal; verify the exact cursor, aggregate DB delta, full-SHA remote
object byte check, cleanup, and cgroup exit status before scheduling. Equivalent
module command (run only inside the unit's cgroup, not an unbounded SSH shell):

```sh
/home/ubuntu/study-hub-venv/bin/python -m fo_hub.materials_cycle \
  --state /home/ubuntu/study-hub-state/federal-online \
  --env-file /home/ubuntu/.config/study-hub/federal_online.env --upload
```

Explicit diagnostic mode remains available only when all four arguments are
provided together: `--course-value`, `--course-label`, `--discipline`, `--row`.
It is not periodic global selection and does not advance the rotation checkpoint.

## Evidence

Local directed RED->GREEN: rotation visits all synthetic branches/rows, rediscovers
new branches, selects new rows, retains byte revisions/provenance, uses dynamic
filters through the collector adapter, defaults CLI to rotation, commits cursor
only after verified indexing, handles empty branches without upload, and never
advances on failed upload. Existing synthetic real-local-rclone copy/check and
idempotency tests pass. These do not establish live portal completeness or real
OneDrive acceptance. Those were the implementation-stage limits; production
invocations and timer activation were subsequently verified as described above.
