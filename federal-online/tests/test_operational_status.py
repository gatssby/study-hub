"""Status consumes existing evidence without claiming global reconciliation."""
import json

from test_store import row
from fo_hub.store import FOStore, lesson_id_for


def test_status_exposes_index_observation_separately_from_last_fallback(tmp_path):
    store = FOStore(tmp_path / "status.db")
    store.sync_lessons([row(), row(media_id="M2")], authoritative=False)
    store.conn.execute("CREATE TABLE ingestion_status(component TEXT PRIMARY KEY,payload TEXT,updated_at REAL)")
    payload = {"created": 2, "unchanged": 4, "pdf_errors": 1, "source_videos": 8,
               "counts": {"last_sync": {"private": "never expose"}},
               "path": "private synthetic path", "error": "private synthetic error"}
    store.conn.execute("INSERT INTO ingestion_status VALUES(?,?,?)", ("index", json.dumps(payload), 100.0))
    fallback = store.sync_lessons([row(media_id="M2")], authoritative=False)
    status = store.sync_status()
    assert status["last_sync"]["run_id"] == fallback["run_id"]
    assert status["last_sync"]["unchanged"] == 1
    assert status["components"]["index"] == {
        "observed_at": 100.0, "summary": {"created": 2, "unchanged": 4, "pdf_errors": 1, "source_videos": 8}}
    assert "private" not in json.dumps(status)
    store.conn.close()
    readonly = FOStore(tmp_path / "status.db", readonly=True)
    assert readonly.sync_status()["components"] == status["components"]
    readonly.conn.close()
    from fastapi.testclient import TestClient
    from fo_hub.api import create_app
    with TestClient(create_app(tmp_path / "status.db")) as client:
        response = client.get("/fo/sync-status")
        assert response.status_code == 200
        assert response.json()["components"] == status["components"]
        assert response.json()["last_sync"] == status["last_sync"]


def test_status_counts_only_current_present_queued_jobs_without_eligible_sources(tmp_path):
    store = FOStore(tmp_path / "status.db")
    store.sync_lessons([row(media_id=f"M{i}") for i in range(7)])
    c = store.conn
    c.execute("CREATE TABLE lesson_video_sources(lesson_id TEXT PRIMARY KEY,remote_path TEXT,revision TEXT,size INTEGER,available INTEGER,checked_at TEXT)")
    for i in range(7):
        lid = lesson_id_for("C1", f"M{i}", "I1")
        c.execute("INSERT INTO transcription_jobs(lesson_id,version,state) VALUES(?,1,?)", (lid, "failed" if i == 6 else "queued"))
        if i == 4:
            c.execute("UPDATE lessons SET present=0 WHERE lesson_id=?", (lid,))
        if i == 5:
            c.execute("UPDATE lessons SET version=2 WHERE lesson_id=?", (lid,))
        if i != 0:
            c.execute("INSERT INTO lesson_video_sources VALUES(?,?,?,?,?,?)",
                      (lid, None if i == 3 else "synthetic/path", "old" if i == 2 else "1", 10, 0 if i == 1 else 1, "0"))
    c.commit()
    assert store.sync_status()["sources"] == {"current_queued": 4, "eligible": 0, "pending": 4}
    c.execute("UPDATE lesson_video_sources SET available=1 WHERE lesson_id=?", (lesson_id_for("C1", "M1", "I1"),))
    assert store.sync_status()["sources"] == {"current_queued": 4, "eligible": 1, "pending": 3}
    store.conn.close()


def test_status_before_ingestion_has_no_component_evidence_and_all_sources_pending(tmp_path):
    store = FOStore(tmp_path / "status.db")
    store.sync_lessons([row()])
    store.conn.execute("INSERT INTO transcription_jobs(lesson_id,version,state) VALUES(?,1,'queued')",
                       (lesson_id_for("C1", "M1", "I1"),))
    status = store.sync_status()
    assert status["components"] == {}
    assert status["sources"] == {"current_queued": 1, "eligible": 0, "pending": 1}
    store.conn.close()
