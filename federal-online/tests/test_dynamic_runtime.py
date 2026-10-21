"""Offline runtime tests: fakes for discovery/collection/download, no network."""
import argparse
import fcntl
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

PORTAL = Path(__file__).resolve().parents[1] / "portal"
sys.path.insert(0, str(PORTAL))
import runtime  # noqa: E402


def test_existing_collector_runs_outside_discovery_playwright_thread(tmp_path,monkeypatch):
    import threading
    from types import SimpleNamespace
    from dataclasses import dataclass
    import fo_collect_aulas_index as collector
    main=threading.get_ident()
    threads=[]
    @dataclass
    class Config:
        course_url:str=''
        storage_state_file:Path=tmp_path/'session.json'
    session=runtime.BrowserSession.__new__(runtime.BrowserSession)
    session.base_config=Config()
    session.paths=runtime.Paths(tmp_path)
    session.args=SimpleNamespace(limit=None)
    session.logger=None
    session._save_session=lambda:None
    def collect(*args):
        threads.append(threading.get_ident())
        return []
    monkeypatch.setattr(collector,'collect_index',collect)
    session.collect_course({'url':'https://example/course'},tmp_path/'checkpoint.json',True)
    assert threads and threads[0]!=main


def ns(tmp_path, command, **kw):
    base = dict(command=command, mode="incremental", state_root=tmp_path, env_file=tmp_path / "x.env",
                course_filter="", limit=None, headed=False, upload=False)
    base.update(kw)
    return argparse.Namespace(**base)


C26 = {"url": "https://www.federalonline.com.br/portal/curso-aula/produto-pacote/a/extensivo-2026", "title": "Ext 2026"}
C27 = {"url": "https://www.federalonline.com.br/portal/curso-aula/produto-pacote/b/extensivo-2027", "title": "Ext 2027"}


def entries_for(course):
    return [{"source_ref": "Obras > Dom Casmurro", "titulo_original": "Aula 1", "status": "ok"},
            {"source_ref": "Categoria Nova > X", "titulo_original": "Aula 1", "status": "ok"}]


def test_no_legacy_paths_in_runtime_and_core():
    for name in ("runtime.py", "fo_sync_materials.py", "fo_collect_aulas_index.py",
                 "fo_sync_materials_from_portal_materiais.py"):
        text = (PORTAL / name).read_text()
        for bad in ("anki-gpt-sync", "cronograma_fo", "fo_bridge", "raw_previous", "materiais_fo_previous",
                    '"rclone", "sync"', "extensivo-ufpr-2026"):
            assert bad not in text, (name, bad)


def test_catalog_discovers_new_year_writes_per_course_and_unknown_branches(tmp_path, monkeypatch):
    monkeypatch.setattr("fo_collect_aulas_index.validate_aulas_index_file", lambda p: None)
    rc = runtime.catalog(ns(tmp_path, "catalog"), discover=lambda: [C26, C27],
                         collect=lambda c, cp, r: entries_for(c), log=lambda m: None)
    assert rc == 0
    reg = json.loads((tmp_path / "catalog/courses.json").read_text())
    assert {c["title"] for c in reg["courses"]} == {"Ext 2026", "Ext 2027"}
    assert all(c["status"] == "ok" for c in reg["courses"])
    for c in reg["courses"]:
        d = tmp_path / "catalog/courses" / c["course_id"]
        assert (d / "aulas_index.json").exists() and (d / "aulas_index.tsv").exists()
        br = json.loads((d / "branches.json").read_text())["unknown_branches"]
        assert [b["root"] for b in br] == ["Categoria Nova"]


def test_catalog_keeps_missing_courses_and_incremental_skips_fresh(tmp_path, monkeypatch):
    monkeypatch.setattr("fo_collect_aulas_index.validate_aulas_index_file", lambda p: None)
    runtime.catalog(ns(tmp_path, "catalog"), discover=lambda: [C26, C27],
                    collect=lambda c, cp, r: entries_for(c), log=lambda m: None)
    calls = []
    runtime.catalog(ns(tmp_path, "catalog"), discover=lambda: [C27],
                    collect=lambda c, cp, r: calls.append(c) or entries_for(c), log=lambda m: None)
    assert calls == []  # fresh -> skipped in incremental
    reg = json.loads((tmp_path / "catalog/courses.json").read_text())
    missing = [c for c in reg["courses"] if c["status"] == "missing"]
    assert len(reg["courses"]) == 2 and missing[0]["title"] == "Ext 2026"
    runtime.catalog(ns(tmp_path, "catalog", mode="weekly"), discover=lambda: [C27],
                    collect=lambda c, cp, r: calls.append(c) or entries_for(c), log=lambda m: None)
    assert [c["title"] for c in calls] == ["Ext 2027"]


