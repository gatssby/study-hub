"""Note reads (revision, media refs), note types, create, delete and patch preconditions."""

from __future__ import annotations

import pytest
from tests.fakes import FULL_DOWNLOAD, FULL_UPLOAD


def _note(api, nid):
    return api.get(f"/v2/notes/{nid}").json()


def _count(api):
    return api.get("/v2/health").json()["notes"]


# ---- reads ---------------------------------------------------------------------------


def test_get_note_exposes_revision_mod_usn_deck_names_and_no_media(api):
    body = _note(api, api.fx.basic_note_id)
    assert body["revision"].startswith("r1-") and len(body["revision"]) == 35
    assert isinstance(body["mod"], int) and isinstance(body["usn"], int)
    assert body["deck_names"] == ["Medicina::Endocrino"]
    assert body["media"] == []


def test_revision_is_stable_across_reads_and_across_a_sync_that_only_changes_usn(api):
    nid = api.add_note("rev")
    first = _note(api, nid)
    assert api.post("/v2/sync").status_code == 200
    second = _note(api, nid)
    assert first["revision"] == second["revision"]


def test_revision_changes_when_a_field_or_a_tag_changes(api):
    nid = api.fx.basic_note_id
    base = _note(api, nid)["revision"]
    api.patch(f"/v2/notes/{nid}", {"fields": {"Back": "outro"}})
    after_field = _note(api, nid)["revision"]
    api.patch(f"/v2/notes/{nid}", {"add_tags": ["novo"]})
    after_tag = _note(api, nid)["revision"]
    assert len({base, after_field, after_tag}) == 3


def test_media_refs_are_structured_deduplicated_and_never_include_remote_or_traversal(api):
    nid = api.add_note(
        '<img src="imagem 1.jpg"><img src="imagem%201.jpg"> <img src=\'gone.png\'>'
        '<img src="https://x.org/r.png"><img src="data:image/png;base64,AA==">'
        '<img src="../z.png"><img src="sub/dir.png">',
        back="[sound:a.mp3]",
    )
    media = _note(api, nid)["media"]
    assert media == [
        {
            "filename": "imagem 1.jpg",
            "field": "Front",
            "kind": "image",
            "mime_type": "image/jpeg",
            "exists": True,
            "size_bytes": 18,
            "viewable": True,
        },
        {
            "filename": "gone.png",
            "field": "Front",
            "kind": "image",
            "mime_type": "image/png",
            "exists": False,
            "size_bytes": None,
            "viewable": True,
        },
        {
            "filename": "a.mp3",
            "field": "Back",
            "kind": "sound",
            "mime_type": "audio/mpeg",
            "exists": False,
            "size_bytes": None,
            "viewable": False,
        },
    ]


# ---- note types ------------------------------------------------------------------------


def test_list_note_types_returns_names_kinds_fields_templates(api):
    body = api.get("/v2/note-types").json()
    by_name = {i["name"]: i for i in body["items"]}
    assert {"Basic", "Cloze", "Basic (and reversed card)"} <= set(by_name)
    basic = by_name["Basic"]
    assert basic["kind"] == "standard" and isinstance(basic["id"], str)
    assert basic["field_names"] == ["Front", "Back"]
    assert basic["template_names"] == ["Card 1"]
    assert basic["note_count"] == 1
    assert by_name["Cloze"]["kind"] == "cloze"
    assert by_name["Cloze"]["field_names"] == ["Text", "Back Extra"]
    assert by_name["Basic (and reversed card)"]["template_names"] == ["Card 1", "Card 2"]


def test_get_note_type_has_ordered_fields_and_templates(api):
    nt_id = _note(api, api.fx.basic_note_id)["note_type"]["id"]
    body = api.get(f"/v2/note-types/{nt_id}").json()
    assert body["id"] == nt_id and body["name"] == "Basic" and body["kind"] == "standard"
    assert body["fields"] == [{"name": "Front", "ord": 0}, {"name": "Back", "ord": 1}]
    assert body["duplicate_check_field"] == "Front"
    assert body["sort_field"] == "Front"
    assert body["templates"][0]["name"] == "Card 1"
    assert body["templates"][0]["question_format"] == "{{Front}}"
    assert "{{Back}}" in body["templates"][0]["answer_format"]


def test_get_note_type_rejects_malformed_and_unknown_ids(api):
    assert api.get("/v2/note-types/abc").json()["error"]["code"] == "invalid_id"
    r = api.get("/v2/note-types/1234567890123")
    assert r.status_code == 404 and r.json()["error"]["code"] == "note_type_not_found"


