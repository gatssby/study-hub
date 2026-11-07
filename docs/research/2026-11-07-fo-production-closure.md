# Federal Online — fechamento operacional da missão AFK

**PROD BLOCKED. Não houve ativação do ASR persistente nem promoção de review.**

Snapshot final: **2026-11-07T04:03:50.402666+00:00**. Baseline: 06/11 22:52 UTC, mesma contagem de aulas/queue informada em 02/11. Horários abaixo em UTC; após 03:00 UTC já é 07/11 também no fuso UTC−03. A tentativa global do catálogo terminou às **03:58:43 UTC**, com exit 1 por vazio não verificável do Simuladão #02; não ficou um job longo aguardando conclusão. Isto encerra a execução nos gates reais, não declara implantação integral concluída.

## Nove condições de entrega

| # | Estado | Evidência e limite |
|---|---|---|
| 1 | BLOCKED | Reconciliação dos 134 originais PASS: 106 Semiextensivo + 28 demais, objetos remotos e candidatos current/available, sem present artificial. Os 288 históricos têm classificação. Registro global com 10 cursos ok e #02 incomplete: não há aceite de cobertura integral. |
| 2 | BLOCKED | 100 fontes técnicas reconectadas, inventário remoto vinculado a SHA; 13 fontes históricas continuam sem disponibilidade comprovada e estão listadas com a observação específica. |
| 3 | BLOCKED | 7.274 páginas text_only reavaliadas pelo sanitizador v5, zero novas rejeições/alterações; 544 bloqueadas; amostra real 6 PDFs/220 páginas. Staging/rollback ainda local; fluxo materials periódico e preservação acadêmica integral não homologados. |
| 4 | BLOCKED | Cinco timers ativos/enabled e next-run relido; index/OneDrive/OCR/videos com últimas execuções success. Catálogo terminou parcial, exit 1 pelo #02, sem OOM; próximo calendário 09:00:32 UTC. Materials disabled, execução legada failed/signal. |
| 5 | BLOCKED | Lote REAL multidisciplinar concluído com dois recibos; recuperação/cursor/limpeza observados. Física e Geografia ficaram review; qualidade não homologada. |
| 6 | BLOCKED | ASR persistente inactive/disabled, gate false no ambiente/API, zero leases/decoders. Restart, novo job e continuidade pelo permanente NOT TESTED; não ativados após QA falhar. |
| 7 | PASS | 628 testes; 36/36 módulos + unit SHA iguais; sete FO/19 Anki; HTTP/MCP validado serve texto, cinco reviews/OCR bloqueados sem texto; paginação/citações e cinco disciplinas verificadas. |
| 8 | PASS | Margem observada acima da reserva de 4 GiB, limites cgroup, tmp vídeo/ASR vazio e Anki com PIDs/saúde preservados. Projeção de crescimento de todo ASR e exaustão real de disco NOT TESTED. |
| 9 | PASS | Código a50cdb9 e primeiro pacote documental eef4da5 publicados; SHA exato da branch relido. Recibo em 2026-11-07-fo-publication-readback.json; o complemento final tem readback separado ao encerrar, sem hash autorreferente. Notion não atualizado: connected=false/CONNECTION_REQUIRED. |

## Aulas antes → depois, sem contagem dupla

Contagem de registros (inclui aliases): **3.213 → 3.311**; presentes **3.079 → 3.023**; ausentes/históricos **134 → 288**. A diferença é explícita: **134 + 56 aliases de erro + 98 fallbacks técnicos = 288**. Os 98 novos registros surgiram durante a rotação de locator e foram aposentados, não são aulas novas. Nenhum dos 56 aliases de erro tinha job; evidências protegidas não foram aposentadas.

