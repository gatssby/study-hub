"""FO MCP protocol tests: only the HTTP boundary is mocked; no ASR or Anki."""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

CASES = [
    ("fo_list_lessons", {"subject": "Bio", "front": "A", "module": "M", "title": "T", "include_missing": True, "limit": 2, "offset": 3}, "/fo/lessons"),
    ("fo_get_lesson", {"lesson_id": "001"}, "/fo/lessons/001"),
    ("fo_search_materials", {"subject": "Bio", "type": "pdf", "limit": 2}, "/fo/materials"),
    ("fo_get_pdf_text", {"material_id": "001", "page_start": 2, "page_end": 3}, "/fo/materials/001/pdf-text"),
    ("fo_search_transcripts", {"q": "cell", "subject": "Bio", "limit": 2}, "/fo/transcripts"),
    ("fo_get_transcript", {"lesson_id": "001"}, "/fo/transcripts/001"),
    ("fo_get_sync_status", {}, "/fo/sync-status"),
]


def call_tool(name, arguments, handler):
    from fo_hub.mcp import FOClient, create_server
    async def exercise():
        with httpx.Client(transport=httpx.MockTransport(handler)) as http:
            async with Client(create_server(FOClient(http=http))) as client:
                return await client.call_tool(name, arguments)
    return asyncio.run(exercise())


@pytest.mark.parametrize("name,args,path", CASES)
def test_tools_are_get_only_with_exact_api_parameters(name, args, path):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"items": [], "observed_at": "2026-10-21"})
    result = call_tool(name, args, handler)
    assert result.is_error is not True
    assert len(requests) == 1
    req = requests[0]
    assert req.method == "GET" and req.url.path == path
    expected = {k: str(v).lower() if isinstance(v, bool) else str(v)
                for k, v in args.items() if k not in {"lesson_id", "material_id"}}
    assert all(req.url.params[k] == v for k, v in expected.items())
    assert all(v != "None" for v in req.url.params.values())


def test_protocol_exposes_exactly_seven_readonly_tools_and_schema_constraints():
    from fo_hub.mcp import create_server
    async def exercise():
        async with Client(create_server()) as client:
            return (await client.list_tools()).tools
    tools = {t.name: t for t in asyncio.run(exercise())}
    assert set(tools) == {row[0] for row in CASES}
    for tool in tools.values():
        assert tool.annotations.read_only_hint is True
        assert tool.annotations.destructive_hint is False
        assert tool.annotations.idempotent_hint is True
    assert tools["fo_get_lesson"].input_schema["properties"]["lesson_id"]["type"] == "string"
    assert tools["fo_list_lessons"].input_schema["properties"]["limit"]["maximum"] == 200
    assert tools["fo_search_transcripts"].input_schema["properties"]["q"]["minLength"] == 2


def test_fo_tools_can_register_alongside_existing_anki_nineteen():
    # Registration is intentionally persistent; isolate it from Anki's tests.
    root=Path(__file__).resolve().parents[2]
    script='''import asyncio
from mcp import Client
from fo_hub.mcp import register_tools
from anki_mcp_v2.server import mcp
async def exercise():
    async with Client(mcp) as client:
        before={t.name for t in (await client.list_tools()).tools}
    assert len(before)==19
    register_tools(mcp)
    async with Client(mcp) as client:
        after={t.name for t in (await client.list_tools()).tools}
    assert len(after)==26 and before<=after
    assert len(after-before)==7 and all(n.startswith('fo_') for n in after-before)
asyncio.run(exercise())
'''
    env={**os.environ,'PYTHONPATH':os.pathsep.join((str(root/'federal-online'),str(root/'services/anki-mcp-v2')))}
    subprocess.run([sys.executable,'-c',script],env=env,check=True,capture_output=True,text=True,timeout=30)


def test_anki_entrypoint_activates_opt_in_fo_registration(monkeypatch):
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'services/anki-mcp-v2'))
    from anki_mcp_v2 import server
    import fo_hub.mcp as fo
    calls=[]
    monkeypatch.setenv('ANKI_API_TOKEN','test-only')
    monkeypatch.setenv('STUDY_HUB_FO_TOOLS','true')
    monkeypatch.setattr(fo,'register_tools',lambda target:calls.append(target))
    monkeypatch.setattr(server.mcp,'run',lambda **kwargs:None)
    server.main()
    assert calls==[server.mcp]
