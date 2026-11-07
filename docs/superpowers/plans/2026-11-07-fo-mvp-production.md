# Federal Online — execução MVP em produção (07/11/2026)

Spec vinculante: missão AFK do proprietário nesta sessão. Substitui gates históricos de perfeição, cobertura integral e gold humano; não substitui integridade, privacidade ou autorização VPS-only.

## Escopo e decisões

- Permanecer em feat/study-hub-migration e preservar dirty worktree alheio, Anki, n8n, originais e checkpoints.
- Recursos indisponíveis são backlog com motivo persistido e exclusão temporária; falhas sistêmicas continuam falhas.
- QA separa blockers e warnings, sem apagar texto ou fabricar alinhamentos. Unknown flags falham fechado. Gold/WER/CER ficam para aprimoramento, não lançamento.
- Homologação: reaproveitar cinco reviews; no máximo três aulas novas, disciplinas distintas. Um decoder ARM64 por vez. Large-v3, mc0, limites existentes.
- Ativar unit persistente e boot após homologação; provar job real, cursor, ausência de duplicação e restart com checkpoints. Não reconstruir acervo.

## Execução e interfaces

1. Revalidar git/VPS/evidências. Registrar baseline e saúde Anki.
2. Catálogo parcial: warnings por curso, sem perda de metadados; regressões dirigidas. Agente independente implementa somente catálogo.
3. QA proporcional, idioma focal e reavaliação sem nova inferência completa. Pai implementa QA/worker; agente focal usa somente um decoder antes dos pilotos.
4. Commit/deploy módulos verificados; lote real pequeno; ativação e restart do ASR persistente.
5. Materiais periódico: agente independente prepara caminho seguro; pai executa ciclo bounded e ativa somente se validado.
6. Suíte integrada uma vez ao final; smoke API/MCP e sincronização; revisão independente dos riscos concretos.
7. Roadmap/relatório/runbook; commits separados, push sem force e readback SHA.

Pre-flight: catálogo produz aulas/source que o worker consome; preservar versão/URL e excluir fontes indisponíveis, sem redefinir identidades. Materiais usa locks próprios e publicação OneDrive; não bloquear ASR pelo backlog OCR. QA pública deve manter allowlist existente e preservar evidências privadas.

Ruling: trabalhar no worktree existente indicado pelo proprietário, sem criar clone ou mover alterações — missão operacional incremental na branch autorizada; custo se errado: escopo de stage exige seleção explícita.
Ruling: executar testes direcionados por correção e suíte integrada única final, como solicitado, em vez de suítes completas por tarefa dos workflows genéricos — custo: regressões cruzadas descobertas no marco final.

## Ledger