def test_note_type_reads_perform_no_write(api):
    api.get("/v2/note-types")
    assert api.transport.sync_calls <= 1


# ---- create ----------------------------------------------------------------------------


def _create(api, **over):
    body = {
        "deck": "Medicina::Endocrino",
        "note_type": "Basic",
        "fields": {"Front": "Q?", "Back": "A"},
        "tags": ["t1", "t2"],
    }
    body.update(over)
    return api.post("/v2/notes", body)


def test_create_note_makes_note_cards_tags_deck_and_syncs_twice(api):
    r = _create(api)
    assert r.status_code == 201, r.text
    body = r.json()
    assert len(body["card_ids"]) == 1 and body["sync"] == {"before": "ok", "after": "ok"}
    assert body["revision"].startswith("r1-")
    assert api.transport.sync_calls == 2
    note = _note(api, body["note_id"])
    assert note["fields"] == [{"name": "Front", "value": "Q?"}, {"name": "Back", "value": "A"}]
    assert sorted(note["tags"]) == ["t1", "t2"]
    assert note["deck_names"] == ["Medicina::Endocrino"]
    assert note["card_ids"] == body["card_ids"]
    assert note["revision"] == body["revision"]


def test_create_note_generates_every_card_the_templates_define(api):
    r = _create(api, note_type="Basic (and reversed card)")
    assert r.status_code == 201 and len(r.json()["card_ids"]) == 2
    r = _create(api, note_type="Cloze", fields={"Text": "a {{c1::b}} c {{c2::d}}"})
    assert r.status_code == 201 and len(r.json()["card_ids"]) == 2


def test_create_note_resolves_deck_and_note_type_by_id(api):
    nt_id = _note(api, api.fx.basic_note_id)["note_type"]["id"]
    r = _create(api, deck=api.fx.cardio_deck_id, note_type=nt_id)
    assert r.status_code == 201, r.text
    assert _note(api, r.json()["note_id"])["deck_ids"] == [api.fx.cardio_deck_id]


def test_create_note_missing_fields_default_to_empty(api):
    r = _create(api, fields={"Front": "so frente"})
    assert r.status_code == 201
    assert _note(api, r.json()["note_id"])["fields"][1] == {"name": "Back", "value": ""}


@pytest.mark.parametrize(
    ("over", "status", "code"),
    [
        ({"fields": {"Front": "x", "Nope": "y"}}, 422, "invalid_field"),
        ({"deck": "Nao::Existe"}, 404, "deck_not_found"),
        ({"deck": "1234567890123"}, 404, "deck_not_found"),
        ({"note_type": "Nao Existe"}, 404, "note_type_not_found"),
        ({"fields": {}}, 422, "empty_note"),
        ({"fields": {"Front": "   "}}, 422, "empty_note"),
        ({"note_type": "Cloze", "fields": {"Text": "sem cloze"}}, 422, "invalid_cloze"),
        ({"fields": {"Front": "x" * 20_001}}, 413, "payload_too_large"),
        ({"tags": ["duas palavras"]}, 422, "invalid_request"),
        ({"surprise": 1}, 422, "invalid_request"),
        ({"deck": ""}, 422, "invalid_request"),
    ],
)
def test_create_note_rejects_bad_input_without_any_write(api, over, status, code):
    before = _count(api)
    api.transport.sync_calls = 0
    r = _create(api, **over)
    assert r.status_code == status, r.text
    assert r.json()["error"]["code"] == code
    assert api.transport.sync_calls <= 1  # at most the sync-before; never a sync-after
    assert _count(api) == before


def test_create_note_refuses_duplicate_first_field_unless_allowed(api):
    assert _create(api).status_code == 201
    r = _create(api)
    assert r.status_code == 409 and r.json()["error"]["code"] == "duplicate_note"
    assert _create(api, allow_duplicate=True).status_code == 201


def test_create_note_sync_before_failure_creates_nothing(api):
    before = _count(api)
    api.transport.fail_on_calls = {1}
    assert _create(api).status_code == 502
    api.transport.fail_on_calls = set()
    assert _count(api) == before


def test_create_note_reports_unconfirmed_when_sync_after_fails(api):
    api.transport.fail_on_calls = {2}
    r = _create(api)
    assert r.status_code == 502
    err = r.json()["error"]
    assert err["details"]["local_change_applied"] is True
    assert err["details"]["server_confirmed"] is False
    assert api.get("/v2/health").json()["sync_state"] == "pending"


