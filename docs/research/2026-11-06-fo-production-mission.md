# Federal Online — missão operacional de 06/11/2026

## Checkpoint 0 — preflight (22:52–23:05 UTC)

Autorização desta sessão abrange correções, deploys FO, pilotos ASR reais e ativação persistente somente após gates. Preservar g20261029a, fila, reviews, recibos, originais OneDrive e todas as alterações alheias ao FO. Nenhum reset/rebuild integral ou ação Anki autorizado.

- Branch confirmada `feat/study-hub-migration`, HEAD `3627d60`; remote origin GitHub gatssby/study-hub. Working tree contém alterações Anki e arquivos de terceiros que não integram esta missão.
- VPS: uptime 29 dias; 23 GiB RAM, 21 GiB disponíveis; 13 GiB livres em volume 46 GiB (73% ocupado). Sem swap.
- API FO active/enabled, PID 3721141. Anki: API 998234, MCP 998235, sync 998212; preservar PIDs e disponibilidade.
- Baseline revalidada: 3.213 aulas / 3.079 presentes / 134 ausentes; jobs 1 done, 3.012 queued, 3 review, 318 superseded. ASR inactive/disabled; gate persistente false; nenhum leased.
- Timers index/onedrive/ocr/videos ativos; catalog/materials sem next-run. Materials Result=signal/15 (SIGTERM), não há prova de OOM.
- Reconciliação read-only delegada e relida: 134 aliases aposentados com candidatos presentes pelo mesmo caminho exato, incluindo os 106 Semiextensivo; preservar present=0. 34/34 falhas de clique históricas reobservadas ok. Fontes pendentes continuam 13, classificadas individualmente no relatório irmão.
- Portal: sessões salvas redirecionam Simuladão #02/#03 ao login; HTTP 200 não prova curso vazio. Autenticação nova pelo runner será testada sem expor credenciais.
- PDFs: 7.818 páginas, 7.274 liberadas reavaliadas sob política 5 sem alteração; 544 seguem bloqueadas. Staging 15.451.322 bytes não tem QuickXor igual aos três candidatos de mesmo tamanho; não excluir. Backup pre-catalog preservado até prova de dispensabilidade.

## Sequência incremental e rollback

1. Corrigir e testar runner para vazio/coleta limitada fail-closed; preservar JSON anterior/checkpoint/last_ok_at.
2. Inspecionar individualmente reviews e evidências acústicas; executar somente recortes necessários, com lock ASR e cgroup, sem promoção por regex.
3. Homologar lote RR real mantendo ordem pedagógica/cursor, revisão isolada, limites e limpeza. Se falhar gate crítico, ASR persistente permanece off.
4. Deploy por arquivos FO selecionados e hashes, smoke após deploy; timers somente após execução segura verificada. Nunca ativar materials legado que repopula originais persistentes.
5. Testes integração/API/MCP isolados, hashes, inventário ferramentas, documentação/commits FO e push sem force.

Rollback de código: registrar hashes remotos antes da cópia; implantar somente versões conhecidas e rastreadas, sem rsync --delete. Não restaurar DB antigo sobre fila corrente. Reverter código por arquivo original commitado, mantendo evidência. Parar unit piloto/ASR e gate false quando necessário; não alterar Anki.

## Evidências relacionadas

- `2026-11-06-fo-catalog-reconciliation.{md,json}`: cobertura, 134 aliases, 13 fontes, 34 cliques, limites da prova.
- `2026-11-06-fo-materials-report.md` e JSONs irmãos: privacy/OCR, staging, retenção e wrapper transitório ainda não ativado.

## Gates de entrega (em execução)

1. Catálogo e classificação completa: em verificação.
2. Vídeos e fontes remotas: em verificação.
3. PDFs transitórios e privacy/OCR: parcial; legado não reativado.
4. Timers essenciais: parcial.
5. Lote RR real: pendente de homologação.
6. ASR persistente: NOT TESTED; permanece desligado até gates.
7. API/MCP, testes e hashes: em verificação.
8. Headroom e isolamento: baseline saudável; revalidar ao final.
9. Roadmap, commit/push e Notion: pendente.

Nenhum PASS de produção é inferido da saída de subagentes ou de testes sintéticos. Checkpoints seguintes registrarão execução e readback reais.
