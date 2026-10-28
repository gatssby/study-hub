# Validação FO PDF — 2026-10-28

## Escopo e segurança

Auditoria read-only do SQLite de produção e leitura privada de PDFs originais; código candidato executado apenas em diretório privado de cache, **sem deploy**, sem alteração do banco, sem ASR e sem Anki. Originais preservados. Nenhum PDF, raster ou valor identificador integra o Git. Esta validação não aprova pixels/metadata dos PDFs para publicação.

Observação em 2026-10-28, UTC−03 (sessão iniciada às 00:27). Produção observada ainda usa política 3; o candidato local usa política 4.

## Contagens reais

Snapshot read-only: **3.147 registros em materials**, **143.265 páginas indexadas**. A contagem de materials não é apresentada como número de PDFs únicos auditados.

| Qualidade persistida | Exposição persistida | Política | Páginas |
|---|---|---:|---:|
| text | text_only | 3 | 142.655 |
| low_text | text_only | 3 | 65 |
| ocr_review | blocked | 3 | 511 |
| privacy_review | blocked | 3 | 34 |

Varredura streaming das 143.265 páginas com sanitizador candidato: **122 páginas antes text_only passam a blocked**. Classificação isolada do sanitizador: text 143.044, low_text 65, privacy_review 122, ocr_pending 34. Esses últimos números **não são previsão de publicação**: a migração existente preserva os bloqueios prévios privacy_review/ocr_review/ocr_empty; por exemplo, OCR já armazenado não deve ser liberado só por passar na classificação textual. Nenhum desses resultados foi gravado no banco de produção.

## Amostras reais e evidência visual privada

Seleção determinística: duas primeiras páginas ordenadas por material/página de cada qualidade text, ocr_review e privacy_review: **6 rasters de página**, máximo 1.200 pixels, renderização sequencial de uma página por vez. **3 rasters inspecionados visualmente** (um de cada classe); não houve alegação de revisão visual de todas as páginas.

| Handle privado | Origem | Extração pypdf crua (chars) | Texto candidato (chars) | Resultado |
|---|---|---:|---:|---|
| b971a07962a4aac9 | text, p. 1 | 6.331 | 6.243 | text / text_only |
| e7b8811c6046cb9f | ocr_review, p. 1 | 323 | 0 | ocr_pending / blocked |
| cf6674ae415c7d1b | privacy_review, p. 2 | 820 | 0 | privacy_review / blocked |

Inspeção visual: a primeira é uma questão discursiva legível com texto em coluna única e área de resposta; existe marca diagonal, sem permitir concluir segurança visual a partir da sanitização textual. A segunda é uma capa de simulado predominantemente gráfica com marca identificadora diagonal: o texto armazenado de OCR (100 caracteres) não prova remoção de PII visual. A terceira é uma tabela legível de tópicos matemáticos com marca diagonal; o bloqueio conservador continua adequado. Não se transcrevem os valores das marcas.

Outros handles renderizados, não inspecionados visualmente nesta execução: cd50fcb610d4fc6f, 006f02f7cd8b3de2, 9cc8a869f02e327e.

Evidências privadas fora do Git:
- VPS: `/home/ubuntu/.cache/fo-pdf-audit-20261028/` — rasters por handle, summary.json e candidato isolado.
- Local: `/Users/gatsby/.hermes/cache/scratch/fo-pdf-validation-20261028/` — seis PNGs privados, sujeitos à expiração do scratch.
- Script da coleta: `/Users/gatsby/.hermes/cache/scratch/fo_pdf_probe.py`.

## Correções e RED → GREEN

Falhas reproduzidas com identidades exclusivamente sintéticas: `Aluno:` sem CPF vazava; `Aluno:` com CPF redigido mantinha nome; CPF numérico inválido sem pontuação de rótulo era liberado; `Nome:` vazio consumia a linha seguinte por `\s`, permitindo liberação indevida. Primeiro run: **4 failed, 1 passed** em test_pdf_identity_labels.py.

Correção mínima: aliases de nome Aluno/Proprietário/Titular, espaços horizontais nos rótulos, bloqueio de campo nome vazio e CPF numérico residual sem delimitador. Política incrementada para 4 para invalidar aprovações anteriores; guard de serving existente reexecuta o sanitizador. Não foi necessário editar store.py, API ou MCP.

A troca de política revelou fixtures com política literal 3 em testes incrementais/OCR. As três falhas de OCR (`processed=0`, callback não chamado, errors=0) ocorriam porque a proteção privacy_review_pending corretamente recusava linhas antigas antes do OCR. Fixtures que representam a política atual agora usam PRIVACY_POLICY_VERSION; fixtures explicitamente antigas continuam antigas. Isso não enfraquece a proteção de produção.

Verificação local final: `services/anki-mcp-v2/.venv/bin/python -m pytest federal-online/tests -q` → **289 passed in 1.82s**. Inclui testes de OCR incremental, backoff sem PII, reserva de disco, confinamento de origem, preservação do bloqueio em upgrades e serving fail-closed.

## Limitações e entrega

