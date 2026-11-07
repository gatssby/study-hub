# Study Hub — auditoria direcionada Sprint 1

Data: 07/11/2026, primeira leitura 17:52–18:02 UTC (14:52–15:02 BRT). SSH `oracle-vps`; comandos read-only, sem deploy/reload/restart nem DNS. Os valores abaixo são snapshots, não garantias permanentes. Ver seção pós-execução ao final.

## n8n e ingresso existentes

- HTTPS `https://n8n.gatssby.com.br/` e `/healthz`: ambos HTTP200, curl sem ignorar TLS. A raiz do editor responde; não foi feito login nem executado workflow.
- Container `n8n-n8n-1`, ID `e479101ea8aafe73f6651c7616d6c7c2513ff66a5d7aa87a71606f2bac8fa603`, processo740519, iniciado `2026-11-01T04:01:04.053050276Z`, RestartCount0, restart policy `always`. Volume Docker persistente montado em `/home/node/.n8n`; conteúdo/nome do volume, ambiente e Compose não foram lidos/modificados.
- Nginx active/enabled, master PID1911615, ativo desde `2026-11-04 06:58:40 UTC`; `sudo nginx -t` passou. Sem reload nesta sessão.
- `/etc/nginx/sites-enabled/n8n.gatssby.com.br` encaminha `location /` a `http://127.0.0.1:5678`; preserva hostname/TLS/rotas. SHA256 do vhost `4c8934b89266b441df0409c84b8183f46581b4259ebcacb2dbf7a73b6c7405d7`.
- Certificado n8n CN n8n.gatssby.com.br, válido de `2026-10-28 02:30:07 UTC` até `2027-01-26 02:30:06 UTC`; SHA256 do fullchain `4ae51b9f67063e200f1bec8be67c104a2d084cec14d6c26d049b9211be44d9b7`. Chave privada não lida.
- Certbot.timer active/enabled, renovação existente preservada. Não emitir/reemitir certificados nesta sessão.
- Nenhum endpoint `/webhook/*` ou `/webhook-test/*` chamado, nem GET: método GET também pode disparar automação. Rotas herdam `location /`; isso comprova configuração, não entrega de um webhook real ou websocket. Essas homologações exigem workflow de teste expressamente autorizado em futura sessão.

## DNS e certificados

Autoridades `b.sec.dns.br` e `c.sec.dns.br`; SOA observado serial2026285000. Consultas a ambas: apex sem A, www sem A. Consultas recursivas A/AAAA de apex/www vazias; n8n/anki/sales/verbo A `137.131.191.66`, sem AAAA observado. n8n TTL autoritativo3600. Sem resposta CAA do apex na leitura.

O mesmo IP `137.131.191.66` foi confirmado como saída pública da VPS e como destino DNS dos serviços existentes; interface privada `10.0.1.138`. Ainda confirmar propriedade/reserva do IP no painel Oracle antes do cutover. Acesso administrativo a Registro.br não foi solicitado nem comprovado; somente autoridade DNS foi confirmada.

Registros a criar **posteriormente**, sem alterar nenhum existente:

| Tipo | Nome na zona gatssby.com.br | Valor | TTL sugerido |
|---|---|---|---|
| A | @ (apex) | 137.131.191.66 | 300 durante cutover |
| CNAME | www | gatssby.com.br. | 300 |

Não criar AAAA enquanto IPv6 não estiver homologado. Não criar wildcard. Não criar `study` nesta sessão. Não alterar A/certificado/webhooks de n8n. `www` redirecionará para apex, mas também precisa TLS/SAN próprio. Não há certificado apex emitido/instalado observado.

Certificados presentes (CN / validade final UTC):

- verboai.com.br: 06/01/2027 16:45:33.
- gatsby-anki.137.131.191.66.nip.io: 22/12/2026 16:35:12 (histórico; não concluir que ingress atual o usa).
- sales-igd.com.br: 08/12/2026 13:43:18.
- n8n.gatssby.com.br: 26/01/2027 02:30:06.
- anki.gatssby.com.br: 10/01/2027 03:14:10.

## Vhosts e serviços preservados

| Vhost habilitado | Responsabilidade/destino observado |
|---|---|
| default | HTTP80 default_server, /var/www/html; manter sem alterações |
| n8n.gatssby.com.br | TLS443 → loopback5678 |
| anki.gatssby.com.br | TLS443 → loopback27701 |
| sales-igd.com.br | apex TLS → loopback3100; www/HTTP redirecionam |
| verboai.com.br | estático /var/www/verboai.com.br, TLS e www |

Smoke GET raiz dos demais serviços antes de mudanças locais: Anki404 (raiz sem rota, não prova falha da API), Sales307 (redirect), Verbo200. Não tentar “corrigir” esses retornos nem inferir regressão sem comparar mesma rota. Não exercitar rotas mutantes.

Docker em execução: igd-links-app (Up18h,3000 em todas interfaces IPv4/IPv6, exposição **preexistente**), n8n-n8n-1 (loopback5678), sales-intelligence-web (healthy loopback3100), sales-intelligence-postgres (healthy loopback5432), ignicao-backend (porta de container8787 sem publicação host observada). Docker enabled. Não enumerar ambientes/bancos ou mudar políticas desses containers.

