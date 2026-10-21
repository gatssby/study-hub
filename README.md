# Study Hub

Dois domínios independentes: Anki GPT vNext (sync oficial, Service Collection, API v2, MCP e Plugin) e Federal Online (catálogo dinâmico, PDFs, vídeos, OneDrive, API de conteúdo e fila de transcrição).

Cronograma FO foi descontinuado e removido. Não executar procedimentos históricos que o recriam.

## Fronteiras

- `anki-vnext/`: mapa do domínio; pacotes em `services/anki-api-v2` e `services/anki-mcp-v2`, preservando imports/deploys estáveis.
- `apps/anki-gpt/gpt-knowledge`: Knowledge, Instructions e metodologias editoriais preservados.
- `federal-online/fo_hub`: banco FO, API somente leitura, fila e integração MCP.
- `federal-online/portal`: core operacional extraído da produção e descoberta dinâmica.
- `ops/study-hub`: units systemd e migração/preparação.
- `contracts`, `packages`, `tests`: contratos e verificações.

## Produção

Anki vNext permanece em `/home/ubuntu/anki-vnext`, sem mover coleção/mídia.
FO: código `/home/ubuntu/study-hub/federal-online`, estado `/home/ubuntu/study-hub-state/federal-online`, ambiente privado `/home/ubuntu/.config/study-hub`, venv `/home/ubuntu/study-hub-venv`.
API FO: `127.0.0.1:8780`, estado `/fo/sync-status`.

O repositório é público. Não versionar dados, PDFs, vídeos, sessões, credenciais ou URLs assinadas.
API Anki antiga na porta 8767 foi retirada. Arquivos locais legados com alterações anteriores não são apagados cegamente; pendências constam no relatório.

## Transcrição bloqueada

`TRANSCRIPTION_ENABLED=false`. Nenhuma autorização decorre da data 22/10/2026. Não existe timer de transcrição. Testes somente com fixtures/mocks; inferência exige nova autorização explícita e execução na VPS.
Pesquisa: `docs/research/2026-10-21-fo-asr-benchmark.md`.

## Verificação

FO: `python -m pytest federal-online/tests -q`, com dependências próprias.
Anki vNext: testes de `services/anki-api-v2` e `services/anki-mcp-v2` em seus ambientes.
Evidências: `docs/migration/2026-10-21/REPORT.md`.
