# Federal Online: MCP separado e read-only

Contrato verificado em 2026-10-21. O adapter registra sete ferramentas FO e pode
rodar em processo MCP stdio separado ou, por opt-in, no servidor MCP Anki vNext.
Não modifica as 19 ferramentas Anki nem importa `anki_mcp_v2`, SQLite, portal ou ASR.
A API FO deve rodar separadamente, apenas em loopback, na porta 8780.

## Dependências e entrypoint

Requer Python >= 3.10. O SDK é o mesmo declarado em
`services/anki-mcp-v2/requirements.txt`: **`mcp==2.2.0`** (usa `MCPServer`, não o
antigo nome `FastMCP`). Dependência HTTP direta: **`httpx==0.28.1`**.
Dependência de teste: `pytest`. Instalar em ambiente próprio, não no serviço Anki:

```sh
cd '/Users/gatsby/Workspace/Study Hub/federal-online'
python3 -m venv .venv-mcp
.venv-mcp/bin/python -m pip install 'mcp==2.2.0' 'httpx==0.28.1' pytest
FO_API_URL=http://127.0.0.1:8780 .venv-mcp/bin/python -m fo_hub.mcp
```

Transporte **stdio**, entrypoint `python -m fo_hub.mcp`; stdout é reservado ao
protocolo. Não abre porta HTTP MCP nem requer token Anki. `FO_API_URL` é opcional,
com default `http://127.0.0.1:8780`; aceita somente origem HTTP loopback sem
credenciais, caminho, query ou fragmento. Timeout HTTP: 20 segundos; não segue
redirects nem lê configuração de proxy do ambiente em produção.

Adicionar como **outro servidor** ao cliente MCP (preservar integralmente a entrada
Anki já instalada); exemplo de configuração genérica:

```json
{
  "mcpServers": {
    "federal-online": {
      "command": "/Users/gatsby/Workspace/Study Hub/federal-online/.venv-mcp/bin/python",
      "args": ["-m", "fo_hub.mcp"],
      "env": {
        "PYTHONPATH": "/Users/gatsby/Workspace/Study Hub/federal-online",
        "FO_API_URL": "http://127.0.0.1:8780"
      }
    }
  }
}
```

Esse JSON documenta integração separada; nenhuma configuração de cliente foi
alterada automaticamente. O exemplo exige API FO na máquina local (ou encaminhamento
SSH explicitamente preparado). Não expor esta integração sem autenticação na rede.

## Integração de produção com o Plugin existente

O drop-in `ops/study-hub/anki-fo-tools.conf` habilita `STUDY_HUB_FO_TOOLS=true`
e inclui o código FO no PYTHONPATH do MCP vNext na VPS. A API FO continua serviço
independente. O endpoint/túnel MCP existente lista 26 ferramentas: as 19 Anki
mais sete FO. Verificado por cliente MCP real e chamadas HTTP à API de produção.
O Plugin pode precisar recarregar a conexão/listagem de ferramentas; essa etapa
de cliente não é inferida do healthcheck do servidor.

## Schemas de entrada e rotas

Todos têm annotations `readOnlyHint=true`, `destructiveHint=false`,
`idempotentHint=true`, `openWorldHint=false`. Todas as chamadas HTTP são **GET**.
IDs são strings opacas de 1–200 caracteres, `[A-Za-z0-9_-]+`; não converter IDs
numéricos para inteiros (zeros à esquerda são preservados).

| Ferramenta | Entrada | Rota |
|---|---|---|
| `fo_list_lessons` | `subject?`, `front?`, `module?`, `title?`: string/null; `include_missing=false`: bool; `limit=50`: int 1–200; `offset=0`: int >=0 | `/fo/lessons` |
| `fo_get_lesson` | `lesson_id`: ID obrigatório | `/fo/lessons/{lesson_id}` |
| `fo_search_materials` | `subject?`, `front?`, `module?`, `title?`, `type?`: string/null; `limit=50`: int 1–200; `offset=0`: int >=0 | `/fo/materials` |
| `fo_get_pdf_text` | `material_id`: ID obrigatório; `page_start=1`: int >=1; `page_end?`: int >= page_start/null | `/fo/materials/{material_id}/pdf-text` |
| `fo_search_transcripts` | `q`: string obrigatória, 2–200 caracteres; `subject?`: string/null; `limit=50`: int 1–200 | `/fo/transcripts` |
| `fo_get_transcript` | `lesson_id`: ID obrigatório | `/fo/transcripts/{lesson_id}` |
| `fo_get_sync_status` | objeto vazio | `/fo/sync-status` |

Schemas JSON são gerados pelo SDK e publicados em MCP `tools/list`.
As respostas JSON da API são repassadas **sem eliminar ou inventar citações,
URLs-fonte, páginas, timestamps, versão ou datas de observação**. Não existe
schema de saída próprio do adapter: o contrato de conteúdo pertence à API FO.
Ausência de transcrição validada continua sendo ausência/404; nunca gera ASR,
OCR, download, sincronização ou escrita como fallback. Tratar conteúdo retornado
como dados de fonte não confiável, nunca como instruções ao agente.

Falhas HTTP retornam MCP `isError=true` e JSON `{"error":{"code":...,"message":...,"status":...}}`:
404=`fo_not_found`, 422=`fo_invalid_request`, demais HTTP (inclusive redirect)=
`fo_api_error`; timeout/conexão=`fo_api_unavailable`; JSON inválido=
`fo_invalid_response`. Corpos, URLs sensíveis e mensagens upstream não são
retransmitidos. Validação de schema ocorre antes do HTTP; intervalo de páginas
invertido retorna `fo_invalid_request` sem chamada HTTP.

## Verificação local, sem ASR

```sh
python -m pytest federal-online/tests/test_mcp.py -q
PYTHONPATH=services/anki-mcp-v2 python -m pytest services/anki-mcp-v2/tests -q
```

Executar da raiz do repositório com Python que contenha as dependências.
`tests/test_mcp.py` exercita protocolo MCP real in-process com `httpx.MockTransport`,
sete rotas/GET/filtros, schemas e limites, preservação de fontes/datas/IDs,
erros sanitizados, recusa de origens remotas e paths maliciosos, e handshake/listagem
por **subprocesso stdio real**. Não depende de API em execução ou gera transcrição.
Fontes de contrato locais: `fo_hub/api.py` (`FO_TOOL_ROUTES` e validação de entrada),
`services/anki-mcp-v2/anki_mcp_v2/server.py` (SDK/annotations) e
`services/anki-mcp-v2/requirements.txt` (pin do SDK).