| Curso / identidade | Total antes → depois | Presentes antes → depois | Ausentes depois |
|---|---|---|---|
| Simulados e Resolução de Provas | 422 → 422 | 422 → 422 | 0 |
| Redação UFPR 2026 | 24 → 24 | 24 → 24 | 0 |
| Extensivo UFPR 2026 | 1228 → 1228 | 1228 → 1206 | 22 |
| Semiextensivo UFPR 2026 | 873 → 873 | 873 → 839 | 34 |
| Matemática Básica | 25 → 25 | 25 → 25 | 0 |
| Intensivo UFPR 2026 | 424 → 424 | 424 → 424 | 0 |
| Ciências Básica | 26 → 26 | 26 → 26 | 0 |
| Materiais exclusivos de medicina | 51 → 51 | 51 → 51 | 0 |
| Simuladão UFPR #01 - Gratuito | 2 → 2 | 2 → 2 | 0 |
| remote:Extensivo UFPR 2026 | 12 → 12 | 2 → 2 | 10 |
| remote:base-intensivo-ufpr | 9 → 107 | 1 → 1 | 106 |
| remote:ciencias-basica | 3 → 3 | 1 → 1 | 2 |
| remote:extensivo-ufpr-2026 | 5 → 5 | 0 → 0 | 5 |
| remote:matematica-basica | 1 → 1 | 0 → 0 | 1 |
| remote:materiais-exclusivos-medicina | 1 → 1 | 0 → 0 | 1 |
| remote:semiextensivo-ufpr-2026 | 106 → 106 | 0 → 0 | 106 |
| remote:simulados-resolucao-de-provas | 1 → 1 | 0 → 0 | 1 |

**134/134** ausências antigas têm objeto remoto observado e ao menos um candidato canônico presente/current/available; **106/106** do Semiextensivo estão vinculados individualmente em `2026-11-07-fo-current-reconciliation.json`, `baseline_134_readback.pairs`. Não foram somados às 839 entradas canônicas. Mesmo caminho/metadata remoto sustenta a classificação de aliases, não prova igualdade de bytes para ASR: o worker continua baixando e calculando SHA antes de compartilhar inferência.

34/34 cliques históricos foram reobservados ok. Aposentadoria com ledger: 34 Semiextensivo + 22 **Extensivo**. Um erro sem candidato elegível (`fo_630e1b4d2a0089f5`) permanece preservado; oito `not_launched`/inválidos sem substituto não viraram vídeo artificialmente.

## Fontes, disponibilidade e Simulados

- **13 pendentes → 13 pendentes históricos**: 5 falhas HLS/404, 2 streams com duração menor que catálogo, 2 falhas de observação autenticada exata e 4 cliques autenticados sem HLS capturado. Os probes abaixo são de **06/11, 23:42–23:43 UTC**; o status API/DB de **07/11, 04:03 UTC** mantém exatamente essas 13 identidades pendentes. Não são novas sondagens HTTP às 04:03 nem prova de remoção/não lançamento. Há **12 media_id distintos**, não garantia de 13 arquivos físicos diferentes. Evidência `pending_sources`/`2026-11-06-fo-live-evidence.json`.

| lesson_id | media_id | Observação preservada / motivo de bloqueio |
|---|---|---|
| fo_d7c2b39c34abedb8 | 12805 | observation_failed, etapa exact_item, AssertionError; inconclusivo |
| fo_985aa43ff95b238a | 12837 | observation_failed, etapa exact_item, AssertionError; inconclusivo |
| fo_4bafd25c15bf6598 | 16357 | HLS 404 direto/com referer/ffprobe |
| fo_c0b8df75e2eb86fe | 16361 | HLS 404 direto/com referer/ffprobe |
| fo_6df4907c116802ed | 16363 | HLS 404 direto/com referer/ffprobe |
| fo_be0bb4362ced545d | 16365 | HLS 404 direto/com referer/ffprobe |
| fo_5c623b7dd096e89b | 16367 | HLS 404 direto/com referer/ffprobe |
| fo_c02b9e2f9df56c60 | 14423 | duração stream 1610.334459 s versus portal 2071 s; cobertura não homologada |
| fo_e5cb97fa3eaf2d1a | 10102 | clique autenticado sem HLS capturado; inconclusivo |
| fo_5d66dfb4bf27853f | 10103 | clique autenticado sem HLS capturado; inconclusivo |
| fo_cf08fb1b5d45e70b | 4368 | duração stream 2769.03 s versus portal 2949 s; cobertura não homologada |
| fo_fcad555740669e31 | 12478 | clique autenticado sem HLS capturado; identidade preservada |
| fo_626434837c181089 | 12478 | clique autenticado sem HLS capturado; não unificar por media_id sem prova |

