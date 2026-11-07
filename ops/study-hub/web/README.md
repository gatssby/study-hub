# Study Hub — preparação de vhost, NÃO publicado

Estes arquivos são exemplos independentes para `gatssby.com.br` e `www.gatssby.com.br`. Nenhum comando deste runbook foi executado na VPS. Publicação, DNS, instalação, emissão de certificado e reload exigem autorização futura explícita. Não executar o documento como script.

## Escopo e contratos

- `gatssby-http.conf.example`: porta 80, somente arquivos ACME públicos; qualquer outra URI redireciona ao apex HTTPS preservando caminho/query. Não serve frontend HTTP.
- `gatssby-https.conf.example`: TLS apex com frontend estático em `/srv/study-hub-web/current`, Basic Auth obrigatório; www apenas redireciona ao apex. O redirect não serve dados e não pede senha antes de redirecionar.
- Único upstream: **GET exato `/api/dashboard`**, sem query, autenticado, em `127.0.0.1:3401/api/dashboard`. HEAD/POST/PUT/DELETE/OPTIONS/PATCH retornam 405; query retorna 400. `/api` e demais `/api/…` retornam 404, nunca proxy/SPA. Essas rejeições ocorrem antes da autenticação e não fornecem dados.
- Adaptador observacional privado **ainda precisa existir e ser homologado**. Não criá-lo aqui. Deve aceitar apenas GET nessa rota, não executar ações, publicar apenas projeção agregada allowlisted e não expor credenciais, conteúdo privado ou controle de FO. Não usar FO 8780 como upstream substituto. Porta 3400 não é necessária para frontend estático.
- Não há `default_server`, wildcard, novo upstream global nem dependência de snippets compartilhados. Não editar nginx.conf, default ou vhosts existentes. Não alterar Anki, n8n, Sales, Verbo, FO/Whisper, units, containers, firewall ou portas públicas 3400/3401/8780.
- Frontend, assets e API usam `private, no-store`; não há cache compartilhado ou assets públicos. CSP bloqueia código inline, CDNs e conexões externas: validar o build real antes de liberar; não relaxar CSP automaticamente. Não definir HSTS inicialmente (sem includeSubDomains/preload).
- Não colocar secrets, fontes privadas, mapas `.map`, service workers ou links simbólicos para arquivos privados no build. Nginx só deve conseguir ler o release e o arquivo de senha dedicado.

## Pré-condições (revalidar na data da autorização)

1. Inventariar **somente leitura** Nginx/version/modules, vhosts, listeners, estado dos serviços e certificados; registrar baseline privado com hashes dos vhosts existentes e respostas dos hosts atuais. Não imprimir envs, senhas, tokens, URLs assinadas ou `nginx -T` indiscriminadamente.
2. Contexto da auditoria anterior, não prova atual: VPS `137.131.191.66`; apex/www ainda sem A/AAAA autoritativos; hosts Anki/n8n/Sales/Verbo já em uso. Nenhum certificado existente deve ser alterado. Conferir os autoritativos (`dig NS gatssby.com.br`), depois A/AAAA/CAA do apex e www em cada servidor autoritativo (incluindo b.sec.dns.br/c.sec.dns.br quando ainda delegados). Não inventar AAAA: publicar IPv6 somente se roteamento/listener externo estiverem homologados. A/CNAME/CAA e propagação são ações futuras separadamente autorizadas.
3. Resolver apex e www publicamente ao destino correto; garantir 80/443 já disponíveis sem interromper outros hosts. Não habilitar HTTPS deste vhost antes de existir certificado para **ambos** os nomes. Nenhum registro dos subdomínios existentes deve mudar.
4. Homologar artefato estático sanitizado, com index.html e assets locais, em release novo e imutável sob `/srv/study-hub-web/releases/<release-id>`. Manter `/srv/study-hub-web/current` apontando apenas ao release aprovado; registrar destino anterior se existir. Nenhum checkout do repo inteiro no webroot.
5. Confirmar adaptador em **127.0.0.1:3401**, nunca 0.0.0.0/[::]; sem side effects e sem passthrough genérico. Validar seu JSON allowlisted por loopback. Não iniciar/reiniciar serviços como parte deste runbook. Sem adaptador aprovado, frontend pode ser preparado mas dashboard não é considerado funcional.
6. Nginx deve possuir módulos SSL/proxy/auth_basic e versão TLS compatível. Criar senha **interativamente**, sem senha em argv/log/repositório: `sudo htpasswd -c /etc/nginx/study-hub-web.htpasswd <usuario>` somente se o arquivo dedicado ainda não existir. Para usuários posteriores omitir `-c`. Se htpasswd faltar, parar e aprovar instalação separadamente. Arquivo root-owned, modo 0640, grupo real do worker (confirmar; não assumir), diretórios sem acesso de escrita do worker. Não reaproveitar usuários/arquivos de senha de outros serviços.
7. Confirmar disponibilidade do Certbot e auditar hooks existentes antes de qualquer emissão/renovação: hooks globais também podem executar ações. Se ausente, aprovar instalação separada; não instalar silenciosamente.

