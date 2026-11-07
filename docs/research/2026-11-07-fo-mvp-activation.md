# Federal Online — MVP e ativação, 07/11/2026

## Autoridade e escopo

A decisão AFK desta missão substitui os gates históricos de cobertura integral e perfeição acadêmica do fechamento `a3d6d05`. Recursos inacessíveis e imperfeições toleráveis são backlog com evidência, não bloqueio global. Integridade, segurança, privacidade, fonte atual e QA grave continuam fail-closed. Não houve reconstrução de corpus, UI ou alteração de Anki/n8n.

**MVP operacional ativado.** Readback final em **2026-11-07T05:49:11 UTC**: serviço ASR active/enabled, gate ASR/API true, um decoder e uma lease, seis transcrições aprovadas e próxima disciplina em processamento. Systemd é independente do Hermes. Tempos em UTC.

Evidências públicas sem raw/URLs privadas: `2026-11-07-fo-mvp-live-evidence.json` e `2026-11-07-fo-mvp-module-hashes.json`. Artefatos completos permanecem privados na VPS; não se publicou conteúdo bruto de review nem credenciais.

## Implementação verificada

- `6da5a48`: QA v4, reavaliação de review íntegra e deferrals de fontes. Sobreposições/fronteiras <=2,5 s cada com orçamento agregado de 1% (piso 5 s), e até três pares de repetições curtas isoladas não sobrepostas, podem publicar com warnings. Defeitos substanciais/sistemáticos, loops, lacuna sem silêncio medido, texto em silêncio, vazio/incompletude e checks desconhecidos continuam review. Texto bruto e timestamps não são reescritos.
- Reavaliação preservou review original byte a byte e criou recibos privados `.qa-v4.json.gz` ligados a SHA. Foram publicadas Bioquímica/Biologia, Mito de Er/Filosofia, Unidades/Física e Cartografia I/Geografia. API/MCP confirmaram texto/citações/warnings. Soma com o validado anterior: cinco publicações nesse checkpoint.
- `3aaa93f`: Espanhol permanece review. Dois decodes focais adicionais reais (40 s, auto/es) não resolvem a mistura PT/ES: auto detectou PT p=0,839, e forçar ES não constitui gold. Nenhuma aula inteira retranscrita para comparar detalhes; nenhuma configuração global alterada por nome da disciplina. O risco da configuração PT para Espanhol é persistido como blocker, sem impedir outras matérias.
- `f8ac1b4`: indisponibilidade isolada do curso é warning persistido com cooldown seis horas, sem avançar last_ok_at. Smoke dirigido real #01 completo / #02 incomplete-empty_unverified terminou exit 0. Registro observado: dez fresh_ok e um warning. Não houve varredura integral redundante, nem vazio inventado para #02.
- `be2d31c`: vídeos continuam após indisponibilidade conhecida. Treze fontes históricas têm motivo e backoff de 24 h: cinco HLS404, duas durações incompatíveis, duas observações autenticadas inconclusivas e quatro sem stream capturado. Isso classifica evidência existente; não alegar novos probes HTTP nem recuperação dos 13. Novas fontes/revisões válidas voltam à seleção; falhas sistêmicas de auth continuam erros reais.
- `5fd8da3`: status passa a excluir deferrals da elegibilidade e expor motivos agregados. Ingest real preservou SHA de identidades, versões, fontes, estados e tentativas das 3.311 aulas.
- `7b93b61`: novo produtor periódico rediscover/rotation, no máximo um PDF aceito por invocação. Originais privados por SHA completo e copy imutável/check de bytes no OneDrive; extração saneada v5 e cursor após commit SQLite; cleanup somente de temporários próprios. Nenhum original novo permanente em materials/.

## Materiais e privacidade

A unit principal foi substituída pelo módulo novo, sem flock duplicado nem restart, CPU100%/2GiB/75min. Dois primeiros ciclos reais observaram ramos vazios e avançaram cursor sem upload; não foram contados como homologação do PDF. O terceiro adquiriu PDF real de 32.590.808 bytes / 436 páginas, verificou bytes remotos, saneou/indexou v5 (435 liberadas / uma bloqueada), gravou cursor 3 e limpou seus temporários. Nenhum original permanente novo na VPS.

Timer materiais habilitado após esse aceite. O catch-up Persistent executou autonomamente o quarto ciclo: 5.703.103 bytes / 203 páginas liberadas v5, check remoto, cursor 4 e cleanup. Dois novos materiais remotos-only, 174 materiais / 8.457 páginas totais; 7.912 text_only / 545 blocked, mantendo as 544 bloqueadas históricas. O calendário diário 04:45 UTC foi mantido; próximo evento observado 08/11. Não equivale a cobertura integral ou descoberta de todos os documentos em um dia.

