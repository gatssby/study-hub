# Federal Online — preparação final de transcrição, 27/10/2026

## Parecer

Preparação de software e infraestrutura concluída para um piloto autorizado, com preflight real aprovado e gates deliberadamente fechados. **Não está homologada a precisão com áudio real nem autorizada a fila integral.** Nenhum modelo venceu benchmark nesta missão. Sem inferência Whisper ASR, sem áudio real baixado/aberto para inferência e sem exclusão de arquivos existentes. O corpus antigo de 1.018 transcrições não foi recriado, migrado ou usado como gold.

Evidência estruturada: `federal-online/transcription/preparation-evidence-2026-10-27.json`. Runbook e comando completo de piloto: `federal-online/transcription/ACTIVATION.md`.

## 1. Implementação e correções

- Stitching de chunks absolutos de 600 s/overlap de 2 s: une somente suffix/prefix inequívocos, com pelo menos três tokens distintos e suporte temporal. Preserva frases interrompidas/continuações, sinais e números científicos e o envelope temporal original. Não estima timestamps de palavras por proporção textual. O bruto não é alterado.
- Overlap esperado não vira regressão temporal. Regressões internas de cada chunk continuam bloqueantes. Fronteiras conflitantes, insuficientes ou repetitivas ficam intactas em review. Uma frase coincidente com timestamps derivados para fora da janela agora recebe `boundary_timestamp_drift`, em vez de duplicar silenciosamente. Repetições temporalmente distintas dentro da janela não são removidas por presunção.
- QA de timestamps não finitos, repetição artificial de tokens/frases, ausência de cobertura e texto em silêncio medido. Lacunas inteiramente explicadas pelo `silencedetect` são observações `measured_silence_gap`, não falhas. São heurísticas conservadoras, não detector infalível de alucinação ou música.
- Checkpoints gzip determinísticos sem perda, checksum de conteúdo/identidade/limites, schema validado e timestamp de criação. Cache inválido é preservado por rename para um irmão único, com motivo/proveniência, e nunca reutilizado. Reexecução exige gate. Texto integral do decoder é preservado antes de parsing, mesmo se o JSON for malformado.
- Raw, comandos, hashes e decisões ficam privados. O documento público contém somente aula, versão, corpus, QA aprovada e segmentos. Review fica isolado, com spans focais `pending_manual_review`, sem descarte de conteúdo incerto.
- OneDrive usa allowlist `--files-from` confrontada com aula/fonte/revisão atuais, QA literal true e segmentos exatos do DB. Symlinks, extras privados, temporários, revisões antigas e arquivos órfãos sem registro validado ficam excluídos. Lock compartilhado na seleção/cópia/check e exclusivo no publicador evita corrida. Um arquivo órfão após falha de DB pode ser preservado em disco; isso não o torna publicável ou servível.
- Consulta MCP/HTTP e contagem de validados exigem aula presente, versão atual, fonte disponível compatível e QA aprovada. Teste de registro opcional de ferramentas agora fica em subprocesso para não poluir a suíte Anki.

## 2. Operação, versionamento e limites

