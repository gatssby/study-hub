# ASR PT-BR para aulas longas em CPU ARM64 — pesquisa e benchmark preparado (NÃO executado)

Data: 2026-10-21 · Status: **pesquisa + protocolo; inferência NÃO executada**. Posteriormente whisper.cpp e pesos large-v3 foram preparados na VPS por serviço separado, sem executar ASR. Não há resultados de qualidade.
Para executar o benchmark é preciso **nova autorização explícita**. Uma data futura (ex.: 22/10) não conta como autorização.

## 1. Restrições do alvo

- VPS aarch64, 4 vCPU, 23 GiB de RAM (~20 GiB livres), **9,3 GB livres em disco**, sem GPU.
- Conteúdo: aulas longas (1–3 h) em PT-BR, com vocabulário científico, silêncios e ruído de sala.
- Prioridade: **qualidade acima de velocidade**. A velocidade só desempata; não há teto eliminatório de RTF. Muitas horas de processamento por hora de aula são aceitáveis se RAM, disco, temperatura/carga e recuperação forem sustentáveis.

## 2. Candidatos (fatos verificados nas fontes primárias, consultadas em 21/10/2026)

| Modelo | PT? | Licença | Params / pesos (HF API) | Áudio longo | Timestamps | Caminho em CPU ARM64 |
|---|---|---|---|---|---|---|
| **Qwen3-ASR-1.7B** [1][2] | Sim: "Portuguese (pt)" na lista de 52 línguas/dialetos | Apache-2.0 | ~2,35 B params (safetensors); ~4,7 GB | Card: "support transcribe long audio"; `max_new_tokens` precisa ser aumentado para áudio longo | Via **Qwen3-ForcedAligner-0.6B**, que cobre pt, mas só em janelas de **até 5 min** | Exemplos oficiais usam CUDA/vLLM/FlashAttention. Existe suporte em `transformers` (`qwen3_asr`, `device_map="auto"`), mas **CPU ARM não é documentado**: risco alto de lentidão |
| Qwen3-ASR-0.6B [1] | Sim | Apache-2.0 | ~0,94 B; ~1,9 GB | idem | idem | idem, mais leve |
| **Whisper large-v3** [3] via **whisper.cpp** [4] | Sim (multilíngue) | Apache-2.0 (pesos) / MIT (whisper.cpp) | 1,55 B; `ggml-large-v3.bin` 3,1 GB; `q5_0` 1,08 GB [5] | Janela de 30 s com long-form sequencial ou em chunks. O card admite que o modo chunked pode custar até 0,5% de WER | Segmento e token (whisper.cpp) | **Melhor caminho documentado**: C/C++ com ARM NEON, quantização inteira e VAD embutido. Na tabela do README, o large exige ~3,9 GB de RAM |
| Whisper large-v3-turbo [5] | Sim | MIT/Apache | 0,81 B; ggml 1,6 GB, `q5_0` 0,57 GB | idem | idem | idem, mais rápido; em princípio menos preciso (a medir) |
| **Canary-1b-v2** [6] | Sim: pt entre 25 línguas europeias. O card reporta FLEURS pt WER 4,39% (**PT europeu e BR misturados no FLEURS, não é aula**) | CC-BY-4.0 | ~1 B | Chunking dinâmico com 1 s de overlap | Palavra e segmento (CTC auxiliar) | NeMo; o card lista apenas GPUs NVIDIA e "at least 6GB RAM". CPU ARM **sem documentação**. Card traz métrica de alucinação: 134,7 caracteres/min no MUSAN |
| Parakeet-tdt-0.6b-v3 [7] | pt listado (25 línguas europeias) | CC-BY-4.0 | 0,63 B | NeMo | Sim | Mesmo risco de NeMo em CPU ARM. Opcional |
| **VibeVoice-ASR** [8] | pt listado (>50 línguas) | MIT | ~8,7 B; ~17,4 GB | 60 min em passe único (64K tokens) + diarização + hotwords | Sim (quem/quando/o quê) | **Inviável no alvo**: 17 GB de pesos contra 9,3 GB livres em disco, e RAM bf16 no limite. Fica fora do benchmark local |

