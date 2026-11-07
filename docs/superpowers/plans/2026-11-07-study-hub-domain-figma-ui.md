# Study Hub — UI fiel ao Figma e publicação em gatssby.com.br

Atualizado: 07/11/2026, Sprint 1 (auditoria pré/pós 14h52–15h08 BRT). Este documento complementa o roadmap de observabilidade `2026-11-07-study-hub-ui-roadmap.md`. **Nenhuma migração DNS, edição do Nginx da VPS, reload ou restart de n8n/Whisper foi executado.** Preview local e arquivos de preparação entregues; publicação pública continua fora desta sessão.

## Decisões do produto

- **Destino de produção:** `https://gatssby.com.br/` para o Study Hub, opcionalmente `www.gatssby.com.br` redirecionando para o apex. O endereço `https://n8n.gatssby.com.br/` e todos os seus webhooks continuam iguais e isolados.
- **Design de referência obrigatória:** https://www.figma.com/community/file/1531598093643920564/student-dashboard-lms-application. O pedido é **replicar fielmente** a interface original, não criar uma interface apenas inspirada. A fidelidade deve ser medida por comparação frame a frame: grid, sidebar, composição, cores, tipografia, espaçamentos, raios, sombras, ícones, imagens e estados. Adaptar apenas conteúdo/domínio Study Hub e comportamento real.
- **Acesso ao design recuperado:** Safari autenticado abriu o Community e permitiu Remix no workspace do proprietário. O original é **Figma Make**, não Design tradicional: cópia editável `https://www.figma.com/make/kd36an23RU8hgKDxF55sTR/Student-Dashboard-LMS-Application--Community-?t=jzVKu5fXZMnONsEo-6`, confirmada pelo proprietário. Preview da autora vinculado pelo Community: `https://poll-meta-32981667.figma.site/`. MCP desktop3845 respondeu, mas ferramentas de frames/layers desse servidor não suportam Make. Tokens/estrutura foram inspecionados no DOM/CSS computado e screenshots reais do preview original; **não existem node IDs Design inspecionados**, nem sidebar no Dashboard original. Contrato em `docs/design/study-hub-figma-contract.md`.
- **Implantação em fases:** localhost/túnel SSH → staging opcional `study.gatssby.com.br` → apex `gatssby.com.br`; cutover somente após health e autenticação.
- **Stack preferencial** para análise: frontend estático React + TypeScript + Vite, distribuído pelo Nginx, com backend observacional mínimo em FastAPI sobre loopback. Ajustar após inspecionar o repositório/template; não adicionar servidor SSR sem necessidade. Separação Anki/FO mantida.
- **Produto inicial:** dashboard/Visão geral com dados reais de transcrição, downloads, PDF, sincronização e saúde da VPS; depois catálogo de cursos e aulas, leitura de transcrições validadas e PDFs saneados. Não reconstruir o backend FO nem reativar cronograma legado.

## Inventário real antes de qualquer mudança

Verificado em 07/11 ~14h41 BRT por SSH e chamadas HTTP/TLS:

| Item | Situação |
| --- | --- |
| DNS autoritativo | `b.sec.dns.br`, `c.sec.dns.br` (DNS.br/Registro.br); sem A publicado no apex `gatssby.com.br` nesta leitura |
| n8n público | `https://n8n.gatssby.com.br/` e `/healthz` HTTP 200 com TLS válido |
| n8n privado | Container Docker `n8n-n8n-1` up, sem reinícios registrados, `127.0.0.1:5678`; Nginx encaminha o hostname somente para essa porta |
| TLS n8n | Certbot certificado exclusivo `n8n.gatssby.com.br`, válido até 26/01/2027; `certbot.timer` ativo/enabled |
| Web ingress | Nginx ativo nas portas 80/443; `sudo nginx -t` passou; hosts separados para `n8n`, `anki`, `sales-igd`, `verboai` e default |
| FO API | `127.0.0.1:8780`, leitura local; ASR/coletores continuam ativos |
| Outros serviços | Porta 3000 ocupada pelo IGD links, porta 3100 usada pelo Sales Intelligence, 8080 por túnel; **3400** livre no snapshot |
| Capacidade | VPS Oracle ARM64 4 OCPU/24 GiB RAM; ~11 GiB disco livre; Whisper usa recursos significativos |
| Figma | A URL Community não entregou frames/layers via leitura automatizada: HTTP 403; não declarar cópia visual concluída |

**Risco principal:** não é conflito entre `n8n` e Study Hub no mesmo domínio, mas mudanças indevidas no vhost, DNS, certificados, autenticação ou nas portas compartilhadas. O Nginx roteia por hostname; criar outro `server_name` com novo serviço em loopback **não exige parar n8n**.