- SQLite com fila persistente, lease por owner, lock de processo, retries limitados a três, backoff e checkpoints retomáveis. Restart recupera predecessor morto sob lock; lease de sete dias é renovado a cada chunk. Timeout máximo ASR por chunk: 48 h. Detectam-se leases vencidos e progresso pelo status. Esses limites não são medição de desempenho real.
- `--lesson-id` restringe o piloto àquela aula; não pode ser combinado com `--loop`. Versões já publicadas são idempotentes; alterações de fonte durante o trabalho rejeitam publicação antiga.
- Observações aditivas de ID/Size/ModTime remoto invalidam revisão, enfileiram substituta e supersedem jobs antigos queued sem roubar leases ativos. Inventário incompleto não apaga metadados fortes; origem ausente de inventário existente fica indisponível. Primeira observação é baseline. **Troca invisível de mesmo tamanho, sem mudança observável de ID/ModTime, não é detectável sem comparar bytes/versão remota.** Inventário atualizado continua necessário depois de validar transcrições.
- Estados físicos legados são preservados, evitando migração destrutiva; status expõe queued, processing, validated, review, failed e superseded (`leased→processing`, `done→validated`, `stale→superseded`). Inclui progresso, total, leases vencidos e estados desconhecidos.
- Três threads ASR, FFmpeg uma thread, uma aula/um vídeo temporário por vez, serviço com CPU 300%, MemoryMax 12 GiB, TasksMax 128, UMask 0077. Reserva 4 GiB mais maior fonte e 100 MiB de temporários antes do lease. `paused_storage` não gasta tentativas; insuficiência durante o trabalho interrompe com tratamento limitado.
- Vídeos não ficam em cache persistente. SHA-256 do vídeo e fingerprint de runtime/modelo/configuração permitem reutilizar inferência entre aliases sem misturar proveniência. Downloads ainda ocorrem para provar bytes; não se ativou cache que confia só em caminho/tamanho. Agrupamento futuro de aliases em um único download exige uma identidade remota forte ou snapshot controlado. Não é requisito de correção nem melhoria de precisão.
- Recuperação/limpeza é limitada a temporários marcados do próprio worker; apenas testada em diretórios sintéticos nesta missão. Logs de erro do worker registram classes, não stderr/URLs assinadas/credenciais.
- Sem boot/timer: após reboot, enquanto disabled, é necessário start manual autorizado para retomar. Habilitar inicialização automática requer decisão futura específica. Aprovação manual/retranscrição focal automatizada não foi implementada; review não retorna automaticamente ao corpus aprovado.

## 3. Whisper e VAD

Runtime instalado: whisper.cpp `1.9.5-dev`, commit `231638a0717b7822784297e5980965ffcec05810`.

- CLI SHA-256: `61f809860bea4cef8a936049280e06006b849a87e7ae35e919e7703237db3c5c`.
- Modelo large-v3 FP16: 3.095.033.483 bytes, SHA-256 `64d182b440b98d5203c4f9bd541544d84c605196c4f7b845dfa11fb23594d1e2`, igual ao objeto LFS oficial consultado. Hashes das bibliotecas são registrados no provenance de cada execução.
- Baseline preparado: `pt`, beam 5, best-of 5, temperatura 0, incremento 0 e `-nf`, no-speech 0,6, entropy 2,4, logprob -1, contexto padrão `-mc -1`, CPU `-ng`, JSON integral `-ojf`; mono PCM s16le/16 kHz, 600 s/2 s. Sem prompts especulativos, tradução ou pós-processamento por IA.
- FFmpeg/FFprobe `6.1.1-3ubuntu5`; rclone `v1.73.1`. Help/version e flags exigidos conferidos no preflight; não foi alterado o runtime/modelo instalado.
- O arquivo `for-tests-silero-v6.2.0-ggml.bin` tem 885.098 bytes e SHA-256 `2aa269b785eeb53a82983a20501ddf7c1d9c48e33ab63a41391ac6c9f7fb6987`, igual aos pesos oficiais Silero v6.2.0. O nome não justifica tratá-lo como dummy.
- A `libwhisper.so` instalada carregou o VAD em CPU e processou **somente dois segundos de zeros em memória**, sem abrir mídia e sem carregar Whisper ASR. Foram 63 frames, todos abaixo do limiar de fala 0,5. Probe reproduzível: `transcription/vad_synthetic_probe.py` (somente zeros, paths da VPS).
- VAD continua **off** no pipeline. A probe comprova integridade, compatibilidade e execução sintética; não comprova retenção de fala baixa, desempenho em música/ruído, nem alinhamento ASR em tempo original após recorte VAD. Essas comparações dependem de autorização real.

Referências de integridade consultadas por API, sem baixar pesos: `https://huggingface.co/api/models/ggerganov/whisper.cpp?blobs=true` e `https://huggingface.co/api/models/ggml-org/whisper-vad?blobs=true`. Detalhes históricos de alternativas: `2026-10-21-fo-asr-benchmark.md`.

## 4. Comparação preparada, não resultado de modelos

O FP16 large-v3 é candidato principal porque já há pesos íntegros e runtime CPU ARM64 instalado/testável, preservando o baseline sem introduzir quantização. Isso é justificativa operacional, não prova de superioridade em PT-BR.

A matriz separa beam 5/fallback off, beam 5/fallback on (incrementos de 0,2) e beam 10/fallback off. Todos precisam dos mesmos áudios e gold para comparação. Quantização q5_0 e large-v3-turbo são alternativas de recursos/velocidade, sem vitória ou derrota de qualidade medida. Qwen3-ASR e candidatos NeMo permanecem alternativas do protocolo histórico, não foram instalados/medidos nesta missão; exigiriam instalação/adapters e avaliação separados. Nenhum corte de RTF elimina um candidato de qualidade por velocidade.

