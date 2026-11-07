# Study Hub Web — Sprint 1

Aplicação React/TypeScript/Vite isolada; somente leitura. Não contém dados de demonstração em runtime. Testes usam fixtures sintéticas identificadas. Não substitui nem modifica Anki/FO/n8n.

## Preview local

Na raiz do repositório, em um terminal:

    python3 ops/study-hub/web/observer.py

Em outro terminal:

    cd apps/study-hub-web
    npm ci --ignore-scripts
    npm run dev

Abrir http://127.0.0.1:3400 . Backend somente em 127.0.0.1:3401; Vite encaminha /api/dashboard, nunca /fo ou SQLite. O backend usa o alias SSH existente oracle-vps; indisponibilidade mostra estado explícito, não dados inventados. Encerrar com Ctrl+C em cada terminal; não afeta produção.

O preview não é instalado como serviço e não é público. Não usar --host 0.0.0.0. O comando npm run preview serve apenas dist estático, sem proxy de API; usar npm run dev para preview integrado. Build: npm run build. Testes direcionados: npm test. Node compatível com os engines de Vite8/Vitest5 (testado26.9.0).

## Estrutura

src/App.tsx: shell e Dashboard observacional; src/components.tsx: Summary, MetricCard e Progress acessível; src/api.ts: contrato/load de snapshot; src/styles.css: tokens e componentes medidos no original; src/App.test.tsx: loading, offline, stale, privacidade e detalhes; vite.config.ts: loopback/porta fixa e proxy local.

Contrato visual e screenshots: ../../docs/design/study-hub-figma-contract.md . Contrato backend: ../../docs/design/study-hub-observer-contract.md . Vhost futuro (NÃO instalado): ../../ops/study-hub/web/README.md .

## Escopo visual

Original identificado como Figma Make; sem sidebar no Dashboard. Conteúdo adaptado para métricas operacionais; sem copiar a barra de hospedagem Figma. Mesmo sistema de dimensões, cores, tipografia, badges, resumos e cards; diferenças de conteúdo/estados operacionais documentadas. Não alegar pixel-perfect de todos os estados: materiais e biblioteca não implementados neste sprint. Interface não é screenshot nem iframe do template.

## Dados e limites

Polling20s com requisições não sobrepostas e timeout30s, stale após60s. Erro mantém snapshot anterior com alerta e horário; ausência não vira0. Não há percentual de download: fontes e objetos são contagens distintas. Estado de timer não comprova conclusão de sincronização. Sem conteúdo de transcrição/review, PDFs originais, nomes pessoais, cookies ou URLs privadas.

Produção futura requer backend observacional próprio na VPS (não reutilizar este wrapper SSH como serviço sem projeto operacional), autenticação HTTPS, DNS aprovado e smoke/rollback. Nenhum destes passos é executado por npm run dev/build.

## Atribuição

Adaptado de Student Dashboard LMS Application, Sakshi Parashar, Figma Community1531598093643920564, CC BY4.0. Conteúdo e integração modificados para Study Hub. Ver THIRD_PARTY_NOTICES.md e atribuição na interface.
