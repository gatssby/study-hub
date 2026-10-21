# Study Hub — relatório da migração de 21/10/2026

Estado verificado em 21/10/2026; snapshot das contagens às 05:22:59 UTC (02:22:59 -03). Coletas iniciais longas continuam por systemd. Nenhuma data substitui a autorização explícita exigida para transcrições.

## Regras e decisões

- `TRANSCRIPTION_ENABLED=false`; nenhuma inferência ASR em áudio real, nem sample, foi autorizada ou executada pelo novo pipeline.
- Sem backups. Exclusões somente após classificação de consumidores e preservação de originais/fontes/editorial.
- Priorizar produção e extração do core existente da VPS; não reescrever o portal inteiro.
- Ruling: manter os pacotes Anki vNext em caminhos atuais no Git e VPS, com `anki-vnext/README.md` como mapa. Mover código/coleção só para estética teria risco sem ganho.
- Ruling: arquivos locais preexistentes modificados e de função ainda ambígua não são removidos cegamente. Produção antiga pode ser retirada sem destruir trabalho local do usuário.
- Ruling: a fila inclui originais remotos ainda ausentes de catálogo parcial. Quando a ligação do portal aparece, identidade remota provisória é marcada superseded, não transcrita duas vezes.

## Auditoria e preservação

VPS ARM64, aproximadamente 24 GiB de RAM, sem GPU, quatro vCPU. Serviços Anki vNext mantidos ativos: sync oficial, API v2, MCP e túnel. Coleção/mídia atuais intocadas. Os 19 arquivos Knowledge/Instructions/referências em `apps/anki-gpt/gpt-knowledge` preservados; hashes em `knowledge-inventory.json`.

Inventários operacionais mínimos, sem texto antigo, em `/home/ubuntu/study-hub-state/federal-online`: `migration-inventory.json`, `retirement-transcripts.json`, `retirement-apps.json`. São manifests de contagens/limites, não backups.

## Remoções verificadas

- `/opt/cronograma-fo` ausente; aplicação, banco e arquivos exclusivos retirados.
- `/home/ubuntu/fo-transcricoes-system` e `/home/ubuntu/fo-transcricoes` ausentes.
- 1.018 Markdown de transcrição antiga e quatro cópias de limpeza excluídos.
- Três linhas cron do legado removidas; cron n8n não relacionado preservado.
- `fo-queue-api` e `fo-vps-worker`: inactive e masked.
- Backend antigo, watchdog e porta 8767 retirados. `/home/ubuntu/anki-gpt-sync` contém somente `state`, com mídia não equivalida preservada.
- 12.359 arquivos de mídia do cache comprovadamente iguais à coleção atual excluídos; 1.262 arquivos sem equivalente atual preservados para não perder mídia legítima.
- Local: `apps/cronograma-fo`, workflow `cronograma-ci.yml`, job de reprogramação e ops exclusivos retirados. Referências históricas Git/documentos não são infraestrutura executável.

Espaço: livre antes da limpeza 8.921.595.904 bytes; após retirada de apps 13.994.205.184 bytes, ganho observado de 5.072.609.280 bytes antes da preparação dos modelos. Na verificação posterior havia 10.079.600.640 bytes livres, com modelos/dependências e coletas em andamento. Não confundir ganho bruto de limpeza com saldo depois das instalações.

## Componentes implantados

Código FO `/home/ubuntu/study-hub/federal-online`; estado independente `/home/ubuntu/study-hub-state/federal-online`; venv própria e ambiente privado fora do Git.