def test_catalog_failure_is_isolated_and_retried(tmp_path, monkeypatch):
    monkeypatch.setattr("fo_collect_aulas_index.validate_aulas_index_file", lambda p: None)

    def collect(c, cp, resume):
        if "2026" in c["url"]:
            raise RuntimeError("boom")
        return entries_for(c)
    assert runtime.catalog(ns(tmp_path, "catalog"), discover=lambda: [C26, C27], collect=collect,
                           log=lambda m: None) == 1
    reg = {c["title"]: c for c in json.loads((tmp_path / "catalog/courses.json").read_text())["courses"]}
    assert reg["Ext 2026"]["status"] == "error" and reg["Ext 2027"]["status"] == "ok"
    due = runtime.courses_due({"courses": list(reg.values())}, "incremental", datetime.now(timezone.utc))
    assert [c["title"] for c in due] == ["Ext 2026"]
    old = dict(reg["Ext 2027"], last_ok_at=(datetime.now(timezone.utc) - timedelta(days=8)).isoformat())
    assert runtime.courses_due({"courses": [old]}, "incremental", datetime.now(timezone.utc))


def test_existing_courses_are_reconciled_every_six_hours_not_only_weekly():
    now=datetime.now(timezone.utc)
    course={'url':C27['url'],'title':'2027','status':'ok','last_ok_at':(now-timedelta(hours=7)).isoformat()}
    assert runtime.courses_due({'courses':[course]},'incremental',now)==[course]


def test_empty_discovery_preserves_registry(tmp_path):
    (tmp_path / "catalog").mkdir()
    (tmp_path / "catalog/courses.json").write_text('{"courses": [{"course_id": "x"}]}')
    with pytest.raises(RuntimeError):
        runtime.catalog(ns(tmp_path, "catalog"), discover=lambda: [], collect=lambda *a: [], log=lambda m: None)
    assert "x" in (tmp_path / "catalog/courses.json").read_text()


def test_materials_discovery_does_not_wait_for_long_catalog_lock(tmp_path):
    reached=[]
    with runtime.run_lock(tmp_path):
        with pytest.raises(RuntimeError,match='nenhum curso em'):
            runtime.materials(ns(tmp_path,'materials'),discover_options=lambda:reached.append(True) or [],
                              process=lambda *a:None,write_manifest=lambda *a:None)
    assert reached


def test_lock_blocks_concurrent_run(tmp_path):
    lock = tmp_path / "locks/runtime.lock"
    lock.parent.mkdir()
    with lock.open("a+") as h:
        fcntl.flock(h, fcntl.LOCK_EX)
        with pytest.raises(RuntimeError, match="lock ocupado"):
            runtime.catalog(ns(tmp_path, "catalog"), discover=lambda: [C26], collect=lambda *a: [],
                            log=lambda m: None)


OPTIONS = [{"value": "P-1", "label": "Extensivo 2027", "disciplines": [
    {"value": "1", "label": "Redação - Federal"}, {"value": "2", "label": "Obras Literárias"}]}]


def fake_process(fail=()):
    def process(job, build, entries):
        if job["discipline"] in fail:
            raise RuntimeError("x")
        rel = f"{job['discipline']}/a.pdf"
        (build / rel).parent.mkdir(parents=True, exist_ok=True)
        (build / rel).write_bytes(b"%PDF-1")
        entries.append({"target_key": job["key"], "status": "ok", "relative_path": rel})
    return process


