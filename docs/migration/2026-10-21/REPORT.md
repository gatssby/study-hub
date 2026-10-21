# Study Hub — relatório da migração de 21/10/2026

Relatório histórico da migração, com atualização operacional de 21/10/2026 abaixo. O snapshot inicial das contagens é das 05:22:59 UTC (02:22:59 -03); a seção de continuidade prevalece para o estado posterior. Nenhuma data substitui a autorização explícita exigida para transcrições.

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

## Continuidade operacional — 21/10/2026, após auditoria externa

Não se repetiram migrações nem exclusões. A branch continua `feat/study-hub-migration`, sem merge na principal. Os 16 arquivos fonte modificados preexistentes foram conferidos por SHA-256 e permaneceram idênticos; as 85 entradas anteriores não foram incluídas nos commits desta correção.

### Causas e correções

- **OneDrive:** o serviço estava failed após `rclone check`; a implementação descartava stderr e gravava `pdf_sync=absent` mesmo diante de falha. A causa exata daquele erro remoto não pode ser recuperada com certeza dos logs antigos. Foram reproduzidas duas falhas locais reais: inclusão de PDFs em `.build_*` ainda não publicados e ausência de exclusão mútua entre promoção e copy/check. Corrigidos os filtros e adotado lock compartilhado durante copy/check, exclusivo na promoção. Downloads continuam em staging enquanto a promoção aguarda. Status passa a registrar fase/código da falha atomicamente; diagnóstico privado tem URLs/tokens redigidos. Nenhuma divergência foi ignorada nem foi usado delete/sync/purge remoto.
- **Filtros:** a busca por substring classificava `Sociologia - Federal` como disciplina estrangeira dentro de `Sociologia - Federal - Intensivo`. A validação agora usa a célula exata da disciplina e continua recusando linhas realmente estrangeiras.
- **PDFs de Medicina:** o portal oferece `btnMaterialView`, não download, e deixa o modal aberto. Usa-se o endpoint de metadados `documento-online-key` e sua URL, sem abrir o viewer. O primeiro ensaio após o reparo revelou OOM; esses PDFs têm **228.728.330 e 126.305.935 bytes**. Abrir canvases ou reter o corpo no driver Playwright não é seguro no limite de 2 GiB. O transporte passou a streaming HTTPX com cookies por domínio, limite de 256 MiB/120 segundos, validação `%PDF-` e publicação atômica do temporário. Não se aumentou o limite de memória para ocultar o problema.
- **Indexação:** o glob também podia aceitar manifesto `.build_*`. Acrescentado teste e exclusão dessas entradas; só material publicado deve ser indexado.

### Evidência em produção

- OneDrive corrigido concluiu em **17:19:24 UTC**; nova passagem após publicação dos PDFs concluiu em **17:36:49 UTC**, ambas `Result=success`, `ExecMainStatus=0`. Byte check real e leitura de volta do alvo remoto `metadata/sync-status.json` iguais ao estado local; `pdf_sync=verified`. O campo `updated_at` identifica o início da passagem (17:30:48 UTC), não seu horário de conclusão.
- Materiais concluíram em **17:29:52 UTC**, `Result=success`, `ExecMainStatus=0`, `NRestarts=0` desde o reinício controlado. Checkpoint `in_progress=false`, `done=[]`, sem loop de retry pendente. Journal confirmou ambos os PDFs de Medicina via document key e download de Sociologia sem erro incoerente. Pico observado após streaming: **732.798.976 bytes**; journal registrou 698,8 MiB no encerramento.
- Catálogo: os oito cursos já possuem passagem concluída OK: Base 424, Ciências Básica 27, Extensivo 1.070, Matemática 25, Medicina 49, Redação 24, Semiextensivo 839 e Simulados 422. Nova reconciliação do Extensivo está avançando por checkpoint; não se confunde isso com catálogo parado ou remoção de aulas.
- Vídeos: estado incremental passou a **219 existing_remote_verified + 1 verified**, sem item error nessa leitura. A tentativa antes incompleta foi validada pelo worker persistente, não por download manual do coordenador.
- Reindexação após os PDFs concluiu em **17:31:37 UTC**, `Result=success`, `ExecMainStatus=0`. Banco observado às **17:32:20 UTC**: **3.033 aulas, 652 materiais, 30.111 páginas**, 3.017 jobs queued e seis superseded. Tabelas `transcripts` e `transcript_segments` continuam com zero linhas; queued não significa execução de inferência.
- Anki sync/API/MCP/túnel e API FO permaneceram ativos. Gate ASR continua false, autorização ausente, unit disabled/inactive, preflight `inference_executed=false`.

### Testes e commits desta continuidade

