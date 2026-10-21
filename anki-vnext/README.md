# Anki GPT vNext

Domínio independente do Federal Online. Código mantido em caminhos estáveis:

- `services/anki-api-v2/anki_api_v2`: API de gerenciamento e actor da Service Collection.
- `services/anki-mcp-v2/anki_mcp_v2`: 19 ferramentas Anki; não substituir pelo MCP legado.
- `apps/anki-gpt/gpt-knowledge`: Knowledge, Instructions e regras editoriais preservadas integralmente.
- `apps/anki-gpt`: arquivos do addon antigo com alterações locais anteriores ainda sob classificação; não são o servidor oficial vNext.

Produção: `/home/ubuntu/anki-vnext/{api,mcp,syncserver,sync-data,service}`. Não mover/editar coleção e mídia para reorganizar o Git. Sync oficial na porta 27701; API v2 na 8770 (`/v2/health` autenticado); MCP na 8771, túnel independente.

## Integração FO

FO tem banco, API e jobs próprios. Suas sete ferramentas read-only usam `federal-online/fo_hub/mcp.py` e consultam a API FO na porta local 8780. A conexão de consulta FO não deve alterar as 19 ferramentas Anki nem introduzir snapshots/fila de operações legada. Transcrição FO permanece desabilitada até autorização explícita.

## Preservação editorial

Preservar os sete arquivos Knowledge 01–07, `INSTRUCTIONS_CURTAS_GPT_BUILDER.md`, `MANUTENCAO_GPT_KNOWLEDGE.md` e referências de recorrência. A migração futura para Skill deve reutilizar essas fontes, não inventar regras substitutas. O relatório da migração registra inventário e hashes.
