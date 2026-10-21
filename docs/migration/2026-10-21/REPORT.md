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

## Fechamento operacional — 21/10/2026, auditoria 22:14 UTC

### Privacidade: correção P0 implantada

- A auditoria refutou a suficiência da política v2: havia 6.465 páginas sem classificação e marcas d'água repetidas cujos CPFs eram removidos, mas cujos nomes sem rótulo permaneciam no texto liberado. Nenhum valor pessoal foi copiado para este relatório, testes ou commits.
- A API foi primeiro fechada para políticas anteriores à v3. Depois, a revisão incremental do texto já extraído cobriu **30.111/30.111 páginas** em lotes transacionais de 250. Não se reiniciou extração de PDFs existentes, download ou migração. A revisão agora alcança materiais antigos fora dos manifests correntes — causa das 6.465 páginas antes ignoradas. Reexecuções não reprocessam revisões concluídas.
- Política v3: remove nomes/identificadores em padrões repetidos delimitados, contempla CPF com quebra de linha e bloqueia ambiguidades. A API exige versão atual, exposição e qualidade explicitamente permitidas e revalida o conteúdo ao servir; uma linha em `pdf_page_quality` sozinha não libera texto. Substituir páginas invalida a classificação anterior.
- Observação às **22:14:23 UTC**: **30.003 páginas liberadas como texto**, **108 bloqueadas**, **zero não revisadas**, **zero com política v2 remanescente**. Bloqueadas: 98 aguardando OCR, três com OCR concluído aguardando revisão visual/privacidade, sete em revisão de privacidade. O total de OCR pendente é mutável pelo timer; não interpretar OCR concluído como aprovação de privacidade.
- Verificação textual de todo o índice: 30.003 candidatas liberadas, zero rejeições pelo guard de leitura e zero CPFs válidos residuais detectados. **108 consultas HTTP reais às páginas bloqueadas: zero retornaram texto**. MCP real também devolveu texto vazio para página bloqueada. Estas verificações não equivalem a uma inspeção visual humana de todas as páginas.
- PDFs originais permanecem privados e inalterados. Nenhuma URL de download dos originais foi adicionada à API/Plugin. Não foi necessário gerar PDF derivado nesta entrega; disponibilizar arquivo PDF continua bloqueado até haver derivado com redação permanente e verificação de texto, imagem e metadados. Saneamento do índice textual não saneia o PDF original.

### OCR incremental e recursos

- Implementado `fo_hub.ocr`: uma página por execução, raster de no máximo 1.800 pixels, subprocessos com timeout, reserva de 4 GiB, retries com backoff e limite de três tentativas. Erros persistidos somente por classe, sem conteúdo pessoal.
- Nova unit/timer `study-hub-fo-ocr`: **25% CPU, 512 MiB, cinco minutos, Nice=15**, periodicidade de dez minutos. Compartilha `index.lock` com o indexador e não trabalha enquanto houver páginas sem a política atual. Não executa OCR concorrente com reindexação.
- Tesseract, idiomas português/inglês e Poppler instalados: previsão do gerenciador de pacotes de 29,5 MB adicionais, sem modelos pesados. Extração real de raster/OCR em PDF sintético passou em 0,49 s. Três páginas reais já tiveram OCR concluído sob systemd, sem liberação automática do resultado.
- A saída OCR fica obrigatoriamente bloqueada (`ocr_review`, `ocr_empty` ou `privacy_review`); OCR pode não reconhecer dados pessoais visuais. Temporários deste worker são recuperáveis/descartáveis por escopo próprio, sem alterar originais.

### Catálogo e vídeos

