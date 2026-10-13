"""Tags, decks and card moves."""

from __future__ import annotations

import pytest
from tests.fakes import FULL_DOWNLOAD


def _note(api, nid):
    return api.get(f"/v2/notes/{nid}").json()


def _deck(api, name):
    items = api.get("/v2/decks", params={"limit": 200}).json()["items"]
    return next((d for d in items if d["name"] == name), None)


def _tags(api, **params):
    return api.get("/v2/tags", params=params).json()


# ---- tags ------------------------------------------------------------------------------


def test_list_tags_sorted_paginated_and_prefix_filtered(api):
    api.add_note("t", tags=["endocrino", "zeta"])
    body = _tags(api)
    assert body["items"] == ["alpha", "endo", "endocrino", "zeta"]
    assert body["total"] == 4 and body["has_more"] is False
    assert _tags(api, prefix="endo")["items"] == ["endo", "endocrino"]
    page = _tags(api, limit=2, offset=1)
    assert page["items"] == ["endo", "endocrino"] and page["has_more"] is True


def test_list_tags_rejects_bad_paging(api):
    assert api.get("/v2/tags", params={"limit": 0}).status_code == 422
    assert api.get("/v2/tags", params={"limit": 10_000}).status_code == 422


def _rename(api, old, new, count, **over):
    body = {"old": old, "new": new, "expected_note_count": count}
    body.update(over)
    return api.post("/v2/tags/rename", body)


def test_rename_tag_renames_on_every_note_including_children(api):
    n1 = api.add_note("a", tags=["proj"])
    n2 = api.add_note("b", tags=["proj::sub", "keep"])
    n3 = api.add_note("c", tags=["project"])  # NOT a child: must stay untouched
    api.transport.sync_calls = 0
    r = _rename(api, "proj", "work", 2)
    assert r.status_code == 200, r.text
    assert r.json()["affected_note_count"] == 2 and r.json()["dry_run"] is False
    assert api.transport.sync_calls == 2
    assert _note(api, n1)["tags"] == ["work"]
    assert sorted(_note(api, n2)["tags"]) == ["keep", "work::sub"]
    assert _note(api, n3)["tags"] == ["project"]


def test_rename_tag_dry_run_reports_count_and_writes_nothing(api):
    n1 = api.add_note("a", tags=["proj"])
    r = api.post("/v2/tags/rename", {"old": "proj", "new": "work", "dry_run": True})
    assert r.status_code == 200
    assert r.json() == {
        "old": "proj",
        "new": "work",
        "affected_note_count": 1,
        "dry_run": True,
        "sync": None,
    }
    assert _note(api, n1)["tags"] == ["proj"]
    assert api.transport.sync_calls <= 1


