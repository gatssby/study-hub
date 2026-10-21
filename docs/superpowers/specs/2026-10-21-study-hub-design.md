# Study Hub — migração operacional de 21/10/2026

## Autoridade e escopo
Execução autônoma autorizada pelo proprietário em 21/10/2026, incluindo commits, deploys e exclusões classificadas sem backups. Não há aprovação para qualquer inferência ASR, nesta sessão ou por horário futuro. `TRANSCRIPTION_ENABLED=false`; não haverá timer de transcrição nem ativação em 22/10 sem nova autorização. Nenhuma inferência no Mac.

## Objetivo e critérios
Dois domínios independentes: Anki vNext (sync oficial, Service Collection, API v2, MCP, Plugin) e Federal Online (catálogo dinâmico, PDFs, vídeos, OneDrive, API de conteúdo e fila ASR parada). Remover Cronograma e backend Anki legado após separar dependências FO. Preservar coleção/mídia, vídeos/PDFs originais, sessões/credenciais, Knowledge/Instructions e outros projetos.

## Achados iniciais verificáveis
- Workspace correto: `/Users/gatsby/Workspace/Study Hub`, branch `feat/anki-vnext-plugin`, HEAD inicial `d2af639`. Há modificações anteriores e arquivos não rastreados; não serão incluídos cegamente nem revertidos.
- VPS `oracle-vps`: ARM64, 23 GiB RAM, filesystem 46 GiB, cerca de 9,3 GiB livres no início.
- `fo-vps-worker.service` executava ASR real; foi parado/desabilitado antes da implementação. `fo-queue-api.service` em restart loop foi parado/desabilitado. Mask inicial recusado porque units locais já existem; estado conferido inactive/disabled.
- vNext escuta em 27701/8770/8771; API antiga escuta 8767.
- Scripts FO estão acoplados a `/opt/cronograma-fo` e `/home/ubuntu/anki-gpt-sync`; full-sync inclui schedule e backups, portanto NÃO será reutilizado.
- Repositório GitHub é público: dados, catálogos com URLs assinadas e credenciais não podem ser versionados.
- Conector Notion não conectado; documentação local não depende dele.

## Abordagens e decisão
1. Reescrever FO: rejeitado; desperdiça navegação, FFmpeg/rclone e sessões existentes.
2. Manter Cronograma como host: rejeitado; viola remoção integral e perpetua acoplamento.
3. Extrair core FO operacional e corrigir suas fronteiras: escolhido. Catálogo usa recursão real existente, sem allowlist de categorias, com descoberta de cursos autenticada. Ausência temporária nunca exclui conteúdo. Scripts de download são adaptados para limites de disco e não criam backups.

## Fronteiras
`federal-online/` contém código FO e testes; runtime VPS próprio em `/home/ubuntu/study-hub/federal-online`, estado em `/home/ubuntu/study-hub-state/federal-online`, configuração privada fora do Git. SQLite FO é separado de Anki, com IDs estáveis e versões de vídeo, fila deduplicada e consulta citável. API read-only em loopback. Services/timers por componente, locks, logs em journal e falhas observáveis.

Anki vNext não será movido na VPS durante cutover FO. A organização do monorepo pode manter diretórios estáveis quando imports/deploys dependam deles, documentando fronteiras em vez de quebrar produção por estética. Knowledge/Instructions têm preservação obrigatória.

## Dados e limpeza
Inventário de metadados é permitido; cópias de dados antigos não. Estado operacional necessário é movido para o novo domínio, não duplicado como retenção. Textos antigos e índices exclusivamente derivados são excluídos após identificar fontes e consumidores. Arquivos ambíguos bloqueiam só sua própria exclusão. Nada de `rclone sync --delete` ou remoção remota por ausência no catálogo.

## Transcrição
Fila pronta não implica modelo validado. Modelo será decidido por benchmark PT-BR com referência humana; preparar medição, QA e contratos agora, sem executar áudio. Dupla trava (configuração falsa e autorização manual ausente), serviço inativo/desabilitado, nenhuma programação de ativação. QA marca revisão e nunca apaga texto legítimo por heurística.

## Segurança, falhas e verificação
Não imprimir credenciais, cookies ou URLs assinadas. Catálogo com falha de login não promove vazio. PDFs verificados por magic bytes e hash, indexados com páginas. Vídeos temporários sequenciais; somente remover local após confirmação remota, sem remover vídeo original. Testes unitários/mock sem ASR; healthchecks reais após deploy; leitura de volta após cada alteração externa.

## Status
Este documento é o desenho de execução. Evidências, desvios e bloqueios finais serão registrados em `docs/migration/2026-10-21/REPORT.md`; não confundir desenho com entrega concluída.
