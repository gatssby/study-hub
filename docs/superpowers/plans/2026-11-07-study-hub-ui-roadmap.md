# Study Hub — roadmap UI e observabilidade
Atualização: 20/11/2026. Documento ativo; substitui apenas o planejamento de interface, sem apagar histórico técnico da reconstrução FO.

## Decisão

Começar pela **Visão geral operacional** (read-only) e, em seguida, criar Biblioteca → Aula → PDFs/Busca → integração Anki. Interface web responsiva, desktop-first, visual sóbrio, modos claro/escuro, busca e estados explícitos. A futura UI deve mostrar indisponibilidades como avisos, não como bloqueios globais. Não reproduzir o Cronograma FO legado.

## Baseline verificada na VPS — 07/11 ~14h10 BRT

- ASR: service active/enabled; gate true, um worker, Round Robin.
- Transcrições: 12 aprovadas, 2.999 queued, 3 review e 1 leased; 519 superseded excluídas do denominador. Progresso global do conjunto de 3.015 jobs ativos ~0,4%; novas revisões/aulas alteram o denominador.
- PDFs: 174 materiais, 8.457 páginas; 7.912 com texto liberado (93,6%), 545 bloqueadas. Entre as bloqueadas: 523 OCR-review, 20 blocked, 1 OCR-empty e 1 OCR-pending. Os originais privados permanecem no OneDrive.
- Vídeos: 3.001 fontes atuais disponíveis no banco e 2.252 objetos de vídeo no último índice. São grãos diferentes: **não representam percentual de downloads**. Status atual indica 14 fontes pending, mas deferrals classificados historicamente somam 13; reconciliar por ID.
- Timers: catálogo, materiais, vídeos, índice, OneDrive e OCR ativos; ~11 GiB livres na VPS.

## M0 — Monitor operacional de terminal (entregue nesta etapa)

- [x] Criar ops/study-hub/fo_monitor.py, dependente apenas de Python e SSH, consulta somente leitura ao FO API, SQLite mode=ro e systemd; atualização periódica.
- [x] Exibir barras de transcrições aprovadas, progresso da aula corrente e páginas PDF liberadas; mostrar fila, revisões, fontes/objetos, serviços e disco.
- [x] Não inventar % de download; distinguir fontes, jobs e arquivos físicos.
- [x] Incorporar as métricas ao dashboard web, sem acesso SSH direto do navegador (Sprint 2).

Comando: cd "$HOME/Workspace/Study Hub" && python3 ops/study-hub/fo_monitor.py --interval 20.

## M1 — Dashboard web operacional (P0; publicado na Sprint 2 em https://study.gatssby.com.br)

- [x] Aplicação isolada read-only, publicada com TLS próprio + Basic Auth no subdomínio study; observer loopback 3401.
- [~] Sem sidebar (fiel ao Figma original); IA futura: Início, Biblioteca, Aula, PDFs, Sistema. Layout: sidebar Visão geral, Biblioteca, Transcrições, PDFs, Sincronização, Configurações; topo com hora do último snapshot e saúde dos serviços.
- [ ] Cards: aula em processamento (nome, disciplina, versão, percentual e chunks), fila (done, queued, leased, review, deferred), PDFs (aprovados/bloqueados), fontes e disponibilidade, status de timers e disco.
- [x] Poll a cada 15–30 segundos, renderizar estados offline/stale com horário; carga de consulta baixa e read-only; evitar locks de escrita.
- [~] Recibos de estado final de vídeos/OneDrive exibidos (verificados/erro/indisponível); bytes/velocidade em tempo real pendentes. Instrumentar eventos de download/sync reais com estado, bytes concluídos/totais quando disponíveis, horário e destino (vídeo, PDF, OneDrive). Etapas: discovered, queued, downloading, uploaded, verified, deferred, failed. Apenas com telemetria suficiente, mostrar barra de download e velocidade; não usar 2.252/3.001 como progresso.
- [~] Ritmo mediano, aulas/áudio 24 h e ETA com faixa interquartil entregues; série temporal 7 dias pendente. Série temporal (24 h/7 dias), taxa real de transcrições e downloads e histórico de falhas. ETA só quando mensurável; nunca inventar prazo para 3 mil aulas.
- [x] API agregada autenticada de monitoramento, separada das sete rotas FO/MCP; não expor URLs assinadas, nomes pessoais, PDFs brutos, dados privados de review ou segredos.
- [x] Smoke no cliente real: normal, sem conexão, partial/incomplete, job que muda de estado, review fail-closed, privacidade.