def test_rename_tag_requires_expected_count_and_refuses_mismatch(api):
    n1 = api.add_note("a", tags=["proj"])
    r = api.post("/v2/tags/rename", {"old": "proj", "new": "work"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "expected_count_required"
    r = _rename(api, "proj", "work", 5)
    assert r.status_code == 409 and r.json()["error"]["code"] == "stale_count"
    assert r.json()["error"]["details"]["affected_note_count"] == 1
    assert _note(api, n1)["tags"] == ["proj"]


@pytest.mark.parametrize(
    ("old", "new", "status", "code"),
    [
        ("nao_existe", "x", 404, "tag_not_found"),
        ("alpha", "alpha", 422, "invalid_request"),
        ("alpha", "a*", 422, "invalid_request"),
        ("al*", "x", 422, "invalid_request"),
        ("alpha", "two words", 422, "invalid_request"),
        ("alpha", "", 422, "invalid_request"),
        ("alpha", "::x", 422, "invalid_tag"),
        ("alpha", "x::", 422, "invalid_tag"),
        ("alpha", "x::::y", 422, "invalid_tag"),
    ],
)
def test_rename_tag_rejects_bad_input(api, old, new, status, code):
    r = _rename(api, old, new, 1)
    assert r.status_code == status, r.text
    assert r.json()["error"]["code"] == code


def test_rename_tag_can_merge_into_an_existing_tag(api):
    n1 = api.add_note("a", tags=["one"])
    n2 = api.add_note("b", tags=["two"])
    assert _rename(api, "one", "two", 1).status_code == 200
    assert _note(api, n1)["tags"] == ["two"] and _note(api, n2)["tags"] == ["two"]


def test_rename_tag_guard_limits_notes_affected(api, monkeypatch):
    monkeypatch.setattr("anki_api_v2.service.MAX_TAG_OP_NOTES", 1)
    api.add_note("a", tags=["big"])
    api.add_note("b", tags=["big"])
    r = _rename(api, "big", "small", 2)
    assert r.status_code == 413 and r.json()["error"]["code"] == "too_many_notes"
    assert "big" in _tags(api)["items"]


def test_delete_tag_removes_tag_from_notes_but_never_the_notes_or_cards(api):
    n1 = api.add_note("a", tags=["gone", "stay"])
    n2 = api.add_note("b", tags=["gone::child"])
    n3 = api.add_note("c", tags=["gonexx"])
    notes_before = api.get("/v2/health").json()
    r = api.post("/v2/tags/delete", {"tag": "gone", "expected_note_count": 2})
    assert r.status_code == 200, r.text
    assert r.json()["affected_note_count"] == 2
    assert _note(api, n1)["tags"] == ["stay"]
    assert _note(api, n2)["tags"] == []
    assert _note(api, n3)["tags"] == ["gonexx"]
    assert "gone" not in _tags(api)["items"] and "gone::child" not in _tags(api)["items"]
    after = api.get("/v2/health").json()
    assert (after["notes"], after["cards"]) == (notes_before["notes"], notes_before["cards"])


def test_delete_tag_requires_count_refuses_stale_count_and_supports_dry_run(api):
    api.add_note("a", tags=["gone"])
    r = api.post("/v2/tags/delete", {"tag": "gone"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "expected_count_required"
    r = api.post("/v2/tags/delete", {"tag": "gone", "expected_note_count": 9})
    assert r.status_code == 409 and r.json()["error"]["code"] == "stale_count"
    dry = api.post("/v2/tags/delete", {"tag": "gone", "dry_run": True}).json()
    assert dry["affected_note_count"] == 1 and dry["dry_run"] is True
    assert "gone" in _tags(api)["items"]


def test_delete_tag_guard_unknown_tag_and_wildcards(api, monkeypatch):
    assert api.post("/v2/tags/delete", {"tag": "nope", "expected_note_count": 0}).status_code == 404
    assert api.post("/v2/tags/delete", {"tag": "al*", "expected_note_count": 1}).status_code == 422
    monkeypatch.setattr("anki_api_v2.service.MAX_TAG_OP_NOTES", 1)
    api.add_note("a", tags=["big"])
    api.add_note("b", tags=["big"])
    r = api.post("/v2/tags/delete", {"tag": "big", "expected_note_count": 2})
    assert r.status_code == 413 and "big" in _tags(api)["items"]


def test_tag_writes_fail_closed_on_full_sync(api):
    api.transport.responses = [FULL_DOWNLOAD]
    r = _rename(api, "alpha", "beta", 1)
    assert r.status_code == 409 and r.json()["error"]["code"] == "full_sync_required"
    assert "alpha" in _tags(api)["items"]


def test_tag_write_not_confirmed_is_never_success(api):
    api.transport.drop_changes = True
    r = _rename(api, "alpha", "beta", 1)
    assert r.status_code == 502 and r.json()["error"]["details"]["server_confirmed"] is False


# ---- decks -----------------------------------------------------------------------------


def test_create_deck_creates_hierarchy_and_returns_201(api):
    api.transport.sync_calls = 0
    r = api.post("/v2/decks", {"name": "Novo::Sub::Fundo"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["created"] is True and body["name"] == "Novo::Sub::Fundo"
    assert isinstance(body["deck_id"], str) and api.transport.sync_calls == 2
    assert _deck(api, "Novo") and _deck(api, "Novo::Sub")


def test_create_deck_is_idempotent(api):
    first = api.post("/v2/decks", {"name": "Once"}).json()
    r = api.post("/v2/decks", {"name": "Once"})
    assert r.status_code == 200
    assert r.json() == {**first, "created": False, "sync": None}
    r = api.post("/v2/decks", {"name": "once"})  # Anki names are case-insensitive
    assert r.status_code == 200 and r.json()["deck_id"] == first["deck_id"]


@pytest.mark.parametrize(
    "name", ["", "   ", "A::", "::A", "A::::B", "A:: ::B", "a\nb", "x" * 201, "Default::"]
)
def test_create_deck_rejects_names_anki_would_silently_rewrite(api, name):
    r = api.post("/v2/decks", {"name": name})
    assert r.status_code == 422, r.text
    assert r.json()["error"]["code"] in {"invalid_deck_name", "invalid_request"}
    assert _deck(api, "A") is None and _deck(api, "A::blank") is None


def test_rename_deck_moves_cards_and_subdecks_natively(api):
    api.post("/v2/decks", {"name": "Medicina::Cardio::Sub"})
    cardio = _deck(api, "Medicina::Cardio")
    cards_before = cardio["card_count"]
    r = api.patch(f"/v2/decks/{cardio['deck_id']}", {"name": "Medicina::Cardiologia"})
    assert r.status_code == 200, r.text
    assert r.json()["old_name"] == "Medicina::Cardio" and r.json()["name"] == "Medicina::Cardiologia"
    assert _deck(api, "Medicina::Cardio") is None
    renamed = _deck(api, "Medicina::Cardiologia")
    assert renamed["deck_id"] == cardio["deck_id"] and renamed["card_count"] == cards_before
    assert _deck(api, "Medicina::Cardiologia::Sub")
    cloze = _note(api, api.fx.cloze_note_id)
    assert cloze["deck_names"] == ["Medicina::Cardiologia"]


def test_rename_deck_refuses_existing_target_instead_of_silent_plus(api):
    cardio = _deck(api, "Medicina::Cardio")
    r = api.patch(f"/v2/decks/{cardio['deck_id']}", {"name": "Medicina::Endocrino"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "deck_exists"
    assert _deck(api, "Medicina::Cardio") and not _deck(api, "Medicina::Endocrino+")


@pytest.mark.parametrize(
    ("name", "status", "code"),
    [
        ("Medicina::Cardio::Dentro", 422, "invalid_deck_move"),
        ("A::", 422, "invalid_deck_name"),
        ("", 422, "invalid_request"),
    ],
)
def test_rename_deck_rejects_invalid_targets(api, name, status, code):
    cardio = _deck(api, "Medicina::Cardio")
    r = api.patch(f"/v2/decks/{cardio['deck_id']}", {"name": name})
    assert r.status_code == status and r.json()["error"]["code"] == code


def test_rename_deck_protects_default_unknown_and_stale_name(api):
    r = api.patch(f"/v2/decks/{api.fx.default_deck_id}", {"name": "Outro"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "deck_protected"
    r = api.patch("/v2/decks/1234567890123", {"name": "Outro"})
    assert r.status_code == 404 and r.json()["error"]["code"] == "deck_not_found"
    r = api.patch("/v2/decks/abc", {"name": "Outro"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_id"
    cardio = _deck(api, "Medicina::Cardio")
    r = api.patch(
        f"/v2/decks/{cardio['deck_id']}", {"name": "Medicina::C2", "expected_name": "Errado"}
    )
    assert r.status_code == 409 and r.json()["error"]["code"] == "stale_deck"


def test_delete_empty_deck_succeeds(api):
    created = api.post("/v2/decks", {"name": "Vazio"}).json()
    api.transport.sync_calls = 0
    r = api.delete(f"/v2/decks/{created['deck_id']}?expected_name=Vazio")
    assert r.status_code == 200, r.text
    assert r.json()["deleted"] is True and r.json()["card_count"] == 0
    assert api.transport.sync_calls == 2
    assert _deck(api, "Vazio") is None


def test_delete_non_empty_deck_is_refused_with_card_count_and_moves_nothing(api):
    endo = _deck(api, "Medicina::Endocrino")
    assert endo["card_count"] == 3
    api.transport.sync_calls = 0
    r = api.delete(f"/v2/decks/{endo['deck_id']}?expected_name=Medicina::Endocrino")
    assert r.status_code == 409
    err = r.json()["error"]
    assert err["code"] == "deck_not_empty" and err["details"]["card_count"] == 3
    assert _deck(api, "Medicina::Endocrino")["card_count"] == 3
    assert _note(api, api.fx.basic_note_id)["deck_names"] == ["Medicina::Endocrino"]
    assert api.transport.sync_calls == 1


def test_delete_parent_deck_counts_cards_in_subdecks(api):
    parent = _deck(api, "Medicina")
    assert parent["card_count"] == 0
    r = api.delete(f"/v2/decks/{parent['deck_id']}?expected_name=Medicina")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "deck_not_empty"
    assert r.json()["error"]["details"]["card_count"] == 4


def test_delete_deck_with_empty_subdecks_is_refused(api):
    api.post("/v2/decks", {"name": "P::Q"})
    p = _deck(api, "P")
    r = api.delete(f"/v2/decks/{p['deck_id']}?expected_name=P")
    assert r.status_code == 409 and r.json()["error"]["code"] == "deck_has_subdecks"
    assert _deck(api, "P::Q")


def test_delete_deck_requires_expected_name_and_protects_default(api):
    created = api.post("/v2/decks", {"name": "Vazio"}).json()
    assert api.delete(f"/v2/decks/{created['deck_id']}").status_code == 422
    r = api.delete(f"/v2/decks/{created['deck_id']}?expected_name=Outro")
    assert r.status_code == 409 and r.json()["error"]["code"] == "stale_deck"
    r = api.delete(f"/v2/decks/{api.fx.default_deck_id}?expected_name=Default")
    assert r.status_code == 409 and r.json()["error"]["code"] == "deck_protected"
    assert api.delete("/v2/decks/1234567890123?expected_name=x").status_code == 404
    assert _deck(api, "Vazio")


def test_deck_writes_fail_closed_on_full_sync(api):
    api.transport.responses = [FULL_DOWNLOAD]
    r = api.post("/v2/decks", {"name": "Nao"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "full_sync_required"
    assert _deck(api, "Nao") is None


# ---- move cards ------------------------------------------------------------------------

SCHED = "select type, queue, due, ivl, factor, reps, lapses, left, odid from cards where id = ?"


def _set_schedule(api, card_id):
    def job(col):
        col.db.execute(
            "update cards set type=2, queue=2, due=100, ivl=7, factor=2500, reps=3, lapses=1 "
            "where id = ?",
            int(card_id),
        )

    api.run(job)


def _schedule(api, card_id):
    return api.run(lambda col: col.db.first(SCHED, int(card_id)))


def test_move_card_changes_only_the_deck_and_preserves_schedule_and_note(api):
    nid = api.fx.basic_note_id
    before = _note(api, nid)
    cid = before["card_ids"][0]
    _set_schedule(api, cid)
    sched = _schedule(api, cid)
    api.transport.sync_calls = 0
    r = api.post("/v2/cards/move", {"card_ids": [cid], "target_deck": "Medicina::Cardio"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["target_deck"] == {"deck_id": api.fx.cardio_deck_id, "name": "Medicina::Cardio"}
    assert body["moved"] == 1 and body["unchanged"] == 0
    assert body["items"] == [
        {
            "card_id": cid,
            "old_deck_id": api.fx.endo_deck_id,
            "old_deck_name": "Medicina::Endocrino",
            "new_deck_id": api.fx.cardio_deck_id,
            "new_deck_name": "Medicina::Cardio",
            "moved": True,
        }
    ]
    assert body["sync"] == {"before": "ok", "after": "ok"} and api.transport.sync_calls == 2
    assert api.get(f"/v2/cards/{cid}").json()["deck_name"] == "Medicina::Cardio"
    assert _schedule(api, cid) == sched
    after = _note(api, nid)
    assert after["revision"] == before["revision"]
    assert after["fields"] == before["fields"] and after["tags"] == before["tags"]
    assert after["deck_names"] == ["Medicina::Cardio"]


def test_move_several_cards_and_resolve_target_by_id(api):
    cids = _note(api, api.fx.reversed_note_id)["card_ids"]
    r = api.post("/v2/cards/move", {"card_ids": cids, "target_deck": api.fx.cardio_deck_id})
    assert r.status_code == 200 and r.json()["moved"] == 2
    assert _note(api, api.fx.reversed_note_id)["deck_ids"] == [api.fx.cardio_deck_id]


def test_move_is_all_or_nothing_when_a_card_is_missing(api):
    cid = _note(api, api.fx.basic_note_id)["card_ids"][0]
    r = api.post(
        "/v2/cards/move", {"card_ids": [cid, "1234567890123"], "target_deck": "Medicina::Cardio"}
    )
    assert r.status_code == 404 and r.json()["error"]["code"] == "card_not_found"
    assert api.get(f"/v2/cards/{cid}").json()["deck_name"] == "Medicina::Endocrino"


def test_move_cards_already_in_target_are_reported_unchanged(api):
    cid = _note(api, api.fx.basic_note_id)["card_ids"][0]
    r = api.post("/v2/cards/move", {"card_ids": [cid], "target_deck": "Medicina::Endocrino"})
    assert r.status_code == 200
    assert r.json()["moved"] == 0 and r.json()["unchanged"] == 1
    assert r.json()["items"][0]["moved"] is False


@pytest.mark.parametrize(
    ("body", "status", "code"),
    [
        ({"card_ids": [], "target_deck": "Default"}, 422, "invalid_request"),
        ({"card_ids": ["x"], "target_deck": "Default"}, 422, "invalid_id"),
        ({"card_ids": ["0"], "target_deck": "Default"}, 422, "invalid_id"),
        ({"card_ids": ["5", "5"], "target_deck": "Default"}, 422, "duplicate_ids"),
        ({"card_ids": [str(i) for i in range(1, 202)], "target_deck": "Default"}, 422, "too_many_cards"),
        ({"card_ids": ["5"], "target_deck": ""}, 422, "invalid_request"),
        ({"card_ids": ["5"]}, 422, "invalid_request"),
        ({"card_ids": ["5"], "target_deck": "Default", "extra": 1}, 422, "invalid_request"),
    ],
)
def test_move_cards_validates_input_before_any_sync(api, body, status, code):
    api.transport.sync_calls = 0
    r = api.post("/v2/cards/move", body)
    assert r.status_code == status, r.text
    assert r.json()["error"]["code"] == code
    assert api.transport.sync_calls == 0


def test_move_cards_unknown_target_deck_is_404_and_moves_nothing(api):
    cid = _note(api, api.fx.basic_note_id)["card_ids"][0]
    r = api.post("/v2/cards/move", {"card_ids": [cid], "target_deck": "Nao::Existe"})
    assert r.status_code == 404 and r.json()["error"]["code"] == "deck_not_found"
    assert api.get(f"/v2/cards/{cid}").json()["deck_name"] == "Medicina::Endocrino"


def test_move_cards_fails_closed_on_full_sync(api):
    cid = _note(api, api.fx.basic_note_id)["card_ids"][0]
    api.transport.responses = [FULL_DOWNLOAD]
    r = api.post("/v2/cards/move", {"card_ids": [cid], "target_deck": "Default"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "full_sync_required"
    assert api.get(f"/v2/cards/{cid}").json()["deck_name"] == "Medicina::Endocrino"


def test_move_cards_not_confirmed_is_never_success(api):
    cid = _note(api, api.fx.basic_note_id)["card_ids"][0]
    api.transport.drop_changes = True
    r = api.post("/v2/cards/move", {"card_ids": [cid], "target_deck": "Default"})
    assert r.status_code == 502 and r.json()["error"]["details"]["server_confirmed"] is False
