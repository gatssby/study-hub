# FO — reconstrução integral e ativação progressiva do ASR (29/10/2026)

Observações reais na VPS `oracle-vps`, horário UTC. Contagens lidas de SQLite `-readonly`, `plan.json`, `verify.json`, `cleanup.json` e journal.

## Estado entregue

- Geração ativa: `g20261029a`. O SHA-256 do DB ativo, `431cf10f…b1d5`, é igual ao `db_sha256` de `verify.json` (pass, 0 divergências). Rollback disponível em `rebuild/g20261029a/previous-hub.sqlite3`; o comando `cutover --rollback` foi coberto por testes.
- Código: o FO e o orquestrador foram implantados por cópia de arquivos commitados, com cada SHA-256 conferido (`.deployed-commit`). Testes locais: `PYTHONPATH=federal-online:ops/study-hub … pytest federal-online/tests tests` com 480 passed.
- API FO reiniciada sobre o novo DB. Smoke read-only: `/fo/sync-status`, `/fo/materials` em seis disciplinas, `/fo/materials/{id}/pdf-text` (sem padrão de CPF) e `/fo/lessons`. Os PIDs do Anki vNext (sync, API e MCP) não mudaram.

## PDFs

- Inventário local: 510 arquivos (3,12 GB), 508 hashes de bytes distintos, 172 conteúdos distintos. A identidade de conteúdo ignora apenas a stream de marca d'água personalizada comprovada (nome/CPF).
- OneDrive `Federal Online PDFs`: as 176 cópias locais com bytes diferentes no caminho canônico remoto foram baixadas, uma por vez, para um diretório temporário. Todas tinham conteúdo igual (176/176) e foram registradas como `register_equivalent`, sem upload. Os 178 PDFs que só existem no remoto foram todos cobertos por um original local de mesmo conteúdo (0 sem cobertura). A primeira sonda foi morta por OOM a 2 GiB num PDF de 228 MB; foi retomada com 5 GiB e o arquivo temporário foi removido.
- Plano `g20261029a`:
  - 334 `register_original`;
  - 176 `register_equivalent`;
  - 0 uploads;
  - 0 `protect_unique`;
  - 2.252 `register_video`.
- Stage: 3.272 recibos, 0 bytes transferidos, 172 materiais reextraídos (Markdown + JSON por página em `rebuild/g20261029a/pdf/`) e 508 linhas em `material_originals`.
- Qualidade por página no novo índice:
  - 7.270 `text`;
  - 4 `low_text`;
  - 524 `ocr_needed` (bloqueadas);
  - 20 `blocked`.
  O índice anterior tinha 147.693 linhas de página porque contava cada cópia com marca d'água como um material; o novo tem 7.818 páginas para 172 conteúdos.
- Cleanup: 510 PDFs locais removidos. Cada remoção exigiu recibo válido, tamanho e QuickXor remotos atuais e sha256/size/quickxor locais recalculados no momento do unlink. Pendentes 0, protegidos 0. Foram removidos também 9 diretórios temporários antigos (playwright, `tmp/videos`). Resta 1 PDF em `materials/.build_extensivo-ufpr-2026/`, staging de um downloader excluído do plano por regra. `materials` passou de 3,1 GB para 16 MB; o disco de 13 GB para 17 GB livres.
- O estado operacional foi preservado: o DB da geração parte de um snapshot do ativo e o verify falha se alguma tabela operacional encolher. Contagens antes e depois são iguais: `focused_reviews` 175, `transcription_jobs` 3.325, `lesson_video_sources` 3.148, `lessons` 3.213.

## Vídeos

- 2.252 objetos registrados no OneDrive `Federal Online` com QuickXor, sem download.
- 20 aulas têm fonte `available=0` sem caminho remoto. Elas não são consumidas pelo worker (o lease exige `available=1`) e ficam como lacuna explícita. A recoleta do catálogo (34 aulas do Semiextensivo com timeout de clique) continua pendente.
- A dedupe remota de vídeos (126 duplicatas de bytes) não foi executada. É opcional e só ocorre com `--dedupe-videos`.

## Whisper: configuração e loops

As medições reais são janelas de 600 s em large-v3, sem referência humana. O resultado prova ausência de loop de decoder, não acurácia.

- Aula do piloto (Biologia, `fo_21fd4985e207c5df`): o piloto em review tinha uma linha repetida 97× e outra 122×. Com `no-context` (`-mc 0`), as duas janelas não têm duplicatas. A janela 24–29 min mantém um flag de token e um de n-grama, que correspondem à fala real do professor. `fallback-no-context` produziu saída idêntica. `fallback` com contexto gerou 27 `duplicate_segment` e ficou mais lento (RTF 3,1–3,7).
- Uma janela por disciplina (História, Química, Física, Matemática, Literatura), comparada com o baseline: os flags de repetição caem em todas; Química vai de 4 duplicatas para 0; Literatura mantém 2 `token_repetition`, que é repetição real.
- Recursos: RTF de 2,35 a 2,58 e RSS de cerca de 3,9 GB.
- Escolha: beam 5, sem fallback, `FO_ASR_MAX_CONTEXT=0`. O fingerprint inclui parâmetros, modelo e binário.

## Round-robin (homologado sobre a fila real, read-only)

- 3.103 jobs elegíveis, 2.252 vídeos distintos, 16 disciplinas normalizadas.
- Defeito encontrado e corrigido: a query de lease não trazia `item_id`, então a ordem caía em ordem alfabética de título. Agora usa a `ordem` do `aulas_index` atual, com a teoria antes dos exercícios do mesmo slot (2.267/3.103 jobs com `ordem`).
- Sequência simulada: Biologia T1 → Ciências Básicas → Espanhol T1 → … → Sociologia T1 → Biologia E1 → … Intervalo máximo entre duas vezes da mesma disciplina nos 500 primeiros: 16.

## Ativação progressiva

- Autorização em `/etc/study-hub/fo-transcription.authorized` (root:ubuntu 640). Gate `allowed=true`, preflight `ready=true`, `max_context=0`.
- Etapa 1: unit transitória `study-hub-fo-progressive-1` (CPUQuota 300%, MemoryMax 12G, TasksMax 128, UMask 0077, RuntimeMaxSec 36000) executando `--run --once`. O round-robin escolheu `fo_135c415d8080927f`, Biologia - Teoria, "Bioquímica", 2.148 s.
- O serviço persistente `study-hub-fo-transcription` ainda não foi iniciado. Critério para iniciar: a etapa 1, e depois um lote curto em disciplinas distintas, terminam com QA sem loop, temporários removidos e publicação conferida.

## Pendências e bloqueios

- OCR: 524 páginas `ocr_needed` ficam bloqueadas porque não há `tesseract` na VPS. As colunas incertas mantêm a ordem original. Tabelas ficam como texto simples.
- Os timers `catalog`, `index` e `materials` já estavam em `failed` antes da missão; a recoleta não foi refeita. O timer `videos` foi pausado durante stage/cutover e reativado.
- Não há gold humano: a qualidade PT-BR, os termos e os timestamps continuam sem medição.