`score-batch` calcula WER/CER ponderados, IC95 bootstrap por segmento de fala, recall por ocorrência e WER restrita ao glossário, caracteres/minuto em não fala, loops de quatro palavras, inserções longas, erros/deriva de timestamps e recursos fornecidos (wall/RSS/RTF/falhas). Speech e full-lesson stability não são misturados nos agregados de WER/CER/termos. Âncoras malformadas e gold/kind/duração inconsistentes entre configurações são rejeitados. IC por segmento não elimina correlação entre aula/professor e não prova equivalência. Normalização v2 preserva acentos, sinais, decimais e operadores científicos.

`benchmark-matrix.json` é metadado, não runner automático; `benchmark-evaluation.md` fornece contrato e procedimento de execução/coleta. O scorer não mede recursos nem gera hipóteses: recebe essas medições reais. A fixture sintética foi pontuada, marcada explicitamente `synthetic=true`/`inference_executed=false`; seus números não medem nenhum modelo e não são publicados como transcrições.

## 5. Pendências necessárias de áudio/gold

`benchmark-selection-2026-10-27.json` contém seis aulas/revisões realmente elegíveis, de seis disciplinas, e 18 janelas propostas por metadados. Ainda faltam:

1. Identificar ao menos dois professores e ouvir para confirmar os estratos de fala/terminologia, ruído/interação, música e silêncio. Metadados não certificam esses estratos.
2. Gold humano verificado de 90 minutos de fala, dois trechos não fala de três minutos, glossário técnico e âncoras temporais; segundo anotador em 20%.
3. Probes curtos de 30 s e fronteiras de 598–602 s; aula longa integral para estabilidade, sem misturar ausência de gold com WER zero.
4. Hashes dos áudios 16 kHz mono, comando de conversão e hipóteses reais/configuração. Medir wall, RSS, RTF, pico de disco e crescimento de evidências; não preencher recursos com estimativas.
5. Escutar e aceitar o piloto, comparar configurações, avaliar ASR+VAD antes de habilitá-lo e então decidir configuração de produção e dimensionamento de armazenamento. Não está comprovado que os ~14 GiB livres comportam todas as evidências do corpus.
6. Validar o primeiro conteúdo real aprovado no MCP e OneDrive; nesta missão houve contrato sintético e chamadas reais com base vazia, não uma transcrição real ponta a ponta nem uma conversa nova no ChatGPT.

O checker do manifesto vazio retorna corretamente `ready=false` e enumera o que falta. Autorização de piloto não deve ser interpretada como autorização de benchmark ou lote integral.

## 6. Testes e homologação técnica sem áudio real

- Local: `services/anki-mcp-v2/.venv/bin/python -m pytest federal-online/tests services/anki-mcp-v2/tests -q` → **322 passed**. Cobrem stitching, fronteiras, sinais científicos, silêncio, retry/restart, cache corrompido, fontes, disco, pré-requisitos, publicação, HTTP/MCP e allowlist OneDrive. ASR/mídia são mocks.
- VPS ARM64, 11 arquivos selecionados com pytest do venv FO e base temporária nova/isolada → **128 passed in 3.89 s**, incluindo rclone real **somente entre diretórios sintéticos locais**, sem publicar conteúdo artificial no OneDrive. Não se instalaram dependências novas.
- VAD: probe real da biblioteca, **entrada sintética em memória**, sucesso; não é teste de qualidade de fala nem inferência ASR.
- CLI benchmark: fixture sintética com IC bootstrap executada; manifesto vazio reprovado como esperado. Sem resultados de áudio real.
- Preflight real `--check-only`: **ready=true**, problems vazio, zero sources inválidas, todas as dependências/flags e SHA aprovados; **gate.allowed=false** pelas duas barreiras esperadas (enabled false e autorização ausente). Não abriu mídia nem tomou lease. `remote_access_verified=false` é correto no JSON do preflight: ele não faz rede; a auditoria remota separada abaixo verificou os caminhos.
- Scanners de segredos e arquivos grandes passaram; diff/check restrito aos arquivos da missão passou.
- Suíte raiz: **259 passed, 4 skipped, 1 failed, 2 warnings**. Falha preexistente preservada, fora do escopo: `apps/anki-gpt/tests/test_regressions.py::test_background_queue_mutation_publishes_snapshot_and_media_before_releasing`. Quatro skips por ausência de `anki.collection`; dois avisos de depreciação `jsonschema.RefResolver`. Há também whitespace preexistente em alterações Anki; não foi corrigido nem incluído.

