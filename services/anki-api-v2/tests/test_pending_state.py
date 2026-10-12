"""A pending (unconfirmed) write must stay pending until the server actually takes it.

A sync that answers NO_CHANGES is a success for the transport, but it says nothing
about a note that the server silently dropped. Clearing "pending" on any successful
sync would report a lost change as healthy.
"""

from __future__ import annotations


def test_no_changes_sync_does_not_clear_a_pending_write(api):
    fx = api.fx
    api.transport.drop_changes = True
    failed = api.patch(f"/v2/notes/{fx.basic_note_id}", {"fields": {"Back": "NOVO"}})
    assert failed.status_code == 502

    # Reads and explicit syncs keep answering NO_CHANGES while the server still drops it.
    api.clock.advance(60)
    assert api.get("/v2/decks").status_code == 200
    assert api.post("/v2/sync").status_code == 200

    health = api.get("/v2/health").json()
    assert health["sync_state"] == "pending"
    assert health["status"] == "degraded"


def test_pending_retry_is_paced_into_a_later_second(api):
    fx = api.fx
    api.transport.drop_changes = True
    failed = api.patch(f"/v2/notes/{fx.basic_note_id}", {"fields": {"Back": "NOVO"}})
    assert failed.status_code == 502
    seconds_before_retry = len(api.transport.sync_seconds)

    api.transport.drop_changes = False
    assert api.post("/v2/sync").status_code == 200
    retry_second = api.transport.sync_seconds[seconds_before_retry]
    previous_second = api.transport.sync_seconds[seconds_before_retry - 1]
    assert retry_second > previous_second


def test_pending_is_cleared_once_the_server_takes_the_change(api):
    fx = api.fx
    api.transport.drop_changes = True
    api.patch(f"/v2/notes/{fx.basic_note_id}", {"fields": {"Back": "NOVO"}})
    api.transport.drop_changes = False
    assert api.post("/v2/sync").status_code == 200
    health = api.get("/v2/health").json()
    assert health["sync_state"] == "ok"
    assert health["status"] == "ok"