- 07/11 04:54 UTC: git HEAD a3d6d05, branch correta, mudanças alheias preservadas. VPS cinco timers, ASR inactive/disabled; 12G livres, 21Gi RAM disponível. API ativa. Cinco reviews e QA artefatos baixados somente para scratch privado. Problemas de fronteira observados entre 0,2 e 2,0s; nenhuma remoção de texto proposta.
- QA v4: testes novos RED→GREEN; 66 testes dirigidos no primeiro commit 6da5a48. Sobreposições/fronteiras até 2,5 s, orçamento agregado de 1% da duração com piso de 5 s, repetições isoladas curtas como warnings. Timestamps inválidos, lacunas sem silêncio medido, loops, discrepância acústica, vazio e checks desconhecidos bloqueiam. Evidência acústica negativa de frases permanece bloqueante.
- Quatro reviews promovidas sem inferência: Bioquímica, Mito de Er, Física e Cartografia I. Arquivos originais review mantidos byte a byte; recibos privados qa-v4 vinculam SHA original. Readback SQLite/publicação confirmado. Espanhol permanece review.
- Catálogo f8ac1b4, vídeo be2d31c implantados por SHA. Smoke real #01 completo e #02 incomplete/empty_unverified: exit 0, last_attempt partial, 10 fresh_ok/1 warning, cooldown seis horas. Não houve varredura integral. Ingest real preservou SHA de identidades/versões/fontes/estados/tentativas (3311 aulas) em 07/11 05:11 UTC.
- Espanhol: dois decodes focais reais de 0–40 s (auto e es), um único decoder e limpeza observada. Auto detectou pt 0,839; comparação não resolve code-switch. 3aaa93f adiciona review por risco de configuração para Espanhol, sem atribuir idioma por disciplina; nenhum texto/timestamp reescrito.
- Revisão independente curta: nenhum blocker demonstrado; allowlist OneDrive seleciona público reavaliado e exclui gzip/private. Menor de status foi reproduzido RED→GREEN em 5fd8da3 (37 testes dirigidos).
- Ruling: corrigir o status de deferrals embora graduado menor — o proprietário exige estados/motivos persistidos e elegibilidade fiel, logo integra a entrega; custo: mudança aditiva pequena no contrato de status.
- 13 fontes históricas classificadas no SQLite com motivos (5 HLS404, 2 duração, 2 observação inconclusiva, 4 sem stream) e rechecagem 24 h. Confirmação atual é de ausência de fonte elegível, não novos probes HTTP. Nenhum ID/URL/job apagado; fonte descoberta muda identidade e volta automaticamente à seleção.
- 5fd8da3 publicado sem force e SHA remoto relido. Piloto novo História fo_1f3a74cb71e98be4 iniciado às 05:05 UTC, CPU300%/12GiB, fonte real; ainda sem resultado no checkpoint 05:11. Gate persistente/API continua false até homologação.
- Task materiais complete: 7b93b61, 13 testes dirigidos; deploy por SHA da unit principal e módulos. Dois ramos vazios não contaram como aceite PDF. Terceiro ciclo completo, 436 páginas / 32.590.808 bytes, v5/remote check/cleanup. Timer enable após aceite; catch-up automático executou quarto ciclo de 203 páginas / 5.703.103 bytes, cursor 4, sem original novo persistente. Seis timers ativos/enabled.
- Ruling: reutilizar a homologação real das quatro aulas reavaliadas e transferir o piloto de História depois do primeiro chunk durável para validar recuperação da unit permanente, em vez de aguardar e retranscrever outra aula inteira — reduz trabalho sem modificar fonte/raw nem QA; custo: interrupção consome tentativa e descarta apenas decode parcial sem checkpoint.
- Ruling: reconciliar apenas streak obsoleto de quatro reviews já aprovadas v4, exigindo zero falhas e breaker não aberto e approval das quatro IDs — não são mais quatro falhas graves consecutivas sob a política vigente; custo: mudança operacional auditada no contador, antes/depois preservados, nenhum reset global/técnico.
- Task ASR complete: gate transcription.env true, API por último EnvironmentFile dedicado (Environment=true isolado perdeu para runtime.env). Unit ativa/enabled 05:34:53; História completou 05:42:37, 121 segmentos/768,283867 s, QA sem flags, chunk reutilizado1/novo1 e SHA original intacto. Original remoto preservado. Próximo Inglês leased automaticamente.
- Restart controlado 05:43:41, removido por SHA somente override transitório; comando final loop normal, MainPID 3137550→3143673. Inglês voltou queued tentativa1; Literatura v2 leased, cursor ciclo5, um decoder/lease, zero duplicatas e nenhum resíduo do job concluído. Não se testou reboot do host.
- Task verificação complete: suíte final 690 passed in7.08s (FO+tests+MCP), 37/37 módulos SHA iguais e units conferidas. HTTP/MCP seis publicadas/uma review negada, OCR privado sem texto, 26 tools e Anki health/PIDs intactos. OneDrive seis JSONs verificados, SQLite quick_check ok; readback 05:49 UTC 11.06GiB livres/~17.12GiB RAM disponível.
- Revisão curta do delta 7b93b61: nenhum blocker demonstrado; menor conhecido de retenção de falha materiais/manual reconcile preservado. Limites de paginação/identidades de observação e renderer histórico documentados, sem alegar cobertura integral. Notion connected=false; não bloqueou operação.
- Entrega e evidências: docs/research/2026-11-07-fo-mvp-activation.md, -live-evidence.json, -module-hashes.json, ACTIVATION.md, roadmap e materials-cycle.md atualizados. Código 7b93b6176b89cd0680f30e3ccb35340d4c6e4b68 publicado/ref remota relida; complemento documental separado, sem autorreferência ao próprio SHA.