- API FO: ativa em loopback 8780.
- Catálogo: timer habilitado, coleta completa inicial em execução por systemd, oito cursos descobertos dinamicamente. Corrigida navegação portal → cursos → produtos e isolamento de lifecycle Playwright. Checkpoint corrente chegou a 395 entradas OK do primeiro curso, com progresso no journal. O registro `courses.json` ainda conserva oito erros da passagem anterior enquanto o curso atual não termina; isso não é uma validação completa dos oito cursos. Cursos concluídos ficam elegíveis para nova reconciliação após seis horas, não somente semanalmente.
- Materiais: timer habilitado e primeira reconciliação por curso em execução; 36 disciplinas observadas no Extensivo 2026. Um erro de contrato em linhas de download falho interrompeu a primeira passagem; corrigidos o contrato de erro sem arquivo e o checkpoint que marcava done antes da promoção. 156 PDFs autenticados em staging foram promovidos sem cópia/backup e com hash verificado; fonte URL não persistida foi explicitamente marcada como indisponível, não inventada. Jobs foram reabertos para reconciliação. Retry systemd em 15 minutos após falha, além do timer diário.
- Vídeos: timer habilitado; primeiro ciclo reconciliou 219 originais já existentes e registrou uma tentativa incompleta, sem promover/uploadar um vídeo truncado. Retry persistente/backoff; pendência real, não declarar todas aulas disponíveis.
- Indexação: timer habilitado; páginas PDF disponíveis pela API.
- OneDrive: timer habilitado; última cópia PDF verificada e metadados remotos confirmados por leitura do alvo exato. Sem exclusão remota por ausência de catálogo.
- Transcrição: worker real implementado e implantado, testado com subprocessos mockados; unit `disabled` e `inactive`, sem timer. Preflight `fo_hub.worker --check-only`: gate fechado por variável false e ausência de autorização. Zero processos whisper-cli/whisper-server/whisper-stream. Nenhuma inferência executada.

## Contagens observadas (mutáveis durante coleta)

OneDrive: 1.074 vídeos, 153.904.975.723 bytes. Manifesto relaciona 1.070 aulas com originais remotos; nenhuma fonte desses vínculos faltava no inventário inicial.

Consulta SQLite às 05:22:59 UTC: 1.180 registros de aulas (incluindo identidades remotas provisórias), 219 PDFs distintos por SHA-256, 10.618 páginas indexadas, 1.161 jobs queued e zero transcrições publicadas. Destes, 1.075 vínculos de source disponíveis e 86 fontes pendentes; 1.075 vínculos não significam 1.075 vídeos distintos (o inventário remoto tem 1.074). Zero jobs de versão stale na leitura anterior. Fila e catálogo ainda em reconciliação; não interpretar contagens como total final do portal.

## MCP/Plugin

Produção verificada por cliente MCP no endpoint loopback 8771: 26 ferramentas = 19 Anki preservadas + 7 FO read-only. Chamadas reais `fo_get_sync_status`, `fo_list_lessons` e `fo_search_materials` retornaram sem erro.

FO: `fo_list_lessons`, `fo_get_lesson`, `fo_search_materials`, `fo_get_pdf_text`, `fo_search_transcripts`, `fo_get_transcript`, `fo_get_sync_status`.

O mesmo túnel MCP existente expõe o servidor; uso pelo cliente Plugin após atualização/listagem de ferramentas ainda exige verificação ponta-a-ponta do cliente. Não confundir servidor disponível com Plugin recarregado.

## Modelos e benchmark

Pesquisa comparativa em `docs/research/2026-10-21-fo-asr-benchmark.md`. Large-v3 é candidato local de alta precisão, não vencedor medido; alternativas abertas também documentadas. Protocolo reproduzível preparado sem inferência real.

Serviço separado preparou whisper.cpp e pesos large-v3-f16. Manifest de preparação confirma `inference_executed=false`; tamanho 3.095.033.483 bytes, SHA-256 `64d182b440b98d5203c4f9bd541544d84c605196c4f7b845dfa11fb23594d1e2`. Isso verifica download/preparação, não qualidade em PT-BR.

## Testes

