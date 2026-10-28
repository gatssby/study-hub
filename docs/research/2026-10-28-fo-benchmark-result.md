# Benchmark FO limitado — 28/10/2026

## Resultado final — seis baselines medidas; extras interrompidas por incompatibilidade

Seis disciplinas, **seis janelas distintas de 300 s**, todas índice 1, concluídas sequencialmente. Sétima configuração tentou beam10 na mesma janela de Química e falhou antes de produzir transcrição: runtime aceita **no máximo oito decoders**, mas beam10 pede dez. Exit decoder 10, unit 1; gate revogada automaticamente e zero decoder. Não se substituiu beam10 por beam8 nem se recompilou/trocou runtime. **Fallback não iniciado**: encerramento conservador das comparações após falha real, sem reiniciar nem ampliar inferência. Sem vencedor e sem alegação de comparação pareada concluída.

Intervalo operacional medido: **07:20:21–09:07:34 UTC**, 6.433,019448 s de orçamento de 21.600 s; não excedeu seis horas. Soma decoding das seis baselines 5.197,109012 s para 1.800 s únicos de áudio (RTF agregado 2,887283), CPU user+system 15.309,15 s. Overhead operacional inclui preparação/download de cinco fontes, intervalos entre sondas e falha; não há timing isolado de download para inventar.

| Disciplina | Decoder wall s | RTF | Segmentos | Palavras whitespace | Cobertura temporal % | Candidatos QA |
|---|---:|---:|---:|---:|---:|---|
| Biologia I | 868,769 | 2,8959 | 70 | 658 | 92,14 | nenhum |
| Física I | 832,818 | 2,7761 | 39 | 770 | 98,51 | nenhum |
| Química I | 999,239 | 3,3308 | 168 | 877 | 85,00 | 4 duplicate_segment + 1 ngram |
| Matemática I | 824,288 | 2,7476 | 90 | 802 | 82,70 | nenhum |
| História I | 808,109 | 2,6937 | 50 | 608 | 94,89 | 1 ngram |
| Literatura Geral | 863,886 | 2,8796 | 63 | 631 | 80,54 | 4 token |

Cobertura, lacunas e excesso de overlap derivam de timestamps ASR, **não validam fala/silêncio acústico**. QA relativa à janela não inventa lacuna até o offset absoluto. Candidatos por minuto relativo e gaps/overlaps por janela estão em `2026-10-28-fo-benchmark-metrics.json`. Nenhum stitching entre chunks foi feito nesses windows únicos; portanto flags são do decoder. Não somar como evidências independentes as mesmas ocorrências observadas no piloto completo. Duração/contexto da janela diferem do chunk do piloto: resultado distinto não demonstra melhoria causal.

MaxRSS individual `/usr/bin/time`: 4.143.940–4.144.516 KiB nas seis baselines. Maior pico **cgroup amostrado** 4.288.942.080 bytes; amostragem de cinco minutos não garante máximo final. Na falha beam10, cgroup persistido mostrou apenas 2.097.152 bytes, enquanto `/usr/bin/time` mediu maxRSS 3.436.432 KiB; são contabilidades distintas e o valor cgroup não representa RAM total necessária ao carregamento. Artefatos privados de janelas: **55 arquivos, 177.614.807 bytes**, incluindo 18 WAVs preparados (somente seis inferidos), raw, logs, manifests e recibos; nenhum apagado. Recursos e falha preservados com hashes, sem conteúdo no Git.

### Comparações: evidência e limite real

A seleção exploratória foi feita **após as seis baselines**: Química, quatro segmentos duplicados e um ngram de 15 tokens/quatro ocorrências entre segundos relativos 273–286. Recibo privado vinculado ao baseline SHA, apenas beam10/fallback, `acoustic_reviewed=false`. Runner verificou baseline/raw/resource/audio/proveniência antes de tentar beam10. Falha privada SHA-256 `485ab6f00b7396e86d8416b2da97319f4116231e9125bab91c981b8645226e54`; resource log SHA-256 `23caa28bca1cf9adb00387b878dddd13fd6ee88dad5a7dd35dca641918fdc4ff`. Modelo carregou e áudio abriu; nenhuma saída de transcrição (stdout zero), sem artefato medido/recibo de sucesso beam10. Fallback, contexto zero, no-speech 0,8 e VAD ficam **não medidos**, não piores nem melhores.

### Barreiras finais verificadas

