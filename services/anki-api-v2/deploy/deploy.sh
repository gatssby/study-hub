#!/usr/bin/env bash
# Deploy Anki GPT API v2 to the Oracle VPS, isolated from the legacy stack.
#
# Touches only /home/ubuntu/anki-vnext/api and the anki-vnext-api.service unit.
# Never touches :8767 (legacy), :27701 (sync server), the Service Collection data,
# or /home/ubuntu/anki-gpt-sync. It does NOT copy any collection or media from the Mac.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE="${REMOTE_HOST:-oracle-vps}"
REMOTE_ROOT="${ANKI_API_V2_REMOTE_ROOT:-/home/ubuntu/anki-vnext/api}"
UNIT="anki-vnext-api.service"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

echo "Local checks"
(cd "$ROOT" && .venv/bin/python -m pytest -q -p no:cacheprovider -m "not e2e")

echo "Preparing remote directories"
ssh "$REMOTE" "set -euo pipefail; umask 077
mkdir -p '$REMOTE_ROOT/src' '$REMOTE_ROOT/deploy' '$REMOTE_ROOT/backups'
if [ -d '$REMOTE_ROOT/src/anki_api_v2' ]; then
  tar -C '$REMOTE_ROOT' -czf '$REMOTE_ROOT/backups/release-$STAMP.tgz' src deploy requirements.txt 2>/dev/null || true
fi"

echo "Uploading code (package, requirements, unit). No data files."
rsync -az --delete --exclude '__pycache__' "$ROOT/anki_api_v2/" "$REMOTE:$REMOTE_ROOT/src/anki_api_v2/"
rsync -az "$ROOT/requirements.txt" "$REMOTE:$REMOTE_ROOT/requirements.txt"
rsync -az "$ROOT/deploy/$UNIT" "$REMOTE:$REMOTE_ROOT/deploy/$UNIT"

echo "Installing isolated venv with pinned dependencies"
ssh "$REMOTE" "set -euo pipefail; umask 077
if [ ! -x '$REMOTE_ROOT/.venv/bin/python' ]; then
  python3 -m venv '$REMOTE_ROOT/.venv'
fi
'$REMOTE_ROOT/.venv/bin/pip' install --disable-pip-version-check --require-virtualenv -q -r '$REMOTE_ROOT/requirements.txt'
'$REMOTE_ROOT/.venv/bin/python' -c 'import importlib.metadata as m, sys; sys.exit(0 if m.version(\"anki\") == \"26.9.3\" else 1)' \
  || { echo 'anki version mismatch on remote' >&2; exit 1; }
"

echo "Ensuring api.env exists (token generated on the VPS, never printed)"
ssh "$REMOTE" "set -euo pipefail; umask 077; F='$REMOTE_ROOT/api.env'
if [ ! -f \"\$F\" ]; then
  TOKEN=\$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')
  printf '%s\n' \"ANKI_API_TOKEN=\$TOKEN\" 'ANKI_API_HOST=127.0.0.1' 'ANKI_API_PORT=8770' \
    'ANKI_API_COLLECTION_PATH=/home/ubuntu/anki-vnext/service/collection.anki2' \
    'ANKI_API_SYNC_CREDENTIALS_FILE=/home/ubuntu/anki-vnext/syncserver.env' \
    'ANKI_API_SYNC_ENDPOINT=http://127.0.0.1:27701/' 'ANKI_API_LOG_LEVEL=INFO' > \"\$F\"
  echo 'api.env created (mode 600)'
fi
chmod 600 \"\$F\"
"

echo "Installing and restarting systemd unit"
ssh "$REMOTE" "set -euo pipefail
sudo install -m 0644 '$REMOTE_ROOT/deploy/$UNIT' /etc/systemd/system/$UNIT
sudo systemctl daemon-reload
sudo systemctl enable $UNIT >/dev/null
sudo systemctl restart $UNIT
"

echo "Waiting for /v2/health on 127.0.0.1:8770"
ssh "$REMOTE" "set -euo pipefail
TOKEN=\$(sed -n 's/^ANKI_API_TOKEN=//p' '$REMOTE_ROOT/api.env')
for _ in \$(seq 1 30); do
  if curl -fsS -o /dev/null -H \"Authorization: Bearer \$TOKEN\" http://127.0.0.1:8770/v2/health; then
    echo 'health OK'; exit 0
  fi
  sleep 1
done
echo 'health check failed; see: journalctl -u $UNIT -n 80' >&2
exit 1
"

echo "ANKI_API_V2_DEPLOYED remote=$REMOTE_ROOT backup=$REMOTE_ROOT/backups/release-$STAMP.tgz"
