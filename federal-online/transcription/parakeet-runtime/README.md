# Parakeet TDT v3 pt-BR 30s — pinned offline ARM64 runtime

Installer assets for a CPU-only, offline **acoustic pilot** of the ONNX export
`alefiury/parakeet-tdt-v3-ptBR-30s-onnx`. This directory contains metadata and
scripts only. It does not download weights, build a venv, start a service, or
change any gate. The parent stages these assets and runs `install.sh` only
after verifying capacity.

## What it creates

Given an install root (`--root`, default: this directory):

```
<root>/venv/                 # isolated CPython 3.12.3 venv, CPU-only onnxruntime
<root>/models/               # exactly six flat files, no subdirectories
<root>/manifest.json         # copy of the pinned manifest (runtime check input)
```

Nothing else is written. The Whisper runtime (`/home/ubuntu/study-hub-models`)
and the FO transcription reserve are never read, moved or deleted.

## Pins

Manifest: **`manifest.json`**, schema `study-hub.parakeet-runtime.manifest/v1`.
The runtime check reads that file (default `<root>/manifest.json`) and reports
the SHA-256 list.

| File | Bytes | SHA-256 |
|---|---|---|
| `encoder-model.int8.onnx` | 654315598 | `2c5ebaa2c0a67ef05cc20e794a0d61006d4733054d1f469b42c2a9aad0e40710` |
| `decoder_joint-model.int8.onnx` | 18309430 | `c6ff05fd0e7babc0fce036421d3cc7f979cb2e64e3a7afcab95b29b39bc03c5d` |
| `nemo128.onnx` | 139764 | `a9fde1486ebfcc08f328d75ad4610c67835fea58c73ba57e3209a6f6cf019e9f` |
| `config.json` | 91 | `6a2577a06b9de8dc201d08722d2fe8b27c5ba13cd5386ed3cf1edaa8807e7102` |
| `vocab.txt` | 93939 | `d58544679ea4bc6ac563d1f545eb7d474bd6cfa467f0a6e2c1dc1c7d37e3c35d` |
| `silero_vad.onnx` | 2327524 | `1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3` |

Sources:

- Hugging Face `alefiury/parakeet-tdt-v3-ptBR-30s-onnx` at revision
  `467eab0884532adfb9d532c074efa1230962ce34` (five files; CC BY 4.0;
  dynamically quantized per-channel QUInt8 encoder and decoder/joint).
- GitHub `snakers4/silero-vad` at commit
  `5cd7945676eb32225748052e2e6a0580e4686a08`, path
  `src/silero_vad/data/silero_vad.onnx` (MIT).

Pip closure (`requirements.txt`), CPython 3.12.3 / aarch64 / manylinux_2_28:

`onnx-asr==0.11.0`, `onnxruntime==1.24.4` (CPU wheel), `numpy==2.4.4`,
`flatbuffers==25.12.19`, `packaging==26.0`, `protobuf==6.33.6`,
`sympy==1.14.0`, `mpmath==1.3.0`. No `torch`, no `huggingface-hub`, no
`onnx`, no GPU extra.

## Capacity gate

`install.sh` requires the live operational reserve to be supplied dynamically
(`--reserve-bytes N` or `PARAKEET_RESERVE_BYTES=N`; `--reserve-gib` is a
convenience). That value must be the existing operational reserve: **Whisper
reserve + largest source + 100 MiB**. It then enforces

```
required_bytes = reserve_bytes + 1 GiB headroom + peak_budget_bytes
peak_budget_bytes = 2 * model_bytes (staging + final) + 1 GiB venv/pip overhead
                 = 2 * 675186346 + 1073741824
                 = 2424114516
```

and compares it with the **actual free bytes on the install filesystem**
(`shutil.disk_usage("<root>").free`). No estimate is substituted. Downloads
start only after the check passes.

## Usage

Capacity only (no download, no target check, safe anywhere):

```sh
./install.sh --root /home/ubuntu/study-hub/parakeet-runtime \
  --reserve-bytes 4294967296 --check-capacity
```

Install (target must be aarch64, Ubuntu 24.04.5, glibc 2.39, Python 3.12.3):

```sh
./install.sh --root /home/ubuntu/study-hub/parakeet-runtime \
  --reserve-bytes "$RESERVE_BYTES" --python python3.12
```

The installer downloads each pinned file to a temporary staging directory on the
same filesystem, verifies size and SHA-256 against `manifest.json`, and only
then moves it flat into `<root>/models`. It never invokes Hugging Face code and
never populates an HF cache. Pip runs with `--no-cache-dir --only-binary=:all:`.

Runtime check (offline load, CPU only, no audio file):

```sh
/home/ubuntu/study-hub/parakeet-runtime/venv/bin/python \
  /path/to/parakeet-runtime/check_runtime.py \
  --root /home/ubuntu/study-hub/parakeet-runtime \
  --manifest /home/ubuntu/study-hub/parakeet-runtime/manifest.json
```

