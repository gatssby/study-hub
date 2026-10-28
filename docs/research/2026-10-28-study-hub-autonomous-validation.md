# Study Hub — missão autônoma de validação, 28/10/2026

Aviso de supersessão: a entrega consistente de texto da política PDF v4 registrada abaixo **não atesta preservação acadêmica**. Revisão independente posterior demonstrou exclusão excessiva e redação parcial; correção v5 `97983a5` bloqueia campos ambíguos sem eliminar linhas acadêmicas. Migração v5 concluída; não homologar v4. Contagens abaixo são snapshots históricos; o marco de 05:06 UTC registra o estado mais recente e a pausa de produtores mutáveis.

## Andamento e autoridade

Em execução. A autorização desta missão cobre um piloto completo (`fo_21fd4985e207c5df`) e até 18 janelas reais de cinco minutos, com comparações adicionais nas janelas informativas. Não cobre fila integral, boot ou worker permanente. Documentos de 21/10 e 27/10 são históricos; a autorização explícita de 28/10 prevalece apenas neste escopo.

Snapshot inicial: 28/10/2026 03:26 UTC. Branch `feat/study-hub-migration`; alterações Anki preexistentes preservadas. VPS acessível. ASR geral inactive/disabled; autorização ausente; ambiente persistente `TRANSCRIPTION_ENABLED=false`. RAM disponível 20.138 MiB; disco livre aproximadamente 14 GiB. Pesos e executável SHA-256 correspondem à matriz; runtime commit `231638a0717b7822784297e5980965ffcec05810`.

Ruling: preservar revisão manual do primeiro piloto mesmo se QA automática passar — sucesso de execução não comprova qualidade acadêmica. O custo é adiar publicação/integracão positiva até revisão fundamentada; evita promover automaticamente resultado ainda não homologado.

Frentes independentes: pai opera ASR e QA; auditoria PDF e auditoria operacional/MCP delegadas com caminhos de relatório separados. Sem inferência no Mac.

## A. Whisper

Piloto iniciado às 03:32:19 UTC; primeira tentativa terminou em retry após 6,81 s, antes de inferência, porque `rclone copyto` recusa o filtro `--max-size` em origem single-file. Reprodução real `--dry-run` confirmou a mensagem. Corrigido sem remover orçamento `--max-transfer ... HARD`, reserva de disco, verificação de tamanho e SHA. A autorização foi revogada automaticamente no fim dessa tentativa.

Segunda tentativa iniciada às 03:39:21 UTC em `study-hub-fo-pilot-20261028-a2.service`, uma aula/revisão exata, CPU 300%, MemoryMax 12 GiB, TasksMax 128, RuntimeMax 18 h, UMask 0077; ExecStopPost root remove a autorização. ASR real observado: um processo `whisper-cli`, memória corrente aproximadamente 4,1 GB, job leased tentativa 2. Dados privados recuperáveis em `/home/ubuntu/study-hub-state/federal-online/validation-2026-10-28/`. Serviço geral e ambiente persistente continuam desativados. Resultado ainda em execução, não homologado.

Correções já testadas: opção `FO_ASR_REVIEW_ONLY=true` impede publicação do primeiro piloto; logs stdout/stderr privados e wall time por chunk; diagnósticos privados de subprocessos; QA de três repetições de frases até 64 tokens, incluindo segmentação/minutos/fronteiras, sem apagar texto; métricas de candidatos por minuto atribuído ao início do segmento (não alinhamento inventado de palavras). Raw QA e QA pós-stitching têm origens distintas. Candidato não é classificação de alucinação: exige revisão acústica. Gold humano, WER/CER, silêncio acusticamente comprovado e precisão de timestamps continuam não medidos.

## B. PDFs

Auditoria inicial concluída e aprofundamento em andamento; detalhes em `2026-10-28-fo-pdf-validation.md`. Snapshot: 3.147 materiais, 143.265 páginas; 511 OCR e 34 privacy_review bloqueadas originalmente. Seis páginas renderizadas privadamente, três inspecionadas visualmente e três reextraídas; isso não homologa o acervo inteiro. Política 4 fecha aliases de rótulo e campos vazios; varredura identificou 122 páginas antes liberadas que precisam bloquear. Commit `5613aae` implantado por hashes, 14 testes de privacidade/OCR na VPS passaram; reiniciada somente API FO. Reclassificação incremental sob lock do índice em unidade CPU50%/1GiB está em andamento, sem reextrair os PDFs. Originais preservados; dados pessoais não pertencem ao Git. Não há derivado visual aprovado.