## M2 — Biblioteca e aula (MVP entregue em 20/11/2026)

- [x] Navegar curso → disciplina → módulo → aula no catálogo existente, com pesquisa sem distinção de acentos e filtro de disciplina.
- [x] Distinguir validada, na fila, em processamento, em revisão, indisponível e ainda não lançada.
- [x] Exibir metadados e segmentos com timestamps somente da revisão atual aprovada e com fonte vigente. Nenhuma transcrição privada de revisão é servida. Aulas legadas que só têm nomes derivados de caminhos privados aparecem com rótulos neutros.
- [ ] Fora deste MVP: frente e ordem do portal, motivo/cooldown/última verificação, avisos QA e relações com materiais oficiais.
- [ ] Incorporar reprodução/autorização de vídeo somente depois de definir contrato seguro para originais e URLs temporárias.

Publicado em `study.gatssby.com.br` no release `library-mvp-PQlJ1e9c`. O mesmo Basic Auth e HTTPS protegem o frontend e os dois novos GETs do observador SQLite somente leitura: `/api/library` e `/api/lessons/<id>`. O painel existente permanece acessível.

Aceite em produção (20/11/2026, 22:20 UTC): navegador autenticado navegou do painel pela biblioteca, selecionou curso, disciplina e módulo, pesquisou e abriu uma aula validada com 237 segmentos exibidos com timestamps. Catálogo: 3.060 aulas, 105 validadas na verificação pré-publicação. Aula em revisão retornou zero segmentos; rotas protegidas sem credencial retornaram 401; TLS válido. Suite focada: 46 testes Python, 23 frontend e build TypeScript/Vite aprovados. Observer, FO e n8n responderam; worker de transcrição e Anki mantiveram os mesmos PIDs, e os sete timers dos coletores permaneceram registrados.

## M3 — PDFs e pesquisa (P1)

- [ ] Visualização de texto paginado e citável, filtros por tipo/disciplina/aula; indicação de páginas bloqueadas/OCR em revisão.
- [ ] Validar preservação acadêmica por amostragem priorizada: fórmulas, tabelas, diagramas, imagens, enunciados, alternativas, ordem de leitura.
- [ ] Manter saneamento v5; jamais fornecer PDF original privado como fallback. Derivados visuais demandam sanitização e validação reais.

## M4 — Anki e operações avançadas (P2)

- [ ] Integração consultiva ao Anki GPT vNext por API/contratos, sem acesso direto à coleção pelo frontend FO.
- [ ] Reprocessamento/rechecagem manual e ações administrativas somente com autenticação, confirmação e trilha de auditoria.
- [ ] Piloto e revisão de permissões antes de abrir a aplicação fora do localhost.

## Backlog técnico remanescente (não bloqueia iniciar a UI)

1. PDFs: 545 páginas bloqueadas, mais QA acadêmica visual. Textos liberados são consultáveis, mas a preservação integral de matemática/diagramas não foi comprovada.
2. Downloads: instrumentação de eventos/bytes por mídia ainda ausente; não há progresso global confiável de transferência.
3. ASR: 53 jobs em review (20/11), 49 com bloqueio grave; reavaliação automática evidence-only ativa desde 20/11, sem aprovar nada sem evidência. Casos de mistura PT/ES e termos científicos seguem pendentes de verificação acústica focal. Não atrasar MVP por perfeccionismo; manter QA grave bloqueante e warnings visíveis.
4. Disponibilidade: itens inacessíveis continuam em cooldown com motivo; conferir a diferença entre 14 pending e 13 deferrals anteriores.
5. Capacidade: ~6,2 GiB livres em 20/11 contra reserva de ~4,75 GiB; crescimento atual negativo (~-165 MB/dia). Margem estreita: monitorar retenção de temporários; estimativa de duração só baseada em throughput.
6. Materiais: coletor rotativo com ciclos reais aprovados, mas cobertura integral dos PDFs e recuperação de falha retida não foram homologadas.
7. Segurança: primeiro dashboard somente leitura, sem expor a porta 8780 publicamente.

