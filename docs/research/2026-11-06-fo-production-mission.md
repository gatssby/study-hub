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

## Checkpoint 1 — 23:34 UTC

- Commits isolados: `f419a8a` (catálogo/materials wrapper), `bac5156` (citações, heartbeat e unit ASR), `7eb64ab` (ações openMedia4 e evidência explícita de vazio/travessia). Sem alterações Anki incluídas.
- Suíte compartilhada executada novamente: **584 passed in 7.39s**; testes do parser exercitam o JavaScript real por Node com fixtures sintéticas.
- Portal autenticado: #02/#03 possuem árvores de documentos/links/ações. Um controle `markSeen` antes de `openMedia4` ocultava a identidade/tipo do item; parser corrigido. “Zero vídeos nativos” não significa “link externo sem conteúdo”. Verificação estruturada completa ainda será relida após deploy.
- Runtime e collector implantados com comparação do hash remoto anterior e hash SHA256 posterior. Nova unit ASR instalada e validada por systemd-analyze: `RestartPreventExitStatus=3 5`, start-limit 3/15min, stop 90s, KillMode=control-group. Unit continua **inactive/disabled**, gate persistente ainda false.
- Piloto RR único ativo: PID 2918805, memória ~4,37 GB; serviço ASR persistente permanece parado. Disco 13 GiB livres; RAM disponível 17 GiB. API FO ativa PID 2918337. Nenhuma ativação persistente antecipada.
- Nova revisão independente solicitada mas recusada pelo limite global de delegação (2/2 usados). Revisão adicional será local, claramente não independente; os dois pareceres anteriores não substituem verificação da produção.

## Checkpoint 2 — 07/11, 00:13 UTC (06/11 no horário local)

- `7ca53de`: indexador e downloader ignoram árvores ocultas `.build_*`; quatro regressões cobrem os dois leitores e os dois roots legados. O default de contexto da construção direta de `Config` também é zero.
- `186963f`: aposentadoria em duas fases de observações `media_type=error`, somente com um vídeo presente do mesmo curso/item e source disponível na revisão atual. Protege qualquer transcript ou job leased/done/review; checksum do plano e transação impedem drift/aplicação parcial. Nenhum merge de bytes, download ou exclusão remota.
- Suíte real completa FO + testes do repositório + integração MCP: **601 passed in 7.73s**. Novas regressões incluem rollback SQL no meio da transação, plano adulterado, fonte stale/indisponível e preservação de review/transcript.
- Plano aplicado `113554e6a26257237d7bc221ad60fdea75d668877d33dbbeecebb85af092f29f`: **56** aliases de erro aposentados (34 Semiextensivo, 22 Extensivo; nome corrigido por JOIN do ledger em 07/11), comprovados por readback de alias/canônico/source e ledger. **1** preservado (`fo_630e1b4d2a0089f5`) por ausência de candidato elegível. Nenhum dos 56 tinha job; todos os estados da fila ficaram iguais antes/depois dessa transação.
- Contagem após a aposentadoria: **3.213 registros, 3.023 presentes, 190 ausentes**, sendo os 134 já classificados mais 56 observações de erro aposentadas. Não foram perdidas 56 aulas: os 56 vídeos canônicos e suas fontes continuam presentes/disponíveis, e os registros históricos permanecem no banco.
- Fontes: cinco HLS retornam **HTTP 404**, reproduzidos com e sem Referer do portal; dois streams são mais curtos que o catálogo; dois itens não foram reencontrados; quatro identidades não expuseram HLS na observação autenticada. Uma segunda tentativa dessas quatro terminou em TimeoutError antes da janela de espera: inconclusiva, não prova indisponibilidade definitiva. Nenhuma recuperação é declarada sem upload/byte check.
- Simuladão #02: a linha “Resolução em vídeo” tem somente controle `marcarVistoDocumentoEvent4`, sem handler de mídia/href na própria linha ou descendentes. Isso não prova curso vazio nem permite inventar stream. #03 e a execução completa do timer ainda serão relidos.
- Seis PDFs reais de seis disciplinas foram usados apenas transitoriamente em amostra de extração/sanitização; recibo em `missions/20261106-pdf-samples/summary.json`. Nenhuma página OCR foi promovida por esse teste. Materials legado permanece desabilitado; resíduo de staging e backup pre-catalog preservados por falta de prova de descarte seguro.
- Às 00:10 UTC: Anki API/MCP/sync mantêm PIDs 998234/998235/998212; ASR persistente inactive/disabled e gate false. Piloto RR único em execução, ~4,4 GB RAM, heartbeat recente. Disco: 12 GiB livres; RAM disponível 15 GiB. Não declarar PROD PASS enquanto o lote não terminar e seus resultados forem inspecionados.

## Checkpoint 3 — hardening pós-revisão (07/11 UTC)