## C. Study Hub

Auditoria inicial em `2026-10-28-fo-operations-validation.md`, commit `018c1ce`: 26 ferramentas MCP reais (19 Anki e sete FO), sete FO chamadas read-only; PDF positivo e transcrição ausente negativa esperada. Sem teste de interface ChatGPT. Cursos 11, um erro; oito erros de vídeo e 20 jobs queued sem source elegível. Novo trabalho delegado corrige curso erroneamente marcado ok ao conter item error e a semântica incompleta do status. Não recriar Cronograma ou legado Anki.

## D. Infraestrutura

Commits ASR: `80adc25`, `a3503e5`, `ffd97fb`, `b0a2caa`. Deploy de três módulos ASR e dois arquivos de testes verificado por SHA-256 contra bytes locais commitados; nenhuma reinicialização Anki. 305 testes FO locais e 58 testes MCP locais passaram; subset VPS atualizado: 27 passed. Três falhas OCR inicialmente observadas foram encaminhadas à frente PDF; a suíte subsequente está verde, sem atribuir correção à mudança ASR. Revisão independente dos eixos segurança/spec e manutenção/correctness em andamento.

Serviço ASR geral permanece desativado. Toda autorização temporária deve ser revogada no encerramento das inferências; unidade transitória executa revogação em ExecStopPost também em falha.

Runner privado de comparações limitadas, commit `37bd2f1`: seis IDs e três janelas congeladas por aula (máximo18), lock comum ao worker, nenhuma lease/publicação; uma aquisição de vídeo prepara três WAVs 16kHz e os mesmos bytes são reutilizados entre configurações. Comparações baseline/beam10/fallback/contexto0/no-speech0,8 são candidatas, sem vencedor. CLI exige cgroup finito CPU≤300%, memória≤12GiB e tasks≤128 além dos gates normais. Sete testes sintéticos passaram; ainda não executado com áudio real. Ruling: extrair três WAVs em uma aquisição reduz downloads redundantes; extração não implica que as três janelas foram inferidas. Custo: aproximadamente 29MB temporários privados por aula.

Suíte FO+MCP após runner: 375 passed. Suíte raiz reexecutada: 259 passed, quatro skips por falta de anki.collection, duas deprecações jsonschema.RefResolver e uma falha preexistente fora do escopo: `apps/anki-gpt/tests/test_regressions.py::test_background_queue_mutation_publishes_snapshot_and_media_before_releasing`. Não alterada. PIDs Anki API998234/MCP998235/sync998212 preservados após restart da API FO.

## E. Próxima etapa e classificação

- Concluído e validado: acesso VPS, branch e limites, integridade de pesos/runtime, gates fechados iniciais.
- Implementado, aguardando validação real: pipeline histórico.
- Parcialmente concluído: preflight e inventário.
- Bloqueado por dependência externa: gold humano e segundo anotador não disponíveis; não fabricar métricas.
- Não iniciado: comparações reais, homologação final e publicação; piloto em execução, não concluído.

Próxima ação: acompanhar primeiro checkpoint real sem concorrência de modelos, inspecionar raw e tempos e preparar comparações limitadas. Consolidar achados PDF/operação e revisão independente. Nenhuma decisão desta missão autoriza ativação integral futura.

## Marco integrado — 28/10/2026 04:07 UTC

