"""Real writer -> ingest regressions using synthetic catalog/source metadata."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from test_catalog_partial import C26, collector, entry, runtime
from fo_hub.ingest import ingest
from fo_hub.store import FOStore


def test_transient_catalog_error_preserves_current_lesson_source_and_job(tmp_path):
    state = tmp_path / "state"
    paths = runtime.Paths(state)
    course = {**C26, "course_id": runtime.course_id_for(C26["url"])}
    db = tmp_path / "hub.sqlite3"
    good = entry(course, "ok", "42")
    good.update(video_stream_url="https://example.invalid/video.m3u8", duracao_segundos=600)
    remote = "Synthetic/Biology/Lesson.mp4"
    paths.catalog.mkdir(parents=True)
    (paths.catalog / "video_upload_manifest.json").write_text(json.dumps({"items": [{
        "video_stream_url": good["video_stream_url"],
        "remote_path": "onedrive:Federal Online/" + remote, "duration_seconds": 600}]}))
    (state / "remote-videos.json").write_text(json.dumps([{"Path": remote, "Size": 99, "ID": "synthetic"}]))

    def publish(row):
        runtime.run_catalog_course(course, paths, lambda *args: [row], "incremental")
        ingest(state, db, index_pdfs=False)

    publish(good)
    store = FOStore(db)
    c = store.conn
    lid = c.execute("SELECT lesson_id FROM lessons WHERE media_id='42'").fetchone()[0]
    before = dict(store.get_lesson(lid))
    source = tuple(c.execute("SELECT remote_path,revision,size,available FROM lesson_video_sources WHERE lesson_id=?", (lid,)).fetchone())
    jobs = [tuple(r) for r in c.execute("SELECT version,state FROM transcription_jobs WHERE lesson_id=?", (lid,))]
    assert before["version"] == 1 and jobs == [(1, "queued")]

    failed = entry(course, "error", "42")
    failed.update(video_stream_url=None, duracao_segundos=None)
    publish(failed)
    after = dict(store.get_lesson(lid))
    for field in ("version", "video_url", "duration_s", "media_type", "present"):
        assert after[field] == before[field]
    assert tuple(c.execute("SELECT remote_path,revision,size,available FROM lesson_video_sources WHERE lesson_id=?", (lid,)).fetchone()) == source
    assert [tuple(r) for r in c.execute("SELECT version,state FROM transcription_jobs WHERE lesson_id=?", (lid,))] == jobs
    assert json.loads((paths.course_dir(course["course_id"]) / "aulas_index.json").read_text())["status_counts"] == {"error": 1}

    revised = {**good, "duracao_segundos": 700}
    publish(revised)
    assert store.get_lesson(lid)["version"] == 2
    assert c.execute("SELECT available FROM lesson_video_sources WHERE lesson_id=?", (lid,)).fetchone()[0] == 0
    assert [tuple(r) for r in c.execute("SELECT j.version,j.state FROM transcription_jobs j JOIN lessons l USING(lesson_id) WHERE j.lesson_id=? AND j.version=l.version", (lid,))] == [(2, "queued")]
    store.conn.close()


def test_newer_error_does_not_outrank_valid_catalog_candidate(tmp_path):
    state = tmp_path / "state"
    (state / "catalog").mkdir(parents=True)
    good = entry(C26, "ok", "42")
    good.update(video_stream_url="https://example.invalid/valid.m3u8", captured_at="2026-10-27T00:00:00Z")
    failed = {**good, "status": "error", "video_stream_url": None,
              "duracao_segundos": None, "captured_at": "2026-10-28T00:00:00Z"}
    fresh_failure = {**failed, "item_id": "new", "media_id": "new"}
    (state / "catalog/aulas_index_good.json").write_text(json.dumps({"aulas": [good]}))
    (state / "catalog/aulas_index_newer.json").write_text(json.dumps({"aulas": [failed, fresh_failure]}))
    db = tmp_path / "hub.sqlite3"
    ingest(state, db, index_pdfs=False)
    store = FOStore(db)
    assert [tuple(r) for r in store.conn.execute("SELECT media_id,version,video_url,media_type FROM lessons")] == [
        ("42", 1, "https://example.invalid/valid.m3u8", "video")]
    store.conn.close()


@pytest.mark.parametrize("status", ["not_launched", "invalid_source"])
def test_definitive_catalog_statuses_are_not_filtered_as_transient_errors(tmp_path, status):
    state = tmp_path / "state"
    (state / "catalog").mkdir(parents=True)
    row = entry(C26, status, "42")
    (state / "catalog/aulas_index.json").write_text(json.dumps({"aulas": [row]}))
    db = tmp_path / "hub.sqlite3"
    ingest(state, db, index_pdfs=False)
    store = FOStore(db)
    assert store.conn.execute("SELECT media_type,present FROM lessons").fetchone()[:] == (status, 1)
    store.conn.close()