## Aceite do dashboard web

Métricas compatíveis com API/banco e denominadores explícitos; polling leve; estado offline/stale; nenhum vazamento de originais/PII/QA review; atualização contínua sem Hermes; testes direcionados e um smoke end-to-end. Evitar testes excessivos e mudanças em serviços Anki/n8n.

## Atualização de domínio e fidelidade visual — 07/11/2026

A arquitetura de implantação, contrato visual e sequenciamento foram desdobrados em `docs/superpowers/plans/2026-11-07-study-hub-domain-figma-ui.md`.

- **Produção desejada:** `https://gatssby.com.br/`, preservando `https://n8n.gatssby.com.br/` e demais vhosts sem alteração; DNS raiz ainda sem A record no snapshot. Nginx/TLS já gerenciam n8n por vhost separado.
- **Design vinculante:** Community file `1531598093643920564`; reprodução fiel do layout após acesso aos frames originais (leitura web automatizada retornou 403). Não partir de inspiração genérica.
- **Primeiro sprint:** auditoria anti-regressão n8n, obtenção de arquivo Figma duplicado, contrato visual, scaffold local-only, sem mudar DNS/Nginx/n8n. Após aceite: backend read-only/telemetria real, host isolado, TLS/auth e cutover com smoke n8n.

## Sprint 1 — implementação local verificada em 07/11/2026

Entregues shell/Dashboard React/TypeScript/Vite em `apps/study-hub-web` e observador local allowlisted em `ops/study-hub/web/observer.py`. Preview127.0.0.1:3400, backend127.0.0.1:3401; browser não acessa FO/SQLite. Dados reais com polling20s, indisponível/null, loading/offline/stale e serviços com falhas explícitas; sem percentual fictício de download. Última conclusão OneDrive permanece desconhecida.

Figma recuperado no Safari autenticado e Remix do proprietário confirmado: Make `kd36an23RU8hgKDxF55sTR`. Preview original da autora inspecionado, contrato/tokens/screenshots em `docs/design/`. Sem sidebar no original; respeitada composição header/quatro resumos/grid2 colunas.10 medidas selecionadas iguais, sem alegar pixel-perfect global. MCP desktop3845 responde, mas não entrega layers/frames de Make.

Build estático e6 testes frontend +5 testes observer aprovados, smoke browser desktop/mobile integrado200. n8n pré/pós raiz/health200, container/PIDs/hashes preservados. Nenhum DNS/Nginx/serviço da VPS alterado. Templates futuros, DNS exato, autenticação/TLS e rollback documentados no roadmap principal e `ops/study-hub/web/README.md`. Publicação e biblioteca continuam próximas fases, não entregues por este sprint.

## Recuperação operacional do MVP — 18/11/2026

