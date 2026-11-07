# Study Hub — contrato visual vinculante

Inspeção: 07/11/2026. Origem obrigatória: https://www.figma.com/community/file/1531598093643920564/student-dashboard-lms-application. Autora: Sakshi Parashar.

## Identidade e acesso legítimo

O Community retornou 403 no Chromium automatizado. Safari autenticado abriu a página original e revelou que o recurso é **Figma Make**, não um Design tradicional de frames. Remix criado/confirmado na conta do proprietário, também confirmado pelo proprietário em mensagem:

https://www.figma.com/make/kd36an23RU8hgKDxF55sTR/Student-Dashboard-LMS-Application--Community-?t=jzVKu5fXZMnONsEo-6

A URL `/make/kd36an23RU8hgKDxF55sTR/` é real; não existe `/design/`/node-id inspecionado nesta sessão. Preview original ligado pelo iframe e pelo botão Visualizar no Community: https://poll-meta-32981667.figma.site/ . Bundle original observado: `d8788dfa-95a6-4bc1-a119-944ff1f39245`, criação `2025-07-28 10:17:03 UTC`.

MCP desktop em `http://127.0.0.1:3845/mcp`: initialize/tools-list responderam (Figma Dev Mode MCP Server 1.0.0). O servidor exige aba Design/FigJam ativa; get_metadata declara que não suporta Make, get_screenshot lista Design/FigJam/Slides. Leitura do recurso de orientação respondeu que só está disponível com Design/FigJam ativo. Não usar a seleção do projeto IGD/Sales como referência Study Hub. A evidência visual desta sessão vem do preview **da própria autora**, não de frames fictícios.

## Inventário observado

- Dashboard inicial: header de boas-vindas + badge de curso, quatro cards-resumo, título/descrição da seção, cinco cards de disciplinas em grid 2 colunas no desktop.
- Materiais da disciplina: botão voltar, título/ícone, quatro resumos, informações do curso e acordeões de módulos.
- Mobile: header empilhado, resumos e disciplinas em uma coluna. Captura real a 390×844.
- Não há sidebar, shell de navegação lateral, avatar de aplicação ou ilustrações no Dashboard original. A barra Figma/Remix pertence ao hospedeiro, não ao produto; não copiar como navegação Study Hub.
- Estados inspecionados: botão de acesso a materiais e retorno, layout desktop/mobile, hover das disciplinas no CSS. Estados de erro/offline do domínio são adaptações funcionais explícitas.

## Tokens e dimensões medidos (não estimados)

Ver `evidence/original-computed-desktop.json` e screenshots originais. Font family system: ui-sans-serif, system-ui, sans-serif, Apple/Segoe/Noto emoji; nenhuma @font-face/import de fonte no stylesheet observado. Root efetivo 14px (não assumir Tailwind 16px).

- Fundo `oklch(0.985 0.002 247.839)`; cards branco; texto `oklch(0.145 0 0)`; heading `oklch(0.21 0.034 264.665)`; secundário `oklch(0.446 0.03 256.802)`; muted `oklch(0.551 0.027 264.364)`.
- Primary `#030213`; borda preto 10%; ring `oklch(.708 0 0)`; progress track primary 20%.
- Blue `oklch(0.623 0.214 259.815)`; green `oklch(0.723 0.219 149.579)`; purple `oklch(0.627 0.265 303.9)`; orange `oklch(0.705 0.213 47.604)`; red `oklch(0.637 0.237 25.331)`.
- Conteúdo máximo 1120px, padding externo14px. Header/sections gap21px. Resumos gap14px. Grid de cards gap21px.
- Heading principal26.25px/31.5px peso700; seção21px/28px peso700; título card15.75px/24.5px peso400; body14px/21px; small12.25px/17.5px; micro10.5px/14px.
- Card raio12.75px, border1px, sem sombra em repouso. Header padding21px 21px 0, content21px, gap21px. Ícone quadrado42px, raio8.75px, glyph21px; resumo glyph28px.
- Badge/button raio6.75px; button31.5px de altura, fonte12.25px/17.5px peso500; gap7px; padding7px 10.5px. Progress7px (resumo3.5px), radius full.
- Hover card scale1.02 e shadow-lg, transition150ms. Focus ring3px. Redução de movimento na implementação é adaptação de acessibilidade.
- Breakpoints originais observados no CSS: 40rem,48rem,64rem; grid resumo md48rem=768 CSS px, disciplinas lg64rem=1024 CSS px (media rem usa inicial16px, não root14px).

## Adaptação de conteúdo, não de estilo

Header Study Hub e observação temporal substituem identidade fictícia do estudante. Quatro resumos: aula em transcrição, concluídas, fila e revisão. Cards operacionais: transcrições, PDFs, vídeos, OneDrive e armazenamento; extensões usam os mesmos tokens/componentes. Sem nomes pessoais/IDs de aula nem texto privado. Botões abrem detalhes locais somente leitura; não prometem biblioteca já construída. Unknown=null/Indisponível; download não recebe percentual por fontes/objetos.

## Licenças e atribuição

Community original exibe explicitamente **CC BY 4.0** e link https://creativecommons.org/licenses/by/4.0/ . Atribuir “Adaptado de Student Dashboard LMS Application, Sakshi Parashar (Figma Community), CC BY 4.0; conteúdo e integração modificados para Study Hub”, com links para original e licença, no README/THIRD_PARTY_NOTICES e interface. Licença do layout não prova licenças de terceiros: ícones originais identificados pelas classes `lucide`, implementar via lucide-react e conservar licença ISC do pacote. Fontes são de sistema (não redistribuídas), emojis dependem do sistema. Não houve imagem/ilustração externa de conteúdo no Dashboard; não importar assets de outros templates.

## Homologação

Comparar screenshots reais originais (desktop1440×1000 e mobile390×844) e implementação no mesmo viewport/browser. Descontar barra Figma48px apenas na análise de geometria, nunca exibir screenshot como UI. Comparar largura/gaps/cores/tipos/radius; conteúdo em português altera quebras/alturas e deve ser registrado. Não alegar pixel-perfect, nem inventário de frames/layers via MCP; design inspecionado pelo preview funcional original.

Homologação realizada no Chromium: `evidence/visual-measurement-comparison.json` registra **10/10 medidas selecionadas iguais**: largura do conteúdo1120px, h1/h2, dimensões269.5×93px e raio12.75px do resumo, header de card68.25px, título15.75px, botão31.5px/raio6.75px. Isso não é score global de fidelidade nem diff pixel-perfect. Screenshots locais desktop/mobile com dados reais salvos; mobile390px com scrollWidth375px (scrollbar15px), sem overflow horizontal. Detalhes de PDFs abriram/fecharam no browser e exibiram somente contagem de páginas bloqueadas, nenhum texto privado. Interface local tem zero iframes.

Diferenças explícitas: barra Figma/Remix48px não replicada; linha operacional adicional17.5px mais composição de gaps desloca conteúdo abaixo do header cerca de18px versus a área de aplicação original; textos/quantidades/card bodies mudam para dados FO; OneDrive/armazenamento usam ícones Lucide sem ilustrações externas; detalhes locais substituem navegação para módulos não implementados. Tipografia/tokens/grid foram medidos, mas todos os estados interativos e glyphs exatos entre versões Lucide ainda não têm comparação pixel-a-pixel.
