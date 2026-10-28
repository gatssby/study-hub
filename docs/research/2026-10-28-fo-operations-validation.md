# FO — validação operacional read-only, 28/10/2026

## Escopo e validade

Observações na VPS `oracle-vps` em **28/10/2026, 03:27–03:31 UTC** (00:27–00:31 -03). Contagens são snapshots durante reconciliação, não cobertura final do portal. Branch local: `feat/study-hub-migration`.

Auditoria de catálogo, sincronização, fontes, indexação, status e integração MCP. Não foram alterados serviços, gates, configuração, banco de produção, Anki, PDFs ou módulos ASR. Não foram baixados vídeos, executados OCR/ASR ou iniciadas reconciliações. O piloto autorizado pertence ao coordenador e seu resultado posterior não está incluído neste snapshot.

Fontes primárias: leitura read-only de SQLite e manifests existentes, propriedades systemd, API FO loopback e chamadas MCP reais. O plano `docs/superpowers/plans/2026-10-21-study-hub.md`, o relatório de migração e `transcription/ACTIVATION.md` foram usados como histórico/contrato, não como prova do estado atual. Nenhum conteúdo pessoal, credencial, sessão ou URL de mídia foi incluído.

## Resultado executivo

- **Servidor funcional:** API FO ativa em 8780; MCP real em 8771 lista **26 ferramentas, 19 Anki + sete FO**. As sete FO foram chamadas, sem mutações; ausência de transcrição respondeu com erro estruturado esperado, não falha de transporte.
- **Reconciliação ainda incompleta:** catálogo tem 11 cursos, dez `ok` e um `error`; checkpoint ativo continua crescendo. Há oito erros de vídeo e 20 jobs queued sem source atual elegível.
- **Índice disponível, não integralmente liberado:** 3.147 materiais e 143.265 páginas; 545 bloqueadas por revisão. Zero materiais sem páginas e zero erros persistidos de ingestão nesta leitura.
- **Bug reproduzido offline:** curso com entrada `status=error` pode ser publicado como `status=ok`, retornar exit 0 e deixar de ser imediatamente elegível para retry. Não corrigido nesta auditoria.
- **Status insuficiente para operação global:** `last_sync` identifica uma chamada individual a `sync_lessons`, não o encerramento da reconciliação; erros de catálogo/vídeo/OneDrive e fontes pendentes não aparecem no endpoint.
- **Cliente ChatGPT não validado aqui:** inventário e chamadas diretas ao servidor não comprovam refresh, seleção ou execução pelo Plugin.

## Estado verificado

### Serviços e temporização

| Componente | Estado observado | Última conclusão / limite da evidência |
|---|---|---|
| API FO | `active/running`, resultado success | Ativa desde 27/10 19:03:59 UTC |
| Catálogo | `activating/start` | Processo iniciado em 28/10 02:22:39 UTC; não é conclusão success |
| Materiais | `inactive/dead`, resultado success | Conclusão 27/10 05:52:33 UTC |
| Vídeos | `inactive/dead`, resultado success | Conclusão 28/10 03:00:05 UTC; o manifesto contém oito erros de itens |
| Indexador | `inactive/dead`, resultado success | Conclusão 28/10 03:21:03 UTC |
| OneDrive | `activating/start` | Nova passagem em andamento; último status persistido é anterior |

Timers catálogo, materiais, vídeos, índice, OneDrive e OCR estão listados. `Result=success`/`ExecMainStatus=0` em serviço ainda `activating` não provam conclusão da passagem atual. Inativo é normal para oneshot que terminou, não sinônimo de indisponibilidade.

### Catálogo e materiais

`catalog/courses.json`: **11 cursos**, dez `ok`, um `error` (`semiextensivo-ufpr-2026-0e9bcc74`). O Semiextensivo conserva `last_ok_at=2026-10-27T14:29:46+00:00`, `last_run_at=2026-10-28T02:07:38+00:00` e erro presente. Seu `last_summary` é histórico, não resumo da tentativa falha atual.

Checkpoint correto é o de cada curso em `catalog/courses/<id>/checkpoint.json`:

- Extensivo: **478 entradas, todas ok**, checkpoint 28/10 03:31:04 UTC; reconciliação atual viva.
- Semiextensivo: **781 entradas: 779 ok, uma not_launched e uma error**, checkpoint 28/10 02:07:05 UTC. Não representa curso completo.
- `catalog/checkpoint.json` da raiz tem timestamp de **10/06/2026**, 819 entradas; é legado e não serve para medir o coletor atual.

O registro inclui cursos com `total=0` em sua última passagem. Isso, sozinho, não prova ausência de material/aulas nem erro: falta validar a expectativa específica do portal. Também não se deve somar resumos de cursos como vídeos físicos distintos.

Materiais: nove opções/cursos no registry; checkpoint `in_progress=false`, `done=[]`, atualizado na conclusão de 27/10 05:52:33 UTC. O array vazio é estado pós-conclusão, não prova de que nada foi processado. Registry de opções não certifica igualdade com o portal ao vivo; esta auditoria não abriu o portal nem disparou nova coleta.

### Fontes, inventários e fila

| Medida | Snapshot |
|---|---:|
| Aulas no banco | 3.213 |
| Aulas presentes / ausentes | 3.190 / 23 |
| Identidades remotas provisórias totais / presentes | 138 / 115 |
| Vídeos físicos em `remote-videos.json` | 2.252 |
| Bytes desses objetos | 337.698.996.081 |
| Linhas de vínculo lesson/source | 3.148 |
| Caminhos remotos distintos nesses vínculos | 2.252 |
| Vínculos `available=1` | 3.105 |
| Sources disponíveis com revisão diferente da aula | 0 |
| Jobs queued atuais sem source elegível | 20 |
| Jobs queued de aula `present=0` | 0 |
| Aulas presentes sem duração | 123 |
| Jobs queued / superseded | 3.140 / 185 |
| Transcrições validadas no snapshot | 0 |

Elegibilidade da contagem de 20: job queued na versão atual da aula, com source ausente/não disponível ou `revision != version`. Não interpretar todos os 3.140 queued como imediatamente processáveis, nem vínculos disponíveis como vídeos distintos.

`remote-videos.json` mtime **28/10 02:31:53 UTC**. O manifesto de vídeos, atualizado às 03:00:05 UTC, tem **1.821 existing_remote_verified, 1.176 verified, oito error**. São estados de registros lógicos, não 2.997 objetos físicos exclusivos. Erros: **três SourceDurationMismatch e cinco CalledProcessError**. Não foi inferida a causa dos cinco subprocessos a partir da classe genérica. Repetir download de fonte comprovadamente mais curta não demonstra recuperação.

Inventários históricos de migração/retirada permanecem presentes. Sua presença não revalida as exclusões históricas nem autoriza novas remoções.

### OneDrive e indexação

Último `onedrive-status.json`: mtime **28/10 02:31:53 UTC**, `pdf_sync=verified`, `transcript_sync=not_generated`; inventário tem prova SHA-256 e timestamp de início. O campo `updated_at` pertence ao início daquela passagem, não ao encerramento. A passagem das 03:25 estava em andamento: **não foi verificado nesta auditoria seu resultado nem feito novo byte check remoto**.

Índice concluído às **03:21:03 UTC**: 2.252 sources inventariadas, zero novas páginas, zero páginas reclassificadas e zero erros naquela execução. A tabela `ingestion_errors` também tinha zero linhas.

| Índice textual / privacidade | Páginas |
|---|---:|
| Total | 143.265 |
| `text` | 142.655 |
| `low_text` | 65 |
| `ocr_review` | 511 |
| `privacy_review` | 34 |
| Liberadas pela classificação do status | 142.720 |
| Bloqueadas | 545 |
| Sem revisão de política atual / política v2 / OCR pendente | 0 / 0 / 0 |

Todas as páginas tinham política v3 na leitura de produção. Essas contagens não são inspeção visual nem garantia de ausência de PII; o endpoint mantém guard de leitura adicional. Não houve varredura de texto/PII nesta auditoria. Nenhum original foi exposto ou alterado. **Zero OCR pendente não significa zero pendência: 511 páginas aguardam revisão após OCR.**

Espaço livre observado às 03:31 UTC: **14.928.240.640 bytes**, antes de eventual consumo do piloto. Não é estimativa de capacidade da fila ASR inteira.