The check prints a JSON report (`--json-out FILE` to save it) covering target
platform, all six file hashes, venv/pip pins, available onnxruntime providers,
and `encoder` / `decoder_joint` / `silero_vad` session providers. It exits
non-zero on any mismatch. `--probe` additionally pushes 1 s of in-memory zeros
through the model (synthetic; still no real audio).

Reversible removal (leaves this source directory untouched):

```sh
./install.sh --root /home/ubuntu/study-hub/parakeet-runtime --uninstall --yes
```

## Safety properties

- **Offline / no untrusted HF code**: direct pinned HTTPS URLs, `curl --proto =https`, SHA-256 verified. No `huggingface_hub`, no `snapshot_download`.
- **No PyTorch / no cache duplicates**: requirements exclude torch; pip uses `--no-cache-dir`; models are downloaded to a cleaned staging directory.
- **No FP32 acoustic weights**: only the int8 encoder/decoder are installed. The check rejects `encoder-model.onnx`, `decoder_joint-model.onnx` and any `*.onnx.data`.
- **Isolated CPU**: private venv, CPU `onnxruntime` wheel, `providers=["CPUExecutionProvider"]`, non-CPU providers rejected.
- **No activation**: no systemd unit, no timer, no gate/env change, no Whisper path access.

## Local validation performed (2026-11-21, no VPS access)

- Hugging Face API at the pinned revision confirms repo id, revision, file sizes
  and LFS SHA-256 for `encoder-model.int8.onnx`, `decoder_joint-model.int8.onnx`
  and `nemo128.onnx`.
- GitHub API at the pinned Silero commit confirms the file path, size
  2327524 and git blob `80c5592ef1f4c9ede3e357bbd02eb863358a6a9d`.
- The four small files were downloaded from the pinned endpoints and their
  SHA-256 was computed locally: `nemo128.onnx` matches the pinned LFS SHA-256;
  `silero_vad.onnx` matches `1a153a22…`; `config.json` and `vocab.txt` match
  the pinned git blobs `d6e61a3e…` and `fc43e1c7…` respectively.
- PyPI metadata confirms aarch64/CPython 3.12 wheels for `onnxruntime 1.24.4`
  (`manylinux_2_28_aarch64`) and `numpy 2.4.4`, and universal wheels for the
  remaining pinned packages.
- `bash -n install.sh` and `python3 -m py_compile check_runtime.py` pass; the
  manifest parses and the capacity/check scripts run locally in
  `--check-capacity` / `--manifest-only` modes.
- A scratch end-to-end run of `install.sh` (reduced manifest containing only the
  four small files, `--skip-target-check --no-verify`) downloaded and verified
  each file, created a venv, installed the pinned closure with
  `--no-cache-dir --only-binary=:all:`, and verified every pin with `torch`
  absent. `check_runtime.py --skip-model` then reported `ok=true` for files,
  venv and pins, and `onnx_asr.load_vad("silero", path=<root>/models)` loaded
  offline with `CPUExecutionProvider`.

Not validated locally: the aarch64 model load itself (requires the target VPS
venv) and real-audio accuracy. This is an installation/integrity pilot, not a
quality result.

## Oracle VPS pilot — operational runbook

The verified runtime is already installed at
`/home/ubuntu/study-hub-models/fo-parakeet-int8`; do not reinstall it. Ubuntu
24.04.5/aarch64 CPU smoke used generated Portuguese speech, not lecture audio:
4.069 s input, 0.114 s VAD, 2.897 s ASR, 1,106,272 KiB peak process RSS,
5.101 cgroup CPU-seconds, 20.211 s wall including model checks and loading.
Models allocated 675,213,312 B and the venv 222,330,880 B. Model execution
is not evidence of lecture accuracy.

### Decoder handoff and safe deployment

The primary worker keeps its leader lock and live job lease across a review
turn. After a chunk is fsynced and progress committed, it acknowledges a pending
request (`review_turn_yielded`), releases the decoder flock, and waits for the
reviewer to finish before taking the flock and logging `review_turn_resumed`.
Child ASR processes inherit the decoder FD so killing the parent cannot grant a
second decoder access while the first survives. Download and ordinary media
conversion do not require the inference lock but inherit the worker leader FD
so scratch recovery cannot race a surviving child. When external publication
holds the publication lock, the worker releases the decoder while waiting.
Never unlink lock files.

Deploy from a known committed revision, not the working tree. On the VPS export,
verify both staged and live SHA-256 values. Include the transitive runtime
closure: `worker.py`, `acoustic_service.py`, `acoustic_review.py`,
`acoustic_candidate.py` and `window_benchmark.py` as applicable. In the production
venv smoke `run_process_group(['/bin/true'], timeout=2, pass_fds=())` as well as
imports. The first real cutover attempt reached the safe boundary but an old
deployed `window_benchmark.py` lacked the `pass_fds` interface; unit tests on the
Mac did not catch drift in the VPS export.