- **Transcrição:** em 12/11, três objetos distintos retornaram 585 bytes em cada tentativa do `rclone`, em destinos novos, e abriram o disjuntor. A causa específica da resposta do transporte não ficou registrada. Em 18/11, os três objetos originais passaram em tamanho, QuickXor e `ffprobe`. A revisão rejeitada passa a aguardar 24 h sem consumir tentativas nem bloquear outras aulas; falhas de autenticação e erros não reconhecidos continuam sujeitos ao disjuntor. O fingerprint antigo foi arquivado e removido sob lock. Modelo, checkpoints, Round Robin, QA e exclusões Inglês/Espanhol mantidos. Dos 84 jobs `done` históricos, 77 são das revisões atuais e 7 foram substituídos; não há reconciliação necessária.
- **Disco:** sob `videos.lock`, removidos somente 19 parciais obsoletos sem descritores abertos, com revisão sucessora verificada no OneDrive. Bytes livres antes/depois: 4.792.598.528 → 6.618.906.624; reserva calculada no momento: 5.097.523.696 bytes. O coletor descarta apenas parciais próprios recém-rejeitados após registrar a falha, preservando arquivos completos usados na retomada. Quatro arquivos sem prova suficiente para remoção e os dois snapshots SQLite históricos foram preservados.
- **Materiais:** falha de upload em 13/11 deixou um ciclo pendente que bloqueava as próximas execuções; a causa do upload original não foi preservada. O serviço recuperou o recibo sob os locks existentes, verificou o PDF de 1.321.024 bytes no OneDrive, indexou 201 páginas `text_only` uma única vez, avançou a rotação de 9 para 10 e limpou o staging. O timer voltou a aguardar o próximo ciclo. As 551 páginas bloqueadas para OCR não foram retrabalhadas.
- **Dashboard:** apresenta falha do serviço de materiais separadamente do timer, a última transcrição aprovada e alertas de espaço calculados com o espaço livre atual. O prazo da telemetria opcional preserva o dashboard básico sob o limite de CPU do observador; detalhes de ritmo/download/revisão podem ficar indisponíveis. Smoke: Study Hub HTTPS retorna o desafio Basic esperado (401 sem credenciais), observer interno retorna 200, n8n `/healthz` retorna 200 e os serviços Anki vNext permanecem ativos. Sem mudanças em autenticação, DNS, portas ou n8n.
- **Aceite ASR (21:02 UTC):** `fo_c7bae61ed53e1e65` v1 concluiu em `review` sob a política de QA existente. O mesmo worker, sem reinício e com o disjuntor fechado, iniciou a decodificação de `fo_edf66441311ee288` v1 como único job ativo. O dashboard reportou 77 revisões aprovadas, 35 em revisão, 2.750 na fila e 1 em processamento. O disco tinha 6.497.533.952 bytes livres durante o próximo job.

## Fechamento do sprint MVP — 20/11/2026

Cinco melhorias incrementais entregues, testadas e implantadas na VPS sem novos serviços, dependências ou mudanças em autenticação/DNS/portas/Nginx/n8n:

1. `f41b4c4` — Reavaliação automática limitada de reviews no loop do worker. Evidence-only: não decodifica, não baixa e não executa ASR; skip determinístico por SHA da entrada + versão da política QA; backoff de erro de 24 h e limite de 3 tentativas; preserva as exclusões Inglês/Espanhol e nunca toca no disjuntor. Resultados persistidos em `transcription_review_log`.
2. `33a2e14` — Snapshot horário de saúde operacional (`health_telemetry.py`, executado pelo `study-hub-storage.service`) e alertas de estado no dashboard: disjuntor, falha/parada/stall/ociosidade da transcrição, falha de materiais, OneDrive desatualizada ou com falha, reserva baixa, risco de crescimento e deferrals persistentes. Contagens de review por severidade sobre o total de artefatos atuais (não a lista truncada). Observações desconhecidas permanecem null; alertas são de estado corrente, não fluxo de eventos.
3. `614ac34` — Uma passada de review limitada na inicialização do worker, após `recover()`.
4. `5a61883` — Telemetria de pipeline dentro do orçamento do observador: cache horário de sumários por artefato (`telemetry/pipeline-artifacts.json`, identidade tamanho+mtime, idade máxima 4.500 s, fallback para parse completo), produzido por `pipeline_telemetry.py --refresh-cache` no mesmo serviço horário. `pace`, `downloads`, `review_counts` e `reassessment` voltaram a ser publicados no dashboard.
5. `e328a69` — Varredura conservadora de parciais de vídeo abandonados de revisões não atuais (`video_runtime.py`), preservando as regras existentes de evidência e retenção.

### Verificação local e de implantação (20/11)