Rotação usa valores de opções do portal e identidades de observação de linha (metadados + ordinal para duplicatas indistinguíveis), não promete IDs imutáveis do portal. Revisa bytes em novas passagens, preserva hashes/proveniência históricos, não infere remoção por ausência e não promete cobertura de paginação não observada. Falha deixa árvore privada e bloqueia novas aquisições até reconciliação, evitando repopular a VPS. Essa necessidade de recuperação manual é limitação conhecida, não escondida.

A política PDF v5 e as 544 páginas historicamente bloqueadas permanecem; mais uma página nova sem texto está ocr_pending/blocked. Nenhum desbloqueio por executar OCR ou trocar política ASR. Originais/pixels/metadata não são sanitizados; apenas texto permitido é servido. Staging e backup pré-catálogo antigos permanecem protegidos até reconciliação específica; não se alegou eliminar todos os originais locais históricos.

## Homologação / operação

História `fo_1f3a74cb71e98be4` iniciou em piloto às 05:05 UTC: large-v3, contexto 0, beam/best-of 5, temperatura 0, fallback/VAD off, CPU300%/12GiB. O primeiro chunk de 600 s ficou durável. O piloto foi encerrado com todo seu cgroup e a unit permanente iniciou às 05:34:53, com retomada explícita temporária seguida do loop normal.

Às **05:42:37**, a unit permanente concluiu esse job real: duração 768,283867 s, 121 segmentos, QA v4 aprovada sem flags, HTTP200 e MCP com citações. Um chunk foi reutilizado pelo SHA de vídeo/runtime, outro decodificado; checkpoint original manteve SHA `cafbd82d…a3f4`. A fonte original OneDrive continuou presente com tamanho conferido. Temporários do job concluído removidos. Não se alegou que todo seu áudio foi decodificado dentro do serviço: a retomada é parte da homologação.

O worker avançou automaticamente História → Inglês. Removi por SHA apenas o override temporário e executei restart controlado às **05:43:41**: MainPID 3137550 → 3143673, ExecStart final `python -m fo_hub.worker --run --loop`, active/enabled. Inglês interrompido voltou queued com a tentativa preservada; Literatura v2 recebeu a lease seguinte, cursor ciclo 5. Uma lease, um decoder e zero duplicatas (lesson_id,version). A retomada não obriga a disciplina interrompida a furar Round Robin.

O serviço está habilitado no boot com Restart=on-failure, KillMode=control-group, TimeoutStopSec=90, CPU300%, MemoryMax12GiB e TasksMax128. Boot está configurado; não houve reboot da VPS, preservando Anki/n8n. Breaker final fechado, zero falhas/reviews consecutivas. Um job novo completo e duas disciplinas iniciadas no exercício de continuidade/restart; não foram feitas três novas retranscrições completas.

Reconciliou-se **somente** a sequência obsoleta de quatro reviews conservadoras agora aprovadas v4: antes 0 falhas / 4 reviews / sem abertura; depois 0/0. O SQL exigiu esses valores exatos e aprovação das quatro identidades; recibo before/after preservado. Nenhum breaker aberto/técnico foi apagado nem reset periódico criado.

Gate true em transcription.env e na API relido via chave maiúscula `TRANSCRIPTION_ENABLED`. Um primeiro drop-in Environment=true não superou o false de runtime.env; corrigido com último EnvironmentFile dedicado transcription-gate.env, sem abrir gates dos coletores. Verificação da API passou após restart somente dela. Os PIDs Anki API/MCP/sync permaneceram 998234/998235/998212, anki_health ok; n8n não foi alterado.

Runbook atual: `federal-online/transcription/ACTIVATION.md`. Não reinstalar todas as units via renderer, que ainda contém configuração histórica do produtor de materiais; instalar apenas a unit revista. Um único worker, lock, fila versionada, três tentativas, checkpoint bruto, reserve 4GiB + fonte + 100MiB e circuit breaker continuam obrigatórios.

## Testes e revisão

Execução final integrada:

    PYTHONPATH=federal-online services/anki-mcp-v2/.venv/bin/python -m pytest federal-online/tests tests services/anki-mcp-v2/tests -q

Resultado real: **690 passed in 7.08s**. Antes dela, testes dirigidos RED→GREEN nos eixos QA, reassess, deferrals, catálogo e vídeo; 13 regressões do novo produtor passaram. Uma invocação de testes sem PYTHONPATH falhou na coleta com ModuleNotFoundError; corrigido o comando, não o produto. Primeiro deploy dos módulos de materiais passou, mas a cópia da unit ao espelho do repo falhou por diretório ausente; diretório criado, reexecução idempotente e SHA instalado relido.