- `8f03ff0`: preserva metadados conhecidos também em coleta parcial **não vazia**, incluindo retorno vazio com erros recuperados do checkpoint. Entradas retidas são explicitamente “não reobservadas”; ingest e downloader não podem usá-las para ressuscitar identidades, trocar revisão ou baixar URL antiga. Erros/registry/checkpoint continuam pendentes. Reconciliação diferencia contagens observadas/retidas.
- `97e6396`: remove propagação de transcrição por igualdade de caminho/tamanho. Cada alias continua na fila até download/SHA256 próprios; os chunks brutos ainda são reutilizados quando bytes e configuração coincidem. Regressões demonstraram a falha anterior e provam dois downloads/um decode para bytes iguais e dois decodes para bytes diferentes de mesmo tamanho/caminho. Unit ASR agora usa `RestartPreventExitStatus=3 4 5`.
- Suíte após esse fix: **608 passed in 7.48s**. Hashes de 35/35 módulos tinham sido conferidos antes dos dois últimos fixes; os arquivos destes deploys tiveram hashes anterior/posterior conferidos individualmente, e a matriz completa será atualizada no fechamento.
- Revisão independente de código obtida via Antigravity/Sonnet e cross-check final Gemini, sem ferramentas/mutações. O primeiro processo com ferramentas foi negado por permissão e não conta. Pareceres, reproduções e limites em `2026-11-06-fo-independent-review.md`; parecer final não encontrou bloqueador demonstrado dentro do escopo, mas não certifica qualidade acústica nem produção.
- Restart real do piloto após dois chunks duráveis: a unit antiga parou, nenhum decoder permaneceu vivo, ambos os SHA256 dos checkpoints ficaram iguais; retomada da mesma aula `fo_ce6134240d753024` v1, tentativa 2, progresso 0,605944, uma pasta temporária/um decoder e heartbeat recente. O readback posterior confirmou isso. Inspeção final de `chunks[].reused` ainda depende da conclusão da aula.
- O piloto em memória ainda carrega o worker anterior à remoção de propagação; consulta live comprovou **zero aliases elegíveis** para essa aula. Handoff limitado para o novo código antes do segundo resultado foi preparado, não é declarado concluído. Gate persistente continua false e service inactive/disabled.
- Catalog reiniciado para carregar `8f03ff0`, preservando as 223 entradas do checkpoint Extensivo e sem repetir os cursos já concluídos. Retomada observada com 509 entradas; Intensivo e Ciências Básicas concluíram com status ok. Execução global ainda em andamento.
- PDFs: amostra comprovada de **6 materiais/6 disciplinas/220 páginas/10.863.483 bytes**, todos com byte check e limpeza dos originais transitórios. Exportação saneada: 7.274 páginas, 544 excluídas, 0 rejeições; nenhuma classificação de OCR alterada. Recibos agregados, sem texto/URL/PII, em `2026-11-06-fo-live-evidence.json`.
- Smoke MCP live refeito após aposentadoria dos aliases: sete FO/19 Anki, paginação e citações em cinco disciplinas, três reviews sem texto e OCR bloqueado sem texto. Evidência em `2026-11-06-fo-mcp-smoke.json`.
- Notion retornou `CONNECTION_REQUIRED` nas buscas específicas e vazia. **Não atualizado**; proprietário AFK, sem nova tentativa de consentimento após as tentativas anteriores. Documentação local permanece a evidência disponível.

## Checkpoint 4 — 07/11, 01:41 UTC: rotação de locator DLX e reparo real