- Duas regressões corrigidas no coletor: erro ao fechar contexto não impede fechamento de browser/driver nem mascara falha original; erro ao persistir checkpoint não vira falsa indisponibilidade de vídeo nem duplica entrada. Correções implantadas durante a espera de retry, sem interromper coleta saudável.
- Simulados concluiu nova reconciliação às **21:58:15 UTC**, 422 itens OK. Intensivo 424, Ciências Básica 27, Matemática 25, Medicina 49 e Redação 24 têm últimas passagens OK. Extensivo tem passagem concluída com 1.070 itens, dos quais 1.065 OK, quatro erros e um não lançado; `status=ok` do curso não significa todos os itens disponíveis.
- **Pendência real:** Semiextensivo conserva último catálogo concluído de 839 itens (838 OK/um não lançado), mas a nova reconciliação falhou com `Locator.evaluate` timeout e mantém checkpoint parcial de 508. O novo processo retomou automaticamente pelo systemd, sem apagar o checkpoint. Houve `Target crashed` anterior, sem evidência de OOM no cgroup inspecionado; não se atribui a causa a OOM nem se declara o crash definitivamente resolvido.
- Descoberta continua dinâmica, sem allowlist de anos/categorias/disciplinas. Oito cursos no catálogo de aulas e nove opções no portal de materiais são conjuntos distintos; não se igualam suas contagens. Materiais: checkpoint `in_progress=false`, última passagem completa em 17:29:52 UTC.
- Corrigida a verificação de vídeo após upload: hardlink temporário mantém o nome estável de retomada; interrupção durante byte check não deixa o único MP4 sob um título fora do caminho esperado. Manifesto continua sendo gravado antes da exclusão local. Não houve reboot real; recuperação foi testada por interrupções sintéticas.
- Inventário OneDrive: **1.077 vídeos / 154.174.794.174 bytes**. Manifesto incremental: 235 `existing_remote_verified`, três `verified`, um `error`. Os legados reconciliados por inventário/tamanho/duração não receberam retroativamente o rótulo de byte check desta sessão.
- Causa comprovada do vídeo em erro: a origem remota atual informa **1.746,368501 s**, enquanto o catálogo exige **2.463 s**. O parcial tem duração compatível com a origem curta. Não é seguro promovê-lo nem reescrever a duração esperada para aceitar o arquivo. Retry agora consulta a origem antes de descartar/rebaixar o parcial; divergência vira `SourceDurationMismatch`, pausa de seis horas e não repete download. Revisão nova pode furar o backoff anterior.
- Dois parciais preservados, **90.754.221 bytes**: um da fonte divergente e outro de revisão antiga da aula atualmente verificada. Não há comprovação byte a byte para excluir o parcial antigo. Limpeza de retry passa a atingir somente a revisão corrente, não outras revisões da mesma aula. Perfis temporários Chromium antigos não foram apagados sem classificação individual.

### API, MCP e autonomia

- API real e quatro serviços Anki vNext ativos. MCP loopback confirmou **26 ferramentas: sete FO + as 19 Anki**, e `anki_health` passou. Sete FO exercitadas em produção, incluindo filtros, paginação, revisões/citações, indisponibilidade, parâmetros inválidos e API fora do ar simulada no adapter, sem parar serviços.
- Corrigidos intervalo PDF invertido (HTTP agora retorna 422 como MCP), desempate por ID na paginação e citações versionadas de materiais. `source_url=null` com `source_access=private_original_not_exposed` é intencional: fontes privadas/signed URLs não devem contornar o bloqueio dos PDFs. Proveniência original continua nos manifests privados quando conhecida.
- Smoke MCP passou no servidor combinado; agora aceita exatamente 19 ou 26 ferramentas conforme opt-in explícito, em vez de falhar por supor sempre 19. Cliente Plugin no ChatGPT não foi acessado/recarregado: **validação ponta a ponta do Plugin permanece pendente**.
- Seis timers não-ASR habilitados/persistentes: catálogo, materiais, vídeos, índice, OneDrive e OCR. Workers oneshot inativos após sucesso não significam serviço parado. Catálogo retomou pelo retry de 15 minutos; os trabalhos permanecem independentes da sessão Hermes. API usa restart on failure.
- OneDrive: `pdf_sync=verified`; leitura real do alvo exato `metadata/sync-status.json` igual ao status local, com inventário acima. Nenhuma operação delete/sync/purge remota. Indexação e OCR concluíram últimas passagens com exit 0. Espaço observado: **7,4 GiB livres**, RAM disponível aproximadamente 21 GiB, sem swap. Nenhum limite Anki alterado.
- SQLite `quick_check=ok`; 3.037 aulas, 3.031 presentes, seis aliases ausentes/superseded, 652 materiais, zero transcrições e zero segmentos publicados. Fila observada com 3.021 queued/seis superseded: indexação pode enfileirar metadados, mas nenhum lease/worker ASR foi iniciado.