Duas revisões independentes restritas aos riscos demonstrados: nenhuma encontrou blocker. A primeira reproduziu divergência de status dos deferrals, corrigida RED→GREEN. A segunda confirmou que ingest não elimina materiais novos remotos, sanitizer/serving continuam fail-closed e rclone local real é idempotente. Menor preservado: falhas de materiais exigem reconciliação manual; objeto enviado antes de falha de parsing pode ficar sem checkpoint final, com recibo/evidência retidos para recuperação. Não simular isso como sucesso de produção.

Smoke final API/MCP real após restart: **seis aprovadas HTTP200 e MCP com segmentos/citações**, Espanhol HTTP404/sem segmentos, OCR bloqueado sem texto, 26 ferramentas (sete FO/19 Anki), anki_health ok. Sincronização OneDrive posterior: unit exit0 e pdf_sync/transcript_sync verified, **seis JSONs aprovados**, 2.252 objetos de vídeo observados. Objetos físicos não equivalem a identidades/aulas canônicas.

## Readback final

| Componente | Resultado comprovado |
|---|---|
| Catálogo | 3.311 registros; 3.023 presentes; 288 históricos/ausentes; dez cursos ok, #02 incomplete com warning empty_unverified/cooldown |
| Fontes | 3.001 vínculos present/current/available; 2.252 objetos físicos no inventário; 13 pendências classificadas, sem inventar conteúdo |
| Fila | 3.006 queued; uma processing (Literatura); seis validated; uma review (Espanhol); zero failed; 518 superseded preservados |
| Elegibilidade | 2.993 queued com fonte elegível; 13 adiados; estado/motivos publicados no status |
| ASR | active/enabled, gate true, um decoder, lease recente, breaker fechado, restart/continuidade observados |
| Timers | Seis active/enabled: catálogo, materiais, vídeos, index, OneDrive, OCR; ASR não usa timer |
| Materiais/PDF | Dois PDFs novos somente remotos; 174 materiais, 8.457 páginas v5; 7.912 liberadas/545 bloqueadas |
| Integridade/temporários | SQLite quick_check ok, zero jobs duplicados, zero árvores materiais falhas; uma árvore ASR pertencente ao job ativo, não resíduo do job concluído |
| Recursos | 11.06 GiB livres; ~17.12 GiB RAM disponível; carga ~3 em quatro CPUs; ASR ~4 GiB, limites 300%/12GiB |
| Testes/deploy | 690 testes integrados, 37/37 módulos/renderer SHA iguais, hashes das units ASR/materiais e drop-in API registrados |

A unit global de catálogo ainda conserva **Result=exit-code/1 de 03:58, anterior à correção**. Não foi zerada para fabricar sucesso, nem se repetiu toda a varredura. O smoke dirigido da implementação atual terminou exit0 e o timer mantém próximo evento 09:00 UTC; isso não é alegação de nova conclusão global pós-deploy. #03 continua vazio de vídeo nativo verificado, não pedagogicamente vazio.

## Pendências não bloqueantes do MVP

Gold humano/WER/CER (não medidos), code-switch, refinamento de timestamps/termos científicos, revisão acadêmica de PDF/figuras/fórmulas e páginas privadas, UI futura de indisponibilidade e novos probes dos recursos adiados. Notion conectado=false nesta missão; não solicitar autenticação AFK nem bloquear entrega por isso.

## Publicação

Branch `feat/study-hub-migration` preservada. Os seis commits de código acima foram publicados sem force; ref 7b93b6176b89cd0680f30e3ccb35340d4c6e4b68 relida no GitHub. Documentação/evidências são um complemento separado; seu SHA remoto é verificado após commit, sem referência circular ao próprio documento. Deploy seletivo, sem deletar, 37/37 módulos SHA iguais e units conferidas. Alterações locais alheias e originais remotos não integram os commits desta missão.

Decisões operacionais: publicar warnings v4 sem editar texto; manter Espanhol privado; aceitar recursos indisponíveis com cooldown; reconciliar somente streak de reviews comprovadamente superadas; usar retomada real do piloto como homologação de recuperação da unit. Custos/limites: QA não é gold acadêmico, Espanhol exige melhoria futura, recursos adiados dependem de descoberta válida e falha de materiais retida pode requerer reconciliação manual. O renderer histórico de units ainda não deve ser usado em instalação integral: a unit materiais revista é instalada seletivamente e o runbook avisa esse limite.
