#!/usr/bin/env bash
# Pinned offline installer for the Parakeet TDT v3 pt-BR ONNX acoustic pilot.
#
# Creates only:
#   <root>/venv
#   <root>/models/<six pinned files, flat>
#   <root>/manifest.json (copy of this asset, unless <root> is the asset dir)
#
# It does not touch the Whisper runtime or weights, does not enable services,
# does not change gates, and does not use PyTorch, NeMo, FP32 acoustic weights,
# the Hugging Face cache, or untrusted HF code. Every network download is a
# pinned HTTPS URL verified byte-for-byte against manifest.json.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST="${SCRIPT_DIR}/manifest.json"
REQUIREMENTS="${SCRIPT_DIR}/requirements.txt"

ROOT="${SCRIPT_DIR}"
RESERVE_BYTES=""
CHECK_CAPACITY=0
UNINSTALL=0
ASSUME_YES=0
VERIFY=0
SKIP_TARGET=0
PYTHON_BIN=""

usage() {
  cat <<'EOF'
Usage: install.sh [options]

Options:
  --root DIR          Install root. Creates DIR/venv and DIR/models.
                      Default: the directory containing this script.
  --reserve-bytes N   Existing operational reserve in bytes (required unless
                      PARAKEET_RESERVE_BYTES is set). Supply the live value:
                      Whisper reserve + largest source + 100 MiB.
  --reserve-gib N     Same, in whole GiB (floor).
  --python BIN        Python 3.12.3 interpreter used to build the venv.
                      Default: python3.12.
  --check-capacity    Print the capacity decision as JSON and exit; downloads
                      nothing and does not check the target platform.
  --no-verify         Do not load models (default); use the capped smoke separately.
  --skip-target-check Do not enforce aarch64 / Ubuntu 24.04.5 / glibc 2.39 /
                      Python 3.12.3.
  --uninstall         Remove <root>/venv and <root>/models (requires --yes).
  --yes               Confirm the uninstall.
  -h, --help          Show this help.
EOF
}

die() { printf 'install.sh: error: %s\n' "$*" >&2; exit 1; }
log() { printf '[parakeet-runtime] %s\n' "$*"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --root) ROOT="${2:-}"; shift 2 ;;
    --reserve-bytes) RESERVE_BYTES="${2:-}"; shift 2 ;;
    --reserve-gib)
      case "${2:-}" in
        ''|*[!0-9]*) die "--reserve-gib requires a non-negative integer" ;;
      esac
      RESERVE_BYTES="$(( $2 * 1073741824 ))"; shift 2 ;;
    --python) PYTHON_BIN="${2:-}"; shift 2 ;;
    --check-capacity) CHECK_CAPACITY=1; shift ;;
    --no-verify) VERIFY=0; shift ;;
    --skip-target-check) SKIP_TARGET=1; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    --yes) ASSUME_YES=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
done

[ -f "$MANIFEST" ] || die "manifest not found: $MANIFEST"
[ -f "$REQUIREMENTS" ] || die "requirements not found: $REQUIREMENTS"
[ -n "$ROOT" ] || die "--root must not be empty"
ROOT="$(python3 -c 'import os,sys;print(os.path.abspath(sys.argv[1]))' "$ROOT")"

if [ "$UNINSTALL" != 1 ]; then
  if [ -z "$RESERVE_BYTES" ]; then
    RESERVE_BYTES="${PARAKEET_RESERVE_BYTES:-}"
  fi
  case "$RESERVE_BYTES" in
    ''|*[!0-9]*) die "reserve must be a non-negative integer byte count (--reserve-bytes or PARAKEET_RESERVE_BYTES)" ;;
  esac
fi

read_capacity() {
  python3 - "$MANIFEST" <<'PY'
import json, sys
c = json.load(open(sys.argv[1]))["capacity"]
print(c["headroom_bytes"], c["peak_budget_bytes"])
PY
}

free_bytes() {
  python3 - "$1" <<'PY'
import os, shutil, sys
path = os.path.abspath(sys.argv[1])
measured = path
while not os.path.exists(measured):
    parent = os.path.dirname(measured)
    if parent == measured:
        break
    measured = parent
print(shutil.disk_usage(measured).free)
print(measured, file=sys.stderr)
PY
}

