# ATIVAÇÃO DAS TRANSCRIÇÕES — AGUARDANDO AUTORIZAÇÃO DO USUÁRIO

Estado entregue: `TRANSCRIPTION_ENABLED=false`, unit `study-hub-fo-transcription.service` desabilitada/inativa, sem timer e sem arquivo de autorização. Nenhum comando abaixo foi executado para ativar ASR. A data 22/10/2026 NÃO autoriza o processamento.

## O que está preparado

Worker `fo_hub.worker`, whisper.cpp e large-v3-f16 na VPS. Modelo é candidato, não vencedor de benchmark. Fila e sources versionadas em SQLite próprio. CLI `--check-only` não abre áudio nem toma lease: lê SQLite/modelo e executa somente consultas de versão/help dos binários. `--run --once` e `--run --loop` exigem gates e preflight aprovados.

Cada fonte deve estar disponível no OneDrive e ter revisão igual ao job e à aula atual. Fontes ausentes/stale não são consumidas. Um lock exclusivo protege o processo; leases recuperam interrupção; retry tem backoff e três tentativas. Sem orçamento de disco, `paused_storage` preserva a fila e não consome tentativas. Exigem-se fonte máxima + 100 MiB temporários além da reserva de 4 GiB. Extração em WAV PCM s16le mono 16 kHz, chunks de 600 s com 2 s de overlap; três threads, FFmpeg com uma thread e serviço limitado a 300% CPU/12 GiB/128 tasks. Não se guardam vídeos persistentes.

Stitching reconcilia somente correspondências textuais inequívocas nas janelas temporalmente sobrepostas. Preserva continuação de frases, sinais científicos, texto bruto e envelopes de timestamps originais; não inventa alinhamento por palavra. Fronteiras conflitantes/curtas/repetitivas permanecem completas em review. Frase coincidente cuja marca temporal deriva para fora da janela recebe `boundary_timestamp_drift`, preservando ambas as versões sem duplicação silenciosa. Regressões internas de cada chunk continuam sendo verificadas antes do stitching. Lacunas totalmente cobertas por silêncio medido viram observação, não revisão; cobertura sem explicação acústica e texto em silêncio medido ficam bloqueados. Há QA de repetição de tokens/frases e timestamps inválidos/não finitos.

Evidências e checkpoints brutos são JSON gzip sem perda em `transcripts/evidence/<sha-video>/<fingerprint>/`; artefatos completos aprovados em `transcripts/private/<aula>/vN.json.gz`; suspeitos em `transcripts/review/<aula>/vN.json.gz`. Cada chunk guarda o JSON integral do decoder e o comando exato no checkpoint, com checksum, schema/limites e data verificados antes do reúso. Checkpoint inválido é preservado em irmão `.rejected-<uuid>` e a rejeição registrada; qualquer nova decodificação exige gate. Texto do decoder é guardado antes do parsing, inclusive JSON malformado. Artefatos privados preservam configuração efetiva, hash do vídeo/modelo/binário/bibliotecas, commit do runtime, offsets e decisões. Mesmo vídeo por SHA-256 e mesma configuração reutilizam chunks sem nova inferência, mantendo aula/revisão/proveniência independentes. O download ainda ocorre para provar identidade; tamanho/título/caminho não provam bytes iguais.

Somente o JSON público mínimo (`lesson_id`, `version`, `corpus`, `qa.passed=true`, `segments`) entra em `transcripts/generated_v2/<aula>/vN.json`. Publicação e cópia usam lock exclusivo/compartilhado comum. OneDrive usa allowlist `--files-from` confrontada com segmentos aprovados no banco e aula/source atuais; não envia raw, temporários, private, review ou revisão antiga. O MCP serve apenas aulas presentes, QA aprovada e revisão/fonte atuais. Spans de revisão focal ficam em `focused_reviews`, `pending_manual_review`; aprovação manual e retranscrição focal automática não fazem parte desta preparação.

## Pré-requisitos manuais depois de nova autorização explícita

