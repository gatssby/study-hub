"""End-to-end against the REAL official sync server (`python -m anki.syncserver`).

Uses only temporary, synthetic collections. Proves the sync protocol behaves as the
service assumes: pull on read, push-then-confirm on write, and fail-closed on
full-sync requirements. Needs the `anki` package importable in this interpreter.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from anki.collection import Collection
from anki.sync_pb2 import SyncCollectionResponse
from anki_api_v2.app import create_app
from anki_api_v2.config import Settings
from fastapi.testclient import TestClient

from tests.conftest import AUTH
from tests.helpers import TEST_TOKEN

pytestmark = pytest.mark.e2e

USER = "tester"
PASSWORD = "pw-e2e-only-not-a-secret"


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def sync_server(tmp_path: Path):
    port = _free_port()
    base = tmp_path / "server"
    base.mkdir()
    env = dict(
        os.environ,
        SYNC_USER1=f"{USER}:{PASSWORD}",
        SYNC_BASE=str(base),
        SYNC_HOST="127.0.0.1",
        SYNC_PORT=str(port),
    )
    proc = subprocess.Popen(
        [sys.executable, "-m", "anki.syncserver"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    deadline = time.monotonic() + 20
    while True:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
            break
        except OSError:
            if proc.poll() is not None or time.monotonic() > deadline:
                proc.kill()
                raise RuntimeError("sync server did not start")
            time.sleep(0.2)
    try:
        yield f"http://127.0.0.1:{port}/"
    finally:
        proc.terminate()
        proc.wait(10)


def _login(col: Collection, endpoint: str):
    return col.sync_login(username=USER, password=PASSWORD, endpoint=endpoint)


def _pace_past_last_sync(col: Collection) -> None:
    # Anki detects changes at one-second resolution. A write in the same second as the
    # last sync can be silently skipped, so the writer waits for the next second.
    last_second = col.db.scalar("select ls from col") // 1000
    while int(time.time()) <= last_second:
        time.sleep(0.02)


def _new_basic(col: Collection, front: str) -> int:
    note = col.new_note(col.models.by_name("Basic"))
    note["Front"] = front
    note["Back"] = "b"
    col.add_note(note, col.decks.id("Default"))
    return int(note.id)


def _seed_server_with_one_note(path: Path, endpoint: str) -> int:
    """Operator step: first upload from a client that has data."""
    col = Collection(str(path))
    try:
        nid = _new_basic(col, "seed")
        auth = _login(col, endpoint)
        required = col.sync_collection(auth, sync_media=False).required
        assert required == SyncCollectionResponse.FULL_UPLOAD
        col.close_for_full_sync()
        col.full_upload_or_download(auth=auth, server_usn=None, upload=True)
        col.reopen(after_full_sync=True)
        return nid
    finally:
        col.close()


def _bootstrap_api_collection(path: Path, endpoint: str) -> None:
    """Operator step: full download into the API collection, as service_sync.py does."""
    col = Collection(str(path))
    try:
        auth = _login(col, endpoint)
        assert (
            col.sync_collection(auth, sync_media=False).required
            == SyncCollectionResponse.FULL_DOWNLOAD
        )
        col.close_for_full_sync()
        col.full_upload_or_download(auth=auth, server_usn=None, upload=False)
        col.reopen(after_full_sync=True)
    finally:
        col.close()


def _client(path: Path, endpoint: str) -> TestClient:
    settings = Settings(
        collection_path=path,
        token=TEST_TOKEN,
        sync_endpoint=endpoint,
        sync_username=USER,
        sync_password=PASSWORD,
        lock_path=path.parent / "collection.lock",
        # Tiny TTL: every read performs a real incremental sync.
        freshness_ttl_seconds=0.001,
        queue_timeout_seconds=30.0,
    )
    return TestClient(create_app(settings), raise_server_exceptions=False)


def test_e2e_full_download_is_refused_and_local_collection_is_untouched(sync_server, tmp_path):
    api_path = tmp_path / "api" / "collection.anki2"
    api_path.parent.mkdir()
    Collection(str(api_path)).close()  # empty local collection: server has data -> FULL_DOWNLOAD

    _seed_server_with_one_note(tmp_path / "seed.anki2", sync_server)

    with _client(api_path, sync_server) as client:
        r = client.get("/v2/decks", headers=AUTH)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "full_sync_required"
    assert r.json()["error"]["details"]["required"] == "FULL_DOWNLOAD"

    check = Collection(str(api_path))
    try:
        assert check.note_count() == 0  # nothing was downloaded or overwritten
    finally:
        check.close()


def test_e2e_read_pulls_remote_changes_made_by_another_client(sync_server, tmp_path):
    seed_path = tmp_path / "seed.anki2"
    api_path = tmp_path / "api" / "collection.anki2"
    api_path.parent.mkdir()
    _seed_server_with_one_note(seed_path, sync_server)
    _bootstrap_api_collection(api_path, sync_server)

    other = Collection(str(seed_path))
    try:
        auth = _login(other, sync_server)
        assert other.sync_collection(auth, sync_media=False).required in (
            SyncCollectionResponse.NO_CHANGES,
            SyncCollectionResponse.NORMAL_SYNC,
        )
        _pace_past_last_sync(other)
        new_nid = _new_basic(other, "criado remotamente")
        other.sync_collection(auth, sync_media=False)
    finally:
        other.close()

    with _client(api_path, sync_server) as client:
        r = client.get(f"/v2/notes/{new_nid}", headers=AUTH)
    assert r.status_code == 200, r.text
    assert {"name": "Front", "value": "criado remotamente"} in r.json()["fields"]


def test_e2e_patch_is_confirmed_on_server_by_sync_after(sync_server, tmp_path):
    seed_path = tmp_path / "seed.anki2"
    api_path = tmp_path / "api" / "collection.anki2"
    api_path.parent.mkdir()
    nid = _seed_server_with_one_note(seed_path, sync_server)
    _bootstrap_api_collection(api_path, sync_server)

    with _client(api_path, sync_server) as client:
        r = client.patch(
            f"/v2/notes/{nid}",
            json={"fields": {"Back": "confirmado pelo servidor"}},
            headers=AUTH,
        )
        assert r.status_code == 200, r.text
        assert r.json()["sync"] == {"before": "ok", "after": "ok"}

    # A third, independent client sees the change only if the server really has it.
    third_path = tmp_path / "third.anki2"
    third = Collection(str(third_path))
    try:
        auth = _login(third, sync_server)
        assert (
            third.sync_collection(auth, sync_media=False).required
            == SyncCollectionResponse.FULL_DOWNLOAD
        )
        third.close_for_full_sync()
        third.full_upload_or_download(auth=auth, server_usn=None, upload=False)
        third.reopen(after_full_sync=True)
        assert third.get_note(nid)["Back"] == "confirmado pelo servidor"
    finally:
        third.close()