- Detectados **100** supersedings por uma alteração exclusivamente no prefixo UUID do caminho DLX do mesmo host/asset, com duração/título inalterados. As fontes ficaram stale e o ingest seguinte criou **98** fallbacks remotos adicionais. Index/vídeos foram pausados, sem parar catálogo, piloto ou Anki.
- `41c501f`: normalização compartilhada estritamente restrita ao contrato observado HTTPS `*.map.azionedge.net` + UUID + `/dlx/<asset>/master.m3u8`. Não remove IDs de asset, não generaliza para outros hosts/rotas e **não é prova de identidade de bytes**. O worker continua baixando e calculando SHA256 próprio antes de reutilizar inferência.
- Regressões RED demonstraram bump/duplicação e aposentadoria indevida de aliases com evidência protegida. O fix protege qualquer job leased/done/review e qualquer transcript. Suíte completa: **620 passed in 7.79s**. `diff --check` nos caminhos FO limpo; whitespace preexistente em arquivos Anki alheios ficou intocado.
- Cinco arquivos implantados por hashes prévios conhecidos do Git e readback SHA256 posterior. O novo helper foi publicado antes dos seus consumidores. `store.py` remoto anterior foi confirmado como o blob de `bac5156`, resolvendo a dúvida do deploy histórico.
- Readback pós-reparo: **100/100** fontes atuais reconectadas, **98/98** fallbacks novos sem evidência protegida aposentados, **13** fontes pendentes novamente (antes do reparo: 113). Nenhuma versão foi reduzida, nenhum registro/histórico foi apagado, nenhum original foi baixado novamente por esse reparo. Os 100 incrementos históricos permanecem auditáveis.
- Estado após reparo: **3.311 registros / 3.023 presentes / 288 ausentes**; os 288 são 134 aliases anteriores + 56 erros aposentados + 98 fallbacks técnicos aposentados. Os 98 não são aulas novas. Jobs: 1 done, 3.008 queued, 4 review, 1 leased, 518 superseded. Transcripts protegidos permaneceram idênticos.
- Recibos privados duráveis: `missions/20261106-ingest-url-drift/{pause,before-repair,after-repair}.json`. SHA256 de before: `8c22762aa1e2bb60956d573a8de4446e9bf94c0813918280fdae568916ea93a4`; after: `7401add3047e3647710044226318a4b1c03aade312d3c655524fc6011ced8233`.
- Index/vídeos retomados; segundo ingest real não criou registros nem mudou mídia. Próximas execuções observadas: index 01:50:06, vídeos 02:01:53, OCR 01:46:20, OneDrive 02:25:43, catálogo 03:01:13 UTC. Catálogo global ainda em execução (checkpoint Extensivo 840); não confundir último `Result=success` com conclusão da unit `activating`.
- Apenas a API FO foi reiniciada (PID 3026573); Anki API/MCP/sync mantêm PIDs 998234/998235/998212. Parecer independente Sonnet sobre esse fix não encontrou bloqueador no escopo descrito; a exigência sugerida de identidade entre dois objetos de módulo não se aplica ao helper puro sem estado mutável. Import na VPS exercitado com o diretório real da unit.
- Física concluiu em **review**: 3 flags non_monotonic + 2 ambiguous_overlap. Nenhum texto foi publicado. Geografia, sob o worker novo, avançou ao primeiro checkpoint (0,330212); o lote ainda não está concluído. ASR persistente segue false/inactive/disabled.
- Arquivamento real concluído e relido: três PDFs residuais (26.524.552 bytes) copiados imutavelmente e comparados byte a byte no OneDrive; dois originais inativos (11.073.230 bytes) removidos, com recibo. Staging de 15.451.322 bytes continua local por dependência/proveniência de manifesto, embora agora tenha cópia remota comprovada. Backup pre-catalog preservado. Evidência pública agregada em `2026-11-06-fo-pdf-archive.json`.

## Checkpoint 5 — 07/11, 01:56 UTC: readback integral e gates ainda fechados

- Nova reconciliação read-only com transação SQLite consistente: **134/134** ausências da baseline continuam aposentadas, possuem objeto no inventário remoto e ao menos um candidato canônico presente com source disponível na versão atual. Inclui **106/106** do Semiextensivo e **28/28** dos demais grupos. Pares individuais, sem caminhos privados, em `2026-11-07-fo-current-reconciliation.json`. O inventário OneDrive está vinculado ao SHA256 registrado; igualdade de caminho não foi usada para compartilhar inferência.
- Nova execução da suíte, sem inferência nem chamadas de escrita ao Anki: **620 passed in 8.26s**. Matriz completa atualizada: **36/36 módulos Python FO/renderer**, mais a unit ASR, com SHA256 local/remoto idêntico. Evidências `2026-11-07-fo-verification.json` e `2026-11-06-fo-module-hashes.json`.
- Estado real: **3.311 / 3.023 / 288** registros/presentes/ausentes; jobs **1 done, 3.008 queued, 4 review, 1 leased, 518 superseded**. Os 288 são históricos/aliases classificados, não uma nova perda de 288 vídeos.
- Física concluiu como review e comprovou restart controlado. Geografia permanece no segundo job do lote, progresso **0,330212**, tentativa 2 e heartbeat com ~30 s. Um único decoder em cgroup; serviço ASR persistente **inactive/disabled**, gate persistente/API **false**. **Não há homologação de qualidade nem PROD PASS.**
- Catálogo global permanece em execução com checkpoint Extensivo **878** entradas, crescente; não existe recibo de conclusão global. Materials permanece desabilitado; as outras agendas retomadas não substituem esse gate. Não encerrar como sucesso integral de coleta.
- Readback agregado de serviços, timers, cursor, flags, privacidade e recursos em `2026-11-07-fo-operational-readback.json`. Memória disponível **16.648.011.776 bytes**, disco livre **11.901.734.912 bytes**, quatro CPUs; carga observada ~4,4. O decoder e o coletor são limitados, e os PIDs Anki continuam preservados.
- A data UTC de 07/11 corresponde à noite de **06/11 no fuso UTC−03** até 02:59 UTC; não há evidência de relógio incorreto. Os documentos de 06/11 conservam a data de início da missão.
