# Study Hub Sprint 2 — relatório de publicação e operação (07/11/2026)

Branch `feat/study-hub-migration`. Base `b18823f`; commits da sprint: `ef18a82`, `00f9c9f`, `26b91e3`, `3b0d89e` e o commit deste relatório.

## Publicação

- `https://study.gatssby.com.br` publicado em 07/11 às ~20:24 UTC.
- DNS: A 137.131.191.66, confirmado no autoritativo (`b.sec.dns.br`) e em 1.1.1.1/8.8.8.8. Sem AAAA. É o mesmo IP da VNIC Oracle. Não houve alteração de raiz nem de `www`.
- TLS: certificado Let's Encrypt próprio, lineage `study.gatssby.com.br`, emissor YE1, válido até 05/02/2027. Renovação por webroot em `/var/www/study-hub-acme`. Os certificados do n8n e do Anki não foram tocados.
- Nginx: novo arquivo exclusivo `sites-available/study.gatssby.com.br`, sem `default_server`.
  - Porta 80 serve apenas ACME e responde 308 para HTTPS.
  - Porta 443 usa Basic Auth, CSP restritiva, `X-Frame-Options DENY` e `no-store`.
  - Rota de API única: `GET /api/dashboard`. Outras `/api/*` retornam 404 e dotfiles retornam 404.
  - Validado com `nginx -t` e reload gracioso; o PID mestre do nginx não mudou.
- Autenticação: `/etc/nginx/study-hub-web.htpasswd` (SHA-512 crypt, `root:www-data 0640`). Credencial gerada na VPS e guardada só em `/root/study-hub-web-credentials` (0600). Nunca passa por argv, log ou repositório.
  - Ler: `ssh oracle-vps sudo cat /root/study-hub-web-credentials`
  - Rotacionar: `sudo bash /home/ubuntu/study-hub/ops/study-hub/web/reset-credentials.sh`
- Backend: `study-hub-observer.service`, Gunicorn com 1 worker, apenas em `127.0.0.1:3401`.
  - Habilitado no boot. Limites: `MemoryMax=192M`, `CPUQuota=20%`, `ProtectSystem=strict`, home read-only, sem `.ssh/.config`.
  - Coletor em subprocesso com timeout de 12 s e cache de 20 s. SQLite aberto `mode=ro` com deadline. Projeção por allowlist; payload ≤16 KiB.
  - Não usa SSH; a API FO 8780 continua privada.
- Frontend: build Vite estático em releases imutáveis `/srv/study-hub-web/releases/*`, servidas pelo symlink `current`. Rollback = repontar o symlink.

Smoke real:

| Teste | Resultado |
|---|---|
| Sem credencial (`/` e API) | 401 |
| Senha errada | 401 |
| Com credencial (`/` e API) | 200 |
| `POST` | 405 |
| Query string | 400 |
| `/api/other`, `/.git` | 404 |
| HTTP | 308 |

## n8n e demais hosts (antes = depois)

- Container `e479101ea8aa…`, start `2026-11-01T04:01:04Z`, PID 740519, 0 restarts, `running`. Root e `/healthz` retornam 200.
- Certificado do n8n servido após o deploy: SHA256 `A9:67:81:…:7C:70`, validade 26/01/2027; arquivo de vhost e lineage não tocados.
- Hashes de `sites-enabled/{anki,default,n8n,sales,verbo}` e de `nginx.conf` idênticos ao baseline.
- Respostas na raiz: Anki 404, Sales 307, Verbo 200 (iguais ao baseline).
- PIDs: FO API 3138706 inalterado.

## Armazenamento (política: VPS guarda texto, índices e estado; originais no OneDrive)

Espaço recuperado:
- 3 SQLite históricos redundantes: 1.918.894.080 B. Comprovação: 0 fds abertos, 0 referências, toda chave existente no live, sem WAL.
- 1 PDF residual de staging: 15.451.322 B. SHA256 do download remoto igual ao local; 0 referências no banco; locks de materials/publication/index segurados. Recibo novo em `missions/20261107-sprint2/residual-pdf-receipt.json`; o recibo antigo não foi alterado.

Itens mantidos e motivo:
- `rebuild/g20261029a/previous-hub.sqlite3`: 3.245 materiais e 147.693 páginas ausentes do live.
- `rebuild/pre-bioq-rerun-20261030.sqlite3`: 178 chaves de focused reviews ausentes do live.
- Ambos ficam até classificação de relevância. Não houve nova cópia histórica.

Mídia e temporários:
- Nenhum PDF original resta em `materials/`.
- Mídia fora de `tmp`: apenas 207 MiB de janelas de validação ASR de 28–29/10 (evidência de homologação). Candidatas a arquivamento no OneDrive numa próxima sprint.
- Temporário do worker: 111 MiB, só do job ativo; removido pelo próprio worker após sucesso.

OneDrive:
- Último ciclo `success` às 20:29 UTC. `pdf_sync` e `transcript_sync` verificados por `rclone check --download`.
- 13 transcrições locais = 13 objetos em `generated_v2`.
- 2.997 vídeos com recibo verificado (439,4 GB), 5 com erro, 3 indisponíveis.

