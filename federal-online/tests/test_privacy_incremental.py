"""Checkpoints must cover retired manifest entries and survive partial reviews."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fo_hub.ingest import ingest
from fo_hub.store import FOStore
from fo_hub.pdf_privacy import PRIVACY_POLICY_VERSION


def test_existing_pages_outside_current_manifest_are_reviewed_incrementally(tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    db = tmp_path / "hub.db"
    store = FOStore(db)
    store.upsert_material({"material_id": "old", "title": "Synthetic"})
    text = "Aula sobre celulas.\n" + "PESSOA FICTICIA 52998224725 " * 3
    store.set_pdf_pages("old", [text, "", "Outra pagina didatica sem marca."])
    with store.conn:
        store.conn.execute("INSERT INTO pdf_page_quality VALUES(?,?,?,?,?,?,?,?)",
                           ("old", 3, "text", "text_only", 30, 0, "then", 3))
    ingest(state, db)
    result = store.get_pdf_text("old")
    assert result["pages"][0]["policy_version"] == PRIVACY_POLICY_VERSION
    assert "PESSOA FICTICIA" not in result["pages"][0]["text"]
    assert result["pages"][1]["quality"] == "ocr_pending"
    assert result["pages"][2]["text"] == "Outra pagina didatica sem marca."
    timestamps = store.conn.execute("SELECT updated_at FROM pdf_page_quality ORDER BY page").fetchall()
    ingest(state, db)
    assert store.conn.execute("SELECT updated_at FROM pdf_page_quality ORDER BY page").fetchall() == timestamps


def test_raw_page_replacement_invalidates_prior_review(tmp_path):
    store = FOStore(tmp_path / "hub.db")
    store.upsert_material({"material_id": "m"})
    store.set_pdf_pages("m", ["safe"])
    with store.conn:
        store.conn.execute("INSERT INTO pdf_page_quality VALUES(?,?,?,?,?,?,?,?)",
                           ("m", 1, "text", "text_only", 4, 0, "then", 3))
    store.set_pdf_pages("m", ["unreviewed replacement"])
    assert store.get_pdf_text("m")["pages"][0]["text"] == ""


def test_sync_status_counts_unreviewed_and_current_policy_separately(tmp_path):
    store = FOStore(tmp_path / "hub.db")
    store.upsert_material({"material_id": "m"})
    store.set_pdf_pages("m", ["raw", "reviewed"])
    with store.conn:
        store.conn.execute("INSERT INTO pdf_page_quality VALUES(?,?,?,?,?,?,?,?)",
                           ("m", 2, "text", "text_only", 8, 0, "then", PRIVACY_POLICY_VERSION))
    status = store.sync_status()["pdf_privacy"]
    assert status["current_policy_pages"] == 1
    assert status["unreviewed_pages"] == 1
    assert status["released_pages"] == 1
    assert status["blocked_pages"] == 1


def test_future_policy_review_never_auto_releases_ocr_text(tmp_path, monkeypatch):
    import fo_hub.ingest as loader
    store = FOStore(tmp_path / 'ocr.db')
    store.upsert_material({'material_id': 'm'})
    store.set_pdf_pages('m', ['Conteudo OCR sintetico aguardando revisao visual.'])
    with store.conn:
        store.conn.execute('INSERT INTO pdf_page_quality VALUES(?,?,?,?,?,?,?,?)',
                           ('m', 1, 'ocr_review', 'blocked', 50, 0, 'then', 3))
    monkeypatch.setattr(loader, 'PRIVACY_POLICY_VERSION', 4)
    loader.review_indexed_pages(store)
    result = store.conn.execute('SELECT quality,exposure FROM pdf_page_quality').fetchone()
    assert tuple(result) == ('ocr_review', 'blocked')
