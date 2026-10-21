"""Offline collector recovery contracts; no network, browser launch or ASR."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "portal"))
import fo_collect_aulas_index as collector


class Log:
    def log(self, message):
        pass


@pytest.mark.parametrize("failing_resource", ["context", "browser", "playwright"])
def test_collect_index_preserves_original_failure_and_releases_all_resources(tmp_path, monkeypatch, failing_resource):
    closed = []
    original = RuntimeError("collection target crashed")

    def closer(name):
        def close():
            closed.append(name)
            if name == failing_resource:
                raise RuntimeError("resource already disconnected")
        return close

    page = SimpleNamespace(set_default_timeout=lambda value: None)
    context = SimpleNamespace(new_page=lambda: page, close=closer("context"))
    browser = SimpleNamespace(new_context=lambda **kw: context, close=closer("browser"))
    pw = SimpleNamespace(chromium=SimpleNamespace(launch=lambda **kw: browser),
                         stop=closer("playwright"))
    monkeypatch.setattr(collector, "sync_playwright", lambda: SimpleNamespace(start=lambda: pw))
    monkeypatch.setattr(collector, "choose_storage_state", lambda *args: None)
    monkeypatch.setattr(collector, "open_course_page_for_collection", lambda *args, **kw: None)
    monkeypatch.setattr(collector, "resolve_collection_root", lambda *args: object())

    def crash(**kwargs):
        raise original

    monkeypatch.setattr(collector, "walk_cards", crash)
    args = SimpleNamespace(path_filter=[], no_resume=False, limit=None)
    config = SimpleNamespace(course_url="https://example.invalid/course", headless=True, nav_timeout_ms=100)
    with pytest.raises(RuntimeError) as caught:
        collector.collect_index(args, config, Log(), tmp_path / "checkpoint.json")
    assert caught.value is original
    assert closed == ["context", "browser", "playwright"]


def test_checkpoint_failure_is_not_converted_to_unavailable_or_duplicated(monkeypatch):
    page = SimpleNamespace(wait_for_timeout=lambda value: None)
    item = SimpleNamespace(scroll_into_view_if_needed=lambda: None, click=lambda: None)
    monkeypatch.setattr(collector, "wait_for_video_items_stable", lambda *args: None)
    monkeypatch.setattr(collector, "list_video_item_paths", lambda body: [[0]])
    monkeypatch.setattr(collector, "page_requires_login", lambda page: False)
    monkeypatch.setattr(collector, "resolve_descendant_path", lambda *args: item)
    monkeypatch.setattr(collector, "extract_item_info", lambda item: {
        "mediaType": "V", "itemId": "1", "dataVideo": "10", "title": "Aula 1"})
    monkeypatch.setattr(collector, "read_current_video", lambda page: {})
    monkeypatch.setattr(collector, "collect_m3u8_urls_from_network", lambda page: ([], []))
    monkeypatch.setattr(collector, "wait_for_selected_video", lambda **kw: {
        "idVideo": "10", "controleDuracao": "120", "nomeAula": "Aula 1"})
    monkeypatch.setattr(collector, "extract_video_stream_url", lambda *args, **kw: None)
    monkeypatch.setattr(collector, "detach_network_listeners", lambda *args: None)
    entries = []
    calls = []

    def checkpoint():
        calls.append(len(entries))
        if len(calls) == 1:
            raise OSError("disk full")

    with pytest.raises(OSError, match="disk full"):
        collector.collect_direct_videos(
            page=page, logger=Log(), body=object(), subject_group="Aulas Gerais > Biologia",
            course_url="https://example.invalid/course", captured_at="2026-10-21T00:00:00Z",
            entries=entries, seen_keys=set(), checkpoint_writer=checkpoint, limit=None)
    assert calls == [1]
    assert len(entries) == 1 and entries[0]["status"] == "ok"
