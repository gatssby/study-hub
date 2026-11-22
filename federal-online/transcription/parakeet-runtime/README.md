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

**Activation gate:** the legacy Whisper loop holds `transcription.lock`
through every job and its idle sleep. The tested successor holds a separate
leader lock for the worker lifetime and takes `transcription.lock` only for
recovery, each complete job, and its existing QA pass. A reviewer can request
the next boundary through `acoustic-review.turn`; it still cannot enter until
the same decoder lock is free. A waiting request owns no lease and expires.

Do not replace running code, restart or signal Whisper, edit the authorization
gate, or remove any lock file to make the pilot run. Roll out the successor at
an approved lifecycle boundary, with the legacy process already quiesced, no
active decoder/lease, and original checkpoints preserved. Verify the loaded
code revision and new lock behavior before the first production review. If
rollback is needed, let the reviewer finish or stop only its transient unit,
then restore the prior Whisper code at a similarly safe boundary. Keep all
existing receipts, original artifacts and lock files.

If the operator session ends during a cutover, first inspect the original
observer's remote PID, command, parent and deadline. Compare the live worker
hash and PID with the staged and legacy hashes, and cross-check the current
lease, decoder child, leader lock and durable checkpoints. A live observer
must not be duplicated; a disconnected operator or empty client log does not
prove that it stopped. At expiry, confirm the process exited and whether it
left a legacy, cooperative, or partial deployment before taking any action.
Retain the hash-verified legacy worker backup. To roll back, first stop only
review admissions, then restore the verified legacy file while the primary
service is stopped at a proven no-decoder, no-lease boundary. Start the
primary unit and verify a single worker, new lease progress and intact
checkpoints. Do not roll back by changing queue rows or lock files.

For a single explicitly authorized cutover and fixed cohort that must survive
SSH disconnection, prefer VPS-owned transient services with `Restart=no` and
hard deadlines. The November 22 recovery uses
`study-hub-fo-parakeet-cutover.service` and
`study-hub-fo-parakeet-cohort.service`; neither is an installed or recurring
service. Inspect `systemctl show` for both PIDs and states, then read their
`journalctl -u` logs. Do not start a manual review while the cohort controller
is active. The controller tied to that observer's invocation requires a
logged zero-lease/no-decoder cutover, the verified new worker holding the
leader lock and a new Whisper lease. It admits only the five authorized
versions in order, once each, and stops on failure, lack of a private audio
receipt, or failure to observe Whisper resuming. To prevent further admissions,
stop only the cohort controller and, if necessary, separately stop its named
transient acoustic pilot unit; do not terminate a cutover in progress or stop
Whisper. After expiry or disconnect, re-read exact process state and receipts
before scheduling any follow-up. A waiting controller is not a completed review.

Once the cooperative Whisper process is verified, run **one** review per unit
as `ubuntu`, from the deployed `federal-online` tree. Reuse the existing
service's environment file without reading it into output. Do not run this
against a legacy worker:

```sh
runtime=/home/ubuntu/study-hub-models/fo-parakeet-int8
sudo systemd-run --unit=study-hub-fo-acoustic-pilot --wait --collect \
  -p User=ubuntu -p Group=ubuntu -p WorkingDirectory=/home/ubuntu/study-hub/federal-online \
  -p EnvironmentFile=/home/ubuntu/.config/study-hub/transcription.env \
  -p CPUQuota=50% -p MemoryMax=3G -p MemorySwapMax=0 \
  -p Nice=15 -p IOSchedulingClass=idle -p UMask=0077 \
  -p RuntimeMaxSec=300 -p TimeoutStopSec=15 -p KillMode=control-group -p Restart=no \
  --setenv=OPENBLAS_NUM_THREADS=1 --setenv=OMP_NUM_THREADS=1 \
  "$runtime/venv/bin/python" -m fo_hub.acoustic_review --runtime "$runtime" \
  --lesson-id "$lesson_id" --version "$version" --wait-for-whisper 120
```

`systemctl status study-hub-fo-acoustic-pilot` shows an active run;
`sudo systemctl stop study-hub-fo-acoustic-pilot` stops only that run. Review
logs contain status codes, not lecture text. On exit 4, defer to another
controlled window; do not loop or increase the cap automatically. Check the
primary worker resumed normally before requesting the next lesson. The runner
rechecks disk, source SHA/revision and QA, and writes an atomic private receipt
under `$FO_STATE_ROOT/transcripts/acoustic-review` (or the default FO state
root). No receipt changes QA or exposes any transcript to the FO Plugin.
Ordinary completion and cooperative cancellation clean scratch; after a hard
kill, inspect any orphaned private `work-*` directories and remove only those
verified to be owned by a finished reviewer with no open descriptors.

An unchanged receipt skips inference. Lexical agreement is not an acoustic
verdict; adjudicate with the original audio, VAD and existing evidence, and
keep uncertain academic content unchanged. No systemd timer or persistent
reviewer is installed. Do not enable one until real cases demonstrate useful
evidence, safe resource use, and a successful controlled handoff.
