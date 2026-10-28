# Private window runner review — 2026-10-28

Scope: four findings in the private benchmark runner introduced at `37bd2f1`. Local synthetic tests only; no real ASR, remote commands, VPS changes, deployment, publication, queue leases or acoustic quality claims.

## Corrections

1. **Owned process group, not just the timing wrapper.** Every production subprocess now starts a new session. All exit paths, including timeout and nonzero/early wrapper exit, terminate the entire group with TERM then KILL, reap the direct child and wait until process inspection shows no live group members. A monitoring failure retries while retaining the transcription lock. Zombies cannot execute; only their parent/init can reap them. Commands must not detach into another session. This is not protection against forced termination of the runner itself; the existing capped service/cgroup remains necessary.
2. **Window-relative QA.** Main transcript segments retain absolute source timestamps. QA receives copies shifted to the start of the five-minute window and a duration of 300 seconds. A synthetic window starting at 1258.5 seconds no longer invents a 1258.5-second leading silence gap.
3. **Original evidence integrity on reuse.** Artifacts retain the original decoder JSON and resource-log paths and SHA-256 values. Cache reuse verifies both originals in addition to the artifact receipt and audio integrity. Missing, modified, symlinked or out-of-root originals fail closed, without downloading or decoding again. Legacy artifacts missing these hashes are deliberately rejected, not silently reconstructed. Private failure JSON, raw decoder output and resource logs remain private and are not deleted or published.
4. **Baseline-first informative comparisons.** Baseline remains available under the existing authorization gate without a new human approval. Other configurations require a private explicit selection receipt and a verified same-window baseline artifact/receipt with intact originals. Model, runtime, libraries, source bytes and audio bytes must match. The selection names a bounded subset of the four additional configurations, marks the window informative, provides nonblank operator/rationale and explicitly does not certify acoustic review. The accepted selection is saved privately. Operator reasoning may be autonomous exploratory reasoning grounded in raw output; it is not human gold or a listening result. The 18-window budget remains per unique selected window, not per configuration.

## Additional comparison receipt

CLI: `--comparison-selection <private-json-file>` (required in practice for every nonbaseline configuration). The private JSON fields are:

- `baseline_artifact`: exact verified baseline artifact path for this lesson/window;
- `baseline_sha256`: hash of that artifact, also checked against its runner receipt;
- `configs`: nonempty unique subset of `beam10`, `fallback`, `no-context`, `no-speech-0.8`;
- `informative`: boolean `true`;
- `operator`: nonblank operator identifier, including an authorized autonomous operator;
- `rationale`: nonblank explanation of why this raw-output window is informative for the named configurations;
- `acoustic_reviewed`: boolean `false`.

This is an audit/selection gate, not proof that the operator's rationale is scientifically correct. `human_gold` remains null, `acoustic_reviewed` remains false, and no benchmark winner is selected.

## RED → GREEN evidence

Command prefix: `services/anki-mcp-v2/.venv/bin/python -m pytest`.

| Regression slice | Observed RED | Verified GREEN |
| --- | --- | --- |
| Window-relative QA | 1 failed: invented leading silence at absolute 1258.5 | 1 passed after shifting QA copies |
| Original raw/log integrity | 4 failed: missing/tampered originals were reused | 4 passed, no added subprocess calls |
| Baseline/selection gate | 6 failed after exposing the selection argument: comparisons proceeded without valid prerequisites | 6 passed within the benchmark suite |
| Real synthetic child cleanup | 2 failed: TERM-resistant child still alive after timeout/early wrapper exit | Both passed; added nonzero-wrapper, lock-held cleanup and transient-monitor-failure coverage also passed |

The process probe launches only synthetic Python processes, not the decoder or a media/model tool. Its integration variant checks that another file handle cannot acquire the shared transcription lock during process-group cleanup, then verifies the child is no longer live before the lock is available. Failure diagnostics are retained privately.

Final local results:

- `federal-online/tests/test_window_benchmark.py -q`: **24 passed**.
- `federal-online/tests -q`: **356 passed**.
- `git diff --check -- federal-online/fo_hub/window_benchmark.py federal-online/tests/test_window_benchmark.py`: clean.
- Existing unrelated Anki working-tree whitespace findings were not modified or staged.

No acoustic strata, real quality metrics, service status or current pilot state were measured in this review.