- Os três findings ASR das revisões independentes foram tratados no commit `c5b72d9`: diagnóstico best-effort não prende lease; checkpoint schema 2 cobre logs/timings no checksum e validação; saída parcial/malformada ou ausência de JSON preserva evidência disponível antes da limpeza. Regressões em `test_worker_failure_evidence.py`; notificação tardia referente ao diff anterior não indica regressão nova. O processo do piloto já estava carregado antes dessas correções; não foi reiniciado para evitar repetir inferência e a presença do commit local não é prova de deploy.
- Piloto continua ativo, um decoder, ainda sem checkpoint concluído. Última telemetria: pico cgroup **4.680.544.256 bytes**, CPU acumulada **4.314,59 s**, livres **14.409.863.168 bytes**. CPU acumulada não é wall time nem RTF. Não há resultado/qualidade/segmentos finais a anunciar.
- Reclassificação PDF v4 finalizada: **143.265 páginas** na política atual, **667 bloqueadas** (511 OCR + 156 privacidade), **122 bloqueios adicionais** sobre o snapshot inicial. Nenhum OCR promovido; originais intactos. Ver relatório PDF para limites acadêmicos.
- Validação direta MCP ampliada: **27 páginas distintas**, 23 text_only/quatro blocked, 27 citações corretas com origem/versão, 22 respostas iguais à reextração sanitizada; busca positiva nas seis disciplinas. Quatro páginas inspecionadas visualmente pelo pai nesta rodada, incluindo três rasters adicionais. Fórmulas, índices e associação de colunas continuam apenas parcialmente avaliados, sem certificação acadêmica.
- Comparação OCR real em duas páginas, oito reconhecimentos/duas orientações, commit `b72b606`: nenhum benefício semântico demonstrado para troca global; nenhuma promoção, deploy ou mudança do extrator. Gold humano continua uma dependência real.
- Catálogo/status corrigidos no commit `4c55df5`, mas deploy aguarda revisão independente; confirmar retry sem falsos desaparecimentos antes de executar coleta real. Suíte integrada FO+MCP: **380 passed in 2.37s** no estado integrado. Mudanças Anki preexistentes continuam fora dos commits.
- Interface ChatGPT indisponível nesta sessão: headless bot-blocked e app nativo sem janela AX utilizável; teste de servidor não foi apresentado como teste do plugin instalado.

## Correção após revisão independente — política PDF v5

Reproduzidos **17 contraexemplos sintéticos (17 falhas antes)**: aliases/nome com cientista e fórmula, marcador literal global, nome multilinha parcialmente exposto, CPF ambíguo consumindo operadores e dois-pontos Unicode. Política 5 para de apagar campos nominais por regex; bloqueia inclusive marcador nominal legado, preserva números/operadores ambíguos e reconhece delimitador Unicode. Três testes antigos que exigiam liberação foram atualizados para o contrato mais restritivo; não se alegou que contexto textual prova identidade. **56 testes PDF/privacidade/OCR/ingestão passaram**. Suíte integrada durante trabalho concorrente: **400 passed, duas falhas** em comparações de benchmark cujo teste novo precedeu a assinatura de implementação; não foram falhas PDF nem se declarou suíte geral verde nesse instante.

Varredura v5 read-only das 143.265 páginas identificou **227 páginas adicionais** antes liberadas, todas com campo nominal e marcador legado. Não há prova de que todas perderam texto acadêmico; há prova de que o texto salvo não certifica redação completa/sem perda. Extratos afetados foram preservados privadamente em gzip (344.896 bytes, hash registrado no recibo privado), sem Git/OneDrive, antes de quarentena. Os 227 registros foram lidos de volta como bloqueados. Originais PDF intactos; conteúdo possivelmente removido por versões antigas requer reextração/validação, não reconstrução por IA.

Commit `97983a5` implantado: cinco arquivos verificados por SHA-256 e recibo lido de volta. Primeira unidade de migração v5 atingiu limite de 1GiB porque o script de auditoria retinha um snapshot integral do acervo em memória; quarentena e arquivo privado já estavam persistidos. Falha **oom-kill** registrada, sem imputar êxito. Retomada `study-hub-fo-privacy-v5-20261028-r2` usa apenas o migrador de produção em lotes de 250, CPU50%/1GiB/20min e lock do índice; snapshot posterior mostrou cerca de 110MB de pico e execução em andamento. API FO reiniciada com política 5; versões antigas permanecem fail-closed durante a migração. Não houve restart do piloto.

Runner de janelas **ainda não foi usado em áudio real**. Revisão encontrou timeout que pode deixar descendente fora do lock, QA absoluto inventando lacuna antes da janela, cache sem validar raw/log externos e comparações sem seleção informativa prévia. Correções com regressões estão em frente independente; não operar o runner anterior.

## Marco de recuperação e integridade PDF — após migração v5

Migração concluída: todas as 143.265 páginas em política 5; **894 bloqueadas (511 OCR + 383 privacidade)**, 142.371 com exposição textual. MCP revalidado em 27 páginas, mais três recém-quarentenadas; nenhuma destas três expõe texto. Evidência: `evidence/2026-10-28-fo-pdf-policy5-validation.json`.