- Seis units baseline inactive/dead; beam10 failed/failed, MainPID 0, sem execução. Nenhuma unit reiniciada; falha retida para diagnóstico.
- Autorização root temporária ausente, geral inactive/disabled, persistente `TRANSCRIPTION_ENABLED=false`, nenhum timer de transcrição e **zero processos reais whisper-cli**.
- MCP direto real mantém 26 ferramentas; piloto review retorna **fo_not_found/404**. Nenhuma aprovação manual para forçar teste positivo. Interface/modelo cliente não testado.
- Allowlist de produção OneDrive zero entradas. Listagem remota read-only do diretório de transcrições teve exit 0 e **zero arquivos**, zero handles do piloto e zero caminhos review/private/evidence/windows. Nenhum upload/copy/publicação solicitado.
- Hashes de todos os seis artefatos, recibos, raw, resource logs e WAVs conferidos; fontes inalteradas. Somente agregados/handles/hashes nos dois arquivos deste benchmark.
- Teste local sintético de runner + OneDrive: **39 passed in 3.30s**. Não é qualidade acústica e não envolve nova inferência. Subset VPS de 29 testes foi informado pelo controlador, não reatribuído a este acompanhamento.

Problemas: primeira construção do comando remoto teve SyntaxError antes de qualquer criação de gate/unit; corrigida antes da primeira execução. Beam10 incompatível com limite compilado de oito decoders, sem tentativa de contornar. Nenhuma falha de OOM/disco/runtime-limit observada nas baselines; não usar isso como homologação do acervo.

Gold humano, WER/CER, termos, erro de timestamps, silêncio/música e julgamento acadêmico continuam **null/não medidos**. Revisão humana e eventual correção/validação de capacidade beam10 são pendências; qualquer retomada de ASR precisa respeitar autorização/escopo vigente. Sem fila integral, timer, boot, publicação ou mudança Anki.

---

## Checkpoints históricos (superados pelo resultado acima)

## Escopo e checkpoint inicial — 07:20 UTC

Piloto completo em review e isolado, commit `0c013fa`. Autorização do controlador cobre no máximo seis janelas distintas, uma baseline por disciplina congelada, preferindo índice 1; depois até beam10/fallback em uma única janela estruturalmente informativa, sem gold ou alegação de vencedor. Orçamento total seis horas desde a primeira unidade. Nenhuma aprovação/publicação/ativação geral.

Runner revisado `6780816`: SHA-256 local/remoto `4f9a39ab3194f63affacc8f1d5e71a80d4713c572bafd64f9a8d06d370d9edf0`. Seis fontes reconfirmadas presentes/elegíveis, versão 1/revisão 1. Disco livre 13.977.194.496 bytes. Nenhuma janela ASR iniciada até este checkpoint.

Cada unidade terá CPU 300%, memória 12 GiB, tasks 128, runtime 90 min, KillMode control-group, UMask 0077 e revogação root da autorização em ExecStopPost. Geral inactive/disabled e persistente false. Execução sequencial; nenhuma próxima unidade antes de inactive e zero decoder. Falha de criação revoga gate em finally. WAVs/evidências privados preservados. Medidas e resultado final pendentes.

## Seis baselines concluídas; seleção exploratória

6/6 disciplinas, todas no índice 1. Decorrido 6.001,24 s de 21.600 s antes das comparações. Escolhida **somente Química I, mesma janela**, por quatro segmentos duplicados e um candidato ngram de 15 tokens/quatro ocorrências entre segundos relativos 273–286. Critério estrutural observado, não escuta nem julgamento de erro científico. Recibo privado aceita apenas beam10 e fallback, `acoustic_reviewed=false`, vinculado ao baseline e SHA; seleção SHA-256 `d90421c045d649f0189b90f40b22f486fdea96135ccc6e9be8402daf79df4e20`. Nenhuma nova janela será aberta. Contexto zero/no-speech 0,8 e VAD não serão executados.

## Progresso durável — quatro baselines concluídas

Quatro janelas distintas medidas, todas com fonte inalterada, recibos/raw/resource/WAV SHA-256 conferidos; cada unidade terminou antes da próxima, autorização ausente e zero decoder entre unidades. Biologia 868,769356 s (RTF 2,895898), segunda disciplina 832,818431 s (2,776061), terceira 999,238954 s (3,330797; quatro flags duplicate_segment e um ngram), quarta 824,288104 s (2,747627). Quinta baseline em execução, sexta pendente. Decorrido do orçamento no checkpoint: 4.119,70 s de 21.600 s. Agregados duráveis no JSON; nenhuma aprovação/publicação. Sem gold, flags vazias não equivalem a transcrição correta.
