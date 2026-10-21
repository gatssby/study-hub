# ATIVAÇÃO DAS TRANSCRIÇÕES — AGUARDANDO AUTORIZAÇÃO DO USUÁRIO

Estado entregue: `TRANSCRIPTION_ENABLED=false`, unit `study-hub-fo-transcription.service` desabilitada/inativa, sem timer e sem arquivo de autorização. Nenhum comando abaixo foi executado para ativar ASR. A data 22/10/2026 NÃO autoriza o processamento.

## O que está preparado

Worker `fo_hub.worker`, whisper.cpp e large-v3-f16 na VPS. Modelo é candidato, não vencedor de benchmark. Fila e sources versionadas em SQLite próprio. CLI `--check-only` não abre áudio, não toma lease nem inicia subprocesso. `--run --once` e `--run --loop` somente com todos os gates aprovados.

Cada fonte deve estar disponível no OneDrive e ter revisão igual ao job e à aula atual. Fontes ausentes/stale não são consumidas. Um lock exclusivo protege o processo; leases recuperam interrupção; retry tem backoff. Vídeo temporário só entra se tamanho previsto + reserva de 4 GiB couberem. Extração em WAV mono 16 kHz, chunks de dez minutos com dois segundos de sobreposição; parâmetros e texto bruto de cada chunk preservados em artefato privado. Segmentos suspeitos não são apagados.

QA sinaliza timestamps, repetição, lacunas e texto contido em silêncio medido pelo FFmpeg. Saída suspeita fica em `transcripts/review`, não é publicada; spans de revisão focal ficam em `focused_reviews`, estado `pending_manual_review`. Execução automática da retranscrição focal ainda não é implementada; revisar/decidir esses spans antes de tratá-los como aprovados. Sobreposição preservada pode gerar revisão nas fronteiras, intencionalmente conservadora.

## Pré-requisitos manuais depois de nova autorização explícita

1. Entrar na VPS com `ssh oracle-vps`. Nunca executar inferência no Mac.
2. Revisar `benchmark-plan.json`, assegurar seis aulas, professores/disciplinas distintos, trechos reais de ruído e silêncio, preparar gold humano. O scorer/seleção existem; métricas avançadas do protocolo ainda exigem conclusão. Executar benchmark somente se a nova autorização cobrir essa inferência.
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

Exigir `gate.allowed=true` e fontes corretas. Para um único job autorizado, executar somente então:

    /home/ubuntu/study-hub-venv/bin/python -m fo_hub.worker --run --once

Se a autorização incluir a fila integral e a amostra estiver aceita, iniciar o serviço persistente:

    sudo systemctl start study-hub-fo-transcription.service
    systemctl status study-hub-fo-transcription.service
    journalctl -u study-hub-fo-transcription.service -n 50 --no-pager

Não é necessário habilitar no boot para manter um serviço iniciado ativo. `systemctl enable` só deve ser usado se a autorização incluir reinício após reboot. Não há timer nem início automático amanhã.

## Parada e revogação

`sudo systemctl stop study-hub-fo-transcription.service`, voltar a variável para `false`, remover o arquivo de autorização e manter `systemctl disable`. Não apagar fontes/vídeos/PDFs. Em retomada autorizada, leases interrompidos voltam à fila respeitando limite de tentativas. Artefatos de review são resultados novos, não backups do corpus antigo.

## Verificação realizada sem ASR

Nove testes do worker injetam todos os subprocessos: gate fechado não faz download/lease, Linux/marker/frase obrigatórios, versões ausentes ou divergentes não são consumidas, disco interrompe com retry/backoff, offsets são ms, texto suspeito não é publicado, saída mockada aprovada é servida, texto durante silêncio medido vira review e recuperação remove somente temporários identificados por marker do próprio worker. Download usa limite explícito de tamanho/transferência. Nenhum áudio real foi utilizado. A validação de inferência real fica deliberadamente pendente até nova autorização.