def test_materials_dynamic_options_keep_old_pdfs_and_checkpoint(tmp_path):
    course_dir = tmp_path / "materials/extensivo-2027"
    course_dir.mkdir(parents=True)
    (course_dir / "old.pdf").write_bytes(b"%PDF-old")
    legacy = tmp_path / "materials/Biologia/legacy.pdf"
    legacy.parent.mkdir()
    legacy.write_bytes(b"%PDF-legacy")
    args = ns(tmp_path, "materials")
    rc = runtime.materials(args, discover_options=lambda: OPTIONS, process=fake_process(fail={"Obras Literárias"}),
                           write_manifest=lambda b, e: None, log=lambda m: None)
    assert rc == 1
    assert (course_dir / "old.pdf").exists() and legacy.exists()
    assert (course_dir / "Redação - Federal/a.pdf").exists()
    cp = json.loads((tmp_path / "materials/checkpoint.json").read_text())
    assert cp["in_progress"] and cp["done"] == ["P-1|Redação - Federal"]
    seen = []
    proc = fake_process()
    rc = runtime.materials(args, discover_options=lambda: OPTIONS,
                           process=lambda j, b, e: seen.append(j["discipline"]) or proc(j, b, e),
                           write_manifest=lambda b, e: None, log=lambda m: None)
    assert rc == 0 and seen == ["Obras Literárias"]
    manifest = json.loads((course_dir / "manifest.json").read_text())
    assert {i["relative_path"] for i in manifest["items"]} == {"Redação - Federal/a.pdf", "Obras Literárias/a.pdf"}
    reg = json.loads((tmp_path / "materials/courses.json").read_text())
    assert reg["courses"][0]["disciplines"] == ["Redação - Federal", "Obras Literárias"]
    assert not list((tmp_path / "materials").glob(".build_*"))


def test_materials_upload_only_after_complete(tmp_path):
    uploads = []
    runtime.materials(ns(tmp_path, "materials", upload=True), discover_options=lambda: OPTIONS,
                      process=fake_process(fail={"Obras Literárias"}), write_manifest=lambda b, e: None,
                      upload=uploads.append, log=lambda m: None)
    assert uploads == []
    runtime.materials(ns(tmp_path, "materials", upload=True), discover_options=lambda: OPTIONS,
                      process=fake_process(), write_manifest=lambda b, e: None, upload=uploads.append,
                      log=lambda m: None)
    assert uploads == [tmp_path / "materials"]


def test_error_material_without_download_path_is_recorded_not_fatal(tmp_path):
    import fo_sync_materials as base
    import fo_sync_materials_from_portal_materiais as mat
    target=mat.PortalTarget(group='disciplina',portal_subject='Bio',output_subject='Bio',material_type='Resumo')
    entries=[]
    mat.append_error_entry(entries,target,'now','download transient error')
    base.write_manifest(tmp_path,entries)
    data=json.loads((tmp_path/'manifest.json').read_text())
    assert data['error_count']==1 and data['items'][0]['relative_path']==''


def test_material_checkpoint_never_marks_download_done_before_manifest_commit(tmp_path):
    def broken_manifest(*args):raise RuntimeError('disk failure during manifest write')
    runtime.materials(ns(tmp_path,'materials'),discover_options=lambda:OPTIONS,process=fake_process(),
                      write_manifest=broken_manifest,log=lambda m:None)
    cp=json.loads((tmp_path/'materials/checkpoint.json').read_text())
    assert cp['in_progress'] and cp['done']==[]


def test_clean_select_options_and_area_fallback():
    import fo_sync_materials_from_portal_materiais as mat
    opts = mat.clean_select_options([{"value": "", "label": "Selecione"}, {"value": "9", "label": " Redação  UFPR "},
                                     {"value": "9", "label": "dup"}, {"value": "0", "label": "Todos"}])
    assert opts == [{"value": "9", "label": "Redação UFPR"}]
    assert mat.subject_area_for("Física I - Federal") == "Física"
    assert mat.subject_area_for("Redação II - Federal") == "Redação"


def test_rclone_is_additive_copy(monkeypatch, tmp_path):
    import fo_sync_materials_from_portal_materiais as mat
    cmds = []
    monkeypatch.setattr(mat.subprocess, "run",
                        lambda c, **k: cmds.append(c) or type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})())
    mat.sync_to_onedrive(tmp_path, type("L", (), {"log": lambda s, m: None})(), "r:x")
    assert [c[1] for c in cmds] == ["copy", "check"]


def test_discover_courses_from_page_fixture():
    class Page:
        def evaluate(self, js):
            return [{"href": "/portal/curso-aula/produto-pacote/z/obras-2027", "text": "Obras 2027"},
                    {"href": "/portal/materiais", "text": "Materiais"}]
    assert runtime.discover_courses_from_page(Page())[0]["title"] == "Obras 2027"
