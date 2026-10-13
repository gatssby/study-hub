"""contracts/openapi/anki-api-v2.openapi.json must be exactly what the app serves."""

from __future__ import annotations

import json
from pathlib import Path

CONTRACT = Path(__file__).resolve().parents[3] / "contracts" / "openapi" / "anki-api-v2.openapi.json"

EXPECTED_OPERATIONS = {
    ("get", "/v2/health"), ("post", "/v2/sync"), ("get", "/v2/decks"), ("post", "/v2/decks"),
    ("patch", "/v2/decks/{deck_id}"), ("delete", "/v2/decks/{deck_id}"),
    ("get", "/v2/notes/{note_id}"), ("patch", "/v2/notes/{note_id}"), ("post", "/v2/notes"),
    ("post", "/v2/notes/delete"), ("get", "/v2/cards/{card_id}"), ("post", "/v2/cards/move"),
    ("post", "/v2/search"), ("get", "/v2/media/{filename}"), ("get", "/v2/note-types"),
    ("get", "/v2/note-types/{note_type_id}"), ("get", "/v2/tags"),
    ("post", "/v2/tags/rename"), ("post", "/v2/tags/delete"),
}


def test_committed_contract_matches_the_running_app(api):
    served = api.client.app.openapi()
    assert json.loads(CONTRACT.read_text(encoding="utf-8")) == served


def test_contract_has_exactly_the_approved_operations():
    spec = json.loads(CONTRACT.read_text(encoding="utf-8"))
    found = {(m, p) for p, item in spec["paths"].items() for m in item}
    assert found == EXPECTED_OPERATIONS