## 7. Commits, deploy e integração real

- Commit executável: **`51cb0e8da8b31f3dd0a23351c70808865d96c79e`**, `fix(fo): prepare accuracy-first transcription with safe stitching and recovery`, branch `feat/study-hub-migration`. Somente 29 arquivos FO/documentação da missão. Relatório/evidência finais são versionados em commit documental posterior.
- Deploy por archive de caminhos desse commit, sem `--delete`, sem git reset/pull e sem limpar a árvore remota. Pré-condições de SHA impediram sobrescrever alterações desconhecidas. O REPORT remoto era o ancestral conhecido `bc23102`, revisado antes da substituição; não havia edição remota nova a preservar.
- **29 arquivos implantados conferidos byte a byte**, mais **todos os 12 módulos `fo_hub/*.py`** iguais ao commit executável. Registro lido de volta: `/home/ubuntu/study-hub-state/federal-online/deploy/transcription-51cb0e8da8b31f3dd0a23351c70808865d96c79e.json`.
- Reiniciada **somente `study-hub-fo-api`** para carregar serving/status novos. Nenhuma unit/configuração Anki foi modificada; os quatro PIDs Anki permaneceram iguais ao snapshot anterior ao deploy. Nenhum start/restart de ASR.
- Smoke real no transporte MCP existente: **26 ferramentas (19 Anki + sete FO)**; `anki_health` e `fo_get_sync_status` aprovados; `fo_search_transcripts` retornou vazio, `fo_get_transcript` retornou `fo_not_found`/404 para o piloto, como exige a base sem transcrições. Nenhuma escrita Anki chamada. Isso não comprova execução pelo modelo no cliente ChatGPT.
- Não foi realizado push nesta missão. Alterações preexistentes Anki e arquivos alheios continuam na árvore local, fora dos commits/deploy FO.

## 8. Estado observado e reconciliação posterior

**27/10/2026, 19:09:20 UTC:**

- SQLite `quick_check=ok`; **3.299 queued, 24 superseded, 3.104 queued elegíveis**. Processing/validated/review/failed: zero. Zero transcrições e zero segmentos; nenhum lease vencido. Elegíveis passaram de 3.102 no inventário fornecido para 3.104 na nova observação; não se inferiu o motivo dessa diferença.
- Auditoria rclone separada às 19:09:19 UTC: **2.252 caminhos físicos elegíveis distintos, 2.252 arquivos remotos**, zero origens ausentes, zero divergências de tamanho, zero bytes de mídia baixados. Há 851 grupos de aliases e 853 vínculos adicionais entre todas as fontes disponíveis; escopos de contagem diferem da seleção só queued elegível.
- Publicação `onedrive:Study Hub/Federal Online/Transcripts/generated_v2`: diretório existente/acessível, **zero arquivos publicados**. O diretório vazio foi criado e verificado, sem transcrição artificial. Cópia de uma transcrição real permanece pendente do piloto.
- Livre: **14.971.527.168 bytes (13,94 GiB)**; RAM disponível **22.738.841.600 bytes (21,18 GiB)**; quatro vCPUs. São snapshots, não capacidade garantida futura. Reserva configurada **4.294.967.296 bytes**; maior fonte **697.698.800 bytes** no preflight.
- ASR: `TRANSCRIPTION_ENABLED=false` persistente; `study-hub-fo-transcription` **inactive/disabled, MainPID=0**; autorização ausente; nenhum timer/processo ASR. Nenhuma inicialização automática criada.

### Read-back final após indexação já agendada — 19:21:46 UTC

O indexador não-ASR existente executou às 19:10:53–19:11:02 UTC, exit status 0, e voltou a executar sem erro. A migração aditiva agora está observada na base real: **2.478 observações de fonte**; **159 jobs de revisões antigas marcados superseded**. A fila corrente é **3.140 queued e 183 superseded**, mantendo **3.104 elegíveis**, zero transcrições/segmentos e nenhuma inferência. Não são 159 aulas transcritas ou excluídas: trata-se de reconciliação de estado/versionamento. Não foi criado/reconfigurado esse timer, nem iniciado manualmente o indexador.

