"""Synthetic offline regressions with the real catalog writer and validator."""
import json
from datetime import datetime, timezone

from test_dynamic_runtime import C26, C27, ns, runtime
import fo_collect_aulas_index as collector


def entry(course, status, item):
    return collector.build_entry(
        subject_group="Disciplinas > Biologia", order=1,
        item_info={"title": "Aula sintetica", "itemId": item, "dataVideo": item,
                   "mediaType": "V", "rawText": "10:00"},
        current={"controleDuracao": "600"}, course_url=course["url"],
        captured_at=runtime.now_iso(), status=status,
        error="synthetic failure" if status == "error" else "")


def test_item_error_preserves_publication_checkpoint_and_retries_only_failed_course(tmp_path):
    paths = runtime.Paths(tmp_path)
    cid = runtime.course_id_for(C26["url"])
    old_ok = "2026-10-01T00:00:00+00:00"
    paths.catalog.mkdir()
    paths.courses_json.write_text(json.dumps({"courses": [
        {**C26, "course_id": cid, "status": "error", "last_ok_at": old_ok}]}))
    calls = []
    checkpoints = {}

    def collect(course, cp, resume):
        calls.append(course["title"])
        rows = [entry(course, "ok", "ok"), entry(course, "error", "bad")]
        cp.parent.mkdir(parents=True, exist_ok=True)
        collector.write_checkpoint(cp, course_url=course["url"], path_filters=[],
                                   entries=rows, seen_keys={collector.checkpoint_seen_key_from_entry(e) for e in rows},
                                   logger=runtime._Log(lambda _: None))
        checkpoints[course["title"]] = cp.read_bytes()
        return rows if course["url"] == C26["url"] else [entry(course, "not_launched", "future")]

    assert runtime.catalog(ns(tmp_path, "catalog"), discover=lambda: [C26, C27],
                           collect=collect, log=lambda _: None) == 1
    reg = json.loads(paths.courses_json.read_text())
    failed = next(c for c in reg["courses"] if c["course_id"] == cid)
    assert failed["status"] == "error"
    assert failed["last_ok_at"] == old_ok
    assert failed["last_summary"]["status_counts"] == {"ok": 1, "error": 1}
    out = paths.course_dir(cid)
    assert (out / "checkpoint.json").read_bytes() == checkpoints[C26["title"]]
    assert json.loads((out / "aulas_index.json").read_text())["status_counts"]["error"] == 1
    collector.validate_aulas_index_file(out / "aulas_index.tsv")
    assert calls == [C26["title"], C27["title"]]
    assert [c["course_id"] for c in runtime.courses_due(reg, "incremental", datetime.now(timezone.utc))] == [cid]
    calls.clear()

    def recover(course, cp, resume):
        calls.append(course["title"])
        assert resume and cp.exists()
        rows, seen = collector.load_checkpoint(cp, course_url=course["url"], path_filters=[],
                                              logger=runtime._Log(lambda _: None), resume_enabled=resume)
        assert [e["item_id"] for e in rows] == ["ok"]
        assert collector.checkpoint_seen_key_from_entry(entry(course, "error", "bad")) not in seen
        return rows + [entry(course, "ok", "bad")]

    assert runtime.catalog(ns(tmp_path, "catalog"), discover=lambda: [C26, C27],
                           collect=recover, log=lambda _: None) == 0
    assert calls == [C26["title"]]
    assert not (out / "checkpoint.json").exists()
    failed = next(c for c in json.loads(paths.courses_json.read_text())["courses"] if c["course_id"] == cid)
    assert failed["status"] == "ok" and failed["last_ok_at"] != old_ok


def test_checkpoint_resume_retries_error_keys_without_replaying_successes(tmp_path):
    cp = tmp_path / "checkpoint.json"
    rows = [entry(C26, status, status) for status in ("ok", "error", "not_launched")]
    keys = {collector.checkpoint_seen_key_from_entry(e) for e in rows}
    logger = runtime._Log(lambda _: None)
    collector.write_checkpoint(cp, course_url=C26["url"], path_filters=[],
                               entries=rows, seen_keys=keys, logger=logger)
    before = cp.read_bytes()
    resumed, seen = collector.load_checkpoint(cp, course_url=C26["url"], path_filters=[],
                                             logger=logger, resume_enabled=True)
    assert [e["status"] for e in resumed] == ["ok", "not_launched"]
    assert seen == {collector.checkpoint_seen_key_from_entry(e) for e in resumed}
    assert cp.read_bytes() == before  # retry preparation never destroys durable evidence
