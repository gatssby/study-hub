# Sprint 2 — Transcrição: exclusão persistente Inglês/Espanhol, telemetria de fase e auditoria de reviews

Data: 07/11/2026. Branch `feat/study-hub-migration`, sem commit (commit seletivo pelo parent). Nenhuma inferência executada; nenhum serviço reiniciado.

## Implementado (local, TDD)

- `fo_hub/scheduler.py`: `EXCLUDABLE_DISCIPLINES = {'Inglês','Espanhol'}` (nomes canônicos exatos); `choose(..., excluded=())` ignora grupos excluídos.
- `fo_hub/worker.py`:
  - Tabela `transcription_discipline_exclusions(discipline, reason, created_at)` criada por `CREATE TABLE IF NOT EXISTS`. `lease()` lê a tabela dentro da transação `BEGIN IMMEDIATE`. Jobs **não são reescritos**: continuam `queued` com tentativas, metadados e versão preservados; nada é marcado como concluído. Job já `leased` não é interrompido.
  - CLI `--exclude-discipline NOME` / `--include-discipline NOME`; nome fora da allowlist exata → exit 2.
  - Telemetria `transcription_job_phases` (uma linha por job/versão): `downloading, hashing, probing, decoding (chunk_index/chunk_total), stitching, repetition_check, qa, publishing, finished`. Best-effort: erro SQLite nunca derruba o job.
  - `--status` agora inclui `excluded_disciplines` (contagem por estado; `null` se a tabela não existe) e `phase` (somente jobs `leased`; lista vazia sem dados — nunca progresso inventado).
  - `--review-audit`: projeção somente leitura por allowlist (kinds de flags/blockers/warnings, métricas escalares, SHA256 do artefato, contagem de chunks/reuso, recibos de reavaliação). Nunca emite texto, segmentos, raw, stdout/stderr. Artefato ausente → campos `null`, não zero.
- Testes: `federal-online/tests/test_sprint2_scheduler.py` (13). Suíte FO completa: **640 passed**.

## Estado remoto (read-only, 07/11/2026)

- `study-hub-fo-transcription`: active/running, MainPID 3143673 (início 05:43:41 UTC), inalterado antes/depois.
- `worker.py` em produção = HEAD `a5b420d7…` (sem o código novo).
- Jobs: done 13, leased 1 (Espanhol), queued 2.997, review 4, superseded 519.
- Fila por disciplina-alvo: Inglês queued 90; Espanhol queued 87 + leased 1 + review 1. Cursor RR: `last_discipline=Espanhol`.

### Auditoria de reviews (código novo executado de diretório temporário, sem escrita)

| lesson | disciplina | QA policy | blockers | warnings | chunks |
|---|---|---|---|---|---|
| fo_4cc5e44ffb6dc603 | Espanhol | v3 | null (v3 sem classificação) | null | 3 |
| fo_5fff36e9eeebf3f2 | Biologia | v4 | duplicate_segment 8, ngram_repetition 2 | non_monotonic 1, ambiguous_overlap 1 | 4 |
| fo_762f065208c3eba8 | Redação | v4 | ngram_repetition 6 | non_monotonic 2, ambiguous_overlap 1 | 5 |
| fo_a32f71f7cfab8eb4 | Química | v4 | bad_timestamp 2 | non_monotonic 1 | 4 |

Recibos de reavaliação: 0 em todas. Mutations: 0.

**Reavaliação evidence-only: não recomendada.** As três reviews v4 têm blockers substantivos sob a política atual (repetição sistemática, timestamps inválidos); reavaliar não mudaria o resultado. A review de Espanhol (v3) receberia de novo `mixed_language_configuration_unverified` (blocking) e a disciplina será excluída. Não existe CLI de reavaliação; `Worker.reassess_review` exige o gate e só deve ser chamado pelo parent, segurando `transcription.lock` (indisponível enquanto o worker roda). Nenhum comando de reavaliação proposto.

## Por que a preferência ainda não está efetiva

O worker em execução usa o código antigo e não lê a tabela de exclusão. Gravar a tabela agora não teria efeito, e a alternativa (mexer em `retry_at`/estado dos jobs) alteraria jobs — fora do escopo autorizado. Fica para o parent.

## Requisitos de deploy (parent)

1. Commit seletivo: `federal-online/fo_hub/scheduler.py`, `federal-online/fo_hub/worker.py`, `federal-online/tests/test_sprint2_scheduler.py`, este relatório.
2. Implantar só esses caminhos; conferir SHA de todos os módulos FO.
3. Gravar a preferência (escrita somente na tabela nova, sem lease):
   ```
   cd /home/ubuntu/study-hub/federal-online && FO_STATE_ROOT=/home/ubuntu/study-hub-state/federal-online STUDY_HUB_FO_DB=/home/ubuntu/study-hub-state/federal-online/hub.sqlite3 /home/ubuntu/study-hub-venv/bin/python -m fo_hub.worker --exclude-discipline 'Inglês'
   # repetir com 'Espanhol'
   ```
4. Passa a valer quando o processo do worker carregar o código novo. **Não reiniciar enquanto houver job leased em decodificação**: o job atual é de Espanhol e o restart descartaria trabalho do chunk em andamento (o chunk persistido é reaproveitado). Fazer o restart controlado só com autorização e depois que o job atual terminar; esse job em curso não é interrompido pela exclusão.
5. Readback: `--status` → `excluded_disciplines` com Inglês/Espanhol e `next_discipline` diferente desses dois; `phase` preenchido a partir do próximo lease; `--review-audit` sem texto.

## Métricas para o contrato (coordenar com o parent)

- `excluded_disciplines`: `{nome: {estado: n}}` ou `null` (tabela ausente / código antigo).
- `phase[]`: `lesson_id, version, discipline, phase, phase_started_at, chunk_index, chunk_total, updated_at`; vazio = sem telemetria (UI deve mostrar "fase indisponível", nunca 0%).
- O denominador de progresso deve excluir as disciplinas excluídas e informar isso explicitamente; jobs excluídos continuam `queued` e não contam como concluídos.
- Progresso de chunk não é medido dentro de um chunk (decode é opaco); `chunk_index/chunk_total` é a granularidade real.