## Integração MCP real

Cliente Python MCP executado na VPS com `/home/ubuntu/anki-vnext/mcp/.venv/bin/python`, transporte HTTP para loopback `http://127.0.0.1:8771/mcp`.

`tools/list`: 26 ferramentas, preservando 19 nomes Anki e exatamente sete FO; todas FO com `read_only_hint=true` e `destructive_hint=false`. Nenhuma ferramenta Anki foi chamada nesta auditoria.

| Ferramenta | Chamada e resultado real |
|---|---|
| `fo_list_lessons` | `limit=1`: um item, sem erro |
| `fo_get_lesson` | ID obtido da listagem: aula/revisões/citação, sem erro |
| `fo_search_materials` | `limit=1`: um item, sem erro |
| `fo_get_pdf_text` | ID obtido da busca, páginas 1–1: envelope de páginas, sem erro; conteúdo não impresso |
| `fo_search_transcripts` | Busca `biologia`, `limit=1`: lista vazia, sem erro |
| `fo_get_transcript` | Aula da listagem: `is_error=true`, `fo_not_found`, HTTP 404; esperado com zero transcrições validadas |
| `fo_get_sync_status` | Contagens/status existentes, sem erro |

Esta matriz testa leitura positiva de metadados/PDF e ausência segura de transcrição. **Não testa recuperação de transcrição validada real**, paginação exaustiva, carga, túnel externo ou execução pelo modelo ChatGPT. O primeiro comando com a venv FO falhou com `ModuleNotFoundError: mcp`; a venv correta do serviço MCP resolveu a inspeção, sem instalar dependências ou mudar produção.

Cliente e servidor são aceites separados: refresh da conexão ChatGPT, leitura de detalhes mostrando 26 ferramentas e execução em conversa nova precisam de evidência própria. Eventuais confirmações históricas em outro relatório não são reexecutadas por este teste.

## Defeitos e lacunas comprovados

### P1 — erro de item de catálogo promovido a sucesso de curso

Em `portal/runtime.py:188–261`, `run_catalog_course` conta `status_counts`, publica a saída e retorna; `catalog` marca `ok` sempre que não há exceção. `status=error` nas entradas não é convertido em falha/retry do curso. O validador de contrato aceita status não vazio; não exige que todas as entradas sejam bem-sucedidas.

Reprodução offline, usando saída TSV real e entrada sintética completa no contrato, sem monkeypatch do writer/validador, em diretório descartável no scratch:

```text
synthetic=true
rc=0
course_status=ok
status_counts={error: 1}
immediately_due=0
```

O probe afirma exatamente esses valores e passou, confirmando o defeito. Não foi alegado teste RED→GREEN: **não houve correção**. Como curso recém-ok fica fora de `courses_due`, falhas por item podem aguardar a janela normal de seis horas em vez de retry imediato. `not_launched` deve continuar distinto de erro. Aceite recomendado: teste que uma lista com item error preserve saída parcial/checkpoint, registre estado parcial/falho e fique elegível para retry, enquanto cursos seguintes continuam sendo processados. Sem deletar material prévio.

### P1 — status de sync não representa a reconciliação integral

Evidência simultânea:

- `ingestion_status.index` às **03:21:03 UTC** registra resumo de **2.433 unchanged** da sincronização inicial.
- `/fo/sync-status.last_sync` aponta para outro run às **03:20:59 UTC**, com **unchanged=1**.
- `fo_hub/ingest.py:227` chama `sync_lessons([row], authoritative=False)` para cada fallback remoto; `FOStore.sync_status()` escolhe simplesmente a última linha de `sync_runs`.

O endpoint não informa que esse último evento é de uma aula remota, nem expõe `ingestion_status`/resultado de catálogo/materiais/vídeos/OneDrive. Logo `last_sync` não é recibo de fim de passagem, nem saúde global, mesmo quando recente. Não é perda de dados demonstrada, mas um defeito semântico operacional observável também via MCP. Correção requer coordenação sobre `store.py`, que não foi editado.

Aceite recomendado: status por componente com início/fim, última tentativa versus último sucesso, resultado em andamento/falha, idade da fonte/inventário e contadores de sources pendentes; manter campos legados e testar o caso ingestão com vários fallbacks. Não converter `available=1` em prova de bytes recém-verificados.