1. Entrar na VPS com `ssh oracle-vps`. Nunca executar inferência no Mac.
2. Revisar `transcription/benchmark-selection-2026-10-27.json`, `benchmark-matrix.json` e `benchmark-evaluation.md`. Há seis aulas elegíveis de seis disciplinas e 18 janelas propostas, sem escuta. Faltam identificar pelo menos dois professores, confirmar ruído/música/silêncio, obter 90 minutos de gold, dois trechos sem fala de 3 min, probes curtos/fronteiras, glossário, timestamps e revisão por segundo anotador de 20%. O scorer WER/CER/termos/alucinação/timestamps/recursos/IC95 está implementado; nenhuma métrica de modelo foi medida. Executar benchmark somente se a nova autorização cobrir essa inferência.
3. Confirmar espaço livre, fontes, pesos e binários. O preflight abaixo é seguro e pode continuar sendo usado antes da autorização:

    cd /home/ubuntu/study-hub/federal-online
    TRANSCRIPTION_ENABLED=false STUDY_HUB_FO_DB=/home/ubuntu/study-hub-state/federal-online/hub.sqlite3 /home/ubuntu/study-hub-venv/bin/python -m fo_hub.worker --check-only

4. Escolher modelo por qualidade, não apenas velocidade; registrar decisão. Se o candidato mudar, atualizar `WHISPER_CPP_BIN` e `WHISPER_MODEL`, implementação de adapter se necessário, e reprovar ativação enquanto não houver suporte testado.

## Comandos de ativação — NÃO executar sem autorização

Somente após aprovação explícita e verificação dos pré-requisitos, editar `/home/ubuntu/.config/study-hub/transcription.env` para conter exatamente:

    TRANSCRIPTION_ENABLED=true
    FO_STATE_ROOT=/home/ubuntu/study-hub-state/federal-online
    STUDY_HUB_FO_DB=/home/ubuntu/study-hub-state/federal-online/hub.sqlite3
    WHISPER_CPP_BIN=/home/ubuntu/study-hub-models/whisper.cpp/build/bin/whisper-cli
    WHISPER_MODEL=/home/ubuntu/study-hub-models/ggml-large-v3.bin
    FO_ASR_MAX_CONTEXT=0

`FO_ASR_MAX_CONTEXT=0` (sem contexto entre janelas) eliminou os loops reais do piloto; ver `docs/research/2026-10-29-fo-full-rebuild-and-asr-activation.md`.

Criar via `sudoedit /etc/study-hub/fo-transcription.authorized` uma única linha:

    I AUTHORIZE FO TRANSCRIPTION ON VPS

Aplicar `sudo chown root:ubuntu /etc/study-hub/fo-transcription.authorized` e `sudo chmod 640 /etc/study-hub/fo-transcription.authorized`.
O marker `/etc/study-hub/fo-vps.marker` já existe; marker sozinho não autoriza.

Validar com as variáveis do arquivo carregadas explicitamente no shell da VPS:

    set -a
    . /home/ubuntu/.config/study-hub/transcription.env
    set +a
    cd /home/ubuntu/study-hub/federal-online
    /home/ubuntu/study-hub-venv/bin/python -m fo_hub.worker --check-only

Exigir `gate.allowed=true`, `preflight.ready=true` e fontes corretas. Para uma única aula científica selecionada por metadados (reconfirmar versão/elegibilidade antes), executar somente então na VPS, com limites também no piloto:

    sudo systemd-run --unit=study-hub-fo-pilot --collect --wait --pipe --uid=ubuntu --working-directory=/home/ubuntu/study-hub/federal-online -p CPUQuota=300% -p MemoryMax=12G -p TasksMax=128 -p UMask=0077 --setenv=TRANSCRIPTION_ENABLED=true --setenv=FO_STATE_ROOT=/home/ubuntu/study-hub-state/federal-online --setenv=STUDY_HUB_FO_DB=/home/ubuntu/study-hub-state/federal-online/hub.sqlite3 --setenv=WHISPER_CPP_BIN=/home/ubuntu/study-hub-models/whisper.cpp/build/bin/whisper-cli --setenv=WHISPER_MODEL=/home/ubuntu/study-hub-models/ggml-large-v3.bin /usr/bin/time -v /home/ubuntu/study-hub-venv/bin/python -m fo_hub.worker --run --once --lesson-id fo_21fd4985e207c5df

Esse comando não cria timer, não habilita boot e limita a seleção à aula `Desenvolvimento embrionário`, Biologia I, versão 1 na observação de 27/10/2026. Sem os gates, recusa executar. A configuração persistente pode permanecer `false` durante um piloto autorizado, pois `--setenv` só vale para a unit transitória. QA automatizada não equivale a aceitação humana da precisão. A unit transitória pode desaparecer após terminar; logs permanecem no journal.

Se a autorização incluir a fila integral e a amostra estiver aceita, iniciar o serviço persistente:

    sudo systemctl start study-hub-fo-transcription.service
    systemctl status study-hub-fo-transcription.service
    journalctl -u study-hub-fo-transcription.service -n 50 --no-pager

