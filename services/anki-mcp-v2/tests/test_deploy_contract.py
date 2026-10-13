from __future__ import annotations

from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
UNIT_PATH = SERVICE_ROOT / "deploy" / "anki-vnext-mcp.service"
DEPLOY_PATH = SERVICE_ROOT / "deploy" / "deploy.sh"
SMOKE_PATH = SERVICE_ROOT / "deploy" / "smoke.py"


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
    for forbidden in ("8767", "nginx", "certbot", "dns", "collection.anki2", "/v2/sync"):
        assert forbidden not in script


def test_deploy_script_uses_localhost_mcp_smoke_check_without_printing_token():
    script = DEPLOY_PATH.read_text(encoding="utf-8")
    smoke = SMOKE_PATH.read_text(encoding="utf-8")

    assert "127.0.0.1:8771/mcp" in script
    assert "streamable_http" in smoke
    assert "ANKI_API_TOKEN=" not in script
