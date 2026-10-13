#!/usr/bin/env bash
# Deploy the isolated localhost-only Anki MCP v2 service.
# This script does not configure public routing and does not access collection data.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE="${REMOTE_HOST:-oracle-vps}"
REMOTE_ROOT="${ANKI_MCP_V2_REMOTE_ROOT:-/home/ubuntu/anki-vnext/mcp}"
UNIT="anki-vnext-mcp.service"
LOCAL_PYTHON="$ROOT/.venv/bin/python"

"$LOCAL_PYTHON" -m pytest "$ROOT/tests" -q

ssh "$REMOTE" "set -euo pipefail; umask 077; mkdir -p '$REMOTE_ROOT/src' '$REMOTE_ROOT/deploy'"
rsync -az --delete --exclude '__pycache__' "$ROOT/anki_mcp_v2/" "$REMOTE:$REMOTE_ROOT/src/anki_mcp_v2/"
rsync -az "$ROOT/requirements.txt" "$REMOTE:$REMOTE_ROOT/requirements.txt"
rsync -az "$ROOT/deploy/" "$REMOTE:$REMOTE_ROOT/deploy/"

ssh "$REMOTE" bash -s -- "$REMOTE_ROOT" "$UNIT" <<'REMOTE_SCRIPT'
set -euo pipefail

REMOTE_ROOT=$1
UNIT=$2

if [ ! -x "$REMOTE_ROOT/.venv/bin/python" ]; then
  python3 -m venv "$REMOTE_ROOT/.venv"
fi
"$REMOTE_ROOT/.venv/bin/pip" install --disable-pip-version-check --require-virtualenv -q -r "$REMOTE_ROOT/requirements.txt"
sudo install -m 0644 "$REMOTE_ROOT/deploy/$UNIT" "/etc/systemd/system/$UNIT"
sudo systemctl daemon-reload
sudo systemctl enable "$UNIT" >/dev/null
sudo systemctl restart "$UNIT"
systemctl is-active --quiet "$UNIT"
systemctl is-active --quiet anki-vnext-api.service
systemctl is-active --quiet anki-vnext-sync.service

listener_ready() {
  ss -ltn 'sport = :8771' | { read -r _header; read -r _listener; test -n "$_listener"; }
}

for _ in $(seq 1 30); do
  if listener_ready; then
    break
  fi
  sleep 1
done
listener_ready
"$REMOTE_ROOT/.venv/bin/python" "$REMOTE_ROOT/deploy/smoke.py" http://127.0.0.1:8771/mcp
REMOTE_SCRIPT

echo "ANKI_MCP_V2_DEPLOYED remote=$REMOTE_ROOT unit=$UNIT"
