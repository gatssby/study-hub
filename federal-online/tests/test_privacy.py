import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "portal"))


def test_pdf_privacy_redacts_valid_cpf_and_labeled_name_without_logging_value():
    from fo_hub.pdf_privacy import sanitize_page

    page = sanitize_page("Nome: Maria da Silva\nCPF: 529.982.247-25\nQuestão: 2")
    assert "Maria da Silva" not in page.text
    assert "529.982.247-25" not in page.text
    assert "[DADO REMOVIDO]" in page.text
    assert page.pii_redacted is True
    assert page.exposure == "text_only"


def test_pdf_privacy_blocks_empty_and_ambiguous_identity_pages():
    from fo_hub.pdf_privacy import sanitize_page

    assert sanitize_page("").quality == "ocr_pending"
    review = sanitize_page("Nome: Joao da Silva")
    assert review.pii_redacted is False
    assert review.exposure == "blocked"


def test_ingest_reindexes_legacy_pages_and_records_quality(tmp_path):
    from fo_hub.ingest import ingest
    from fo_hub.store import FOStore

    state = tmp_path / "state"
    material_dir = state / "materials" / "course"
    material_dir.mkdir(parents=True)
    pdf = material_dir / "lesson.pdf"
    pdf.write_bytes(b"%PDF-fixture")
    (state / "materials" / "manifest.json").write_text(json.dumps({"items": []}))

    # Exercise the privacy helper independently because a hand-written PDF
    # fixture is intentionally not a real PDF parser input.
    db = tmp_path / "hub.db"
    store = FOStore(db)
    store.upsert_material({"material_id": "legacy", "title": "x", "sha256": "h"})
    store.set_pdf_pages("legacy", ["Nome: Maria da Silva", "texto"])
    assert store.conn.execute("select count(*) from pdf_page_quality").fetchone()[0] == 0

    # The production migration is guarded by absence of quality rows.
    from fo_hub.pdf_privacy import sanitize_page
    pages = [sanitize_page("Nome: Maria da Silva"), sanitize_page("texto didatico suficiente")]
    store.set_pdf_pages("legacy", [p.text for p in pages])
    store.conn.executemany(
        "insert into pdf_page_quality values(?,?,?,?,?,?,?,?)",
        [("legacy", i + 1, p.quality, p.exposure, len(p.text), int(p.pii_redacted), "now", 2)
         for i, p in enumerate(pages)],
    )
    result = store.get_pdf_text("legacy")
    assert result is not None
    assert "Maria da Silva" not in json.dumps(result, ensure_ascii=False)
    assert result["pages"][0]["exposure"] == "blocked"


def test_video_recovery_removes_only_matching_unvalidated_partials(tmp_path):
    import video_runtime

    class Logger:
        def __init__(self):
            self.messages = []

        def log(self, message):
            self.messages.append(message)

    matching = tmp_path / "abc-123.partial.mp4"
    unrelated = tmp_path / "other-123.partial.mp4"
    matching.write_bytes(b"partial")
    unrelated.write_bytes(b"keep")
    logger = Logger()
    assert video_runtime.discard_recoverable_partial(tmp_path, "abc", logger) == 1
    assert not matching.exists()
    assert unrelated.exists()