- Testes direcionados: FO 658 aprovados; telemetria pipeline/health/storage 27; observer/production 15; frontend 15 (vitest); `tsc --noEmit` limpo.
- SHA-256 dos seis arquivos implantados (`worker.py`, `video_runtime.py`, `pipeline_telemetry.py`, `health_telemetry.py`, `observer.py`, `production.py`) idênticos entre o HEAD local e a VPS. Unidade de storage instalada com as três ExecStart (storage, health, refresh-cache); cache de artefatos presente e atualizado.
- Frontend publicado: release `5a61883-20261120073239` (o commit `e328a69` é apenas backend).

### Estado de produção verificado — 20/11 ~21h15 UTC

- **Transcrição:** worker novo (PID 797393 desde 07:47:42 UTC, NRestarts=0) com `whisper-cli` ativo; disjuntor fechado; 1 lease. Passada de review na inicialização (07:47:46) e passadas periódicas do loop registradas no journal. Jobs: 111 done, 2.896 queued, 53 review, 1 leased, 752 superseded. Projeção de versões atuais no dashboard (21:12 UTC): 104 done, 2.715 queued, 50 review, 1 em processamento.
- **Reavaliação automática conservadora:** 14 registros em `transcription_review_log` (14 aulas distintas), todos `outcome=review`, política QA v4, `attempts=1`; 0 validadas, 0 erros. Nenhum review foi publicado sem evidência e a política QA não foi alterada. Os 49 reviews graves permanecem bloqueados.
- **Reviews projetados:** 50 artefatos atuais — 49 graves, 1 desconhecida.
- **Ritmo (observação 20/11):** 152 amostras comparáveis; mediana ~2,64× a duração do áudio; 12 aulas e ~4,6 h de áudio nas últimas 24 h; ETA ~154 dias (faixa 147–161 dias) para o áudio ativo restante — estimativa por throughput, não prazo; 30 jobs com duração desconhecida.
- **Downloads:** 2.996 fontes verificadas (~439 GB verificados); recibos de estado final, sem progressão em tempo real.
- **Saúde (recibo 20:33 UTC):** `alerts=[]`, materiais `success`, `pdf_sync` e `transcript_sync` verificados, OneDrive ~6 min, 1 deferral ativo, 0 persistentes, crescimento ~-165 MB/dia.
- **Disco (21:14 UTC):** 6.634.176.512 bytes livres (~6,2 GiB) > reserva de 5.097.523.696 bytes (~4,75 GiB).
- **Timers:** catálogo, materiais, vídeos (hourly), índice, OneDrive, OCR e storage ativos; últimos ciclos dos coletores com `Result=success`.
- **Endpoints:** HTTPS sem credenciais retorna o desafio Basic esperado (401); `GET /api/dashboard` autenticado com a credencial vigente retorna 200 (21:12 UTC), sem rotação nem mudança de configuração; observer interno 200; n8n `/healthz` 200.

### Limitações remanescentes do MVP

- 49 reviews graves seguem bloqueadas (repetição sistemática, timestamps inválidos, contradições acústicas). A reavaliação evidence-only não pode aprová-las sem nova evidência; a verificação acústica focal humana continua pendente.
- PDFs: 545 páginas bloqueadas no baseline 07/11 (523 OCR-review, 20 blocked, 1 empty, 1 pending) aguardam revisão visual; preservação integral de fórmulas/diagramas não comprovada. Nenhuma página é liberada por regra.
- Instrumentação de bytes/velocidade de download em tempo real ausente; série temporal de 7 dias pendente.
- Reconciliação por ID entre fontes pending e deferrals históricos (14 vs 13) ainda aberta; snapshots SQLite históricos e janelas ASR de validação aguardam classificação/arquivamento.
- Margem de disco estreita (~6,2 GiB livres vs reserva ~4,75 GiB); crescimento atual negativo, mas a retenção de temporários precisa de monitoramento contínuo.
- O MVP da Biblioteca/Aula (M2) foi publicado no mesmo host; M3 (PDFs/Busca) e M4 (Anki) seguem pendentes.

## Fechamento — recuperação de metadados e reviews + inventário completo (21/11)

Missão autônoma de correção de metadados e recuperação conservadora de reviews, seguida de inventário estruturado completo. Escopo restrito a qualidade de dados; nenhuma feature nova de UI.

