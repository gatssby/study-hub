# FO — diagnóstico de repetição e protocolo de aceitação, 28/10/2026

Este documento distingue hipóteses de mecanismo de defeitos efetivamente medidos. Não é laudo de qualidade do piloto ainda em execução. Nenhum texto de transcrição anterior foi reutilizado como referência humana.

## Matriz de atribuição

| Hipótese | Evidência necessária | Comportamento seguro implementado / limite |
|---|---|---|
| Decoder repete palavras/frases | Mesma sequência no JSON bruto, antes de stitching | QA por chunk preservada com origem decoder; candidato não significa alucinação confirmada |
| Stitching duplica ou modifica | Comparação dos segmentos brutos absolutos, decisões de fronteira e saída | Origem stitching separada; ambiguidades retidas; envelope temporal original, sem alinhamento de palavras inventado |
| Professor repete legitimamente | Escuta do trecho real; idealmente anotação independente | Texto nunca apagado por métrica; enumeração/hesitação repetitiva pode exigir review |
| Silêncio | Escuta humana e/ou observação acústica verificável com limites do detector | silencedetect é detector de energia, não gold; texto em intervalo detectado bloqueia e não é substituído por vazio |
| Música/ruído | Escuta e rótulo acústico manual | Texto isolado não distingue música de fala baixa; ausência de metadado não é confirmação de silêncio |
| Loop após falha | Logs do decoder, probabilidades/tokens e JSON bruto; confronto acústico | Saída parcial de erro/timeout preservada antes da limpeza; erro privado não entra no payload público |
| Fallback de temperatura | Mesmos bytes de WAV, mudança só de configuração e logs de fallback | Baseline off; candidato on preserva seus resultados, sem assumir que fallback melhora |
| Contexto anterior | Mesmo WAV, comparação contexto padrão versus max-context 0 | Novo candidato exploratório; processos independentes por chunk não compartilham estado entre processos, mas o decoder mantém contexto dentro de uma invocação |
| Timestamps/offset | Marcos acústicos anotados no vídeo original e offsets em ms | Parse ms→s testado, raw e tempos absolutos mantidos; falta revisão de âncoras humanas para medir precisão |

## Semântica verificada no runtime instalado

Fonte primária local: `/home/ubuntu/study-hub-models/whisper.cpp`, commit `231638a0717b7822784297e5980965ffcec05810`; leitura de `src/whisper.cpp` e `examples/cli/cli.cpp` na VPS e confronto com upstream fixado no mesmo commit em 28/10.

- `-nf` zera o incremento de temperatura; não desativa todos os testes internos de falha do decoder.
- O agendamento com incremento 0,2 percorre temperaturas até aproximadamente 1; os resultados continuam sujeitos aos testes de qualidade internos.
- `-mc -1` mantém o limite padrão. `-mc 0` impede condicionamento pelo histórico textual no laço consultado; não é uma correção já homologada em PT-BR.
- A condição de não-fala usa conjuntamente probabilidade no-speech e logprob; alterar apenas o limiar no-speech não equivale a um VAD validado.
- O limiar chamado entropy no whisper.cpp não deve ser apresentado como a mesma métrica de compression_ratio da implementação Python OpenAI.

A implementação Python oficial documenta que desabilitar condicionamento prévio pode ajudar a sair de ciclos de repetição, mas prejudicar consistência. Isso justifica comparação, não alteração automática do baseline. A transferência desse efeito para o runtime C++ precisa de medição real própria.

Fontes consultadas (apenas fontes primárias):

- https://raw.githubusercontent.com/ggml-org/whisper.cpp/231638a0717b7822784297e5980965ffcec05810/src/whisper.cpp
- https://raw.githubusercontent.com/ggml-org/whisper.cpp/231638a0717b7822784297e5980965ffcec05810/examples/cli/cli.cpp
- https://raw.githubusercontent.com/openai/whisper/main/whisper/transcribe.py (estado consultado em 28/10/2026, não versão instalada)
- https://rclone.org/commands/rclone_copyto/ (contrato geral; incompatibilidade com filtro de arquivo único foi reproduzida no rclone instalado, não inferida só desta página)

## Métricas e limites novos

`repetition_candidates` detecta corridas tandem contíguas de frases com 2–64 tokens e pelo menos três ocorrências; palavras isoladas exigem pelo menos cinco. Runs não atravessam lacunas superiores a 20 s. Texto, sinais, números e acentos não são reescritos. São candidatos a revisão acústica; o algoritmo não distingue professor de alucinação.

O numerador conta tokens em corridas disjuntas, sem dupla contagem de rotações da mesma corrida. O denominador usa a mesma tokenização científica. A métrica por minuto atribui tokens ao minuto de início do segmento original, explicitamente sem alegar timestamps de palavras. QA e métricas por chunk e por aula são armazenadas separadamente.

Testes sintéticos cobrem frases de dois e mais de oito tokens repetidas três vezes, loops longos, quebra entre segmentos/minutos e fronteira de 600 s, hesitações, enumerações, sinais/fórmulas gregas e fala interrompida. Teste textual de música/silêncio prova apenas que o texto não pode certificar a classe acústica. Integração acústica real ainda depende dos resultados e da revisão do piloto.

## Retranscrição focal e publicação

Spans de `focused_reviews` não são aprovações. A missão prepara comparações privadas de janelas de cinco minutos, incluindo candidato sem contexto; esse mecanismo pode investigar trechos suspeitos contidos nas janelas, mas não implementa substituição automática de spans de uma transcrição nem aprovação humana assistida. Não afirmar retranscrição focal produtiva concluída.

O primeiro piloto usa `FO_ASR_REVIEW_ONLY=true`: mesmo zero flags de conteúdo não o publica. Publicação positiva no SQLite/API/MCP/OneDrive permanece pendente enquanto não existir conteúdo realmente aprovado. Testes negativos (review indisponível) são relevantes, mas não substituem essa integração positiva.

## Revisão independente e correções

Dois revisores independentes reproduziram problemas com fixtures sintéticas. Corrigidos com cinco regressões inicialmente vermelhas e depois verdes:

1. Falha ao escrever diagnóstico podia manter job leased. Persistência auxiliar agora é best-effort e informa somente a classe sanitizada da falha, sem impedir retry da fila.
2. JSON parcial em exit não zero/timeout era apagado pela limpeza do diretório. Agora é arquivado enquanto o temporário ainda existe; sucesso sem JSON preserva stdout/stderr e ausência explícita de raw.
3. Checkpoint antigo não autenticava logs/timings. Novos checkpoints schema 2 incluem diagnósticos, comando e timestamp no checksum e validam tipos/tempo finito não negativo. Schema 1 continua permitindo reúso do raw verificado, mas seus diagnósticos não são promovidos como evidência autenticada.

A execução real do piloto iniciada antes dessa revisão continua usando o processo original; não foi reiniciada para fabricar um piloto sem retry. Seu resultado deve registrar exatamente essa versão de execução e suas limitações.
