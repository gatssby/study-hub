# Observador local do Study Hub — contrato e fronteiras

## Execução local

```sh
python3 ops/study-hub/web/observer.py
python3 -m unittest discover -s ops/study-hub/web -p test_observer.py -v
```

O processo escuta exclusivamente `127.0.0.1:3401`. Apenas `GET /api/dashboard` é aceito; query strings, barras adicionais e caminhos codificados não são aliases. Outros métodos recebem 405, outros caminhos 404, Host/Origin inesperados 403. Hosts aceitos: `127.0.0.1:3401` e `localhost:3401`, sem duplicação. Origins opcionais são somente HTTP loopback nas portas 3400 e 3401; `null`, duplicações e `Sec-Fetch-Site: cross-site` são rejeitados. Não há CORS. O frontend deve usar `/api/dashboard` na mesma origem, via proxy Vite para `http://127.0.0.1:3401`, preservando Origin local e alterando Host para o destino (`changeOrigin: true`).

Respostas do handler são JSON com `Cache-Control: no-store` e `X-Content-Type-Options: nosniff`. Falha de coleta produz somente `503 {"error":"observation_unavailable"}`: nunca stderr, exceção remota ou snapshot anterior vencido. Não há logs de requests nem do conteúdo bruto.

## Contrato allowlisted

```ts
type Dashboard = {
  observed_at: string;
  transcription: {
    done: number | null; queued: number | null; review: number | null;
    processing: number | null; current_progress: number | null;
  };
  pdf: { materials: number | null; pages: number | null;
         released: number | null; blocked: number | null };
  video: { available_sources: number | null; indexed_objects: number | null;
           pending_sources: number | null };
  services: Record<string, string>;
  storage: { free_bytes: number | null; total_bytes: number | null };
  onedrive: { state: string; last_observed_at: string | null };
  transfer: { state: 'not_instrumented' };
};
```

A projeção cria um objeto novo; não serializa, copia ou repassa `status`, listas ativas ou campos desconhecidos. URLs, títulos, disciplinas, IDs, caminhos e erros não fazem parte do contrato. Contadores exigem números inteiros finitos não negativos; strings numéricas, booleanos, negativos, frações e valores não finitos viram `null`. Ausência nunca vira zero. Progresso é o primeiro valor numérico finito observado na lista de jobs ativos dentro de 0..1; valores fora do intervalo são desconhecidos, não são convertidos em 0%/100%. Não representa progresso agregado, download ou porcentagem calculada dos contadores.

Mapeamento: `transcription_jobs.done/queued/review`, `leased` (ou `processing` quando a chave leased está ausente); `materials_total`, `pdf_pages_total`, `pdf_privacy.released_pages/blocked_pages`; `available_sources`, `components.index.summary.source_videos`, `sources.pending`; `disk_free/disk_total`. `observed_at` é o instante UTC local da projeção bem-sucedida, não um timestamp arbitrário vindo do status remoto.

Serviços: apenas `transcription`, `catalog`, `materials`, `videos`, `index`, `onedrive`, `ocr`. Valores aceitos: `active`, `inactive`, `failed`, `activating`, `deactivating`, `reloading`, `unknown`; qualquer outro vira `unknown`. O estado OneDrive reflete exclusivamente sua unidade systemd, NÃO confirma sincronização concluída; `last_observed_at` fica `null` pois não existe instrumento confiável de última sincronização. Transferências ficam explicitamente `not_instrumented`.

## Coleta, cache e limites

Reutiliza `fo_monitor.fetch('oracle-vps', timeout=25)`, sem alterar o monitor. O SSH existente usa BatchMode e ConnectTimeout=8. A coleta existente consulta API FO, SQLite em modo somente leitura, estado das unidades e disco. Há inevitavelmente dados privados na memória temporária do coletor: a fronteira de publicação é a projeção escalar, não a saída bruta do monitor.

Cache apenas em memória, compartilhado e protegido por lock: próxima tentativa só após pelo menos 20 segundos do término da anterior, inclusive falhas. Requests concorrentes não multiplicam SSH. Não há polling em background, persistência, escrita em bancos, endpoints de comando, reinícios, instalação de serviço, leitura de secrets/env ou alteração de VPS/FO/Anki/n8n. Encerrar o processo local não interfere nos serviços remotos.

## Futuro backend VPS (não implementado)

Uma migração futura deve manter a mesma projeção e contrato, trocar somente o adaptador de coleta por leitura local explicitamente autorizada e definir autenticação, autorização, TLS, rate limiting, observabilidade sanitizada e política de retenção. Loopback e verificação de Host/Origin não substituem autenticação para publicação remota. `http.server` é uma opção de desenvolvimento local, não servidor de produção. Nenhum deploy, serviço permanente, template nginx ou abertura pública faz parte desta entrega.

## Verificação

Testes stdlib cobrem projeção contra URLs privadas aninhadas, ausências/null, números não finitos e progresso, mapeamento escalar, timeout de 25 s do adaptador, falha sem cache vencido, throttling de falhas, HTTP real em porta efêmera loopback, métodos/rotas/Host/Origin e respostas 503 sanitizadas. Fixtures sintéticas não são métricas reais.

Uma coleta real foi executada em 2026-11-07T17:58:24Z, imprimindo somente a projeção: transcrições 12 concluídas, 2999 na fila, 3 em revisão, 1 em processamento; materiais 174; páginas 8457, liberadas 7912, bloqueadas 545; fontes disponíveis 3002, objetos indexados 2253, fontes pendentes 13. São uma observação pontual, não valores fixos do produto.