FO API `127.0.0.1:8780`, active/enabled PID3138706 desde05:36:16 UTC. ASR `study-hub-fo-transcription.service` active/running/enabled PID3143673 desde05:43:41 UTC; memória cgroup4.35GB no snapshot, não alterado. Sem iniciar ASR concorrente. Timers catalog/materials/videos/index/onedrive/ocr ativos, calendários presentes; timer ativo não prova ciclo concluído. Os limites/permanência ASR estão em federal-online/transcription/ACTIVATION.md; não reinstalar units antigas pelo renderer.

Persistência FO: código `/home/ubuntu/study-hub/federal-online`; estado `/home/ubuntu/study-hub-state/federal-online`; venv `/home/ubuntu/study-hub-venv`. Observador local consulta as mesmas fontes em somente leitura; não relocou banco/corpus nem criou serviço na VPS. Anki/Verbo/Whisper/IGD não modificados.

## Portas e capacidade

VPS ARM64,4 CPUs, RAM23972MiB, disponível17598MiB no primeiro snapshot, swap0. Disco raiz46G total/35G usados/11G livres (76%). Load averages3.30/3.14/3.11: Whisper já ocupa CPU; build deve ficar no Mac, não compilar na VPS durante ASR.

Listeners preexistentes:

- Públicos/all-interface IPv4/IPv6:22,80,111,443,3000. Não alterar firewall nesta missão.111/3000 merecem auditoria de segurança separada, não “consertar” incidentalmente.
- Loopback: DNS53,3100,5432,5678,8080,8770,8771,8780,27701.
- Bridge Docker172.18.0.1:8788.
- VPS3400 e3401 livres no snapshot. Não iniciar frontend/backend na VPS nesta sessão.

Topologia escolhida: Nginx estático para apex; `/api/dashboard` somente leitura → backend observacional privado3401. FO8780 permanece interno. Preview React/Vite3400 e observador3401 só em loopback **do Mac**; backend SSH é ferramenta de desenvolvimento, não serviço público a instalar na VPS.

## Preparação sem publicação

Templates em `ops/study-hub/web/`: vhost HTTP ACME e vhost HTTPS isolados, auth antes de static/API, proxy restrito, sem default_server nem referência ao backend n8n. Runbook separa DNS, certonly webroot, nginx-t/reload gracioso e rollback somente do novo host. Nesta sessão templates não foram copiados para `/etc/nginx`, nenhum symlink foi criado, nenhum certificado emitido, nenhum DNS alterado.

## Pós-execução

Leitura pós em **07/11/2026 18:08:32 UTC / 15:08:32 BRT**:

- n8n raiz200, healthz200, TLS validado por curl; mesmo ID/início/PID740519 e RestartCount0. SHA256 do vhost e certificado idênticos aos valores acima.
- Nginx active/running PID1911615, NRestarts0; `nginx -t` aprovado. ASR active/running PID3143673, NRestarts0; API FO active/running PID3138706, NRestarts0. Nenhum reload/restart executado.
- Mesmos listeners VPS: nenhuma porta pública nova e3400/3401 ausentes. FO8780 segue loopback.
- Anki raiz404, Sales307, Verbo200, iguais à primeira leitura. Apex/www continuam sem A nas consultas autoritativas repetidas.
- RAM disponível17529MiB; disco livre arredondado12G no `df -h` (fronteira de arredondamento durante processamento normal); load3.25/3.12/3.09. Sem build na VPS.
- Mac: preview PID25486, RSS35120KiB/CPU0.0% instantâneo; observador PID26237, RSS7744KiB/CPU0.0% instantâneo. Ambos listeners somente127.0.0.1:3400/3401. Medição instantânea não é benchmark de pico.
- Smoke integrado real às18:06:38 UTC: `/api/dashboard` pelo Vite200;12 done,2998 queued,4 review,1 processing,174 materiais,8457 páginas/7912 liberadas/545 bloqueadas,3002 fontes/2253 objetos/13 pendentes. Alteração de review/fila foi observada enquanto worker continuou com mesmo PID; não é fixture nem efeito de UI.

Nenhuma comparação com tráfego real de webhook, websocket autenticado, login no editor ou reboot está incluída. Foram verificados HTTP público, TLS, configuração, identidade de processo e ausência de alteração de vhost/certificado; não prometer homologação funcional completa de todos os workflows.

Fechamento em **07/11/2026 18:18:05 UTC /15:18:05 BRT**: n8n raiz/healthz200/200; mesmo container/PID/início/restarts0; hashes vhost/certificado iguais. Nginx/Whisper/API active/running com mesmosPIDs e NRestarts0; nginx-t aprovado; listeners públicos e loopback inalterados. RAM disponível17517MiB e raiz12G livres (76% usados). Preview3400/observer3401 seguem somente127.0.0.1 no Mac. Reexecução final:6 testes frontend, build e5 testes observer aprovados; smoke Nginx isolado aprovado.84 arquivos preexistentes novamente comparados por SHA256, nenhum modificado.