Limites desta pesquisa:
- Nenhum card traz WER em **PT-BR de aula**. Os números de FLEURS/Common Voice não se transferem para o nosso caso.
- Não verifiquei RTF em ARM de nenhum modelo.
- Os tamanhos são somas de arquivos no repositório HF. O repositório do whisper-large-v3 tem vários formatos, então 9,26 GB não equivale ao disco necessário.

## 3. Escolha provisória (depende do benchmark)

1. **Baseline e candidato padrão: whisper.cpp + large-v3 FP16**, `-l pt`. VAD permanece **desligado até comprovação de pesos, compatibilidade e funcionamento**; suporte no help não basta. Quantização q5_0 é comparação posterior, não baseline de maior precisão presumida. A estimativa do README é de ~3,9 GB para large, não um pico medido nesta VPS.
2. **Desafiante de qualidade: Qwen3-ASR-1.7B** (transformers, CPU fp32/bf16), opcionalmente com ForcedAligner em janelas ≤ 5 min. Substitui o baseline se vencer pelos critérios da seção 4.5 e operar sustentavelmente, mesmo muito mais lento.
3. **Desafiantes opcionais: Canary-1b-v2 e Parakeet v3** se o NeMo instalar em aarch64 sem GPU; large-v3-turbo pelo runtime whisper.cpp, sem depender de NeMo.
4. **Excluídos localmente: VibeVoice-ASR (disco/RAM) e APIs de nuvem** (fora do escopo).

Nenhum número de qualidade ou velocidade é afirmado aqui. A decisão final sai do benchmark.

## 4. Protocolo de benchmark (preparado; NÃO executar sem autorização)

### 4.1 Seleção estratificada
- O corpus de teste sai de **≥ 6 aulas** distintas, com **≥ 2 professores** e **≥ 2 disciplinas**. A gravação inclui o ruído típico do material.
- De cada aula entram **3 trechos de 5 min**: início (abertura e silêncio), meio (conteúdo denso com termos técnicos) e um trecho com fala sobreposta, perguntas de alunos ou ruído. Isso dá ≥ 90 min de gold.
- Entram também **≥ 2 trechos de 3 min com silêncio/música/ruído sem fala**, para testar alucinação.
- **≥ 1 aula inteira** (sem gold completo) serve para estabilidade de longa duração: deriva de timestamps, repetições em loop e cortes.
- A seleção sai de semente fixa (`seed`) sobre a lista de aulas. Registre o SHA-256 de cada arquivo de áudio.

### 4.2 Gold humano
- A transcrição é verbatim leve: sem hesitações "é…", mas com repetições significativas.
- A normalização é definida antes de rodar: minúsculas, pontuação removida, números por extenso **ou** dígitos (escolher um), siglas como faladas.
- Um segundo anotador revisa 20% do material. A concordância é medida como WER entre anotadores e deve ficar ≤ 3%; acima disso, revisar o guia.
- Uma **lista de termos científicos** é extraída do gold (glossário da disciplina) para a métrica específica.
- Timestamps do gold: marcação manual de início/fim de 1 frase a cada 30 s.

### 4.3 Métricas
- **WER e CER** (jiwer) sobre texto normalizado, por trecho e agregados. Reportar média ponderada por palavras e IC 95% via bootstrap por trecho.
- **Term-recall**: termos do glossário corretos ÷ ocorrências no gold. Reportar também a **WER restrita a termos**.
- **Alucinação**:
  - caracteres/min emitidos em trechos sem fala (mesma métrica do card do Canary);
  - taxa de n-gramas repetidos (loop ≥ 3 repetições de 4-grama);
  - inserções longas (≥ 5 palavras) sem correspondência no gold.
