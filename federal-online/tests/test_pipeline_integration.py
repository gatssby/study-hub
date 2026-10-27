"""Synthetic worker -> SQLite -> HTTP/MCP and publication selection integration."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
from mcp import Client

from test_worker_readiness import ready
from fo_hub.worker import Worker
from fo_hub.api import create_app
from fo_hub.mcp import FOClient, create_server
from fo_hub.onedrive import _transcript_allowlist


def test_two_chunk_stitch_is_queryable_and_sync_eligible(tmp_path, monkeypatch):
    store, lesson, cfg = ready(tmp_path, duration=602)
    calls = []
    def run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[0] == 'rclone':
            Path(cmd[3]).write_bytes(b'fakevideo')
        elif cmd[0] == 'ffprobe':
            return SimpleNamespace(stdout=json.dumps({'format': {'duration': 602}}), stderr='')
        elif cmd[0] == 'ffmpeg' and cmd[-1].endswith('.wav'):
            Path(cmd[-1]).write_bytes(b'fakewav')
        elif cmd[0] == str(cfg.binary):
            n = sum(c[0] == str(cfg.binary) for c in calls)
            rows = ([{'offsets': {'from': 0, 'to': 596000}, 'text': 'Explicação anterior.'},
                     {'offsets': {'from': 596000, 'to': 600000}, 'text': 'Explique a função renal'}]
                    if n == 1 else [{'offsets': {'from': 0, 'to': 4000}, 'text': 'a função renal controla água'}])
            Path(cmd[cmd.index('-of')+1]+'.json').write_text(json.dumps({'transcription':rows}))
        return SimpleNamespace(stdout='', stderr='')
    w = Worker(cfg, store, runner=run, gate_fn=lambda:{'allowed':True}, free_bytes=lambda:20*1024**3)
    assert w.run_once()['state'] == 'validated'
    transcript = store.get_transcript(lesson['lesson_id'])
    assert transcript['segments'][-1]['text'] == 'Explique a função renal controla água'
    assert transcript['segments'][-1]['start'] == 596
    assert transcript['segments'][-1]['end'] == 602
    monkeypatch.setenv('STUDY_HUB_FO_DB', str(cfg.db))
    assert _transcript_allowlist(tmp_path, tmp_path/'transcripts/generated_v2') == [lesson['lesson_id']+'/v1.json']
    app = create_app(cfg.db)
    from fastapi.testclient import TestClient
    with TestClient(app) as api:
        def handler(request):
            response = api.get(str(request.url.path), params=request.url.params)
            return httpx.Response(response.status_code, json=response.json())
        async def exercise():
            with httpx.Client(transport=httpx.MockTransport(handler)) as http:
                async with Client(create_server(FOClient(http=http))) as client:
                    found = await client.call_tool('fo_search_transcripts', {'q':'renal'})
                    full = await client.call_tool('fo_get_transcript', {'lesson_id':lesson['lesson_id']})
                    status = await client.call_tool('fo_get_sync_status', {})
                    return found, full, status
        found, full, status = asyncio.run(exercise())
        assert not any(r.is_error for r in (found, full, status))
        assert 'renal' in found.content[0].text
        assert 'controla água' in full.content[0].text
        assert json.loads(status.content[0].text)['transcripts_validated'] == 1
    assert not list((tmp_path/'tmp/transcription').glob('*'))


def test_scientific_sign_conflict_is_not_silently_deduplicated():
    from fo_hub.stitching import stitch_chunks
    chunks = [{'offset_s':0,'duration_s':600,'segments':[{'start':596,'end':600,'text':'o valor é -5'}]},
              {'offset_s':598,'duration_s':20,'segments':[{'start':598,'end':604,'text':'o valor é 5 no exemplo'}]}]
    result = stitch_chunks(chunks)
    assert result['flags']
    assert len(result['segments']) == 2
    assert '-5' in result['segments'][0]['text']


def test_continuation_preserves_negative_numeric_sign():
    from fo_hub.stitching import stitch_chunks
    chunks = [{'offset_s':0,'duration_s':600,'segments':[{'start':596,'end':600,'text':'o valor é'}]},
              {'offset_s':598,'duration_s':20,'segments':[{'start':598,'end':604,'text':'o valor é -5 graus'}]}]
    result = stitch_chunks(chunks)
    assert '-5 graus' in ' '.join(s['text'] for s in result['segments'])
