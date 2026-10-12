from __future__ import annotations

import pytest
from anki_api_v2.config import ConfigError, Settings

from tests.helpers import TEST_TOKEN


def test_settings_require_token_of_sufficient_length(tmp_path):
    env = {
        "ANKI_API_TOKEN": "short",
        "ANKI_API_COLLECTION_PATH": str(tmp_path / "c.anki2"),
        "ANKI_API_SYNC_CREDENTIALS_FILE": str(tmp_path / "s.env"),
    }
    with pytest.raises(ConfigError):
        Settings.from_env(env)


def test_settings_read_sync_credentials_from_existing_file_without_copying(tmp_path):
    creds = tmp_path / "syncserver.env"
    creds.write_text("SYNC_USER1=leonardo:super-secret-pw\nSYNC_PORT=27701\n")
    env = {
        "ANKI_API_TOKEN": TEST_TOKEN,
        "ANKI_API_COLLECTION_PATH": str(tmp_path / "c.anki2"),
        "ANKI_API_SYNC_CREDENTIALS_FILE": str(creds),
    }
    s = Settings.from_env(env)
    assert s.sync_username == "leonardo"
    assert s.sync_password == "super-secret-pw"
    assert "super-secret-pw" not in repr(s)
    assert s.sync_endpoint == "http://127.0.0.1:27701/"


def test_settings_refuse_missing_credentials_file(tmp_path):
    env = {
        "ANKI_API_TOKEN": TEST_TOKEN,
        "ANKI_API_COLLECTION_PATH": str(tmp_path / "c.anki2"),
        "ANKI_API_SYNC_CREDENTIALS_FILE": str(tmp_path / "missing.env"),
    }
    with pytest.raises(ConfigError):
        Settings.from_env(env)


def test_auth_is_required_on_every_v2_route(api):
    assert api.client.get("/v2/health").status_code == 401
    assert api.client.get("/v2/decks").status_code == 401
    r = api.client.get("/v2/health", headers={"Authorization": "Bearer " + "x" * 40})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_auth_rejects_non_bearer_scheme(api):
    r = api.client.get("/v2/health", headers={"Authorization": f"Basic {TEST_TOKEN}"})
    assert r.status_code == 401


def test_health_reports_collection_counts_and_versions_without_secrets(api):
    r = api.get("/v2/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["anki_version"] == "26.09.3"
    assert body["collection_open"] is True
    assert body["notes"] == 3
    assert body["cards"] == 4
    assert body["decks"] >= 3
    assert body["media_count"] == 1
    assert body["sync_state"] == "unknown"
    assert body["last_collection_sync_at"] is None
    assert body["last_media_sync_at"] is None
    text = r.text
    assert TEST_TOKEN not in text
    assert "pw-never-logged" not in text


def test_health_does_not_trigger_a_sync(api):
    api.get("/v2/health")
    assert api.transport.sync_calls == 0
