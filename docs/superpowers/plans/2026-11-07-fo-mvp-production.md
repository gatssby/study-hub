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
