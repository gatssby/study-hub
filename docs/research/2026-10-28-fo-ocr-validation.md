# Validação conservadora de OCR FO — 2026-10-28

## Resultado e decisão

Comparação real limitada a **duas páginas bloqueadas**, sem promoção de DB, deploy ou alteração do extrator. O baseline permanece `pdftoppm -scale-to 1800` + Tesseract `por+eng --psm 11`, sem rotação automática. Não foi demonstrada correção acadêmica superior de outra configuração; alterar globalmente resolução, segmentação ou orientação seria prematuro. Não há ciclo RED→GREEN alegado nem regressão nova: nenhuma falha com gold suficiente motivou mudança de código. Os testes existentes não foram modificados ou enfraquecidos.

## Método e limites de recursos

- Seleção determinística via SQLite `mode=ro`: primeira página ordenada por material_id/página em cada classe `ocr_review` e `privacy_review`, ambas `exposure='blocked'`. A migração de privacidade concorrente pode mudar a população; o snapshot desta execução mostrou 511 `ocr_review` e 147 `privacy_review`, não os 34 históricos. Não se reivindica snapshot imutável entre observações.
- Originais abertos somente para leitura, com confinamento ao diretório privado de materiais. Nenhum job/qualidade/texto foi atualizado; o script não chama `process_pending`, não abre FOStore e não cria conexão gravável. Não houve re-OCR dos 511, áudio, inferência ASR ou alteração de gate/serviços persistentes.
- Unidade transitória `fo-ocr-audit-20261028`, usuário ubuntu, `CPUQuota=50%`, `MemoryMax=1G`, `TasksMax=16`, `RuntimeMaxSec=900`; subprocessos sequenciais, `OMP_THREAD_LIMIT=1`, `OMP_NUM_THREADS=1`, timeout 120 s por subprocesso. Uma página/um raster por vez, removido após uso; quatro renderizações, oito reconhecimentos e dois diagnósticos OSD. Nenhuma instalação.
- Execução terminou com código 0 em **1 min 40,578 s**, CPU **50,315 s**. Pico RSS de processos-filhos informado por `getrusage`: **129.896 KiB**; não é pico agregado de toda a árvore. A linha de memória do systemd-run não é usada como medida confiável da árvore. Unidade já coletada (`LoadState=not-found`); leitura posterior confirmou **zero PNGs retidos**.
- Evidência privada VPS: `/home/ubuntu/.cache/fo-ocr-validation-20261028/` (0700); arquivos 0600. Textos OCR, stderr e mapa de fontes permanecem ali, não em Git/API/OneDrive. Scripts privados: `/home/ubuntu/.cache/fo_ocr_probe_20261028.py` e `fo_ocr_geometry_20261028.py`; cópias no scratch local. O Git recebe apenas esta síntese agregada, sem texto reconhecido, identificadores pessoais ou caminhos de originais.

## Dependências e geometria verificadas

VPS: Tesseract **5.3.4**, Leptonica **1.82.0**, Poppler/pdftoppm **24.02.0**. `tesseract --list-langs` confirmou `eng`, `por` e **`osd`**; não se presumiu a presença do modelo de orientação.

As duas páginas têm MediaBox **595,32 × 841,92 pt**, UserUnit 1 e `/Rotate=0`. Raster 1800: **1273 × 1800 px** (~153,93 DPI pelo lado longo físico); raster 2600: **1839 × 2600 px** (~222,35 DPI). Portanto, o baseline é um limite em pixels, não 300 DPI. O experimento aumentou o limite de pixels, não aplicou `-r 300`, não mudou geometria ou pixels do original e não comprova resolução nativa de imagens embutidas.

## Resultados reais

Todos os oito reconhecimentos e ambos os OSD terminaram com exit 0. Tempos são de parede sob a quota, não benchmarks isolados de máquina.

| Handle / página / classe | Escala / PSM | Caracteres | Palavras | Tokens numéricos | OCR (s) |
|---|---|---:|---:|---:|---:|
| `e7b8811c6046cb9f` / 1 / ocr_review | 1800 / 11 (baseline) | 101 | 18 | 2 | 1,188 |
| mesmo | 1800 / 3 | 63 | 9 | 6 | 0,982 |
| mesmo | 1800 / 12 | 99 | 19 | 2 | 1,456 |
| mesmo | 2600 / 11 | 111 | 19 | 3 | 2,008 |
| `f9e2233d740142e8` / 28 / privacy_review | 1800 / 11 (baseline) | 6.309 | 989 | 16 | 13,727 |
| mesmo | 1800 / 3 | 6.237 | 985 | 16 | 15,663 |
| mesmo | 1800 / 12 | 6.305 | 989 | 16 | 14,823 |
| mesmo | 2600 / 11 | 6.312 | 993 | 17 | 15,607 |

Tokens numéricos são contados por regex `\d+(?:[.,]\d+)*`; não equivalem a números matematicamente corretos, CER ou preservação semântica. Todas as variantes produziram bytes distintos dentro de cada página. Mais caracteres/palavras ou números não demonstram melhora: podem refletir marca identificadora, fragmentação, alucinação de OCR ou associação incorreta. Tempos de renderização 1800/2600: **9,615/17,413 s** na capa; **1,692/2,781 s** na segunda página.

### Orientação

Na capa `e7b8811c6046cb9f`, OSD propôs **180°**, com confiança de orientação **0,17** (script 1,11). Na outra página propôs **0°**, confiança **13,23** (script 6,48). Não foi aplicado giro automático ou limiar inventado de confiança. A capa já havia sido inspecionada na auditoria PDF como predominantemente gráfica com marca diagonal; esta rodada não acrescentou inspeção visual. O resultado de baixa confiança é evidência de incerteza, não prova de que a capa esteja invertida ou de que OSD a corrija. PSM 12 não estabeleceu vantagem semântica sobre 11 nesta amostra.

## Testes e critérios antes de eventual mudança

Comando local executado: `services/anki-mcp-v2/.venv/bin/python -m pytest federal-online/tests/test_ocr_incremental.py federal-online/tests/test_pdf_identity_labels.py federal-online/tests/test_privacy*.py federal-online/tests/test_ingest*.py -q` → **39 passed in 0.19s**. Rodada isolada de `test_ocr_incremental.py` → **5 passed in 0.02s**. Não se reivindica suíte geral ou teste integrado com OCR real no CI: os testes incrementais usam extrator simulado; a comparação real acima é evidência operacional separada.

Antes de alterar `fo_hub/ocr.py`, exigir gold privado humano de orientação e conteúdo, incluindo ordem de colunas/células, sinais, índices/expoentes e fórmulas. Acrescentar então fixture exclusivamente sintética reproduzindo a falha pelo seam público `extract_page`, observar RED e implementar apenas a mudança causal; preservar limites e bloqueio de privacidade. Não transformar a capa e uma página de texto em justificativa para mudança global. A evidência estrutural em `2026-10-28-fo-pdf-validation.md` continua válida: OCR textual não certifica fórmulas rasterizadas, tabelas, pixels ou metadata como seguros. Os bloqueios não foram promovidos; nenhuma variante é homologada academicamente.
