# Federal Online — operação ASR do MVP / QA v4

A decisão AFK de 07/11/2026 autoriza deploy, serviço persistente e boot após homologação prática. Cursos incompletos, recursos inacessíveis, WER/CER/gold humano e pequenas imperfeições não são gates globais. Integridade, privacidade e bloqueio de transcrições gravemente comprometidas continuam obrigatórios. Isto substitui os gates operacionais históricos, preservados nos relatórios anteriores.

Produção verificada em 07/11/2026: serviço persistente active/enabled, gate ASR/API true, História concluída/publicada pela unit, restart controlado e próxima disciplina em processamento. Quatro reviews históricas publicadas com warnings, Espanhol privado; seis transcrições aprovadas no total. O relatório `docs/research/2026-11-07-fo-mvp-activation.md` e seu readback registram a evidência. Comandos abaixo não substituem readback.

## Contrato de produção

- VPS somente; um processo/decoder por vez sob `locks/transcription.lock`.
- Large-v3 FP16, três threads, beam/best-of 5, contexto 0, temperatura 0, fallback/VAD off. Não trocar modelo sem evidência; não alegar vencedor de benchmark.
- Unit `study-hub-fo-transcription.service`: CPUQuota=300%, MemoryMax=12G, TasksMax=128, Restart=on-failure, KillMode=control-group. Saídas 3/4/5 (gate/lock/breaker) não geram restart infinito.
- Reserva 4 GiB + maior fonte + 100 MiB. Backpressure antes de lease não consome tentativas. Nenhum vídeo permanente na VPS.
- Fila versionada SQLite, Round Robin por disciplina/ordem pedagógica, três tentativas, retry limitado, heartbeat e chunks persistentes.
- Três falhas técnicas ou cinco reviews graves consecutivas abrem breaker. Não resetar automaticamente para fabricar saúde.
- Ausente/stale não é selecionado. 404/duração incompatível têm motivo/backoff de 24 h sem consumir tentativas ASR. Mudança efetiva de revisão/path/size permite nova seleção. Auth/erros desconhecidos continuam erros reais.

## QA proporcional v4

Flags permanecem em `qa.flags`, com severity/policy_reason, e em `qa.warnings`/`qa.blockers`. Nunca apagar falas ou inventar timestamps para aprovar.

Warnings: sobreposição/fronteira local <=2,5 s cada, com orçamento agregado de 1% da duração (piso 5 s), sem defeito sistemático; até três pares de repetições curtas isoladas e não sobrepostas. São tolerâncias operacionais, não medidas de acurácia.

Blockers: timestamps inválidos/não finitos, sobreposição substancial/sistemática, loops, lacunas sem silêncio medido, texto em silêncio medido, vazio/incompletude, checks desconhecidos e evidência acústica negativa significativa. Review não publica e não impede a próxima aula; somente falhas consecutivas acionam breaker.

Espanhol: dois decodes focais adicionais não resolveram a mistura PT/ES. Não forçar ES para a aula inteira nem atribuir idioma por disciplina. A disciplina sinaliza risco da configuração PT atual; esses resultados vão a review até validar code-switch. Não bloqueia outras disciplinas.

## Evidência e publicação

`transcripts/evidence/<video-sha>/<runtime-fingerprint>/` guarda raw e checkpoints gzip com schema/checksum/identidade verificados. Inválidos são preservados em rejected. Mesmo título/path/tamanho não prova mesmos bytes.

`transcripts/review/<id>/vN.json.gz` permanece intacto. Reavaliação v4 cria `.qa-v4.json.gz` separado, vinculado ao SHA original, sem inferência; confere fonte, cobertura dos chunks, raw e stitching. `transcripts/private` nunca é público.

Somente a whitelist mínima (`lesson_id/version/corpus/qa.passed/segments`) em `generated_v2` é enviada ao OneDrive, comparada à DB sob lock de publicação comum. API/MCP exigem QA/revisão/fonte atuais. Warnings completos persistem na DB e no privado. Temporários MP4/WAV pertencentes à invocação são removidos; originais OneDrive e evidências nunca são apagados.

## Preflight e ativação autorizada

Na VPS, diretório `/home/ubuntu/study-hub/federal-online`:

    set -a
    . /home/ubuntu/.config/study-hub/transcription.env
    set +a
    /home/ubuntu/study-hub-venv/bin/python -m fo_hub.worker --check-only

