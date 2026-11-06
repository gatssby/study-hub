# Reconciliação FO — 06/11/2026

## Resultado e limites

Snapshot SQLite **read-only** e metadados persistidos observados em **2026-11-06 23:01:27 UTC**: **3.213 registros, 3.079 presentes, 134 ausentes**, mantendo a baseline fornecida. O JSON irmão contém individualmente os **134 ausentes**, seus substitutos candidatos, os **13 sources pendentes**, as **34 falhas históricas únicas** e os **65 registros não-vídeo**. Não há URLs, caminhos remotos legíveis, credenciais, cookies, nomes de alunos ou mídia nesse artefato. IDs de curso que originalmente eram URLs foram pseudonimizados explicitamente como `url-sha256:<handle>`; os demais identificadores foram preservados.

**Não houve deploy, commit, push, alteração de DB/services, execução de worker/ASR, download de original ou operação OneDrive.** A execução remota do módulo ocorreu por stdin, sem instalar arquivos no servidor. A auditoria acessou somente SQLite `mode=ro`, JSONs existentes e páginas do portal com sessões existentes; não persistiu/renovou sessões.

**Bloqueio remanescente:** não é possível confirmar que Simuladão #02/#03 realmente não têm aulas. As duas sessões persistidas redirecionam para autenticação. O retorno HTTP 200 não autentica o usuário nem comprova catálogo vazio. A classificação é `empty_catalog_not_live_verified`, não “curso sem aulas”.

## 134 ausências: todas são identidades remotas aposentadas

| Curso da identidade remota | Ausentes | Classificação |
|---|---:|---|
| `remote:semiextensivo-ufpr-2026` | 106 | Alias remoto aposentado, substituto presente no mesmo caminho exato |
| `remote:Extensivo UFPR 2026` | 10 | Idem |
| `remote:base-intensivo-ufpr` | 8 | Idem |
| `remote:extensivo-ufpr-2026` | 5 | Idem |
| `remote:ciencias-basica` | 2 | Idem |
| `remote:matematica-basica` | 1 | Idem |
| `remote:materiais-exclusivos-medicina` | 1 | Idem |
| `remote:simulados-resolucao-de-provas` | 1 | Idem |
| **Total** | **134 = 106 + 28** | **Nenhuma ausência sem substituto por caminho exato** |

Para **134/134**, o objeto consta do inventário persistido e cada candidato presente possui source `available=1` com revision igual à versão atual. **125** aliases têm um candidato; **9** têm dois candidatos presentes. Não eleger um único “dono” nesses nove casos: a mesma fonte pode ser compartilhada por cursos distintos. O JSON conserva todos os candidatos por `lesson_id`, `media_id`, `item_id`, versão e handle de caminho.

Isso demonstra substituição das identidades provisórias e ausência de uma lacuna adicional nesses 134 registros. **Não prova bytes recém-verificados**, identidade acústica, equivalência de título, disponibilidade atual do stream ou sucesso de transcrição. Nenhum `present=1` deve ser forçado, e os aliases aposentados não devem voltar à fila.

## 13 sources pendentes: lacunas reais de aquisição/mapeamento, separadas dos aliases

Todos os 13 são vídeos presentes com job atual `queued`, source da versão atual indisponível e **sem caminho remoto mapeado**. Não são os 134 aliases. Nenhum possui match no upload manifest pelo URL canônico atual nem candidato já elegível pelo mesmo URL.

| Curso | Pendentes | Diagnóstico observado |
|---|---:|---|
| Extensivo UFPR 2026 | 3 | 2 sem URL; 1 `SourceDurationMismatch` |
| Intensivo UFPR 2026 | 5 | 5 `CalledProcessError` no estado do downloader; erro genérico não prova causa HTTP nem ausência remota |
| Simulados e Resolução de Provas | 4 | 2 sem URL; 2 `SourceDurationMismatch` |
| Semiextensivo UFPR 2026 | 1 | URL compartilhado com o pendente Extensivo `media_id=12478`; sem estado individual de download |
| **Total** | **13** | **4 sem URL + 9 com URL** |

