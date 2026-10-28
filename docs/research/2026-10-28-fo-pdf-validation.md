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
