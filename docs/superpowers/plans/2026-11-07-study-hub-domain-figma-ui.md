# Study Hub — UI fiel ao Figma e publicação em gatssby.com.br

Atualizado: 07/11/2026, 14h40–15h BRT. Este documento complementa o roadmap de observabilidade `2026-11-07-study-hub-ui-roadmap.md`. **Nenhuma migração DNS, edição Nginx ou restart de n8n foi executado nesta fase de planejamento.**

## Decisões do produto

- **Destino de produção:** `https://gatssby.com.br/` para o Study Hub, opcionalmente `www.gatssby.com.br` redirecionando para o apex. O endereço `https://n8n.gatssby.com.br/` e todos os seus webhooks continuam iguais e isolados.
- **Design de referência obrigatória:** https://www.figma.com/community/file/1531598093643920564/student-dashboard-lms-application. O pedido é **replicar fielmente** a interface original, não criar uma interface apenas inspirada. A fidelidade deve ser medida por comparação frame a frame: grid, sidebar, composição, cores, tipografia, espaçamentos, raios, sombras, ícones, imagens e estados. Adaptar apenas conteúdo/domínio Study Hub e comportamento real.
- **Limite de acesso ao design:** tentativa de leitura da Community por `curl` e web automatizado retornou HTTP 403. Não há link editável `/design/<fileKey>` nem ID de frame conhecido. A primeira sessão deve obter acesso autorizado no browser/Figma (preferivelmente duplicar no workspace do proprietário) e registrar o arquivo/frames. **Não inventar tokens, layouts ou assets até inspecionar o original**. Se não houver acesso, manter UI visual em hold e concluir só infraestrutura segura.
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
- [ ] Salvar inventário redigido em `docs/research/`: nomes dos vhosts existentes e responsabilidades, DNS records relevantes, health/HTTP, certificados, timers, paths e dependências; não salvar tokens/credenciais nem conteúdos dos workflows.
- [ ] Preparar e validar teste de regressão n8n pré/pós: `GET /`, `GET /healthz`, TLS, certificado, rota proxy, acessibilidade do editor e endpoint de webhook **somente leitura/sem disparar automação**, além de status/uptime do container.
- [ ] Confirmar autoridade e possibilidade de gerir DNS em Registro.br; se sem sessão/permissão, fornecer as entradas exatas a serem criadas, sem inventar alteração aplicada.
- [ ] Definir estratégia de cutover sem downtime: novo vhost isolado, `nginx -t`, reload gracioso, revalidar n8n. Preparar rollback somente do vhost Study Hub, sem tocar n8n ou seu banco.
- [ ] Confirmar portas livres e limite de CPU/disco, evitando competir com Whisper e uploads.

## M1 — Acesso ao design exato e contrato visual (P0, primeira sessão)

- [ ] Abrir o link Community no navegador autorizado ou pelo Figma conectado. Se necessário duplicar o arquivo do Community no workspace do usuário (respeitar licenciamento/atribuição). Obter URL editável `/design/<fileKey>` e os node IDs das telas de referência.
- [ ] Obter screenshot **real** dos frames e inspect de layers, tokens, tipografia, hierarquia, assets originais, responsividade e componentes. Nunca usar imagem inteira do design como interface estática; implementar elementos reais e interações.
- [ ] Criar `docs/design/study-hub-figma-contract.md`: frame inventory, URLs/node IDs, componentes, tokens, dimensões e alvos de comparação. Se Figma bloquear acesso, marcar esse requisito BLOCKED (não substituir por templates externos ou screenshots de outros designers).
- [ ] Verificar direito de uso de assets/fontes e preservar atribuições exigidas.

## M2 — Primeira UI funcional, ainda sem domínio público (P0)

- [ ] Criar frontend isolado no repo (`apps/study-hub-web` ou equivalente aprovado), stack compatível com VPS ARM64 e build estático, sem alterar Anki, n8n ou serviços legados.
- [ ] Implementar fielmente dashboard, navegação e componentes extraídos do Figma. Trocar rótulos educacionais pela semântica FO sem distorcer layout.
- [ ] Dados reais read-only, preferencialmente API agregada com allowlist e autenticação: queue done/queued/review/processing, progresso atual, PDFs saneados, fontes disponíveis/deferred, uso de disco, últimos eventos, status/última execução.
- [ ] Instrumentar bytes, velocidade e estados de transferências **antes** de barra global de downloads. Sem telemetria real: mostrar contagens e aviso `progresso indisponível`.
- [ ] Visualização responsiva, loading/offline/stale/error sem mascarar falhas. Testar render comparado a screenshots do Figma; componentes reais, nada de screenshot como UI.
- [ ] Servir somente por loopback ou túnel SSH no staging inicial; nenhuma página publicamente acessível sem controle de acesso.

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