Identidades que exigem recaptura autenticada de URL:

- `fo_985aa43ff95b238a` — Extensivo, `media_id=12837`.
- `fo_d7c2b39c34abedb8` — Extensivo, `media_id=12805`.
- `fo_5d66dfb4bf27853f` — Simulados, `media_id=10103`.
- `fo_e5cb97fa3eaf2d1a` — Simulados, `media_id=10102`.

Estado `SourceDurationMismatch`:

- `fo_fcad555740669e31` — Extensivo, `media_id=12478`.
- `fo_c02b9e2f9df56c60` — Simulados, `media_id=14423`.
- `fo_cf08fb1b5d45e70b` — Simulados, `media_id=4368`.
- `fo_626434837c181089` — Semiextensivo, `media_id=12478`, compartilha exatamente o URL canônico do primeiro; **não contar como um segundo stream independente**.

Estado `CalledProcessError` (Intensivo): `fo_4bafd25c15bf6598` / 16357, `fo_5c623b7dd096e89b` / 16367, `fo_6df4907c116802ed` / 16363, `fo_be0bb4362ced545d` / 16365 e `fo_c0b8df75e2eb86fe` / 16361.

O erro de duração registrado não autoriza remover o original, ajustar duração por conveniência ou repetir downloads ilimitadamente. A causa específica dos cinco erros de subprocesso continua não estabelecida por estes metadados. Revisar diagnóstico privado e autenticação/expiração antes de qualquer retry. Reutilização entre aliases exige prova de identidade da fonte/versão; igualdade de URL é indicação, não checksum de bytes.

## 34 falhas históricas de clique: 34/34 reobservadas como `ok`

Evidência histórica: `rebuild/g20261029a/catalog/courses/semiextensivo-ufpr-2026-0e9bcc74/aulas_index.json`. A comparação usa a identidade durável do collector **`source_ref + item_id`**, com fallback para `media_id` apenas quando não há `item_id`; não usa títulos nem `media_id` isolado entre ramos/cursos. As 34 identidades únicas constam como `ok` no catálogo atual do mesmo curso. O JSON lista cada uma com handle de ramo e IDs originais.

**Desfecho de clique resolvido não equivale a vídeo baixado/transcrito.** Não somar as 34 falhas aos 106 aliases nem tratar snapshots antigos de checkpoint/catalog como novas aulas. O catálogo atual do Semiextensivo tem **839 entradas: 838 `ok`, 1 `not_launched`**, sem erro de clique remanescente nesse artefato.

## Resíduos `error` e `not_launched` na DB

A DB ainda contém **57 registros `media_type=error` presentes**: **22 Extensivo + 35 Semiextensivo**. Cada um possui **outro vídeo presente no mesmo curso com o mesmo `item_id` exato**. São identidades de erro legadas com substituto conhecido, não 57 novas aulas faltantes. O JSON registra as 57 correspondências. O filtro de erros no ingest evita novas degradações, mas não remove retroativamente esses registros legados. **Não houve aposentadoria automática deles nesta tarefa.**

Há ainda **8 `not_launched` na DB**, sem substituto vídeo pelo mesmo item, e **2 observações `not_launched` nos catálogos atuais por curso** (1 Extensivo, 1 Semiextensivo). Contagens de observações e identidades DB não são intercambiáveis: a divergência **8/2** não comprova seis remoções nem identifica correspondências um-a-um entre as listas. Precisam de reobservação autenticada; não restaurar nem apagar por ausência em um percurso parcial.

## Cobertura dos catálogos publicados por curso