Última indexação registrou zero jobs novos, zero páginas PDF novas e zero erros PDF. `quick_check=ok` e preflight real repetido **ready=true/gate.allowed=false**. Disco livre **14.969.307.136 bytes**; RAM disponível **22.751.297.536 bytes**. Gates, serviço ASR inativo/desabilitado, ausência de autorização/timer/processos e PIDs Anki inalterados foram reconfirmados. O JSON de evidência preserva também o snapshot anterior para não apagar a história dos contadores.

### Fechamento da cobertura de aliases — 19:34:13 UTC (estado final)

A auditoria adicional identificou 627 vínculos elegíveis persistidos fora da descoberta atual do catálogo, sem observação de fonte. Corrigido no commit **`fd42367852d53945a225c4de09039ad25da552b3`**, implantado com quatro hashes conferidos: todos os aliases classificados agora recebem baseline/invalidação e podem recuperar disponibilidade sem recriar identidades aposentadas ou promover mapeamento de revisão antiga. Inventário só substitui upload verificado de tamanho divergente com SHA do snapshot e início da listagem comprovadamente posterior à verificação; mtime de conclusão sozinho não prova essa ordem. Inventário legado sem prova permanece conservador. Prova nova é registrada pelo sync existente; nenhuma sincronização em massa foi iniciada nesta missão.

Reconciliação manual **somente de metadados**, sob lock existente e `index_pdfs=False`: zero jobs novos, zero PDF/ASR, **3.105 observações**, **zero fontes disponíveis ou jobs elegíveis sem observação**. Após reconciliações já agendadas, estado final **3.138 queued, 185 superseded, 3.104 elegíveis**, zero processing/validated/review/failed/transcrições/segmentos; **161 jobs de versões antigas superseded** no total. Não houve exclusão de arquivos/aulas nem mudança de autorização.

Verificação final: **340 testes locais FO/MCP**, **146 testes sintéticos na VPS**. O ARM revelou um teste cujo glob dependia da ordem de diretório; corrigido no commit **`9e0e58d13fa38c4792519c1358e300fd7e1ff128`**, implantado e repetido com sucesso. Não era defeito de perda de evidência no worker. **Todos os 12 módulos atuais FO** foram reconferidos contra `fd42367`. MCP real repetido: 26 ferramentas/19 Anki/sete FO, status e buscas corretos. Preflight repetido **ready=true**, gate fechado. Os números anteriores nesta seção e no histórico de testes são snapshots preservados, não o resultado final.

Livre **14.945.374.208 bytes (13,92 GiB)**; RAM disponível **22.652.657.664 bytes (21,10 GiB)**. Persistem false, inactive/disabled, autorização ausente, sem timer/processos ASR. Somente a API FO foi reiniciada; componentes Anki não foram reiniciados/modificados. Não foi feito push. Evidência e relatório completos são entregues em commit documental posterior; registros de deploy por commit ficam em `state/deploy/transcription-<sha>.json` com leitura de confirmação.

## 9. Piloto e ativação posterior

Somente depois de nova autorização, criar a autorização root-owned com a frase exata do runbook. Para piloto, manter o ambiente persistente false e usar a unit transitória limitada com `--setenv=TRANSCRIPTION_ENABLED=true`, `--run --once --lesson-id fo_21fd4985e207c5df`. O comando completo está em `ACTIVATION.md`, linha 55: seleciona **Desenvolvimento embrionário**, Biologia I, versão observada 1. Reconfirmar elegibilidade antes; não habilita boot nem consome outra aula.

Inspecionar o JSON de resultado, evidências e QA; exit zero sozinho não é aceitação de precisão. Só após aceitação humana e autorização que cubra a fila integral, configurar enabled true no ambiente FO e iniciar manualmente `study-hub-fo-transcription.service`. Monitorar journal, estados/progresso MCP, leases vencidos, MemoryCurrent/MemoryPeak, CPU e disco. Ao atingir reserva, pausar/ampliar armazenamento sem apagar evidências. Parar serviço, voltar false e revogar autorização se necessário. Boot requer autorização adicional específica; não criar timer.