### P2 — lacunas de observabilidade, não novas causas inventadas

- API/MCP omitem oito erros persistidos de vídeo, curso falho e 20 fontes pendentes; precisam de painel/diagnóstico paralelo ao contador queued.
- `CalledProcessError` sem contexto sanitizado não permite identificar causa dos cinco erros nesta leitura; consultar evidência privada sem exportar URLs/tokens.
- Courses com total zero e identidades provisórias precisam de classificação, não de remoção automática.
- Status `TRANSCRIPTION_ENABLED` reflete o ambiente do processo API, não autorização completa nem ambiente transitório do piloto; não usá-lo como detector único de inferência ativa.

## Testes e paridade

Comandos locais executados com `services/anki-mcp-v2/.venv/bin/python`:

1. Suíte focada MCP/API/runtime/catálogo/vídeos/ingestão: **64 passed**.
2. Primeira suíte completa durante alterações concorrentes de outro agente em privacidade: **286 passed, três failed** em OCR incremental. Não foi tratada como regressão estável: havia alterações concomitantes nesses arquivos, que não foram editados por esta auditoria.
3. Reexecução isolada OCR: **cinco passed**.
4. Reexecução completa com `TMPDIR=/Users/gatsby/.hermes/cache/scratch`: **289 passed em 2,18 s**.
5. Probe sintético do sucesso indevido de catálogo: confirmou os cinco valores acima. Teste de caracterização, não correção.

Hashes SHA-256 locais versus produção comparados para `store.py`, `mcp.py`, `api.py`, `ingest.py`, `portal/runtime.py`, `onedrive.py`: **seis iguais** no momento da comparação. Não é atestado de paridade de todos os módulos nem deploy das alterações concorrentes. Não foram executadas suítes Anki nesta auditoria.

## Roadmap factual restante

| Prioridade | Trabalho | Critério de conclusão |
|---|---|---|
| P1 | Tratar erros de entrada como curso parcial/falho | Regressão RED→GREEN, preservação de checkpoint/saída válida, retry sem aguardar seis horas; deploy somente pelo coordenador |
| P1 | Status por componente e source elegível | Não confundir último fallback com fim de ingestão; testes de passagem parcial, falha, stale e source ausente; compatibilidade API/MCP |
| P1 | Fechar Semiextensivo | Passagem concluída por curso, erros classificados e último sucesso atualizado; crescimento de checkpoint sozinho não fecha |
| P1 | Classificar oito erros de vídeo e 20 jobs sem source | Distinguir fonte indisponível/duração discrepante de falha recuperável; prova de revisão/bytes quando aplicável, sem redownload redundante |
| P1 | Verificar resultado OneDrive em andamento | Fim/resultado da passagem e recibo de verificação da geração exata; não reutilizar status anterior como conclusão nova |
| P1 | Aceite do piloto pelo coordenador | Recursos medidos e qualidade humana/benchmark; separado da saúde MCP e das fixtures sintéticas |
| P2 | Revisar 545 páginas bloqueadas | Aprovação visual/privacidade explícita, sem liberar OCR automaticamente nem expor originais |
| P2 | Validar Plugin ChatGPT | Ferramentas atualizadas na conexão correta e chamadas em conversa nova; evidência distinta do servidor |
| P2 | Reconciliar provisórias/total zero/material registry | Evidência de origem e descoberta completa; não excluir por ausência em coleta parcial |
| P2 | Atualizar checklist histórico | Marcar implementado/testado/implantado/aceito separadamente, sem usar caixas antigas abertas como prova de função ausente |
| P3 | Merge/retirada editorial remanescente | Revisão independente, classificação de arquivos e respeito ao dirty Anki; não necessário para API FO já ativa |

Este documento não executa nenhum item pendente nem autoriza ativação integral/boot ASR. Não houve mudança funcional ou deploy nesta auditoria; somente este relatório foi criado.

## Adendo — correção local posterior ao relatório `018c1ce` (28/10/2026)

As seções anteriores preservam o snapshot e os limites da auditoria original. Este adendo registra **implementação/testes locais, sem deploy**, não uma nova observação da VPS.

