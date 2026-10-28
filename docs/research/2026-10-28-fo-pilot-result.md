# Piloto FO — acompanhamento real de 28/10/2026

## Checkpoint durável — 04:34 UTC

Piloto preexistente `study-hub-fo-pilot-20261028-a2.service`, iniciado às 03:39:21 UTC, continua **active/running**. Este acompanhamento não iniciou inferência, não reiniciou o processo e não autoriza janelas adicionais. Uso observado: CPU acumulada 8.384,363735 s; pico cgroup 4.680.708.096 bytes. CPU acumulada não é tempo decorrido nem RTF.

Escopo: aguardar conclusão ou limite operacional de 18 h da unidade, manter revisão obrigatória, medir artefatos reais e verificar isolamento MCP/OneDrive e revogação após término. Processo carregado antes de `c5b72d9`; correções posteriores não podem ser atribuídas a esta execução.

## Progresso — 04:56 UTC

Primeiro chunk real concluído e persistido: 600 s de áudio, 3.207,294613 s de decodificação, 289 segmentos brutos. Checkpoint privado SHA-256 `b71762fd5848dd0aa6a9191bbf0d5b1f7faa1d0b60eaa94aedc1c9ac89951705`; schema 1 da execução antiga. Arquivo decoder-raw preservado separadamente. Às 04:39 UTC havia dois artefatos de evidência, 218.487 bytes, nenhum review/final público. Às 04:56 UTC piloto ainda active/running, CPU acumulada 11.701,107682 s e pico cgroup 4.715.765.760 bytes. Não confundir progresso parcial com conclusão.

Controlador ampliou escopo após piloto completo e seguro: no máximo seis janelas distintas (uma baseline por disciplina), orçamento benchmark de seis horas, até duas configurações extras na mesma única janela informativa. Nenhuma janela ASR foi iniciada neste acompanhamento. Runner revisado `6780816` e worker `c5b72d9` implantados pelo controlador; não mudam o código já carregado do piloto. Preparação privada de três WAVs reaproveita mídia corrente, duração ffprobe informada 2.817,724844 s; valor final será conferido no artefato.

## Progresso — 06:49 UTC

Piloto permanece ativo, sem reinício. Evidência privada acumulada: seis arquivos gzip, 699.902 bytes (checkpoints e raw separados). CPU acumulada 31.282,844248 s. Resultado final ainda não existe; inferências de benchmark continuam não iniciadas.

## Resultado real — encerrado às 07:12:23 UTC

Piloto terminou com exit status **0**, artefato em **review**, `qa.passed=false`; não houve aprovação nem publicação. Fonte efetiva 2.817,724844 s e 403.566.145 bytes. Artefato privado gzip 605.628 bytes, SHA-256 `b2c0334a7079044abe56c83af3cde69cc87c0a50707bc93c963177728e3f2961`. Métricas reproduzíveis em `2026-10-28-fo-pilot-metrics.json` (somente agregados).

- Wall interno total 12.780,000516 s; `/usr/bin/time` 3:33:02; soma decoding 12.748,949888 s. Diferença não-decoding 31,050629 s inclui download/hash/extração/silêncio/IO; **não existe medição isolada do download**.
- RTF total 4,535574; decoding/áudio fonte 4,524555 (denominador fonte única, inclui trabalho de overlap). Cinco chunks, nenhum reutilizado, offsets 0/598/1196/1794/2392 s; durações 600/600/600/600/425,724844 s.
- CPU user 35.170,70 s + system 100,33 s; maxRSS `/usr/bin/time` 4.197.176 KiB; pico **cgroup** observado 5.519.093.760 bytes. Medidas distintas, não intercambiáveis. Onze artefatos transcripts (cinco checkpoints, cinco raw, um review), 1.591.366 bytes.
- 1.396 segmentos, 10.585 tokens separados por whitespace (não tokenizer lexical). União temporal 2.632,58 s (93,4293% da fonte), 372 lacunas somando 185,144844 s, maior 8,4 s; excesso de overlap 7,46 s. Cobertura por timestamps do decoder, não evidência de cobertura acústica correta.

### Raw versus stitching

Concatenação ordenada dos segmentos dos cinco chunks é **exatamente igual** aos segmentos finais: mesmo texto, timestamps, 1.396 segmentos e 10.585 palavras whitespace. Portanto os padrões de repetição já estavam no decoder; stitching não os criou nem removeu. Preservou três fronteiras ambíguas (598–600, 1196–1198, 1794–1796 s). Uma regressão de início e cinco flags `non_monotonic` pós-stitching refletem definições diferentes (início versus envelope anterior); não são cinco regressões de início.

Flags de repetição em cada origem (decoder e stitched_text, **não somar como eventos independentes**): 114 segmentos duplicados, 42 candidatos ngram e dois candidatos token. Por chunk: 0 → 113 duplicados/12 ngram/um token; 1 → nenhum; 2 → 30 ngram; 3 → um token; 4 → um duplicado. Candidatos por minuto e métricas de cobertura relativas a cada chunk no JSON. Concentração estrutural forte nos minutos 7–9 e 24–29; não classificada como alucinação sem escuta/gold. Oito flags de texto em silêncio **medido automaticamente**, sem afirmar silêncio acústico humano; uma flag de revisão manual obrigatória.

### Barreiras verificadas após piloto — 07:16–07:18 UTC

Autorização temporária ausente, zero executáveis reais `whisper-cli`, geral inactive/disabled, configuração persistente false, sem timer de transcrição. Chamada MCP real: 26 ferramentas, `fo_get_transcript` retorna **fo_not_found/404** para o piloto. Primeira sonda teve erro local de atributo `inputSchema` na biblioteca instalada; repetida corretamente, sem alteração de serviço. Allowlist OneDrive calculada read-only em produção tem zero entradas e exclui o piloto; nenhum copy/upload foi solicitado. Isso verifica seleção local, **não uma varredura byte-a-byte do remoto**. Interface/modelo cliente não disponível e não foi apresentada como E2E.

Piloto completo permite seguir apenas o benchmark limitado autorizado; geral permanece desligado e gate será temporária por unidade. WER/CER, gold humano, classificação acústica de silêncio/música e precisão acadêmica não medidos. Nenhum texto acadêmico, URL de origem ou identificação pessoal pertence a este relatório.