- **100/100** fontes técnicas reconectadas após normalização limitada ao contrato Azion DLX; **98/98** fallbacks técnicos sem evidência protegida aposentados, nenhuma versão reduzida. Segundo ingest idempotente. Isso não equivale a recuperar 100 vídeos ou os 13 anteriores; **0 dos 13 foi comprovadamente recuperado**.
- Inventário OneDrive atual com SHA vinculado ao início da listagem; o hash do snapshot confere. O preflight identificou 2.995 jobs elegíveis e 13 sem source; não promete integridade de bytes de milhares de originais não baixados.
- Simuladão #03: vazio de vídeo **nativo** verificado no escopo do coletor; não significa curso pedagogicamente vazio nem resolução externa assistida. #02: nova execução às 03:37:05 UTC manteve **incomplete**, zero entradas publicadas e `empty_verified=false`; controles externos ainda não dão prova independente de vazio. Esse é o motivo específico do exit global 1, não uma perda das aulas conhecidas nem novo OOM.
- Descoberta dinâmica de categorias/anos/cursos e preservação em coleta parcial têm regressões; não se introduziu allowlist de cursos.

## QA, fila e lote Round Robin real

Jobs: **done 1, queued 3.008, review 5, superseded 518, processing/leased 0**. Antes: 1/3.012/3/318/0. O único validado continua `fo_3f92db67195e2bbf` — Vetores IV. Nenhum review foi promovido.

- Índice 0: `fo_ce6134240d753024` v1 → review; cursor ciclo 2 → 3; temporários 0.
- Índice 1: `fo_0978f8f807c122f4` v1 → review; cursor ciclo 3 → 4; temporários 0.

Os dois recibos e `completed.json` existem; o segundo terminou às 02:35 UTC. Física retomou dois chunks por bytes/configuração iguais e completou os restantes; Geografia tem quatro chunks e resultado próprio. Cursor avançou, review da Física não impediu Geografia. Foram observados limites de 300% CPU/12 GiB, um decoder por vez, heartbeat e limpeza; evidências brutas privadas preservadas. Não confundir os pilotos systemd transitórios com a unit persistente que não foi iniciada nesta missão.

| Disciplina/aula | ID | Alertas atuais | Decisão |
|---|---|---|---|
| Biologia - Teoria — Bioquímica | fo_135c415d8080927f | 2 duplicate_segment | review; sem publicação |
| Espanhol - Teoria — Identificación de ideas | fo_4cc5e44ffb6dc603 | 2 non_monotonic, 1 ambiguous_overlap | review; sem publicação |
| Filosofia - Teoria — Mito de Er | fo_d9f369413fd5cf40 | 1 non_monotonic, 1 ambiguous_overlap | review; sem publicação |
| Física - Teoria — Unidades de medida e Análise Dimensional | fo_ce6134240d753024 | 3 non_monotonic, 2 ambiguous_overlap | review; sem publicação |
| Geografia - Teoria — Cartografia I | fo_0978f8f807c122f4 | 1 non_monotonic, 1 ambiguous_overlap | review; sem publicação |

Cinco recortes focais reais: Bioquímica 1156/8 e 1166/8 s; Espanhol 588/32 e 1186/36 s; Filosofia 588/32 s. Glicerídeo/repetição científica não homologado acusticamente; não aprovar por regex, apagar fala ou ajustar timestamp sem prova. Espanhol foi efetivamente decodificado com idioma `pt`; exige validação de idioma/acústica, não alteração global automática.