## Topologia-alvo

```text
Internet (HTTPS :443)
        |
      Nginx [VPS Oracle]
        ├── n8n.gatssby.com.br ──> 127.0.0.1:5678 (Docker n8n; inalterado)
        ├── anki.gatssby.com.br ─> serviço Anki atual (inalterado)
        ├── sales-igd.com.br ────> serviço IGD atual (inalterado)
        ├── verboai.com.br ──────> host atual (inalterado)
        └── gatssby.com.br ──────> Study Hub frontend estático (Nginx)
                                      /api/* --> backend read-only 127.0.0.1:3401
                                      backend --> FO API/SQLite privada (sem acesso browser)
```

O frontend pode ser testado localmente em `127.0.0.1:3400` antes da publicação do domínio. **Não usar 3000, 5678, 8780, 8080 ou 3100**. O backend do dashboard não deve habilitar mutações nem expor conteúdos privados de revisão, PDFs brutos ou URLs HLS assinadas.

## M0 — Auditoria de integração e proteção do n8n (P0, primeira sessão)

- [x] Verificação read-only de n8n/Nginx/TLS/DNS/portas/recursos, sem interferir na operação.
- [x] Salvar inventário redigido em `docs/research/2026-11-07-study-hub-sprint1-infrastructure.md`: vhosts, DNS, health, TLS, timers, paths, recursos e pré/pós; sem secrets/workflows.
- [x] Validar regressão n8n pré/pós: `GET /`, `GET /healthz`, TLS, hashes vhost/certificado, rota proxy e identidade/início/restarts do container. **Webhooks não foram chamados nem por GET**, pois podem disparar automação; configuração da rota inspecionada, não homologação de workflow/websocket/login autenticado.
- [ ] Confirmar autoridade e possibilidade de gerir DNS em Registro.br; se sem sessão/permissão, fornecer as entradas exatas a serem criadas, sem inventar alteração aplicada.
- [x] Preparar cutover e rollback do vhost isolado em `ops/study-hub/web/README.md` e exemplos HTTP/HTTPS; validação local com fixtures separada de futura homologação na VPS. Sem instalar os exemplos.
- [x] Confirmar3400/3401 livres na VPS, recursos e Whisper contínuo. Build feito no Mac; processos de preview só em loopback do Mac.

## M1 — Acesso ao design exato e contrato visual (P0, primeira sessão)

- [x] Community aberto no Safari autenticado e Remix editável verificado; recurso Make, sem `/design/` ou node IDs convencionais. Link acima.
- [x] Screenshots reais Dashboard desktop/mobile e materiais, DOM/componentes e CSS computado do preview original salvos em `docs/design/evidence/`. Layers/variáveis Design via MCP não disponíveis para esse Make; não alegar inspeção de frames inexistente.
- [x] Contrato visual criado com tokens/dimensões/limites;10/10 medidas selecionadas iguais na comparação local, não score pixel-perfect global.
- [x] Licença CC BY4.0 observada no Community, autora Sakshi Parashar, atribuição na UI/README/notices. Lucide ISC e fontes de sistema; nenhum asset de outro template.

## M2 — Primeira UI funcional, ainda sem domínio público (P0)

- [x] Frontend isolado `apps/study-hub-web`, React/TypeScript/Vite, build estático; Anki e serviços legados intocados.
- [x] Shell, header, resumos, badges, MetricCard/Progress/detalhes reais e Dashboard adaptados ao original inspecionado. Sidebar não foi inventada; biblioteca/módulos não implementados. Limites de fidelidade registrados no contrato.
- [x] Dados reais read-only via `ops/study-hub/web/observer.py`, allowlist GET `/api/dashboard`, timeout/cache20s/Host/Origin e null para desconhecidos. Somente local, não backend de produção autenticado. Counters de fila/progresso/PDF/vídeos/disco/units presentes; histórico e término real de sync ainda pendentes.
- [ ] Instrumentar bytes, velocidade e estados de transferências **antes** de barra global de downloads. Sem telemetria real: mostrar contagens e aviso `progresso indisponível`.
- [x] Responsivo, loading/offline/stale/error e falhas conhecidas de serviços explícitas;6 testes frontend e5 observer direcionados, build aprovado, smoke browser real e10 medidas comparadas. Não há screenshot/iframe como UI.
- [x] Preview `http://127.0.0.1:3400` e observador3401 no Mac. Nenhum serviço permanente/público; proxy Vite same-origin, FO8780 não exposta.

## M3 — DNS, HTTPS e publicação do domínio (P0 após M2)