### Catálogo parcial: corrigido e exercitado offline

- RED: `tests/test_catalog_partial.py::test_item_error_preserves_publication_checkpoint_and_retries_only_failed_course` falhou no código anterior com `assert 0 == 1`, usando writer, TSV e validador reais, sem monkeypatch desses componentes.
- GREEN: `portal/runtime.py` agora publica a saída parcial válida, preserva o checkpoint byte a byte quando há `error`, persiste `last_summary` da tentativa, conserva `last_ok_at` anterior, marca o curso `error` e retorna 1. Continua os cursos seguintes; `not_launched` não provoca falha.
- A próxima passagem incremental seleciona imediatamente apenas o curso falho. A regressão simula recuperação com o loader real e verifica remoção do checkpoint e atualização de `last_ok_at` somente após sucesso.
- Segundo RED: o loader retomava também a entrada `error` e sua chave em `seen_keys`; preservar o checkpoint sozinho causaria retries que pulam o item falho. Ajuste mínimo em `portal/fo_collect_aulas_index.py::load_checkpoint`: exclui erros/chaves apenas da visão em memória, preservando sucessos e `not_launched`, sem modificar o arquivo durante a leitura. A segunda regressão passou após essa correção.
- Essas provas são sintéticas/offline; não demonstram recuperação do curso real nem conclusão da reconciliação na VPS.

### Status: extensão aditiva e limitada às evidências existentes

- `last_sync` e todos os campos legados mantêm a semântica anterior. Um teste realiza sync inicial seguido de fallback individual e verifica que `last_sync` continua identificando o fallback, separado da observação persistida do indexador.
- Novo `components.index`: `observed_at` da linha existente de `ingestion_status` e `summary` com allowlist de contadores inteiros não negativos. Não retorna payload aninhado `counts`, paths, mensagens privadas nem URLs. Ausência de tabela/evidência resulta em `components={}`; não cria tabelas em leitura.
- Novo `sources`: `current_queued`, `eligible`, `pending`. Considera apenas jobs queued da versão atual de aulas presentes; mapping elegível exige `available=1`, mesma revisão e caminho não nulo. Não transforma disponibilidade em prova de bytes recém-verificados. Sem tabela de sources, todos esses jobs são pendentes.
- Testes cobrem fonte ausente, indisponível, revisão obsoleta, caminho nulo, exclusão de aula ausente/job obsoleto/job failed, leitura read-only e resposta HTTP real do app local.
- **Ainda pendente:** status de catálogo/materiais/vídeos/OneDrive, início/fim/último sucesso por componente e política de staleness. O produtor atual não fornece esses eventos no SQLite; não foram inventados timestamps nem inferida saúde global a partir da observação do indexador.

### Execuções e limites

Com `TMPDIR=/Users/gatsby/.hermes/cache/scratch` e `services/anki-mcp-v2/.venv/bin/python -m pytest`:

1. Catálogo + runtime dinâmico: **19 passed**.
2. Status operacional: **3 passed** após RED por ausência de `components`/`sources`.
3. Suíte FO completa: **310 passed, quatro failed em 2,68 s**. As quatro falhas são `ModuleNotFoundError: fo_hub.window_benchmark` em `tests/test_window_benchmark.py`, arquivo untracked concorrente de ASR, fora desta correção. Não alterado.
4. Reexecução FO excluindo explicitamente apenas esse arquivo concorrente: **310 passed em 1,75 s**. Inclui API, MCP e integração existentes; não equivale a declarar a suíte integral verde.
5. `git diff --check` restrito aos três módulos de produção desta correção: sem erros. O check global encontra whitespace preexistente em alterações Anki, que não foram tocadas.
6. Foco final catálogo/status/runtime/API/MCP: **58 passed em 1,11 s**. Após o outro agente criar `fo_hub/window_benchmark.py` (untracked, não incluído neste commit), nova execução **integral FO: 314 passed em 1,76 s**. Esse resultado depende também do trabalho concorrente presente no workspace; as quatro falhas anteriores permanecem registradas acima como histórico real.