For an authorized interruption, stop the primary systemd cgroup and prove all
children and relevant flock owners are gone. A decoder FD may still be closing
when the cgroup appears empty; allow a short, bounded drain (up to 15 seconds)
and abort rather than bypass a held flock. Save a private, hash-checked
before-image and checkpoint inventory. Reconcile only the exact lesson/version/
owner lease in one `BEGIN IMMEDIATE` transaction, with no attempt charge. Verify
the job was requeued and unchanged checkpoints verify before restarting. Check
the actual loaded generation, singleton leader, live lease and decoder, not just
the new files. On November 22, 2026 the cutover from `06981f9` to `49e6303`
requeued `fo_9c48da1a924603a1` v1 and resumed `fo_ab7589742bc156fd` v3 from a
durable checkpoint. A follow-up cutover loaded `c1272a3` after the first timer
run and verified renewed real decoding and timer rearm. Preserve the cutover
and lease receipts; never replay one against a new lease. If interrupted
mid-deployment, inspect the existing VPS
controller, cgroup, file hashes and lease before acting; never duplicate it.

For primary rollback, stop acoustic admissions first and let the reviewer finish
or stop only its unit. Restore a verified worker generation after quiescence or
the same authorized stop-and-reconcile sequence. Verify a single active worker,
resumed progress and readable checkpoints. Do not restore a stale database or
change the authorization gate to make deployment pass.

### Scheduled evidence-only reviewer

The versioned `study-hub-fo-acoustic-review.service` and `.timer` in
`ops/study-hub/systemd/` are installed; the timer was enabled on November 22,
2026, after real lecture audio proved exclusive handoff and resume and the FO
API/Plugin QA gate was verified. In proof invocation `e834ace2061a4720a4b0f264e5d26d16`,
the reviewer requested at 18:10:42 UTC, acquired at 18:12:00 UTC after 78.016 s
with the same primary lease at progress 1.0 and the old decoder gone, and
released at 18:12:38 UTC. Whisper then started another decoder. Biology v2
produced a private receipt for 8.16 s of audio; speech was present, comparison
was inconclusive, and the transcript stayed in review.

The first timer invocation `76c0fadddfeb4603a4b8aa15f0e09c78` completed
successfully at 18:37:54 UTC. It waited 980.189 s for a 600 s Whisper audio
chunk to commit and processed 8.50 s of History v1 in 28.60 s active wall
time. The original primary resumed with another decoder; the private receipt
is inconclusive and no transcript changed. The timer scheduled the next turn.

For a new host or reactivation after rollback, require the same evidence before
enabling. Check that earlier transient controllers and their children are
inactive, precreate `transcripts/acoustic-review` (`ubuntu:ubuntu`, `0700`),
and run `systemd-analyze verify` on the exact unit files. Enable only the timer.

- `sudo systemctl enable --now study-hub-fo-acoustic-review.timer` schedules
  the first check in five minutes. `systemctl list-timers --all` and
  `systemctl status study-hub-fo-acoustic-review.timer` show its schedule.
- `journalctl -u study-hub-fo-acoustic-review.service` shows state and IDs,
  not transcript text. A service in `activating` can be waiting for a turn.
  The request expires after 48 minutes (systemd startup cap: 52 minutes);
  the expensive Whisper chunk is capped at 45 minutes, not interrupted for
  ordinary handoff. Once the decoder fence is acquired,
  systemd caps active work at five minutes. Clean skips are also acknowledged
  but exit immediately without inference.
- `python3 ops/study-hub/fo_monitor.py --check` is a read-only health probe
  using the existing SSH alias. It prints only health codes, not lesson details:
  exit `0` healthy, `1` monitor unavailable, `2` actionable failure. Normal
  chunk waits do not alert. `--once` displays the aggregate operating metrics.
- Each activation checks eligibility read-only and admits at most one job.
  Focal cases get a 24-hour priority boost, not absolute priority. Oversized
  or corrupt inputs cannot block other lessons. The timer waits 15 minutes
  after completion and yields to Whisper. An unchanged evidence receipt
  prevents duplicate inference. At most two attempts per evidence key are
  allowed, separated by 24 hours. An attempt is reserved before media
  acquisition, not during runtime setup. After a crash, the next scheduled
  turn cleans only verified disposable scratch while holding the decoder
  fence, even when no case is eligible. The service is capped at 0.5 OCPU and
  3 GiB with no swap.
- Optional `FO_ACOUSTIC_PRIORITY` accepts up to five exact `fo_<id>:<version>`
  pairs in a service drop-in. This changes rank only: current source, QA,
  receipt and retry checks still apply. Do not run a parallel cohort controller.
- To stop or roll back only the reviewer, disable and stop the timer first,
  then stop its service: `sudo systemctl disable --now study-hub-fo-acoustic-review.timer`
  and `sudo systemctl stop study-hub-fo-acoustic-review.service`. Verify that
  both are inactive and Whisper acquires its next turn. Keep private receipts
  and attempt history. No Whisper restart is required to disable reviews.

Receipts are private, immutable and keyed by current source and QA evidence.
An exact one-row overlap candidate may record raw-row provenance, a window PCM
hash, and a projected QA result. It remains non-publishable until independent
listening confirms it represents one utterance, not a legitimate repetition.
A favorable VAD or Parakeet result alone cannot clear a blocker. Keep uncertain
content and all original artifacts; retain the existing publication QA gate.
