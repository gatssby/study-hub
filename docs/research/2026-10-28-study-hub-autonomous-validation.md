# Study Hub — missão autônoma de validação, 28/10/2026

## Andamento e autoridade

Em execução. A autorização desta missão cobre um piloto completo (`fo_21fd4985e207c5df`) e até 18 janelas reais de cinco minutos, com comparações adicionais nas janelas informativas. Não cobre fila integral, boot ou worker permanente. Documentos de 21/10 e 27/10 são históricos; a autorização explícita de 28/10 prevalece apenas neste escopo.

Snapshot inicial: 28/10/2026 03:26 UTC. Branch `feat/study-hub-migration`; alterações Anki preexistentes preservadas. VPS acessível. ASR geral inactive/disabled; autorização ausente; ambiente persistente `TRANSCRIPTION_ENABLED=false`. RAM disponível 20.138 MiB; disco livre aproximadamente 14 GiB. Pesos e executável SHA-256 correspondem à matriz; runtime commit `231638a0717b7822784297e5980965ffcec05810`.

Ruling: preservar revisão manual do primeiro piloto mesmo se QA automática passar — sucesso de execução não comprova qualidade acadêmica. O custo é adiar publicação/integracão positiva até revisão fundamentada; evita promover automaticamente resultado ainda não homologado.

Frentes independentes: pai opera ASR e QA; auditoria PDF e auditoria operacional/MCP delegadas com caminhos de relatório separados. Sem inferência no Mac.

## A. Whisper

Piloto: preparação em andamento. Nenhuma inferência desta missão registrada ainda. Gold humano, WER/CER, silêncio acusticamente comprovado e precisão de timestamps continuam não medidos.

## B. PDFs

Auditoria em andamento; resultados em `2026-10-28-fo-pdf-validation.md` quando produzidos. Originais preservados; dados pessoais não pertencem ao Git.

## C. Study Hub

Auditoria operacional em andamento; resultados em `2026-10-28-fo-operations-validation.md` quando produzidos. Não recriar Cronograma ou legado Anki.

## D. Infraestrutura

Commit inicial da missão ainda não criado. Deploys ainda não realizados. Serviço ASR geral permanece desativado. Toda autorização temporária deve ser revogada no encerramento das inferências; unidade transitória deverá executar revogação em ExecStopPost também em falha.

## E. Próxima etapa e classificação

- Concluído e validado: acesso VPS, branch e limites, integridade de pesos/runtime, gates fechados iniciais.
- Implementado, aguardando validação real: pipeline histórico.
- Parcialmente concluído: preflight e inventário.
- Bloqueado por dependência externa: gold humano e segundo anotador não disponíveis; não fabricar métricas.
- Não iniciado: piloto, comparações reais, homologação final e publicação.

Próxima ação: impedir publicação automática do piloto com opção explícita de revisão, testada; confirmar elegibilidade atual, implantar somente mudança commitada e iniciar unidade limitada. Nenhuma decisão desta missão autoriza ativação integral futura.
