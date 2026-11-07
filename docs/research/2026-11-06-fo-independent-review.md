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