Configuração observada: large-v3, beam 5/best-of 5, max_context=0, fallback off, VAD off, chunks 600 s/overlap 2 s. **WER/CER null; referência humana ausente.** VAD, preservação de fala em silêncio/ruído e precisão acadêmica não estão homologados. Breaker: 0 falhas, 4 reviews consecutivas, não aberto nesta observação; não foi mascarado ou reinicializado.

## PDFs, privacidade e resíduos

172 materiais / 7.818 páginas, todas com política v5:

| Qualidade | Páginas | Exposure |
|---|---|---|
| text | 7.270 | text_only |
| low_text | 4 | text_only |
| ocr_review | 523 | blocked |
| ocr_empty | 1 | blocked |
| blocked | 20 | blocked |

Total **7.274 text_only / 544 blocked**, zero ocr_needed. Sanitização serving-time, bloqueio de campos nominais ambíguos e testes sintéticos de CPF/nomes permanecem. Smoke real retornou texto vazio em página OCR bloqueada e citações nas liberadas. Amostra real de seis originais/seis disciplinas, 220 páginas/10.863.483 bytes: byte check remoto e limpeza dos originais de invocação passaram. Isso não certifica fórmulas, tabelas, imagens, pixels/metadata do original ou todas as páginas; não houve liberação OCR por mera execução.

Auditoria adicional read-only às **03:21:51 UTC**: todas as **7.274 páginas text_only** passaram novamente pelo sanitizador de produção v5, com **0 rejeições, 0 alterações de texto e 0 alterações de exposure**; 544 excluídas da liberação. Seleção vinculada por SHA256; nenhum original aberto e nenhuma página publicada/reclassificada. Evidência `2026-11-07-fo-pdf-privacy-final.json`. Esse resultado é da política automática atual, não revisão visual/acadêmica nem garantia sobre pixels/metadata dos originais.

Três resíduos selecionados, **26.524.552 bytes**, foram arquivados imutavelmente e comparados byte a byte no OneDrive; dois originais inativos (**11.073.230 bytes**) removidos mediante equivalência/ausência de uso. O staging de **15.451.322 bytes** tem cópia remota mas permanece por dependência/proveniência de manifesto. Backup pre-catalog (~614 MB) protegido, não descartado por tamanho. Não existe aceite de “todos os originais apenas remotos”. Nenhuma exclusão remota; snapshots falhos vazios removidos, zero bytes de originais nessas remoções. Recibo agregado `2026-11-06-fo-pdf-archive.json`.

Materials timer continua desabilitado: o wrapper opt-in transitório e seu teste não substituem uma execução nova homologada do caminho periódico produtor→upload→extração saneada→cleanup. Não reiniciar o coletor legado que pode repopular originais locais.

## Timers e recuperação real do catálogo