def test_create_note_never_reports_success_when_server_did_not_take_it(api):
    api.transport.drop_changes = True
    r = _create(api)
    assert r.status_code == 502
    assert r.json()["error"]["details"]["reason"] == "change_not_detected"


@pytest.mark.parametrize("required", [FULL_DOWNLOAD, FULL_UPLOAD])
def test_create_note_fails_closed_on_full_sync(api, required):
    before = _count(api)
    api.transport.responses = [required]
    r = _create(api)
    assert r.status_code == 409 and r.json()["error"]["code"] == "full_sync_required"
    assert _count(api) == before


# ---- patch preconditions -----------------------------------------------------------


def test_patch_with_matching_expected_revision_succeeds_and_returns_new_revision(api):
    nid = api.fx.basic_note_id
    rev = _note(api, nid)["revision"]
    r = api.patch(f"/v2/notes/{nid}", {"fields": {"Back": "novo"}, "expected_revision": rev})
    assert r.status_code == 200, r.text
    assert r.json()["revision"] == _note(api, nid)["revision"] != rev


def test_patch_with_stale_revision_is_409_and_writes_nothing(api):
    nid = api.fx.basic_note_id
    stale = _note(api, nid)["revision"]

    def other_client(col):  # another client changed the note and the sync-before pulls it in
        note = col.get_note(int(nid))
        note["Back"] = "REMOTE"
        col.update_note(note)

    api.transport.on_sync = [other_client]
    api.transport.sync_calls = 0
    r = api.patch(f"/v2/notes/{nid}", {"fields": {"Back": "MINE"}, "expected_revision": stale})
    assert r.status_code == 409, r.text
    err = r.json()["error"]
    assert err["code"] == "stale_revision"
    assert err["details"]["current_revision"] == _note(api, nid)["revision"]
    assert {"name": "Back", "value": "REMOTE"} in _note(api, nid)["fields"]
    assert api.transport.sync_calls == 1  # sync-before only: no write, no sync-after


def test_patch_without_expected_revision_keeps_working(api):
    r = api.patch(f"/v2/notes/{api.fx.basic_note_id}", {"add_tags": ["x"]})
    assert r.status_code == 200 and "revision" in r.json()


@pytest.mark.parametrize("bad", ["", "abc", "r1-xyz", "r1-" + "g" * 32, 5])
def test_patch_rejects_malformed_expected_revision(api, bad):
    r = api.patch(
        f"/v2/notes/{api.fx.basic_note_id}", {"fields": {"Back": "x"}, "expected_revision": bad}
    )
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_request"


# ---- delete notes ----------------------------------------------------------------------


def _del_item(api, nid, **over):
    n = _note(api, nid)
    item = {
        "note_id": nid,
        "expected_card_ids": n["card_ids"],
        "expected_revision": n["revision"],
    }
    item.update(over)
    return item


def _delete(api, *items):
    return api.post("/v2/notes/delete", {"notes": list(items)})


def test_delete_note_removes_note_and_all_derived_cards(api):
    nid = api.fx.reversed_note_id
    item = _del_item(api, nid)
    assert len(item["expected_card_ids"]) == 2
    api.transport.sync_calls = 0
    r = _delete(api, item)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["deleted"] == [
        {"note_id": nid, "card_ids": sorted(item["expected_card_ids"])}
    ]
    assert body["sync"] == {"before": "ok", "after": "ok"}
    assert api.transport.sync_calls == 2
    assert api.get(f"/v2/notes/{nid}").status_code == 404
    for cid in item["expected_card_ids"]:
        assert api.get(f"/v2/cards/{cid}").status_code == 404
    assert api.get(f"/v2/notes/{api.fx.basic_note_id}").status_code == 200


def test_delete_expected_card_ids_order_does_not_matter(api):
    nid = api.fx.reversed_note_id
    item = _del_item(api, nid)
    item["expected_card_ids"] = list(reversed(item["expected_card_ids"]))
    assert _delete(api, item).status_code == 200


def test_delete_wrong_expected_card_ids_is_409_and_deletes_nothing(api):
    nid = api.fx.reversed_note_id
    item = _del_item(api, nid)
    item["expected_card_ids"] = item["expected_card_ids"][:1]  # missing a derived card
    api.transport.sync_calls = 0
    r = _delete(api, item)
    assert r.status_code == 409 and r.json()["error"]["code"] == "card_ids_mismatch"
    assert api.get(f"/v2/notes/{nid}").status_code == 200
    assert api.transport.sync_calls == 1