Sem gold humano, sem métrica CER/WER de OCR, sem OCR real adicional: foram reaproveitados textos OCR já armazenados e reextraídas três páginas com pypdf. Esta rodada não mede qualidade de fórmulas/tabelas em todo o acervo e não valida original/metadata como artefato publicável. MCP servidor/cliente não foi exercitado nesta rodada; a cobertura local não equivale a E2E de plugin.

Antes de eventual deploy pelo agente pai: considerar a política 4 como invalidação fail-closed de toda a política 3 até revisão incremental. Espera-se bloqueio temporário de texto legado; preservar os 511 bloqueios OCR e demais bloqueios históricos. Nenhuma alteração de runtime de produção foi feita por este subagente.

## Aprofundamento acadêmico: geometria, objetos e ordem de leitura

Segunda rodada read-only em 2026-10-28: **23 páginas de 13 materiais**, seis grupos disciplinares. A seleção inicial tomou os dois primeiros material_id de cada grupo, páginas `min(2, total)` e `min(5, total)`, deduplicadas; somou-se a tabela matemática já identificada na rodada anterior. Resultaram Linguagens 2, Química 4, Biologia 4, Matemática 5, História 4 e Física 4 páginas. Não é amostra aleatória nem representativa de todo o acervo. **Nenhuma nova inspeção visual**: esta rodada amplia a análise estrutural, não as três revisões visuais anteriores.

Dependências verificadas no VPS: **pypdf 6.21.1**; fitz, pdfplumber e reportlab ausentes. Nenhuma instalação, OCR, rasterização ou ASR foi iniciada. A coleta usou `visitor_text`, matrizes `tm × cm`, ângulo, posição e tamanho das fontes, operadores de desenho e invocações `Do` com tipos `/Image` e `/Form`. Comparou ainda extração padrão, `extraction_mode='layout'` e layout com `layout_mode_strip_rotated=False`. Textos brutos, assinaturas de repetição e mapeamento handle→original permaneceram privados; o Git recebe somente contagens/handles no arquivo `evidence/2026-10-28-fo-pdf-geometry.json`.

### Resultados verificáveis — não são homologação semântica

| Handle | Disciplina / página | Evidência estrutural e consequência |
|---|---|---|
| `8577d1f4345caa67` | Matemática / 2 | 231 invocações de imagem; 229 no corpo, 216 pequenas. Texto padrão tem 5.764 caracteres não brancos. Uma camada textual extensa não demonstra completude de notação desenhada/raster. |
| `d8f04a9cf62a4a19` | Matemática / 5 | 108 invocações de imagem; 88 no corpo, 65 pequenas; 1.058 operações `l`/`re`. O multiconjunto de tokens numéricos muda no layout mesmo sem perda de caracteres não brancos. |
| `b97590e90e8454a5` | Física / 2 | 213 invocações de imagem; 211 no corpo, 192 pequenas. Não reconstruir sinais, expoentes ou unidades a partir de texto restante. |
| `100c1aae557663c7` | Física / 5 | 192 invocações de imagem; 178 no corpo, 123 pequenas. Tokens numéricos diferem entre padrão/layout; igualdade de contagem de caracteres não prova preservação acadêmica. |
| `f571f03396bf0527` | Química / 5 | Layout padrão perde 8 caracteres não brancos; preservar rotacionados recupera esses caracteres, mas não iguala o multiconjunto numérico. |
| `7495eb3b8cd26d88` | Química / 5 | Layout padrão perde 9 caracteres não brancos; flag de preservação de rotacionados recupera a contagem. Sem gold para declarar qual ordem é correta. |
| `6ca448e0a0036bdd` | Biologia / 5 | 834 operações de desenho; layout padrão perde 11 caracteres não brancos. Contagem de linhas não é detector confiável de tabela: desenhos e diagramas também as produzem. |
| `7204654e205250cb` | Física / 5 | Inclui `/Form`; layout perde 1 caractere não branco inclusive preservando rotacionados. Recursos aninhados impedem tratar callbacks como caixas de glifos confiáveis. |
| `cf6674ae415c7d1b` | Matemática / 2 | Tabela de tópicos vista na primeira rodada: 138 operações `l`/`re`, 726 caracteres não brancos. Layout muda a sequência; não há gold de células/mesclagens para aprovar conversão em tabela estruturada. Mantido bloqueio anterior. |

No conjunto: **815 invocações de imagem**, não 815 imagens únicas; 750 com origem entre 10% e 90% da altura da página, em 13 páginas. Destas invocações de corpo, 598 têm largura <150 pt e altura <30 pt. São **candidatos** a símbolos, fórmulas ou pequenos diagramas, não classificação semântica comprovada. `extract_text` não interpreta pixels; ausência de fórmula textual não autoriza inventar expressão. Os tipos são observações de recursos da página; atribuição de recursos dentro de Forms não foi resolvida recursivamente e pode estar incompleta.