- **106 testes FO locais passaram**. Regressões RED→GREEN para filtros exatos, recuperação do PDF, segredo fora do log, transporte sem viewer, limites de streaming, exclusão de staging/lock real rclone, fases de falha e manifesto de indexação ainda não publicado. O teste rclone local não usa rede nem áudio; a validação remota real é separada.
- `c558b97`: recuperação de PDFs/filtros, publicação coordenada e diagnóstico OneDrive.
- `00c8dc5`: streaming dos PDFs grandes, sem canvases/retention no driver.
- `58fe728`: indexação somente de manifestos publicados.
- Commits publicados e alvo GitHub consultado. CI do `58fe728` concluído com sucesso em **Federal Online, Contracts e Repository Safety**; mesmas três verificações verdes em `c558b97` e `00c8dc5`. Hashes locais/deploy iguais nos quatro fontes alterados (`onedrive.py`, `ingest.py`, runtime e extrator de materiais).
- Revisão independente de `c558b97`/`00c8dc5` não encontrou defeitos importantes e executou 105 testes. O pequeno ajuste posterior `58fe728` teve teste RED→GREEN próprio, suíte local de 106 testes e CI verde; não se atribui esse ajuste à revisão anterior.
- Limites conhecidos, não bloqueantes no ensaio real: transferência do PDF falha explicitamente acima de 256 MiB ou 120 segundos; documentos maiores/conexão lenta podem exigir revisão desses limites. A promoção aguarda o lock do OneDrive, cujos dois subprocessos têm timeout de 7.200 segundos cada. Não se encobre essa espera como download travado.
- Alterações de terceiros continuam locais. A checagem global de whitespace ainda acusa avisos preexistentes nos arquivos Anki; eles não foram corrigidos incidentalmente. Nenhum merge foi executado, nenhum backup criado e nenhum dado compartilhado apagado nesta continuidade.

## ATIVAÇÃO DAS TRANSCRIÇÕES — AGUARDANDO AUTORIZAÇÃO DO USUÁRIO

Não executar comandos de ativação antes de nova autorização explícita. O marco 22/10/2026 não é autorização nem há agendamento automático.

Procedimento exato em `federal-online/transcription/ACTIVATION.md`. Exige executar somente na VPS, validar versões/fontes/disco/modelo, nova decisão do usuário, configurar variável true e criar `/etc/study-hub/fo-transcription.authorized` com a frase `I AUTHORIZE FO TRANSCRIPTION ON VPS`. Só então preflight deve mostrar gate permitido e o serviço pode ser iniciado manualmente. Nenhum desses passos de ativação foi executado. Benchmark real deve preceder promoção de um modelo como vencedor. Não há timer nem data de ativação automática.

## Continuidade operacional — auditoria posterior, 21/10/2026 21:08 UTC

- Branch local e remota continuam `feat/study-hub-migration`; o commit publicado mais recente é `1715c45604083efdd631fd8f110e79f16c263a7e`. Os arquivos Anki e demais alterações dirty preexistentes continuam fora dos commits FO.
- Auditoria VPS: API FO ativa; Anki vNext sync/API/MCP/túnel ativos; materiais, vídeos e OneDrive concluíram suas últimas execuções com `Result=success`; catálogo está em execução/retry persistente; indexação está em execução contínua sob systemd, com `TimeoutStartSec=12h`, independente da sessão Hermes.
- Contagem observada durante a reconciliação: 3.037 aulas, 652 materiais, 30.111 páginas, zero transcrições publicadas, 3.020 jobs queued e seis superseded. A contagem anterior não é tratada como final enquanto catálogo/indexação continuam.
- A primeira política de privacidade experimental foi rejeitada após auditoria de falso positivo (rótulos genéricos marcavam quase todas as páginas). A política publicada `v2` limita a remoção automática a CPF válido e nome explicitamente associado ao marcador; páginas ambíguas são bloqueadas, não expostas. A reindexação completa está em andamento sob o serviço `study-hub-fo-index`; não declarar a cobertura final antes da conclusão.
- O serviço indexador já registrou páginas com a política v2 enquanto continua trabalhando. A API foi reiniciada após o deploy para carregar o código novo. O resultado final, inclusive páginas `ocr_pending` e `privacy_review`, será verificado após o término.
- Mesmo durante a reindexação, a API agora retorna texto vazio para toda página `blocked` ou `legacy_unreviewed`; a verificação real encontrou dez páginas bloqueadas consultadas e zero com texto exposto.
- Vídeos: o manifesto observado durante a coleta tinha 235 `existing_remote_verified`, três `verified` e um `error`; havia dois temporários `.partial.mp4`. O código agora remove apenas parciais não validados do job correspondente antes de nova tentativa e preserva parciais de outros jobs.
- Espaço observado: 7,5 GiB livres de 46 GiB; RAM disponível aproximada de 19 GiB, sem swap. A reserva de armazenamento dos vídeos permanece ativa.
- O Notion continua sem conexão (`connected=false`); não foi autorizado login nem criado conteúdo remoto. Não há roadmap local identificável além dos documentos de migração/research existentes.
- O gate ASR permanece fechado: `TRANSCRIPTION_ENABLED=false`, arquivo de autorização ausente, unit desabilitada/inativa, nenhum timer ASR e nenhum processo de inferência. Nenhuma fila foi consumida.

