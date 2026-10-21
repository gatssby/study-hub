import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fo_hub.store import FOStore, TranscriptRejected, lesson_id_for  # noqa: E402


def row(**kw):
    base = {
        "course_id": "C1", "media_id": "M1", "item_id": "I1", "subject": "Cardiologia",
        "front": "Clinica", "module": "Mod 1", "title": "Aula 1 - IC",
        "media_type": "video", "video_url": "https://v/1", "duration_s": 600,
    }
    base.update(kw)
    return base


@pytest.fixture
def store(tmp_path):
    return FOStore(tmp_path / "fo.db")


def test_lesson_id_stable_from_course_and_media_not_title():
    a = lesson_id_for("C1", "M1", "I1")
    assert a == lesson_id_for("C1", "M1", "other-item")
    assert a != lesson_id_for("C2", "M1", "I1")
    assert lesson_id_for("C1", "", "I9") != lesson_id_for("C1", "", "I8")


def test_rename_vs_media_change_and_no_delete(store):
    r1 = store.sync_lessons([row(), row(media_id="M2", title="Aula 2")])
    assert r1["created"] == 2
    lid = lesson_id_for("C1", "M1", "I1")
    r2 = store.sync_lessons([row(title="Aula 1 - Insuficiencia")], authoritative=True)
    assert r2 == {"created": 0, "renamed": 1, "media_changed": 0, "unchanged": 0, "missing": 1,
                  "run_id": r2["run_id"]}
    les = store.get_lesson(lid)
    assert les["title"] == "Aula 1 - Insuficiencia" and les["version"] == 1
    r3 = store.sync_lessons([row(title="Aula 1 - Insuficiencia", duration_s=900)])
    assert r3["media_changed"] == 1
    les = store.get_lesson(lid)
    assert les["version"] == 2
    kinds = [r["change_kind"] for r in les["revisions"]]
    assert kinds == ["created", "renamed", "media_changed"]
    gone = store.get_lesson(lesson_id_for("C1", "M2", "I1"))
    assert gone is not None and gone["present"] is False


def test_search_materials_filters_and_injection_safe(store):
    store.upsert_material({"material_id": "m1", "subject": "Cardiologia", "front": "Clinica",
                           "module": "Mod 1", "title": "Resumo IC", "material_type": "pdf"})
    store.upsert_material({"material_id": "m2", "subject": "Pneumo", "front": "Clinica",
                           "module": "Mod 2", "title": "Asma", "material_type": "slides"})
    assert [m["material_id"] for m in store.search_materials(subject="Cardiologia")] == ["m1"]
    assert [m["material_id"] for m in store.search_materials(title="asma")] == ["m2"]
    assert len(store.search_materials(front="Clinica")) == 2
    assert store.search_materials(material_type="pdf")[0]["material_id"] == "m1"
    assert store.search_materials(title="' OR 1=1 --") == []


def test_pdf_text_pages_with_citations(store):
    store.upsert_material({"material_id": "m1", "subject": "S", "title": "Resumo IC",
                           "material_type": "pdf"})
    store.set_pdf_pages("m1", ["pagina um", "pagina dois", "pagina tres"])
    out = store.get_pdf_text("m1", page_start=2, page_end=3)
    assert [p["page"] for p in out["pages"]] == [2, 3]
    assert out["pages"][0]["citation"] == "Resumo IC, p. 2 [m1#p2]"
    assert out["page_count"] == 3


def _seg():
    return [{"start": 0.0, "end": 5.0, "text": "insuficiencia cardiaca"}]


def test_transcripts_only_validated_new_corpus_current_version(store):
    store.sync_lessons([row()])
    lid = lesson_id_for("C1", "M1", "I1")
    with pytest.raises(TranscriptRejected):
        store.add_transcript(lid, 1, _seg(), model="m", corpus="legacy", validated=True)
    with pytest.raises(TranscriptRejected):
        store.add_transcript(lid, 1, _seg(), model="m", corpus="generated_v2", validated=False)
    with pytest.raises(TranscriptRejected):
        store.add_transcript(lid, 7, _seg(), model="m", corpus="generated_v2", validated=True)
    store.add_transcript(lid, 1, _seg(), model="m", corpus="generated_v2", validated=True,
                         qa={"flags": []})
    hits = store.search_transcripts("cardiaca")
    assert hits[0]["lesson_id"] == lid and hits[0]["start"] == 0.0
    assert store.get_transcript(lid)["segments"][0]["text"] == "insuficiencia cardiaca"
    store.sync_lessons([row(video_url="https://v/new")])  # version 2 -> transcript stale
    assert store.get_transcript(lid) is None
    assert store.search_transcripts("cardiaca") == []


def test_sync_status_counts(store):
    store.sync_lessons([row(), row(media_id="M2")])
    store.sync_lessons([row()], authoritative=True)
    s = store.sync_status()
    assert s["lessons_total"] == 2 and s["lessons_present"] == 1 and s["lessons_missing"] == 1
    assert s["transcripts_validated"] == 0 and s["last_sync"]["missing"] == 1


def test_readonly_store_cannot_write(store, tmp_path):
    store.sync_lessons([row()])
    ro = FOStore(tmp_path / "fo.db", readonly=True)
    assert ro.list_lessons()[0]["title"] == "Aula 1 - IC"
    with pytest.raises(sqlite3.OperationalError):
        ro.sync_lessons([row(title="x")])


def test_db_path_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDY_HUB_FO_DB", str(tmp_path / "env.db"))
    FOStore.from_env()
    assert (tmp_path / "env.db").exists()
