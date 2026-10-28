# Study Hub — missão autônoma de validação, 28/10/2026

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
