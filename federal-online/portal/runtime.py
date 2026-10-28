#!/usr/bin/env python3
"""Operational runner for Federal Online: dynamic course catalog + materials.

    python runtime.py catalog   [--mode incremental|weekly] [--course-filter TXT] [--limit N] [--headed]
    python runtime.py materials [--mode incremental|weekly] [--course-filter TXT] [--headed] [--upload]

Paths come from env (FO_STATE_ROOT, FO_ENV_FILE); nothing is fixed to a year or course.
Missing PDFs/courses are never deleted; no backup dirs are created; uploads are additive.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import sys
import traceback
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Iterator

from discovery import ORIGIN, course_links, merge_materials, catalog_navigation_links
from safe_io import atomic_write_json

DEFAULT_STATE_ROOT = Path(os.environ.get("FO_STATE_ROOT") or "/home/ubuntu/study-hub-state/federal-online")
DEFAULT_ENV_FILE = Path(os.environ.get("FO_ENV_FILE") or "/home/ubuntu/.config/study-hub/federal_online.env")
PORTAL_URL = os.environ.get("FO_PORTAL_URL") or f"{ORIGIN}/portal"
INCREMENTAL_MAX_AGE = timedelta(hours=6)
SCHEMA_VERSION = 1


# --------------------------------------------------------------------------- utils

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_iso(value: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(value) if value else None
    except ValueError:
        return None


def slug(text: str) -> str:
    import unicodedata

    value = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value[:80] or "item"


def course_id_for(url: str) -> str:
    tail = url.rstrip("/").rsplit("/", 1)[-1]
    return f"{slug(tail)}-{hashlib.sha1(url.encode()).hexdigest()[:8]}"


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return default


@contextmanager
def run_lock(state_root: Path, name: str = "runtime") -> Iterator[Path]:
    """Non-blocking flock; compatible with an outer `flock` in systemd units on the same file."""
    lock_path = state_root / "locks" / f"{name}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+")
    try:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"lock ocupado: {lock_path}") from exc
        yield lock_path
    finally:
        handle.close()


@dataclass(frozen=True)
class Paths:
    state_root: Path

    @property
    def catalog(self) -> Path:
        return self.state_root / "catalog"

    @property
    def courses_json(self) -> Path:
        return self.catalog / "courses.json"

    def course_dir(self, course_id: str) -> Path:
        return self.catalog / "courses" / course_id

    @property
    def materials(self) -> Path:
        return self.state_root / "materials"

    @property
    def materials_courses_json(self) -> Path:
        return self.materials / "courses.json"

    @property
    def materials_checkpoint(self) -> Path:
        return self.materials / "checkpoint.json"

    @property
    def logs(self) -> Path:
        return self.state_root / "logs"

    @property
    def storage_state(self) -> Path:
        return self.state_root / "storage_state.json"


# ----------------------------------------------------------------- reconciliation

def reconcile_courses(previous: dict[str, Any], discovered: list[dict[str, str]], at: str) -> dict[str, Any]:
    """Merge discovered courses into the persistent registry. Never drops a course."""
    by_id = {c["course_id"]: dict(c) for c in previous.get("courses", [])}
    seen: set[str] = set()
    for item in discovered:
        cid = course_id_for(item["url"])
        seen.add(cid)
        entry = by_id.setdefault(cid, {"course_id": cid, "first_seen": at, "status": "new"})
        entry.update(url=item["url"], title=item.get("title") or entry.get("title", ""), last_seen=at)
        entry.pop("missing_since", None)
        if entry.get("status") == "missing":
            entry["status"] = "pending"
    for cid, entry in by_id.items():
        if cid not in seen:
            entry.setdefault("missing_since", at)
            entry["status"] = "missing"
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": at,
        "courses": sorted(by_id.values(), key=lambda c: c["course_id"]),
    }


def courses_due(registry: dict[str, Any], mode: str, now: datetime, course_filter: str = "") -> list[dict]:
    due = []
    for course in registry.get("courses", []):
        if course.get("status") == "missing":
            continue
        if course_filter and course_filter.lower() not in f"{course.get('title','')} {course.get('url','')}".lower():
            continue
        if mode == "weekly":
            due.append(course)
            continue
        last_ok = parse_iso(course.get("last_ok_at"))
        if course.get("status") != "ok" or last_ok is None or now - last_ok >= INCREMENTAL_MAX_AGE:
            due.append(course)
    return due


def unknown_branches(entries: list[dict[str, Any]], known_roots: tuple[str, ...]) -> list[dict[str, Any]]:
    """Roots/branches seen in a course that are not in the historical known-root list (reporting only)."""
    known = {slug(r) for r in known_roots}
    counts: dict[str, dict[str, Any]] = {}
    for entry in entries:
        ref = str(entry.get("source_ref") or "")
        parts = [p.strip() for p in ref.split(">") if p.strip()]
        if not parts or slug(parts[0]) in known:
            continue
        branch = " > ".join(parts[:2])
        item = counts.setdefault(branch, {"branch": branch, "root": parts[0], "items": 0})
        item["items"] += 1
    return sorted(counts.values(), key=lambda b: b["branch"])


# ------------------------------------------------------------------------ catalog

def discover_courses_from_page(page: Any) -> list[dict[str, str]]:
    links = page.evaluate(
        "() => Array.from(document.querySelectorAll('a[href]')).map(a => ({href: a.getAttribute('href') || '', "
        "text: (a.innerText || a.textContent || a.getAttribute('title') || '').replace(/\\s+/g, ' ').trim()}))"
    )
    return course_links(links)


def run_catalog_course(
    course: dict[str, Any],
    paths: Paths,
    collect: Callable[[dict[str, Any], Path, bool], list[dict[str, Any]]],
    mode: str,
) -> dict[str, Any]:
    """Collect one course into catalog/courses/<id>/ with a per-course checkpoint."""
    import fo_collect_aulas_index as collector

    out = paths.course_dir(course["course_id"])
    out.mkdir(parents=True, exist_ok=True)
    checkpoint = out / collector.CHECKPOINT_FILENAME
    resume = mode != "weekly" or checkpoint.exists()
    entries = collect(course, checkpoint, resume)
    pending, _ = collector.load_checkpoint(
        checkpoint, course_url=course["url"], path_filters=[],
        logger=_Log(lambda _: None), resume_enabled=True)
    observed = {collector.checkpoint_seen_key_from_entry(e) for e in entries}
    entries = list(entries) + [e for e in pending if e.get("status") == "error"
                              and (collector.checkpoint_seen_key_from_entry(e) is None
                                   or collector.checkpoint_seen_key_from_entry(e) not in observed)]
    at = now_iso()
    from collections import Counter

    status_counts = dict(Counter(str(e.get("status") or "") for e in entries))
    payload = {
        "schema_version": collector.SCHEMA_VERSION,
        "generated_at": at,
        "course_url": course["url"],
        "course_title": course.get("title", ""),
        "path_filters": [],
        "total": len(entries),
        "status_counts": status_counts,
        "aulas": entries,
    }
    build = out / f"{collector.BUILD_PREFIX}{os.getpid()}"
    if build.exists():
        import shutil

        shutil.rmtree(build)
    collector.write_outputs(output_dir=out, build_dir=build, output_stem="aulas_index", payload=payload, entries=entries)
    build.rmdir()
    branches = unknown_branches(entries, collector.ACADEMIC_ROOT_AREAS)
    atomic_write_json(out / "branches.json", {"generated_at": at, "unknown_branches": branches})
    if not status_counts.get("error", 0):
        checkpoint.unlink(missing_ok=True)
    return {"total": len(entries), "status_counts": status_counts, "unknown_branches": len(branches)}


def catalog(args: argparse.Namespace, *, discover: Callable[[], list[dict[str, str]]] | None = None,
            collect: Callable[[dict[str, Any], Path, bool], list[dict[str, Any]]] | None = None,
            log: Callable[[str], None] = print) -> int:
    paths = Paths(args.state_root)
    with run_lock(args.state_root):
        browser_ctx = None
        if discover is None or collect is None:
            browser_ctx = BrowserSession(args, paths, log)
            discover = discover or browser_ctx.discover_courses
            collect = collect or browser_ctx.collect_course
        try:
            discovered = discover()
            if not discovered:
                raise RuntimeError("nenhum curso descoberto em /portal; registro preservado")
            registry = reconcile_courses(read_json(paths.courses_json, {}), discovered, now_iso())
            atomic_write_json(paths.courses_json, registry)
            due = courses_due(registry, args.mode, datetime.now(timezone.utc), args.course_filter)
            log(f"[catalog] descobertos={len(discovered)} pendentes={len(due)} mode={args.mode}")
            failures = 0
            for course in due:
                try:
                    summary = run_catalog_course(course, paths, collect, args.mode)
                    errors = summary["status_counts"].get("error", 0)
                    if errors:
                        failures += 1
                        update = {"status": "error", "last_summary": summary,
                                  "last_error": f"catalog item errors: {errors}; checkpoint preserved"}
                        log(f"[catalog] curso={course['course_id']} parcial: {errors} erros")
                    else:
                        update = {"status": "ok", "last_ok_at": now_iso(), "last_summary": summary, "last_error": ""}
                except Exception as exc:  # per-course isolation; checkpoint keeps progress
                    failures += 1
                    update = {"status": "error", "last_error": f"{type(exc).__name__}: {exc}"[:500]}
                    log(f"[catalog] curso={course['course_id']} falhou: {update['last_error']}")
                registry = read_json(paths.courses_json, registry)
                for entry in registry["courses"]:
                    if entry["course_id"] == course["course_id"]:
                        entry.update(update, last_run_at=now_iso())
                atomic_write_json(paths.courses_json, registry)
            return 1 if failures else 0
        finally:
            if browser_ctx:
                browser_ctx.close()


# ---------------------------------------------------------------------- materials

def material_jobs(options: list[dict[str, Any]], course_filter: str = "") -> list[dict[str, str]]:
    jobs = []
    for course in options:
        if course_filter and course_filter.lower() not in course["label"].lower():
            continue
        for disc in course.get("disciplines", []):
            jobs.append({"course_value": course["value"], "course_label": course["label"],
                         "discipline": disc["label"], "key": f"{course['value']}|{disc['label']}"})
    return jobs


def materials(args: argparse.Namespace, *, discover_options: Callable[[], list[dict[str, Any]]] | None = None,
              process: Callable[[dict[str, str], Path, list], None] | None = None,
              write_manifest: Callable[[Path, list], None] | None = None,
              upload: Callable[[Path], None] | None = None,
              log: Callable[[str], None] = print) -> int:
    paths = Paths(args.state_root)
    with run_lock(args.state_root, 'materials-runtime'):
        session = None
        if discover_options is None or process is None:
            session = BrowserSession(args, paths, log)
            discover_options = discover_options or session.discover_material_options
            process = process or session.process_material_job
        if write_manifest is None:
            from fo_sync_materials import write_manifest as write_manifest  # noqa: PLW0127
        try:
            options = discover_options()
            if not options:
                raise RuntimeError("nenhum curso em #idCurso; nada alterado")
            at = now_iso()
            registry = read_json(paths.materials_courses_json, {"courses": []})
            known = {c["value"]: c for c in registry.get("courses", [])}
            for opt in options:
                entry = known.setdefault(opt["value"], {"value": opt["value"], "first_seen": at})
                entry.update(label=opt["label"], slug=slug(opt["label"]), last_seen=at,
                             disciplines=[d["label"] for d in opt.get("disciplines", [])])
                entry.pop("missing_since", None)
            for value, entry in known.items():
                if value not in {o["value"] for o in options}:
                    entry.setdefault("missing_since", at)
            atomic_write_json(paths.materials_courses_json,
                              {"schema_version": SCHEMA_VERSION, "generated_at": at,
                               "courses": sorted(known.values(), key=lambda c: c["value"])})

            cp = read_json(paths.materials_checkpoint, {})
            done = set(cp.get("done", [])) if args.mode == "incremental" or cp.get("in_progress") else set()
            if args.mode == "weekly" and not cp.get("in_progress"):
                done = set()
            failures = 0
            jobs = material_jobs(options, args.course_filter)
            by_course: dict[str, list[dict[str, str]]] = {}
            for job in jobs:
                by_course.setdefault(job["course_value"], []).append(job)
            for course_value, course_jobs in by_course.items():
                label = course_jobs[0]["course_label"]
                final_dir = paths.materials / slug(label)
                build = paths.materials / f".build_{slug(label)}"
                for job in course_jobs:
                    if job["key"] in done:
                        continue
                    # Retry an interrupted durable generation before downloads can
                    # mutate staging inodes already linked into the final tree.
                    if build.exists() or build.is_symlink():
                        try:
                            with (paths.state_root/'locks/materials-publication.lock').open('a+') as publication:
                                fcntl.flock(publication, fcntl.LOCK_EX)
                                merge_materials(build, final_dir)
                        except Exception as exc:
                            failures += 1
                            log(f"[materials] pending promotion failed for {job['key']}: {type(exc).__name__}")
                            break
                    build.mkdir(parents=True, exist_ok=True)
                    entries: list = []
                    successful=True
                    try:
                        process(job, build, entries)
                    except Exception as exc:
                        successful=False
                        failures += 1
                        log(f"[materials] {job['key']} falhou: {exc}")
                    try:
                        # OneDrive holds a shared lock from copy through check;
                        # publish a new generation only outside that interval.
                        with (paths.state_root/'locks/materials-publication.lock').open('a+') as publication:
                            fcntl.flock(publication,fcntl.LOCK_EX)
                            if entries:
                                write_manifest(build, entries)
                                if not (build / 'manifest.json').exists():
                                    _write_course_manifest(final_dir, build, entries)
                            merge_materials(build, final_dir)
                    except Exception as exc:
                        failures+=1
                        log(f"[materials] promotion failed for {job['key']}: {type(exc).__name__}")
                        # Never checkpoint success before durable publication.
                        break
                    if successful:done.add(job['key'])
                    atomic_write_json(paths.materials_checkpoint,
                                      {"in_progress": True, "updated_at": now_iso(), "done": sorted(done)})
            complete = failures == 0
            atomic_write_json(paths.materials_checkpoint,
                              {"in_progress": not complete, "updated_at": now_iso(),
                               "done": [] if complete else sorted(done)})
            if complete and args.upload and upload:
                upload(paths.materials)
            elif complete and args.upload:
                from fo_sync_materials_from_portal_materiais import ONEDRIVE_REMOTE, sync_to_onedrive

                sync_to_onedrive(paths.materials, _Log(log), ONEDRIVE_REMOTE)
            return 0 if complete else 1
        finally:
            if session:
                session.close()


def _write_course_manifest(final_dir: Path, build: Path, entries: list) -> None:
    """Stage new observations only; merge_materials owns historical version merge."""
    from dataclasses import asdict, is_dataclass

    items = [asdict(e) if is_dataclass(e) else dict(e) for e in entries]
    atomic_write_json(build / "manifest.json", {"schema_version": SCHEMA_VERSION, "generated_at": now_iso(),
                                                "count": len(items), "items": items})


class _Log:
    def __init__(self, fn: Callable[[str], None]) -> None:
        self.log = fn


# ------------------------------------------------------------- browser (live only)

class BrowserSession:
    """Thin adapter over the existing scripts' login/navigation/process functions."""

    def __init__(self, args: argparse.Namespace, paths: Paths, log: Callable[[str], None]) -> None:
        import fo_sync_materials as base
        import fo_sync_materials_from_portal_materiais as mat
        from fo_session_security import protect_storage_state

        if mat.sync_playwright is None:
            raise RuntimeError("playwright ausente")
        paths.logs.mkdir(parents=True, exist_ok=True)
        self.args, self.paths = args, paths
        self.logger = base.Logger([paths.logs / f"runtime.{args.command}.latest.log"])
        ns = SimpleNamespace(env_file=args.env_file, state_root=args.state_root, headed=args.headed,
                             nav_timeout_ms=base.DEFAULT_NAV_TIMEOUT_MS,
                             download_timeout_ms=base.DEFAULT_DOWNLOAD_TIMEOUT_MS)
        self.base_config = base.build_runtime_config(ns)
        self.mat_config = mat.build_runtime_config(SimpleNamespace(**vars(ns)))
        self.mat_config = type(self.mat_config)(**{**vars(self.mat_config), "final_dir": paths.materials})
        self._pw = mat.sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=not args.headed)
        kwargs: dict[str, Any] = {"accept_downloads": True}
        protect_storage_state(paths.storage_state)
        if paths.storage_state.exists():
            kwargs["storage_state"] = str(paths.storage_state)
        self.context = self._browser.new_context(**kwargs)
        self._hashes: dict[str, str] = {}

    def _save_session(self) -> None:
        from fo_session_security import save_storage_state

        save_storage_state(self.context, self.paths.storage_state)

    def discover_courses(self) -> list[dict[str, str]]:
        import fo_sync_materials as base

        page = self.context.new_page()
        try:
            page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=self.base_config.nav_timeout_ms)
            if base.page_requires_login(page):
                base.login_if_needed(page, self.base_config, self.logger)
                page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=self.base_config.nav_timeout_ms)
            page.wait_for_load_state("load", timeout=self.base_config.nav_timeout_ms)
            discovered={}
            pending=[PORTAL_URL]
            visited=set()
            while pending:
                url=pending.pop(0)
                if url in visited:continue
                visited.add(url)
                page.goto(url,wait_until='networkidle',timeout=self.base_config.nav_timeout_ms)
                if base.page_requires_login(page):raise RuntimeError('Login expired during course discovery; registry unchanged')
                links=page.evaluate("() => Array.from(document.querySelectorAll('a[href]')).map(a=>({href:a.getAttribute('href')||'',text:(a.innerText||a.getAttribute('title')||'').trim()}))")
                for item in course_links(links):discovered[item['url']]=item
                pending.extend(x for x in catalog_navigation_links(links) if x not in visited)
            self._save_session()
            return list(discovered.values())
        finally:
            page.close()

    def collect_course(self, course: dict[str, Any], checkpoint: Path, resume: bool) -> list[dict[str, Any]]:
        from dataclasses import replace
        from concurrent.futures import ThreadPoolExecutor

        import fo_collect_aulas_index as collector

        config = replace(self.base_config, course_url=course["url"], storage_state_file=self.paths.storage_state)
        self._save_session()
        args = SimpleNamespace(path_filter=[], no_resume=not resume, limit=self.args.limit,
                               storage_state=self.paths.storage_state)
        # The collector owns sync_playwright; discovery already owns a loop on
        # this thread. Keep the two lifecycle contexts on independent threads.
        with ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(collector.collect_index, args, config, self.logger, checkpoint).result()

    def discover_material_options(self) -> list[dict[str, Any]]:
        import fo_sync_materials_from_portal_materiais as mat

        page = mat.open_authenticated_materials_page(self.context, self.mat_config, self.logger)
        try:
            self._save_session()
            return mat.discover_material_options(page, self.mat_config, self.logger)
        finally:
            page.close()

    def process_material_job(self, job: dict[str, str], build: Path, entries: list) -> None:
        import fo_sync_materials_from_portal_materiais as mat

        out_subject = mat.output_subject_for(job["discipline"])
        target = mat.PortalTarget(group="obra" if "obra" in job["discipline"].lower() else "disciplina",
                                  portal_subject=job["discipline"], output_subject=out_subject, material_type="")
        before = len(entries)
        mat.process_subject(self.context, self.mat_config, self.logger, [target], build, build,
                            self._hashes, entries, course_value=job["course_value"],
                            course_label=job["course_label"])
        if any(getattr(e, "status", "") == "error" for e in entries[before:]):
            raise RuntimeError("downloads com erro; disciplina sera repetida")

    def close(self) -> None:
        for closer in (self.context.close, self._browser.close, self._pw.stop):
            try:
                closer()
            except Exception:
                pass


# --------------------------------------------------------------------------- CLI

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("catalog", "materials"))
    parser.add_argument("--mode", choices=("incremental", "weekly"), default="incremental")
    parser.add_argument("--state-root", type=Path, default=DEFAULT_STATE_ROOT)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--course-filter", default="")
    parser.add_argument("--limit", type=int, default=None, help="catalog: limite de aulas por curso (teste)")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--upload", action="store_true", help="materials: rclone copy+check (aditivo) ao final")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.state_root.mkdir(parents=True, exist_ok=True)
    try:
        return catalog(args) if args.command == "catalog" else materials(args)
    except Exception as exc:
        print(f"[runtime] falha: {type(exc).__name__}: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 2 if "lock ocupado" in str(exc) else 1


if __name__ == "__main__":
    raise SystemExit(main())