- **Timestamps**: erro absoluto mediano e p90 de início/fim nas frases marcadas, e deriva ao longo da aula inteira.
- **Recursos**: RTF, pico de RSS (`/usr/bin/time -v`), disco de pesos + runtime, e falhas/OOM.

### 4.4 Configurações fixas
- `language=pt` forçado, temperatura 0 e beam declarado. Whisper: `no_speech_threshold`/VAD on vs off são duas configs separadas. Qwen: `max_new_tokens` suficiente, chunking declarado.
- Para cada configuração, registrar o commit/versão do runtime, o hash dos pesos e as threads (3 na preparação de 27/10, preservando uma vCPU para serviços).
- Mesmo áudio de entrada para todos: 16 kHz mono WAV, gerado uma vez com comando ffmpeg registrado.

### 4.5 Critérios de decisão (qualidade acima de velocidade)
1. Eliminar a configuração que tiver OOM ou exceder o orçamento seguro de disco/RAM. Medir RTF, mas não eliminar por lentidão: o usuário priorizou precisão e aceita muitas horas por aula.
2. Ordenar por WER agregado. Diferença dentro do IC 95% conta como empate.
3. Desempate, nesta ordem: term-recall, alucinação em silêncio, erro de timestamp, CER, RAM e RTF.
4. Alucinação em silêncio > 2× o baseline exige revisão acústica humana e investigação antes da promoção; não apagar texto legítimo por heurística ou tratar razão isolada como prova.

### 4.6 Orçamento de disco (9,3 GB livres)
- Rodar um candidato por vez. Não apagar pesos ou arquivos existentes sem autorização específica; ampliar armazenamento ou adiar candidatos quando a reserva não comportar a comparação.
- Estimativas de pico:
  - whisper.cpp large-v3: f16 3,1 GB + q5_0 1,1 GB;
  - Qwen3-ASR-1.7B: 4,7 GB + Aligner + torch (~1–2 GB);
  - Canary: ~4 GB + NeMo.
- Corpus de 90 min em WAV 16 kHz: ≈ 170 MB.

### 4.7 Artefatos
- Resultados em JSON conforme `federal-online/transcription/benchmark.schema.json`, um registro por (modelo, config, trecho).

## 5. Fontes

### Preparação executável sem ASR

`PYTHONPATH=federal-online python -m fo_hub.benchmark plan lessons.json --seed 20261021 --count 6`
produz seleção determinística estratificada por disciplina e três janelas por aula, sem ler áudio.
O arquivo de produção `/home/ubuntu/study-hub-state/federal-online/benchmark-plan.json` contém seis aulas e `inference_executed=false`.
Confirmar professores distintos e escolher manualmente ruído/silêncio antes de colher o gold; as janelas automáticas não comprovam esses estratos.

`PYTHONPATH=federal-online python -m fo_hub.benchmark score gold.txt hypothesis.txt --duration-s 300`
calcula WER/CER por distância de edição e caracteres/minuto em gold vazio; não inicia modelo.
Atualização de 27/10: `score-batch` implementa agregação ponderada de WER/CER, IC95 bootstrap, termos por ocorrência, erros restritos ao glossário, alucinação em não fala, loops, inserções longas, timestamps e recursos fornecidos. Normalização v2 preserva acentos, números com sinal/decimais e operadores científicos; não mistura métricas anteriores. Detalhes, limites estatísticos, fixture sintética e contrato em `federal-online/transcription/benchmark-evaluation.md`. Recursos e hipóteses precisam ser medidos, não preenchidos por estimativa. Nenhum resultado real foi obtido.

## Atualização de preparação — 27/10/2026 (prevalece sobre estimativas históricas)