## Rollout futuro em duas fases

**Apenas após autorização; executar cada etapa manualmente, parando em qualquer falha.** Os exemplos pressupõem paths Debian/Ubuntu confirmados na inspeção. Recusar sobrescrever arquivos/symlinks preexistentes com os nomes abaixo; se existirem, identificar dono e revisar antes de prosseguir. Transferir só estes dois exemplos, nunca envs ou configurações de outros hosts.

### 1. HTTP / ACME isolado

- Criar `/var/www/study-hub-acme/.well-known/acme-challenge/` dedicado, root-owned, diretórios 0755 e tokens legíveis pelo worker. Não usar webroots de Anki/n8n.
- Instalar o exemplo HTTP como `/etc/nginx/sites-available/study-hub-gatssby-http.conf` e criar somente seu link `/etc/nginx/sites-enabled/study-hub-gatssby-http.conf`.
- Executar `sudo nginx -t`. Se falhar, remover apenas o link recém-criado e repetir o teste; **não reload** enquanto falhar.
- Somente após teste aprovado e janela autorizada: `sudo systemctl reload nginx`. Reload é do Nginx compartilhado, não existe reload por vhost; não é restart. Se nem reload compartilhado estiver autorizado, parar aqui.
- Criar token sintético no webroot e conferir externamente, por HTTP nos dois nomes, conteúdo 200 exato; token inexistente 404; demais caminhos 308 para apex HTTPS (temporariamente ainda sem TLS deste host). Remover somente o token sintético. Revalidar hosts existentes contra baseline.

### 2. Certificado novo e HTTPS

Revisar hooks primeiro; obter certificado **sem plugin nginx**, sem standalone e sem parar serviço:

```sh
sudo certbot certonly --webroot \
  --webroot-path /var/www/study-hub-acme \
  --cert-name gatssby.com.br \
  -d gatssby.com.br -d www.gatssby.com.br
```

- Confirmar ausência prévia da lineage `gatssby.com.br`; se já existir, parar e revisar, não expandir/reusar certificado de terceiros. Informar email/termos interativamente. Conferir SANs, validade, permissões e caminhos reais em `/etc/letsencrypt/live/gatssby.com.br/`. Não copiar chaves para repo nem alterar permissões globais.
- Somente então instalar o exemplo HTTPS como `/etc/nginx/sites-available/study-hub-gatssby-https.conf` e seu link homônimo em sites-enabled. Manter HTTP para renovação.
- Confirmar senha/build/adaptador e rodar `sudo nginx -t` novamente; se aprovado, reload autorizado e validação abaixo. Falha de sintaxe nunca deve causar restart ou edição de outros vhosts.
- Renovação futura: `sudo certbot renew --cert-name gatssby.com.br --dry-run` somente após revisão de hooks e autorização, pois acessa ACME e pode disparar hooks. Não executar renew global nem force-renewal. Planejar deploy-hook **restrito a esta lineage** que rode `nginx -t` antes de reload autorizado; não alterar timers/hooks compartilhados automaticamente. Certificado renovado em disco sem reload não prova certificado servido atualizado. Preservar webroot HTTP e testar renovação antes de aceitar operação contínua.

## Validação de aceite na publicação futura

Use `curl --resolve 'gatssby.com.br:443:137.131.191.66'` quando necessário para controlar o destino, **sem `-k` em produção**; verifique DNS público também. Para auth use `curl --user <usuario>` (senha solicitada, não registrada em shell). Não colocar credenciais no histórico, URLs ou documentação. Redirecionamentos devem ser inspecionados inicialmente sem `-L`.

