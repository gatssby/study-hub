#!/usr/bin/env bash
# Install OpenAI's current ARM64 tunnel-client and connect it only to local MCP v2.
set -euo pipefail

REMOTE="${REMOTE_HOST:-oracle-vps}"
LOCAL_DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOTE_ROOT="/home/ubuntu/anki-vnext/mcp"
ENV_FILE="/etc/anki-vnext-mcp-tunnel.env"
UNIT="anki-vnext-mcp-tunnel.service"
MCP_URL="http://127.0.0.1:8771/mcp"
STATE_DIR="/var/lib/anki-vnext-mcp-tunnel"

ssh "$REMOTE" "set -euo pipefail; mkdir -p '$REMOTE_ROOT/deploy'"
rsync -az "$LOCAL_DEPLOY_DIR/anki-vnext-mcp-tunnel.service" "$REMOTE:$REMOTE_ROOT/deploy/"

ssh "$REMOTE" bash -s -- "$ENV_FILE" "$UNIT" "$MCP_URL" "$STATE_DIR" <<'REMOTE_SCRIPT'
set -euo pipefail

ENV_FILE=$1
UNIT=$2
MCP_URL=$3
STATE_DIR=$4

require_root_env_file() {
  test -f "$ENV_FILE"
  test "$(stat -c '%U:%G %a' "$ENV_FILE")" = "root:root 600"
}

require_root_env_file
systemctl is-active --quiet anki-vnext-mcp.service
systemctl is-active --quiet anki-vnext-api.service
systemctl is-active --quiet anki-vnext-sync.service
ss -ltn 'sport = :8771' | grep -q '127.0.0.1:8771'

case "$(uname -m)" in
  aarch64|arm64) ;;
  *) echo "unsupported architecture: $(uname -m)" >&2; exit 1 ;;
esac

for command in curl unzip sha256sum python3 systemd-run; do
  command -v "$command" >/dev/null
 done

release_json=$(mktemp)
checksums=$(mktemp)
archive=$(mktemp --suffix=.zip)
stage=$(mktemp -d)
cleanup() {
  rm -f "$release_json" "$checksums" "$archive"
  rm -rf "$stage"
}
trap cleanup EXIT

curl --fail --silent --show-error --location \
  --header 'Accept: application/vnd.github+json' \
  --header 'User-Agent: anki-vnext-mcp-tunnel-installer' \
  https://api.github.com/repos/openai/tunnel-client/releases/latest >"$release_json"
TAG=$(python3 - "$release_json" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as source:
    tag = json.load(source).get("tag_name")
if not isinstance(tag, str) or not tag.startswith("v"):
    raise SystemExit("latest release did not include a valid tag")
print(tag)
PY
)
ARCHIVE_NAME="tunnel-client-${TAG}-linux-arm64.zip"
BASE_URL="https://github.com/openai/tunnel-client/releases/download/${TAG}"
curl --fail --silent --show-error --location "${BASE_URL}/SHA256SUMS.txt" >"$checksums"
EXPECTED_SHA=$(awk -v name="$ARCHIVE_NAME" '$2 == name {print $1}' "$checksums")
test -n "$EXPECTED_SHA"
curl --fail --silent --show-error --location "${BASE_URL}/${ARCHIVE_NAME}" >"$archive"
printf '%s  %s\n' "$EXPECTED_SHA" "$archive" | sha256sum --check --status
unzip -q -j "$archive" -d "$stage"
test -x "$stage/tunnel-client"
sudo install -o root -g root -m 0755 "$stage/tunnel-client" /usr/local/bin/tunnel-client

/usr/local/bin/tunnel-client --version
/usr/local/bin/tunnel-client help quickstart

sudo install -d -o ubuntu -g ubuntu -m 0700 "$STATE_DIR"
sudo install -o root -g root -m 0644 \
  /home/ubuntu/anki-vnext/mcp/deploy/anki-vnext-mcp-tunnel.service \
  "/etc/systemd/system/${UNIT}"

run_as_tunnel_user() {
  sudo systemd-run --wait --collect --pipe --quiet \
    --property=User=ubuntu \
    --property=Group=ubuntu \
    --property="EnvironmentFile=${ENV_FILE}" \
    --property="Environment=HOME=${STATE_DIR}" \
    --property="Environment=XDG_CONFIG_HOME=${STATE_DIR}" \
    /bin/sh -ceu "$1"
}

run_as_tunnel_user 'exec /usr/local/bin/tunnel-client init --sample sample_mcp_remote_no_auth --profile anki-vnext --tunnel-id "$TUNNEL_ID" --mcp-server-url "http://127.0.0.1:8771/mcp"'
run_as_tunnel_user 'exec /usr/local/bin/tunnel-client doctor --profile anki-vnext --explain'

sudo systemctl daemon-reload
sudo systemctl enable "$UNIT" >/dev/null
sudo systemctl restart "$UNIT"
systemctl is-active --quiet "$UNIT"
REMOTE_SCRIPT