### Metadados (Priority A) — commit `e65926f`

- **Causas-raiz:** (1) a Biblioteca mascarava todo título contendo `/` — 381 títulos acadêmicos legítimos (intervalos de ano `2023/2024` e termos `oxidação/redução`, `Realismo/Naturalismo`); (2) objetos OneDrive em caminhos legacy criavam identidades fallback `remote:` duplicadas de aulas portal já presentes, com subject/module/title derivados de pastas privadas.
- **Correção:** `library.py` permite uma barra acadêmica em títulos (mantém máscara estrita para subject/front/module e fragmentos path-like); `metadata_recovery.py` reconcilia deterministicamente cada fallback remoto a um canonical portal único (source_ref + título, tiers exact/year/separator), retirando duplicatas desprotegidas e backfilling das protegidas; `ingest.py` reaplica metadados canônicos a cada sync; `store.py` preserva metadados verificados não-vazios em syncs não-autoritativos.
- **Aplicação production (sob index.lock, transacional, preimage+ledger):** 46 fallbacks resolvidos, 0 ambíguos → **38 retirados, 8 backfilled** (7 com transcrição validada + 1 em review). Presentes: 3065 → **3027** (3019 portal + 8 aliases protegidos).
- **Verificação:** projeção da Biblioteca com **0** subject/module/title mascarados; 381 títulos com barra visíveis; aliases protegidos com nomes/hierarquia canônicos e agrupados no curso canonical; nenhum vazamento (onedrive:/https:///.mp4/produto-pacote). **Sobrevive à sincronização:** ciclo de ingest com `renamed=0, created=0, missing=0`; retirados permanecem present=0.

### Reviews de transcrição (Priority B) — commit `61572cd`

- **Auditoria:** 58 jobs review (53 aulas) no início; bloqueios `ngram_repetition`, `token_repetition`, `duplicate_segment`, `bad_timestamp`, `acoustic_repetition_unconfirmed`, `text_during_measured_silence`.
- **Recuperação evidence-bound:** o whisper.cpp preenche a última linha do chunk final até ~start+30s, ultrapassando a duração ffprobe → `bad_timestamp` sintético. `normalize_final_padding` clamp apenas o end do segmento final ao bound de áudio provado (cópias, identidade verificada nos originais, texto intacto, fail-closed se re-stitch inconsistente); flags `bad_timestamp` resolvidas viram observação `timestamp_correction` documentada. **5 aulas bloqueadas só por isso foram validadas** (done 117→122): `fo_a32f71f7cfab8eb4`, `fo_40f898e1a4ad480e`, `fo_349df4e4f5027e2f`, `fo_197613d80e6e04fd`, `fo_f731f5eeb1d14ea8`. Originais imutáveis; recibos qa-v5 com SHA do input.
- **QA preservada:** `QA_POLICY_VERSION` 4→5 sinaliza mudança de lógica de processamento (thresholds de `classify_qa` inalterados); review_log SHA+política evita reavaliação indefinida de evidência idêntica.
- **Retidos com razão precisa (50):** 11 repetições isoladas já com `acoustic_repetition_unconfirmed` (checagem acústica anterior não confirmou fala genuína — reexecutar janelas idênticas daria resultado idêntico); 39 loops sistemáticos de decoder / alucinações em silêncio medida (exigem re-decode completo, fora de escopo). Nenhuma aprovação forçada; nenhuma repetição genuína removida.

### Plugin (Priority B5)

- `GET /fo/transcripts/{id}` das aulas recuperadas: 200, segmentos com end clampado, `qa.passed=true`, sem vazamento. `GET /fo/lessons/{id}` dos aliases backfilled: metadados canônicos. Busca `q=cinemática` retorna aula recuperada. **115 transcrições validadas atuais disponíveis**; browse exclui retirados; gate `TRANSCRIPTION_ENABLED=true` verificado via API.

### Inventário completo (tarefa queued) — `docs/research/exports/federal-online/`

- `lessons-current.csv` + `lessons-current.jsonl`: **3027 aulas canônicas atuais** (IDs únicos, == SQLite present=1, sem amostragem). `lessons-historical-and-aliases.csv`: **371** (38 retire_alias com mapeamento canonical, 277 fallback remoto histórico, 56 ausentes do catálogo). `catalog-summary.md`: índice hierárquico Curso→Disciplina→Frente→Módulo→Aula + métricas + validação.
- **9 cursos canônicos, 102 disciplinas, 140 módulos**; 115 validadas; 0 metadados incompletos; 2881 com ordem verificável (`ordem` do catálogo); 22 sem fonte de vídeo verificada; 159 aulas em Inglês/Espanhol (excluídas). Materiais PDF (172) são de nível disciplina, sem vínculo por aula → `pdf_count=null`. Nenhum caminho privado/URL assinada/credencial exportado; course_ids baseados em URL neutralizados para slug.

### Estado de produção verificado — 21/11

- **Worker:** ativo (PID 2011009 após restart controlado), 1 lease novo, job interrompido re-enfileirado com chunks duráveis preservados. Jobs: 122 done, 2852 queued, 50 review, 1 processing, 808 superseded.
- **Saúde:** `study-hub-fo-api`, `study-hub-observer` ativos; Anki vNext (api/mcp/mcp-tunnel/sync) ativos; n8n (docker) Up 6 days.
- **Disco:** ~6,20 GiB livres > reserva de 4 GiB.
- **Testes:** 679 aprovados na passada de integração focada (FO + observer); 3 falhas apenas ambientais (disco local da Mac < reserva; módulos não tocados pela missão). SHA-256 dos arquivos implantados idênticos ao HEAD.
- **Commits pushed:** `e65926f` (metadados), `61572cd` (timestamps) em `origin/feat/study-hub-migration`.

### Limitações remanescentes

- 50 reviews exigem nova evidência acústica (parâmetros de decode distintos ou re-transcrição focal autorizada); não recuperáveis com evidência inalterada.
- 22 aulas atuais sem fonte de vídeo verificada; 146 sem ordem de catálogo verificável.
- PDFs de nível disciplina não vinculados por aula; revisão visual de páginas OCR segue pendente (baseline 07/11).
- `get_lesson` por ID direto ainda retorna registros present=0 (comportamento pré-existente da API; excluídos de browse/busca); nenhum vazamento nas aulas recuperadas.

## Piloto de revisão acústica Parakeet — 22/11/2026 UTC

- **Validado:** Parakeet TDT v3 pt-BR INT8 + Silero no Oracle ARM64, CPU-only (`onnx-asr` 0.11.0, ORT 1.24.4), runtime isolado e ~856 MiB instalados. Smoke de fala sintética PT-BR: 4,069 s de áudio, 3,011 s de VAD + ASR, 1,055 GiB de RSS de pico. Não mede precisão ou custo em aulas reais.
- **Bloqueado em produção:** o Whisper legado detém `transcription.lock` durante todo o loop, inclusive enquanto dorme. O handoff cooperativo foi testado no Oracle com locks descartáveis, sem intervenção no Whisper em execução. O código não foi carregado pelo processo vivo. A troca deve ocorrer somente em uma janela autorizada com o processo anterior já quiescido, sem decoder/lease ativo e preservando checkpoints. Nenhum serviço/timer contínuo foi ativado.
- **Coorte:** os cinco artefatos atuais e suas fontes foram conferidos; nenhuma janela real foi decodificada. 0 recuperadas, 5 mantidas em revisão, sem correção/publicação e sem mudança de QA. Nenhum caso de timestamp já recuperado foi reaberto. Inglês/Espanhol excluídos. Fila: 55 registros em review, 50 atuais e elegíveis após excluir os dois idiomas.
- **Capacidade:** 164.374.413.312 B livres no smoke, contra reserva operacional de 5.097.523.696 B (4 GiB + maior fonte + 100 MiB), além de 1 GiB extra e orçamento temporário exigidos pelo reviewer.

| Aula/revisão | Bloqueio atual | Janelas planejadas (s, não executadas) |
|---|---|---|
| `fo_86307c2dd5ba3e22` v2 — Biologia | Repetição sem confirmação acústica, potencialmente legítima | 661,84–670,00 |
| `fo_2f7972942ef5c195` v1 — História | Repetição isolada sem confirmação acústica | 1488,26–1496,76 |
| `fo_409adc43759b2c92` v1 — Português | Loop de n-gramas/tokens | 1332,10–1340,22; 2056,80–2062,80; 2056,80–2082,80; 2076,80–2092,80 |
| `fo_1d3cbdf905d6c3f9` v1 — Filosofia | Texto durante silêncio medido | 1612,70–1617,55 |
| `fo_d6edf80d9016f394` v1 — Redação | Repetição de tokens e texto durante silêncio medido | 1741,64–1753,72; 2015,40–2021,40; 2178,20–2184,68 |

Próximo aceite: executar as cinco revisões manuais, uma de cada vez no handoff
validado; medir recursos por aula, adjudicar a evidência acústica e preservar as
transcrições originais. Só considerar correção versionada pelo QA existente ou
automação contínua após esse aceite. Runbook:
`federal-online/transcription/parakeet-runtime/README.md`.

### Retomada do cutover — 22/11/2026 UTC

- A interrupção da sessão de operação não encerrou o observador de cutover. Foi
  confirmado um único observador remoto, ainda dentro do limite de 150 min, e
  nenhum segundo observador foi iniciado. A instalação aguarda a primeira
  fronteira comprovada entre tarefas; um decoder ativo ou um lease impede a troca.
- Na retomada, o Whisper ainda rodava com o código legado, zero reinícios e
  progresso persistido de 55,3% em `fo_ffc2128800c4dd37` v1 (janela 3 de 4).
  Dois checkpoints v2 da fonte ativa foram lidos e conferidos por SHA-256. Nenhum
  lease, checkpoint, lock ou gate foi alterado na retomada.
- A API FO registrava 126 transcrições atuais validadas e 55 jobs em revisão.
  As cinco revisões piloto ainda estavam sem recibos acústicos, ocultas no
  Plugin (HTTP 404) e sem aprovação ou publicação. Anki e n8n responderam
  HTTP 200; a interface Study Hub retornou o desafio de autenticação esperado.

### Retomada após desligamento do Mac — 22/11/2026, 01:43 UTC

- Os observadores vinculados ao SSH já tinham saído. O job anterior,
  `fo_ffc2128800c4dd37` v1, terminou com quatro checkpoints; os dois hashes
  anotados antes da interrupção permaneceram idênticos. O Whisper legado
  continuava no PID 2011009, com zero reinícios, decodificando o primeiro de
  quatro blocos de `fo_ab7589742bc156fd` v3. Nenhuma fronteira segura tinha sido
  observada: nenhum processo Whisper, lease ou lock foi interrompido.
- O runtime ARM64 existente passou na verificação dos seis arquivos e de todos
  os pins, sem reinstalação ou inferência adicional. As revisões atuais, os
  hashes dos originais e as respectivas reavaliações QA v5 da coorte também
  passaram na pré-verificação somente leitura.
- O Oracle assumiu a espera em duas unidades systemd transitórias, sem timer
  ou reinício automático: `study-hub-fo-parakeet-cutover` (observador único,
  janela de 180 min) e `study-hub-fo-parakeet-cohort` (limite total de 14 h).
  A segunda aguarda prova do cutover e um lease real do novo líder. Admite
  somente os cinco IDs e versões acima, em ordem e uma vez cada, e encerra se
  faltar recibo acústico privado ou evidência de que o Whisper retomou. Cada
  inferência usa os limites já descritos no runbook e não publica.
- Na retomada: 0 de 5 aulas revisadas com áudio,
  0 recuperadas, 5 ainda em review e HTTP 404 no endpoint de transcrição.
  Espaço livre: 164.355.276.800 B; reserva Whisper: 5.097.523.696 B.
  Nenhum serviço de revisão contínua está habilitado. O aceite continua
  condicionado aos recibos reais e à adjudicação da evidência.
