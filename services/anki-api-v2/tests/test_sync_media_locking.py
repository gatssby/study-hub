from __future__ import annotations

import threading
import time

import pytest
from anki_api_v2.actor import CollectionActor, CollectionBusy, CollectionLockedError
from anki_api_v2.media import InvalidMediaPath, validate_media_filename

from tests.fakes import FULL_DOWNLOAD, FULL_SYNC, FULL_UPLOAD, NORMAL_SYNC
from tests.helpers import SYNTHETIC_MEDIA_BYTES, SYNTHETIC_MEDIA_NAME

# ---- explicit sync endpoint -------------------------------------------------


def test_post_sync_reports_normal_sync(api):
    api.transport.responses = [NORMAL_SYNC]
    r = api.post("/v2/sync")
    assert r.status_code == 200
    assert r.json()["collection"] == "normal_sync"
    assert r.json()["last_collection_sync_at"] is not None
    assert api.get("/v2/health").json()["sync_state"] == "ok"


def test_post_sync_full_required_returns_409_and_never_uploads(api):
    api.transport.responses = [FULL_UPLOAD]
    r = api.post("/v2/sync")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "full_sync_required"
    assert "full" in r.json()["error"]["message"].lower()
    assert api.get("/v2/health").json()["sync_state"] == "full_sync_required"


@pytest.mark.parametrize("required", [FULL_SYNC, FULL_DOWNLOAD, FULL_UPLOAD])
def test_every_full_sync_kind_is_refused(api, required):
    api.transport.responses = [required]
    assert api.post("/v2/sync").status_code == 409


def test_network_failure_maps_to_sync_failed_without_traceback(api):
    api.transport.fail_on_calls = {1}
    r = api.post("/v2/sync")
    assert r.status_code == 502
    body = r.json()
    assert body["error"]["code"] == "sync_failed"
    assert "Traceback" not in r.text


def test_post_sync_with_media_starts_media_and_reports_running(api):
    r = api.post("/v2/sync", json={"media": True})
    assert r.status_code == 202
    assert r.json()["media"] == "running"
    assert api.transport.media_starts == 1
    assert api.get("/v2/health").json()["media_sync"]["state"] == "running"


def test_media_sync_completion_is_observed_on_health(api):
    api.post("/v2/sync", json={"media": True})
    api.transport.media_active = False
    health = api.get("/v2/health").json()
    assert health["media_sync"]["state"] == "ok"
    assert health["last_media_sync_at"] is not None


def test_media_sync_error_is_reported_as_error_state(api):
    api.post("/v2/sync", json={"media": True})
    api.transport.media_active = False
    api.transport.media_error = "media backend said no"
    health = api.get("/v2/health").json()
    assert health["media_sync"]["state"] == "error"
    assert "media backend said no" not in health.__repr__()


def test_collection_reads_do_not_start_media_sync(api):
    api.get("/v2/decks")
    api.get("/v2/health")
    assert api.transport.media_starts == 0


# ---- media file serving -----------------------------------------------------


def test_media_file_is_served_byte_for_byte(api):
    from urllib.parse import quote

    r = api.get(f"/v2/media/{quote(SYNTHETIC_MEDIA_NAME)}")
    assert r.status_code == 200
    assert r.content == SYNTHETIC_MEDIA_BYTES
    assert r.headers["x-content-type-options"] == "nosniff"


def test_media_is_served_without_any_sync(api):
    from urllib.parse import quote

    api.get(f"/v2/media/{quote(SYNTHETIC_MEDIA_NAME)}")
    assert api.transport.sync_calls == 0


def test_media_missing_file_returns_media_not_found(api):
    r = api.get("/v2/media/absent.png")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "media_not_found"


