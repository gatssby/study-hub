"""Synthetic worker -> SQLite -> HTTP/MCP, without transcript file publication."""
import asyncio
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
import wave

from fastapi.testclient import TestClient
import httpx
from mcp import Client
from mcp.types import TextContent
import pytest

from fo_hub.api import create_app
from fo_hub.mcp import FOClient, create_server
from fo_hub.stitching import stitch_chunks



def mcp_text(result):
    item, = result.content
    assert isinstance(item, TextContent)
    return item.text


@pytest.mark.parametrize('interrupt,remote_changed', [(False, False), (True, False), (False, True)])
def test_two_chunk_stitch_is_queryable_only_for_current_source(tmp_path, mvp_case, interrupt, remote_changed):
    calls = []
    decoded_offsets = []
    audio_length = 0

    def run(cmd, **kwargs):
        nonlocal audio_length
        calls.append(cmd)
        assert kwargs['pass_fds'] == (case.worker.lock_fd,)
        if cmd[:2] == ['rclone', 'copyto']:
            Path(cmd[3]).write_bytes(b'fakevideo')
        elif cmd[:2] == ['rclone', 'hashsum']:
            return SimpleNamespace(stdout=f'{case.source_quickxor}  {Path(cmd[3]).name}\n', stderr='')
        elif cmd[:2] == ['rclone', 'lsjson']:
            proof = 'f' * 40 if remote_changed else case.source_quickxor
            return SimpleNamespace(stdout=json.dumps({'IsDir': False, 'Size': 9,
                                                       'Hashes': {'quickxor': proof}}), stderr='')
        elif cmd[0] == 'ffprobe':
            return SimpleNamespace(stdout=json.dumps({'streams': [{'index': 0}],
                                                       'format': {'duration': 602}}), stderr='')
        elif cmd[0] == 'ffmpeg' and cmd[-1].endswith('.wav'):
            filters = cmd[cmd.index('-af') + 1]
            sample_count = int(filters.split('atrim=end_sample=', 1)[1].split(',', 1)[0])
            offset_ticks = round(float(cmd[cmd.index('-ss') + 1]) * 16000)
            audio_length = sample_count // 16000
            with wave.open(cmd[-1], 'wb') as wav:
                wav.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
                wav.writeframes(b'\xff\x7f' * sample_count)
            return SimpleNamespace(stdout='', stderr=f'[Parsed_ashowinfo_3 @ 0x42] n:0 pts:{offset_ticks} '
                                                      f'rate:16000 nb_samples:{sample_count}\n')
        elif cmd[0] == str(case.cfg.binary):
            decoded_offsets.append(0 if audio_length == 600 else 598)
            if interrupt and decoded_offsets == [0, 598]:
                raise subprocess.TimeoutExpired(cmd, kwargs['timeout'])
            rows = ([{'offsets': {'from': 0, 'to': 596000}, 'text': 'Explicação anterior.'},
                     {'offsets': {'from': 596000, 'to': 600000}, 'text': 'Explique a função renal'}]
                    if audio_length == 600 else
                    [{'offsets': {'from': 0, 'to': 4000}, 'text': 'a função renal controla água'}])
            Path(cmd[cmd.index('-of') + 1] + '.json').write_text(json.dumps({'transcription': rows}))
        else:
            raise AssertionError(f'unexpected command: {cmd!r}')
        return SimpleNamespace(stdout='', stderr='')

    case = mvp_case(runner=run)
    if interrupt:
        result = case.worker.run_once()
        assert (result['state'], result['reason']) == ('queued', 'whisper_timeout')
        assert case.store.get_transcript(case.lesson_id) is None
        assert case.queue.retry(case.lesson_id)
    result = case.worker.run_once()
    if remote_changed:
        assert result['state'] == 'queued' and result['reason'] == 'source_changed_before_publication'
        assert case.store.get_transcript(case.lesson_id) is None
        return
    assert result['state'] == 'done' and result['reused_chunks'] == int(interrupt)
    assert decoded_offsets == ([0, 598, 598] if interrupt else [0, 598])
    transcript = case.store.get_transcript(case.lesson_id)
    assert transcript['segments'][-1]['text'] == 'Explique a função renal controla água'
    assert transcript['segments'][-1]['start'] == 596
    assert transcript['segments'][-1]['end'] == 602
    assert [c[1] for c in calls if c[0] == 'rclone'] == ['copyto', 'hashsum'] * (1 + interrupt) + ['lsjson']
    assert not (tmp_path / 'transcripts').exists()

    with TestClient(create_app(case.cfg.db)) as api:
        def handler(request):
            response = api.get(str(request.url.path), params=request.url.params)
            return httpx.Response(response.status_code, json=response.json())

        async def exercise():
            with httpx.Client(transport=httpx.MockTransport(handler)) as http:
                async with Client(create_server(FOClient(http=http))) as client:
                    found = await client.call_tool('fo_search_transcripts', {'q': 'renal'})
                    full = await client.call_tool('fo_get_transcript', {'lesson_id': case.lesson_id})
                    status = await client.call_tool('fo_get_sync_status', {})
                    return found, full, status

        found, full, status = asyncio.run(exercise())
        assert not any(r.is_error for r in (found, full, status))
        assert 'renal' in mcp_text(found)
        assert 'controla água' in mcp_text(full)
        assert json.loads(mcp_text(status))['transcripts_validated'] == 1
        # The revision did not change, but a different source cannot inherit the transcript.
        with case.store.conn:
            case.store.conn.execute('UPDATE lesson_video_sources SET size=size+1')
        assert api.get(f'/fo/transcripts/{case.lesson_id}').status_code == 404
        assert api.get('/fo/transcripts', params={'q': 'renal'}).json() == {'items': []}
        found, full, status = asyncio.run(exercise())
        assert json.loads(mcp_text(found)) == {'items': []}
        assert full.is_error and 'controla água' not in mcp_text(full)
        assert json.loads(mcp_text(status))['transcripts_validated'] == 0
    assert all(not list(path.iterdir()) for path in case.worker.roots())


def test_scientific_sign_conflict_is_not_silently_deduplicated():
    chunks = [{'offset_s': 0, 'duration_s': 600, 'segments': [{'start': 596, 'end': 600, 'text': 'o valor é -5'}]},
              {'offset_s': 598, 'duration_s': 20, 'segments': [{'start': 598, 'end': 604, 'text': 'o valor é 5 no exemplo'}]}]
    result = stitch_chunks(chunks, exact=True)
    assert result['flags']
    assert len(result['segments']) == 2
    assert '-5' in result['segments'][0]['text']


def test_continuation_preserves_negative_numeric_sign():
    chunks = [{'offset_s': 0, 'duration_s': 600, 'segments': [{'start': 596, 'end': 600, 'text': 'o valor é'}]},
              {'offset_s': 598, 'duration_s': 20, 'segments': [{'start': 598, 'end': 604, 'text': 'o valor é -5 graus'}]}]
    result = stitch_chunks(chunks, exact=True)
    assert '-5 graus' in ' '.join(s['text'] for s in result['segments'])