Não é necessário habilitar no boot para manter um serviço iniciado ativo. `systemctl enable` só deve ser usado se a autorização incluir reinício após reboot. Não há timer nem início automático amanhã.

## Parada e revogação

`sudo systemctl stop study-hub-fo-transcription.service`, voltar a variável para `false`, revogar a autorização e manter `systemctl disable`. Não apagar fontes/vídeos/PDFs. Em retomada autorizada, leases interrompidos voltam à fila respeitando limite de tentativas e checkpoints concluídos não repetem inferência. A retomada após reboot precisa de novo start manual enquanto a unit estiver disabled; não foi habilitado boot. Interrupção por falta de disco antes do lease não gasta tentativa. Artefatos de review são resultados novos, não backups do corpus antigo.

## Verificação realizada sem ASR

Os testes injetam os subprocessos ASR: gates, integridade SHA, offsets em ms, retomada, retry, backpressure de disco, cache por bytes, stitching e sinais negativos, fontes versionadas, isolamento de review, publicação, HTTP/MCP e OneDrive allowlist. Gzip é verificado por round-trip sem perda. Testes de recuperação removem apenas temporários sintéticos marcados; nenhuma limpeza de arquivos existentes foi executada na VPS. Download tem limites explícitos de tamanho/transferência. Ver relatório datado em `docs/research/2026-10-27-fo-transcription-preparation.md` para os números finais.

## Configuração e monitoramento após autorização integral

Baseline: large-v3 FP16, `pt`, beam 5/best-of 5, temperatura 0, fallback off/incremento efetivo 0, no-speech 0,6, entropy 2,4, logprob -1, contexto padrão `-mc -1`, CPU `-ng`, saída `-ojf`. Não usar prompt especulativo nem pós-processamento por IA. Fallback 0→1 em incrementos 0,2 e beam 10 são comparações, não melhorias já comprovadas. VAD permanece desligado por decisão de qualidade, não ausência de pesos: `models/for-tests-silero-v6.2.0-ggml.bin` tem 885.098 bytes e SHA-256 `2aa269b785eeb53a82983a20501ddf7c1d9c48e33ab63a41391ac6c9f7fb6987`, idêntico ao Silero v6.2.0 oficial `ggml-org/whisper-vad`. A biblioteca instalada carregou esses pesos e classificou dois segundos de zeros PCM em memória, em CPU, sem carregar Whisper ASR e sem abrir áudio real. Isso prova compatibilidade e execução sintética, não retenção de fala baixa, música/ruído nem alinhamento dos timestamps ASR com VAD. Não adicionar `--vad` ao pipeline antes da comparação real autorizada e da validação desse mapeamento.

1. Aceitar piloto e benchmark por qualidade PT-BR/termos/alucinação/timestamps, não por velocidade. Registrar configuração vencedora e consumo observado. Não há vencedor antes disso.
2. Atualizar somente o ambiente FO para `true`, manter autorização explícita e repetir preflight. Iniciar manualmente o serviço apenas quando a autorização também abranger a fila integral. Boot exige decisão separada; não criar timer.
3. Monitorar `journalctl -u study-hub-fo-transcription.service -f`, `systemctl show study-hub-fo-transcription.service -p ActiveState -p MemoryCurrent -p MemoryPeak -p CPUUsageNSec`, `df -h /home/ubuntu` e `/fo/sync-status`/`fo_get_sync_status`.
4. Status preserva `transcription_jobs` legado e expõe `transcription_states`: `leased→processing`, `done→validated`, `stale→superseded`. `transcription_progress` informa total, progresso e leases vencidos. `paused_storage` é backpressure do worker; jobs ficam queued. Comandos têm timeout (ASR por chunk até 48 h), leases de sete dias são renovados por chunk; serviço recupera owner antigo sob lock após restart. Uma execução sintética não mede o tempo real em ARM.
5. Observar crescimento dos artefatos gzip e do JSON público; não existe estimativa medida de bytes/hora ASR antes do piloto. Ao atingir reserva, pausar sem exclusões e ampliar armazenamento conforme necessidade, em vez de apagar evidências. Mudanças observadas de ID/tamanho/ModTime remoto invalidam a revisão; sem metadata nova não é possível detectar uma troca invisível de mesmo tamanho após validação. Hash do download protege reúso de inferência, não substitui inventário remoto atualizado.