@pytest.mark.parametrize(
    "raw",
    [
        "..",
        "..%2Fsecret.txt",
        "..%5Csecret.txt",
        "%2e%2e%2fsecret.txt",
        "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        "..%5C..%5Csecret.txt",
        ".hidden",
        "a%00b.jpg",
        "%2Fetc%2Fpasswd",
    ],
)
def test_media_path_traversal_never_returns_content(api, raw, tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("TOP-SECRET-CONTENT")
    r = api.get(f"/v2/media/{raw}")
    assert r.status_code in {400, 404}
    assert "TOP-SECRET-CONTENT" not in r.text


def test_media_symlink_escaping_media_dir_is_refused(api, tmp_path):
    media_dir = api.fx.path.parent / "collection.media"
    outside = tmp_path / "outside.txt"
    outside.write_text("OUTSIDE")
    (media_dir / "link.txt").symlink_to(outside)
    r = api.get("/v2/media/link.txt")
    assert r.status_code in {400, 404}
    assert "OUTSIDE" not in r.text


def test_media_symlink_pointing_inside_media_dir_is_still_refused(api):
    # Policy is "no symlinks at all", not just "no escaping symlinks".
    media_dir = api.fx.path.parent / "collection.media"
    (media_dir / "alias.jpg").symlink_to(media_dir / SYNTHETIC_MEDIA_NAME)
    r = api.get("/v2/media/alias.jpg")
    assert r.status_code in {400, 404}
    assert r.content != SYNTHETIC_MEDIA_BYTES


def test_validate_media_filename_rules():
    assert validate_media_filename("imagem 1.jpg") == "imagem 1.jpg"
    for bad in ["", "..", "a/b", "a\\b", ".hidden", "x\x00y", "a" * 256]:
        with pytest.raises(InvalidMediaPath):
            validate_media_filename(bad)


# ---- locking / ownership ----------------------------------------------------


def test_actor_serializes_operations_on_a_single_thread(tmp_path):
    lock = tmp_path / "collection.lock"
    actor = CollectionActor(open_fn=lambda: object(), lock_path=lock, queue_timeout=5)
    actor.start()
    try:
        in_flight = 0
        max_in_flight = 0
        threads = set()
        guard = threading.Lock()

        def op(_col):
            nonlocal in_flight, max_in_flight
            with guard:
                in_flight += 1
                max_in_flight = max(max_in_flight, in_flight)
                threads.add(threading.get_ident())
            time.sleep(0.01)
            with guard:
                in_flight -= 1
            return 1

        workers = [threading.Thread(target=lambda: actor.submit(op, timeout=10)) for _ in range(20)]
        for w in workers:
            w.start()
        for w in workers:
            w.join()
        assert max_in_flight == 1
        assert len(threads) == 1
    finally:
        actor.stop()


def test_actor_owns_collection_object_on_its_own_thread(tmp_path):
    seen = {}

    def open_fn():
        seen["open_thread"] = threading.get_ident()
        return object()

    actor = CollectionActor(open_fn=open_fn, lock_path=tmp_path / "l.lock", queue_timeout=5)
    actor.start()
    try:
        actor.submit(lambda col: seen.setdefault("op_thread", threading.get_ident()), timeout=5)
        assert seen["open_thread"] == seen["op_thread"]
        assert seen["open_thread"] != threading.get_ident()
    finally:
        actor.stop()


def test_second_owner_of_same_collection_lock_is_refused(tmp_path):
    lock = tmp_path / "collection.lock"
    first = CollectionActor(open_fn=lambda: object(), lock_path=lock, queue_timeout=5)
    first.start()
    try:
        second = CollectionActor(open_fn=lambda: object(), lock_path=lock, queue_timeout=5)
        with pytest.raises(CollectionLockedError):
            second.start()
    finally:
        first.stop()


def test_lock_is_released_after_stop_so_the_api_is_restartable(tmp_path):
    lock = tmp_path / "collection.lock"
    a = CollectionActor(open_fn=lambda: object(), lock_path=lock, queue_timeout=5)
    a.start()
    a.stop()
    b = CollectionActor(open_fn=lambda: object(), lock_path=lock, queue_timeout=5)
    b.start()
    b.stop()


def test_busy_collection_returns_collection_busy_instead_of_hanging(tmp_path):
    gate = threading.Event()
    actor = CollectionActor(
        open_fn=lambda: object(), lock_path=tmp_path / "l.lock", queue_timeout=5
    )
    actor.start()
    outcome: list[BaseException | str] = []

    def caller() -> None:
        try:
            actor.submit(lambda c: 1, timeout=0.05)
            outcome.append("returned")
        except CollectionBusy as exc:
            outcome.append(exc)

    try:
        blocker = threading.Thread(
            target=lambda: actor.submit(lambda c: gate.wait(5), timeout=10), daemon=True
        )
        blocker.start()
        time.sleep(0.05)
        t = threading.Thread(target=caller, daemon=True)
        t.start()
        t.join(2)
        # If the bounded queue wait is removed, submit() blocks behind the gate.
        assert not t.is_alive(), "submit() hung instead of raising CollectionBusy"
        assert len(outcome) == 1 and isinstance(outcome[0], CollectionBusy)
        gate.set()
        blocker.join(5)
    finally:
        gate.set()
        actor.stop()


def test_busy_collection_maps_to_503_over_http(api, monkeypatch):
    from anki_api_v2 import actor as actor_mod

    def boom(self, fn, timeout=None):
        raise actor_mod.CollectionBusy("busy")

    monkeypatch.setattr(actor_mod.CollectionActor, "submit", boom)
    r = api.get("/v2/decks")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "collection_busy"
    assert "retry-after" in {k.lower() for k in r.headers}


def test_unhandled_exception_returns_generic_500_without_traceback(api, monkeypatch):
    from anki_api_v2 import service as service_mod

    def explode(self, col, root=None, limit=50, offset=0):
        raise RuntimeError("internal detail SHOULD-NOT-LEAK")

    monkeypatch.setattr(service_mod.CollectionService, "list_decks", explode)
    r = api.get("/v2/decks")
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "internal_error"
    assert "SHOULD-NOT-LEAK" not in r.text
    assert "Traceback" not in r.text