Arquivos funcionais: `portal/runtime.py`, `portal/fo_collect_aulas_index.py`, `fo_hub/store.py`; regressões novas: `tests/test_catalog_partial.py`, `tests/test_operational_status.py`. Nenhum módulo PDF/ASR, alteração Anki, serviço, gate, banco de produção ou VPS foi modificado. **Sem deploy ou push.**

## Adendo — dois P1 da revisão `4c55df5` corrigidos localmente (28/10/2026)

Este adendo substitui **a estratégia de descartar entradas error da memória** descrita acima; o snapshot de produção e as execuções históricas continuam válidos somente nos seus respectivos momentos. Nenhuma observação nova de produção foi feita.

### Pendências não revisitadas

- RED real: os dois testes de retomada, atualizados para exigir a retenção do item pendente, falharam com o loader anterior. Depois do ajuste no loader, o novo teste de checkpoint intermediário/runner retornando somente sucessos ainda falhou com `assert 0 == 1`: o runtime apagava o checkpoint e concluía o curso.
- GREEN: o loader conserva entradas `error`, mas não suas chaves em `seen_keys`, inclusive quando precisa reconstruir esse conjunto. Cada gravação intermediária preserva a pendência se seu ramo não for revisitado. Uma observação explícita da mesma chave substitui o erro, em vez de duplicá-lo, nos três caminhos de publicação do coletor.
- O runtime também reconcilia os erros pendentes do checkpoint com as observações retornadas pelo adapter antes de contar/publicar a passagem. Um retorno somente com sucessos não resolve itens omitidos. Curso continua `error`, imediatamente elegível para retry, sem novo `last_ok_at`; checkpoint e saída parcial conservam o erro. Uma resolução explícita permite concluir e remover o checkpoint normalmente.
- Regressões exercitam loader/writer/TSV/validador reais, checkpoint intermediário, preservação do último sucesso e substituição de erro no coletor sem duplicação, inclusive se a publicação seguinte falhar.

### Erro transitório não é revisão de mídia

- RED real, writer de catálogo e ingestão SQLite reais: após aula válida v1, publicar `error` com URL/duração nulas produzia v2 (`assert 2 == 1`). `authoritative=False` não protegia contra atualizar destrutivamente uma identidade presente.
- GREEN: `ingest` filtra somente `status=error` **antes** de selecionar candidatos e chamar `sync_lessons`. O erro continua observável no catálogo/checkpoint e retry; não é persistido como nova revisão de aula. Mesmo um erro mais recente em outro arquivo não ganha de um candidato válido, e uma identidade conhecida apenas por erro não cria aula inválida.
- A regressão comprova preservação de versão, URL, duração, tipo/presença, vínculo source (caminho/revisão/tamanho/disponibilidade) e job atual após erro. Um `ok` posterior com duração realmente alterada cria v2, invalida o vínculo antigo e mantém job da versão atual queued. Não afirma que jobs obsoletos sejam automaticamente marcados superseded em todos os caminhos.
- `not_launched` e `invalid_source` continuam sendo estados explícitos ingeridos; não são filtrados como erro transitório. Não foi alterada a semântica de remoção real do store, nem introduzida remoção por ausência em coleta parcial.

### Verificação e escopo do commit

Com `TMPDIR=/Users/gatsby/.hermes/cache/scratch` e `services/anki-mcp-v2/.venv/bin/python -m pytest`:

1. Foco `test_catalog_partial.py test_catalog_recovery.py test_dynamic_runtime.py test_ingest.py test_ingest_catalog_errors.py`: **33 passed em 0,10 s**.
2. Suíte integral `federal-online/tests -q`: **362 passed em 4,95 s**, no workspace compartilhado com outras frentes; não é prova isolada das mudanças concorrentes nem paridade com a VPS.
3. `git diff --check` limitado aos sete arquivos desta correção: sem erros.

Arquivos desta correção: `federal-online/portal/fo_collect_aulas_index.py`, `federal-online/portal/runtime.py`, `federal-online/fo_hub/ingest.py`, `federal-online/tests/test_catalog_partial.py`, `federal-online/tests/test_catalog_recovery.py`, novo `federal-online/tests/test_ingest_catalog_errors.py` e este relatório. Todas as fixtures são sintéticas. `store.py`, PDF/privacy, worker e window benchmark não foram alterados. **Sem VPS, deploy, push, ASR ou mutações de produção.**
