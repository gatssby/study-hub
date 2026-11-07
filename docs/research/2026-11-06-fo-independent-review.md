# FO — revisão independente e disposição dos achados

## Escopo e evidência

- Revisão externa de código pelo Antigravity/Claude Sonnet 4.6, fonte completa selecionada e diff do collector até `186963f`, sem ferramentas, SSH ou mutações. Handle da execução Hermes: `proc_5c58d2c4c7d3` (exit 0). A primeira tentativa com ferramentas foi negada por permissão; **não** é contada como revisão concluída.
- Revisão final externa pelo Antigravity/Gemini 3.8 Flash High sobre o código `97e6396` e regressões dos dois últimos fixes, igualmente sem ferramentas ou mutações. Handle `proc_b535ba4ec526` (exit 0). Saída original: `/Users/gatsby/.hermes/cache/scratch/fo-final-independent-review.txt`.
- O coordenador verificou os achados por leitura do código e execução de regressões; severidades e sugestões do agente não foram aceitas automaticamente. Referências de linha emitidas pelos agentes são aproximadas; as funções e testes abaixo são os localizadores usados.

## Reparos demonstrados

1. **Publicação parcial eliminava metadados conhecidos.** `portal/runtime.py:run_catalog_course` podia substituir uma publicação boa por observações parciais não vazias, inclusive somente erros trazidos do checkpoint após coleta live vazia. Corrigido em `8f03ff0`: preservar entradas conhecidas com marca explícita `retained_previous_not_observed`; preservar erros/checkpoint/status operacional; não tratar os retidos como novas observações. Ingest e downloader ignoram retidos para não ressuscitar identidades ou baixar URLs antigas. Regressões: `test_catalog_completeness.py`, `test_catalog_staging_visibility.py`, `test_ingest_catalog_errors.py`.
2. **Propagação de transcrição por caminho/tamanho não provava os bytes da outra revisão.** O primeiro parecer tratou a limitação como não bloqueante; o coordenador reproduziu o problema com duas versões de bytes de mesmo tamanho no mesmo caminho. Corrigido em `97e6396`: remover conclusão automática dos aliases. Cada aula permanece queued até seu próprio download limitado e SHA256; apenas chunks de bytes/configuração comprovadamente iguais são reutilizados. Regressões provam duas transferências/um decode para bytes iguais e dois decodes para bytes diferentes, sem copiar review/aprovação para um alias ainda não verificado.
3. **Contenção de lock não deve gerar restart churn.** Unit passa a `RestartPreventExitStatus=3 4 5`; preserva start-limit, gate, breaker, cgroup e limites. `systemd-analyze verify` executado na VPS; readback confirma a propriedade. Serviço persistente continua inactive/disabled.

## Achados não aceitos como bloqueadores demonstrados

- Trocar `build.rmdir()` por exclusão recursiva com `ignore_errors=True` foi rejeitado: sobras desconhecidas devem falhar fechado, não ser apagadas para mascarar um erro. `write_outputs` promove os arquivos esperados e a falha de limpeza mantém checkpoint/status de erro.
- Segurar o lock de publicação durante todo download de materiais não resolve identidade/proveniência; o fluxo já separa staging e promoção. O writer legado continua **desabilitado**, sem alegação de substituição transitória homologada.
- Double-read de PDF e concorrência do writer legado permanecem motivo para **não reativar materials**. A amostra operacional usou originais OneDrive transitórios com verificação de bytes e não aprovou OCR/semântica.
- O parecer inicial fez afirmações incorretas sobre `flock` e reverteu outros próprios alertas. Elas não foram usadas como evidência de segurança ou para alterar locks funcionais.
- O guard de idempotência do ledger não faz nova aposentadoria; um ledger com mesmo digest comprova a aplicação histórica. Aplicação nova exige plano atual sob transação e `media_type='error'` no UPDATE.

## Resultado e limites

A revisão final Gemini declarou não haver bloqueador demonstrado **no código e dentro das fronteiras informadas**, após os reparos. Isso não certifica precisão acústica, deployment, conclusão do lote RR, pixels/semântica de PDFs ou ativação de produção. A suíte real após o último fix retornou **608 passed in 7.48s**. A decisão operacional continua dependente dos recibos reais do piloto e dos gates no relatório da missão.