Há callbacks horizontais iniciando dos dois lados em **17 das 22 páginas da seleção inicial** (ao menos dez inícios em cada faixa). Isso indica candidatos multicoluna, não comprova duas colunas: callback pode agregar múltiplas linhas, e a origem não fornece a largura do texto. Não houve salto horizontal reverso >30% da largura na mesma baseline (±3 pt) nas 23 páginas. Esse teste estreito **não prova ordem correta**. Não se aplicou ordenação global `(y,x)`, que poderia intercalar colunas, alternativas e células. Saltos verticais >30 pt aparecem em múltiplas páginas, mas também são compatíveis com transição normal entre colunas.

Uma mesma assinatura de texto rotacionado reaparece nas **23 páginas**; valores e hashes dessa assinatura não foram publicados. Repetição/geometria são sinais úteis para revisão de marca, não autorização para excluir texto rotacionado: uma fórmula, legenda ou rótulo também pode ser rotacionado/repetido. Esta rodada **não removeu objetos nem fragmentos adicionais**, nem derivou PDF visual supostamente seguro.

### Experimento de melhoria rejeitado conservadoramente

Trocar globalmente para layout **não foi aceito**. Em 22/23 páginas a sequência de caracteres sem espaços difere da extração padrão. Em quatro páginas há perda de caracteres (8, 9, 11 e 1), não apenas mudança de espaçamento. Preservar rotacionados reduz a perda a uma página, mas o multiconjunto de tokens numéricos ainda muda em quatro páginas: `f571f03396bf0527`, `d8f04a9cf62a4a19`, `100c1aae557663c7`, `7204654e205250cb`. O diagnóstico numérico é sensível a separação/concatenação e não prova erro acadêmico específico. Entretanto, basta para **rejeitar uma alegação de melhoria sem perda**. Igualdade de caracteres também não garante expoentes, índices, frações ou associação correta de células.

**Decisão:** nenhum defeito de ordenação do extrator atual foi demonstrado com gold suficiente para uma correção segura. A limitação de conteúdo não textual e o risco da troca para layout foram demonstrados; não se reconstruiu matemática, não se removeu marca por ângulo/repetição, não se alterou ingest.py/ocr.py ou banco. Não há nova correção de produção nem ciclo RED→GREEN alegado nesta rodada. O commit de evidência documenta a limitação em vez de introduzir heurística destrutiva.

### Entrega privada e reprodução

- VPS: `/home/ubuntu/.cache/fo-pdf-geometry-20261028/`, diretório 0700, arquivos de evidência 0600. `private.json` contém spans/texto e o mapeamento handle→material/página/original; `detail-private.json` acrescenta posições de objetos. Não enviar esses arquivos para logs, API, OneDrive ou Git.
- Scripts privados executados: `/home/ubuntu/.cache/fo_pdf_geometry_probe.py`, `fo_pdf_geometry_detail.py` e `fo_pdf_geometry_differential.py`; cópias locais no scratch com os mesmos nomes. Saída de warnings foi redirecionada a logs privados. Os scripts com conteúdo bruto são ferramentas de auditoria, não comandos de produção.
- Resumos sanitizados: `summary.json`, `detail-summary.json`, `differential-summary.json`; cópias locais `/Users/gatsby/.hermes/cache/scratch/fo-pdf-geometry-*-summary.json`. O arquivo de evidência versionado agrega esses três resumos com contagem/unicidade de handles verificadas programaticamente.
- Sem alteração de serviços, originais ou dados de produção. Não se afirmou que a produção permaneceu na mesma revisão enquanto outros agentes atuavam.

### Critérios para o pai: migração v4 versus qualidade acadêmica

1. **V4 é revisão de privacidade textual, não certificado acadêmico/visual.** A migração de texto salvo não recupera fórmulas que nunca foram extraídas; manter esse limite explícito em respostas e status.
2. Não servir linha legado/não revisada como atual só porque existe quality. Conferir versão atual, exposição permitida e guard de sanitização. Preservar bloqueios históricos `privacy_review`, `ocr_review`, `ocr_empty`, inclusive com OCR já salvo.
3. Não liberar `cf6674ae415c7d1b` ou qualquer original/derivado visual por passar regex, contagem, repetição ou análise de coordenadas. Pixels, metadata e anexos não foram homologados.
4. Para futuras mudanças de extração, usar estes handles como regressão privada e acrescentar gold humano de ordem por coluna, células, sinais, expoentes/índices, frações e unidades. Comparar por conteúdo e associação, não só chars/CER. Qualquer objeto sem interpretação inequívoca deve continuar explicitamente não validado, não reconstruído.
5. Separar aceitação da migração fail-closed do aceite acadêmico: reclassificar páginas não equivale a aprovar o significado. Não promover globalmente layout, OCR ou filtros geométricos com base nesta amostra.
6. Rerodar a suíte no SHA final do pai. Nesta árvore compartilhada, a rodada geral retornou **313 passed, 1 failed**: `test_window_benchmark.py::test_comparisons_reuse_exact_window_audio_and_never_publish_or_lease` esperava uma chamada ffmpeg e observou três, em arquivo ASR concorrente fora deste escopo. Não foi corrigido aqui. O subconjunto `test_pdf_identity_labels.py test_privacy*.py test_ocr*.py test_ingest*.py` retornou **39 passed in 0.19s**. Os 289 passes da primeira rodada permanecem evidência histórica daquele estado, não total atual.