Exigir gate.allowed/preflight.ready, hashes e orçamento corretos. `--check-only` não abre áudio nem toma lease. Marker VPS e arquivo de autorização explícita continuam obrigatórios. A data sozinha não autoriza.

Após homologação real, `transcription.env` contém `TRANSCRIPTION_ENABLED=true`, caminhos FO/modelo/binário atuais e `FO_ASR_MAX_CONTEXT=0`. A API usa o drop-in `30-transcription-enabled.conf` que acrescenta `/home/ubuntu/.config/study-hub/transcription-gate.env` como último EnvironmentFile, contendo somente esse gate. Um Environment=true simples NÃO supera o false de runtime.env. Coleta/index/OCR mantêm false; não iniciam ASR. Verificar a chave maiúscula `TRANSCRIPTION_ENABLED` em `/fo/sync-status`.

    sudo systemctl enable --now study-hub-fo-transcription.service
    systemctl is-active study-hub-fo-transcription.service
    systemctl is-enabled study-hub-fo-transcription.service
    journalctl -u study-hub-fo-transcription.service -n 30 --no-pager
    /home/ubuntu/study-hub-venv/bin/python -m fo_hub.worker --status

Não há timer ASR; systemd independe da sessão Hermes. Não iniciar piloto concorrente. Não reinstalar todas as units pelo renderer: isso pode restaurar o produtor legado de materiais ou overrides históricos.

## Monitoramento e restart

    systemctl show study-hub-fo-transcription.service -p MainPID -p ActiveState -p SubState -p MemoryCurrent -p CPUUsageNSec -p NRestarts
    df -h /home/ubuntu
    /home/ubuntu/study-hub-venv/bin/python -m fo_hub.worker --status
    sudo systemctl restart study-hub-fo-transcription.service

Progresso é o último chunk durável; durante decode observar heartbeat/CPU/decoder único. MainPID=0/auto-restart/OOM não significa atividade saudável. Após restart, verificar novo PID, lease recuperado, reúso de chunks, cursor/fila e conclusão real; PID sozinho não prova recuperação. Interrupção pode consumir uma tentativa; não reiniciar repetidamente uma mesma aula.

Cutover comprovado: o chunk 0–600 s de História persistiu antes de encerrar o piloto. A unit permanente recuperou o job, verificou os bytes da fonte, reutilizou esse chunk e decodificou a cauda; resultado aprovado às 05:42:37 UTC. Um override temporário retomava só esse job e depois executava o loop; foi removido por SHA antes do restart das 05:43:41. ExecStart final é somente `python -m fo_hub.worker --run --loop`. Após restart, Inglês ficou queued com tentativa preservada e Literatura foi selecionada; Round Robin não promete retomar imediatamente a disciplina interrompida. Nunca reinstalar o override transitório como configuração permanente.

## Recuperação e revogação

- paused_storage: preservar fila/evidências e ampliar espaço ou limpar somente resíduos classificados. Não apagar corpus/Anki.
- Fonte indisponível: consultar deferrals e motivos agregados em `/fo/sync-status`; fonte válida nova volta automaticamente.
- breaker_open: inspecionar erro privado/configuração; corrigir causa antes de `python -m fo_hub.worker --reset-breaker` e `systemctl reset-failed/start`. Nunca criar timer de reset.
- Auth sistêmica: corrigir acesso pelo procedimento existente, não converter em warning de curso.
- Review isolado: manter raw/QA para futuro, continuar outras aulas.

Revogação: `sudo systemctl disable --now study-hub-fo-transcription.service`, gate false em transcription.env E transcription-gate.env, restart somente da API para refletir a mudança e revogar autorização se solicitado. Não apagar fila, checkpoints ou originais. Preservar Anki/n8n/serviços terceiros.

## Aprimoramentos fora do gate MVP

Gold/WER/CER, code-switch validado, refinamentos de alinhamento e revisão acadêmica/OCR são backlog. PDF policy v5 e privacidade continuam obrigatórias; não expor original como substituto de derivado seguro. Materiais legado permanece proibido; um timer novo exige ciclo real seguro e não pode alegar cobertura global se só atualiza uma linha fixa.
