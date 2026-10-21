# Study Hub — arquitetura operacional

## Anki GPT vNext

Sync Server oficial ↔ Service Collection → API v2 → MCP → Plugin.

Produção preservada em `/home/ubuntu/anki-vnext`; coleção e mídia não são snapshots da API antiga. API em loopback 8770, MCP 8771 e sync 27701. Código em `services/anki-api-v2` e `services/anki-mcp-v2`; mapa em `anki-vnext/README.md`.

## Federal Online

Portal autenticado → catálogo dinâmico por curso → adaptadores de ingestão → SQLite próprio → API FO 8780.

Materiais: opções reais de curso/disciplina → download autenticado → validação PDF e SHA-256 → índice de páginas → rclone copy/check OneDrive.
Vídeos: catálogo/manifestos/OneDrive → processamento sequencial com reserva de disco → upload versionado → verificação de bytes → remoção apenas do temporário confirmado.
Transcrição: fila persistente e fontes versionadas; execução real bloqueada aguardando autorização explícita. Metadados de fontes e jobs não contêm texto antigo.

Código FO em `/home/ubuntu/study-hub/federal-online`; estado privado `/home/ubuntu/study-hub-state/federal-online`; ambiente `/home/ubuntu/.config/study-hub`; logs por unit e domínio. Nenhuma dependência operacional de `/opt/cronograma-fo` ou do backend Anki antigo.

Serviços independentes: catálogo, materiais, vídeos, indexação, OneDrive, API FO. Units e calendários em `ops/study-hub/render_units.py`. Workers longos pertencem a systemd, não ao terminal Hermes.

## Contrato de consulta

As 19 ferramentas Anki continuam inalteradas. O opt-in `STUDY_HUB_FO_TOOLS=true` registra sete ferramentas FO read-only no mesmo endpoint MCP. Elas chamam HTTP loopback FO sem acessar coleção Anki ou disparar jobs. O adaptador FO também suporta stdio independente.

PDFs são citáveis por identificador de conteúdo, SHA-256 e página. Aulas têm IDs por curso e mídia/item; títulos não definem identidade. URLs com query de autenticação rotativa não criam revisão de vídeo por si só. Transcrições publicáveis precisam pertencer ao corpus `generated_v2`, versão atual e QA aprovado.

## Limites e decisões

- Cronograma FO eliminado; documentação anterior é histórica e não deve servir como runbook.
- Descoberta de cursos percorre navegação autenticada `/portal/cursos` e produtos, sem amarrar o ano a 2026. Árvores acadêmicas não usam categorias conhecidas como allowlist.
- Falhas de login/navegação não autorizam apagar arquivos nem conteúdo remoto. Índice é aditivo e registra ausências/erros.
- Não foram criados backups, dumps ou retenção de transcrições antigas.
- Knowledge e Instructions editoriais foram preservados; migração futura para Skill não altera essas fontes.
- Mídia exclusiva/ambígua do cache Anki antigo é preservada até comprovação de equivalência com a coleção atual. Não se presume que um cache é dispensável pelo nome.
- Repositório público: nenhum estado real, sessão, credencial, URL assinada ou corpus é versionado.

Evidências e limitações específicas: `docs/migration/2026-10-21/REPORT.md`.