| Prova | Esperado |
| --- | --- |
| HTTP token existente / ausente, nos dois nomes | 200 token / 404; sem frontend |
| HTTP `/rota?q=1`, ambos os nomes | 308 `https://gatssby.com.br/rota?q=1` |
| TLS/SNI apex e www | cadeia válida, SAN correto, certificado novo |
| HTTPS www qualquer URI | 308 apex, preservando URI; nenhum dado |
| Apex `/`, asset e GET `/api/dashboard` sem credencial ou com senha incorreta | 401 + WWW-Authenticate |
| Apex `/` e rota SPA, credencial correta | 200 build aprovado; CSP sem violações funcionais |
| GET exato `/api/dashboard`, auth correta, sem query | 200 JSON allowlisted do adaptador |
| HEAD, POST, PUT, DELETE, OPTIONS, PATCH em `/api/dashboard` | 405, nenhum request ao adaptador |
| GET `/api/dashboard?x=1` | 400, nenhum request ao adaptador |
| `/api`, `/api/`, `/api/dashboard/`, `/api/fo`, `/.env` | 404, nenhum request ao adaptador |
| Headers apex (incluindo 401/404/405) | CSP, nosniff, DENY, no-referrer, Permissions-Policy, private/no-store |
| API upstream | sem Authorization/Cookie encaminhados; sem Set-Cookie retornado |
| Listeners | adaptador só loopback; nenhuma nova porta pública |
| Hosts e serviços existentes | respostas/estado iguais ao baseline; FO/Whisper continuam intactos |

Não usar apenas `curl -I` para testar dashboard: HEAD deve falhar. Não considerar 502 um aceite da API. Erros 404/405 podem preceder auth de propósito. Não há garantia de que um usuário autenticado não copie dados: Basic Auth é barreira de acesso, não DRM. Não aprovar só com `nginx -t`; conferir comportamento, conteúdo sanitizado e ausência de exposição FO.

## Rollback restrito ao novo vhost

- Antes do primeiro reload: remover somente os links recém-criados deste vhost; `sudo nginx -t`. Configuração ativa permanece anterior se não houve reload.
- Após publicação defeituosa: desabilitar **somente** `/etc/nginx/sites-enabled/study-hub-gatssby-https.conf` e `/etc/nginx/sites-enabled/study-hub-gatssby-http.conf`, conferir `sudo nginx -t`, então reload autorizado; nunca restart. Preservar arquivos disponíveis, release, senha e certificado para diagnóstico. Não apagar `/etc/letsencrypt`, não rodar rollback Certbot e não tocar nos links dos outros hosts.
- Atenção: sem estes vhosts, requisições aos nomes podem cair no default já existente. Remoção não garante resposta neutra; validar esse efeito antes de optar por rollback. Se for preciso manter isolamento dos nomes, preparar/revisar separadamente um vhost de manutenção dedicado com certificado existente e 503, sem backend; não editar o default compartilhado às pressas.
- Falha apenas no frontend: restaurar atomicamente somente o symlink `current` ao release anteriormente verificado, se houver. Não restaurar backend/FO/DB. Na primeira publicação, não há release anterior: desabilitar apenas o vhost ou aplicar manutenção aprovada.
- Se DNS foi criado nesta publicação, eventual reversão é ação separada autorizada, somente apex/www criados, respeitando TTL; não muda DNS dos subdomínios. Certificado novo pode permanecer em disco; revisar sua renovação dedicada depois, sem alterar renovações alheias.
- Validar novamente hosts existentes, estado FO/Whisper/n8n/Anki e hashes dos vhosts antigos. Registrar limite: um reload compartilhado substitui workers Nginx, embora só os novos arquivos sejam alterados.

## Validação local realizada nesta preparação

Nginx não estava instalado; Docker CLI existia, mas o daemon não estava disponível. Sem iniciar Docker ou instalar pacote global, Nginx **1.28.2** foi compilado do tarball oficial em cache scratch, usando compilador/OpenSSL/PCRE2 já presentes. Executados `nginx -t` e smoke HTTP/HTTPS real em loopback com certificado, senha, frontend e adaptador **sintéticos**. Apenas na cópia scratch: listeners foram mudados para portas altas aleatórias/loopback e paths de certificado/auth/static/ACME/upstream para fixtures. Diretivas dos exemplos foram mantidas.

Resultado: sintaxe aprovada; ACME 200/404, redirects 308, frontend/API sem auth 401, frontend/SPA autenticados 200, dashboard autenticado 200, seis métodos proibidos 405 (incluindo HEAD), query 400, rotas negadas 404, headers de segurança/cache e remoção de Set-Cookie/Authorization/Cookie aprovados. O adaptador sintético recebeu exatamente uma chamada GET allowlisted. Processo Nginx de teste encerrado no finally; nenhuma alteração/reload/conexão à VPS ou DNS, nenhum commit.

Limites: não valida Nginx/módulos Linux efetivos, permissões de produção, DNS/ACME público, certificado real, senha real, build/CSP real, conteúdo do futuro adaptador ou serviços existentes. `nginx -t` **na VPS com os paths reais** e todos os aceites acima continuam obrigatórios antes de publicar.

Referências oficiais para revisão (não instruções para executar agora): módulos Nginx `ngx_http_auth_basic_module`, `ngx_http_core_module` (GET em limit_except inclui HEAD; por isso guarda explícita de método) e documentação Certbot `certonly`/`--webroot`/`renew`.
