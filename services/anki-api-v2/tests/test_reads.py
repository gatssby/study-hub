from __future__ import annotations

from tests.fakes import FULL_DOWNLOAD


def test_decks_lists_all_decks_with_string_ids(api):
    r = api.get("/v2/decks")
    assert r.status_code == 200
    body = r.json()
    names = {d["name"] for d in body["items"]}
    assert {"Default", "Medicina", "Medicina::Endocrino", "Medicina::Cardio"} <= names
    assert all(isinstance(d["deck_id"], str) for d in body["items"])
    assert body["total"] == len(body["items"])


def test_decks_root_filter_returns_subtree_only(api):
    body = api.get("/v2/decks", params={"root": "Medicina"}).json()
    names = {d["name"] for d in body["items"]}
    assert names == {"Medicina", "Medicina::Endocrino", "Medicina::Cardio"}


def test_decks_limit_and_offset_paginate(api):
    body = api.get("/v2/decks", params={"limit": 2, "offset": 0}).json()
    assert len(body["items"]) == 2
    assert body["limit"] == 2
    assert body["has_more"] is True


def test_decks_rejects_limit_above_maximum(api):
    r = api.get("/v2/decks", params={"limit": 10_000})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_request"


def test_decks_rejects_zero_limit(api):
    assert api.get("/v2/decks", params={"limit": 0}).status_code == 422


def test_get_note_returns_fields_tags_cards_and_decks(api):
    fx = api.fx
    r = api.get(f"/v2/notes/{fx.basic_note_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["note_id"] == fx.basic_note_id
    assert body["note_type"]["name"] == "Basic"
    assert body["fields"] == [
        {"name": "Front", "value": "Tireoide?"},
        {"name": "Back", "value": "TSH"},
    ]
    assert sorted(body["tags"]) == ["alpha", "endo"]
    assert len(body["card_ids"]) == 1 and isinstance(body["card_ids"][0], str)
    assert body["deck_ids"] == [fx.endo_deck_id]


def test_get_note_missing_returns_note_not_found(api):
    r = api.get("/v2/notes/1234567890123")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "note_not_found"


def test_get_note_rejects_non_numeric_id(api):
    r = api.get("/v2/notes/abc")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_id"


def test_get_card_returns_note_and_deck_context(api):
    fx = api.fx
    note = api.get(f"/v2/notes/{fx.basic_note_id}").json()
    card_id = note["card_ids"][0]
    r = api.get(f"/v2/cards/{card_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["card_id"] == card_id
    assert body["note_id"] == fx.basic_note_id
    assert body["deck_id"] == fx.endo_deck_id
    assert body["deck_name"] == "Medicina::Endocrino"
    assert body["template_name"] == "Card 1"
    assert body["note_type"]["name"] == "Basic"
    assert "question" in body and "answer" in body


def test_get_card_missing_returns_card_not_found(api):
    r = api.get("/v2/cards/1234567890123")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "card_not_found"


def test_search_notes_by_tag(api):
    r = api.post("/v2/search", json={"query": "tag:endo", "kind": "notes"})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["note_id"] == api.fx.basic_note_id
    assert body["has_more"] is False


def test_search_cards_by_deck_counts_every_generated_card(api):
    body = api.post(
        "/v2/search", json={"query": "deck:Medicina::Endocrino", "kind": "cards"}
    ).json()
    assert body["total"] == 3
    assert all(isinstance(i["card_id"], str) for i in body["items"])


def test_search_respects_limit_and_offset(api):
    body = api.post(
        "/v2/search",
        json={"query": "deck:Medicina::Endocrino", "kind": "cards", "limit": 2, "offset": 2},
    ).json()
    assert body["total"] == 3
    assert len(body["items"]) == 1
    assert body["has_more"] is False


def test_search_rejects_invalid_query_syntax(api):
    r = api.post("/v2/search", json={"query": 'tag:"unclosed', "kind": "notes"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_search"


def test_search_rejects_empty_query_to_avoid_full_scans(api):
    r = api.post("/v2/search", json={"query": "", "kind": "notes"})
    assert r.status_code == 422


def test_search_rejects_unknown_kind_and_oversized_limit(api):
    assert api.post("/v2/search", json={"query": "x", "kind": "decks"}).status_code == 422
    assert (
        api.post(
            "/v2/search", json={"query": "tag:endo", "kind": "notes", "limit": 101}
        ).status_code
        == 422
    )


def test_reads_trigger_sync_only_when_freshness_ttl_expired(api):
    api.get("/v2/decks")
    assert api.transport.sync_calls == 1
    api.clock.advance(10)
    api.get("/v2/decks")
    assert api.transport.sync_calls == 1
    api.clock.advance(25)
    api.get("/v2/decks")
    assert api.transport.sync_calls == 2


def test_reads_fail_closed_when_collection_needs_full_sync(api):
    api.transport.responses = [FULL_DOWNLOAD]
    r = api.get("/v2/decks")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "full_sync_required"


def test_media_count_in_health_matches_directory(api):
    assert api.get("/v2/health").json()["media_count"] == 1