- [ ] Após prova de UI operacional e autenticação: adicionar DNS A para `gatssby.com.br` apontando para **IP público já confirmado da VPS** no painel DNS.br. Criar `www` se desejado e staging `study` opcional; não editar/remover o registro de `n8n`.
- [ ] Verificar resolução de DNS por resolvedores diferentes e autoritativos; evitar repetir Certbot enquanto DNS não propagar.
- [ ] Criar `/etc/nginx/sites-available/gatssby.com.br` separado, habilitar seu symlink, `nginx -t` e reload gracioso, sem restart do Docker n8n. Proteger frontend/API por auth adequada antes de exposição.
- [ ] Emitir certificado Let's Encrypt do novo hostname com método compatível com Nginx atual; manter autorrenovação sem alterar certificado n8n. HTTPS testado externamente.
- [ ] Testes pré e pós: n8n HTTP200/healthz/websocket/webhook routes sem chamadas mutantes, anki/sales/verboai vhosts, certificado correto, Study Hub host/403 vs login, proxy auth, latência, recursos e restart.
- [ ] Rollback: remover/desabilitar **somente** vhost novo, reload Nginx e restaurar apontamento DNS do Study Hub, nunca o n8n.

## M4 — Biblioteca e leitor (P1)

- [ ] Curso → disciplina → frente → módulo → aula, transcrições validadas com timestamps e warnings, estados inacessível/incomplete/review sem bloquear a biblioteca.
- [ ] PDFs saneados/citados, com páginas bloqueadas identificadas; validação acadêmica prioritária para fórmulas, tabelas, figuras e imagens.
- [ ] Ações administrativas somente com papéis e auditoria. Integração Anki isolada via contratos.

## Condições de conclusão e exclusões

1. O n8n mantém a URL exata, TLS, fluxo de webhooks e estado Docker; não há regressão observada.
2. Study Hub utiliza hostname próprio em `gatssby.com.br`, sem reutilizar raiz/path do n8n e sem expor FO API interna.
3. Design é reproduzido de **frames reais** do arquivo Community autorizado; comparações documentadas, sem alegar fidelidade se não houve acesso.
4. Transcrições, PDF, vídeos e sincronizações aparecem com métricas reais; bytes de downloads só quando instrumentados.
5. Nenhum serviço de ASR, Anki, IGD, n8n ou outros projetos é reiniciado/interrompido na sessão inicial.
6. Git: branch `feat/study-hub-migration`, stage seletivo, commits/push sem force, working tree Anki intocado.
7. **Não é objetivo da primeira sessão concluir tudo nem publicar o domínio sem DNS/auth**; entregar auditoria protegida, contrato do Figma quando acessível, skeleton local e plano de cutover testável.

## Handoff do Sprint 1

- Abrir preview local: iniciar `python3 ops/study-hub/web/observer.py` na raiz e `npm run dev` em `apps/study-hub-web`; ambos já foram exercitados juntos. README local documenta instalação/encerramento.
- n8n pré/pós200/200, mesmo container iniciado01/11, zero restarts, hashes vhost/TLS iguais. Nginx/Whisper/API mesmos PIDs; portas públicas VPS inalteradas.84 arquivos locais preexistentes comparados por SHA256, sem alterações nossas.
- DNS futuro exato: A `@` →137.131.191.66, CNAME `www` →gatssby.com.br., TTL300 inicial; revalidar IP reservado/autoridade no painel. Administração DNS não comprovada e nenhum registro alterado.
- Antes de produção: adaptar coletor observacional à VPS com autenticação/contrato homologado (wrapper SSH/http.server é desenvolvimento), revisar auth Basic/produção, CSP com build real, permissões, ACME/hooks e lineage nova apex/www. Validar `nginx -t` na VPS e preparar manutenção/rollback antes de reload aprovado.
- Backlog: instrumentação real de bytes/velocidade/término OneDrive, histórico/última execução, biblioteca/leitor, revisão pixel-a-pixel dos estados e glyphs. Não concluir download ou sincronização a partir de timer/counters.
- Build passou com dois avisos do bundler sobre diretiva `use client` da dependência Lucide; app é client-only, sem SSR. Avisos registrados, não ocultados. Suite global Anki não executada por escopo proporcional; whitespace já existente no Anki não foi corrigido.
- Revisão independente sem Critical/Important no escopo local. Falhas conhecidas de serviços já corrigidas por TDD (sexto teste). Minors remanescentes: o template futuro envia Host localhost e origem HTTPS, incompatíveis com a allowlist **do observador de desenvolvimento**; adaptar/homologar o futuro backend antes de ligar o vhost. O header local compensa5.25px de gap de linha vazia do grid original com padding inferior; altura externa68.25px confere, mas a propriedade CSS interna não é idêntica. Revisar na próxima passagem de fidelidade, sem alegar equivalência pixel-perfect.
