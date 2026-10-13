from __future__ import annotations

from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
UNIT_PATH = SERVICE_ROOT / "deploy" / "anki-vnext-mcp.service"
DEPLOY_PATH = SERVICE_ROOT / "deploy" / "deploy.sh"
SMOKE_PATH = SERVICE_ROOT / "deploy" / "smoke.py"
TUNNEL_UNIT_PATH = SERVICE_ROOT / "deploy" / "anki-vnext-mcp-tunnel.service"
TUNNEL_DEPLOY_PATH = SERVICE_ROOT / "deploy" / "deploy_tunnel.sh"


def test_systemd_unit_is_loopback_only_and_reuses_api_token_env():
    unit = UNIT_PATH.read_text(encoding="utf-8")

    assert "EnvironmentFile=/home/ubuntu/anki-vnext/api/api.env" in unit
    assert "Environment=ANKI_MCP_V2_HOST=127.0.0.1" in unit
    assert "Environment=ANKI_MCP_V2_PORT=8771" in unit
    assert "ExecStart=/home/ubuntu/anki-vnext/mcp/.venv/bin/python -m anki_mcp_v2" in unit
    assert "NoNewPrivileges=true" in unit
    assert "PrivateTmp=true" in unit
    assert "0.0.0.0" not in unit
    assert "8767" not in unit


def test_deploy_script_is_isolated_from_legacy_network_and_collection_data():
    script = DEPLOY_PATH.read_text(encoding="utf-8").lower()

    assert "/home/ubuntu/anki-vnext/mcp" in script
    assert "anki-vnext-mcp.service" in script
    assert "anki_mcp_v2_remote_root" not in script
    for forbidden in ("8767", "nginx", "certbot", "dns", "collection.anki2", "/v2/sync"):
        assert forbidden not in script


def test_deploy_script_uses_localhost_mcp_smoke_check_without_printing_token():
    script = DEPLOY_PATH.read_text(encoding="utf-8")
    smoke = SMOKE_PATH.read_text(encoding="utf-8")

    assert "127.0.0.1:8771/mcp" in script
    assert "streamable_http" in smoke
    assert "ANKI_API_TOKEN=" not in script


def test_remote_listener_check_uses_ss_port_selector_without_nested_python_quotes():
    script = DEPLOY_PATH.read_text(encoding="utf-8")

    assert "ss -ltn 'sport = :8771'" in script
    assert "python3 -c 'import sys; assert any" not in script
    assert "read -r _listener" in script
    assert 'test -n "$_listener"' in script
    assert 'case "$_listener" in' in script
    assert "*127.0.0.1:8771*" in script
    assert "for _ in $(seq 1 30)" in script
    assert "sleep 1" in script


def test_deploy_uses_a_stdin_remote_script_to_avoid_nested_ssh_shell_quoting():
    script = DEPLOY_PATH.read_text(encoding="utf-8")

    assert 'ssh "$REMOTE" bash -s -- "$REMOTE_ROOT" "$UNIT" <<\'REMOTE_SCRIPT\'' in script
    assert "REMOTE_ROOT=$1" in script
    assert "UNIT=$2" in script


def test_tunnel_unit_keeps_the_control_plane_secret_in_the_root_only_environment_file():
    unit = TUNNEL_UNIT_PATH.read_text(encoding="utf-8")

    assert "User=ubuntu" in unit
    assert "Group=ubuntu" in unit
    assert "EnvironmentFile=/etc/anki-vnext-mcp-tunnel.env" in unit
    assert "ExecStart=/usr/local/bin/tunnel-client run --profile anki-vnext" in unit
    assert "Restart=on-failure" in unit
    assert "RestartSec=5" in unit
    assert "NoNewPrivileges=true" in unit
    assert "PrivateTmp=true" in unit
    assert "ProtectSystem=strict" in unit
    assert "ProtectHome=read-only" in unit
    assert "RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6" in unit
    assert "0.0.0.0" not in unit
    assert "8770" not in unit
    assert "8767" not in unit
    assert "CONTROL_PLANE_API_KEY=" not in unit


def test_tunnel_deploy_uses_official_arm64_release_checksum_and_loopback_mcp_only():
    script = TUNNEL_DEPLOY_PATH.read_text(encoding="utf-8")

    assert "api.github.com/repos/openai/tunnel-client/releases/latest" in script
    assert "SHA256SUMS.txt" in script
    assert "tunnel-client-${TAG}-linux-arm64.zip" in script
    assert "http://127.0.0.1:8771/mcp" in script
    assert "--mcp-server-url" in script
    assert "--sample sample_mcp_remote_no_auth" in script
    assert "systemd-run" in script
    assert '--property="EnvironmentFile=${ENV_FILE}"' in script
    assert "tunnel-client doctor --profile anki-vnext --explain" in script
    assert 'rsync -az "$LOCAL_DEPLOY_DIR/anki-vnext-mcp-tunnel.service"' in script
    assert '"$REMOTE:$REMOTE_ROOT/deploy/"' in script
    assert "tunnel-client run" not in script
    assert "cat /etc/anki-vnext-mcp-tunnel.env" not in script
    assert "CONTROL_PLANE_API_KEY=" not in script
    for forbidden in ("0.0.0.0", "8767", "8770", "nginx", "certbot", "dns", "anki_update_note"):
        assert forbidden not in script