Reextração estrita das 227 páginas em quarentena recuperou **40 páginas/36 materiais** privadamente e recusou **187 páginas/169 materiais** por divergência entre hash histórico e bytes atuais no mesmo caminho. Não substituir a identidade antiga pelo PDF atual. Há 419 caminhos com múltiplos hashes em 3.058 registros; investigação/proteção de versões originais está em frente independente. Recuperação não promoveu conteúdo nem escreveu SQLite/originais. Indisponibilidade no alias conhecido é uma pendência real; não demonstra ausência do original em todo o acervo/OneDrive nem autoriza fabricar texto.

Nova revisão operacional encontrou duas lacunas importantes em `4c55df5`: retomada pode esquecer falha não revisitada e publicação `error` pode degradar URL/duração/versão de aula válida. Correções com regressões estão em andamento; esse commit não foi implantado. Piloto real permanece limitado à aula única e passou a ter acompanhamento independente de métricas/QA até conclusão; nenhuma inferência extra foi iniciada.

Suíte raiz reexecutada: **259 passed, quatro skips, uma falha Anki preexistente** `apps/anki-gpt/tests/test_regressions.py::test_background_queue_mutation_publishes_snapshot_and_media_before_releasing` e duas deprecações. Mantida fora do escopo, sem alteração da coleção.

## Marco operacional — 05:06 UTC

- Dois P1 de catálogo receberam correções/regressões em `c149e64`. O filtro de erros transitórios na ingestão já foi implantado por SHA; collector/runtime aguardam nova revisão independente e não foram apresentados como validados em coleta real.
- Runner corrigido `6780816` e worker `c5b72d9` implantados por hash, sem reiniciar o piloto. Regressões VPS selecionadas: **29 passed**. Três WAVs de Biologia preparados a partir do vídeo já verificado, sem inferência adicional; preparação não conta como resultado de benchmark. Frente ASR autorizada a continuar sequencialmente após concluir o piloto, no máximo seis janelas distintas inicialmente e duas configurações extras em uma única janela informativa, dentro do teto original de 18 janelas, com orçamento adicional de seis horas. Sem gold ou publicação automática.
- `186438c` implantado com observação de fonte vinculada ao SHA esperado; API FO reiniciada. **13 testes VPS passaram** após completar as dependências de fixtures ausentes na primeira coleta. Respostas `fo_get_pdf_text` agora identificam `indexed_snapshot`, `source=null` e observação temporal sem garantia dos bytes atuais; não confundem caminho mutável com versão original.
- Revalidação completa e limitada: **3.245 identidades, 508 aliases físicos, nove lotes**, cada um com no máximo 512 IDs/64 caminhos. **430 verified**, **2.815 historical_source_unavailable**, observações persistidas e lidas de volta, 6,45 s de wall time. Zero escrita em PDFs, texto de páginas ou OneDrive nessa operação. Duas chamadas HTTP reais na porta descoberta da API confirmaram ambos os estados, identidade e ausência de link de original. Isso não constitui novo teste do cliente ChatGPT/MCP.
- Contagem atual de privacidade: **147.693 páginas**, todas política 5; **919 blocked** e **146.774 text_only**. O acervo mudou desde os snapshots anteriores porque produtores periódicos ainda estavam ativos. Para preservar originais durante homologação do produtor imutável `3ecd6cf`, foram pausados serviços catalog/materials/index/OCR e timers correspondentes mais OneDrive. Não confundir interrupção controlada desses serviços com sucesso de coleta; o piloto ASR segue independente. Retomar somente após revisão/deploy/verificação do contrato no-clobber.
- Snapshot Git congelado `186438c` exportado para diretório privado e testado sem alterações Anki/untracked: **433 testes FO+MCP passaram**. História pendente: 25 commits/104 blobs únicos verificados para extensão privada, credenciais literais, URLs assinadas e CPFs fora das fixtures sintéticas conhecidas; scanner conservador, não prova universal de ausência de segredos. Push não forçado da branch autorizado e SHA remoto `186438c` lido de volta (SHA completo na evidência JSON). Não houve merge em main nem push das alterações Anki não commitadas.

Evidência agregada: `evidence/2026-10-28-fo-pdf-source-status-live.json`. Homologação acadêmica, resultado final do piloto, comparações reais e cliente ChatGPT continuam pendentes.