- FO: 93 testes passaram, incluindo nove testes do worker com subprocessos injetados, sem áudio real.
- MCP Anki vNext: 56 passaram após integração opt-in FO.
- API Anki vNext: 228 passaram, com um aviso de depreciação do TestClient.
- Raiz/addon antigo: 259 passaram, quatro skipped por ausência da biblioteca Anki nesse ambiente e uma falha no teste `test_background_queue_mutation_publishes_snapshot_and_media_before_releasing`. A falha está no fluxo antigo de snapshot com alterações locais preexistentes; não foi mascarada. O traceback conserva o caminho antigo; o comando foi executado no workspace renomeado, não no caminho antigo.
- Varreduras `check_no_secrets.py` e `check_large_files.py`: passaram. `git diff --check` identificou whitespace em arquivos addon preexistentes não incluídos nesta migração.
- Regressões novas reproduzidas RED→GREEN: navegação por produtos, Playwright sync em thread própria, materiais independentes do lock longo de catálogo, source inválida após revisão e supressão de fallback remoto duplicado.
- Testes ASR somente mocks/fixtures; nenhum áudio real.
- CI do commit publicado `015009f`: Federal Online, Contracts, Repository Safety e Anki GPT concluídos com success. A suíte limpa do CI Anki passou; o teste local falho acima inclui alterações dirty anteriores, não incluídas no commit.
- `systemd-analyze verify` das sete units FO: exit 0. Hashes de 19 fontes Python FO comparados com a VPS: zero divergências. Refresh privado do token rclone permitido no sandbox, sem alterar configurações compartilhadas.

## GitHub

Repositório renomeado com sucesso para `gatssby/study-hub`, visibilidade pública preservada. Remote local atualizado e lido novamente. Branches remotas originais preservadas; produção não faz git pull do nome antigo (deploys por arquivos). Workflow remoto Cronograma desabilitado manualmente; arquivo removido na branch publicada `feat/study-hub-migration`. A branch padrão ainda não foi mesclada, portanto conserva código histórico; não há deploy Cronograma ativo associado.

Commit de desenho/plano: `941b1eb`. Implementação e retirada classificada: `015009f417bb3a9f67e59a57a1d293f2140ddc6a`, publicado e confirmado pela API GitHub na branch `feat/study-hub-migration` (199 arquivos, 8.146 inserções e 31.978 exclusões). Branch original preservada; 85 entradas preexistentes do workspace permaneceram fora do commit. Push inicial pelo osxkeychain expirou sem publicar; retry com helper gh por comando publicou sem mudar configuração global ou expor credenciais.

## Pendências e limites

- Worker real preparado com gates, validação por mocks e unit desabilitada/inativa. Validação de inferência real intencionalmente pendente até autorização. Revisão focal registra spans e preserva texto; execução automática desses spans ainda pendente.
- Coletas iniciais extensas em andamento; confirmar completude por curso e erros no próximo checkup.
- Tentativa de vídeo incompleta precisa renovar origem/reavaliar duração, não promover truncado.
- Mídia Anki exclusiva e código local antigo dirty: exclusão bloqueada somente para o conjunto ambíguo.
- Merge para a branch padrão e verificação do cliente Plugin após reload permanecem pendentes; implantação VPS não depende desse merge.
- Notion: conector consultado, `connected=false`; não atualizado e não bloqueia produção.
- Delegações falharam por HTTP 429 do provedor. O coordenador assumiu integração e implementação do worker; não se considera a mensagem de falha como evidência de código concluído.
- Revisão independente também bloqueada por HTTP 429. Realizada auto-revisão de segurança pelo autor, mais fraca que revisão independente. Corrigidas recuperação de temporários marcados, limite explícito rclone por tamanho, checkpoint de materiais e permissões mínimas de refresh de token rclone. Configurações compartilhadas de outros projetos não foram editadas.

## ATIVAÇÃO DAS TRANSCRIÇÕES — AGUARDANDO AUTORIZAÇÃO DO USUÁRIO

Não executar comandos de ativação antes de nova autorização explícita. O marco 22/10/2026 não é autorização nem há agendamento automático.

Procedimento exato em `federal-online/transcription/ACTIVATION.md`. Exige executar somente na VPS, validar versões/fontes/disco/modelo, nova decisão do usuário, configurar variável true e criar `/etc/study-hub/fo-transcription.authorized` com a frase `I AUTHORIZE FO TRANSCRIPTION ON VPS`. Só então preflight deve mostrar gate permitido e o serviço pode ser iniciado manualmente. Nenhum desses passos de ativação foi executado. Benchmark real deve preceder promoção de um modelo como vencedor. Não há timer nem data de ativação automática.
