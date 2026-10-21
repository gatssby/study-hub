import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fo_hub.api import FO_TOOL_ROUTES, create_app  # noqa: E402
from fo_hub.store import FOStore, lesson_id_for  # noqa: E402

LID = lesson_id_for("C", "M1", None)


@pytest.fixture
def client(tmp_path):
    s = FOStore(tmp_path / "fo.db")
    s.sync_lessons([{"course_id": "C", "media_id": "M1", "subject": "Cardio", "title": "IC",
                     "video_url": "u", "duration_s": 60}])
    s.upsert_material({"material_id": "m1", "subject": "Cardio", "title": "Resumo",
                       "material_type": "pdf"})
    s.set_pdf_pages("m1", ["p1 text", "p2 text"])
    s.add_transcript(LID, 1, [{"start": 0, "end": 3, "text": "fração de ejeção"}], model="x",
                     corpus="generated_v2", validated=True)
    return TestClient(create_app(tmp_path / "fo.db"))


def test_exactly_seven_get_tool_routes(client):
    paths = {r.path for r in client.app.routes if getattr(r, "methods", None)
             and r.path.startswith("/fo/")}
    assert paths == set(FO_TOOL_ROUTES.values()) and len(paths) == 7
    for r in client.app.routes:
        if r.path.startswith("/fo/"):
            assert r.methods == {"GET"}


def test_endpoints(client):
    assert client.get("/fo/lessons", params={"subject": "cardio"}).json()["items"][0][
        "lesson_id"] == LID
    assert client.get(f"/fo/lessons/{LID}").json()["version"] == 1
    assert client.get("/fo/lessons/nope").status_code == 404
    assert client.get("/fo/materials", params={"type": "pdf"}).json()["items"][0][
        "material_id"] == "m1"
    pdf = client.get("/fo/materials/m1/pdf-text", params={"page_start": 2}).json()
    assert pdf["pages"][0]["citation"] == "Resumo, p. 2 [m1#p2]"
    assert client.get("/fo/transcripts", params={"q": "ejeção"}).json()["items"][0][
        "lesson_id"] == LID
    assert client.get(f"/fo/transcripts/{LID}").json()["segments"][0]["start"] == 0
    assert client.get("/fo/sync-status").json()["transcripts_validated"] == 1


def test_writes_rejected(client):
    assert client.post("/fo/lessons").status_code == 405
    assert client.get("/fo/lessons", params={"limit": 10000}).status_code == 422
