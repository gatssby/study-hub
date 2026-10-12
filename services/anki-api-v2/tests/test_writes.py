from __future__ import annotations

from tests.fakes import FULL_DOWNLOAD


def _note(api, note_id=None):
    return api.get(f"/v2/notes/{note_id or api.fx.basic_note_id}").json()


def test_patch_updates_existing_field(api):
    fx = api.fx
    r = api.patch(f"/v2/notes/{fx.basic_note_id}", {"fields": {"Back": "TSH e T4 livre"}})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["note_id"] == fx.basic_note_id
    assert body["updated_fields"] == ["Back"]
    assert {"name": "Back", "value": "TSH e T4 livre"} in _note(api)["fields"]


def test_patch_add_and_remove_tags(api):
    fx = api.fx
    r = api.patch(
        f"/v2/notes/{fx.basic_note_id}",
        {"add_tags": ["revisar"], "remove_tags": ["alpha"]},
    )
    assert r.status_code == 200, r.text
    assert sorted(_note(api)["tags"]) == ["endo", "revisar"]


def test_patch_rejects_empty_payload_without_writing(api):
    r = api.patch(f"/v2/notes/{api.fx.basic_note_id}", {})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_request"
    assert api.transport.sync_calls == 0


def test_patch_rejects_unknown_field_and_leaves_note_untouched(api):
    fx = api.fx
    before = _note(api)
    r = api.patch(f"/v2/notes/{fx.basic_note_id}", {"fields": {"Nope": "x"}})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_field"
    assert _note(api) == before


def test_patch_rejects_note_type_change_attempt(api):
    r = api.patch(
        f"/v2/notes/{api.fx.basic_note_id}",
        {"fields": {"Back": "x"}, "note_type": "Cloze"},
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_request"


def test_patch_rejects_oversized_field(api):
    r = api.patch(
        f"/v2/notes/{api.fx.basic_note_id}",
        {"fields": {"Back": "x" * 20_001}},
    )
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "payload_too_large"


def test_patch_rejects_too_many_tags(api):
    tags = [f"t{i}" for i in range(51)]
    r = api.patch(f"/v2/notes/{api.fx.basic_note_id}", {"add_tags": tags})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_request"


def test_patch_rejects_tag_containing_space(api):
    r = api.patch(f"/v2/notes/{api.fx.basic_note_id}", {"add_tags": ["duas palavras"]})
    assert r.status_code == 422


def test_patch_rejects_same_tag_added_and_removed(api):
    r = api.patch(
        f"/v2/notes/{api.fx.basic_note_id}",
        {"add_tags": ["x"], "remove_tags": ["x"]},
    )
    assert r.status_code == 422


def test_patch_missing_note_returns_note_not_found(api):
    r = api.patch("/v2/notes/1234567890123", {"fields": {"Back": "x"}})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "note_not_found"


def test_patch_refuses_change_that_would_create_new_cards(api):
    fx = api.fx
    before_cards = api.get(f"/v2/notes/{fx.cloze_note_id}").json()["card_ids"]
    r = api.patch(
        f"/v2/notes/{fx.cloze_note_id}",
        {"fields": {"Text": "Fase {{c1::A}} e {{c2::B}}"}},
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "card_set_change_blocked"
    after = api.get(f"/v2/notes/{fx.cloze_note_id}").json()
    assert after["card_ids"] == before_cards
    assert "{{c2::B}}" not in " ".join(v["value"] for v in after["fields"])


def test_patch_syncs_before_and_after_and_sees_change_only_after(api):
    fx = api.fx
    api.transport.responses = []
    r = api.patch(f"/v2/notes/{fx.basic_note_id}", {"fields": {"Back": "NOVO"}})
    assert r.status_code == 200, r.text
    events = api.transport.sync_events()
    assert len(events) == 2
    before_snapshot, after_snapshot = events[0][1], events[1][1]
    assert before_snapshot["Back"] == "TSH"
    assert after_snapshot["Back"] == "NOVO"
    assert r.json()["sync"] == {"before": "ok", "after": "ok"}


def test_patch_not_applied_when_sync_before_fails(api):
    fx = api.fx
    api.transport.fail_on_calls = {1}
    r = api.patch(f"/v2/notes/{fx.basic_note_id}", {"fields": {"Back": "NOVO"}})
    assert r.status_code == 502
    assert r.json()["error"]["code"] == "sync_failed"
    api.transport.fail_on_calls = set()
    assert {"name": "Back", "value": "TSH"} in _note(api)["fields"]


def test_patch_reports_unconfirmed_when_sync_after_fails(api):
    fx = api.fx
    api.transport.fail_on_calls = {2}
    r = api.patch(f"/v2/notes/{fx.basic_note_id}", {"fields": {"Back": "NOVO"}})
    assert r.status_code == 502
    err = r.json()["error"]
    assert err["code"] == "sync_failed"
    assert err["details"]["local_change_applied"] is True
    assert err["details"]["server_confirmed"] is False
    health = api.get("/v2/health").json()
    assert health["sync_state"] == "pending"


def test_pending_change_is_pushed_by_next_write_sync(api):
    fx = api.fx
    api.transport.fail_on_calls = {2}
    api.patch(f"/v2/notes/{fx.basic_note_id}", {"fields": {"Back": "NOVO"}})
    api.transport.fail_on_calls = set()
    r = api.patch(f"/v2/notes/{fx.basic_note_id}", {"add_tags": ["ok"]})
    assert r.status_code == 200, r.text
    assert api.get("/v2/health").json()["sync_state"] == "ok"


def test_patch_fails_closed_on_full_sync_before_write(api):
    fx = api.fx
    api.transport.responses = [FULL_DOWNLOAD]
    api.transport.sync_calls = 0
    r = api.patch(f"/v2/notes/{fx.basic_note_id}", {"fields": {"Back": "NOVO"}})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "full_sync_required"
    api.transport.fail_on_calls = set()
    assert {"name": "Back", "value": "TSH"} in _note(api)["fields"]