file_size() {
  python3 - "$1" <<'PY'
import os, sys
print(os.path.getsize(sys.argv[1]))
PY
}

file_sha256() {
  python3 - "$1" <<'PY'
import hashlib, sys
h = hashlib.sha256()
with open(sys.argv[1], "rb") as f:
    for chunk in iter(lambda: f.read(1 << 20), b""):
        h.update(chunk)
print(h.hexdigest())
PY
}

manifest_rows() {
  python3 - "$MANIFEST" <<'PY'
import json, sys
m = json.load(open(sys.argv[1]))
for f in m["files"]:
    url = m["sources"][f["source"]]["url_template"].format(file=f["name"])
    print("\t".join((f["name"], url, str(f["bytes"]), f["sha256"])))
PY
}

target_check() {
  [ "$SKIP_TARGET" = 1 ] && return 0
  local arch pyver libc py osid verid ver
  arch="$(uname -m)"
  [ "$arch" = "aarch64" ] || die "architecture is ${arch}, expected aarch64"
  py="${PYTHON_BIN:-python3.12}"
  command -v "$py" >/dev/null 2>&1 || die "python interpreter not found: ${py}"
  pyver="$("$py" -c 'import platform;print(platform.python_version())')"
  [ "$pyver" = "3.12.3" ] || die "python is ${pyver}, expected 3.12.3"
  libc="$("$py" -c 'import platform;print(platform.libc_ver()[1])')"
  [ "$libc" = "2.39" ] || die "glibc is '${libc}', expected 2.39"
  [ -r /etc/os-release ] || die "/etc/os-release not readable; cannot verify Ubuntu 24.04.5"
  osid="$(sed -n 's/^ID=//p' /etc/os-release | tr -d '"')"
  verid="$(sed -n 's/^VERSION_ID=//p' /etc/os-release | tr -d '"')"
  ver="$(sed -n 's/^VERSION=//p' /etc/os-release | tr -d '"')"
  [ "$osid" = "ubuntu" ] || die "OS ID is '${osid}', expected ubuntu"
  [ "$verid" = "24.04" ] || die "Ubuntu VERSION_ID is '${verid}', expected 24.04"
  case "$ver" in
    *"24.04.5"*) ;;
    *) die "Ubuntu VERSION is '${ver}', expected 24.04.5" ;;
  esac
  log "target ok: aarch64 / Ubuntu 24.04.5 / glibc 2.39 / Python 3.12.3"
}

# Prints the capacity decision and exits 1 when free < required.
capacity_decision() {
  local reserve free required headroom peak
  read -r headroom peak < <(read_capacity)
  reserve="$RESERVE_BYTES"
  required=$(( reserve + headroom + peak ))
  free="$(free_bytes "$ROOT")"
  python3 - "$reserve" "$headroom" "$peak" "$required" "$free" "$ROOT" <<'PY'
import json, sys
reserve, headroom, peak, required, free = (int(x) for x in sys.argv[1:6])
root = sys.argv[6]
ok = free >= required
print(json.dumps({
    "ok": ok,
    "root": root,
    "free_bytes": free,
    "reserve_bytes": reserve,
    "headroom_bytes": headroom,
    "peak_budget_bytes": peak,
    "required_bytes": required,
    "shortfall_bytes": max(0, required - free),
}, indent=2))
sys.exit(0 if ok else 1)
PY
}

if [ "$CHECK_CAPACITY" = 1 ]; then
  capacity_decision
  exit 0
fi

if [ "$UNINSTALL" = 1 ]; then
  [ "$ASSUME_YES" = 1 ] || die "--uninstall requires --yes"
  for path in "${ROOT}/venv" "${ROOT}/models"; do
    if [ -e "$path" ]; then
      rm -rf -- "$path"
      log "removed ${path}"
    fi
  done
  log "uninstall complete; source assets in ${SCRIPT_DIR} untouched"
  exit 0
fi

target_check

if ! capacity_decision; then
  die "insufficient free space on the install filesystem ${ROOT}"
fi