def test_delete_unexpected_extra_card_id_is_409(api):
    nid = api.fx.basic_note_id
    item = _del_item(api, nid)
    item["expected_card_ids"] = item["expected_card_ids"] + ["1234567890123"]
    r = _delete(api, item)
    assert r.status_code == 409 and r.json()["error"]["code"] == "card_ids_mismatch"
    assert api.get(f"/v2/notes/{nid}").status_code == 200


def test_delete_stale_revision_is_409_and_deletes_nothing(api):
    nid = api.fx.basic_note_id
    item = _del_item(api, nid)
    api.patch(f"/v2/notes/{nid}", {"fields": {"Back": "mudou depois da leitura"}})
    api.transport.sync_calls = 0
    r = _delete(api, item)
    assert r.status_code == 409 and r.json()["error"]["code"] == "stale_revision"
    assert api.get(f"/v2/notes/{nid}").status_code == 200
    assert api.transport.sync_calls == 1


def test_delete_batch_is_all_or_nothing(api):
    good = _del_item(api, api.fx.basic_note_id)
    bad = _del_item(api, api.fx.cloze_note_id, expected_revision="r1-" + "0" * 32)
    r = _delete(api, good, bad)
    assert r.status_code == 409
    assert api.get(f"/v2/notes/{api.fx.basic_note_id}").status_code == 200
    assert api.get(f"/v2/notes/{api.fx.cloze_note_id}").status_code == 200


def test_delete_batch_limit_is_ten(api):
    ids = [api.add_note(f"n{i}") for i in range(11)]
    items = [_del_item(api, i) for i in ids]
    assert _delete(api, *items).status_code == 422
    assert _delete(api, *items[:10]).status_code == 200
    assert api.get(f"/v2/notes/{ids[10]}").status_code == 200


@pytest.mark.parametrize(
    "mutate",
    [
        lambda i: i.pop("expected_card_ids"),
        lambda i: i.pop("expected_revision"),
        lambda i: i.update(expected_card_ids=[]),
        lambda i: i.update(expected_revision="nope"),
        lambda i: i.update(extra=1),
    ],
)
def test_delete_requires_both_preconditions(api, mutate):
    item = _del_item(api, api.fx.basic_note_id)
    mutate(item)
    r = _delete(api, item)
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_request"
    assert api.get(f"/v2/notes/{api.fx.basic_note_id}").status_code == 200


def test_delete_rejects_empty_batch_duplicates_and_malformed_ids(api):
    assert api.post("/v2/notes/delete", {"notes": []}).status_code == 422
    item = _del_item(api, api.fx.basic_note_id)
    r = _delete(api, item, dict(item))
    assert r.status_code == 422 and r.json()["error"]["code"] == "duplicate_ids"
    r = _delete(api, dict(item, note_id="12ab"))
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_id"
    r = _delete(api, dict(item, expected_card_ids=["x1"]))
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_id"


def test_delete_missing_note_is_404(api):
    item = _del_item(api, api.fx.basic_note_id)
    r = _delete(api, dict(item, note_id="1234567890123"))
    assert r.status_code == 404 and r.json()["error"]["code"] == "note_not_found"


def test_delete_fails_closed_on_full_sync_and_keeps_note(api):
    item = _del_item(api, api.fx.basic_note_id)
    api.transport.responses = [FULL_UPLOAD]
    r = _delete(api, item)
    assert r.status_code == 409 and r.json()["error"]["code"] == "full_sync_required"
    assert api.get(f"/v2/notes/{api.fx.basic_note_id}").status_code == 200


def test_delete_reports_unconfirmed_when_server_does_not_take_it(api):
    item = _del_item(api, api.fx.basic_note_id)
    api.transport.drop_changes = True
    r = _delete(api, item)
    assert r.status_code == 502
    assert r.json()["error"]["details"]["server_confirmed"] is False
    assert api.get("/v2/health").json()["sync_state"] == "pending"


def test_there_is_no_generic_card_delete_route(api):
    assert api.delete(f"/v2/cards/{api.get(f'/v2/notes/{api.fx.basic_note_id}').json()['card_ids'][0]}").status_code in {404, 405}
    assert api.delete(f"/v2/notes/{api.fx.basic_note_id}").status_code in {404, 405}
