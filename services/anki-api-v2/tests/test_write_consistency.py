"""Write confirmation under Anki's one-second change detection.

Measured against anki==26.9.3 and the official sync server: a change made in the
same wall-clock second as the previous successful sync is not uploaded, yet the
sync still answers NO_CHANGES. The write path therefore (a) waits for the next
second before writing, and (b) never reports success for a real change that the
sync-after did not carry.
"""

from __future__ import annotations


def test_write_is_paced_into_a_later_second_than_the_sync_before(api):
    fx = api.fx
    r = api.patch(f"/v2/notes/{fx.basic_note_id}", {"fields": {"Back": "NOVO"}})
    assert r.status_code == 200, r.text
    sync_before, sync_after = api.transport.sync_seconds[0], api.transport.sync_seconds[1]
    assert sync_after > sync_before


def test_successful_write_is_confirmed_on_the_server(api):
    fx = api.fx
    r = api.patch(f"/v2/notes/{fx.basic_note_id}", {"fields": {"Back": "NOVO"}})
    assert r.status_code == 200, r.text
    assert api.transport.server_fields["Back"] == "NOVO"


def test_change_not_carried_by_sync_after_is_never_reported_as_success(api):
    fx = api.fx
    api.transport.drop_changes = True
    r = api.patch(f"/v2/notes/{fx.basic_note_id}", {"fields": {"Back": "NOVO"}})
    assert r.status_code == 502
    err = r.json()["error"]
    assert err["code"] == "sync_failed"
    assert err["details"]["reason"] == "change_not_detected"
    assert err["details"]["local_change_applied"] is True
    assert err["details"]["server_confirmed"] is False
    assert api.transport.server_fields["Back"] == "TSH"
    assert api.get("/v2/health").json()["sync_state"] == "pending"


def test_noop_patch_with_identical_value_is_not_a_false_failure(api):
    fx = api.fx
    api.transport.drop_changes = True
    r = api.patch(f"/v2/notes/{fx.basic_note_id}", {"fields": {"Back": "TSH"}})
    assert r.status_code == 200, r.text


def test_pending_change_is_carried_by_next_successful_sync(api):
    fx = api.fx
    api.transport.drop_changes = True
    first = api.patch(f"/v2/notes/{fx.basic_note_id}", {"fields": {"Back": "NOVO"}})
    assert first.status_code == 502
    api.transport.drop_changes = False
    r = api.post("/v2/sync")
    assert r.status_code == 200, r.text
    assert api.transport.server_fields["Back"] == "NOVO"
    assert api.get("/v2/health").json()["sync_state"] == "ok"