command -v curl >/dev/null 2>&1 || die "curl not found"
command -v python3 >/dev/null 2>&1 || die "python3 not found"

MODELS="${ROOT}/models"
STAGING="${ROOT}/.parakeet-staging"
mkdir -p -- "$MODELS" "$STAGING"
trap 'rm -rf -- "$STAGING"' EXIT

while IFS=$'\t' read -r name url expected_bytes expected_sha; do
  [ -n "$name" ] || continue
  dest="${MODELS}/${name}"
  if [ -f "$dest" ] \
     && [ "$(file_size "$dest")" = "$expected_bytes" ] \
     && [ "$(file_sha256 "$dest")" = "$expected_sha" ]; then
    log "verified existing ${name}"
    continue
  fi
  log "downloading ${name} (${expected_bytes} bytes)"
  tmp="${STAGING}/${name}"
  # curl also applies this limit to redirect bodies, which can exceed config.json.
  wire_max=$(( expected_bytes > 1048576 ? expected_bytes : 1048576 ))
  curl -fL --silent --show-error --proto '=https' --proto-redir '=https' --max-time 180 \
       --max-filesize "$wire_max" --retry 1 --retry-delay 2 -o "$tmp" "$url"
  actual_bytes="$(file_size "$tmp")"
  [ "$actual_bytes" = "$expected_bytes" ] \
    || die "size mismatch for ${name}: ${actual_bytes} != ${expected_bytes}"
  actual_sha="$(file_sha256 "$tmp")"
  [ "$actual_sha" = "$expected_sha" ] \
    || die "sha256 mismatch for ${name}: ${actual_sha} != ${expected_sha}"
  mv -f -- "$tmp" "$dest"
  log "verified ${name}"
done < <(manifest_rows)

# Fail closed: after the loop every pinned file must be present and verified.
while IFS=$'\t' read -r name _url expected_bytes expected_sha; do
  [ -n "$name" ] || continue
  dest="${MODELS}/${name}"
  [ -f "$dest" ] || die "missing after download: ${dest}"
  [ "$(file_size "$dest")" = "$expected_bytes" ] \
    || die "size changed after download: ${name}"
  [ "$(file_sha256 "$dest")" = "$expected_sha" ] \
    || die "sha256 changed after download: ${name}"
done < <(manifest_rows)
log "all pinned files verified in ${MODELS}"

if [ "$MANIFEST" != "${ROOT}/manifest.json" ]; then
  cp -- "$MANIFEST" "${ROOT}/manifest.json"
  log "wrote ${ROOT}/manifest.json"
fi

VENV="${ROOT}/venv"
PY="${PYTHON_BIN:-python3.12}"
if [ ! -x "${VENV}/bin/python" ]; then
  log "creating venv ${VENV}"
  "$PY" -m venv "$VENV"
fi

log "installing pinned pip closure"
TMPDIR="$STAGING" PIP_CONFIG_FILE=/dev/null "${VENV}/bin/python" -m pip --isolated install \
  --index-url https://pypi.org/simple --require-hashes --no-cache-dir --only-binary=:all: \
  --disable-pip-version-check -r "$REQUIREMENTS"

"${VENV}/bin/python" - "$MANIFEST" <<'PY'
import importlib.metadata as md
import json
import sys

pins = json.load(open(sys.argv[1]))["pip"]
bad = []
for name, want in pins.items():
    try:
        got = md.version(name)
    except md.PackageNotFoundError:
        bad.append(f"{name} missing")
        continue
    if got != want:
        bad.append(f"{name} {got} != {want}")
try:
    md.version("torch")
    bad.append("torch is installed")
except md.PackageNotFoundError:
    pass
if bad:
    print("pip verification failed: " + "; ".join(bad), file=sys.stderr)
    sys.exit(1)
print("pip pins verified: " + ", ".join(f"{k}=={v}" for k, v in pins.items()))
PY

if [ "$VERIFY" = 1 ]; then
  log "loading models offline from ${MODELS}"
  "${VENV}/bin/python" "${SCRIPT_DIR}/check_runtime.py" \
    --root "$ROOT" --manifest "${ROOT}/manifest.json" --threads 1
fi

log "install complete: ${VENV}"