| Curso | Entradas | `ok` | `not_launched` |
|---|---:|---:|---:|
| Intensivo | 424 | 424 | 0 |
| Ciências Básica | 27 | 27 | 0 |
| Extensivo | 1070 | 1069 | 1 |
| Matemática Básica | 25 | 25 | 0 |
| Materiais exclusivos de medicina | 51 | 51 | 0 |
| Redação | 24 | 24 | 0 |
| Semiextensivo | 839 | 838 | 1 |
| Simuladão #01 | 2 | 2 | 0 |
| Simuladão #02 | 0 | 0 | 0 |
| Simuladão #03 | 0 | 0 | 0 |
| Simulados e Resolução de Provas | 422 | 422 | 0 |

Esses são números dos artefatos publicados, não uma nova coleta nem a cardinalidade deduplicada de aulas da DB. O JSON também fornece `coverage_by_db_course`, incluindo aliases remotos, tipos presentes e contagens DB. Um curso pode repetir a mesma mídia em múltiplas entradas; a DB ainda conserva identidades de catálogos históricos e erros legados.

### Verificação live dos Simuladões

- 22:56:28–22:56:34 UTC: #02 e #03, sessão `storage_state`, HTTP 200, `login_required=true`.
- 22:56:43–22:56:49 UTC: #02 e #03, sessão `catalog_storage_state`, HTTP 200, `login_required=true`.
- Bloqueadas requisições de mídia/imagem/font e extensões comuns de vídeo/PDF; sem login automático, salvamento de cookie ou download de original.
- Necessária nova autenticação pelo coordenador. Não extrair uma conclusão de “zero aulas” de uma tela de login.

## Correções locais demonstradas e testes

**Somente `portal/runtime.py` foi alterado entre módulos existentes**. `fo_hub/ingest.py` permaneceu intacto. Novo módulo `fo_hub/catalog_reconcile.py` é estritamente relatório read-only, sem ação apply e sem import de `FOStore`, worker ou downloader.

Bugs corrigidos no runner:

1. Uma coleta que retornava zero entradas era marcada `ok`, avançava `last_ok_at` e apagava checkpoint. Agora fica `incomplete`, retorna erro operacional/retry e preserva o timestamp anterior/checkpoint.
2. Uma coleta com `--limit` era marcada completa e perdia checkpoint. Agora também permanece `incomplete`, mesmo sem item `error`.
3. Uma observação vazia podia sobrescrever uma publicação não vazia. Agora preserva o JSON/TSV anterior e reporta a tentativa como incompleta, sem aposentar conteúdo.

Os dois testes parametrizados de completude falharam antes da alteração (`2 failed`, retorno antigo 0 em vez de 1). Após correção: testes de catálogo/ingest selecionados **39 passed**; suíte completa compartilhada **508 passed** (última execução: 5,83 s). Novos testes também cobrem publicação preservada, autenticação expirada na descoberta/curso, ausência de criação de DB, não alteração dos bytes SQLite, sanitização e deduplicação histórica por ramo/item. Os testes preexistentes de perda de URL/erro transitório preservam versão, source e jobs atuais. Tudo offline/sintético; nenhum teste fez ASR real.

## Comandos reproduzíveis e proposta de aplicação segura

### Auditoria agora, sem deploy e sem gravar no VPS

Do repositório local, enviar apenas código de relatório por stdin e salvar o resultado localmente:

```bash
ssh oracle-vps 'python3 - --state-root /home/ubuntu/study-hub-state/federal-online' \
  < federal-online/fo_hub/catalog_reconcile.py \
  > /Users/gatsby/.hermes/cache/scratch/fo-catalog-audit.json

TMPDIR=/Users/gatsby/.hermes/cache/scratch \
  services/anki-mcp-v2/.venv/bin/python -m pytest federal-online/tests -q
```

O comando é a implementação exercitada nesta tarefa. O JSON publicado inclui adicionalmente os recibos sanitizados das tentativas live de autenticação; eles não são gerados pelo módulo de DB.

### Collector autenticado — proposta para o coordenador, NÃO executada