- Modelo local SHA-256 `64d182b440b98d5203c4f9bd541544d84c605196c4f7b845dfa11fb23594d1e2`, 3.095.033.483 bytes, igual ao objeto LFS publicado de `ggerganov/whisper.cpp/ggml-large-v3.bin`, consultado via API Hugging Face. Verificação não carrega o modelo para inferência.
- Runtime instalado `1.9.5-dev`, commit `231638a0717b7822784297e5980965ffcec05810`, CLI SHA-256 `61f809860bea4cef8a936049280e06006b849a87e7ae35e919e7703237db3c5c`. Help e código do commit confirmam os flags e o fallback 0→1 em passos de 0,2; `-nf` torna o incremento efetivo zero.
- Matriz de parâmetros preparados em `benchmark-matrix.json`: beam 5/fallback off como candidato inicial, fallback on e beam 10 como comparações isoladas. PT forçado, três threads, no-speech 0,6, entropy 2,4, logprob -1. É metadado de execução, não um runner automático. Não há superioridade medida de nenhuma configuração.
- A seleção antiga incluía Espanhol e não certificava professores/ruído. A nova `benchmark-selection-2026-10-27.json` seleciona metadados reais de seis aulas em Biologia, Física, Química, Matemática, História e Literatura, com revisões e 18 janelas propostas. Janelas propostas não são gold nem comprovação acústica dos estratos.
- Gold, pelo menos dois professores identificados, glossário, fala/ruído/música/silêncio anotados, amostras curtas, hashes de áudio e âncoras temporais continuam faltando. O checker deliberadamente reprova o manifesto vazio. Comparações de modelos e qualidade PT-BR permanecem pendentes de autorização + áudio real + trabalho humano.
- O nome `for-tests-silero-v6.2.0-ggml.bin` não identifica um dummy: a investigação confirmou **885.098 bytes e SHA-256 `2aa269b785eeb53a82983a20501ddf7c1d9c48e33ab63a41391ac6c9f7fb6987`**, iguais aos pesos oficiais v6.2.0 em `ggml-org/whisper-vad`. O runtime carregou o modelo VAD e executou **somente zeros sintéticos em memória**, sem carregar ASR ou abrir áudio real. Sucesso de carregamento/execução não homologa retenção de fala, ruído/música nem timestamps ASR+VAD. Baseline permanece VAD off; habilitação exige comparação real autorizada e validação do mapeamento temporal.
- Em 27/10 às 18:05 UTC havia 14.980.911.104 bytes livres e 22.749.376.512 bytes de RAM disponíveis. São observações anteriores ao deploy, não garantia de orçamento futuro. Reserva de 4 GiB, serviço de 12 GiB/300% CPU, gzip sem perda e um vídeo temporário por vez protegem a preparação; medir bytes/hora e RSS no piloto antes de afirmar que todo o corpus caberá.

O relatório final da preparação e do deploy está em `docs/research/2026-10-27-fo-transcription-preparation.md`. A precisão real não está homologada; não usar os resultados sintéticos como ranking de modelos.

### Referências primárias

1. https://huggingface.co/Qwen/Qwen3-ASR-1.7B (README: línguas, Apache-2.0, ForcedAligner 5 min / 11 línguas, exemplos CUDA/vLLM)
2. https://github.com/huggingface/transformers/blob/main/docs/source/en/model_doc/qwen3_asr.md
3. https://huggingface.co/openai/whisper-large-v3 (janela de 30 s, chunked vs sequencial, thresholds)
4. https://github.com/ggml-org/whisper.cpp (NEON, quantização, VAD, tabela de memória)
5. https://huggingface.co/ggerganov/whisper.cpp (tamanhos ggml via HF API)
6. https://huggingface.co/nvidia/canary-1b-v2 (25 línguas, FLEURS pt 4,39%, MUSAN 134,7 caracteres/min, 6 GB RAM, CC-BY-4.0)
7. https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3
8. https://huggingface.co/microsoft/VibeVoice-ASR (60 min, >50 línguas, MIT, ~8,7 B params)