from mcp import Client


@pytest.mark.parametrize("url", ["https://remote.example", "http://localhost.evil:8780", "http://127.0.0.1:8780/path", "http://user:pass@127.0.0.1:8780", "http://0.0.0.0:8780"])
def test_client_refuses_non_loopback_or_credentialed_origins(url):
    from fo_hub.mcp import FOClient
    with pytest.raises(ValueError):
        FOClient(url)


@pytest.mark.parametrize("name,args", [("fo_get_lesson", {"lesson_id": "../sync-status"}),
    ("fo_get_transcript", {"lesson_id": "a/b"}), ("fo_get_pdf_text", {"material_id": "a?x=1"}),
    ("fo_list_lessons", {"limit": 201}), ("fo_search_transcripts", {"q": "x"}),
    ("fo_get_pdf_text", {"material_id": "1", "page_start": 3, "page_end": 2})])
def test_invalid_inputs_never_reach_http(name, args):
    def fail(request):
        pytest.fail("invalid input reached HTTP")
    assert call_tool(name, args, fail).is_error is True


@pytest.mark.parametrize("status,code", [(404, "fo_not_found"), (422, "fo_invalid_request"),
                                         (503, "fo_api_error"), (302, "fo_api_error")])
def test_http_errors_are_sanitized(status, code):
    def handler(request):
        return httpx.Response(status, text="SECRET upstream body", headers={"location": "https://remote.example"})
    result = call_tool("fo_get_sync_status", {}, handler)
    assert result.is_error is True
    payload = json.loads(result.content[0].text)
    assert payload["error"]["code"] == code
    assert payload["error"]["status"] == status
    assert "SECRET" not in result.content[0].text


@pytest.mark.parametrize("failure,code", [("timeout", "fo_api_unavailable"), ("json", "fo_invalid_response")])
def test_transport_and_invalid_json_errors_are_structured(failure, code):
    def handler(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("SECRET", request=request)
        return httpx.Response(200, text="SECRET not JSON")
    result = call_tool("fo_get_sync_status", {}, handler)
    assert result.is_error is True
    assert json.loads(result.content[0].text)["error"]["code"] == code
    assert "SECRET" not in result.content[0].text


def test_main_defaults_to_stdio(monkeypatch):
    import fo_hub.mcp as module
    calls = []
    class Server:
        def run(self, **kwargs):
            calls.append(kwargs)
    monkeypatch.setattr(module, "create_server", lambda: Server())
    module.main()
    assert calls == [{"transport": "stdio"}]

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_stdio_entrypoint_handshake_and_seven_tools():
    async def exercise():
        from mcp.client.stdio import StdioServerParameters
        command = StdioServerParameters(command=sys.executable, args=["-m", "fo_hub.mcp"],
                                        cwd=str(Path(__file__).resolve().parents[1]))
        async with Client(command) as client:
            tools = (await client.list_tools()).tools
            assert {t.name for t in tools} == {row[0] for row in CASES}
    asyncio.run(exercise())



def test_lesson_roundtrip_preserves_sources_and_dates():
    from fo_hub.mcp import FOClient, create_server

    payload = {"lesson_id": "001", "source_url": "https://source.example/lesson/001",
               "observed_at": "2026-10-21T12:00:00Z", "citation": {"page": 2}}
    requests = []
    def handle(request):
        requests.append(request)
        return httpx.Response(200, json=payload)

    async def exercise():
        with httpx.Client(transport=httpx.MockTransport(handle)) as http:
            async with Client(create_server(FOClient(http=http))) as mcp:
                result = await mcp.call_tool("fo_get_lesson", {"lesson_id": "001"})
                assert result.is_error is not True
                assert json.loads(result.content[0].text) == payload
    asyncio.run(exercise())
    assert len(requests) == 1
    assert requests[0].method == "GET"
    assert str(requests[0].url) == "http://127.0.0.1:8780/fo/lessons/001"
