# Study Hub — roadmap UI e observabilidade
Atualização: 07/11/2026. Documento ativo; substitui apenas o planejamento de interface, sem apagar histórico técnico da reconstrução FO.

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
- [ ] Incorporar as métricas ao dashboard web, sem acesso SSH direto do navegador.

Comando: cd "$HOME/Workspace/Study Hub" && python3 ops/study-hub/fo_monitor.py --interval 20.

## M1 — Dashboard web operacional (P0; próxima implementação)

- [ ] Aplicação isolada, inicialmente read-only e acessível somente via localhost/túnel SSH; autenticação/TLS/permissões antes de exposição pública.
- [ ] Layout: sidebar Visão geral, Biblioteca, Transcrições, PDFs, Sincronização, Configurações; topo com hora do último snapshot e saúde dos serviços.
- [ ] Cards: aula em processamento (nome, disciplina, versão, percentual e chunks), fila (done, queued, leased, review, deferred), PDFs (aprovados/bloqueados), fontes e disponibilidade, status de timers e disco.
- [ ] Poll a cada 15–30 segundos, renderizar estados offline/stale com horário; carga de consulta baixa e read-only; evitar locks de escrita.
- [ ] Instrumentar eventos de download/sync reais com estado, bytes concluídos/totais quando disponíveis, horário e destino (vídeo, PDF, OneDrive). Etapas: discovered, queued, downloading, uploaded, verified, deferred, failed. Apenas com telemetria suficiente, mostrar barra de download e velocidade; não usar 2.252/3.001 como progresso.
- [ ] Série temporal (24 h/7 dias), taxa real de transcrições e downloads e histórico de falhas. ETA só quando mensurável; nunca inventar prazo para 3 mil aulas.
- [ ] API agregada autenticada de monitoramento, separada das sete rotas FO/MCP; não expor URLs assinadas, nomes pessoais, PDFs brutos, dados privados de review ou segredos.
- [ ] Smoke no cliente real: normal, sem conexão, partial/incomplete, job que muda de estado, review fail-closed, privacidade.

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
3. ASR: três reviews, casos de mistura PT/ES e termos científicos. Não atrasar MVP por perfeccionismo; manter QA grave bloqueante e warnings visíveis.
4. Disponibilidade: itens inacessíveis continuam em cooldown com motivo; conferir a diferença entre 14 pending e 13 deferrals anteriores.
5. Capacidade: ~11 GiB livres, verificar retenção de temporários e crescimento em produção; estimativa de duração só baseada em throughput.
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