| Componente | Timer active/enabled | Serviço/resultado | Última saída ou início | Próxima execução observada |
|---|---|---|---|---|
| catalog | active/enabled | inactive/exit-code (1, #02) | Sat 2026-11-07 03:58:43 UTC | Sat 2026-11-07 09:00:32 UTC |
| materials | inactive/disabled | failed/signal | Wed 2026-10-28 05:03:13 UTC | — |
| index | active/enabled | inactive/success | Sat 2026-11-07 04:02:44 UTC | Sat 2026-11-07 04:11:30 UTC |
| onedrive | active/enabled | inactive/success | Sat 2026-11-07 03:29:36 UTC | Sat 2026-11-07 04:25:20 UTC |
| ocr | active/enabled | inactive/success | Sat 2026-11-07 03:55:19 UTC | Sat 2026-11-07 04:06:05 UTC |
| videos | active/enabled | inactive/success | Sat 2026-11-07 04:02:00 UTC | Sat 2026-11-07 05:01:01 UTC |
| transcription | sem timer; disabled | inactive/dead, MainPID=0 | sem timestamp registrado | nenhuma; gate false |

API FO active/running. ASR persistente inactive/dead/disabled, MainPID=0, `TRANSCRIPTION_ENABLED=false` no ambiente e boolean false em `/fo/sync-status`; autorização em arquivo presente mas não constitui gate. `worker --check-only`: dependências prontas, gate.allowed=false; nenhuma inferência/lease. Não existe timer ASR. Restart/resultado de novo job pelo permanente: **NOT TESTED**.

OOM real do catálogo às 02:24 UTC, pico 1,9 GiB no cgroup de 2 GiB. Commits `34f38bf`/`a50cdb9` limitam o lifecycle por 200 novas linhas duráveis, preservam erros intermediários e propagam falhas. Não são um teto de requests nem prova de ausência de leak. Deploy com SHA guard preservou exatamente o checkpoint de 1.012 entradas. **Extensivo concluiu 1.070 às 02:54:31 UTC; Semiextensivo 839 às 03:36:17; Simulados/Resolução 422 às 03:58:43**, todos status ok. Matemática/Medicina/Redação/#01 também concluíram novas execuções. Foram observadas **seis rotações reais de navegador**, nenhum novo evento OOM e NRestarts=0. Pico final **1.946.517.504 bytes (1,81 GiB)** no limite mantido de 2 GiB; CPUQuota 100%. Nenhum checkpoint parcial permaneceu. O registro final tem **10 ok / 1 incomplete** (#02); tentativa concluída não equivale a catálogo global aceito. Recibo `2026-11-07-fo-catalog-global-final.json`.

O calendário do catalog.timer é `*-*-* 03,09,15,21:00:00`, Persistent=true, RandomizedDelaySec=120. O evento 03:00 foi consumido com o mesmo serviço em curso; NextElapse ficou vazio enquanto SubState=running. Após a saída 1 por #02, **MainPID=0/auto-restart** não foi contado como coleta ativa. Cancelei apenas o retry pendente de 15 min, sem interromper processo em execução, para não repetir indefinidamente descoberta sem evidência nova. Timer permaneceu enabled/active/waiting; próxima execução **09:00:32 UTC**, relida após a ação; Result=exit-code/ExecMainStatus=1 preservados. Nenhuma frequência ou limite foi alterado.

Depois da publicação dos cursos, **dois ingests incrementais reais** concluíram success. O SHA do estado de negócio (identidades, versões, presença/metadados das aulas e estado/tentativas de todos os jobs, sem timestamps de observação) foi idêntico antes e depois de ambos. Contagens, 13 fontes pendentes, gate false e cinco reviews permaneceram iguais. Evidência `2026-11-07-fo-final-ingest-idempotency.json`.

## Recursos, testes e publicação

- Quatro CPUs; carga [0.1708984375, 0.48876953125, 0.7177734375]; RAM disponível **22585659392 bytes (21.03 GiB)** de 23.41 GiB; disco livre **11993427968 bytes (11.17 GiB)** de 45.37 GiB. Reserva do worker 4 GiB, além da maior fonte/temporário.
- Temporários ASR e vídeos: **0 arquivos / 0 bytes**; snapshots residuais de arquivo 0. Journal: Archived and active journals take up 287.6M in the file system.. Sem novos backups de corpus. Não se preencheu o disco para simular exaustão num host compartilhado.
- Anki API/MCP/sync PIDs **998234/998235/998212**, inalterados; `anki_health=ok`, coleção aberta. Nenhum write Anki nem alteração de serviços/projetos terceiros.
- Suíte repetida no fechamento: `services/anki-mcp-v2/.venv/bin/python -m pytest federal-online/tests tests services/anki-mcp-v2/tests -q` → **628 passed in 7.79s**. 36/36 hashes Python FO/renderer e unit ASR novamente iguais. Código final `a50cdb9ea72397c2be6948a7fc622b3c3dee6a28`.
- Dois erros históricos não tinham diagnóstico capturado: exit 2 de uma suíte anterior e exit 1 de um start do index. Não se inventou causa retroativa; a execução final é 628 pass (não os marcos anteriores 608/620), e execuções reais posteriores do index concluíram success. Isso prova o estado atual, não explica retrospectivamente os dois retornos.
- MCP: 26 tools = 7 FO + 19 Anki. Cinco disciplinas com citações, paginação disjunta em duas páginas, validado HTTP 200 e cinco reviews HTTP 404/sem texto. A busca multidisciplinar é de materiais; não se fabricou transcrição validada de outras disciplinas.
- Revisões/disposições em `2026-11-06-fo-independent-review.md`; achados externos não foram aceitos cegamente. Notion **não atualizado**: status reconfirmado connected=false, sem credenciais/contas; não se solicitou login AFK nem simulou sincronização.
- Stage/commits somente dos caminhos FO/documentação da missão; dirty worktree alheio preservado. Primeiro pacote `eef4da5854856e7889941c81adc85d06fa8ff96e` publicado sem force e ref remota relida. Recibo público prova esse pacote; o complemento documental final é verificado por readback separado ao encerrar, sem referência circular ao próprio commit.

Commits anteriores ao fechamento documental:

- f419a8a fix(fo): preserve incomplete catalogs and classify retired source aliases
- bac5156 fix(fo): cite validated transcript spans and heartbeat long ASR leases
- 7eb64ab fix(fo): distinguish native-video emptiness from incomplete portal traversal
- 7ca53de fix(fo): exclude unpublished catalog builds from ingest and video acquisition
- 186963f fix(fo): retire proven failed-observation aliases with atomic evidence ledger
- 8f03ff0 fix(fo): retain known catalog metadata without fabricating new observations
- 97e6396 fix(fo): require fresh byte identity before completing transcript aliases
- c12affc docs(fo): record real reconciliation, privacy samples and independent safety review
- 41c501f fix(fo): preserve DLX asset identity across rotating authorization paths
- f2b31f4 docs(fo): publish verified production checkpoints and remaining gates
- 34f38bf fix(fo): bound catalog browser lifetime by durable progress
- a50cdb9 fix(fo): preserve traversal uncertainty across browser batches
- eef4da5 docs(fo): close real RR pilots and record blocked production gates

## Retomada segura, por prioridade

1. **Qualidade ASR:** preservar os cinco reviews, validar acusticamente janelas/fronteiras/idioma e obter referência humana; corrigir defeitos reproduzíveis com regressões. Não retirar flags ou habilitar serviço por testes verdes. Depois dos gates, usar `federal-online/transcription/ACTIVATION.md`; ainda faltam restart e resultado real pelo permanente.
2. **Catálogo:** manter os cinco timers habilitados; catálogo tem calendário confirmado para 09:00:32 UTC. Resolver o modelo/controles externos do #02 sem fabricar vazio ou HLS. Após nova evidência/correção, pode-se antecipar somente a coleta incremental com `ssh oracle-vps 'sudo systemctl start --no-block study-hub-fo-catalog.service'`; não duplicar serviço em execução. Não confundir o exit 1 já classificado com OOM ou com tarefa global ainda rodando.
3. **13 fontes:** novas observações autenticadas dirigidas apenas aos IDs pendentes; não repetir download de stream curto nem declarar lançamento/remoção por timeout.
4. **Materials/PDF:** homologar o wrapper como caminho periódico novo; reconciliar dependências do staging/pre-catalog antes de remoção. Revisão acadêmica/privacidade por página antes de liberar 544 bloqueadas.
5. **Notion:** sincronizar seção 10 e resumo quando houver conexão autorizada; este relatório é a fonte Git disponível, não comprova atualização Notion.

Check-only sem áudio/lease/gate de produção: executar o comando com `TRANSCRIPTION_ENABLED=false`, caminhos de modelo/binário e `--check-only` já especificados em ACTIVATION.md. **Não há comando seguro para ativar ASR antes de resolver o bloqueio de qualidade.**
