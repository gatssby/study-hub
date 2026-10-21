"""The deployment smoke supports both isolated and combined toolsets."""
import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize('enabled', [False, True])
def test_smoke_accepts_exact_anki_set_and_explicit_fo_optin(monkeypatch, enabled):
    path = Path(__file__).resolve().parents[1] / 'deploy/smoke.py'
    spec = importlib.util.spec_from_file_location('smoke_fo_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv('STUDY_HUB_FO_TOOLS', str(enabled).lower())
    # Use the real registration schema, but health transport stays synthetic.
    names = {'anki_health', 'anki_list_decks', 'anki_search_notes', 'anki_search_cards',
             'anki_get_note', 'anki_get_card', 'anki_update_note', 'anki_get_media',
             'anki_list_note_types', 'anki_get_note_type', 'anki_create_note', 'anki_delete_notes',
             'anki_list_tags', 'anki_rename_tag', 'anki_delete_tag', 'anki_create_deck',
             'anki_rename_deck', 'anki_delete_deck', 'anki_move_cards'}
    if enabled:
        names |= {'fo_list_lessons', 'fo_get_lesson', 'fo_search_materials', 'fo_get_pdf_text',
                  'fo_search_transcripts', 'fo_get_transcript', 'fo_get_sync_status'}
    calls = []
    class Client:
        def __init__(self, url):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def list_tools(self):
            return SimpleNamespace(tools=[SimpleNamespace(name=n) for n in names])
        async def call_tool(self, name, arguments):
            calls.append(name)
            return SimpleNamespace(is_error=False)
    monkeypatch.setattr(module, 'Client', Client)
    asyncio.run(module.run('http://127.0.0.1:8771/mcp'))
    assert calls == (['anki_health', 'fo_get_sync_status'] if enabled else ['anki_health'])