Alertas:
- `study-hub-storage.timer` (horário) grava `telemetry/storage.json`.
- Primeira amostra: livre 12,8 GiB; Study Hub 2,3 GiB; temporários 134 MiB; reserva do Whisper 4,7 GiB (4 GiB + 100 MiB + maior fonte).
- Alerta só para `low_reserve` ou crescimento que esgote a reserva em ≤7 dias. Nunca apaga arquivos.

## Transcrições

Estado da fila no momento do relatório: done 13, review 4, queued 2.997 (dos quais 177 ignorados), leased 1, superseded 519.

Exclusão de Inglês e Espanhol:
- Preferência persistente gravada em `transcription_discipline_exclusions`, somente com os nomes canônicos exatos. Qualquer outro nome retorna exit 2.
- O mapeador já normaliza "— Teoria e Exercícios" para o nome canônico.
- Jobs continuam `queued`, com metadados e transcrições preservados.
- Reativar: `python -m fo_hub.worker --include-discipline 'Inglês'` (análogo para Espanhol).
- O worker em execução só lê a preferência depois de reiniciar. Um watcher (`study-hub-sprint2-exclusion-apply`) espera o fim do job Espanhol em andamento e reinicia uma única vez. Recibo: `missions/20261107-sprint2/exclusion-apply-receipt.json`.

Telemetria de fase:
- Tabela `transcription_job_phases`: downloading, hashing, probing, decoding (chunk i/n), stitching, repetition_check, qa, publishing, finished.
- Começa a ser preenchida a partir do primeiro lease do worker novo.

Reviews (4) — motivos documentados em `2026-11-07-study-hub-sprint2-transcription.md`:

| Disciplina | Blockers | Warnings | Gravidade |
|---|---|---|---|
| Biologia | duplicate_segment ×8, ngram_repetition ×2 | non_monotonic ×1, ambiguous_overlap ×1 | grave |
| Redação | ngram_repetition ×6 | non_monotonic ×2, ambiguous_overlap ×1 | grave |
| Química | bad_timestamp ×2 | non_monotonic | grave |
| Espanhol (QA v3) | mixed_language_configuration_unverified | — | — |

- A reavaliação só com evidência não mudaria nenhum resultado. Nenhuma foi publicada.
- Verificação acústica focal fica para quando o worker puder ceder o lock.
- A UI mostra disciplina, gravidade, motivos e intervalos sem nenhum texto. Ações administrativas não foram expostas.

Ritmo e ETA:
- Mediana de 2,60 min de processamento por minuto de áudio (n=15 comparáveis; exclui pilotos <5 min e execuções com reuso de cache). Faixa interquartil de 2,56 a 2,85.
- Fila ativa sem Inglês/Espanhol: ~1.459 h de áudio (antes da exclusão: ~1.540 h). Mais 4 jobs sem duração no catálogo, reportados à parte.
- ETA de ~158 dias (156–173). Com menos de 5 amostras, nenhum prazo é exibido.
- Últimas 24 h: 8 aulas, 3,6 h de áudio.

Ativação verificada às 20:55 UTC:
- A aula Espanhol em andamento terminou normalmente e foi para `review` (QA v4: idioma misto não verificado).
- O worker reiniciou uma única vez (PID 3143673 → 3768054, 0 restarts por falha). Nenhum job estava leased no momento, então nenhuma tentativa foi consumida.
- O worker novo pegou Filosofia, com telemetria de fase em `decoding 1/3`. A próxima disciplina é Física.
- Contagens: done 13, review 5, queued 2.996 (Inglês 90 e Espanhol 87 ignorados), leased 1.
- n8n inalterado: mesmo start, mesmo PID e 0 restarts.

## PDFs

- 174 materiais e 8.457 páginas: 7.912 liberadas, 545 bloqueadas (523 OCR review, 20 blocked, 1 vazia, 1 pendente sem original).
- Triagem sem conteúdo (`triage_ocr_review`) das 523: 192 com fórmulas, 188 de texto, 134 ruidosas/visuais, 9 de privacidade.
- Nenhuma página foi liberada por regra nesta sessão. A liberação exige comparação visual, na ordem: texto, depois fórmulas, depois privacidade.
- Os 20 `blocked` não guardam texto; recuperá-los exige re-extração a partir do OneDrive (design pendente).

## Testes

| Escopo | Resultado |
|---|---|
| FO | 640 passed |
| Telemetria storage/pipeline | 10 passed |
| Observer/produção (unittest) | 10 OK |
| Frontend (vitest) | 12 passed; tsc limpo; build ok |
| Visual | smoke em 1280 px e 390 px sem overflow, dados reais |

## Pendências

1. Classificar os dois snapshots históricos mantidos e arquivar as janelas de validação de mídia.
2. Revisão visual priorizada das páginas OCR; design de re-extração para os 20 `blocked`.
3. Instrumentar bytes e velocidade em tempo real de downloads. Hoje só existem recibos de estado final.
4. Verificação acústica focal dos 3 reviews v4.
5. Notion: conector desconectado, roadmap não sincronizado (o roadmap no GitHub está atualizado).
