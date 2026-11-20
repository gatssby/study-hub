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

## M2 — Biblioteca e aula (P1)

- [ ] Navegar curso → disciplina → frente → módulo → aula por ordem do portal; filtros e pesquisa.
- [ ] Mostrar claramente disponível, não lançado, vídeo inacessível, fila, transcrevendo, validado e revisão, com motivo/cooldown/última verificação.
- [ ] Página de aula com informações, transcrição validada e citável, timestamps, avisos QA v4 e relações com materiais oficiais. Reviews privados não ficam legíveis.
- [ ] Incorporar reprodução/autorização de vídeo somente depois de definir contrato seguro para originais e URLs temporárias.

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
- M2 (Biblioteca/Aula), M3 (PDFs/Busca) e M4 (Anki) não iniciados; o dashboard atual é a Visão geral operacional read-only.