Pré-condições: revisar o diff local; coordenador decide deployment separado; resolver autenticação com as credenciais já configuradas por mecanismo seguro sem expô-las; impedir que a publicação de catálogo dispare ingest concorrente antes de revisar os resultados. Não alterar serviços nesta tarefa. Não usar `--upload`, `--no-resume`, reconstrução/geração nova, reset ou coleta integral indiscriminada.

Após aprovação e código revisado no host, os comandos existentes do runner são:

```bash
cd /home/ubuntu/study-hub/federal-online
/home/ubuntu/study-hub-venv/bin/python portal/runtime.py catalog \
  --state-root /home/ubuntu/study-hub-state/federal-online \
  --env-file /home/ubuntu/.config/study-hub/federal_online.env \
  --mode incremental --course-filter 'Simuladão UFPR #02'
/home/ubuntu/study-hub-venv/bin/python portal/runtime.py catalog \
  --state-root /home/ubuntu/study-hub-state/federal-online \
  --env-file /home/ubuntu/.config/study-hub/federal_online.env \
  --mode incremental --course-filter 'Simuladão UFPR #03'
```

Esses comandos **escrevem catálogo, checkpoint e sessão** e portanto são proposta, não parte da auditoria read-only. O `--limit 1` pode ser usado somente como probe de autenticação/coleta de um curso conhecido; a correção garante que nunca será anunciado como completo. Uma nova execução com zero entradas deve permanecer `incomplete` até inspeção autenticada independente da árvore, seus ramos e eventuais avisos vazios. O runner não tem uma flag que certifique vazio intencional.

Para os 13 pendentes, coletar somente os cursos/itens selecionados, conservar checkpoints e revisar URLs/identidades/durações em evidência privada; o runner atual só oferece filtro de curso, **não filtro exato por lesson_id/item_id**, portanto não inventar uma opção de CLI para isso. Implementar um seletor exato validado antes de pedir retry automático por item, ou usar uma inspeção autenticada pontual com orçamento limitado, sem download integral.

### Aplicação lógica da reconciliação — gate proposto

1. Manter **os 134 aliases remotos `present=0`** e seus jobs aposentados. Não há restauração pendente desses IDs. Preservar os originais OneDrive.
2. Tratar o relatório como evidência temporal; antes de write, reler as versões/sources/paths exatos e comparar o fingerprint do inventário. Em caso de drift, regenerar somente o relatório read-only, não o acervo.
3. Para os **57 aliases de erro legados**, produzir um plano explícito de aposentadoria de identidade, condicionado a mesmo curso + mesmo item + substituto vídeo presente da versão corrente. Nunca apagar histórico/source/original e nunca identificar por título. Requer revisão do coordenador e teste transacional/idempotente antes de qualquer SQL apply; **este módulo não implementa nem executa esse apply**.
4. Os 8 `not_launched` continuam observações indisponíveis, não erros transitórios nem remoções provadas. Resolver apenas mediante observação autenticada do mesmo item.
5. Só promover source disponível após prova da fonte/objeto e revision correta. Nunca usar `UPDATE lessons SET present=1` como reparo, nunca mapear por similaridade de nomes e nunca superseder job atual por falha de coleta.
6. Reexecutar a auditoria e confirmar individualmente as 134 correspondências, os 13 estados, as 34 observações resolvidas, a preservação de jobs validados/review e a ausência de alterações em Anki. Só então considerar index/collector recorrente; ASR/deploy/services continuam fora deste escopo.

### Limitações metodológicas

O relatório obtém uma transação consistente para as tabelas SQLite, mas JSONs de produtores distintos não compartilham essa transação. O inventário é o snapshot persistido, não um `rclone lsjson` novo; nenhuma leitura de bytes OneDrive foi feita. A resolução de erro histórico compara os artefatos retidos e o catálogo atual, não uma nova reprodução de clique. Por essas razões o relatório distingue `ok` observado, identidade substituta, source elegível e vazio não autenticado, sem transformá-los em prova de conteúdo/acústica.
