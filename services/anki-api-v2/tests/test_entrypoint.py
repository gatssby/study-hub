from __future__ import annotations

from pathlib import Path

import pytest
from anki_api_v2 import __main__ as entry

from tests.helpers import TEST_TOKEN


def _env(tmp_path: Path, *, collection: bool = True, **extra: str) -> dict[str, str]:
    creds = tmp_path / "syncserver.env"
    creds.write_text("SYNC_USER1=tester:pw-entrypoint\n")
    col = tmp_path / "collection.anki2"
    if collection:
        col.write_bytes(b"")  # existence is what the entrypoint checks, not contents
    env = {
        "ANKI_API_TOKEN": TEST_TOKEN,
        "ANKI_API_COLLECTION_PATH": str(col),
        "ANKI_API_SYNC_CREDENTIALS_FILE": str(creds),
        "ANKI_API_HOST": "127.0.0.1",
        "ANKI_API_PORT": "8770",
    }
    env.update(extra)
    return env


@pytest.fixture
def started(monkeypatch) -> list[dict]:
    calls: list[dict] = []
    monkeypatch.setattr(entry.uvicorn, "run", lambda app, **kw: calls.append(kw))
    return calls


def test_missing_collection_exits_2_and_never_starts_the_server(tmp_path, started, capsys):
    # Exit 2 means configuration error; the systemd unit does not restart on it.
    # Without this check, Collection() would silently create an empty collection.
    assert entry.main(_env(tmp_path, collection=False)) == 2
    assert started == []
    assert "not found" in capsys.readouterr().err


def test_non_loopback_host_exits_2_and_never_starts_the_server(tmp_path, started):
    assert entry.main(_env(tmp_path, ANKI_API_HOST="0.0.0.0")) == 2
    assert started == []


def test_missing_token_exits_2(tmp_path, started):
    env = _env(tmp_path)
    env["ANKI_API_TOKEN"] = "short"
    assert entry.main(env) == 2
    assert started == []


def test_valid_config_starts_exactly_one_worker_on_loopback(tmp_path, started):
    assert entry.main(_env(tmp_path)) == 0
    assert len(started) == 1
    assert started[0]["workers"] == 1
    assert started[0]["host"] == "127.0.0.1"
    assert started[0]["port"] == 8770
