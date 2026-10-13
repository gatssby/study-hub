"""Media serving limits and MIME, plus cross-cutting sync/security guarantees."""

from __future__ import annotations

import inspect
import pathlib

import anki_api_v2
import pytest

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 16
GIF = b"GIF89a" + b"0" * 16
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"0" * 16
JPEG = b"\xff\xd8\xff\xe0" + b"0" * 16


def _put(api, name, data):
    (api.fx.path.parent / "collection.media" / name).write_bytes(data)


@pytest.mark.parametrize(
    ("name", "data", "mime"),
    [
        ("a.png", PNG, "image/png"),
        ("a.gif", GIF, "image/gif"),
        ("a.webp", WEBP, "image/webp"),
        ("a.jpg", JPEG, "image/jpeg"),
        ("liar.jpg", PNG, "image/png"),  # bytes win over the extension
        ("liar.png", b"<html>not an image</html>", "application/octet-stream"),
        ("noext", PNG, "image/png"),
    ],
)
def test_media_mime_comes_from_the_bytes_not_the_extension(api, name, data, mime):
    _put(api, name, data)
    r = api.get(f"/v2/media/{name}")
    assert r.status_code == 200
    assert r.headers["content-type"].split(";")[0] == mime
    assert r.headers["x-content-type-options"] == "nosniff"


def test_media_non_image_types_keep_their_extension_type_or_octet_stream(api):
    _put(api, "s.mp3", b"ID3" + b"0" * 16)
    _put(api, "d.svg", b"<svg xmlns='http://www.w3.org/2000/svg'/>")
    _put(api, "weird.xyz", b"data")
    assert api.get("/v2/media/s.mp3").headers["content-type"].startswith("audio/")
    assert api.get("/v2/media/d.svg").headers["content-type"].startswith("image/svg")
    assert api.get("/v2/media/weird.xyz").headers["content-type"] == "application/octet-stream"


def test_media_over_the_size_limit_is_refused_without_serving_bytes(api, monkeypatch):
    monkeypatch.setattr("anki_api_v2.media.MAX_MEDIA_BYTES", 10)
    _put(api, "big.png", PNG + b"0" * 100)
    r = api.get("/v2/media/big.png")
    assert r.status_code == 413 and r.json()["error"]["code"] == "media_too_large"
    assert b"PNG" not in r.content


def test_media_at_the_limit_is_still_served(api, monkeypatch):
    monkeypatch.setattr("anki_api_v2.media.MAX_MEDIA_BYTES", len(PNG))
    _put(api, "edge.png", PNG)
    assert api.get("/v2/media/edge.png").status_code == 200


def test_media_directory_is_not_a_file(api):
    (api.fx.path.parent / "collection.media" / "dir.png").mkdir()
    assert api.get("/v2/media/dir.png").status_code == 404


# ---- cross-cutting guarantees ---------------------------------------------------------


def test_api_package_never_contains_a_full_upload_or_download_call():
    for path in pathlib.Path(inspect.getfile(anki_api_v2)).parent.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "full_upload_or_download" not in text, path.name
        assert "upload=True" not in text, path.name


def test_every_write_route_requires_the_bearer_token(api):
    calls = [
        ("post", "/v2/notes", {}),
        ("post", "/v2/notes/delete", {}),
        ("post", "/v2/tags/rename", {}),
        ("post", "/v2/tags/delete", {}),
        ("post", "/v2/decks", {}),
        ("patch", "/v2/decks/1", {}),
        ("delete", "/v2/decks/1?expected_name=x", None),
        ("post", "/v2/cards/move", {}),
        ("get", "/v2/note-types", None),
        ("get", "/v2/tags", None),
    ]
    for method, path, body in calls:
        kwargs = {"json": body} if body is not None else {}
        r = getattr(api.client, method)(path, **kwargs)
        assert r.status_code == 401, (method, path)


@pytest.mark.parametrize("bad_id", ["0", "-1", "1.5", "１２３", "9" * 25, "1e9", " 12"])
def test_malformed_ids_are_rejected_everywhere(api, bad_id):
    for path in (f"/v2/notes/{bad_id}", f"/v2/cards/{bad_id}", f"/v2/note-types/{bad_id}"):
        r = api.get(path)
        assert r.status_code in {404, 422}, path
        if r.status_code == 422:
            assert r.json()["error"]["code"] == "invalid_id"


def test_input_rejected_before_the_collection_causes_no_sync_at_all(api):
    api.transport.sync_calls = 0
    api.post("/v2/cards/move", {"card_ids": ["x"], "target_deck": "Default"})
    api.post("/v2/decks", {"name": "A::"})
    api.post("/v2/notes/delete", {"notes": []})
    assert api.transport.sync_calls == 0


def test_state_rejected_after_sync_before_never_triggers_a_sync_after(api):
    api.transport.sync_calls = 0
    r = api.post(
        "/v2/notes", {"deck": "Default", "note_type": "Basic", "fields": {"Nope": "x"}}
    )
    assert r.status_code == 422
    assert api.transport.sync_calls == 1