## Terceira revisão delimitada — locator DLX (`41c501f`)

Antigravity/Sonnet concluiu nova revisão read-only, sem ferramentas, da função normalizadora fornecida e do contrato de aposentadoria descrito (`proc_0ece7932e261`, exit 0). Não foi uma auditoria nova de todos os arquivos em produção. Não encontrou bloqueador dentro desse escopo; pediu confirmar pureza/imports, estado mutável, proteção por aula e conjunto afetado/excluído.

Disposição do coordenador, com código, regressões e readback da VPS:

- Helper importa apenas parsing URL/regex da biblioteca padrão, sem cache/singleton mutável nem dependência circular em worker/ingest/downloader.
- Duas grafias de import podem produzir dois objetos de módulo. A sugestão de exigir identidade desses objetos não é gate necessário para função pura sem estado; imports reais no diretório da unit e comportamento equivalente são as verificações pertinentes. Nenhum resultado `is True` foi inventado.
- A proteção usa o ID da aula fallback, qualquer transcript ou job leased/done/review entre versões. Regressões sintéticas preservam cada caso protegido; caminho compartilhado não prova bytes nem permite copiar inferência.
- Reparo real: 100/100 fontes atuais conectadas e 98/98 fallbacks novos desprotegidos aposentados; nenhuma versão histórica reduzida. Os 13 pending IDs continuam iguais à baseline. Os 134 aliases antigos seguem ligados a candidatos atuais/disponíveis e objetos observados.
- Segundo ingest real idempotente; suíte completa com 620 testes aprovados; 36 módulos Python FO e unit ASR com SHA256 local/VPS idêntico.

Isso encerra as confirmações de código do escopo revisado, não qualidade de fala, gold acadêmico PDF, conclusão do catálogo global ou gate do ASR persistente.

## Revisão do orçamento de navegador após OOM real

O readback final encontrou `Result=oom-kill` no catálogo às 02:24 UTC, com 1.012 entradas duráveis e pico de 1,9 GiB no cgroup de 2 GiB. O limite não foi ampliado. `34f38bf` recicla o lifecycle completo do collector a cada 200 **novas entradas duráveis**, retomando o checkpoint; `a50cdb9` acumula a incerteza de travessia entre os lotes. Isso não promete um teto de 200 requests/tentativas nem mede leak específico do Chromium.

Nova revisão Antigravity/Sonnet, sem ferramentas/mutações, terminou exit 0; fonte selecionada, `load_checkpoint`, `collect_index` e testes foram fornecidos. Saída privada: `fo-browser-budget-review.txt` no scratch do coordenador. O parecer chegou a chamar de bloqueantes casos que em seguida demonstrou serem funcionalmente corretos; não foi aceito sem verificação:

- A sondagem adicional quando o total é múltiplo exato de 200 é **necessária**: atingir o limite não comprova fim do curso. Trocar `<` por `<=` publicaria um curso parcial como completo e foi rejeitado. Regressões agora cobrem total 400 e progresso zero.
- O mock é teste do orquestrador, não prova de navegador/portal real; ausência de tal prova não foi escondida. A retomada real usa o checkpoint validado e seu SHA permaneceu igual no deploy. O cenário fresh ignora intencionalmente seed anterior e retoma somente o novo checkpoint nos lotes seguintes.
- Aceito o risco de descartar erros de travessia intermediários: agora são preservados, sem duplicatas, até o retorno do curso; somente execução posterior pode resolver a incerteza. Regressão específica adicionada.
- Falha de lote posterior propaga exceção, não devolve sucesso parcial. O `finally` existente encerra contexto/browser/driver e o executor mantém o lifecycle fora do loop Playwright de descoberta.

Suíte completa após os ajustes: **628 passed in 7.27s**. O deploy não perdeu as 1.012 entradas, não mudou a frequência dos timers, o cgroup de 2 GiB, o gate ASR ou serviços Anki. Retomada e progresso são verificados separadamente no fechamento; isso não certifica execução global concluída nem ausência de OOM em qualquer carga futura.