### Testes e limites da entrega

- Baseline: 111 testes FO. Após integração inicial: 143 FO e 58 MCP passaram; API Anki vNext: 228 passaram, um aviso de depreciação. Regressões adicionais de fonte curta/limpeza por revisão têm execução final registrada na continuação de publicação.
- Suíte raiz, após instalar a dependência de desenvolvimento já declarada `openapi-spec-validator`: **259 passaram, quatro skipped, uma falha preexistente** em `test_background_queue_mutation_publishes_snapshot_and_media_before_releasing`. Não se alteraram arquivos dirty Anki para ocultá-la. Dois erros iniciais de dependência ausente foram eliminados pela instalação local, sem mudar manifests do projeto.
- Scanners de segredos/arquivos grandes passaram; whitespace das mudanças desta sessão limpo. Arquivos dirty preexistentes permanecem fora dos commits. Nenhum backup/snapshot, migração repetida, merge ou exclusão de originais foi feito.
- Notion sem conexão: não atualizado, sem bloquear operação. Revisão visual das páginas OCR, fonte divergente de vídeo, reconciliação Semiextensivo, Plugin E2E e eventual PDF derivado são pendências reais, não validações concluídas.
- ASR: `TRANSCRIPTION_ENABLED=false`, unit disabled/inactive, autorização ausente, nenhum timer e zero processos de inferência. Preflight read-only continua gate fechado; nenhum áudio real foi processado nem benchmark executado.

### Publicação e verificação final — 22:19 UTC

- Implementação publicada: **`649af484610f20388d20e276294e55cf6e765705`** (`fix(fo): close PDF privacy gaps and harden autonomous recovery`). SHA consultado na branch GitHub, sem merge nem criação de PR. Vinte arquivos de implementação/testes/units incluídos explicitamente, sem stage das alterações Anki preexistentes.
- CI desse commit concluído com **success** em **Federal Online** (run `39685585634`), **Contracts** (`39685585424`) e **Repository Safety** (`39685585493`). Execução local final: **148 FO + 58 MCP passaram**. API Anki vNext: 228 passaram; a falha raiz preexistente acima continua declarada, não mascarada pelo CI limpo da branch.
- A revisão independente identificou e reproduziu um P0 sintético adicional (CPF rotulado inválido não podia isentar nome adjacente da remoção) e um risco latente de promover texto OCR numa futura mudança de política. Ambos corrigidos com regressões RED→GREEN antes do commit. Cada rótulo é avaliado individualmente; classificações `ocr_review`, `ocr_empty` e `privacy_review` continuam bloqueadas em revisões futuras, inclusive quando têm texto. O revisor não conseguiu rodar a suíte pela venv que escolheu; a execução integral acima foi feita pelo coordenador na venv correta, sem atribuí-la ao revisor.
- Varredura do corpus textual após os ajustes de revisão: **30.003 páginas verificadas, zero rejeições pelo guard final e zero CPFs válidos residuais**. Não foi necessário repetir a extração ou rever páginas cujo texto já satisfazia a política; o ajuste de leitura foi carregado na API.
- Leitura às **22:19:25 UTC**: 30.111 páginas sob política atual, 30.003 liberadas/108 bloqueadas; **97 OCR pendentes, quatro OCR em revisão e sete em revisão de privacidade; zero não revisadas**. Sem materiais órfãos nas páginas e sem classificações órfãs.
- Catálogo avançou de **508 para 619** entradas do Semiextensivo, checkpoint durável às **22:19:23 UTC**, após retry automático com o código corrigido. Isto comprova progresso/recovery, **não o término da reconciliação nem a eliminação de todos os crashes possíveis**. Coleta saudável não foi reiniciada para fechar a sessão.
- Indexador, materiais, vídeos, OneDrive e OCR: últimas execuções `Result=success`, exit 0; catálogo em execução; API FO ativa e habilitada no boot. Seis timers ativos/habilitados. Quatro serviços Anki ativos. Vídeo divergente confirmado em produção como `SourceDurationMismatch`, backoff de seis horas, ambos parciais intactos. Nenhum original perdido/promovido sem validação.
- Oito hashes fonte local/VPS comparados sem divergência durante o deploy; ajustes finais de privacidade também implantados. Smoke MCP real combinado passou; leitura OneDrive remota igual ao status local. Descrição textual de ferramenta MCP alterada no código só será recarregada pelo processo Anki em seu próximo restart normal; não se reiniciou o serviço compartilhado apenas para atualizar descrição.
- Disco livre às 22:19:24 UTC: **7.898.013.696 bytes**. Nenhum ASR habilitado: variável false lida do ambiente privado sem mostrar credenciais, unit disabled/inactive, autorização ausente, nenhum timer nem processo de inferência; fila somente queued/superseded.

### Integração do Plugin ChatGPT — auditoria 23:31 UTC

- Sintoma reproduzido no cliente real ChatGPT desktop: Settings -> Plugins -> Anki GPT vNext -> View details -> Apps mostrava **19 ferramentas (nove write/dez read)**. A conexão existente, criada em 13/10/2026, está em `dev mode`/`DEVELOPMENT`; não é uma publicação pública que precise de novo pacote ou submissão.
- MCP ativo em `127.0.0.1:8771/mcp`: **26 ferramentas**, sendo 19 `anki_*` e sete `fo_*`; todos os schemas FO têm raiz `object` e `readOnlyHint=true`. Smoke remoto combinado passou; `fo_get_sync_status` e `fo_list_lessons(limit=1)` responderam sem erro. Nenhuma operação de escrita Anki foi chamada.
- Túnel vivo: canal `main`, transporte `http-streamable`, probe `ok`, aponta para o mesmo `127.0.0.1:8771/mcp`; `/readyz` HTTP 200. `/health/mcp` informa `not_observed`/`unsupported_transport` para evidência de discovery HTTP, não uma lista efetiva de zero ferramentas. Não se alterou configuração, versão ou credencial do túnel.
- Causa confirmada por correção isolada: a descoberta de ferramentas persistida na conexão ChatGPT estava desatualizada. Executado **Refresh tools** no Plugin existente; reabertos os detalhes do mesmo Plugin e lido **26 ferramentas (nove write/17 read)**. Não foi necessário alterar OpenAPI, nomes/schemas das ferramentas, reinstalar/reconectar o Plugin, publicar nova versão nem reiniciar MCP/túnel/API.
- A descoberta atualizada no cliente real está validada. **Limite:** não foi enviada uma nova conversa nem executada uma chamada FO pelo modelo dentro do ChatGPT; as chamadas positivas acima foram via cliente MCP na VPS. Para validar seleção/execução pelo modelo, abrir conversa nova, selecionar `@Anki GPT vNext` e pedir `fo_get_sync_status` e `fo_list_lessons(limit=1)`. Conversas abertas antes do refresh não são evidência de recarga do novo conjunto.
- Testes locais desta auditoria: **206 passaram** (`services/anki-mcp-v2/tests` e `federal-online/tests`). Não houve mudança em código executável nem deploy/restart; README MCP atualizado com ferramentas opcionais, diferença entre discovery MCP e registro ChatGPT, procedimento de refresh e limites da validação.
- Estado read-back às 23:31:11 UTC: quatro serviços Anki vNext e API FO ativos. MCP PID **70375**, túnel PID **3495063** e API FO PID **377374** iguais aos observados antes da intervenção; seis timers FO não-ASR continuam presentes. Nenhum serviço/timer foi alterado nesta intervenção.
- Gate ASR confirmado por `fo_get_sync_status`: **TRANSCRIPTION_ENABLED=false**, `transcripts_validated=0`; unit `disabled`/`inactive`, autorização ausente. Nenhum worker, benchmark, processamento de áudio ou migração foi iniciado.

