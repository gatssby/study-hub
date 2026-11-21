# Federal Online — Catálogo Completo de Aulas (Study Hub)

Inventário somente-leitura gerado a partir do SQLite de produção corrigido e dos snapshots verificados do catálogo.

- Aulas canônicas atuais: **3027**
- Cursos canônicos: **9** | Disciplinas: **102** | Módulos: **140**
- Registros históricos/aliases (present=0): **371**
- Transcrições validadas (versão atual): **115**
- Estados de transcrição: {'queued': 2852, 'done': 115, 'processing': 1, 'review': 50, 'none': 9}
- Aulas com metadados incompletos: **0** | Sem fonte de vídeo verificada: **22**
- Disciplinas excluídas (Inglês/Espanhol): ['Espanhol', 'Inglês'] | aulas nessas disciplinas: **159**
- Materiais PDF (nível disciplina, não vinculados por aula): **172** de 182 materiais
- Aliases verificados retirados: **38** | fallback remoto histórico: **277** | ausentes do catálogo: **56**

## Métricas por curso

| Curso | Aulas |
|---|---|
| Extensivo UFPR 2026 | 1206 |
| Semiextensivo UFPR 2026 | 839 |
| Intensivo UFPR 2026 | 424 |
| Simulados e Resolução de Provas | 422 |
| Materiais exclusivos de medicina | 55 |
| Ciências Básica | 30 |
| Matemática Básica | 25 |
| Redação UFPR 2026 | 24 |
| Simuladão UFPR #01 - Gratuito | 2 |

## Métricas por disciplina

| Disciplina | Aulas |
|---|---|
| História I | 118 |
| História II | 117 |
| Aprofundamento - Extras | 116 |
| Sociologia UFPR | 96 |
| Matemática III | 94 |
| Português II | 94 |
| Matemática II | 88 |
| Física III | 83 |
| Inglês | 80 |
| Biologia I | 80 |
| Biologia II | 80 |
| Biologia III | 80 |
| Física I | 80 |
| Física II | 80 |
| Matemática I | 80 |
| Espanhol | 79 |
| Filosofia UFPR | 79 |
| Química | 67 |
| Biologia | 63 |
| Geografia I | 61 |
| Geografia II | 60 |
| Química I | 60 |
| Química II | 60 |
| Química III | 60 |
| Português I | 58 |
| Redação UFPR | 52 |
| Português | 51 |
| Matemática | 46 |
| Física | 43 |
| Geografia | 40 |
| Geografia III | 40 |
| Literatura UFPR | 36 |
| História | 31 |
| Biologia - Exercícios | 30 |
| Biologia - Teoria | 30 |
| Física - Exercícios | 30 |
| Física - Teoria | 30 |
| Matemática - Exercícios | 30 |
| Matemática - Teoria | 30 |
| Química - Exercícios | 30 |
| Química - Teoria | 30 |
| Curso de Ciências Básica | 30 |
| Curso de Matemática Básica | 25 |
| História - Exercícios | 25 |
| História - Teoria | 25 |
| Curso de Redação | 24 |
| Literatura Geral | 21 |
| Sociologia Geral | 21 |
| Filosofia Geral | 20 |
| Geografia - Exercícios | 20 |
| Geografia - Teoria | 20 |
| História Geral - Extras | 17 |
| Anki - Flashcards | 15 |
| História do Brasil - Extras | 12 |
| Português - Exercícios | 12 |
| Português - Teoria | 12 |
| Literatura - Exercícios | 8 |
| Literatura - Teoria | 8 |
| Espanhol - Exercícios | 5 |
| Espanhol - Teoria | 5 |
| Filosofia - Exercícios | 5 |
| Filosofia - Teoria | 5 |
| Inglês - Exercícios | 5 |
| Inglês - Teoria | 5 |
| Sociologia - Exercícios | 5 |
| Sociologia - Teoria | 5 |
| Redação | 4 |
| II - Momento da prova | 4 |
| Caderno de erros | 3 |
| Introdução | 3 |
| Método Pomodoro | 3 |
| Método de Cornell | 3 |
| Método de Feynman | 3 |
| Simulado 10: 27 a 29 de ago | 3 |
| Simulado 11: 03 a 05 de set | 3 |
| Simulado 12: 10 a 12 de set | 3 |
| Simulado 1: 25 a 27 de jun | 3 |
| Sociologia | 2 |
| Reprodução - Foco ENEM - Extras | 2 |
| I - Período de estudos | 2 |
| I - Rotina | 2 |
| II - Descanso e motivação | 2 |
| II - Simulados e Redações | 2 |
| III - Pós-prova | 2 |
| Simulado 14: 24 a 26 de set | 2 |
| Simulado 15: 01 a 03 de out | 2 |
| Simulado 17: 15 a 17 de out | 2 |
| Simulado 18: 22 a 24 de out | 2 |
| Simulado 2: 02 a 04 de jul | 2 |
| Simulado 3: 09 a 11 de jul | 2 |
| Simulado 4: 16 a 18 de jul | 2 |
| Simulado 5: 23 a 25 de jul | 2 |
| Simulado 6: 30 de jul a 01 de ago | 2 |
| Simulado 7: 06 a 08 de ago | 2 |
| Simulado 8: 13 a 15 de ago | 2 |
| Simulado 9: 20 a 22 de ago | 2 |
| Simuladão UFPR #01 | 2 |
| Dicas finais | 1 |
| I - Pré-prova | 1 |
| III - Foco | 1 |
| III - Frustração da reprovação | 1 |
| Introdução ao material | 1 |

## Notas de completude e proveniência

- `order` vem do campo `ordem` do snapshot do catálogo quando verificável; `null` caso contrário.
- `pdf_count` é `null`: os materiais são de nível disciplina (module='disciplina'), sem vínculo por aula no banco.
- `duration_s` é `null` para aliases remotos protegidos sem duração observada.
- Proveniência: `portal_catalog` (catálogo portal) ou `metadata_recovery_backfill` (alias remoto protegido com metadados canônicos recuperados).
- Caminhos privados do OneDrive, URLs assinadas e credenciais NÃO são exportados; rótulos path-like são mascarados.

## Índice hierárquico completo (Curso → Disciplina → Frente → Módulo → Aula)


### Ciências Básica


#### Curso de Ciências Básica


##### Curso de Ciências Básica


**Curso de Ciências Básica** (30 aulas)

-   1. O que é ciências? — `fo_ff9f28b297133516` ✓validada
-   3. Grandezas e unidades — `fo_ebc07c36fd67ffb7` ✓validada
-   4. Grandezas da cinemática — `fo_40f898e1a4ad480e` ✓validada
-   5. Estudo dos gráficos I — `fo_2dcc326b0a289b3d` ✓validada
-   6. Estudo dos gráficos II — `fo_31bed8804ecefca9` ✓validada
-   7. Proporção direta — `fo_672ccda5deeabbf6` ✓validada
-   8. Manipulação algébrica — `fo_b4b3b59f97a77b04` ✓validada
-   9. Particulas fundamentais, átomos, Moléculas e representações — `fo_c954d49f33abf522` ✓validada
-  10. Carga elétrica — `fo_0d859dac2872c874` ✓validada
-  11. Número de mols, massa molar e massa molecular — `fo_8afdd5af6dc414ac`
-  12. Temperatura e calor — `fo_02a3f8b8b1e70ca1`
-  13. Aula extra - Vetores I — `fo_17815cd55ae483a0`
-  14. Aula extra - Matemática para vetores I — `fo_18a5f8d850bca4f5`
-  15. Aula extra - Matemática para vetores II — `fo_34ce202007e4f9ca`
-  16. Aula extra - Vetores II — `fo_9f2c15bb2ef4b097`
-  17. Aula extra - Vetores II — `fo_1187542fcfd1eff8`
-  18. Aula extra - Vetores III — `fo_95deba6e5aca05d4`
-  19. Aula extra - Vetores IV — `fo_9c26e8184c8e8df6`
-  20. Aula extra - Vetores V — `fo_3ff32edc4d315455`
-  21. Aula extra - Processos de Eletrização — `fo_df0e57b73a6a517a`
-  22. Aula extra - íons — `fo_c148ce39fbca4add`
-  23. Aula extra - Força Elétrica — `fo_5555f666f4b019ff`
-  24. Aula extra - Campo Elétrico — `fo_b8a8682a7d550fb7`
-  25. Aula extra - Relação entre Força elétrica e Campo Elétrico — `fo_9ea14047994b13cf`
-  26. Aula extra - Energia Potencial Elétrica — `fo_9cb29e32598922a8`
-  27. Aula extra - Potencial Elétrico — `fo_ece7fb11b78d0b3f`
-   - Aula extra - Processos de Eletrização — `fo_66d8bf00855e01d6` ✓validada
-   - Aula extra - Processos de Eletrização — `fo_9b85e54ea9717249` ✓validada
-   - Aula extra - Vetores IV — `fo_3f92db67195e2bbf` ✓validada
-   - Aula extra - Vetores IV — `fo_c94695b9fee33ecb` ✓validada

### Extensivo UFPR 2026


#### Anki - Flashcards


##### Anki - Flashcards


**Vídeos** (5 aulas)

-   1. Introdução ao Anki — `fo_d52201b87f2b6f00`
-   2. Como baixar o Anki — `fo_cb6e8cc26f3cb154`
-   3. Como funcionam os Flashcards? — `fo_b667f517bd3611b1`
-   4. Como fazer os seus próprios Flashcards? — `fo_ea6dd2d1a95523b9`
-   5. Como baixar os Cards do FO no Anki — `fo_274c41bf83219112`

#### Aprofundamento - Extras


##### Aprofundamento


**Aprofundamento** (116 aulas)

-   1. Análises gráficas e conceitos matemáticos básicos — `fo_18948c4157730124`
-   1. Cinemática I — `fo_60eb517627450ed9`
-   1. Imunologia — `fo_1f746fc822484c5f`
-   1. Semelhança — `fo_c5fdd42c3226aac1`
-   2. Cinemática II — `fo_d3d60076657bf20d`
-   2. Entropia e Energia Livre de Gibbs — `fo_254e54f9a1eb6678`
-   2. Epidemiologia — `fo_b8177478e82fcc5f`
-   2. Teorema de Pitágoras — `fo_6a6fb9bd80a83604`
-   3. Círculos — `fo_7ac40c8fdfaa6feb`
-   3. Doenças com transmissão pelo ar — `fo_c39382f7984fa73f`
-   3. Leis de Newton — `fo_4309a6777aa14faa`
-   3. Termoquímica e Estequiometria — `fo_c1aacb86cbf09897`
-   4. Doenças com transmissão vertical — `fo_f78aa77dd6678c27`
-   4. Estática de um ponto material — `fo_0084bb8e9582a052`
-   4. Gases — `fo_08bd20b449b63bae`
-   4. Relação entre retas e circunferência — `fo_c6f5614a703cdc5d`
-   5. Cálculos de Concentração — `fo_14953634f3c414df`
-   5. Doenças transmitidas pelo Aedes aegypti — `fo_498e7e8b820d956c`
-   5. Estática de um corpo extenso — `fo_791e49efd02f372d`
-   5. Prismas — `fo_9639587c49d22c50`
-   6. Balanceamento por oxirredução — `fo_ed98cd50f157e543`
-   6. Cilindros — `fo_40c6ac563ebcab53`
-   6. Doenças com ciclo oral-fecal — `fo_d21969fd4c4569b0`
-   6. Trabalho mecânico e potência mecânica — `fo_3ab70e5bd279df49`
-   7. Cones e troncos de cone — `fo_3cf4e1aa5739ec2d`
-   7. Doenças com reservatório urbano — `fo_c481dc0df8038080`
-   7. Pilhas — `fo_adc34c64c2cbb67b`
-   7. Tipos de energias e conservação de energia — `fo_19f6b105ae88f29a`
-   8. Ciclo do carbono — `fo_da206ad28ce2629c`
-   8. Cinemática e Dinâmica Circular — `fo_26c2f39fdec06ee6`
-   8. Eletrólise — `fo_83c2bf100f745a9b`
-   8. Pirâmides e troncos de pirâmide — `fo_0c6d90077f77ec19`
-   9. Ciclo do nitrogênio — `fo_f338882db370920f`
-   9. Cinética Química — `fo_366b289485c81338`
-   9. Esferas — `fo_137874f73d410db7`
-   9. Gravitação — `fo_90bc76aaf7f64967`
-  10. Equilíbrio Químico — `fo_5f5b4b54b45666c5`
-  10. Estatística — `fo_1aa389e3f9c1b6d0`
-  10. Hidrostática — `fo_6d038ddf60b048cd`
-  10. Polinização e dispersão — `fo_0c38d338ba9b243c`
-  11. Competição e predação — `fo_33272de28e40756f`
-  11. Equilíbrio Iônico — `fo_61b866b6f03304f7`
-  11. Movimento Harmônico Simples (MHS) E Ondas estacionárias — `fo_6621cfec8db7d772`
-  11. Produto de matrizes — `fo_d6614e2c802e6e42`
-  12. Acústica — `fo_ba528eb59cd2c4f7`
-  12. Fluxo de matéria e energia — `fo_58b09aee536d4d7c`
-  12. Matriz inversa — `fo_e435fd7268b66d44`
-  12. Sistema tampão — `fo_bf3af83ddd77061f`
-  13. Biologia da conservação — `fo_c19e75744896973b`
-  13. Calorimetria — `fo_1db2ee48b702d8f8`
-  13. Determinante de matrizes — `fo_b374ef0a88f6322d`
-  13. Propriedades Coligativas — `fo_c1a06b34aa02e444`
-  14. Acidez e basicidade - compostos orgânicos — `fo_fb3f5529d4e3cb66`
-  14. Estudo da reta — `fo_63d7df2c4ebc3e1d`
-  14. Gases ideais — `fo_8c16029921426cd9`
-  14. Teoria sintética e especiação — `fo_e694fc567e447595`
-  15. Estudo da circunferência — `fo_b85666ea43d691c7`
-  15. Reação de Neutralização — `fo_d1092cce46dd168f`
-  15. Termodinâmica I — `fo_e1aee3f71b8f21bb`
-  15. Tipos de seleção natural — `fo_fdfac45ed6398572`
-  16. Divisão de polinômios — `fo_0826572c28efa2a6`
-  16. Forças Intermoleculares — `fo_80c306c7b15f348e`
-  16. Primeira Lei de Mendel — `fo_3c81eb86c20422d6`
-  16. Termodinâmica II — `fo_5bd5ea2b9b35ef91`
-  17. Raízes polinomiais — `fo_c47ebc543aa7a936`
-  17. Segunda Lei de Mendel — `fo_88531581a834d24c`
-  17. Separação de misturas — `fo_6d6b906a753357e0`
-  17. Óptica I — `fo_ad2f3851bb067a70`
-  18. Chuva ácida e aquecimento Global — `fo_0309b0dac15ed8cf`
-  18. Inequações — `fo_8c20f27d2030069f`
-  18. Método da linha bifurcada — `fo_adf6d4899ac3996c`
-  18. Óptica II — `fo_89bfcf9649c1401b`
-  19. Eletrostática I — `fo_6c71f5c50cc64397`
-  19. Função composta e inversa — `fo_fe63b38774259f5d`
-  19. Herança sexual e determinação do sexo em mamíferos — `fo_c071b7c1901bbc57`
-  19. Tendências Periódicas — `fo_574572d705863086`
-  20. DNA, cromatina e cromossomos — `fo_73c6f15e08a3eb16`
-  20. Eletrostática II — `fo_885ec9505bb6ff39`
-  20. Equação modular — `fo_f10b9dbc6868240c`
-  20. Geometria Molecular — `fo_a41ad7bbb3079208`
-  21. Circuitos elétricos I — `fo_1256baa92afb5e9d`
-  21. Determinação de formulas químicas — `fo_711e829c405dc584`
-  21. Logarítmo — `fo_4a4e34b8ff6e10f1`
-  21. Replicação e Mutação gênica — `fo_26ed7429c42a94d8`
-  22. Circuitos elétricos II — `fo_ecb313bf28d96655`
-  22. Estrutura de Lewis — `fo_4c7e80f5e69472d7`
-  22. Gráfico de funções afim, quadrática e modular — `fo_3aa2dae3ddf6dde2`
-  22. Transcrição — `fo_fe7ff55df3f79f85`
-  23. Aromáticidade — `fo_9341f00a3e0dde48`
-  23. Circuitos elétricos III — `fo_c3a0d4b0207225ee`
-  23. Gráfico de funções exponencial e logarítmica — `fo_04d27adf86a0428d`
-  23. Tradução — `fo_993c9f80a70fc18d`
-  24. Força magnética e Campo magnético — `fo_34cfa297072f025f`
-  24. Função trigonométrica — `fo_4d77dbe7d2dae479`
-  24. Isomeria Geométrica — `fo_06662f0e63986779`
-  24. Regulação gênica — `fo_c70d44ee0a948c1e`
-  25. Carga formal e Isomeria Plana — `fo_17615afed3a23dca`
-  25. Homeostase — `fo_e66fd6327dc10c17`
-  25. Identidades trigonométricas — `fo_751c70f9fa715ed3`
-  25. Lei de Faraday-Lenz — `fo_cfd99ff8f6725c49`
-  26. Ondas eletromagnéticas — `fo_f8f4c4bfbe924717`
-  26. Probabilidade condicional — `fo_de924bfef1470dc2`
-  26. Reações de Substituição — `fo_69a4d7bbd30ac6d6`
-  26. Sistema digestório e digestão comparada — `fo_3fb8f337475a6cdc`
-  27. Circulação comparada e homeotermia — `fo_42b0eb5edfbbf2ba`
-  27. Dualidade Onda-Partícula + Efeito fotoelétrico — `fo_e39bbc31c514cd29`
-  27. Números Complexos — `fo_2ceedbb3f1d52cbc`
-  27. Reações de Oxidação — `fo_cb5061771715b346`
-  28. Excreção comparada — `fo_c341f4603a472946`
-  28. Modelo atômico de Bohr — `fo_7e467ef27f406c12`
-  28. Números complexos: forma trigonométrica — `fo_caa80acbcb1d4046`
-  28. Reação de Eliminação — `fo_795061f5ae784d5c`
-  29. Biomoléculas e Polímeros naturais — `fo_ee051127ce4ba151`
-  29. Cladogramas de plantas e animais — `fo_448a07cb9e853b04`
-  29. Relatividade — `fo_44757ae8361a6a25`
-  29. Sistema Linear: Classificação — `fo_9bc65e9df1590777`

#### Biologia I


##### Biologia I


**Biologia I** (40 aulas)

-   1. Água e Sais minerais — `fo_ea356c6ac17a0e3b`
-   2. Vitaminas e Doenças de carência — `fo_c2aa86036cd2a62d`
-   3. Carboidratos e Lipídios — `fo_1fcd194987a81d26`
-   4. Proteínas e Enzimas — `fo_cf5df5b0962d57cb`
-   5. Membrana plasmática — `fo_9e09046888879cc0`
-   6. Transporte através da membrana — `fo_598c93b66bbace4f`
-   7. Citoplasma — `fo_c32118eb4e778fb6`
-   8. Respiração celular — `fo_899fff6cdbb68e4f`
-   9. Núcleo — `fo_12bd2064b8667103`
-  10. Divisão celular — `fo_1abf592ddaab7a0c`
-  11. Tecido epitelial — `fo_1ed12d26cff2c9f8`
-  12. Tecido conjuntivo I — `fo_44fa96a575602d2c`
-  13. Tecido conjuntivo II — `fo_b3a6465c89fe3aae`
-  14. Tecido muscular — `fo_307d83438efb71d6`
-  15. Tecido nervoso — `fo_a0dc0d58f874e872`
-  16. Sistema nervoso — `fo_e4dd7b00f7dd41cf`
-  17. Sistema digestório — `fo_7c20135fdd890095`
-  18. Sistema respiratório — `fo_9a6ecd00524b75f9`
-  19. Sistema circulatório — `fo_9b980293ee0cdda8`
-  20. Sistema excretor — `fo_37982d4c43fe7e88`
-  21. Sistema endócrino — `fo_471926411fd34026`
-  22. Sistema reprodutor — `fo_b65101728a6b83d5`
-  23. Ciclo menstrual — `fo_9bf0b816e443121e`
-  24. Tipos de ovos e Clivagem — `fo_99ea6c8f3955a981`
-  25. Desenvolvimento embrionário — `fo_21fd4985e207c5df`
-  26. Anexos embrionários — `fo_e8330a194dd320bd`
-  27. Reino Animal e Filo Porifera — `fo_aa2e72796f8be9a5`
-  28. Filo Cnidaria — `fo_5334bcbff062ec64`
-  29. Filo Platyhelminthes e Filo Nematoda — `fo_5024624915fb28b7`
-  30. Filo Mollusca — `fo_65b8360d8f006ca9`
-  31. Filo Annelida — `fo_3a3d766a92dec321`
-  32. Filo Arthropoda — `fo_246013762117f561`
-  33. Filo Echinodermata — `fo_bc6a2f7a6dd0c831`
-  34. Filo Chordata e Peixes — `fo_df30f8f90d6c5d82`
-  35. Anfíbios — `fo_49021ec259b74475`
-  36. Répteis — `fo_5abf41643a3f0e5e`
-  37. Aves — `fo_3c4ebdb16ff2886b`
-  38. Mamíferos — `fo_3dbf707a220b62a4`
-  39. Digestão e Excreção comparada — `fo_e4e02b4359f406af`
-  40. Circulação e Respiração comparada — `fo_b0c334f5388a2a13`

#### Biologia II


##### Biologia II


**Biologia II** (40 aulas)

-   1. Taxonomia — `fo_deb630b786f261a9`
-   2. Vírus — `fo_9ab8c3d06bb18b05`
-   3. Reino Monera — `fo_a761d5bcf6d1754c`
-   4. Reino Protista — `fo_d4a92d4bd6dd7b75`
-   5. Algas — `fo_9bf8da22075500dd`
-   6. Reino Fungi — `fo_bdfe1d5233630123`
-   7. Reino Plantae — `fo_d74fc5c8fc8d491a`
-   8. Briófitas — `fo_74fde03466b7f92b`
-   9. Pteridófitas — `fo_08234f5631826046`
-  10. Gimnospermas — `fo_587d0f807e164878`
-  11. Angiospermas — `fo_1fbe90c3e7f4ddec`
-  12. Reprodução das Angiospermas — `fo_2c9d46c6b5d8ccea`
-  13. Histologia vegetal — `fo_78d5b1ac9a804687`
-  14. Tecidos de revestimento e Sustentação — `fo_fba622bfc1161806`
-  15. Tecidos de armazenamento e Secreção — `fo_535e9ffba126d795`
-  16. Tecidos condutores de seiva — `fo_2393bf81cda67a22`
-  17. Raiz — `fo_7e08469c94a7b523`
-  18. Caule — `fo_ae3eedfaa5837d07`
-  19. Folha — `fo_93a137ab8948fc34`
-  20. Fruto — `fo_cc37ff313d5637d6`
-  21. Nutrição e Absorção — `fo_cace57c227e58a0e`
-  22. Transporte de seiva — `fo_2f4b426a04ba36f0`
-  23. Fotossíntese I — `fo_0e1759963895510d`
-  24. Fotossíntese II — `fo_c61f678ec57cc507`
-  25. Ponto de compensação fótica — `fo_91d5423e496e88a3`
-  26. Hormônios vegetais I — `fo_f9ca729e1fd3e967`
-  27. Hormônios vegetais II — `fo_4e45040cda30cee7`
-  28. Fotoperiodismo e Movimentos vegetais — `fo_a947873c7e0b844d`
-  29. Cultivo de plantas — `fo_33918f4ce7c6f4da`
-  30. Parasitologia — `fo_c4038f06ddf7e12d`
-  31. Viroses — `fo_59d6aed6c794fe07`
-  32. Bacterioses — `fo_48256f510716bad7`
-  33. Protozooses I — `fo_a0fbed37cccdd1b9`
-  34. Protozooses II — `fo_32d0059eb393567a`
-  35. Verminoses I — `fo_f0fe81c9d69620ab`
-  36. Verminoses II — `fo_dccf91a1bda39cc0`
-  37. Sistema imune — `fo_97d3e97e7c4ccb56`
-  38. Vacinas — `fo_972556d0f3b81144`
-  39. ISTs — `fo_2e6fbeca4ea87426`
-  40. Métodos contraceptivos — `fo_2d50f035a37b2b85`

#### Biologia III


##### Biologia III


**Biologia III** (40 aulas)

-   1. Origem da vida — `fo_6035458e86e7db4b`
-   2. Teorias evolutivas — `fo_65b80c004c53fe9e`
-   3. Teoria sintética da evolução — `fo_fad752dd289cc358`
-   4. Tipos de seleção natural — `fo_4fc911d8652c2d5d`
-   5. Evidências evolutivas e Especiação — `fo_bb407c41cae91060`
-   6. Introdução à ecologia — `fo_790d6e03f9d33442`
-   7. Cadeia e Teia alimentar — `fo_dedac42f00d8cc43`
-   8. Pirâmides ecológicas e Produtividade — `fo_202773e5b211df16`
-   9. Ciclos biogeoquímicos — `fo_5112ee7ca89e80b8`
-  10. Relações ecológicas I — `fo_f6b4142aec372215`
-  11. Relações ecológicas II — `fo_0fda7717ddba7f8c`
-  12. Dinâmica de populações — `fo_e34d8ce89a987532`
-  13. Sucessão ecológica — `fo_e5e316bf301bb24e`
-  14. Biomas — `fo_bce78bcd92260648`
-  15. Biomas brasileiros — `fo_872fdd70196b1c29`
-  16. Ecossistemas aquáticos — `fo_c392485df9802c91`
-  17. Poluição atmosférica — `fo_aa9f57c46bfc0476`
-  18. Poluição da água — `fo_e8e1f2d18da79351`
-  19. Espécies exóticas e Extinção de espécies — `fo_fefbc3f854fd76d5`
-  20. Introdução à genética — `fo_ade456b4dd0421a1`
-  21. Primeira lei de Mendel — `fo_bf073a09229243c3`
-  22. Extensões do Mendelismo I — `fo_4138dc7576d42783`
-  23. Extensões do Mendelismo II — `fo_09b45bebc59a1ca7`
-  24. Tipagem sanguínea — `fo_5d1393ca46a0298e`
-  25. Segunda lei de Mendel — `fo_bf2ac3fc3f352c6e`
-  26. Interação gênica — `fo_8e1cab61d36696bf`
-  27. Herança quantitativa — `fo_a25093237526ebaa`
-  28. Herança sexual — `fo_78fe48370ccce15f`
-  29. Alterações cromossômicas — `fo_966bdf708dced15d`
-  30. Ligação gênica — `fo_6dc0ff0d18d464d2`
-  31. Genética de populações — `fo_b4a76182208eceff`
-  32. Ácidos nucleicos — `fo_43e5971562212c5c`
-  33. Biologia molecular I — `fo_9079a59ac2667865`
-  34. Biologia molecular II — `fo_fb0f75c400bef7a1`
-  35. Expressão gênica — `fo_f18d0b00cd338ac1`
-  36. Melhoramento genético — `fo_22ccd59c45cb0cbd`
-  37. Biotecnologia I — `fo_d5f1660cd1231d57`
-  38. Biotecnologia II — `fo_82c97b73458013ac`
-  39. Biotecnologia III — `fo_a07dae5fbb2fdd0e`
-  40. Câncer — `fo_861301ce64bdcce4`

#### Caderno de erros


##### Caderno de erros


**Caderno de erros** (1 aulas)

-   1. Caderno de erros — `fo_d37977e779e532f3`

#### Espanhol


##### Espanhol


**Aulas** (20 aulas)

-   1. Sinónimos e Técnicas de leitura — `fo_dce84835347e345d`
-   2. Heterosemánticos - Falsos cognatos — `fo_8e46da28881c5beb`
-   3. Acentuación e Heterotónicos — `fo_6ffbc90d321781c2`
-   4. Artículos e Heterogenéricos — `fo_18079402c03159ef`
-   5. Adverbios e Usos de muy y mucho — `fo_26f740cac64175c6`
-   6. Preposiciones — `fo_c4695496965cb7cf`
-   7. Verbo gustar — `fo_c94c8b190aec41a5`
-   8. Pronombre complemento — `fo_dc9ce21df9b499f5`
-   9. Conjunciones — `fo_15214cf210f4a91e`
-  10. Posesivos e Demostrativos — `fo_125612d1bfa78b59`
-  11. Verbos de cambio — `fo_b7f8203d0530e2d1`
-  12. Apócope — `fo_03e0f664378e2e57`
-  13. Numerales e Signos de puntuación — `fo_ff0454a41aa3c478`
-  14. Modo indicativo (presente) — `fo_c746891c4076a745`
-  15. Pretérito indefinido e Imperfecto — `fo_f550634790775d3f`
-  16. Pretérito perfecto compuesto — `fo_333e81378c993655`
-  17. Pretérito pluscuamperfecto — `fo_3e19c7a865fdb0b2`
-  18. Subjuntivo — `fo_7c41bf886c41d7fa`
-  19. Modo imperativo — `fo_d149d6f63344b426`
-  20. Condicional e Expresiones — `fo_e2b54fd83e59f637`

#### Filosofia Geral


##### Filosofia Geral


**Aulas** (20 aulas)

-   1. Origem da filosofia — `fo_c91e7fde5213a512`
-   2. Pré-socráticos — `fo_38724c7155e7f2f7`
-   3. Sócrates — `fo_3867f9ffc09df486`
-   4. Platão — `fo_f71b2404c36f544c`
-   5. Aristóteles — `fo_40e1c1a4b4ffbe39`
-   6. O Helenismo — `fo_2b61bebfb77c6adb`
-   7. Lógica e conhecimento — `fo_a9eff032f84ecde8`
-   8. Filosofia medieval — `fo_68530b7d45951c9f`
-   9. Filosofia renascentista — `fo_8ff121a525495480`
-  10. Filosofia moderna — `fo_6629ca60d4eb440f`
-  11. Racionalismo — `fo_c248760d41d3437c`
-  12. Empirismo — `fo_4da5544a00907562`
-  13. Filosofia crítica — `fo_c1390cc3f4f6d97f`
-  14. Contratualismo — `fo_07f38eb5cf225968`
-  15. Filosofia política — `fo_fe344a78a6ad3d06`
-  16. Positivismo — `fo_4d36875e4c3f1ffc`
-  17. Ética e moral — `fo_6888922d9a8bb239`
-  18. Filosofia contemporânea — `fo_2327958c0fe44327`
-  19. Existencialismo — `fo_ca1a4d666ea11aa5`
-  20. Filosofia pós-moderna — `fo_a65e79e4bdd9d68c`

#### Filosofia UFPR


##### Filosofia UFPR


**Filosofia UFPR** (44 aulas)

-   1. Filosofia clássica — `fo_b6fe0ef449efb82e`
-   2. Platão: Introdução — `fo_28ae675dd8733175`
-   3. Mito de Er I — `fo_f302e2de3f7d73f0`
-   4. Mito de Er II — `fo_6b58bffd53072895`
-   5. Mito de Er III — `fo_e754204b9663597c`
-   6. Justiça e injustiça — `fo_a2b2415e7fef8c05`
-   7. Conclusão do mito — `fo_58eddd75531e93d1`
-   8. Filosofia moderna — `fo_0a49a1143fd15cf2`
-   9. Jean Jacques Rousseau: Introdução — `fo_e3d136925a972526`
-  10. Estado de natureza — `fo_6f68ef6b4cc24b6f`
-  11. Surgimento da propriedade privada — `fo_e9d1504357d90aba`
-  12. Instituição das leis — `fo_0099c3bb39994a87`
-  13. Relações de poder — `fo_a3030a67a8be99e1`
-  14. Conclusão do discurso — `fo_6315818205964eac`
-  15. Filosofia contemporânea — `fo_0b0922575a3eb9e4`
-  16. Karl Popper: Introdução — `fo_ef742f7b8f247794`
-  17. O problema da demarcação — `fo_247bd6fc21daaecd`
-  18. O problema da indução — `fo_8f618ca762c0c7cd`
-  19. O critério da falseabilidade — `fo_2c7cf5c050bd0331`
-  20. Objetividade científica — `fo_6eb1fcdc66c9a4b0`
-  21. Conclusão da lógica — `fo_909b5f36728dbe7d`
-  22. Carole Pateman: Introdução — `fo_48f43054519ea45a`
-  23. Teoria crítica — `fo_a928034ba23bced8`
-  24. Sistema democrático — `fo_d82b3589fe2c9eff`
-  25. Apatia política — `fo_716626fd2960f0af`
-  26. Participação política — `fo_9256e96337105fef`
-  27. Democracia participativa — `fo_1a7a99b26517c684`
-  28. Conclusão da teoria — `fo_5ee1a5d63a433fb8`
-  29. Filosofia contemporânea brasileira — `fo_43a587900218b6c2`
-  30. Sueli Carneiro: introdução — `fo_c2e10bcebca7e61e`
-  31. Dispositivo de poder — `fo_231b437b456ea9f8`
-  32. Construção do outro — `fo_142a3c45677dbb6b`
-  33. Crítica a filosofia ocidental — `fo_5e8fc8939d15e618`
-  34. Epistemicídio no Brasil — `fo_1a129d59a7ac8e42`
-  35. Conclusão da racialidade — `fo_659773a34cfcb4a6`
-   - Karl Popper: A Experiência como Método (aula do curso 2025) — `fo_f19be237a16c27e7`
-   - Karl Popper: A Falseabilidade como Critério de Demarcação (aula do curso 2025) — `fo_0016b280c3261d07`
-   - Karl Popper: Biografia (aula do curso 2025) — `fo_3701d8e018dea40b`
-   - Karl Popper: Eliminação do Psicológico (aula do curso 2025) — `fo_889fd646bccbcd15`
-   - Karl Popper: O Problema da Demarcação (aula do curso 2025) — `fo_ce9d919e3b0183c9`
-   - Karl Popper: O Problema da Indução (aula do curso 2025) — `fo_d7c2b39c34abedb8`
-   - Karl Popper: O Problema da `Base Empírica` (aula do curso 2025) — `fo_5530ed4e0201ae9a`
-   - Karl Popper: Objetividade Científica e Convicção Subjetiva (aula do curso 2025) — `fo_985aa43ff95b238a`
-   - Karl Popper: Prova Dedutiva de Teorias (aula do curso 2025) — `fo_9d1da88e72f9fd52`

#### Física I


##### Física I


**Física I** (40 aulas)

-   1. Introdução à física — `fo_d194a604214edd91`
-   2. Análise dimensional e Conversão de unidades — `fo_6f1f0ae15840d536`
-   3. Vetores I — `fo_39bd0d4d1d2f16e3`
-   4. Vetores II — `fo_9af83655ed6958de`
-   5. Grandezas da cinemática — `fo_93a0ebf4105b245e`
-   6. Velocidade relativa e MRU — `fo_1449712569ab0c44`
-   7. MRUV — `fo_d656eaa24c41f699`
-   8. Gráficos da cinemática — `fo_46c77d92b73202ec`
-   9. Exercícios introdutórios — `fo_5d93200092038aff`
-  10. Movimentos na vertical — `fo_adb7c0add830b59c`
-  11. Lançamento oblíquo — `fo_582f49923c30bd5a`
-  12. Exercícios sobre lançamentos — `fo_0a1ce589516d70e5`
-  13. Aceleração centrípeta — `fo_9480ac02a6be5252`
-  14. Movimento circular — `fo_a3adadd695947329`
-  15. Transmissão do Movimento circular — `fo_424854cf09715f6a`
-  16. Velocidade e Aceleração vetorial — `fo_c93fdce26eddf3e3`
-  17. Exercícios sobre MCU — `fo_57376fe37af5edc0`
-  18. Força peso, normal e atrito — `fo_660a7ec4f87c04ae`
-  19. Força elástica e tração — `fo_8c946ff719418a08`
-  20. Diagrama de forças — `fo_35445d128d2ef7ac`
-  21. Leis de Newton — `fo_b5cb87156ea7ad0d`
-  22. Plano inclinado — `fo_e31f69e7ef4b12a7`
-  23. Força Resultante centrípeta — `fo_6a669b7f5c5cef75`
-  24. Exercícios sobre Leis de Newton — `fo_a6ed5e29d33fbb6a`
-  25. Equilíbrio de um ponto material — `fo_253cd9843f4eec54`
-  26. Equilíbrio de um corpo extenso — `fo_cc5f0e7d355fcb4e`
-  27. Gravitação universal — `fo_918cefe5e69fb621`
-  28. Exercícios sobre estatística e gravitação — `fo_820ef76e9c96ebe8`
-  29. Trabalho mecânico — `fo_78b0e8607e7de60b`
-  30. Energia mecânica — `fo_666a4d5a58fa3a72`
-  31. Relação trabalho-energia — `fo_5d76a9d831c771db`
-  32. Quantidade de movimento — `fo_9ebe19bc0644d534`
-  33. Impulso — `fo_84691981860e5f3a`
-  34. Colisões — `fo_be46a0aee230f12a`
-  35. Exercícios sobre trabalho e energia — `fo_c5869965a5869207`
-  36. Densidade, massa específica e pressão — `fo_e03b543e2d7fe48c`
-  37. Princípios da hidrostática I — `fo_3cf9245cff910796`
-  38. Princípios da hidrostática II — `fo_68b56cab23c3d39e`
-  39. Exercícios sobre hidrostática — `fo_4147995ba9ac93c1`
-  40. Revisão geral — `fo_004c9c0cb7e52dd4`

#### Física II


##### Física II


**Física II** (40 aulas)

-   1. Termometria — `fo_8ed65b595f1b0886`
-   2. Dilatometria — `fo_e67fc880ef6ae4fa`
-   3. Exercícios sobre termometria e dilatometria — `fo_1a37e805441d7098`
-   4. Propagação de calor — `fo_20813df4604610a1`
-   5. Lei de Fourier — `fo_0cb818051fe4e561`
-   6. Calor sensível e Calor latente — `fo_2372d19be19962df`
-   7. Diagrama de fases e Equilíbrio térmico — `fo_eb861e86c2956eef`
-   8. Exercícios sobre calorimetria — `fo_22abdf5218fe6343`
-   9. Gás ideal — `fo_a1aea40fe705c733`
-  10. Trabalho e Energia interna — `fo_5afc1e71c2c2a455`
-  11. Lei 0 e Primeira lei da termodinâmica — `fo_090509847e5072bb`
-  12. Segunda lei da termodinâmica — `fo_31cac2ad7a30a2b3`
-  13. Ciclo de Carnot e Entropia — `fo_26b2d68737232fa7`
-  14. Exercícios sobre termodinâmica — `fo_bec5267180956cc8`
-  15. Conceitos iniciais de óptica — `fo_ffef5aa837aa8cae`
-  16. Princípios de propagação da luz — `fo_6034442ecb77f396`
-  17. Reflexão da luz e Espelhos planos — `fo_a9e984b1e3b67e64`
-  18. Espelhos esféricos I — `fo_027437ce45e39266`
-  19. Espelhos esféricos II — `fo_ea368cd01afd0251`
-  20. Exercícios sobre óptica I — `fo_ce3ec1eae34765f7`
-  21. Refração da luz — `fo_a32831f69d0d6010`
-  22. Reflexão interna total — `fo_28a62b441001d766`
-  23. Prismas e Dispersão da luz — `fo_2b84be387c4612b6`
-  24. Lentes esféricas I — `fo_68156c40ed224af8`
-  25. Lentes esféricas II — `fo_74cd1430d5998d60`
-  26. Instrumentos ópticos — `fo_9add898b04bc866f`
-  27. Óptica da visão — `fo_d52919caa5c9f555`
-  28. Exercícios sobre óptica II — `fo_817d381224ab5303`
-  29. Introdução à ondulatória — `fo_ace39e08204f3e6b`
-  30. Refração e Reflexão de ondas — `fo_6df9df66910009c3`
-  31. Interferência, difração e polarização — `fo_e7cc6068f8d910c9`
-  32. Ondas eletromagnéticas — `fo_47eaeac0e3bb86bf`
-  33. Acústica I — `fo_0d368e6d560ce891`
-  34. Acústica II — `fo_5310aa7e67605cd0`
-  35. Instrumentos musicais — `fo_c3bfb7033b6a96ee`
-  36. Efeito Doppler do som — `fo_4fad599ea2a22aac`
-  37. Efeito Doppler da luz — `fo_1a3ead34a3137988`
-  38. Movimento harmônico simples — `fo_552a8f2d2ac13959`
-  39. Exercícios sobre ondulatória — `fo_d30852f5fb02a10d`
-  40. Revisão geral — `fo_47e34bf206466522`

#### Física III


##### Física III


**Física III** (41 aulas)

-   1. Carga elétrica e Processos de eletrização — `fo_db6c3896451c5bdb`
-   2. Força elétrica — `fo_2f949da57afbc837`
-   3. Campo elétrico — `fo_cf32fa39d52d7528`
-   4. Relação entre Força elétrica e Campo elétrico — `fo_5c82c80159f6950f`
-   5. Energia potencial elétrica — `fo_b0b36004de467295`
-   6. Potencial elétrico — `fo_df2ded9b67ac7459`
-   7. Trabalho de uma força elétrica — `fo_f45e002d3334c68d`
-   8. Campo elétrico uniforme — `fo_04d7e0d58c2eaa66`
-   9. Condutores em equilíbrio — `fo_78e6cbc80ce8baa0`
-  10. Exercícios sobre eletrostática — `fo_9d8ed91949d11369`
-  11. Corrente elétrica — `fo_fe3a9e2020bdd795`
-  12. Potência elétrica — `fo_8c10ca7886a3e874`
-  13. Primeira lei de Ohm — `fo_5ed23b59dbe08a04`
-  14. Segunda lei de Ohm — `fo_567b2994bae6381c`
-  15. Exercícios sobre corrente elétrica e leis de Ohm — `fo_4062d7cfbb38cf84`
-  16. Associação de resistores — `fo_7b67bcc7cab706cd`
-  17. Associação mista de resistores — `fo_85d4d741c924b8ae`
-  18. Medidores elétricos — `fo_072dc035a52be5dc`
-  19. Ponte de Wheatstone e Brilho — `fo_2da237da353c5db6`
-  20. Geradores e Receptores — `fo_74556835c718730a`
-  21. Aplicações em circuitos elétricos — `fo_df0cdc87e374ad6f`
-  22. Exercícios sobre circuitos elétricos — `fo_bec1cc0d8498115b`
-  23. Capacitores — `fo_89f3be8c0a1817e9`
-  24. Associação de capacitores — `fo_874137be2c3a64c7`
-  25. Exercícios sobre capacitores — `fo_ee2b0f3425e70fce`
-  26. Magnetismo — `fo_8815f0df5c2ee293`
-  27. Campo magnético e Corrente elétrica — `fo_6a12b9716cbbb26c`
-  28. Lei de Ampère I — `fo_559e61a85ade26f4`
-  29. Lei de Ampère II — `fo_ceb773e466bb5aaf`
-  30. Força magnética I — `fo_83cce729b6409364`
-  31. Força magnética II — `fo_2494c41ee0e64fbf`
-  32. Lei de Faraday — `fo_779ed3bf5780de70`
-  33. Lei de Lenz — `fo_b66cb5e57efd280f`
-  34. Exercícios sobre eletromagnetismo — `fo_7c972158e10ea9c8`
-  35. Radiação do corpo negro — `fo_6611361735a2e739`
-  36. Raios X e Dualidade onda partícula — `fo_904992f659d5fa7a`
-  37. Efeito fotoelétrico — `fo_26ffd83cdae4316c`
-  38. Relatividade — `fo_23816472c4b8b353`
-  39. Exercícios sobre física moderna — `fo_15505b010473f0b6`
-  40. Revisão geral — `fo_027aaf9868de583c`
-  41. Física III - UFPR Extensivo - Aula 21 - REEDITADA — `fo_fcad555740669e31`

#### Geografia I


##### Geografia I


**Geografia I** (34 aulas)

-   1. Movimentos da Terra — `fo_c75f085bf2cf5511`
-   2. Cartografia I — `fo_4a774ec42e3fdf8e`
-   3. Cartografia II — `fo_7727bb8c691d9207`
-   4. Cartografia III — `fo_a0141ed43367452b`
-   5. Cartografia IV — `fo_eb3ed67b7a7e874d`
-   6. Geologia I — `fo_5f62decbdce7ba7a`
-   7. Geologia II — `fo_cc4f1ca76f03a860`
-   8. Geomorfologia — `fo_7b0d718ef1d1986f`
-   9. Geologia brasileira — `fo_e2459c0adf376ff1`
-  10. Geomorfologia brasileira — `fo_06af79f3a577010d`
-  11. Solos — `fo_9001070ba0a1a165`
-  12. Climatologia I — `fo_e4b3bcee7ffd0e0e`
-  13. Climatologia II — `fo_4a1583f39b148074`
-  14. Climas do Brasil — `fo_9494de4ed2ca4636`
-  15. Hidrologia — `fo_9b4247f8f17e693d`
-  16. Biomas mundiais — `fo_ba5de8756a0ca359`
-  17. Biomas brasileiros — `fo_eb3930ab77b20f7e`
-  18. Recursos naturais e legislação ambiental brasileira — `fo_db9adaa31d302472`
-  19. Problemas ambientais I — `fo_c58fbdee5424335a`
-  20. Problemas ambientais II — `fo_7a4056b4d723a4e7`
-  21. Convenções ambientais I — `fo_e35a985beae60031`
-  22. Convenções ambientais II — `fo_719030c2383438e3`
-  23. Principais aspectos físicos da Ásia — `fo_dc9a3737236967cb`
-  24. Principais aspectos físicos da Europa — `fo_072d00527b59b52f`
-  25. Principais aspectos físicos da América — `fo_80cd7c6ca47f39d6`
-  26. Principais aspectos físicos da África — `fo_9014aac7222e0b12`
-  27. Principais aspectos físicos da Oceania — `fo_4b7f14e1ba742c99`
-   - Biomas Mundiais (aula do curso 2025) — `fo_243f5827e0dbeb1f`
-   - Biomas do Brasil (aula do curso 2025) — `fo_94db1adb8684ebf8`
-   - Climas do Brasil (aula do curso 2025) — `fo_e0fba97149a87288`
-   - Convenções Ambientais I (aula do curso 2025) — `fo_ab3f3fcab2cb9aff`
-   - Convenções Ambientais II (aula do curso 2025) — `fo_5d0e940cf217d220`
-   - Hidrologia (aula do curso 2025) — `fo_c99b0abd0ba31292`
-   - Problemas Ambientais (aula do curso 2025) — `fo_10747d74cc019c9b`

#### Geografia II


##### Geografia II


**Geografia II** (33 aulas)

-   1. Conceitos básicos — `fo_106d3eff6bf49247`
-   2. Território brasileiro — `fo_8ab734d736ff9eb9`
-   3. Regionalização do Brasil — `fo_8239c04f3acec455`
-   4. Demografia — `fo_be5fedc2936f631a`
-   5. Demografia brasileira I — `fo_4dc430a569c38cb9`
-   6. Demografia brasileira II — `fo_a03311c4dae49a9e`
-   7. Processo de industrialização I — `fo_a93e8af7c98b9802`
-   8. Processo de industrialização II — `fo_eef1d0d5e08a2cc1`
-   9. Urbanização I — `fo_3cbffaaf7b0366a6`
-  10. Urbanização II — `fo_c6ad147d4f590a9a`
-  11. Setor primário I — `fo_c294cc367b77d2a0`
-  12. Setor primário II — `fo_57bd700bf3000094`
-  13. Urbano-rural — `fo_a434b76602fb09f6`
-  14. Conflitos por terra no Brasil — `fo_decab040dac27fa8`
-  15. Produção e infraestrutura — `fo_2e0e258dcaa651bb`
-  16. Disparidades regionais — `fo_ad0f0845a5655f03`
-  17. Globalização — `fo_71af7d0332d800cb`
-  18. Geopolítica I — `fo_67280d5849d12cca`
-  19. Geopolítica II — `fo_69ecd883fc352b77`
-  20. Geopolítica III — `fo_1e369aa75dd5cd64`
-  21. Geopolítica IV — `fo_ed52fc413ae53c79`
-  22. Organização do espaço mundial — `fo_270e9b6110c0e484`
-  23. Principais aspectos humanos da Ásia — `fo_18997a911739e837`
-  24. Principais aspectos humanos da Europa — `fo_9a5974f78a9cb4e2`
-  25. Principais aspectos humanos América — `fo_6e40a52dd557b795`
-  26. Principais aspectos humanos da África — `fo_d0bbdffcf4d6cbe1`
-  27. Principais aspectos humanos da Oceania — `fo_502f8d1595b7fdd8`
-   - Geopolítica I (aula do curso 2025) — `fo_0c171cbd2c34c821`
-   - Geopolítica II (aula do curso 2025) — `fo_1d86ab62df395c01`
-   - Geopolítica III (aula do curso 2025) — `fo_6c910ea0e4fb218f`
-   - Geopolítica IV (aula do curso 2025) — `fo_94bba0b23f801c75`
-   - Ocupação do Brasil (aula do curso 2025) — `fo_ee3a5b180a910db9`
-   - Produção e Infraestrutura (aula do curso 2025) — `fo_c14ba129d40edf0b`

#### Geografia III


##### Geografia III


**Geografia III** (20 aulas)

-   1. Economia geral — `fo_197fa5edbc02d34f`
-   2. Cenário político-econômico I — `fo_12516419090cb5d5`
-   3. Cenário político-econômico II — `fo_2fc50f1c3bbf19ee`
-   4. Fronteiras problemáticas contemporâneas — `fo_05c1f82d903766de`
-   5. Blocos econômicos — `fo_d4b4fac9391c17c4`
-   6. Disputas no Mar da China — `fo_cf10178c23546708`
-   7. Ditadura em Myanmar e Nicarágua — `fo_10014a182094b83e`
-   8. Guerra civil Sudão e Iêmen — `fo_457502657e95561b`
-   9. Revolução iraniana e os grupos terroristas — `fo_ee969d5cabeedc10`
-  10. Reformas em Israel — `fo_3bb6ff373ebd2f07`
-  11. Terrorismo e os principais grupos — `fo_ab6a39a1c1716f2e`
-  12. Conflitos — `fo_b07b1fe1e93cce9d`
-  13. Eventos climáticos extremos — `fo_de0c6f677b69c3ce`
-  14. Mudanças climáticas e saúde — `fo_5f84a2277e63dfa2`
-  15. Energia limpa e a transição energética — `fo_e1ba37efa310c6ee`
-  16. Desafios econômicos do estado brasileiro — `fo_b3b259bfe4220f0b`
-  17. Amazônia e a política externa brasileira — `fo_bf96c289285d3afa`
-  18. Agronegócio, produção política e cultura — `fo_58fe731c104ca074`
-  19. Atualidades 2026 I — `fo_8ac1b653625d7440`
-  20. Atualidades 2026 II — `fo_cfa102e46eaec958`

#### História Geral - Extras


##### História Geral


**História Geral** (17 aulas)

-   1. Política e poder na antiguidade clássica — `fo_1ff5f564ea478e6a`
-   2. Alta Idade Média: Diversidade religiosa e cultural — `fo_31d3364e947eb053`
-   3. Baixa Idade Média: Religião, hegemonia e poder — `fo_b7b627f2415cb020`
-   4. Idade Moderna: Racionalização da vida — `fo_6c1208b6a232d813`
-   5. Idade Moderna: Estado, soberania e humanismo — `fo_a4ab1646e294e881`
-   6. Idade Moderna: Iluminismo, liberalismo e revolução — `fo_4a046568549f7803`
-   7. Idade Contemporânea: Independências e inovações tecnológicas — `fo_633941b3d06e8e5d`
-   8. Idade Contemporânea: Movimentos sociais, conferências e tratados I — `fo_033775e068c70117`
-   9. Idade Contemporânea: Movimentos sociais, conferências e tratados II — `fo_f326218725050b40`
-  10. Idade Contemporânea: A era do capital e expansões territoriais — `fo_704863e67bed0187`
-  11. Idade Contemporânea: Cultura e política nos reinos africanos — `fo_52a761114657a66c`
-  12. Neocolonialismo e Nacionalismos: Partilha da África e Colonização — `fo_c4b06931443f0511`
-  13. A Era da Guerra Total: 1ª Guerra Mundial — `fo_b54f0492ffbd12e3`
-  14. Revolução de 1917 e Stalinismo — `fo_b7ba5cee3bff9f80`
-  15. Regimes Totalitários e suas Consequências — `fo_184524d92f9f3a96`
-  16. Guerra Fria e Descolonização — `fo_4524cb17eed1fd4b`
-  17. Contracultura e Revoluções — `fo_a91079a367f8eddf`

#### História I


##### História I


**História I** (59 aulas)

-   1. Período pré-colonial — `fo_227a6cb841e9703c`
-   2. Ciclo da cana-de-açúcar — `fo_59e3f86eafe6c9f7`
-   3. Invasões e conflitos — `fo_ad9ef5945f53a916`
-   4. Ciclo da mineração — `fo_ce57ea989eeb8aba`
-   5. Movimentos de resistência — `fo_b2d1c3a1d1e53928`
-   6. Revoltas coloniais I — `fo_40adb6c6f48d1a61`
-   7. Revoltas coloniais II — `fo_85556bb9f0c2d633`
-   8. Período joanino e independência — `fo_05a6db94a4ffc252`
-   9. Primeiro reinado — `fo_5f98752d848818ee`
-  10. Período regencial — `fo_cb985d51418749d0`
-  11. Segundo reinado I — `fo_508c506069a9100a`
-  12. Segundo reinado II — `fo_07e700f5978c279b`
-  13. República velha — `fo_3c6363ca9880efd5`
-  14. República oligárquica I — `fo_3b5da940cd18eae9`
-  15. República oligárquica II — `fo_d82fc3b73dc586ec`
-  16. Revolução de 1930 — `fo_6d904a3618676b02`
-  17. Era Vargas - Constitucional — `fo_b3f0429522af3251`
-  18. Estado Novo — `fo_ab49f8bfac41431d`
-  19. República populista I — `fo_58f7f2427645f3d6`
-  20. República populista II — `fo_2d0a613d77a27173`
-  21. Ditadura militar I — `fo_5e5b67f175783313`
-  22. Ditadura militar II — `fo_650941bf902041b6`
-  23. Redemocratização — `fo_48328c5468b4d569`
-  24. Movimentos sociais — `fo_2a8b37b04f277dbf`
-  25. Patrimônio histórico-cultural brasileiro — `fo_1be17f9f64d9a70b`
-  26. Períodos da História do Brasil (aula do curso 2025) — `fo_472b5bda6b748a97`
-  27. Baixa Idade média e Grandes Navegações (aula do curso 2025) — `fo_350c7f36015a821b`
-  28. Conquista e Formação Cultural do Brasil (aula do curso 2025) — `fo_0afd39ae58bba575`
-  29. Período Pré-Colonial (aula do curso 2025) — `fo_3825ff0a6fe22fd9`
-  30. Capitanias Hereditárias e Governos Gerais (aula do curso 2025) — `fo_d01595af3c4e0c29`
-  31. Ciclo da Cana de Açúcar (aula do curso 2025) — `fo_2e6b5937b5940113`
-  32. O Tráfico Negreiro (aula do curso 2025) — `fo_259b1e7538a32653`
-  33. Os Índigenas e a Cataquese (aula do curso 2025) — `fo_03b21fbfa4071050`
-  34. União Ibérica e Holandeses no Brasil (aula do curso 2025) — `fo_b2fbe5c062bff985`
-  35. Entradas e Bandeiras (aula do curso 2025) — `fo_c3a3880a5a27daf4`
-  36. A Economia da Mineração (aula do curso 2025) — `fo_1cbb17f98356b6ca`
-  37. Crise do Sistema Colonial (1750 - 1808) (aula do curso 2025) — `fo_7cf9dadad0ab11c6`
-  38. Revoltas Separatistas Coloniais (aula do curso 2025) — `fo_85c1e9c2cdf3af8a`
-  39. A Família Real no Brasil (aula do curso 2025) — `fo_741ec5dd7ee911bd`
-  40. Primeiro Reinado (aula do curso 2025) — `fo_8e1dd3ecd63d6c75`
-  41. Período Regencial (aula do curso 2025) — `fo_cbb4bb409331ae52`
-  42. Segundo Reinado - Política Interna (aula do curso 2025) — `fo_ba36feb209991220`
-  43. Proclamação da República 1889 (aula do curso 2025) — `fo_5b0a011793e15e5f`
-  44. República da Espada (aula do curso 2025) — `fo_06d49d3266663be0`
-  45. Crise da República Velha (aula do curso 2025) — `fo_cf65e47f3cca28a3`
-  46. República Oligárquica (aula do curso 2025) — `fo_4242bd46dc38bb77`
-  47. Crise da República Velha (aula do curso 2025) — `fo_b84ba98c6c2b16a4`
-  48. Crise da República Velha e Revolução de 1930 (aula do curso 2025) — `fo_52a6a67358b1f40a`
-  49. A Era Vargas (1930 - 1934) - Governo Provisório (aula do curso 2025) — `fo_13e4ae81bb8076a0`
-  50. A Era Vargas (1934 - 1937) - Governo Constitucional (aula do curso 2025) — `fo_2a3bca3264545f25`
-  51. A Era Vargas (1937 - 1945) - Estado Novo (aula do curso 2025) — `fo_b85125dd9308139a`
-  52. Fim do Estado Novo (aula do curso 2025) — `fo_c4285eda8844f660`
-  53. Getúlio Vargas (1951 - 1954) (aula do curso 2025) — `fo_119b19fd5461bb21`
-  54. Getúlio Vargas (1954 - 1956) (aula do curso 2025) — `fo_cfe0806a6919edcf`
-  55. Governo JK (1956 - 1961) (aula do curso 2025) — `fo_ada3377a4eb0f19f`
-  56. Governos de: Jânio Quadros (1961) e João Goulart (1961 - 1964) (aula do curso 2025) — `fo_fda032cb30a159b4`
-  57. Ditadura Militar (aula do curso 2025) — `fo_8b3a2ab29bb26d80`
-  58. Nova República - Sarney a FHC (aula do curso 2025) — `fo_735fa196ce4ba417`
-  59. Nova República - Lula a Bolsonaro (aula do curso 2025) — `fo_b6c37b096f3891e8`

#### História II


##### História II


**História II** (73 aulas)

-   1. Patrimônio histórico — `fo_7805144bb050a767`
-   2. Egito antigo — `fo_dd39159bf3666e92`
-   3. Grécia antiga I — `fo_98593f7d12ab1f46`
-   4. Grécia antiga II — `fo_3713dab1c4da619c`
-   5. Grécia antiga III — `fo_14103d850d38ce7e`
-   6. Roma antiga I — `fo_cfa566ee02eef186`
-   7. Roma antiga II — `fo_0cb31e27e356c401`
-   8. Roma antiga III — `fo_98f06ace2d59cdde`
-   9. Império Bizantino — `fo_3a51166d9e86d81b`
-  10. Civilização Árabe — `fo_db66907ea0389692`
-  11. Igreja e Feudalismo — `fo_cbf4dc0ccbcc8e0a`
-  12. Alta Idade Média — `fo_2bc512e49492125a`
-  13. Baixa Idade Média — `fo_11398342cc33cd26`
-  14. Renascimento — `fo_7454adc95877242f`
-  15. Expansão marítima — `fo_ca718d07e1b068bd`
-  16. Reforma protestante — `fo_e94d13643c14001d`
-  17. Povos africanos — `fo_73fef1e8f65a0b50`
-  18. Colonização das Américas — `fo_83021642908d6fa2`
-  19. Absolutismo I — `fo_fb7cc61386a76e9b`
-  20. Absolutismo II — `fo_121cf0e6c819f022`
-  21. Iluminismo — `fo_3d7dd1747484362d`
-  22. Revolução industrial — `fo_fdfb2c0794fd49b6`
-  23. Independência dos EUA — `fo_a3361bbf5b26555f`
-  24. Revolução francesa — `fo_997969c604365ac2`
-  25. Era Napoleônica — `fo_02e2deccacaab116`
-  26. Independência do Haiti — `fo_bfc702ef004ba538`
-  27. Independência da América Espanhola — `fo_06b68643a741069f`
-  28. Revoluções liberais — `fo_6e964be4bc547646`
-  29. Século XIX — `fo_a47911a08dabce37`
-  30. Imperialismo — `fo_c947f9619a9d3c89`
-  31. Primeira guerra mundial — `fo_3c476067fbc72d90`
-  32. Rússia no século XX — `fo_28312610f8b6759c`
-  33. Ascensão do Nazifascismo — `fo_890866935c38bcf5`
-  34. Segunda guerra mundial I — `fo_9cbcf5f94dff827b`
-  35. Segunda guerra mundial II — `fo_fc1b40e28b46d7c6`
-  36. Guerra fria I — `fo_b8829dec5c3f3a70`
-  37. Guerra fria II — `fo_4d8999b774a4ddf0`
-  38. Supremacia americana — `fo_39c53674a611ff5b`
-  39. Conflitos asiáticos — `fo_900a14c14cf7a5d8`
-  40. Descolonização afro-asiática — `fo_8b2ec7ca25bac9ef`
-  41. Movimentos sociais do século XX — `fo_5bbd4af4db87be5b`
-  42. Ditaduras na América Latina — `fo_9eeec8893dac1c1b`
-  43. Século XXI — `fo_d5d912788030e7de`
-  44. Efemérides — `fo_828e1ce02e0e9b3b`
-   - América Latina no Século XX (aula do curso 2025) — `fo_d0f69b4b3f9a42d8`
-   - Ascensão do Fascismo (aula do curso 2025) — `fo_1c8bbca6d976403e`
-   - Ascensão do Nazismo (aula do curso 2025) — `fo_89e0b4098843ccd8`
-   - Crise de 1929 (aula do curso 2025) — `fo_6ce412dbd24ef48f`
-   - Cultura do XX (aula do curso 2025) — `fo_f8a13941b437fe4b`
-   - Descolonização da África e da Ásia I (aula do curso 2025) — `fo_8db73c5e69e61b7b`
-   - Descolonização da África e da Ásia II (aula do curso 2025) — `fo_abf23c6742179cfd`
-   - Fim da URSS (aula do curso 2025) — `fo_c1c19178aedcc821`
-   - Guerra Civil Espanhola (aula do curso 2025) — `fo_352a61f0bceccb63`
-   - Guerra Fria I (aula do curso 2025) — `fo_2309183ad5e0222c`
-   - Guerra Fria II (aula do curso 2025) — `fo_a848eb4f98b3a1cc`
-   - Ideologias do Séc. XIX (aula do curso 2025) — `fo_13ea94d1b3350f3b`
-   - Independência da América Espanhola (aula do curso 2025) — `fo_020d8f5797a8efd9`
-   - Independência do Haiti (aula do curso 2025) — `fo_7689374c4c24a150`
-   - Independência dos EUA (aula do curso 2025) — `fo_d40688c01b5a7e7b`
-   - Neocolonialismo (aula do curso 2025) — `fo_445f746f69b42da5`
-   - Primeira Guerra Mundial I (aula do curso 2025) — `fo_548983b5cd6ea832`
-   - Primeira Guerra Mundial II (aula do curso 2025) — `fo_6288131ba4ad0450`
-   - Revolução Chinesa e Conflitos Árabes (aula do curso 2025) — `fo_47053eec6d5e8e3c`
-   - Revolução Francesa I (aula do curso 2025) — `fo_af0cde1d5aa534e5`
-   - Revolução Francesa II (aula do curso 2025) — `fo_e92355f8b16654c9`
-   - Revolução Industrial (aula do curso 2025) — `fo_bf8573db92272535`
-   - Revolução Mexicana (aula do curso 2025) — `fo_a12ebb3d4e9bd3f6`
-   - Revolução Russa (aula do curso 2025) — `fo_cf15e552b43f09ef`
-   - Segunda Guerra Mundial (1939 - 1945) - Europa (aula do curso 2025) — `fo_fa82100a4d1eefa9`
-   - Segunda Guerra Mundial - Pacífico (aula do curso 2025) — `fo_62433a526d10bb98`
-   - Supremacia Americana I (aula do curso 2025) — `fo_5673c33abf69f9ce`
-   - Supremacia Americana II (aula do curso 2025) — `fo_ea32364a16268960`
-   - Século XIX (aula do curso 2025) — `fo_5a79fffa31c5674b`

#### História do Brasil - Extras


##### História do Brasil


**História do Brasil** (12 aulas)

-   1. Brasil Colônia: a decisão de ocupar a terra — `fo_d7edae8e3911eed8`
-   2. Brasil Colônia: Resistências — `fo_0abeadae40e785fd`
-   3. Brasil Império: o início — `fo_dc3e87eb91142923`
-   4. Brasil Império: Os Reinados — `fo_629c22d4392e976f`
-   5. Brasil Império: Resistência cultural — `fo_606ff44f328036a3`
-   6. República Velha: Novo começo — `fo_6b1c2f05a7b64671`
-   7. República Velha: Alianças e conflitos — `fo_4bcd2141f23f63b3`
-   8. Nova República: Política Varguista — `fo_3513f05ac30e2655`
-   9. Nova República: Carisma político — `fo_5c860a2ef84143bd`
-  10. Nova República: Tempos de censura — `fo_c0e8a6b7eb7510f6`
-  11. Nova República: Brasil atual — `fo_8b908645c137ce00`
-  12. Patrimônio e Memória Brasileira — `fo_60d938ce8c906081`

#### Inglês


##### Inglês


**Aulas** (20 aulas)

-   1. Introdução — `fo_3ec0923acaca52f9`
-   2. Purpose of the text — `fo_14bfdfc48541d5cc`
-   3. Exercícios sobre purpose of the text — `fo_1e3c18cd9d33d4fb`
-   4. Reading techniques I — `fo_dc36cd68222b2001`
-   5. Reading techniques II — `fo_8a826bf8c79b8ff3`
-   6. Termos importantes e vocabulário — `fo_8cd0987fa0c17594`
-   7. Reading techniques - skimming — `fo_93aa680c772a6e4a`
-   8. Reading techniques - scanning — `fo_bfb2d3353b2e8935`
-   9. Pronouns — `fo_7d1df8c612d22381`
-  10. Exercícios sobre pronouns — `fo_3299dccd3b4f1ec1`
-  11. Cognatos — `fo_6ba3ef2e86e65fa4`
-  12. Falsos cognatos — `fo_dc6f50398f728d61`
-  13. Conjunções e conectivos — `fo_d184b294220c3371`
-  14. Exercícios sobre conjunções e conectivos — `fo_49ee026076754d34`
-  15. Adverbs — `fo_6e2741db685e973a`
-  16. Adverbs and vocabulary — `fo_36d50361e8a10de5`
-  17. Modal verbs — `fo_e274fef78f8c641c`
-  18. Prepositions — `fo_016902fbfff00f92`
-  19. Exercícios gerais — `fo_1abb99b5dc5e7453`
-  20. Revisão — `fo_3f261fe804d77182`

#### Introdução


##### Introdução


**Introdução** (1 aulas)

-   1. Introdução aos métodos de estudo — `fo_294ddf3224863fea`

#### Literatura Geral


##### Literatura Geral


**Aulas** (21 aulas)

-   1. Gêneros literários — `fo_6482cf1ce4bb48af`
-   2. Literatura e Língua Portuguesa — `fo_99d87eb145eb1bab`
-   3. Literatura e outras Artes — `fo_b513dbc5f39165a3`
-   4. Prosa e poesia — `fo_2252c6aaa1e5e8cd`
-   5. Estudos do poema — `fo_bacc7e39949310d6`
-   6. Estudos da narrativa — `fo_4226130442f62c8e`
-   7. Origens da literatura Luso-Brasileira — `fo_94b44afee8f9fcc1`
-   8. Quinhentismo e Barroco — `fo_c7b8adcbf74ca89d`
-   9. Arcadismo — `fo_965e9dd9ad661e22`
-  10. Romantismo 1ª geração — `fo_a9402e9b2760ccde`
-  11. Romantismo 2ª e 3ª geração — `fo_ad412a284f7f3a57`
-  12. Realismo/Naturalismo — `fo_cc58fb8d6fe26e4a`
-  13. Parnasianismo e Simbolismo — `fo_1f43db40addc39b0`
-  14. Pré-modernismo — `fo_413293e8a262006e`
-  15. Semana da Arte Moderna — `fo_56ae1e20d3947da9`
-  16. Modernismo 1ª geração — `fo_4773843af57cf3d6`
-  17. Modernismo 2ª geração — `fo_98115b665171006b`
-  18. Modernismo 3ª geração — `fo_3bf5b215787d272e`
-  19. Contemporâneo - séc. XX — `fo_e2d45966e0eba19c`
-  20. Contemporâneo - séc. XXI — `fo_05dcd19cbc99ba95`
-   - Romantismo 1ª geração — `fo_b425f35470e52a2f`

#### Literatura UFPR


##### Literatura UFPR


**Literatura UFPR** (18 aulas)

-   1. A falência — `fo_9857880ef944d652`
-   2. A falência - Exercícios — `fo_7584eb4e838ce28e`
-   3. Noite na taverna — `fo_632e728ce5a38b8d`
-   4. Noite na taverna - Exercícios — `fo_8fbddebddc838a35`
-   5. O Drible - Parte I — `fo_e4bcd8e283236111`
-   6. O Drible - Parte II — `fo_ac3f85c492173f54`
-   7. O sol na cabeça - Parte I — `fo_255736403885cc64`
-   8. O sol na cabeça - Parte II — `fo_af3f3bbf5874f146`
-   9. O sol na cabeça - Parte III — `fo_df44ac04c1ba2f0d`
-  10. Poema Sujo - Parte I — `fo_f8c9e23c3ed93197`
-  11. Poema Sujo - Parte II — `fo_32a4a9c12e646f5e`
-  12. Poema Sujo - Parte III — `fo_a6d6bc0bdd6e96c2`
-  13. Eu - Parte I — `fo_24c5ea7b5bffb257`
-  14. Eu - Parte II — `fo_808d27404769994c`
-  15. O Demônio Familiar - Parte I — `fo_1afe4ac00d99d689`
-  16. O Demônio Familiar - Parte II — `fo_5a3b74ad1f3ec6c3`
-  17. O Quinze - Parte I — `fo_32cdf170556f4c11`
-  18. O Quinze - Parte II — `fo_faf7eac8cd58ebf9`

#### Matemática I


##### Matemática I


**Matemática I** (40 aulas)

-   1. Teoria dos conjuntos — `fo_865adc46282f0fde`
-   2. Conjuntos numéricos — `fo_ece3965e5741f3f0`
-   3. Múltiplos e Divisores — `fo_c17e9dae0baa629f`
-   4. Potenciação — `fo_97c13e5e506de2d2`
-   5. Radiciação — `fo_6781a1df6dbfb0a6`
-   6. Radiciação e Racionalização — `fo_5782b5dd09cbc535`
-   7. Definição de função — `fo_cb6bbd91de586443`
-   8. Tipologia de função — `fo_64e758a43193be18`
-   9. Função inversa — `fo_2273f9c69b013d95`
-  10. Função composta — `fo_139ce9fcc3b5acb1`
-  11. Exercícios sobre funções — `fo_331c67e49d81917c`
-  12. Função afim — `fo_a719610740cb128f`
-  13. Exercícios sobre função afim — `fo_987d0f8c6a0035fd`
-  14. Função quadrática I — `fo_70439622fbb4d6d0`
-  15. Função quadrática II — `fo_1dc535f9229bc8c9`
-  16. Exercícios sobre função quadrática — `fo_118b3c6bca666572`
-  17. Inequações — `fo_3e598094f9bbc9a9`
-  18. Exercícios sobre inequações — `fo_8827aaf37f7e4dc9`
-  19. Função modular — `fo_f2bd483d70e23e9a`
-  20. Equação e Inequação modular — `fo_e493e694ff2af48f`
-  21. Exercícios sobre módulos — `fo_53074486e466c3f6`
-  22. Equação exponencial — `fo_668039a96f39cfdf`
-  23. Função exponencial — `fo_87105bb8c4994340`
-  24. Inequação exponencial — `fo_ee054f9db0c7fded`
-  25. Exercícios sobre exponenciais — `fo_4dcbe49529f31c6c`
-  26. Logaritmos — `fo_f44161e9ea5d3076`
-  27. Equação logarítmica — `fo_080cc573c43b8c3d`
-  28. Função logarítmica — `fo_a7efe301da20f90b`
-  29. Inequação logarítmica — `fo_a471bae869815697`
-  30. Exercícios sobre logaritmos e exponenciais — `fo_dbe84e04ed063e77`
-  31. Identidades trigonométricas — `fo_0b077858e4abda49`
-  32. Equações trigonométricas — `fo_127a8e05e393a2db`
-  33. Inequações trigonométricas — `fo_48ccea628dafaddd`
-  34. Função trigonométrica — `fo_030f97adefd68122`
-  35. Exercícios sobre função trigonométrica — `fo_5531ab60e13e948f`
-  36. Exercícios sobre inequações e equações trigonométricas — `fo_42672a681d8dc22c`
-  37. Progressão aritmética — `fo_818c1485440b4b52`
-  38. Soma de PA — `fo_335997b18e9760e3`
-  39. Progressão geométrica — `fo_0b84c7c8a6fda608`
-  40. Soma de PG — `fo_6cffe00bb4fa803d`

#### Matemática II


##### Matemática II


**Matemática II** (52 aulas)

-   1. Ângulos — `fo_8f5a177e103402b4`
-   2. Triângulos — `fo_4c5aae1255bd36f9`
-   3. Cevianas — `fo_8aaab58852e60278`
-   4. Quadriláteros — `fo_653ab99067cd7779`
-   5. Polígonos — `fo_ae06e7259343442c`
-   6. Área de polígono — `fo_5f2663339c2dc669`
-   7. Exercícios sobre polígonos — `fo_518150240871e48e`
-   8. Teorema de Tales — `fo_f36a31279d439c0a`
-   9. Semelhança de triângulos — `fo_0589af02311553aa`
-  10. Exercícios sobre semelhança e Tales — `fo_2e2544989570a46f`
-  11. Relações métricas no triângulo retângulo — `fo_a823f7cb2d1be759`
-  12. Teorema de Pitágoras — `fo_c98ea23fe914cfaa`
-  13. Razões trigonométricas — `fo_fc147c60fd58079d`
-  14. Círculo trigonométrico — `fo_7cd1c3b935158809`
-  15. Trigonometria em um triângulo qualquer — `fo_ae1ba4cb7d61d601`
-  16. Exercícios sobre trigonometria — `fo_2fd2501c3749d04a`
-  17. Círculo — `fo_67c25624be2dc8dc`
-  18. Círculo e retas — `fo_3cae05922f15d359`
-  19. Exercícios sobre círculos — `fo_d669e4080d2e8b56`
-  20. Geometria espacial de posição — `fo_b20a772ede7f61f0`
-  21. Poliedros regulares — `fo_44c3f8fcc234b8e4`
-  22. Exercícios sobre poliedros — `fo_414c9d5adf840f99`
-  23. Prismas — `fo_214dceaedf4c3956`
-  24. Exercícios sobre prismas — `fo_eb1cb3e9f10f14a2`
-  25. Pirâmide — `fo_c5ddbe06b055807a`
-  26. Tronco de pirâmide — `fo_8e5e69f494583e66`
-  27. Exercícios sobre pirâmides — `fo_e47867f11b4dc129`
-  28. Cilindro — `fo_677883033a77822d`
-  29. Cone — `fo_d687e1978952e069`
-  30. Exercícios sobre cilindros e cones — `fo_aad434b5379e6a8d`
-  31. Esfera — `fo_942bab15898a688e`
-  32. Exercícios sobre esferas — `fo_0a18fb4c60c4d334`
-  33. Estudo do ponto — `fo_ca7d1bec0d104b96`
-  34. Estudo da reta — `fo_8cfe96edca88540c`
-  35. Estudo da circunferência — `fo_8d7ad0bdeda9ac46`
-  36. Exercícios sobre geometria analítica — `fo_4eedec06bb99670b`
-   - Cilindro (aula do curso 2025) — `fo_9895164ce5bda08a`
-   - Cilindros e Cones - Exercícios (aula do curso 2025) — `fo_88e1237b2cd8cc6f`
-   - Circunferências (aula do curso 2025) — `fo_2cd456e9714b1136`
-   - Cones (aula do curso 2025) — `fo_f1eca1ca2e16a70f`
-   - Esferas (aula do curso 2025) — `fo_8a09b2fd5d68b8f6`
-   - Esferas - Exercícios (aula do curso 2025) — `fo_0c45b918aa0889c9`
-   - Estudo da Reta (aula do curso 2025) — `fo_8ed91a1e097ff92c`
-   - Estudo do ponto (aula do curso 2025) — `fo_f3df01f2a0189d4d`
-   - Geometria Analítica - Exercícios I (aula do curso 2025) — `fo_bb4b32ed4350eb6b`
-   - Geometria Analítica - Exercícios II (aula do curso 2025) — `fo_a66d97e71b379871`
-   - Pirâmides (aula do curso 2025) — `fo_da04d6ad0c1d5e89`
-   - Pirâmides - Exercícios (aula do curso 2025) — `fo_f85cc36832038c53`
-   - Prismas (aula do curso 2025) — `fo_cd890305e41e2046`
-   - Prismas - Exercícios (aula do curso 2025) — `fo_5f67d9e48417d7e5`
-   - Prismas Notáveis (aula do curso 2025) — `fo_1f1e1e679e66f50c`
-   - Tronco de Pirâmide (aula do curso 2025) — `fo_0d17cddd20046035`

#### Matemática III


##### Matemática III


**Matemática III** (54 aulas)

-   1. Razão e Proporção — `fo_568cce2978fce88a`
-   2. Porcentagem I — `fo_6fdaaf202a8c5f11`
-   3. Porcentagem II — `fo_a3f00fc2b3da3464`
-   4. Juros simples — `fo_0a9b5fce40cdf68b`
-   5. Juros compostos — `fo_e53b7bd8eed6067e`
-   6. Estatística I — `fo_73740cea11d1f6fc`
-   7. Estatística II — `fo_7adf98698867be81`
-   8. Exercícios sobre estatística — `fo_d7612b39dfc003fc`
-   9. Princípio fundamental da contagem — `fo_c0665cd5073c6462`
-  10. Combinação — `fo_49ea8f864818eafb`
-  11. Arranjo e permutação — `fo_6f27da62bca8898d`
-  12. Exercícios sobre arranjo e combinação — `fo_972003b4f243a986`
-  13. Princípio da casa dos pombos — `fo_0080c5ad8d2d8927`
-  14. Binômio de Newton — `fo_87579f5848d28a31`
-  15. Probabilidade I — `fo_1a4ad9f8488b5bfc`
-  16. Probabilidade II — `fo_fb8611f1de2b2ff5`
-  17. Probabilidade III — `fo_5e8c47c4884fdef0`
-  18. Exercícios sobre probabilidade I — `fo_47a60c2b38ab4ac3`
-  19. Exercícios sobre probabilidade II — `fo_61f9fb81788f24af`
-  20. Matrizes I — `fo_2bac76fc32f37819`
-  21. Matrizes II — `fo_7df4b0495921452c`
-  22. Determinantes — `fo_6cd6423798a0838d`
-  23. Propriedade de determinantes — `fo_8565172b9c90894f`
-  24. Sistemas lineares — `fo_29660a562065f0f3`
-  25. Produtos notáveis e Fatoração — `fo_5393f387d97dde36`
-  26. Exercícios sobre Produtos notáveis e Fatoração — `fo_96a747c90693d6f6`
-  27. Polinômios I — `fo_f58d450a7772c2f5`
-  28. Polinômios II — `fo_751d16249c3a8a6d`
-  29. Teoremas — `fo_f487b14743074096`
-  30. Equação polinomial — `fo_441135ecf660a76a`
-  31. Exercícios sobre polinômios — `fo_777165eea4a004c7`
-  32. Números complexos — `fo_6d3867bc31a4b83b`
-  33. Exercícios sobre números complexos — `fo_ec1befd029f89942`
-  34. Forma trigonométrica de complexos — `fo_39f83bf0f7b9da64`
-  35. Fórmulas de Moivre — `fo_f9164ef5d1c7f8ef`
-  36. Exercícios sobre forma trigonométrica complexos — `fo_d1e63cc3b3bd7c50`
-  37. Raízes complexas — `fo_5d46c3ed2f1b426c`
-  38. Exercícios sobre raízes complexas — `fo_d93e0d7c1b466278`
-  39. Raízes Complexas (aula do curso 2025) — `fo_ffc0f3b1c123edb0`
-  40. Raízes Complexas - Exercícios (aula do curso 2025) — `fo_583cc16c49049bc0`
-   - Complexos - Exercícios (aula do curso 2025) — `fo_2f86757a7a2608ff`
-   - Complexos - Forma Trigonométrica - Exercícios (aula do curso 2025) — `fo_4e1c7d79c2c22cfc`
-   - Equação Polinomial (aula do curso 2025) — `fo_6f99d8f7623ec27f`
-   - Fórmulas de Moivre (aula do curso 2025) — `fo_29348f10653d9a90`
-   - Números Complexos (aula do curso 2025) — `fo_7e81ecc69ba2759e`
-   - Números Complexos - Exercícios (aula do curso 2025) — `fo_3f844688e7a555ee`
-   - Números Complexos - Formas Trigonométricas (aula do curso 2025) — `fo_c0284254b424260b`
-   - Polinômios - Exercícios I (aula do curso 2025) — `fo_3e59840750907dc0`
-   - Polinômios - Exercícios II (aula do curso 2025) — `fo_03b5fb2a6cf24e5d`
-   - Polinômios I (aula do curso 2025) — `fo_b7cfab87a1f1246a`
-   - Polinômios II (aula do curso 2025) — `fo_595f32c98c07790c`
-   - Propriedade de Determinantes (aula do curso 2025) — `fo_b59baf0238e6fce8`
-   - Sistemas Lineares (aula do curso 2025) — `fo_b14b21d315e94e6d`
-   - Teoremas (aula do curso 2025) — `fo_4dcbb481eeda3631`

#### Método Pomodoro


##### Método Pomodoro


**Método Pomodoro** (1 aulas)

-   1. Método Pomodoro — `fo_ad11f4a9934d8e57`

#### Método de Cornell


##### Método de Cornell


**Método de Cornell** (1 aulas)

-   1. Método de Cornell — `fo_7e1ded24c00d0dfd`

#### Método de Feynman


##### Método de Feynman


**Método de Feynman** (1 aulas)

-   1. Método de Feynman — `fo_21b094f86f495443`

#### Português I


##### Português I


**Português I** (29 aulas)

-   1. Introdução: o que é texto — `fo_20def4744f403c6c`
-   2. Linguagem — `fo_55e088042bbb757b`
-   3. Estratégias de leitura — `fo_e345ddd611e94dc5`
-   4. Identificação de ideias do texto — `fo_f28a2717c47955ca`
-   5. Intenção comunicativa — `fo_53eb130a15a19f06`
-   6. Interpretação de texto: Narrativo e injuntivo — `fo_0a484ce53b4f5e3f`
-   7. Interpretação de texto: Dissertativo — `fo_c9afcb77a543b0a2`
-   8. Interpretação de texto: Expositivo — `fo_7f941f03e8ed8ab4`
-   9. Interpretação de texto: Descritivo — `fo_a7892ac247c50d04`
-  10. Interpretação de textos jornalísticos — `fo_8245aaa885949b85`
-  11. Interpretação de textos literários — `fo_d4c050ea98ee8897`
-  12. Interpretação de quadrinhos — `fo_34cba6c78abc9748`
-  13. Interpretação de gráfico e infográfico — `fo_54dca96a183ad077`
-  14. Intertextualidade — `fo_be0e94add5cac64c`
-  15. Inferência: Explícitos — `fo_5333d038f84bba97`
-  16. Inferência: Implícitos — `fo_21493b45a54547ef`
-  17. Operações textuais: Síntese, paráfrase e perífrase — `fo_d0357f89d6738008`
-  18. Operações textuais: Tipos de discurso — `fo_d5811cb1c2b93058`
-  19. Coesão referencial — `fo_bb793eddfe7ddb56`
-  20. Coesão conectiva — `fo_9962221a6c3645c8`
-  21. Semântica — `fo_0a97c024b0007c7c`
-  22. Ambiguidade — `fo_a79eaae650f25a0b`
-  23. Figuras de Linguagem: Palavras e construção — `fo_40e260102a63ba25`
-  24. Figuras de Linguagem: Pensamento — `fo_984cb580d6025e31`
-  25. UFPR: Tipos de leitura — `fo_ea159560b84a0a9c`
-  26. UFPR: Tipos de questão — `fo_7809d70aa05ba5a2`
-  27. UFPR: Análise de alternativas — `fo_77f88812099fbbae`
-  28. UFPR: Análise de múltipla escolha — `fo_98d55c1799fd8db9`
-  29. UFPR: Análise de comando textual — `fo_0a5f70c1ddc76f86`

#### Português II


##### Português II


**Português II** (47 aulas)

-   1. Fonologia — `fo_e5271b2ad1b027e9`
-   2. Acentuação — `fo_86f3b2471d6050ab`
-   3. Emprego do hífen — `fo_ed4380ec1a3f46e0`
-   4. Estrutura e formação de palavras — `fo_cf29b2d3b083b356`
-   5. Substantivos — `fo_871588e4afeabfa9`
-   6. Adjetivos — `fo_19f8a20dc907b62d`
-   7. Pronomes — `fo_f0e1374ea14ed9e6`
-   8. Verbos — `fo_4d1051c58bdc3742`
-   9. Advérbios — `fo_5e829d58dea8615e`
-  10. Sujeito — `fo_33e79f437a63da50`
-  11. Predicado — `fo_9b88f14644afa607`
-  12. Termos integrantes da oração — `fo_19dd95a2aba410bc`
-  13. Termos acessórios da oração — `fo_63e7ffa38ad36c1d`
-  14. Concordância verbal — `fo_49a5349f55861585`
-  15. Concordância nominal — `fo_17021b7d2f976750`
-  16. Regência Verbal + Nominal — `fo_9cf898b039232c80`
-  17. Crase — `fo_3e33e744a69d84dc`
-  18. Colocação pronominal — `fo_a6335c2a5468d904`
-  19. Oração coordenada — `fo_bf183b657a3df234`
-  20. Oração subordinada substantiva — `fo_d9181af5e2361bd1`
-  21. Oração subordinada adjetiva — `fo_3d09daae3057c9b6`
-  22. Oração subordinada adverbial — `fo_38cac52de6ca0c35`
-  23. Pontuação — `fo_6a5130f23812d1e8`
-  24. Aula extra - Exercícios: Fonologia — `fo_353b5c6f1fab015d`
-  25. Aula extra - Exercícios: Acentuação — `fo_dad9a6c7b2f66c9a`
-  26. Aula extra - Exercícios: Emprego do hífen — `fo_4dcd9916e2e2d627`
-  27. Aula extra - Exercícios: Estrutura e formação de palavras I — `fo_8abb0fd9d8a08c40`
-  28. Aula extra - Exercícios: Estrutura e formação de palavras II — `fo_228abfa2d90d8da8`
-  29. Aula extra - Exercícios: Substantivo — `fo_8d8fe6d50bd57ec4`
-  30. Aula extra - Exercícios: Adjetivos — `fo_db2eac9495f7ef8b`
-  31. Aula extra - Exercícios: Pronomes — `fo_6f0b1422f0307698`
-  32. Aula extra - Exercícios: Verbos — `fo_041f0e8cc2068c17`
-  33. Aula extra - Exercícios: Advérbios — `fo_c92a51e065bdf69e`
-  34. Aula extra - Exercícios: Sujeito e predicado — `fo_71e9095910c02d8a`
-  35. Aula extra - Exercícios: Concordância verbal — `fo_aedcd3f2c8993fa3`
-  36. Aula extra - Exercícios: Regência verbal + nominal — `fo_a9a896e68b30018f`
-  37. Aula extra - Exercícios: Crase — `fo_b88ff262a9c3d8aa`
-  38. Aula extra - Exercícios: Colocação pronominal — `fo_5dd5f77c504df7fd`
-  39. Aula extra - Exercícios: Oração coordenada — `fo_c59edf5ed4e8b813`
-  40. Aula extra - Exercícios: Oração subordinada substantiva — `fo_75599efb5eaa1d2d`
-  41. Aula extra - Exercícios: Oração subordinada adverbial — `fo_b97c3850ab651f30`
-  42. Aula extra - Exercícios: Pontuação — `fo_5c33489a227ca741`
-  43. Aula extra - Exercícios: Figuras de linguagem — `fo_4512b431e53e7800`
-  44. Aula extra - Exercícios: UFPR 2019-2020 — `fo_52476dea76972850`
-  45. Aula extra - Exercícios: UFPR 2017-2018 e 2018-2019 — `fo_06fef310263e1013`
-  46. Aula extra - Exercícios: UFPR 2016-2017 e outras questões do NC-UFPR — `fo_23aae8083189706a`
-  47. Aula extra - Exercícios: UFPR 2014-2015 e outras questões do NC-UFPR — `fo_82d99057f29fc96f`

#### Química I


##### Química I


**Química I** (30 aulas)

-   1. Classificação da matéria — `fo_692cc76a8697a97a`
-   2. Separação de misturas — `fo_599ef20ecd503cab`
-   3. Leis ponderais — `fo_c45544669bf5371c`
-   4. Balanceamento — `fo_228b313ad2c6cde8`
-   5. Modelos atômicos — `fo_942e2409f128165c`
-   6. Átomo de Bohr e Distribuição eletrônica — `fo_e8497cdd59a5686c`
-   7. Organização da tabela periódica — `fo_8d61ee867e8dff8c`
-   8. Tendências periódicas — `fo_56aec452eed891ef`
-   9. Ligações covalentes — `fo_b72bfc52b9f70b35`
-  10. Ligações iônicas e metálicas — `fo_52e1efbbffc815cc`
-  11. Geometria molecular e Polaridade — `fo_b7c2a599be506905`
-  12. Forças intermoleculares — `fo_7d13b6fb212249f9`
-  13. NOX — `fo_e37708f52972fb50`
-  14. Exercícios sobre química geral — `fo_83ae2bd4482f7655`
-  15. Ácidos I — `fo_bd36550fdd154f8b`
-  16. Ácidos II — `fo_117508d65e099da8`
-  17. Bases — `fo_2999136a4a5a3953`
-  18. Sais — `fo_8da04f851b13807f`
-  19. Óxidos — `fo_61bd55e41c36837b`
-  20. Reações inorgânicas — `fo_1232b31bb51fc5f2`
-  21. Definição de soluções — `fo_40fe51f8f708289b`
-  22. Concentração de soluções — `fo_ffd8c225f2fc9c7b`
-  23. Mistura de soluções — `fo_27ea6f2ad66ad7a5`
-  24. Propriedades coligativas — `fo_cb19eb03bc2d40ed`
-  25. Exercícios sobre soluções — `fo_a32f5dd10e3df0f3`
-  26. Radioatividade I — `fo_9d78a835190bdaa3`
-  27. Radioatividade II — `fo_4533e71ac72ab5ee`
-  28. Números quânticos e Carga formal — `fo_07c3993ba6eaf989`
-  29. Teoria ácido-base de Bronsted-Lowry e Lewis — `fo_4a0a7d95f223c51a`
-  30. Química ambiental — `fo_88ad0ffde53113dd`

#### Química II


##### Química II


**Química II** (30 aulas)

-   1. Relações de massa — `fo_f730ab9ceb3eaf0b`
-   2. Relações de massa e mol — `fo_d02d86b438a3d9d9`
-   3. Determinação de fórmulas químicas e Isotopia — `fo_6a047fc982c756e7`
-   4. Gases I — `fo_47d2ae841984870e`
-   5. Gases II — `fo_0c7a843808e7b8da`
-   6. Balanceamento — `fo_13c706a2e28016c5`
-   7. Estequiometria — `fo_d70da1a2894361f9`
-   8. Pureza e Hidratação — `fo_282e36284e08d583`
-   9. Exercícios sobre estequiometria — `fo_20d5f4af14025c1c`
-  10. Reações termoquímicas — `fo_7ac045c0a3f02ee6`
-  11. Entalpia — `fo_7a36e960498c0b09`
-  12. Lei de Hess — `fo_aa93fc3321a8347f`
-  13. Leis da termodinâmica — `fo_628478d148e15c68`
-  14. Oxirredução — `fo_2cf87009fee88f65`
-  15. Pilhas I — `fo_eec57babefe42e31`
-  16. Pilhas II — `fo_f798810fe1739378`
-  17. Eletrólise — `fo_d7c9560a21f5a91e`
-  18. Eletrólise II — `fo_fa5ee8191641c604`
-  19. Exercícios sobre eletroquímica e termoquímica — `fo_62c09ba677547b23`
-  20. Cinética química I — `fo_ff84b7aea596ca09`
-  21. Cinética química II — `fo_e72c7007290c8f12`
-  22. Equilíbrio químico I — `fo_ab3afd8d20fde8c1`
-  23. Equilíbrio químico II — `fo_bed2402154cc46f9`
-  24. Equilíbrio iônico — `fo_d1382680bdec0cc7`
-  25. Exercícios sobre cinética química e equilíbrio — `fo_1894a636a87ba84f`
-  26. pH — `fo_40d0fe8f03a7da7a`
-  27. Hidrólise salina — `fo_f6d09d3fbeb1fac0`
-  28. Solução tampão — `fo_18b239eea53c7932`
-  29. Produto de solubilidade (kps) — `fo_9c1bcf4c20380418`
-  30. Exercícios finais — `fo_e1d454eea1e5101e`

#### Química III


##### Química III


**Química III** (30 aulas)

-   1. Introdução à orgânica — `fo_15805d159ce2af34`
-   2. Cadeias carbônicas — `fo_c8aa64138685460f`
-   3. Hibridização e aromaticidade — `fo_e518198e8a571841`
-   4. Hidrocarbonetos de cadeia normal — `fo_71f339a71b0faee6`
-   5. Hidrocarbonetos de cadeia ramificada — `fo_dfee8a8c020cea63`
-   6. Hidrocarbonetos aromáticos — `fo_5eaa46046c6bfb23`
-   7. Exercícios sobre cadeias carbônicas — `fo_841f6072db63352f`
-   8. Álcoois, enóis e fenóis — `fo_33bfff611d0d6326`
-   9. Aldeídos e cetonas — `fo_cb58ae74832cc1fe`
-  10. Ácidos carboxílicos — `fo_5e8d746e0f56a006`
-  11. Ésteres e anidridos — `fo_1b038f92471fa07d`
-  12. Funções nitrogenadas e demais funções — `fo_700f0cff08a380fb`
-  13. Exercícios sobre funções orgânicas — `fo_663420a30419cfa6`
-  14. Isomeria plana — `fo_5bdb4b77269974d1`
-  15. Isomeria geométrica — `fo_653952a8ede94939`
-  16. Isomeria óptica — `fo_e8390ff74f6598c0`
-  17. Exercícios sobre isomeria — `fo_e36cebddc90f289d`
-  18. Propriedades de compostos orgânicos — `fo_b9e5d538e74fd0bc`
-  19. Teorias ácido-base e Configuração R e S — `fo_8792ab707188ddd6`
-  20. Reação de substituição — `fo_451fb7c0aa066cd7`
-  21. Reação de substituição e neutralização — `fo_0f706dd697385ce4`
-  22. Reação de adição — `fo_be0dea4e38cac848`
-  23. Reação de oxidação/redução — `fo_44bdc80cf74d8aca`
-  24. Reação de eliminação — `fo_dd9d6dd5e817d397`
-  25. Exercícios sobre reações orgânicas — `fo_acec99cc15a9b68d`
-  26. Polímeros — `fo_a580bbd94d0c4de5`
-  27. Reação de polimerização — `fo_0aa7b0637af7ad8d`
-  28. Bioquímica — `fo_6bb0821fd4b1bafb`
-  29. Exercícios sobre polimerização — `fo_40c766d33412b7ec`
-  30. Revisão geral — `fo_1b205f187be54069`

#### Redação UFPR


##### Redação UFPR


**Aulas** (52 aulas)

-   1. Entendendo o edital — `fo_1fe27d2cdcf6e0e7`
-   2. Ajeitando a estrutura — `fo_5b61925361cf3d73`
-   3. Dissertativo-argumentativo I — `fo_c3d77bf8036f1082`
-   4. Dissertativo-argumentativo II — `fo_f412a838efdfa7e3`
-   5. Dissertativo-argumentativo III — `fo_44619341188b9019`
-   6. Dissertativo-argumentativo IV — `fo_f2970a022c066970`
-   7. Dissertativo-argumentativo V — `fo_451b82c034c7e1ab`
-   8. Transposição de Discurso — `fo_f01f5239e6cfe0a8`
-   9. Continuação Textual I — `fo_97249c8424bf9c5f`
-  10. Continuação Textual II — `fo_948532dd22006b50`
-  11. Narrativa — `fo_1756e69ef00419ef`
-  12. Interpretação de Poemas — `fo_796b6fd1ff55fbe4`
-  13. Interpretação de Tira — `fo_c83bb416e4af9748`
-  14. Interpretação de Charge I — `fo_8fb6977495883def`
-  15. Interpretação de Charge II — `fo_67deb434a59665fc`
-  16. Notícia de jornal — `fo_dce5982e1c301c00`
-  17. Carta — `fo_809733f223a8c81c`
-  18. Gráficos, Infográficos e Mapas I — `fo_8313a058e169f989`
-  19. Gráficos, Infográficos e Mapas II — `fo_f261c06bcc4e58e3`
-  20. Gêneros diversos — `fo_f731d56da170538c`
-  21. Revisando a redação — `fo_f223437ae26154cf`
-  22. Aula extra - Memorial — `fo_815d89024d5bfff8`
-  23. Aula extra - Estratégias na redação — `fo_629ee9e225c34fa7`
-  24. Aula extra - Estratégias na redação e gêneros diversos — `fo_98cba2e08f00d079`
-   - Ajeitando a estrutura do texto (Aula do curso de 2025) — `fo_479a7c303fcc6872`
-   - Carta I — `fo_7260c89b1edf80d2`
-   - Carta II (Aula do curso de 2025) — `fo_1da635447b4a2426`
-   - Charge I (Aula do curso de 2025) — `fo_35a0b719945de1c8`
-   - Charge II (Aula do curso de 2025) — `fo_3ef5b0dddbd5d21d`
-   - Continuação de texto I (Aula do curso de 2025) — `fo_5cf14805762c0dd3`
-   - Continuação de texto II (Aula do curso de 2025) — `fo_0b1edc82ce2426c0`
-   - Dissertação (Aula do curso de 2025) — `fo_72926c6afe3b8a84`
-   - Dissertação - Exemplo I (Aula do curso de 2025) — `fo_fd525d231272ef27`
-   - Dissertação - Exemplo II (Aula do curso de 2025) — `fo_18b39cd5c27805ac`
-   - Dissertação - Exemplo III (Aula do curso de 2025) — `fo_d0fa1869cf69b128`
-   - Dissertação - Exemplo IV (Aula do curso de 2025) — `fo_50a3d5fffd59849e`
-   - Dissertação - Nota máxima I (Aula do curso de 2025) — `fo_edc63eb9c3418451`
-   - Dissertação - Nota máxima II (Aula do curso de 2025) — `fo_0a144fdc4bb126a9`
-   - Dissertação - Nota zero (Aula do curso de 2025) — `fo_650991743fa1f94c`
-   - Dissertação - Redações adequadas I (Aula do curso de 2025) — `fo_19c09060e0ef0598`
-   - Dissertação - Redações adequadas II (Aula do curso de 2025) — `fo_5e8e4f6b9fd3844d`
-   - Fábula (Aula do curso de 2025) — `fo_00dc19c89d67bedd`
-   - Gráficos e infográficos (Aula do curso de 2025) — `fo_c9111d0c83048aae`
-   - Gêneros diversos (Aula do curso de 2025) — `fo_9e528c126195447d`
-   - Narrativa (Aula do curso de 2025) — `fo_00c7d2f8cf6c554e`
-   - Notícia de jornal — `fo_69122bf66c4c5745`
-   - Poema (Aula do curso de 2025) — `fo_519b80dbd9513825`
-   - Revisando a redação (Aula do curso de 2025) — `fo_e2314b71686318b0`
-   - Tirinha I (Aula do curso de 2025) — `fo_f7a2ee801ae8bf85`
-   - Tirinha II (Aula do curso de 2025) — `fo_7fa13ad8161368db`
-   - Transposição de discurso I (Aula do curso de 2025) — `fo_62c47132ad71f013`
-   - Transposição de discurso II (Aula do curso de 2025) — `fo_791feead02717af2`

#### Reprodução - Foco ENEM - Extras


##### Reprodução - Foco ENEM


**Reprodução - Foco ENEM** (2 aulas)

-   1. Gametogênese — `fo_abb94f5e5437df17`
-   2. Fecundação e Ciclo menstrual — `fo_957bdaeddeefbbe9`

#### Sociologia Geral


##### Sociologia Geral


**Aulas** (21 aulas)

-   1. Introdução à sociologia — `fo_5bb06cc827b048fb`
-   2. Émile Durkheim — `fo_f75be3e867ac6b78`
-   3. Karl Marx — `fo_5ad69c3d90209c3b`
-   4. Max Weber — `fo_8d7cbabdb339e806`
-   5. Trabalho e sociedade — `fo_fbc62cb49059059f`
-   6. Política e poder — `fo_a069169f3b2852db`
-   7. Globalização — `fo_7b78b970fa1e446f`
-   8. Direitos humanos — `fo_4c6d542fcae7a0a1`
-   9. Desigualdades sociais — `fo_4b27bb7157a827e4`
-  10. Indivíduos e natureza — `fo_d3580cbf9082013f`
-  11. Gênero e identidade — `fo_2eb794bc3bbdee67`
-  12. Diversidade religiosa — `fo_492232b5a51294a0`
-  13. Movimentos sociais — `fo_d7df238868d9fb81`
-  14. Indústria cultural — `fo_4d788c23db76bb43`
-  15. Socialização — `fo_2ad8d4fac1e17333`
-  16. Aspectos culturais — `fo_a544ed16aadd1c66`
-  17. Diversidade cultural — `fo_df4cade378e0bce9`
-  18. Sociedade brasileira — `fo_71a66631d4ff5f2e`
-  19. Cultura e política — `fo_3072a6eb58cd2c98`
-  20. Tecnologia e sociedade — `fo_fc30b4b9a3e2014b`
-   - Globalização — `fo_60379f0cc0d22a5b`

#### Sociologia UFPR


##### Sociologia UFPR


**Sociologia UFPR** (61 aulas)

-   1. Introdução às ciências sociais — `fo_99aa625c891efe6d`
-   2. Émile Durkheim: Instituições e fato social — `fo_ce5d50f83bb23770`
-   3. Émile Durkheim: Fato social normal e anomia — `fo_10713807b2a08fc4`
-   4. Émile Durkheim: Solidariedade mecânica e orgânica — `fo_12f9ceab4de79f99`
-   5. Max Weber: Sociologia compreensiva e ações sociais — `fo_6901b110dd4642ab`
-   6. Max Weber: Tipo ideal — `fo_2389565bfe3e02d6`
-   7. Max Weber: Dominação e desencantamento do mundo — `fo_216b1125a2121a96`
-   8. Karl Marx: Fontes do marxismo — `fo_6165df614b4afad8`
-   9. Karl Marx: Concepção de sociedade, base e superestrutura — `fo_b8c6f7291bffeabc`
-  10. Karl Marx: Mais-valia e alienação — `fo_9741a6402fa0021a`
-  11. As Clássicas do Pensamento Social: Introdução — `fo_d1c146bcb47151c0`
-  12. 1º Capítulo: Harriet Martineau — `fo_82d8596b2ae8ea14`
-  13. 2º Capítulo: Anna Júlia Cooper — `fo_851134e954604de1`
-  14. 3º Capítulo: Pandita Ramabai — `fo_846818153a8791b3`
-  15. 4º Capítulo: Charlotte Gilman — `fo_89c4d574dd227dac`
-  16. 5º Capítulo: Olive Schreiner — `fo_180a6d6632e96534`
-  17. 6º Capítulo: Alexandra Kollontai — `fo_634ea0301f4b8d12`
-  18. 7º Capítulo: Ercília Nogueira Cobra — `fo_4b6e84e23feffdf8`
-  19. 8º Capítulo: Alfonsina Storni — `fo_c5828034fd88e859`
-  20. O pacto da branquitude - Introdução — `fo_26b6629506b6660a`
-  21. Pacto narcísico (branquitude e colonização europeia) — `fo_eff31ce7f50e67ca`
-  22. Capitalismo racial — `fo_626a010cf4e5c343`
-  23. Racismo institucional — `fo_3719b586b2bc4990`
-  24. O caso das mulheres — `fo_2ebb423daab0448a`
-  25. Projetos de transformação — `fo_63fe401480a47d07`
-  26. Quem tem medo do gênero? - Introdução — `fo_8610559780d90112`
-  27. O cenário global — `fo_e81c3deec1b42672`
-  28. Feminismo radical — `fo_8089e3eb1c9ada69`
-  29. Natureza e cultura — `fo_dded566f95a8a469`
-  30. O medo da destruição — `fo_e81838273b624eb1`
-  31. Sobre o autoritarismo no Brasil - Introdução — `fo_a67cbf4019984aba`
-  32. Escravidão e mandonismo — `fo_79e3f8af053af5b9`
-  33. Patrimonialismo e corrupção — `fo_f3479e14aff6ae4d`
-  34. Desigualdade social — `fo_79e3aedda7e2ae95`
-  35. Raça e gênero — `fo_ffeab66bb4d90eea`
-   - Auguste Comte (aula do curso 2025) — `fo_c9142ec5bc45858f`
-   - Clássicas Do Pensamento Social - 1º Capítulo: Harriet Matineau (aula do curso 2025) — `fo_b2c7f48d058e2673`
-   - Clássicas Do Pensamento Social - 2º Capítulo: Ana Júlia Copper (aula do curso 2025) — `fo_1df8b1848e6d9ef2`
-   - Clássicas Do Pensamento Social - 3º Capítulo: Pandita Ramabai (aula do curso 2025) — `fo_62147c25551bac4f`
-   - Clássicas Do Pensamento Social - 4º Capítulo: Charlotte Gilman (aula do curso 2025) — `fo_8e2984a4ccdda7f3`
-   - Clássicas Do Pensamento Social - 5º Capítulo: Olive Shreiner (aula do curso 2025) — `fo_2f92c6c911590fc8`
-   - Clássicas Do Pensamento Social - 6º Capítulo: Alexandra Kollontai (aula do curso 2025) — `fo_35ad79718b687e28`
-   - Clássicas Do Pensamento Social - 7º Capítulo: Ercília Nogueira Cobra (aula do curso 2025) — `fo_63c9780c16f56bca`
-   - Clássicas Do Pensamento Social - 8° Capítulo: Alfonsini Storni (aula do curso 2025) — `fo_d119cc54f9cd0208`
-   - Clássicas Do Pensamento Social - Antropologia nos séculos XIX e XX (aula do curso 2025) — `fo_06ac716d2e76f9c1`
-   - Clássicas Do Pensamento Social - Introdução (aula do curso 2025) — `fo_f3eeb2baffe89f9e`
-   - Introdução às Ciências Sociais (aula do curso 2025) — `fo_66dbfd7dec94fc2c`
-   - Pacto da Branquitude - Branquitude e Colonização Europeia (aula do curso 2025) — `fo_b8f56995708a5fb7`
-   - Pacto da Branquitude - Capitalismo Racial (aula do curso 2025) — `fo_d6afe682a917238f`
-   - Pacto da Branquitude - O Caso das Mulheres (aula do curso 2025) — `fo_a83432802da29986`
-   - Pacto da Branquitude - Projetos de Transformação (aula do curso 2025) — `fo_6691ec57fe566006`
-   - Pacto da Branquitude - Racismo Institucional (aula do curso 2025) — `fo_8ab2c427143e28bb`
-   - Um toque de clássicos - Karl Marx: Concepção de sociedade, base e superestrutura (aula do curso 2025) — `fo_84eeea6eb901204c`
-   - Um toque de clássicos - Karl Marx: Fontes do marxismo (aula do curso 2025) — `fo_7448452da608fbe6`
-   - Um toque de clássicos - Karl Marx: Mais Valia e alienação (aula do curso 2025) — `fo_ce290c389c7476c8`
-   - Um toque de clássicos - Max Weber: Dominação e desencantamento do mundo (aula do curso 2025) — `fo_01e617ec5a15c403`
-   - Um toque de clássicos - Max Weber: Sociologia compreensiva e ações sociais (aula do curso 2025) — `fo_ce4791fa3f84a88e`
-   - Um toque de clássicos - Max Weber: Tipo Ideal (aula do curso 2025) — `fo_1abd0f833e5f8912`
-   - Um toque de clássicos - Èmile Durkheim: Fato social normal e anomia (aula do curso 2025) — `fo_2111dcc100a80a35`
-   - Um toque de clássicos - Èmile Durkheim: Instituições e Fato Social (aula do curso 2025) — `fo_7b0fea7fead8097b`
-   - Um toque de clássicos - Èmile Durkheim: Solidariedade mecânica e orgânica (aula do curso 2025) — `fo_dc33a4eccf9bdb23`

### Intensivo UFPR 2026


#### Anki - Flashcards


##### Anki - Flashcards


**Vídeos** (5 aulas)

-   1. Introdução ao Anki — `fo_e1386eb25e598623`
-   2. Como baixar o Anki — `fo_4854d90c56501fa4`
-   3. Como funcionam os Flashcards? — `fo_48427a84932368d0`
-   4. Como fazer os seus próprios Flashcards? — `fo_fc626c6f3aa098fe`
-   5. Como baixar os Cards do FO no Anki — `fo_88f16005d8c65aa9`

#### Biologia - Exercícios


##### Biologia - Exercícios


**Biologia - Exercícios** (30 aulas)

-   1. Bioquímica — `fo_5fff36e9eeebf3f2`
-   2. Membrana e Transporte — `fo_2a84ba1ebb16d941`
-   3. Organelas — `fo_9b90c5da7112791e`
-   4. Bioenergética — `fo_86307c2dd5ba3e22`
-   5. Divisão celular — `fo_ec69d488ba1a0743`
-   6. Primeira lei de Mendel e Heredogramas — `fo_c156b1afc739c0e6`
-   7. Segunda lei de Mendel — `fo_4ae47ea3fea94d70`
-   8. Herança sexual e Sistema ABO — `fo_e451970a72fe5249`
-   9. Biologia molecular — `fo_4c6f697516cff08c`
-  10. Biotecnologia — `fo_0117a02c7a4bedde`
-  11. Teoria sintética da evolução — `fo_8f8100ef6a083fd7`
-  12. Tipos de seleção e Evidências evolutivas — `fo_954af431e27d1f29`
-  13. Taxonomia e Microbiologia — `fo_eae7d681d1f64b4b`
-  14. Botânica I — `fo_a17f0efa29b52124`
-  15. Botânica II — `fo_c191af111d0a4c55`
-  16. Zoologia I — `fo_966d1609a07a6792`
-  17. Zoologia II — `fo_eced8db064374847`
-  18. Fisiologia animal comparada — `fo_f4fd34a149b7c14f`
-  19. Histologia animal — `fo_8e0fbcb5efa981aa`
-  20. Sistema endócrino — `fo_bf4369b0ea6960ab`
-  21. Sistema circulatório e Sistema respiratório — `fo_684e99d390ba3aa4`
-  22. Sistema digestório e Sistema urinário — `fo_9fc0d2591c4a59fd`
-  23. Viroses e Bacterioses — `fo_ba51df7db953234b`
-  24. Protozooses e Verminoses — `fo_8873725b8585cda8`
-  25. Sistema imunológico — `fo_9703245e7ed58b6f`
-  26. Cadeia e teia alimentar — `fo_6fe6e7cc49a03f4c`
-  27. Pirâmides ecológicas e Produtividade — `fo_31186ef4a80de914`
-  28. Relações ecológicas — `fo_fcf890ee923c53f4`
-  29. Ciclos biogeoquímicos — `fo_255d1d2d683afebd`
-  30. Problemas ambientais — `fo_ae11f3faa7fd09d1`

#### Biologia - Teoria


##### Biologia - Teoria


**Biologia - Teoria** (30 aulas)

-   1. Bioquímica — `fo_135c415d8080927f` ✓validada
-   2. Membrana e Transporte — `fo_4ed9b21e0b57f771`
-   3. Organelas — `fo_eb05fd8938210647`
-   4. Bioenergética — `fo_01c6dea4d18483ff`
-   5. Divisão celular — `fo_8f4b863409f49c3c`
-   6. Primeira lei de Mendel e Heredogramas — `fo_1ca42ab86fd9c310`
-   7. Segunda lei de Mendel — `fo_3034dfb5c9320905`
-   8. Herança sexual e Sistema ABO — `fo_9fa683f3121066f0`
-   9. Biologia molecular — `fo_260d109083791e05`
-  10. Biotecnologia — `fo_9d6dc1e8e790e819`
-  11. Teoria sintética da evolução — `fo_fab694dbd3076e7b`
-  12. Tipos de seleção e Evidências evolutivas — `fo_8796bef5611f27b1`
-  13. Taxonomia e Microbiologia — `fo_014ae006b9e12ac6`
-  14. Botânica I — `fo_1aa38be757fea852`
-  15. Botânica II — `fo_9728c81eed9c71ff`
-  16. Zoologia I — `fo_9d247a657c531602`
-  17. Zoologia II — `fo_0aa7d252c34d8391`
-  18. Fisiologia animal comparada — `fo_9f3d4958bc33bc3c`
-  19. Histologia animal — `fo_95e3a4a4a5e73985`
-  20. Sistema endócrino — `fo_dd09cccd372d143b`
-  21. Sistema circulatório e Sistema respiratório — `fo_6703b8ae33b6640f`
-  22. Sistema digestório e Sistema urinário — `fo_0bbf3a6efa7c8eee`
-  23. Viroses e Bacterioses — `fo_70f13fd0b3b47f98`
-  24. Protozooses e Verminoses — `fo_d9020869b22302c1`
-  25. Sistema imunológico — `fo_1759602dcce06975`
-  26. Cadeia e teia alimentar — `fo_531c749ba159ee64`
-  27. Pirâmides ecológicas e Produtividade — `fo_450608e4eb6b863d`
-  28. Relações ecológicas — `fo_1083512f5f6a4a86`
-  29. Ciclos biogeoquímicos — `fo_09df48c248d82691`
-  30. Problemas ambientais — `fo_131c23e82b95e0e7`

#### Caderno de erros


##### Caderno de erros


**Caderno de erros** (1 aulas)

-   1. Caderno de erros — `fo_17425f161bfd392a`

#### Espanhol - Exercícios


##### Espanhol - Exercícios


**Espanhol - Exercícios** (5 aulas)

-   1. Identificación de ideas — `fo_b9791e24f3a287bb`
-   2. Inferencia e Intención — `fo_43254eb369a00642`
-   3. Clases gramaticales — `fo_cb1727688a04d787`
-   4. Semántica — `fo_0b4a1f87312e8559`
-   5. Expresiones y Conocimientos del mundo — `fo_3ac761ea3aaf2d1c`

#### Espanhol - Teoria


##### Espanhol - Teoria


**Espanhol - Teoria** (5 aulas)

-   1. Identificación de ideas — `fo_4cc5e44ffb6dc603`
-   2. Inferencia e Intención — `fo_c2f92ae13a2b2917`
-   3. Clases gramaticales — `fo_f8ec00b77041e1fc`
-   4. Semántica — `fo_63dcc0ddce75a9ea`
-   5. Expresiones y Conocimientos del mundo — `fo_2cae30a244a43d11`

#### Filosofia - Exercícios


##### Filosofia - Exercícios


**Filosofia - Exercícios** (5 aulas)

-   1. Mito de Er — `fo_05e70342932c0af2` ✓validada
-   2. Discurso sobre a desigualdade entre os homens — `fo_d33cc9c298a40f29` ✓validada
-   3. Lógica da Pesquisa Científica — `fo_83c500190efa8a12` ✓validada
-   4. Participação e Teoria Democrática — `fo_67085294c1430d65` ✓validada
-   5. Dispositivo de Racialidade — `fo_0150f085e845e923` ✓validada

#### Filosofia - Teoria


##### Filosofia - Teoria


**Filosofia - Teoria** (5 aulas)

-   1. Mito de Er — `fo_d9f369413fd5cf40` ✓validada
-   2. Discurso sobre a desigualdade entre os homens — `fo_d4729050d08d6758` ✓validada
-   3. Lógica da Pesquisa Científica — `fo_d3b85582677ba9cb` ✓validada
-   4. Participação e Teoria Democrática — `fo_51807766beb78c82` ✓validada
-   5. Dispositivo de Racialidade — `fo_5a11589ea178a152`

#### Física - Exercícios


##### Física - Exercícios


**Física - Exercícios** (30 aulas)

-   1. Unidades de medida e Análise Dimensional — `fo_55243adb14f5c2a5`
-   2. MRU — `fo_4bafd25c15bf6598`
-   3. MRUV — `fo_1f921f6edf7f9926` ✓validada
-   4. Gráficos da Cinemática — `fo_f683fcc8560d59d5` ✓validada
-   5. Queda Livre e Lançamentos — `fo_cb11971f03e9cbf1` ✓validada
-   6. Movimento Circular Uniforme — `fo_c0b8df75e2eb86fe`
-   7. Leis de Newton e Aplicações — `fo_2aadb5245beaa18d` ✓validada
-   8. Equilíbrio de um Ponto Material — `fo_6df4907c116802ed`
-   9. Equilíbrio de um Corpo Extenso — `fo_54b06bc5c67ad954`
-  10. Trabalho e Energia Mecânica — `fo_be0bb4362ced545d`
-  11. Impulso e Quantidade de Movimento — `fo_c5a3a423c35ee6ef`
-  12. Hidrostática — `fo_5c623b7dd096e89b`
-  13. Termometria — `fo_7a9f3b8d5bd77945`
-  14. Calorimetria — `fo_19443753933df98b`
-  15. Transformações Gasosas — `fo_926d3a8c3cfa9e54`
-  16. Diagrama P×V — `fo_6f5f4f8c49316e2b`
-  17. Termodinâmica — `fo_e7e0a0f9fa11a5f1`
-  18. Reflexão e Refração da Luz — `fo_219ef063c746f553`
-  19. Lentes Esféricas — `fo_49a1159e1d3cc1a8`
-  20. Equação Fundamental da Ondulatória — `fo_876970748d324e9b`
-  21. Ondas Estacionárias — `fo_4a8f13ce5dea6ff4`
-  22. Força Elétrica e Campo Elétrico — `fo_e269c41ba396a628`
-  23. Energia Potencial Elétrica e Potencial Elétrico — `fo_0ce28c33271fb684`
-  24. Leis de Ohm e Potência Elétrica — `fo_6e674e03b624f6dc`
-  25. Capacitores — `fo_334079d1b5c7f0e8`
-  26. Geradores e Receptores — `fo_26f739676bf3d05c`
-  27. Circuitos Elétricos — `fo_32e7dbdad8d95b49`
-  28. Força Magnética e Campo Magnético — `fo_9bd62b67382f3bb6`
-  29. Lei de Faraday-Lenz — `fo_a8423d62003d9d76`
-  30. Física Moderna — `fo_6a7b3cfdab7aea42`

#### Física - Teoria


##### Física - Teoria


**Física - Teoria** (30 aulas)

-   1. Unidades de medida e Análise Dimensional — `fo_ce6134240d753024` ✓validada
-   2. MRU — `fo_e7946c26c704c93f` ✓validada
-   3. MRUV — `fo_1155b8df8ef65ad0` ✓validada
-   4. Gráficos da Cinemática — `fo_677499e681561da8` ✓validada
-   5. Queda Livre e Lançamentos — `fo_a9376e5548abb07c` ✓validada
-   6. Movimento Circular Uniforme — `fo_ef9cc10f347cd99d` ✓validada
-   7. Leis de Newton e Aplicações — `fo_6965b4befdebda10` ✓validada
-   8. Equilíbrio de um Ponto Material — `fo_12746d8f111957a3`
-   9. Equilíbrio de um Corpo Extenso — `fo_a765c94a62488bd7`
-  10. Trabalho e Energia Mecânica — `fo_2fa7dfefe16055f7`
-  11. Impulso e Quantidade de Movimento — `fo_d2da37c1d896a72b`
-  12. Hidrostática — `fo_09a8d8f7891f21cb`
-  13. Termometria — `fo_8c884284da43309d`
-  14. Calorimetria — `fo_749920a8fe207f49`
-  15. Transformações Gasosas — `fo_2bd0d0eb90ca9821`
-  16. Diagrama P×V — `fo_13fda49c24c055ee`
-  17. Termodinâmica — `fo_8dab19c6273dd2f7`
-  18. Reflexão e Refração da Luz — `fo_957bbee567e39569`
-  19. Lentes Esféricas — `fo_0ebd3aebc1de8d1e`
-  20. Equação Fundamental da Ondulatória — `fo_fc7b381395f6e4ef`
-  21. Ondas Estacionárias — `fo_f730c1901b30136f`
-  22. Força Elétrica e Campo Elétrico — `fo_6f9445c9079e322e`
-  23. Energia Potencial Elétrica e Potencial Elétrico — `fo_7315dce8b375d872`
-  24. Leis de Ohm e Potência Elétrica — `fo_be3402e562fafbbe`
-  25. Capacitores — `fo_f479d8638885fc46`
-  26. Geradores e Receptores — `fo_3c79e82f094c3109`
-  27. Circuitos Elétricos — `fo_3040a4d17f6786da`
-  28. Força Magnética e Campo Magnético — `fo_500188d47c23a2d5`
-  29. Lei de Faraday-Lenz — `fo_9be799f2669f373b`
-  30. Física Moderna — `fo_3381de1cb0528f43`

#### Geografia - Exercícios


##### Geografia - Exercícios


**Geografia - Exercícios** (20 aulas)

-   1. Cartografia I — `fo_16194795ca2f92e8`
-   2. Cartografia II — `fo_c6780c2339744bb4`
-   3. Geologia — `fo_50778ff69697508d` ✓validada
-   4. Geomorfologia — `fo_f82d7f0e5fc27eef`
-   5. Climatologia — `fo_63c2313e22bfd982` ✓validada
-   6. Hidrologia — `fo_2a07cad9e96a681d`
-   7. Biomas — `fo_04fc98ac428d27e0`
-   8. Problemas ambientais — `fo_a1b71dce883a2deb`
-   9. Regionalizações I — `fo_c8cc581c23eb0a09`
-  10. Regionalizações II — `fo_891910718b118e59`
-  11. Demografia I — `fo_090cc8f19f88678c`
-  12. Demografia II — `fo_b0c82d9a28c31983`
-  13. População Brasileira — `fo_3ae5e1eeae57ba26`
-  14. Indústria e Energia — `fo_c6c4a0525d5afeee`
-  15. Urbana — `fo_5ddd7960eeed6d38`
-  16. Rural — `fo_41c9eff500d21ef6`
-  17. Geopolítica — `fo_d4d304667533de2e`
-  18. Economia — `fo_18de399ed24b6018`
-  19. Conflitos — `fo_f76422af17add36b`
-  20. Atualidades — `fo_e5971d9d2cebe675`

#### Geografia - Teoria


##### Geografia - Teoria


**Geografia - Teoria** (20 aulas)

-   1. Cartografia I — `fo_0978f8f807c122f4` ✓validada
-   2. Cartografia II — `fo_16c259dfbd8bdba6`
-   3. Geologia — `fo_391279f0161c9410` ✓validada
-   4. Geomorfologia — `fo_c73ac5ca72689248` ✓validada
-   5. Climatologia — `fo_1d43dc586ba55de1` ✓validada
-   6. Hidrologia — `fo_c6cfae9e41a9042a` ✓validada
-   7. Biomas — `fo_5c71a0b41fb6406b`
-   8. Problemas ambientais — `fo_7175ed9db1c7f5b1`
-   9. Regionalizações I — `fo_3724dd6acdad55f8`
-  10. Regionalizações II — `fo_4280dfaa1d8c2d14`
-  11. Demografia I — `fo_d5b257b609b5aea0`
-  12. Demografia II — `fo_ea3f10778b216f28`
-  13. População Brasileira — `fo_6428c247e951a6b2`
-  14. Indústria e Energia — `fo_30eca26428188e73`
-  15. Urbana — `fo_7b9d3ad096b4a9ef`
-  16. Rural — `fo_33d899ae628115f6`
-  17. Geopolítica — `fo_aec05b0b323345f8`
-  18. Economia — `fo_b8ea9129fbd1191c`
-  19. Conflitos — `fo_26cbba411d428ed0`
-  20. Atualidades — `fo_b6f637b8d77967ab`

#### História - Exercícios


##### História - Exercícios


**História - Exercícios** (25 aulas)

-   1. Grécia Antiga — `fo_dc3ab11af8cbf5f5` ✓validada
-   2. Roma Antiga — `fo_c4fc36f61eda92ac` ✓validada
-   3. Idade Média — `fo_2f7972942ef5c195`
-   4. Civilizações não europeias — `fo_a3024fb92bed07b5` ✓validada
-   5. Expansão Marítima e Renascimento — `fo_d2b689e046b87e6f`
-   6. Absolutismo — `fo_fd51da0795030b50` ✓validada
-   7. Revoluções burguesas — `fo_f3982c76fbcbd5e7`
-   8. Iluminismo e Revolução industrial — `fo_54690b4c3496ae63`
-   9. Independência das Américas — `fo_a54c4dcb2d8566f7`
-  10. Primeira Guerra Mundial — `fo_fd4cc80abb3afc88`
-  11. Segunda Guerra Mundial — `fo_a8e16ca3a26d5269`
-  12. Guerra Fria — `fo_8803826049e5dcb8`
-  13. Supremacia Americana — `fo_76e5121d6a82302b`
-  14. América Latina — `fo_96d8321c150d1ea4`
-  15. Movimentos Sociais — `fo_d4d7e5e25ee80079`
-  16. Brasil colônia I — `fo_db785e42852f780d`
-  17. Brasil colônia II — `fo_3d68e6b7c9ab0219`
-  18. Brasil colônia III — `fo_4d9fa82ac21da4a6`
-  19. Primeiro Reinado — `fo_8dae3883d8205fcd`
-  20. Segundo Reinado — `fo_ddbcd55a2b6c0cbe`
-  21. República Velha — `fo_9563a9d832af9d65`
-  22. Era Vargas — `fo_70a862a9493fff85`
-  23. República Populista — `fo_6a3eebdd6794fd20`
-  24. Ditadura Militar — `fo_cf6ac896d1a6568e`
-  25. Redemocratização — `fo_f842ad930365d1c5`

#### História - Teoria


##### História - Teoria


**História - Teoria** (25 aulas)

-   1. Grécia Antiga — `fo_99f7ab9544bb4e99` ✓validada
-   2. Roma Antiga — `fo_c5a6690775e7dae6` ✓validada
-   3. Idade Média — `fo_678b34290ecae085` ✓validada
-   4. Civilizações não europeias — `fo_be56fb001046187c` ✓validada
-   5. Expansão Marítima e Renascimento — `fo_197613d80e6e04fd` ✓validada
-   6. Absolutismo — `fo_e9d655943924c620` ✓validada
-   7. Revoluções burguesas — `fo_91787f7dc32c2047`
-   8. Iluminismo e Revolução industrial — `fo_3aaac3369a8425f5`
-   9. Independência das Américas — `fo_01a64dca0ce7803e`
-  10. Primeira Guerra Mundial — `fo_4a33697c0c98f496`
-  11. Segunda Guerra Mundial — `fo_35c7cc7e21643287`
-  12. Guerra Fria — `fo_1abc1eee6b4ecdca`
-  13. Supremacia Americana — `fo_ee77299f0da9e689`
-  14. América Latina — `fo_a0f09046df5c294c`
-  15. Movimentos Sociais — `fo_dbe87e1f54c54b73`
-  16. Brasil colônia I — `fo_13ab510ef33ad386`
-  17. Brasil colônia II — `fo_c52d5d76f08b95f6`
-  18. Brasil colônia III — `fo_7609da18c8a35ec9`
-  19. Primeiro Reinado — `fo_75a3432490779338`
-  20. Segundo Reinado — `fo_51efc754c1b62dd5`
-  21. República Velha — `fo_f7d11a01e274ea26`
-  22. Era Vargas — `fo_8bc2539ad3b5a85f`
-  23. República Populista — `fo_845578a9cee2ab0e`
-  24. Ditadura Militar — `fo_8cbb4a590e260ae5`
-  25. Redemocratização — `fo_bfc655edd55ab19a`

#### Inglês - Exercícios


##### Inglês - Exercícios


**Inglês - Exercícios** (5 aulas)

-   1. Linguistics - Variation and Registers — `fo_3877e8c5ad521ca1`
-   2. Syntax - Connectors and Logical Relations — `fo_bbde43d11a058170`
-   3. Point of View, Demonstrative Pronouns and Conjunctions — `fo_2967a0ac21704bc0`
-   4. Semantics, Idiomatic Expressions and Phrasal Verbs — `fo_c2b6a274995523c3`
-   5. Linguistic Variation, Syntax, and Critical Analysis — `fo_3feb88d13e270cc1`

#### Inglês - Teoria


##### Inglês - Teoria


**Inglês - Teoria** (5 aulas)

-   1. Linguistics - Variation and Registers — `fo_d876d085003dd47b`
-   2. Syntax - Connectors and Logical Relations — `fo_e3e7437fc5b8dee3`
-   3. Point of View, Demonstrative Pronouns and Conjunctions — `fo_39caebdeb12cd1b2`
-   4. Semantics, Idiomatic Expressions and Phrasal Verbs — `fo_f8f96bd63a1fb436`
-   5. Linguistic Variation, Syntax, and Critical Analysis — `fo_64c566ed3bbc3354`

#### Introdução


##### Introdução


**Introdução** (1 aulas)

-   1. Introdução aos métodos de estudo — `fo_40231c67a7e3cb55`

#### Literatura - Exercícios


##### Literatura - Exercícios


**Literatura - Exercícios** (8 aulas)

-   1. A Falência — `fo_1521678964925f45` ✓validada
-   2. Noite na Taverna — `fo_9effd7012c53e6e0` ✓validada
-   3. O Drible — `fo_89f8d3c32a2d3780` ✓validada
-   4. O Sol na Cabeça — `fo_99a96a4665b974a4` ✓validada
-   5. Poema Sujo — `fo_a039c9e4282944c1` ✓validada
-   6. Eu — `fo_63b5436e94c95250` ✓validada
-   7. O Demônio Familiar — `fo_aa62b0d61e8d9452`
-   8. O Quinze — `fo_5a0a309bc912a43e`

#### Literatura - Teoria


##### Literatura - Teoria


**Literatura - Teoria** (8 aulas)

-   1. A Falência — `fo_11dfe6966cdd813f` ✓validada
-   2. Noite na Taverna — `fo_408f4f895adb7e67` ✓validada
-   3. O Drible — `fo_a6d5579d1d378b42` ✓validada
-   4. O Sol na Cabeça — `fo_5253386d617a1f1e`
-   5. Poema Sujo — `fo_836372171d9432e4`
-   6. Eu — `fo_bdf8e4541f8b5280` ✓validada
-   7. O Demônio Familiar — `fo_534ac1cabb0f7acc`
-   8. O Quinze — `fo_463a01feca67dd3a`

#### Matemática - Exercícios


##### Matemática - Exercícios


**Matemática - Exercícios** (30 aulas)

-   1. Matemática Básica — `fo_bd74b4b7e030175f`
-   2. Equações e Inequações — `fo_c4cc56aee96d5e83` ✓validada
-   3. Porcentagem — `fo_bf84b23f784e4304` ✓validada
-   4. Razão e Proporção — `fo_feb6c7d31d0e0e91` ✓validada
-   5. Estatística — `fo_460e813da0ce2592`
-   6. Função Afim — `fo_8b79c2de69adc1f1`
-   7. Função Quadrática — `fo_a91317896b8927a3`
-   8. Função Exponencial — `fo_1bbd33a274c306ad`
-   9. Logaritmos — `fo_f3495ab818c6c6dd`
-  10. Juros — `fo_1cbcb63c57bbd06e`
-  11. Triângulos — `fo_5da7dc94729c8a5f`
-  12. Áreas — `fo_cd43613f6c2ce2a2`
-  13. Circunferência — `fo_d7cd863a83859711`
-  14. Trigonometria no Triângulo — `fo_a8911322a1474d6c`
-  15. Identidades Trigonométricas — `fo_f4a7a0a72df9e236`
-  16. Funções Trigonométricas — `fo_148de8fdffda573d`
-  17. Prismas — `fo_25d2c705db188b46`
-  18. Pirâmides — `fo_1bf6c466bc06c91d`
-  19. Cilindros e Cones — `fo_a72e8fae929c0ee7`
-  20. Esferas — `fo_b83389fd64f9dfca`
-  21. Geometria Analítica: Pontos e Retas — `fo_1bc348f1b00ae1a8`
-  22. Geometria Analítica: Circunferência — `fo_8bbb3379bd99fe6e`
-  23. Análise Combinatória — `fo_971b54e1a3f0ef54`
-  24. Probabilidade I — `fo_63b99ce094e6d590`
-  25. Probabilidade II — `fo_b8df60b04c61dbcd`
-  26. Matriz — `fo_228c670fe19cd319`
-  27. Sistemas de Equações — `fo_b781aae17646282c`
-  28. Polinômios — `fo_dd4d22e616530218`
-  29. Complexos — `fo_06add8681855a295`
-  30. Sequências — `fo_27d727082a210d1f`

#### Matemática - Teoria


##### Matemática - Teoria


**Matemática - Teoria** (30 aulas)

-   1. Matemática Básica — `fo_8e3b791bd95d1ffe` ✓validada
-   2. Equações e Inequações — `fo_3d061d56090bfeeb` ✓validada
-   3. Porcentagem — `fo_9ccbab762c166a3c`
-   4. Razão e Proporção — `fo_98283e78cf248f47` ✓validada
-   5. Estatística — `fo_959a02fa20e6bd93` ✓validada
-   6. Função Afim — `fo_5c3c3fb916d97fa8` ✓validada
-   7. Função Quadrática — `fo_bfb5d901624f3bed`
-   8. Função Exponencial — `fo_8dba9add5f071c83`
-   9. Logaritmos — `fo_962fba3195397c9b`
-  10. Juros — `fo_fb26c383504fb942`
-  11. Triângulos — `fo_f5b209060d05dd60`
-  12. Áreas — `fo_d8bb44fa5c511230`
-  13. Circunferência — `fo_a08c6489fe60e739`
-  14. Trigonometria no Triângulo — `fo_7bff055737121a49`
-  15. Identidades Trigonométricas — `fo_1a731c9a26076e7e`
-  16. Funções Trigonométricas — `fo_2ab3eaac68bb29e5`
-  17. Prismas — `fo_65dcb7f7fab621c3`
-  18. Pirâmides — `fo_27da615cb601d449`
-  19. Cilindros e Cones — `fo_c73bfa5130221264`
-  20. Esferas — `fo_f047438fcc3d9e38`
-  21. Geometria Analítica: Pontos e Retas — `fo_c8830d84768ec436`
-  22. Geometria Analítica: Circunferência — `fo_adc9e8a6710958f8`
-  23. Análise Combinatória — `fo_a0ef81ce2ac648c6`
-  24. Probabilidade I — `fo_ee9ed2df7239e17b`
-  25. Probabilidade II — `fo_b550caaa1a1224f7`
-  26. Matriz — `fo_534f6d0e68c91068`
-  27. Sistemas de Equações — `fo_5e2b42d72c42ce86`
-  28. Polinômios — `fo_804ba45c62c95728`
-  29. Complexos — `fo_cb9561137782c519`
-  30. Sequências — `fo_79b6d287b1a06bc3`

#### Método Pomodoro


##### Método Pomodoro


**Método Pomodoro** (1 aulas)

-   1. Método Pomodoro — `fo_ef8ce48bd2146458`

#### Método de Cornell


##### Método de Cornell


**Método de Cornell** (1 aulas)

-   1. Método de Cornell — `fo_aca048dc846fd7d1`

#### Método de Feynman


##### Método de Feynman


**Método de Feynman** (1 aulas)

-   1. Método de Feynman — `fo_a90dc5a1e43311be`

#### Português - Exercícios


##### Português - Exercícios


**Português - Exercícios** (12 aulas)

-   1. Identificação de ideias do texto — `fo_44d971c5aa722e0e`
-   2. Identificação da tese central do texto — `fo_082feeefff5192df` ✓validada
-   3. Identificação de argumentos — `fo_b753fea8716d7a6f` ✓validada
-   4. Identificação das marcas linguísticas — `fo_6c6c54de33f46df3` ✓validada
-   5. Efeitos de sentido e significação — `fo_bd5d71d21df394c6` ✓validada
-   6. Figuras de linguagem — `fo_7c7f491e336acb79`
-   7. Coesão conectiva — `fo_dd23f77584df2929`
-   8. Coesão referencial — `fo_f009d629dc80ee61`
-   9. Operações textuais — `fo_b083d3782ca2a515`
-  10. Pontuação — `fo_f111093bcf961636`
-  11. Verbos e sujeito — `fo_83242dd830d1834c`
-  12. Coordenadas e subordinadas — `fo_ff6efffb0d01a82a`

#### Português - Teoria


##### Português - Teoria


**Português - Teoria** (12 aulas)

-   1. Identificação de ideias do texto — `fo_6d8310919b9d3516` ✓validada
-   2. Identificação da tese central do texto — `fo_9491d82739ad843a` ✓validada
-   3. Identificação de argumentos — `fo_37d10a5958b99bba` ✓validada
-   4. Identificação das marcas linguísticas — `fo_e4a3945453ee9f94` ✓validada
-   5. Efeitos de sentido e significação — `fo_c7bae61ed53e1e65`
-   6. Figuras de linguagem — `fo_409adc43759b2c92`
-   7. Coesão conectiva — `fo_19b1c038338f1b3a` ✓validada
-   8. Coesão referencial — `fo_e118909fdbbd4678`
-   9. Operações textuais — `fo_f00c198f72997c80`
-  10. Pontuação — `fo_0b8bedb30fe4de80`
-  11. Verbos e sujeito — `fo_3d477217b39c7112`
-  12. Coordenadas e subordinadas — `fo_cdd5eb97adc6f011`

#### Química - Exercícios


##### Química - Exercícios


**Química - Exercícios** (30 aulas)

-   1. Organização da matéria — `fo_2e35202c6294c159`
-   2. Distribuição eletrônica — `fo_20fdfb3fac367654`
-   3. Tabela periódica — `fo_7a793ecda9a6957d`
-   4. Radioatividade — `fo_a38233316322b86d`
-   5. Ligações químicas — `fo_ef0595c032fdce29` ✓validada
-   6. Geometria molecular e Estrutura de Lewis — `fo_112b4ec8b72fc1ae`
-   7. Funções Inorgânicas — `fo_9c48da1a924603a1`
-   8. Soluções — `fo_da2aafd1c2b49ce6`
-   9. Propriedades coligativas — `fo_6a72f24511900fce`
-  10. Separação de misturas — `fo_8f7e75b193dd85d0`
-  11. Relações de massa e Leis ponderais — `fo_6f5f64d5b6d986a9`
-  12. Balanceamento — `fo_234059db9700049e`
-  13. Estequiometria — `fo_1cabbf2ef92c9a2a`
-  14. Estudo dos gases — `fo_6ed7fc840be3ead7`
-  15. Termoquímica — `fo_8f0f107d7ee50cdc`
-  16. Cinética química — `fo_e362f34fd2c62eba`
-  17. Equilíbrio químico — `fo_bb2a68c02b7c66de`
-  18. Equilíbrio iônico e Produto de solubilidade — `fo_b8c172ff7397d5e1`
-  19. NOX — `fo_67b8b2d9fb23f9a8`
-  20. Balanceamento Redox — `fo_dd22887e74ba380f`
-  21. Eletroquímica — `fo_23cd12545b845ed9`
-  22. Química Orgânica: Conceitos iniciais — `fo_714b9d6be097407e`
-  23. Funções orgânicas I — `fo_ca4eb0ddb8cc6e40`
-  24. Funções orgânicas II — `fo_c764d8b7cf58f14a`
-  25. Nomenclatura de compostos orgânicos — `fo_95747e298e748546`
-  26. Isomeria plan — `fo_528f655d57a19b6c`
-  27. Isomeria espacia — `fo_aa9bb1b62e1ce98d`
-  28. Reações de adição, eliminação e substituição — `fo_9184601ae83c68d1`
-  29. Reações de oxidação — `fo_7acdb39c596f8055`
-  30. Polímeros — `fo_26f15955062ea818`

#### Química - Teoria


##### Química - Teoria


**Química - Teoria** (30 aulas)

-   1. Organização da matéria — `fo_a32f71f7cfab8eb4` ✓validada
-   2. Distribuição eletrônica — `fo_457700aa96996d03`
-   3. Tabela periódica — `fo_c75cbfb0a297c1df` ✓validada
-   4. Radioatividade — `fo_4c5019ab3352c1da`
-   5. Ligações químicas — `fo_edf66441311ee288` ✓validada
-   6. Geometria molecular e Estrutura de Lewis — `fo_c553a7fe15ea8518`
-   7. Funções Inorgânicas — `fo_ffc2128800c4dd37`
-   8. Soluções — `fo_2d7d3b9b17021afa`
-   9. Propriedades coligativas — `fo_ba6901d4a8e77a31`
-  10. Separação de misturas — `fo_59bfe7dd1deee6ea`
-  11. Relações de massa e Leis ponderais — `fo_49c65e57898dd670`
-  12. Balanceamento — `fo_1b8878c3aecc2087`
-  13. Estequiometria — `fo_0121c4344f415e17`
-  14. Estudo dos gases — `fo_076cec256ad25581`
-  15. Termoquímica — `fo_a86edb7dd675ddf8`
-  16. Cinética química — `fo_57a838e2416e0f5f`
-  17. Equilíbrio químico — `fo_fbdf262042885bc3`
-  18. Equilíbrio iônico e Produto de solubilidade — `fo_e7c1b2b189478bc0`
-  19. NOX — `fo_08a6bdbeb8dbd581`
-  20. Balanceamento Redox — `fo_ac69e1528fe53c24`
-  21. Eletroquímica — `fo_20f60a3c74954e4e`
-  22. Química orgânica: Conceitos iniciais — `fo_6e8af3f77b65ffd2`
-  23. Funções orgânicas I — `fo_24f156a0352728cb`
-  24. Funções orgânicas II — `fo_a55b4cee033803df`
-  25. Nomenclatura de compostos orgânicos — `fo_5a01919296793371`
-  26. Isomeria plana — `fo_d99c71ee309ff940`
-  27. Isomeria espacial — `fo_6f42717c66c6c103`
-  28. Reações de adição, eliminação e substituição — `fo_08dc9daa19359352`
-  29. Reações de oxidação — `fo_a3f85f36e1d5fdb2`
-  30. Polímeros — `fo_868214e019681924`

#### Redação


##### Redação


**Redação** (4 aulas)

-   1. Dissertação-argumentativa — `fo_762f065208c3eba8`
-   2. Continuação textual — `fo_4e5678e4960bbc63`
-   3. Texto informativo — `fo_15b7c47066d14efa`
-   4. Interpretação de charge e tira — `fo_d6edf80d9016f394`

#### Sociologia - Exercícios


##### Sociologia - Exercícios


**Sociologia - Exercícios** (5 aulas)

-   1. Um toque de clássicos — `fo_3895d1b6f076917e` ✓validada
-   2. Clássicas do Pensamento Social — `fo_0870bebcebdef7f5` ✓validada
-   3. Pacto da Branquitude — `fo_64ffc368d89640d8` ✓validada
-   4. Quem tem medo do gênero? — `fo_fe3c35dc3eede401` ✓validada
-   5. Sobre o autoritarismo brasileiro — `fo_4044209bdc6b7f20` ✓validada

#### Sociologia - Teoria


##### Sociologia - Teoria


**Sociologia - Teoria** (5 aulas)

-   1. Um toque de clássicos — `fo_b47100b6d88da08a` ✓validada
-   2. Clássicas do Pensamento Social — `fo_944e470fa7c0c817` ✓validada
-   3. Pacto da Branquitude — `fo_cc9f5c29daa695af` ✓validada
-   4. Quem tem medo do gênero? — `fo_605547672634aef1` ✓validada
-   5. Sobre o autoritarismo brasileiro — `fo_f8bbaddd668536b2` ✓validada

### Matemática Básica


#### Curso de Matemática Básica


##### Curso de Matemática Básica


**Curso de Matemática Básica** (25 aulas)

-   1. Introdução — `fo_bcd2b30b7ee694e9`
-   2. Tabuada — `fo_c6a5aa9c4bd3e8b3`
-   3. Divisibilidade — `fo_0f0ca45ecbc4a65b`
-   4. Fatoração — `fo_74d3b93f9e07a387`
-   5. Exercícios sobre raízes — `fo_260c45ab39b7cd69`
-   6. MMC e MDC — `fo_202e75b94c121456`
-   7. Operações com Números Inteiros — `fo_768c0e616d92527b`
-   8. Exercícios sobre divisão — `fo_d5ca2f275131482f`
-   9. Operações com Números Decimais — `fo_212b4486be048e7d`
-  10. Operações com Frações (Parte 1) — `fo_82d6c2efc11f00fc`
-  11. Operações com Frações (Parte 2) — `fo_e630d8184ba32bb9`
-  12. Operações com Frações (Parte 3) — `fo_0aabe9f7bc0186f2`
-  13. Potenciação — `fo_979f6ea4321a5e75`
-  14. Radiciação — `fo_0d218ea5dd94cc97`
-  15. Expressões Numéricas (Parte 1) — `fo_f94c08e25aeb53cd`
-  16. Expressões Numéricas (Parte 2) — `fo_3eba2a8e11a90022`
-  17. Equação do 1º Grau — `fo_aca7fdd3fb152646`
-  18. Exercícios sobre Equação do 1° Grau — `fo_480e39561cb1f91b`
-  19. Equação do 2º Grau — `fo_b3223ad686f9dead`
-  20. Exercícios sobre Equação do 2° Grau — `fo_320768ee49750584`
-  21. Sistema de Equações — `fo_0ffeeb2e339ff71a`
-  22. Exercícios sobre Sistemas de Equações por substituição — `fo_85928cd2ee7314d6`
-  23. Exercícios sobre Sistemas de Equações por Cancelamento — `fo_4a9c0d23f9e45966`
-  24. Sistemas de Medidas (Parte 1) — `fo_d2a8a36423c1b376`
-  25. Sistemas de Medidas (Parte 2) — `fo_2701676cb6a8f5d6`

### Materiais exclusivos de medicina


#### Dicas finais


##### Dicas finais


**Dicas finais** (1 aulas)

-   1. Mensagens dos ex-vestibulandos :) — `fo_352df5590cea0674`

#### I - Período de estudos


##### I - Período de estudos


**I - Período de estudos** (2 aulas)

-   1. A pressão de estudar para o curso mais concorrido — `fo_c240b15bae746f61` ✓validada
-   2. Estratégias para lidar com a pressão — `fo_0d89f064b0f1a806` ✓validada

#### I - Pré-prova


##### I - Pré-prova


**I - Pré-prova** (1 aulas)

-   1. Semana e dia anterior à prova — `fo_60593c3fb6f18fcd`

#### I - Rotina


##### I - Rotina


**I - Rotina** (2 aulas)

-   1. Organização da rotina — `fo_0fdf7b7879b79c81` ✓validada
-   2. Organização das revisões — `fo_59c5834d2096ed37` ✓validada

#### II - Descanso e motivação


##### II - Descanso e motivação


**II - Descanso e motivação** (2 aulas)

-   1. Importância do descanso — `fo_0a0ef99c0d54f383` ✓validada
-   2. Como lidar com a falta de motivação — `fo_6130ff14e97ab95b`

#### II - Momento da prova


##### II - Momento da prova


**II - Momento da prova** (4 aulas)

-   1. Estratégias de resolução da prova — `fo_694f28d389a79e2b`
-   2. Estratégias para o vestibular UFPR 2026/2027 — `fo_cad66295d016fd02`
-   3. O emocional no momento da prova — `fo_0afb71d24e7026d2`
-   4. Sugestões de lanche para a prova — `fo_6ad13ea6ea2121b4`

#### II - Simulados e Redações


##### II - Simulados e Redações


**II - Simulados e Redações** (2 aulas)

-   1. Organização dos simulados — `fo_1ee25dcb93a0c1cb` ✓validada
-   2. Organização das redações — `fo_fc0469daf391d9a7` ✓validada

#### III - Foco


##### III - Foco


**III - Foco** (1 aulas)

-   1. Conciliando focos — `fo_35fb596691f150af` ✓validada

#### III - Frustração da reprovação


##### III - Frustração da reprovação


**III - Frustração da reprovação** (1 aulas)

-   1. Superando a reprovação — `fo_43d6a3e7e532dddb`

#### III - Pós-prova


##### III - Pós-prova


**III - Pós-prova** (2 aulas)

-   1. O momento pós-prova — `fo_67ea6dcbbd3a8ac6`
-   2. A aprovação!!! — `fo_b830391c55ed43fc`

#### Introdução ao material


##### Introdução ao material


**Introdução ao material** (1 aulas)

-   1. Bem-vindos, Medbulandos! — `fo_e4a65d18386b152a`

#### Simulado 10: 27 a 29 de ago


##### Simulado 10: 27 a 29 de ago


**Simulado 10: 27 a 29 de ago** (3 aulas)

-   1. Comentários sobre a redação 1 — `fo_02158540d18e6757` ✓validada
-   2. Comentários sobre a redação 2 — `fo_fecb822b7b8f93cc`
-   - Comentários sobre a redação 2 — `fo_1ef6fad5aea1078c` ✓validada

#### Simulado 11: 03 a 05 de set


##### Simulado 11: 03 a 05 de set


**Simulado 11: 03 a 05 de set** (3 aulas)

-   1. Redação 01 - Comentários — `fo_d20898f1e0040100` ✓validada
-   2. Redação 02 - Comentários — `fo_250074bc979134a1`
-   - Redação 02 - Comentários — `fo_40bb7566a32db23a` ✓validada

#### Simulado 12: 10 a 12 de set


##### Simulado 12: 10 a 12 de set


**Simulado 12: 10 a 12 de set** (3 aulas)

-   1. Comentários sobre a redação 01 — `fo_349df4e4f5027e2f` ✓validada
-   2. Comentários sobre a redação 02 — `fo_9f1a01dcaac2575e`
-   - Comentários sobre a redação 02 — `fo_f731f5eeb1d14ea8` ✓validada

#### Simulado 14: 24 a 26 de set


##### Simulado 14: 24 a 26 de set


**Simulado 14: 24 a 26 de set** (2 aulas)

-   1. Comentários sobre a redação 01 — `fo_3c25f79d87f68bd8` ✓validada
-   2. Comentários sobre a redação 01 — `fo_771544c16624f01f` ✓validada

#### Simulado 15: 01 a 03 de out


##### Simulado 15: 01 a 03 de out


**Simulado 15: 01 a 03 de out** (2 aulas)

-   1. Comentários sobre a redação 01 — `fo_1237714a067b1889`
-   2. Comentários sobre a redação 02 — `fo_9a00b2724eb75aa5`

#### Simulado 17: 15 a 17 de out


##### Simulado 17: 15 a 17 de out


**Simulado 17: 15 a 17 de out** (2 aulas)

-   1. Comentários sobre a redação 01 — `fo_40a0d1541829962e`
-   2. Comentários sobre a redação 02 — `fo_ee9ea086413576bf`

#### Simulado 18: 22 a 24 de out


##### Simulado 18: 22 a 24 de out


**Simulado 18: 22 a 24 de out** (2 aulas)

-   1. Comentários da redação 01 — `fo_1c19ab6722078e07`
-   2. Comentários da redação 02 — `fo_14888779dba6b334`

#### Simulado 1: 25 a 27 de jun


##### Simulado 1: 25 a 27 de jun


**Simulado 1: 25 a 27 de jun** (3 aulas)

-   1. Redação 01 - Comentários — `fo_2232d09b3e35e8be`
-   2. Redação 02 - Comentários — `fo_654e03e3f348a4d7`
-   - Redação 02 - Comentários — `fo_41b93763c969cc94` ✓validada

#### Simulado 2: 02 a 04 de jul


##### Simulado 2: 02 a 04 de jul


**Simulado 2: 02 a 04 de jul** (2 aulas)

-   1. Redação 01 - Comentários — `fo_125d53fe71d748f7`
-   2. Redação 02 - Comentários — `fo_d510ba7f7b769d99`

#### Simulado 3: 09 a 11 de jul


##### Simulado 3: 09 a 11 de jul


**Simulado 3: 09 a 11 de jul** (2 aulas)

-   1. Redação 01 - Comentários — `fo_6cd6872b8ef6536c`
-   2. Redação 02 - Comentários — `fo_1393f63cca231a83`

#### Simulado 4: 16 a 18 de jul


##### Simulado 4: 16 a 18 de jul


**Simulado 4: 16 a 18 de jul** (2 aulas)

-   1. Redação 01 - Comentários — `fo_77dfa9cd9c619b7d`
-   2. Redação 02 - Comentários — `fo_c68a9b6b78d584c7`

#### Simulado 5: 23 a 25 de jul


##### Simulado 5: 23 a 25 de jul


**Simulado 5: 23 a 25 de jul** (2 aulas)

-   1. Redação 01- Comentários — `fo_fb58f9c63e35efac`
-   2. Redação 02 - Comentários — `fo_d7c4ea7b6774483c`

#### Simulado 6: 30 de jul a 01 de ago


##### Simulado 6: 30 de jul a 01 de ago


**Simulado 6: 30 de jul a 01 de ago** (2 aulas)

-   1. Redação 01 - Comentários — `fo_3b110bda9276d82e`
-   2. Redação 02 - Comentários — `fo_d7d49c9fd5a57508`

#### Simulado 7: 06 a 08 de ago


##### Simulado 7: 06 a 08 de ago


**Simulado 7: 06 a 08 de ago** (2 aulas)

-   1. Redação 01 - Comentários — `fo_caa46fa3b95bffcf`
-   2. Redação 02 - Comentários — `fo_274ada7aa4660a7e`

#### Simulado 8: 13 a 15 de ago


##### Simulado 8: 13 a 15 de ago


**Simulado 8: 13 a 15 de ago** (2 aulas)

-   1. Redação 01 - Comentários — `fo_f30199e2d1108281`
-   2. Redação 02 - Comentários — `fo_3f65e7f2b4efcf91`

#### Simulado 9: 20 a 22 de ago


##### Simulado 9: 20 a 22 de ago


**Simulado 9: 20 a 22 de ago** (2 aulas)

-   1. Redação 01 - Comentários — `fo_dc2aaec7fe81c69c`
-   2. Redação 02 - Comentários — `fo_dcb7361d4b98e009`

### Redação UFPR 2026


#### Curso de Redação


##### Curso de Redação


**Aulas** (24 aulas)

-   1. Entendendo o edital — `fo_22139902ff87405a`
-   2. Ajeitando a estrutura — `fo_705dcb6d0c28d231` ✓validada
-   3. Dissertativo-argumentativo I — `fo_0dfc770d27fa9589` ✓validada
-   4. Dissertativo-argumentativo II — `fo_da94ae5cd73c4e2b`
-   5. Dissertativo-argumentativo III — `fo_ef1c0dd25cf3608c` ✓validada
-   6. Dissertativo-argumentativo IV — `fo_20872db7e5379e3a` ✓validada
-   7. Dissertativo-argumentativo V — `fo_4686db5408155a9f`
-   8. Transposição de Discurso — `fo_c7a1c01e6d46e934`
-   9. Continuação Textual I — `fo_53152502c8177484`
-  10. Continuação Textual II — `fo_ab7589742bc156fd`
-  11. Narrativa — `fo_ae1d25b5de786d0b`
-  12. Interpretação de Poemas — `fo_685daf95a1763ed1`
-  13. Interpretação de Tira — `fo_a512ecff4f7c9be4`
-  14. Interpretação de Charge I — `fo_40465da6d0e801e6`
-  15. Interpretação de Charge II — `fo_b726d76fdde0eac5`
-  16. Notícia de jornal — `fo_9a4d2f163ce58c6b`
-  17. Carta — `fo_88faec5fc907640d`
-  18. Gráficos, Infográficos e Mapas I — `fo_a6f8768b6e1d0c95`
-  19. Gráficos, Infográficos e Mapas II — `fo_5a4facaca203a491`
-  20. Gêneros diversos — `fo_6df46b7279a9a165`
-  21. Revisando a redação — `fo_0cc58888e9f53821`
-  22. Aula extra - Memorial — `fo_c4b79f9e44a732e4`
-  23. Aula extra - Estratégias na redação — `fo_8250097115dc23aa`
-  24. Aula extra - Estratégias na redação e gêneros diversos — `fo_87540217fb7229f5`

### Semiextensivo UFPR 2026


#### Anki - Flashcards


##### Anki - Flashcards


**Vídeos** (5 aulas)

-   1. Introdução ao Anki — `fo_57ce9c9c6a37a006`
-   2. Como baixar o Anki — `fo_c6a50e00826a6678`
-   3. Como funcionam os Flashcards? — `fo_7e1a4f2bd6e17bdf`
-   4. Como fazer os seus próprios Flashcards? — `fo_d11bcdaa9b41d101`
-   5. Como baixar os Cards do FO no Anki — `fo_dcfe067990a3ba41`

#### Biologia I


##### Biologia I


**Biologia I** (40 aulas)

-   1. Água e Sais minerais — `fo_cde037515ee11175`
-   2. Vitaminas e Doenças de carência — `fo_ccdacc057639171e`
-   3. Carboidratos e Lipídios — `fo_004ddd93c92571e1`
-   4. Proteínas e Enzimas — `fo_d27c3aef4d82cd23`
-   5. Membrana plasmática — `fo_5b9a9d11555084e4`
-   6. Transporte através da membrana — `fo_9e5ab312d146d192`
-   7. Citoplasma — `fo_fd28999d965f3917`
-   8. Respiração celular — `fo_a3d6dc0fd0b57acd`
-   9. Núcleo — `fo_a0d8a194456aa202`
-  10. Divisão celular — `fo_73f9ce0c94d02ee5`
-  11. Tecido epitelial — `fo_a7430ee87f0fc049`
-  12. Tecido conjuntivo I — `fo_1b70a3818e92ad7c`
-  13. Tecido conjuntivo II — `fo_2e0fee83a5f7570e`
-  14. Tecido muscular — `fo_28eb34a3bb9e9200`
-  15. Tecido nervoso — `fo_3c901ca44bea21c6`
-  16. Sistema nervoso — `fo_4ebf9f73a05f9edb`
-  17. Sistema digestório — `fo_e92c4645803a3e43`
-  18. Sistema respiratório — `fo_4ca31dd75271fdc0`
-  19. Sistema circulatório — `fo_a8699b47b1b25c98`
-  20. Sistema excretor — `fo_292d9718eaa65801`
-  21. Sistema endócrino — `fo_e2319d01666929d9`
-  22. Sistema reprodutor — `fo_f52a41e67fcb7e61`
-  23. Ciclo menstrual — `fo_e06f95331cc2e143`
-  24. Tipos de ovos e Clivagem — `fo_6bc23b287ad40fd2`
-  25. Desenvolvimento embrionário — `fo_759d7e3905a15378`
-  26. Anexos embrionários — `fo_7243c92225fe4e6f`
-  27. Reino Animal e Filo Porifera — `fo_b0625293b6bc6fb7`
-  28. Filo Cnidaria — `fo_020b8d43bdd676e3`
-  29. Filo Platyhelminthes e Filo Nematoda — `fo_e09e61fb10995b68`
-  30. Filo Mollusca — `fo_816da76605be7522`
-  31. Filo Annelida — `fo_4e86af3fe99bdb59`
-  32. Filo Arthropoda — `fo_4ddb096634ccc692`
-  33. Filo Echinodermata — `fo_7339cf8251d5a7e8`
-  34. Filo Chordata e Peixes — `fo_5dd1517e80a67dff`
-  35. Anfíbios — `fo_8c72c3c80687a4e0`
-  36. Répteis — `fo_b02d4c1d5e7b0b36`
-  37. Aves — `fo_0e4b17308d6d1298`
-  38. Mamíferos — `fo_103ade00ad7b8458`
-  39. Digestão e Excreção comparada — `fo_e251946442009c61`
-  40. Circulação e Respiração comparada — `fo_1423815ae5ef6195`

#### Biologia II


##### Biologia II


**Biologia II** (40 aulas)

-   1. Taxonomia — `fo_b602c0e202d47888`
-   2. Vírus — `fo_2b5a1cd1e2d5b8fc`
-   3. Reino Monera — `fo_c6f88145a35a21df`
-   4. Reino Protista — `fo_bff215062552c446`
-   5. Algas — `fo_9bac8cecf4fc9428`
-   6. Reino Fungi — `fo_da9cfaeb16ad9c20`
-   7. Reino Plantae — `fo_b0326949d1a16342`
-   8. Briófitas — `fo_625b4c9bfcbed73c`
-   9. Pteridófitas — `fo_01cd0904a1d5cc7a`
-  10. Gimnospermas — `fo_08169c9ef3ad6001`
-  11. Angiospermas — `fo_59d0467454aa612e`
-  12. Reprodução das Angiospermas — `fo_3553a88bec1a40fe`
-  13. Histologia vegetal — `fo_93c1f6c598f1f82a`
-  14. Tecidos de revestimento e Sustentação — `fo_317e7a830201dd0f`
-  15. Tecidos de armazenamento e Secreção — `fo_196c22cfd6c4bb0d`
-  16. Tecidos condutores de seiva — `fo_2bff1b39dd47597c`
-  17. Raiz — `fo_a641085d24b8a408`
-  18. Caule — `fo_0cfc051739734ca1`
-  19. Folha — `fo_fa230b42b95c7ae9`
-  20. Fruto — `fo_89af6df741be5001`
-  21. Nutrição e Absorção — `fo_5ea97057bb76dc9a`
-  22. Transporte de seiva — `fo_c073b144d1b3d4e4`
-  23. Fotossíntese I — `fo_2a6ed8b5fdcdb451`
-  24. Fotossíntese II — `fo_3607fe1a83dede32`
-  25. Ponto de compensação fótica — `fo_84457982cfeb9acb`
-  26. Hormônios vegetais I — `fo_4265f438ebcb9a19`
-  27. Hormônios vegetais II — `fo_87d414a0c6900315`
-  28. Fotoperiodismo e Movimentos vegetais — `fo_56d94a290406f412`
-  29. Cultivo de plantas — `fo_0bb608258241f823`
-  30. Parasitologia — `fo_0933ca8119e99b96`
-  31. Viroses — `fo_e03aa254c2b4b274`
-  32. Bacterioses — `fo_91dab793c4f591b7`
-  33. Protozooses I — `fo_adc67cf7fc8f271b`
-  34. Protozooses II — `fo_76a22c35c0a6bbdf`
-  35. Verminoses I — `fo_eaffa0b8561cb8de`
-  36. Verminoses II — `fo_f6840e211b447e6f`
-  37. Sistema imune — `fo_20c36edd6499ce4a`
-  38. Vacinas — `fo_5400966329c12d2b`
-  39. ISTs — `fo_332be54597c26c2e`
-  40. Métodos contraceptivos — `fo_ba99d1992bfaa4bf`

#### Biologia III


##### Biologia III


**Biologia III** (40 aulas)

-   1. Origem da vida — `fo_738429c673f3a8b5`
-   2. Teorias evolutivas — `fo_3660c04024443f5c`
-   3. Teoria sintética da evolução — `fo_af738b24b03dbccb`
-   4. Tipos de seleção natural — `fo_cb2ecb68dd15d905`
-   5. Evidências evolutivas e Especiação — `fo_240d4619893c01ca`
-   6. Introdução à ecologia — `fo_23870eecd42faee7`
-   7. Cadeia e Teia alimentar — `fo_0302887c5933994a`
-   8. Pirâmides ecológicas e Produtividade — `fo_73ea49b23728531c`
-   9. Ciclos biogeoquímicos — `fo_236a57d4dabb86da`
-  10. Relações ecológicas I — `fo_1178f8383c484f6b`
-  11. Relações ecológicas II — `fo_d9a7354de04e5a33`
-  12. Dinâmica de populações — `fo_4931946b1059527c`
-  13. Sucessão ecológica — `fo_025317fd7a566aca`
-  14. Biomas — `fo_4d2348e10c038219`
-  15. Biomas brasileiros — `fo_dfe7d7e667d5e702`
-  16. Ecossistemas aquáticos — `fo_51c9407f28b9b116`
-  17. Poluição atmosférica — `fo_3b0ca755df50d6fe`
-  18. Poluição da água — `fo_9eed11b61dc96992`
-  19. Espécies exóticas e Extinção de espécies — `fo_dfbff0444f7bbc68`
-  20. Introdução à genética — `fo_8ad28a28657f9e6d`
-  21. Primeira lei de Mendel — `fo_b30355878c37dd5e`
-  22. Extensões do Mendelismo I — `fo_aa1bb2567c66d639`
-  23. Extensões do Mendelismo II — `fo_d67d8787d18f2b1a`
-  24. Tipagem sanguínea — `fo_ae31e0f348eeb6d8`
-  25. Segunda lei de Mendel — `fo_6be3034d211ac6b4`
-  26. Interação gênica — `fo_c2e662fc09220582`
-  27. Herança quantitativa — `fo_77d4019841af7008`
-  28. Herança sexual — `fo_eed595687139e3d3`
-  29. Alterações cromossômicas — `fo_eda4ebcfde1a4187`
-  30. Ligação gênica — `fo_bd7c4032e9c3f1f2`
-  31. Genética de populações — `fo_e806f8c91304f383`
-  32. Ácidos nucleicos — `fo_1bc3678f483f6be7`
-  33. Biologia molecular I — `fo_98ab055d69d304a9`
-  34. Biologia molecular II — `fo_e3756826ee885011`
-  35. Expressão gênica — `fo_42681ea7f6af8e53`
-  36. Melhoramento genético — `fo_433d36c3a906932f`
-  37. Biotecnologia I — `fo_09be91f33d51b131`
-  38. Biotecnologia II — `fo_059275a5f4900a54`
-  39. Biotecnologia III — `fo_0ecdda3dd440a336`
-  40. Câncer — `fo_941833d126bbdd61`

#### Caderno de erros


##### Caderno de erros


**Caderno de erros** (1 aulas)

-   1. Caderno de erros — `fo_6cd6cae4406cda25`

#### Espanhol


##### Espanhol


**Aulas** (20 aulas)

-   1. Sinónimos e Técnicas de leitura — `fo_bc7ed4ad52e38ea3`
-   2. Heterosemánticos - Falsos cognatos — `fo_90eee7c96a9f3e3c`
-   3. Acentuación e Heterotónicos — `fo_7d0058a93006c98d`
-   4. Artículos e Heterogenéricos — `fo_6e6826b3ea9213b7`
-   5. Adverbios e Usos de muy y mucho — `fo_bae9c7405ac1b71d`
-   6. Preposiciones — `fo_ff4436879a04c0d3`
-   7. Verbo gustar — `fo_1f01ef4c4a7286f0`
-   8. Pronombre complemento — `fo_c5113b3c6493e5bb`
-   9. Conjunciones — `fo_0d02aa5e2dbe57f3`
-  10. Posesivos e Demostrativos — `fo_86ceb4c4e6ccda96`
-  11. Verbos de cambio — `fo_4038cbf0cda33c13`
-  12. Apócope — `fo_f469b475e5370dbb`
-  13. Numerales e Signos de puntuación — `fo_e5f1442030c67206`
-  14. Modo indicativo (presente) — `fo_7829036751040e9e`
-  15. Pretérito indefinido e Imperfecto — `fo_b03ec8a79017e172`
-  16. Pretérito perfecto compuesto — `fo_50eb0dc215d6f48f`
-  17. Pretérito pluscuamperfecto — `fo_3af99c079a648059`
-  18. Subjuntivo — `fo_1427b4bb6050611f`
-  19. Modo imperativo — `fo_319f792313d2aca3`
-  20. Condicional e Expresiones — `fo_a47a70181750d627`

#### Filosofia UFPR


##### Filosofia UFPR


**Filosofia UFPR** (35 aulas)

-   1. Filosofia clássica — `fo_0d14842fdd815c75`
-   2. Platão: Introdução — `fo_1d3cbdf905d6c3f9`
-   3. Mito de Er I — `fo_b46df8f1e802c0cb`
-   4. Mito de Er II — `fo_74d0794577c8486b`
-   5. Mito de Er III — `fo_bdd4b036835cc6ed`
-   6. Justiça e injustiça — `fo_3eed5e7b1f4ebf57`
-   7. Conclusão do mito — `fo_b585003b5e149369`
-   8. Filosofia moderna — `fo_53371b6a70557f3e`
-   9. Jean Jacques Rousseau: Introdução — `fo_598cd7b5bf0479fd`
-  10. Estado de natureza — `fo_5ec06320217d9dc7`
-  11. Surgimento da propriedade privada — `fo_bdd571ce69cec8c8`
-  12. Instituição das leis — `fo_c8ff2999bf3969d1`
-  13. Relações de poder — `fo_547f60eb7df6044d`
-  14. Conclusão do discurso — `fo_8c7b6499055af6fc`
-  15. Filosofia contemporânea — `fo_9878bab05dc00ace`
-  16. Karl Popper: Introdução — `fo_73b3b2ffdbf790c6`
-  17. O problema da demarcação — `fo_fbf8474897c059b0`
-  18. O problema da indução — `fo_c51d36e6eb31720f`
-  19. O critério da falseabilidade — `fo_026b0b3950c812a8`
-  20. Objetividade científica — `fo_df22e7ddb15601e4`
-  21. Conclusão da lógica — `fo_611bb9cd20d66aae`
-  22. Carole Pateman: Introdução — `fo_a8a07c8ab8a544cb`
-  23. Teoria crítica — `fo_947dd389b99785eb`
-  24. Sistema democrático — `fo_cb90d88b2087f20b`
-  25. Apatia política — `fo_fcedf070d5afa861`
-  26. Participação política — `fo_445c61cc7599d292`
-  27. Democracia participativa — `fo_c132f8b2e04a0307`
-  28. Conclusão da teoria — `fo_91b3e6449c9543e5`
-  29. Filosofia contemporânea brasileira — `fo_b5c2749b81adad0b`
-  30. Sueli Carneiro: introdução — `fo_2b7bee99c2453701`
-  31. Dispositivo de poder — `fo_0cb41e4e4b8a39e0`
-  32. Construção do outro — `fo_059f5565408f80ea`
-  33. Crítica a filosofia ocidental — `fo_ba860ee951c5ca75`
-  34. Epistemicídio no Brasil — `fo_adb2cca53ce84675`
-  35. Conclusão da racialidade — `fo_6676742d565aa9bb`

#### Física I


##### Física I


**Física I** (40 aulas)

-   1. Introdução à física — `fo_f41c13d47d37714c`
-   2. Análise dimensional e Conversão de unidades — `fo_875fc3592fc97c83`
-   3. Vetores I — `fo_90f015b580c72ce0`
-   4. Vetores II — `fo_0695206c36d31ca4`
-   5. Grandezas da cinemática — `fo_0c99d6d8761c4135`
-   6. Velocidade relativa e MRU — `fo_5616ffd80b2ac216`
-   7. MRUV — `fo_5aeb6a0bdd468abc`
-   8. Gráficos da cinemática — `fo_44395d275368e3fc`
-   9. Exercícios introdutórios — `fo_6a1a9fe29e4f2a29`
-  10. Movimentos na vertical — `fo_13bbc6dfc924aaca`
-  11. Lançamento oblíquo — `fo_7fd099c7f62b0372`
-  12. Exercícios sobre lançamentos — `fo_0fea136ebb3b0783`
-  13. Aceleração centrípeta — `fo_a5f6b27f8692470f`
-  14. Movimento circular — `fo_349cfb04e8d9b29c`
-  15. Transmissão do Movimento circular — `fo_6bd4821ff4461643`
-  16. Velocidade e Aceleração vetorial — `fo_2a80d73b2fc7191c`
-  17. Exercícios sobre MCU — `fo_77a5f3332e3acc5b`
-  18. Força peso, normal e atrito — `fo_403933009beeb010`
-  19. Força elástica e tração — `fo_41df2c7ebeb1aed2`
-  20. Diagrama de forças — `fo_9315122a5a2f294a`
-  21. Leis de Newton — `fo_ea753b61dfca57d6`
-  22. Plano inclinado — `fo_8f2f76220ac67e76`
-  23. Força Resultante centrípeta — `fo_efa741f238b8c465`
-  24. Exercícios sobre Leis de Newton — `fo_96b34dec1cb7d2f6`
-  25. Equilíbrio de um ponto material — `fo_9dbc7f17cc54da0a`
-  26. Equilíbrio de um corpo extenso — `fo_3f96b0dc7a88969f`
-  27. Gravitação universal — `fo_9a0ea48656db2dfc`
-  28. Exercícios sobre estatística e gravitação — `fo_0aa442746417e514`
-  29. Trabalho mecânico — `fo_2d3fb5791f4a014c`
-  30. Energia mecânica — `fo_82da185c6df4cf00`
-  31. Relação trabalho-energia — `fo_a5b937d339fa6a03`
-  32. Quantidade de movimento — `fo_121bcec8406b4719`
-  33. Impulso — `fo_790c22d62f40d69a`
-  34. Colisões — `fo_eebc8b5c6dc9c711`
-  35. Exercícios sobre trabalho e energia — `fo_d8eece50e67c4aac`
-  36. Densidade, massa específica e pressão — `fo_0de733bb830094ce`
-  37. Princípios da hidrostática I — `fo_ae3c3e0e581189ee`
-  38. Princípios da hidrostática II — `fo_27d1f67246c0aeb2`
-  39. Exercícios sobre hidrostática — `fo_fafdc444d9e264c0`
-  40. Revisão geral — `fo_fa5bc36fadaca90e`

#### Física II


##### Física II


**Física II** (40 aulas)

-   1. Termometria — `fo_d4771759cabd57b1`
-   2. Dilatometria — `fo_c00958326996322e`
-   3. Exercícios sobre termometria e dilatometria — `fo_f98d2805dd79a574`
-   4. Propagação de calor — `fo_e968b24ac0c22064`
-   5. Lei de Fourier — `fo_8342d82b0c4e446e`
-   6. Calor sensível e Calor latente — `fo_d38994da29271f1b`
-   7. Diagrama de fases e Equilíbrio térmico — `fo_e130c1639b693bec`
-   8. Exercícios sobre calorimetria — `fo_8b2864e3a9c64553`
-   9. Gás ideal — `fo_a316dc4a0d739a61`
-  10. Trabalho e Energia interna — `fo_bed08d695aa5c32c`
-  11. Lei 0 e Primeira lei da termodinâmica — `fo_3b4f6c385df23b2c`
-  12. Segunda lei da termodinâmica — `fo_b43715c26f80569a`
-  13. Ciclo de Carnot e Entropia — `fo_d44c722653eac443`
-  14. Exercícios sobre termodinâmica — `fo_e6feab60e9f0f642`
-  15. Conceitos iniciais de óptica — `fo_1857f5e6637f74da`
-  16. Princípios de propagação da luz — `fo_ce567e224c5886b8`
-  17. Reflexão da luz e Espelhos planos — `fo_17c1ed67fff9d9f9`
-  18. Espelhos esféricos I — `fo_2754ea6cdc8fcaaa`
-  19. Espelhos esféricos II — `fo_67e3eeef5721fa63`
-  20. Exercícios sobre óptica I — `fo_613a4e2df9c42afc`
-  21. Refração da luz — `fo_c5031cdb8ac6162d`
-  22. Reflexão interna total — `fo_6bb0810acea057be`
-  23. Prismas e Dispersão da luz — `fo_8f3607eaab953e27`
-  24. Lentes esféricas I — `fo_0b026a2fa808b28e`
-  25. Lentes esféricas II — `fo_6e9a010de762c285`
-  26. Instrumentos ópticos — `fo_022974b503b4e13d`
-  27. Óptica da visão — `fo_906c3a34ede8768d`
-  28. Exercícios sobre óptica II — `fo_2efcf8b98d0cb312`
-  29. Introdução à ondulatória — `fo_8584806688b01108`
-  30. Refração e Reflexão de ondas — `fo_f6917e5ed8355de3`
-  31. Interferência, difração e polarização — `fo_0b801f89ee922871`
-  32. Ondas eletromagnéticas — `fo_9127fcb2b8256f26`
-  33. Acústica I — `fo_72416db3c12add6e`
-  34. Acústica II — `fo_518e6a283f1a9d47`
-  35. Instrumentos musicais — `fo_464053a3a110fe42`
-  36. Efeito Doppler do som — `fo_4929ec0b2373b084`
-  37. Efeito Doppler da luz — `fo_aa728f71feee96c0`
-  38. Movimento harmônico simples — `fo_21a2bb1ce5bf9a0f`
-  39. Exercícios sobre ondulatória — `fo_0ca7432fc4fde056`
-  40. Revisão geral — `fo_52cbef30636b5838`

#### Física III


##### Física III


**Física III** (42 aulas)

-   1. Carga elétrica e Processos de eletrização — `fo_949c11c546993379`
-   2. Força elétrica — `fo_e748445706f3779a`
-   3. Campo elétrico — `fo_b411e47a5baa8026`
-   4. Relação entre Força elétrica e Campo elétrico — `fo_91428d7126af63db`
-   5. Energia potencial elétrica — `fo_36ed70bc865c175e`
-   6. Potencial elétrico — `fo_7db4af1dfde438c8`
-   7. Trabalho de uma força elétrica — `fo_c6c1eda232ca70ad`
-   8. Campo elétrico uniforme — `fo_30dafe5fb7ef3ef5`
-   9. Condutores em equilíbrio — `fo_8ecb4056b40d9aeb`
-  10. Exercícios sobre eletrostática — `fo_1334d77208d9603e`
-  11. Corrente elétrica — `fo_efa3aef43c7a692b`
-  12. Potência elétrica — `fo_0f8b98985810df9b`
-  13. Primeira lei de Ohm — `fo_e2f31448e12b6175`
-  14. Segunda lei de Ohm — `fo_3f7e48935e5c6797`
-  15. Exercícios sobre corrente elétrica e leis de Ohm — `fo_f2ae9da12a50e148`
-  16. Associação de resistores — `fo_8b7c252780f51c48`
-  17. Associação mista de resistores — `fo_c502e7746cf9cf37`
-  18. Medidores elétricos — `fo_c8c587d75937fff8`
-  19. Ponte de Wheatstone e Brilho — `fo_db5873e22dea8377`
-  20. Geradores e Receptores — `fo_de1ab826514c9450`
-  21. Aplicações em circuitos elétricos — `fo_11d042d4ac3c0be9`
-  22. Exercícios sobre circuitos elétricos — `fo_964fdd79353aecb0`
-  23. Capacitores — `fo_f4e98b3fb31980da`
-  24. Associação de capacitores — `fo_c59b03e6c6ead404`
-  25. Exercícios sobre capacitores — `fo_2b3a9b9aefa02389`
-  26. Magnetismo — `fo_9345b0ab2826af1c`
-  27. Campo magnético e Corrente elétrica — `fo_a6ef4cbe2a6a9110`
-  28. Lei de Ampère I — `fo_9136f8c17aed33bb`
-  29. Lei de Ampère II — `fo_6864e17ba9141b25`
-  30. Força magnética I — `fo_6bedac40367de6d3`
-  31. Força magnética II — `fo_18d557b6dd3eef96`
-  32. Lei de Faraday — `fo_d8bcb9eac540de68`
-  33. Lei de Lenz — `fo_6332458e0d6340f0`
-  34. Exercícios sobre eletromagnetismo — `fo_3ef2fc941c44a0d5`
-  35. Radiação do corpo negro — `fo_659204d740e163b8`
-  36. Raios X e Dualidade onda partícula — `fo_5427778644d81b80`
-  37. Efeito fotoelétrico — `fo_78118dcb4ec9c448`
-  38. Relatividade — `fo_fdb95c81c57ceea1`
-  39. Exercícios sobre física moderna — `fo_e47bad6e43cb7a69`
-  40. Revisão geral — `fo_d582bcb30f092fd6`
-  41. Física III - UFPR Extensivo - Aula 21 - REEDITADA — `fo_626434837c181089`
-   - Física III - UFPR Extensivo - Aula 21 - REEDITADA — `fo_630e1b4d2a0089f5`

#### Geografia I


##### Geografia I


**Geografia I** (27 aulas)

-   1. Movimentos da Terra — `fo_63c27e4200c5bc1e`
-   2. Cartografia I — `fo_35e581cccd47e1ae`
-   3. Cartografia II — `fo_a0ecda60a1e95721`
-   4. Cartografia III — `fo_0501a2a7d94e73f1`
-   5. Cartografia IV — `fo_dae093deb3fd4024`
-   6. Geologia I — `fo_9c1d2d8378eae12a`
-   7. Geologia II — `fo_864aceec30d224d0`
-   8. Geomorfologia — `fo_4fca816c06d69288`
-   9. Geologia brasileira — `fo_3a50062c4704d906`
-  10. Geomorfologia brasileira — `fo_271b0740d4b1f19f`
-  11. Solos — `fo_70340d2c976bf099`
-  12. Climatologia I — `fo_885fcce445923b60`
-  13. Climatologia II — `fo_f6bf376412897b5c`
-  14. Climas do Brasil — `fo_18c7481220115240`
-  15. Hidrologia — `fo_0c927c1f1d9a04e8`
-  16. Biomas mundiais — `fo_4e17fbcafeedea44`
-  17. Biomas brasileiros — `fo_59efa42f03f3022b`
-  18. Recursos naturais e legislação ambiental brasileira — `fo_89b2a328ab617b24`
-  19. Problemas ambientais I — `fo_5dc3f339de7d521c`
-  20. Problemas ambientais II — `fo_f794f0ab8c9fcbae`
-  21. Convenções ambientais I — `fo_f4737e983d7954da`
-  22. Convenções ambientais II — `fo_d3ef5ecabee10994`
-  23. Principais aspectos físicos da Ásia — `fo_0bcbb89826fc3fef`
-  24. Principais aspectos físicos da Europa — `fo_464b897ad79512b4`
-  25. Principais aspectos físicos da América — `fo_62a70f54aef8135a`
-  26. Principais aspectos físicos da África — `fo_b1742d0ab1617b59`
-  27. Principais aspectos físicos da Oceania — `fo_61bf2ad8e0c17164`

#### Geografia II


##### Geografia II


**Geografia II** (27 aulas)

-   1. Conceitos básicos — `fo_4023153e2631494f`
-   2. Território brasileiro — `fo_2adc4ff701503652`
-   3. Regionalização do Brasil — `fo_62c75b35b27fdbae`
-   4. Demografia — `fo_9551d7547f66b97b`
-   5. Demografia brasileira I — `fo_ac83cbfc3395fa14`
-   6. Demografia brasileira II — `fo_2d65bf88155ed679`
-   7. Processo de industrialização I — `fo_b7fd2f77f96aa849`
-   8. Processo de industrialização II — `fo_1919d5411e58ba40`
-   9. Urbanização I — `fo_7ce50683c0255cd7`
-  10. Urbanização II — `fo_d8b9e48f507e36f9`
-  11. Setor primário I — `fo_4cdfa4fdaa4b71ce`
-  12. Setor primário II — `fo_8376899d9994a9c1`
-  13. Urbano-rural — `fo_f39298e8f078a5bd`
-  14. Conflitos por terra no Brasil — `fo_1ef6eee5687bfdf4`
-  15. Produção e infraestrutura — `fo_97e73a3b394fd7cc`
-  16. Disparidades regionais — `fo_3c617a57ce207c76`
-  17. Globalização — `fo_088f8826a8abcf30`
-  18. Geopolítica I — `fo_6709eabf3252ae59`
-  19. Geopolítica II — `fo_cc278476aea30529`
-  20. Geopolítica III — `fo_4e84bdfbbb67df77`
-  21. Geopolítica IV — `fo_a9fcec54444d4565`
-  22. Organização do espaço mundial — `fo_79f16de3654809c4`
-  23. Principais aspectos humanos da Ásia — `fo_2a48286ddcb5c2ed`
-  24. Principais aspectos humanos da Europa — `fo_90ac6a4e7afe733b`
-  25. Principais aspectos humanos América — `fo_04ea5b1986a391ae`
-  26. Principais aspectos humanos da África — `fo_72b0a9cbb970f95c`
-  27. Principais aspectos humanos da Oceania — `fo_9b5fe79cc9e7fe6d`

#### Geografia III


##### Geografia III


**Geografia III** (20 aulas)

-   1. Economia geral — `fo_a188d67351effe75`
-   2. Cenário político-econômico I — `fo_1369ed58b80c7077`
-   3. Cenário político-econômico II — `fo_319e246f061ef3da`
-   4. Fronteiras problemáticas contemporâneas — `fo_d5f71f74b4a55e64`
-   5. Blocos econômicos — `fo_9c080b337209db9b`
-   6. Disputas no Mar da China — `fo_f1a48bfb4d7b4767`
-   7. Ditadura em Myanmar e Nicarágua — `fo_0b6d90c5192a42cd`
-   8. Guerra civil Sudão e Iêmen — `fo_598f5bcae0a0737f`
-   9. Revolução iraniana e os grupos terroristas — `fo_d211fd8bf5a3cbde`
-  10. Reformas em Israel — `fo_7294aad8f14d6dc7`
-  11. Terrorismo e os principais grupos — `fo_cb74fb3a37b21c1a`
-  12. Conflitos — `fo_0877d5c4c0cd2ccb`
-  13. Eventos climáticos extremos — `fo_e69a3e7a3a176b31`
-  14. Mudanças climáticas e saúde — `fo_6974fe0bf1f94166`
-  15. Energia limpa e a transição energética — `fo_4e30577381e7640d`
-  16. Desafios econômicos do estado brasileiro — `fo_6b685e66963b78cd`
-  17. Amazônia e a política externa brasileira — `fo_636e1eb6800db889`
-  18. Agronegócio, produção política e cultura — `fo_2fed235e04fa1e50`
-  19. Atualidades 2026 I — `fo_bd1125afc77cf173`
-  20. Atualidades 2026 II — `fo_7006bf944aec3b0e`

#### História I


##### História I


**História I** (59 aulas)

-   1. Período pré-colonial — `fo_e8b0489edd7901a8`
-   2. Ciclo da cana-de-açúcar — `fo_8208fd1de90d05c9`
-   3. Invasões e conflitos — `fo_576390e42313899a`
-   4. Ciclo da mineração — `fo_371f161048ee3d47`
-   5. Movimentos de resistência — `fo_94e1815e494e83f5`
-   6. Revoltas coloniais I — `fo_51a962cd3dd13a04`
-   7. Revoltas coloniais II — `fo_6b74273736216a47`
-   8. Período joanino e independência — `fo_dedbd3e0e749bf73`
-   9. Primeiro reinado — `fo_d5321847f37f41a0`
-  10. Período regencial — `fo_09be41eb00a3484f`
-  11. Segundo reinado I — `fo_e7180d52c506ffc2`
-  12. Segundo reinado II — `fo_1a5d72fe8805e7ca`
-  13. República velha — `fo_8c02e28d4f8f9303`
-  14. República oligárquica I — `fo_043ed58e95c0b864`
-  15. República oligárquica II — `fo_5e545843b6a2d5d9`
-  16. Revolução de 1930 — `fo_2c57eb8250bb0bf0`
-  17. Era Vargas - Constitucional — `fo_0191fea2f16112ef`
-  18. Estado Novo — `fo_b87742e675486b47`
-  19. República populista I — `fo_3d70d51bcf067d31`
-  20. República populista II — `fo_3c55e9dfd1cf906d`
-  21. Ditadura militar I — `fo_bfda130ff1888690`
-  22. Ditadura militar II — `fo_a33ecd7a715fdcea`
-  23. Redemocratização — `fo_1cef9ff0b34485b8`
-  24. Movimentos sociais — `fo_799f5de5e801c59a`
-  25. Patrimônio histórico-cultural brasileiro — `fo_f669ba98a315434e`
-  26. Períodos da História do Brasil (aula do curso 2025) — `fo_60cb61120e1569f6`
-  27. Baixa Idade média e Grandes Navegações (aula do curso 2025) — `fo_08a84fcb9c5a53ba`
-  28. Conquista e Formação Cultural do Brasil (aula do curso 2025) — `fo_de39ee3c36c592f5`
-  29. Período Pré-Colonial (aula do curso 2025) — `fo_efc6182a369d5749`
-  30. Capitanias Hereditárias e Governos Gerais (aula do curso 2025) — `fo_7cfe5d671a1f13c8`
-  31. Ciclo da Cana de Açúcar (aula do curso 2025) — `fo_1c831c445c8fa8d1`
-  32. O Tráfico Negreiro (aula do curso 2025) — `fo_4c830f35a5bc5192`
-  33. Os Índigenas e a Cataquese (aula do curso 2025) — `fo_6577f2fce0093469`
-  34. União Ibérica e Holandeses no Brasil (aula do curso 2025) — `fo_b001600ee4300976`
-  35. Entradas e Bandeiras (aula do curso 2025) — `fo_e37f30f512a995e1`
-  36. A Economia da Mineração (aula do curso 2025) — `fo_afc927663f7155a1`
-  37. Crise do Sistema Colonial (1750 - 1808) (aula do curso 2025) — `fo_730cd01cde5bf17e`
-  38. Revoltas Separatistas Coloniais (aula do curso 2025) — `fo_63bf92940db776ed`
-  39. A Família Real no Brasil (aula do curso 2025) — `fo_2cc4719c799a7d8e`
-  40. Primeiro Reinado (aula do curso 2025) — `fo_b0159137587fef4c`
-  41. Período Regencial (aula do curso 2025) — `fo_66b78ea9e5dc62e3`
-  42. Segundo Reinado - Política Interna (aula do curso 2025) — `fo_0f67bcb2e60fd7c3`
-  43. Proclamação da República 1889 (aula do curso 2025) — `fo_9687fa899e3455ea`
-  44. República da Espada (aula do curso 2025) — `fo_e39f92bf1574ea3e`
-  45. Crise da República Velha (aula do curso 2025) — `fo_e3d51e873da6c312`
-  46. República Oligárquica (aula do curso 2025) — `fo_b37c5b736237e37d`
-  47. Crise da República Velha (aula do curso 2025) — `fo_cfe7e88a1ad441af`
-  48. Crise da República Velha e Revolução de 1930 (aula do curso 2025) — `fo_dc2ca8951f47acbf`
-  49. A Era Vargas (1930 - 1934) - Governo Provisório (aula do curso 2025) — `fo_5757d4be27a64e2e`
-  50. A Era Vargas (1934 - 1937) - Governo Constitucional (aula do curso 2025) — `fo_3c2b2507663a777c`
-  51. A Era Vargas (1937 - 1945) - Estado Novo (aula do curso 2025) — `fo_4246bc7d6f8b0e33`
-  52. Fim do Estado Novo (aula do curso 2025) — `fo_3c4c69e58e4beedb`
-  53. Getúlio Vargas (1951 - 1954) (aula do curso 2025) — `fo_f413f6cf8ff4e5d6`
-  54. Getúlio Vargas (1954 - 1956) (aula do curso 2025) — `fo_9ebf7007d5d64b5a`
-  55. Governo JK (1956 - 1961) (aula do curso 2025) — `fo_00f1d411c04e2225`
-  56. Governos de: Jânio Quadros (1961) e João Goulart (1961 - 1964) (aula do curso 2025) — `fo_ac9548e8a0ff4bb8`
-  57. Ditadura Militar (aula do curso 2025) — `fo_1dfa89374f1c1469`
-  58. Nova República - Sarney a FHC (aula do curso 2025) — `fo_d9654545ade1b68a`
-  59. Nova República - Lula a Bolsonaro (aula do curso 2025) — `fo_20820f4a1e8816a9`

#### História II


##### História II


**História II** (44 aulas)

-   1. Patrimônio histórico — `fo_ce4b9be2a9589190`
-   2. Egito antigo — `fo_b90ef2ee4c44cf2d`
-   3. Grécia antiga I — `fo_dd9609afe2963523`
-   4. Grécia antiga II — `fo_1043d7b9c8a95fa0`
-   5. Grécia antiga III — `fo_91f25dcc6721ae8f`
-   6. Roma antiga I — `fo_5bd60a94f4c803b0`
-   7. Roma antiga II — `fo_337fa3765af65a9e`
-   8. Roma antiga III — `fo_ed7ac9292bd72594`
-   9. Império Bizantino — `fo_c85453840fd5fa20`
-  10. Civilização Árabe — `fo_b6d7943f18d3b8cc`
-  11. Igreja e Feudalismo — `fo_5d06f58164efad5e`
-  12. Alta Idade Média — `fo_04ad95f0dc65118c`
-  13. Baixa Idade Média — `fo_84408678158f7502`
-  14. Renascimento — `fo_194719fb080bc810`
-  15. Expansão marítima — `fo_5d199dfcccf70847`
-  16. Reforma protestante — `fo_98fa70232e5c4465`
-  17. Povos africanos — `fo_484e48a1b455aea5`
-  18. Colonização das Américas — `fo_196b11819945bd91`
-  19. Absolutismo I — `fo_b70335ab72c35658`
-  20. Absolutismo II — `fo_8072ef13e8cf0702`
-  21. Iluminismo — `fo_071676e1634b94d0`
-  22. Revolução industrial — `fo_98958b94e85087da`
-  23. Independência dos EUA — `fo_5639af9e0ae6b7fc`
-  24. Revolução francesa — `fo_31c353b40111f83c`
-  25. Era Napoleônica — `fo_f75e910dd83fc989`
-  26. Independência do Haiti — `fo_f9eaf23e2183d45b`
-  27. Independência da América Espanhola — `fo_ba7c80fd7215fb15`
-  28. Revoluções liberais — `fo_d8a9b10a577f0b2c`
-  29. Século XIX — `fo_de33e5634974c3c3`
-  30. Imperialismo — `fo_daf15e12e4967bfc`
-  31. Primeira guerra mundial — `fo_d077ffb970769ac7`
-  32. Rússia no século XX — `fo_42b081c502698f96`
-  33. Ascensão do Nazifascismo — `fo_05ea1ded84ca8608`
-  34. Segunda guerra mundial I — `fo_bda9f2b9d3a2bf08`
-  35. Segunda guerra mundial II — `fo_10c6aeadbff74d58`
-  36. Guerra fria I — `fo_16dbf1c14b20b3e6`
-  37. Guerra fria II — `fo_c9a50ed7f00d170c`
-  38. Supremacia americana — `fo_f70020f547a7ff7f`
-  39. Conflitos asiáticos — `fo_852c228f0648c77d`
-  40. Descolonização afro-asiática — `fo_ca7427b50e17afa7`
-  41. Movimentos sociais do século XX — `fo_497aeef4021f6eea`
-  42. Ditaduras na América Latina — `fo_bd015316067905a8`
-  43. Século XXI — `fo_f8311b2e3bae0141`
-  44. Efemérides — `fo_91037e2fa38f8e28`

#### Inglês


##### Inglês


**Aulas** (20 aulas)

-   1. Introdução — `fo_7573241a86540b52`
-   2. Purpose of the text — `fo_dbd3b4fa3aa5bb89`
-   3. Exercícios sobre purpose of the text — `fo_db9aa233398d9a92`
-   4. Reading techniques I — `fo_7ed7e6f9520bd7af`
-   5. Reading techniques II — `fo_8fc82948f32a2286`
-   6. Termos importantes e vocabulário — `fo_e838f19410b5e722`
-   7. Reading techniques - skimming — `fo_92345983a5b6e871`
-   8. Reading techniques - scanning — `fo_294b8bd191e3c5a5`
-   9. Pronouns — `fo_6143a87dc0af4b0b`
-  10. Exercícios sobre pronouns — `fo_d88be0f5b4630a71`
-  11. Cognatos — `fo_2a0f7e5ae8ca7af7`
-  12. Falsos cognatos — `fo_c670fd3942079862`
-  13. Conjunções e conectivos — `fo_ab1dee277a655953`
-  14. Exercícios sobre conjunções e conectivos — `fo_1d2e091fe1896aa1`
-  15. Adverbs — `fo_ada999c5c625f139`
-  16. Adverbs and vocabulary — `fo_958ca7ff14d235d2`
-  17. Modal verbs — `fo_d462635d2d85e66a`
-  18. Prepositions — `fo_c8a8d042ba283043`
-  19. Exercícios gerais — `fo_585efb016a6e6b93`
-  20. Revisão — `fo_a536540d7d9f0af6`

#### Introdução


##### Introdução


**Introdução** (1 aulas)

-   1. Introdução aos métodos de estudo — `fo_ee1e45bf6bf1fa36`

#### Literatura UFPR


##### Literatura UFPR


**Literatura UFPR** (18 aulas)

-   1. A falência — `fo_6025ed51c164b1e9`
-   2. A falência - Exercícios — `fo_06933bf27ba0d869`
-   3. Noite na taverna — `fo_d35743dfcf2a72ef`
-   4. Noite na taverna - Exercícios — `fo_c5f90691fb9a4a4f`
-   5. O Drible - Parte I — `fo_4d61ca66f2ccdb1a`
-   6. O Drible - Parte II — `fo_bc9c34d21018ec6d`
-   7. O sol na cabeça - Parte I — `fo_1f26cc23da9d8401`
-   8. O sol na cabeça - Parte II — `fo_2b6d3b90f1c2749c`
-   9. O sol na cabeça - Parte III — `fo_d8008397ff7e05ec`
-  10. Poema Sujo - Parte I — `fo_a1ebaa88580984c5`
-  11. Poema Sujo - Parte II — `fo_93ed46e48b2a0df1`
-  12. Poema Sujo - Parte III — `fo_dc1d2939009ae5c1`
-  13. Eu - Parte I — `fo_f885b5b8bf21b1d1`
-  14. Eu - Parte II — `fo_7159c2f70f79d494`
-  15. O Demônio Familiar - Parte I — `fo_6269cc582acaf4d1`
-  16. O Demônio Familiar - Parte II — `fo_c3dc169f3e222c83`
-  17. O Quinze - Parte I — `fo_0f55cae341561722`
-  18. O Quinze - Parte II — `fo_45e895764d935580`

#### Matemática I


##### Matemática I


**Matemática I** (40 aulas)

-   1. Teoria dos conjuntos — `fo_50c7081442ea1f10`
-   2. Conjuntos numéricos — `fo_aad954027cc877d1`
-   3. Múltiplos e Divisores — `fo_54b4496c9ce8b6e0`
-   4. Potenciação — `fo_4309c4087e914880`
-   5. Radiciação — `fo_459fa091e43b50a7`
-   6. Radiciação e Racionalização — `fo_564963e1e9fa17f8`
-   7. Definição de função — `fo_3fef32ceb18471fb`
-   8. Tipologia de função — `fo_405882b86be1627a`
-   9. Função inversa — `fo_39d6fe3632eabb29`
-  10. Função composta — `fo_60ce0a03356b59c9`
-  11. Exercícios sobre funções — `fo_aeab293912fb0e2b`
-  12. Função afim — `fo_6b8a7d55bbe7a7f3`
-  13. Exercícios sobre função afim — `fo_80834e8446da7bec`
-  14. Função quadrática I — `fo_5c7b283926f5fad1`
-  15. Função quadrática II — `fo_6170022dd55b23c0`
-  16. Exercícios sobre função quadrática — `fo_0850ee131026dae2`
-  17. Inequações — `fo_0ada38b2f7a8be76`
-  18. Exercícios sobre inequações — `fo_52e27401fa8e059d`
-  19. Função modular — `fo_ee4d57958ad0191d`
-  20. Equação e Inequação modular — `fo_f954059c86831093`
-  21. Exercícios sobre módulos — `fo_0b293653c00a9f48`
-  22. Equação exponencial — `fo_24d1d4569df50671`
-  23. Função exponencial — `fo_32fc0ff5da2ee4a1`
-  24. Inequação exponencial — `fo_9a76dcd9a76ddf8e`
-  25. Exercícios sobre exponenciais — `fo_c75b19daac24d161`
-  26. Logaritmos — `fo_7016879baa091bdc`
-  27. Equação logarítmica — `fo_b382f2870f6a6914`
-  28. Função logarítmica — `fo_c38aec9032d7d9de`
-  29. Inequação logarítmica — `fo_e6fe98ba61d71ffe`
-  30. Exercícios sobre logaritmos e exponenciais — `fo_033de71a87138732`
-  31. Identidades trigonométricas — `fo_d9157d781e585e8b`
-  32. Equações trigonométricas — `fo_d246fcdf8db2a8c3`
-  33. Inequações trigonométricas — `fo_09b595860f9381bd`
-  34. Função trigonométrica — `fo_8ab8f40dfd7c46b3`
-  35. Exercícios sobre função trigonométrica — `fo_4dbd9baeeda75b87`
-  36. Exercícios sobre inequações e equações trigonométricas — `fo_5fb628c617135948`
-  37. Progressão aritmética — `fo_c5cb250433083292`
-  38. Soma de PA — `fo_6c8541136442dac3`
-  39. Progressão geométrica — `fo_0ecb58fac8c4b489`
-  40. Soma de PG — `fo_be04a40a7621c29d`

#### Matemática II


##### Matemática II


**Matemática II** (36 aulas)

-   1. Ângulos — `fo_c01a828c17609d1e`
-   2. Triângulos — `fo_657eb17a2f5806ea`
-   3. Cevianas — `fo_147d35d161317278`
-   4. Quadriláteros — `fo_2154a107eba95fa4`
-   5. Polígonos — `fo_0ef94854790b51be`
-   6. Área de polígono — `fo_b2586af651898159`
-   7. Exercícios sobre polígonos — `fo_7812106846b2e01b`
-   8. Teorema de Tales — `fo_c151520a8039c239`
-   9. Semelhança de triângulos — `fo_0373779f4cea4597`
-  10. Exercícios sobre semelhança e Tales — `fo_fd739132af87d46c`
-  11. Relações métricas no triângulo retângulo — `fo_d03240fafdf3e4fe`
-  12. Teorema de Pitágoras — `fo_b329094351b8f420`
-  13. Razões trigonométricas — `fo_616dfa05864ba26e`
-  14. Círculo trigonométrico — `fo_79d0193b0b9e20bc`
-  15. Trigonometria em um triângulo qualquer — `fo_102a36de9b2f16d3`
-  16. Exercícios sobre trigonometria — `fo_632c4215c5650820`
-  17. Círculo — `fo_caa8d955b43a110c`
-  18. Círculo e retas — `fo_9f0a9d37261b7bd6`
-  19. Exercícios sobre círculos — `fo_a8b0776fb4023177`
-  20. Geometria espacial de posição — `fo_bf9127b44ad2583e`
-  21. Poliedros regulares — `fo_ad60ab9ed8e5487f`
-  22. Exercícios sobre poliedros — `fo_ee25dafb2048f0c4`
-  23. Prismas — `fo_d5a1b8da34c345c9`
-  24. Exercícios sobre prismas — `fo_b976b5e6b60c19a5`
-  25. Pirâmide — `fo_8d2ed34d4220cc55`
-  26. Tronco de pirâmide — `fo_796a378c9c5b3985`
-  27. Exercícios sobre pirâmides — `fo_581f151098380e61`
-  28. Cilindro — `fo_bcf5c210d3012661`
-  29. Cone — `fo_b75b3a8f952e4801`
-  30. Exercícios sobre cilindros e cones — `fo_1640e6c2957a8958`
-  31. Esfera — `fo_6f2d5c75bf3ea2a0`
-  32. Exercícios sobre esferas — `fo_9145ca2af7e03a4d`
-  33. Estudo do ponto — `fo_e41934b7cd0d4d51`
-  34. Estudo da reta — `fo_bf9ef4738a29d428`
-  35. Estudo da circunferência — `fo_d59c839c7288eb05`
-  36. Exercícios sobre geometria analítica — `fo_bce9e430ccb64544`

#### Matemática III


##### Matemática III


**Matemática III** (40 aulas)

-   1. Razão e Proporção — `fo_ec7c5d18576b21c9`
-   2. Porcentagem I — `fo_61bcaae187598572`
-   3. Porcentagem II — `fo_8bd63a6dc32837dc`
-   4. Juros simples — `fo_075a0ec762c4545d`
-   5. Juros compostos — `fo_7560d5860d593468`
-   6. Estatística I — `fo_7eeb4c6b62a5bb1c`
-   7. Estatística II — `fo_c6282b4aa1261666`
-   8. Exercícios sobre estatística — `fo_118cee4ae2c7f5b0`
-   9. Princípio fundamental da contagem — `fo_7b0440949a197734`
-  10. Combinação — `fo_f12b156cb2becd17`
-  11. Arranjo e permutação — `fo_5fe136dfeef1960f`
-  12. Exercícios sobre arranjo e combinação — `fo_0a8b87728b14091c`
-  13. Princípio da casa dos pombos — `fo_3d39b0602c079384`
-  14. Binômio de Newton — `fo_d8adee5a30a079a7`
-  15. Probabilidade I — `fo_1fe73c2ee8c8c4fb`
-  16. Probabilidade II — `fo_97dc1ad38c6f33a8`
-  17. Probabilidade III — `fo_fcda82568b47ffc6`
-  18. Exercícios sobre probabilidade I — `fo_4dab20297f71f15d`
-  19. Exercícios sobre probabilidade II — `fo_39a7792fa1dd4bb3`
-  20. Matrizes I — `fo_4d0f07f463319fa0`
-  21. Matrizes II — `fo_f6c085d392a0309a`
-  22. Determinantes — `fo_9c9502c86e385ba9`
-  23. Propriedade de determinantes — `fo_8765fce044aa529d`
-  24. Sistemas lineares — `fo_ca6792dde1f3037a`
-  25. Produtos notáveis e Fatoração — `fo_f6488d78723ab2dd`
-  26. Exercícios sobre Produtos notáveis e Fatoração — `fo_bc75348f43f367ea`
-  27. Polinômios I — `fo_c70f0fe0f14e434c`
-  28. Polinômios II — `fo_4e19a86899d50828`
-  29. Teoremas — `fo_0e230924ba84f501`
-  30. Equação polinomial — `fo_080ac3298287cb67`
-  31. Exercícios sobre polinômios — `fo_45b723d540cd9106`
-  32. Números complexos — `fo_80e6efd5999d21d6`
-  33. Exercícios sobre números complexos — `fo_d75a39afd6ece7e9`
-  34. Forma trigonométrica de complexos — `fo_77bf7cd83cef58e6`
-  35. Fórmulas de Moivre — `fo_cef63861a8db233a`
-  36. Exercícios sobre forma trigonométrica complexos — `fo_6fa279174bbd1361`
-  37. Raízes complexas — `fo_d0b3e53160d380e1`
-  38. Exercícios sobre raízes complexas — `fo_811bc7b222f7aaa1`
-  39. Raízes Complexas (aula do curso 2025) — `fo_22474158f069d646`
-  40. Raízes Complexas - Exercícios (aula do curso 2025) — `fo_611847a70cb341ed`

#### Método Pomodoro


##### Método Pomodoro


**Método Pomodoro** (1 aulas)

-   1. Método Pomodoro — `fo_fa6b5050e79f487f`

#### Método de Cornell


##### Método de Cornell


**Método de Cornell** (1 aulas)

-   1. Método de Cornell — `fo_84e3bc9c7e64560a`

#### Método de Feynman


##### Método de Feynman


**Método de Feynman** (1 aulas)

-   1. Método de Feynman — `fo_d5449df9bb51e2cb`

#### Português I


##### Português I


**Português I** (29 aulas)

-   1. Introdução: o que é texto — `fo_7343ad88207d064c`
-   2. Linguagem — `fo_a26f88dc4f23fa77`
-   3. Estratégias de leitura — `fo_37e880916af87b04`
-   4. Identificação de ideias do texto — `fo_06c4bd92a794a3d5`
-   5. Intenção comunicativa — `fo_9f2263718db00bd3`
-   6. Interpretação de texto: Narrativo e injuntivo — `fo_025c3a2fa9d83ad4`
-   7. Interpretação de texto: Dissertativo — `fo_1bdd1fa0633fe088`
-   8. Interpretação de texto: Expositivo — `fo_bd50ee276e07ae01`
-   9. Interpretação de texto: Descritivo — `fo_8a4bba3932729ac1`
-  10. Interpretação de textos jornalísticos — `fo_9dc81433831830ee`
-  11. Interpretação de textos literários — `fo_d32a3b4ed79e4387`
-  12. Interpretação de quadrinhos — `fo_b211b0783264fb37`
-  13. Interpretação de gráfico e infográfico — `fo_5bf28bf8a0bbc2e8`
-  14. Intertextualidade — `fo_5c8802d304e85924`
-  15. Inferência: Explícitos — `fo_77e5880651db4071`
-  16. Inferência: Implícitos — `fo_0a7b7357f6f44bbe`
-  17. Operações textuais: Síntese, paráfrase e perífrase — `fo_2e8652b4c8846309`
-  18. Operações textuais: Tipos de discurso — `fo_35d5388684782dcf`
-  19. Coesão referencial — `fo_35cec9253bac1641`
-  20. Coesão conectiva — `fo_ee3add711c522b27`
-  21. Semântica — `fo_675adf79c2a11a43`
-  22. Ambiguidade — `fo_195c05646d7c226f`
-  23. Figuras de Linguagem: Palavras e construção — `fo_56eeb09f85df1ff0`
-  24. Figuras de Linguagem: Pensamento — `fo_808cbe4600c8e98a`
-  25. UFPR: Tipos de leitura — `fo_f114f1409e7490a1`
-  26. UFPR: Tipos de questão — `fo_865ee7d1a175bfa9`
-  27. UFPR: Análise de alternativas — `fo_b610ac314c91b257`
-  28. UFPR: Análise de múltipla escolha — `fo_c4c28537dbd0bd80`
-  29. UFPR: Análise de comando textual — `fo_dfefbc2eac7392c0`

#### Português II


##### Português II


**Português II** (47 aulas)

-   1. Fonologia — `fo_4407940ffeaa1477`
-   2. Acentuação — `fo_0faefc2e0f6e2490`
-   3. Emprego do hífen — `fo_61d0cf5719acfa9a`
-   4. Estrutura e formação de palavras — `fo_275e77051fdb97ac`
-   5. Substantivos — `fo_075568abb99e4ed1`
-   6. Adjetivos — `fo_915eaae42ea34815`
-   7. Pronomes — `fo_ededfd034999452e`
-   8. Verbos — `fo_f22c57ff5afb4735`
-   9. Advérbios — `fo_a94866bfd68f3243`
-  10. Sujeito — `fo_6a390b7ad9724c71`
-  11. Predicado — `fo_2b284e8d99d3f61e`
-  12. Termos integrantes da oração — `fo_433644ee17a90447`
-  13. Termos acessórios da oração — `fo_d8ec5ee1156457d4`
-  14. Concordância verbal — `fo_b12d67239ee64e8e`
-  15. Concordância nominal — `fo_794c19bb935e08fe`
-  16. Regência Verbal + Nominal — `fo_765ecaf974c8d0f6`
-  17. Crase — `fo_712fcefe8104b63a`
-  18. Colocação pronominal — `fo_52fa2144c7692f90`
-  19. Oração coordenada — `fo_94fe5a9366b7f627`
-  20. Oração subordinada substantiva — `fo_69f2ba64303b1d83`
-  21. Oração subordinada adjetiva — `fo_d80136844d25192a`
-  22. Oração subordinada adverbial — `fo_dfec162316ad6971`
-  23. Pontuação — `fo_9010eadd39709d20`
-  24. Aula extra - Exercícios: Fonologia — `fo_7c7c4b7a68d8e53f`
-  25. Aula extra - Exercícios: Acentuação — `fo_a9981b2e78e74697`
-  26. Aula extra - Exercícios: Emprego do hífen — `fo_1c773325d9b971f9`
-  27. Aula extra - Exercícios: Estrutura e formação de palavras I — `fo_785b7f580f81402d`
-  28. Aula extra - Exercícios: Estrutura e formação de palavras II — `fo_d3f75f311fac3072`
-  29. Aula extra - Exercícios: Substantivo — `fo_54c0e366fb00a056`
-  30. Aula extra - Exercícios: Adjetivos — `fo_b434acc720d7e524`
-  31. Aula extra - Exercícios: Pronomes — `fo_66d6f03c79b73137`
-  32. Aula extra - Exercícios: Verbos — `fo_8ec0ad0ab88ceab4`
-  33. Aula extra - Exercícios: Advérbios — `fo_9621b4f28d3573c8`
-  34. Aula extra - Exercícios: Sujeito e predicado — `fo_06bc83294336bfb2`
-  35. Aula extra - Exercícios: Concordância verbal — `fo_2545c510d8860349`
-  36. Aula extra - Exercícios: Regência verbal + nominal — `fo_6c1d6e5580ddc8d2`
-  37. Aula extra - Exercícios: Crase — `fo_9832a2626b4114c6`
-  38. Aula extra - Exercícios: Colocação pronominal — `fo_f3c96cf6982398a3`
-  39. Aula extra - Exercícios: Oração coordenada — `fo_0b0044e6d6f97220`
-  40. Aula extra - Exercícios: Oração subordinada substantiva — `fo_3b57a8628f3c228d`
-  41. Aula extra - Exercícios: Oração subordinada adverbial — `fo_d1164177b6e548bf`
-  42. Aula extra - Exercícios: Pontuação — `fo_7456c97286a84e59`
-  43. Aula extra - Exercícios: Figuras de linguagem — `fo_4542fe6371edd5cd`
-  44. Aula extra - Exercícios: UFPR 2019-2020 — `fo_c4aa1f2ceae1f3cd`
-  45. Aula extra - Exercícios: UFPR 2017-2018 e 2018-2019 — `fo_8f0db0fb27c1a36b`
-  46. Aula extra - Exercícios: UFPR 2016-2017 e outras questões do NC-UFPR — `fo_95031865bfb86247`
-  47. Aula extra - Exercícios: UFPR 2014-2015 e outras questões do NC-UFPR — `fo_579ef8c64013a0e4`

#### Química I


##### Química I


**Química I** (30 aulas)

-   1. Classificação da matéria — `fo_b59134869bcee29a`
-   2. Separação de misturas — `fo_1f2fdf23be046860`
-   3. Leis ponderais — `fo_a4db300f36f00195`
-   4. Balanceamento — `fo_9ced4133a87b75f6`
-   5. Modelos atômicos — `fo_c6c3506afb72b6c0`
-   6. Átomo de Bohr e Distribuição eletrônica — `fo_454148e49d56f05d`
-   7. Organização da tabela periódica — `fo_23854f4805ab6efe`
-   8. Tendências periódicas — `fo_ba76f424e0057f3a`
-   9. Ligações covalentes — `fo_e0f05b0458ff4048`
-  10. Ligações iônicas e metálicas — `fo_f282ea6a3154943f`
-  11. Geometria molecular e Polaridade — `fo_f28256c8d96f5bbf`
-  12. Forças intermoleculares — `fo_b768b02a13936c06`
-  13. NOX — `fo_311229c4e552010c`
-  14. Exercícios sobre química geral — `fo_66852004f033bfce`
-  15. Ácidos I — `fo_1d6c25d5e9538462`
-  16. Ácidos II — `fo_5b309013da642889`
-  17. Bases — `fo_e2505cdd5131c7c8`
-  18. Sais — `fo_e5fa9347d58abbd8`
-  19. Óxidos — `fo_ef5ea26e4ae04a09`
-  20. Reações inorgânicas — `fo_f8f5700cfc631d59`
-  21. Definição de soluções — `fo_8046a1de4657552e`
-  22. Concentração de soluções — `fo_c1f9e576e7b440f1`
-  23. Mistura de soluções — `fo_21bc53736297a731`
-  24. Propriedades coligativas — `fo_2d728cf137421e70`
-  25. Exercícios sobre soluções — `fo_936a9f2e3734b595`
-  26. Radioatividade I — `fo_b38f6f7d1823a3b1`
-  27. Radioatividade II — `fo_54d89fb818c7dc22`
-  28. Números quânticos e Carga formal — `fo_3f58d76fe3b6911f`
-  29. Teoria ácido-base de Bronsted-Lowry e Lewis — `fo_4fcd3510609a2a09`
-  30. Química ambiental — `fo_82c59a01cf13d86e`

#### Química II


##### Química II


**Química II** (30 aulas)

-   1. Relações de massa — `fo_4ded675e5cea4f4c`
-   2. Relações de massa e mol — `fo_e1688ea619cb9750`
-   3. Determinação de fórmulas químicas e Isotopia — `fo_4c8c00ef647503ce`
-   4. Gases I — `fo_c52fe6d73d388f7b`
-   5. Gases II — `fo_9a5714cc5abfe8a6`
-   6. Balanceamento — `fo_6060e4ee938e0fad`
-   7. Estequiometria — `fo_dabde8d73e9f5868`
-   8. Pureza e Hidratação — `fo_32fb02532e819dc8`
-   9. Exercícios sobre estequiometria — `fo_8f2203443791d664`
-  10. Reações termoquímicas — `fo_24206dcc9aa439f2`
-  11. Entalpia — `fo_5b4e8dcc11022eed`
-  12. Lei de Hess — `fo_4863e33d0e3df486`
-  13. Leis da termodinâmica — `fo_420095e285d36178`
-  14. Oxirredução — `fo_735e20c8e29d52f1`
-  15. Pilhas I — `fo_4053591cf909939e`
-  16. Pilhas II — `fo_cccb4e0be34d2c26`
-  17. Eletrólise — `fo_e97cc3328e088ce8`
-  18. Eletrólise II — `fo_9558ac5b5a78d05e`
-  19. Exercícios sobre eletroquímica e termoquímica — `fo_bc75388faff5b378`
-  20. Cinética química I — `fo_63e39741d32866ff`
-  21. Cinética química II — `fo_e1fa73ad7ad7ea9b`
-  22. Equilíbrio químico I — `fo_f794a99789d47377`
-  23. Equilíbrio químico II — `fo_10fd662c2fadf3c6`
-  24. Equilíbrio iônico — `fo_45cf1c520ef8c4f0`
-  25. Exercícios sobre cinética química e equilíbrio — `fo_36c99f76c52ebb29`
-  26. pH — `fo_67d004bf9f4d603a`
-  27. Hidrólise salina — `fo_f17a36d5e4c3d576`
-  28. Solução tampão — `fo_d1e52b2e017587ac`
-  29. Produto de solubilidade (kps) — `fo_1174634c535387dd`
-  30. Exercícios finais — `fo_8cd9c754e9cdb58c`

#### Química III


##### Química III


**Química III** (30 aulas)

-   1. Introdução à orgânica — `fo_809618ecd51bd729`
-   2. Cadeias carbônicas — `fo_741ea1e5825d74b2`
-   3. Hibridização e aromaticidade — `fo_812674542e118e0c`
-   4. Hidrocarbonetos de cadeia normal — `fo_cfb683b86a27185c`
-   5. Hidrocarbonetos de cadeia ramificada — `fo_65f4aed63c37bac7`
-   6. Hidrocarbonetos aromáticos — `fo_75e1be5a625e126c`
-   7. Exercícios sobre cadeias carbônicas — `fo_de0e697cf23c3856`
-   8. Álcoois, enóis e fenóis — `fo_947ccfbce1afc386`
-   9. Aldeídos e cetonas — `fo_7ce36d5f72ac7593`
-  10. Ácidos carboxílicos — `fo_9e3803e37c9579f9`
-  11. Ésteres e anidridos — `fo_807997fc5c4333d1`
-  12. Funções nitrogenadas e demais funções — `fo_e573deaaaa588a8a`
-  13. Exercícios sobre funções orgânicas — `fo_0aefb2f3a42b0ba9`
-  14. Isomeria plana — `fo_3ee3108c7a2e4411`
-  15. Isomeria geométrica — `fo_2842ba0235910291`
-  16. Isomeria óptica — `fo_e09a208a8557aea3`
-  17. Exercícios sobre isomeria — `fo_4233ea38c9f971b2`
-  18. Propriedades de compostos orgânicos — `fo_228ed1a6b12edab9`
-  19. Teorias ácido-base e Configuração R e S — `fo_1384008b4d9c203c`
-  20. Reação de substituição — `fo_5afe163f54fbcd30`
-  21. Reação de substituição e neutralização — `fo_1f6e4b895afa4f41`
-  22. Reação de adição — `fo_7dcb465d84c5b167`
-  23. Reação de oxidação/redução — `fo_6a51d8c3020be635`
-  24. Reação de eliminação — `fo_12995348b14dc54b`
-  25. Exercícios sobre reações orgânicas — `fo_358077bff09ebb92`
-  26. Polímeros — `fo_0c3b9cff7b806bd8`
-  27. Reação de polimerização — `fo_a60919b0f2faf7d4`
-  28. Bioquímica — `fo_8ea4a860d7c9ee0e`
-  29. Exercícios sobre polimerização — `fo_2b89b19799301e44`
-  30. Revisão geral — `fo_eb7dbb6f3c06fcf5`

#### Sociologia UFPR


##### Sociologia UFPR


**Sociologia UFPR** (35 aulas)

-   1. Introdução às ciências sociais — `fo_0b9c382d3fc982a0` ✓validada
-   2. Émile Durkheim: Instituições e fato social — `fo_a53700251bacb29b`
-   3. Émile Durkheim: Fato social normal e anomia — `fo_a7c6fa76872d6946`
-   4. Émile Durkheim: Solidariedade mecânica e orgânica — `fo_228bb9d1d4570bbf`
-   5. Max Weber: Sociologia compreensiva e ações sociais — `fo_c7b900a9bd396c62`
-   6. Max Weber: Tipo ideal — `fo_db71843a23d740ed`
-   7. Max Weber: Dominação e desencantamento do mundo — `fo_826377bcd5e2aeb4`
-   8. Karl Marx: Fontes do marxismo — `fo_f3084dbea026bdcd`
-   9. Karl Marx: Concepção de sociedade, base e superestrutura — `fo_52d11f6bd9152ecb`
-  10. Karl Marx: Mais-valia e alienação — `fo_1d1d96379393109a`
-  11. As Clássicas do Pensamento Social: Introdução — `fo_db5a401d8b47672b`
-  12. 1º Capítulo: Harriet Martineau — `fo_7e53e107f749b9e0`
-  13. 2º Capítulo: Anna Júlia Cooper — `fo_87c882e082486a54`
-  14. 3º Capítulo: Pandita Ramabai — `fo_05b56ab8e7bc0702`
-  15. 4º Capítulo: Charlotte Gilman — `fo_cf02ff0f0424abb4`
-  16. 5º Capítulo: Olive Schreiner — `fo_25f0e1df6a25d032`
-  17. 6º Capítulo: Alexandra Kollontai — `fo_3a71116baecb11a1`
-  18. 7º Capítulo: Ercília Nogueira Cobra — `fo_82bdeaf94a220cf9`
-  19. 8º Capítulo: Alfonsina Storni — `fo_f2462f27b47e793a`
-  20. O pacto da branquitude - Introdução — `fo_5f1a0289707372fc`
-  21. Pacto narcísico (branquitude e colonização europeia) — `fo_d2e68b7e54599c94`
-  22. Capitalismo racial — `fo_f71ae01708c8420d`
-  23. Racismo institucional — `fo_15675e5b353286a0`
-  24. O caso das mulheres — `fo_d30cd39b42d81fba`
-  25. Projetos de transformação — `fo_5038f1c45eb8239f`
-  26. Quem tem medo do gênero? - Introdução — `fo_f720bf17a093c963`
-  27. O cenário global — `fo_207ac601ada789bc`
-  28. Feminismo radical — `fo_811f0182060181e3`
-  29. Natureza e cultura — `fo_d9067dda6ac49bf9`
-  30. O medo da destruição — `fo_612e01f8503321b2`
-  31. Sobre o autoritarismo no Brasil - Introdução — `fo_c8aa55842bb02cdc`
-  32. Escravidão e mandonismo — `fo_f4eab9715421ba83`
-  33. Patrimonialismo e corrupção — `fo_bbca419fc894181b`
-  34. Desigualdade social — `fo_8dd8c31b70267152`
-  35. Raça e gênero — `fo_0cb44c15b3ec9ddd`

### Simulados e Resolução de Provas


#### Biologia


##### Biologia


**Biologia** (63 aulas)

-   1. Prova de 2019/2020 — `fo_c36f1e9470588772`
-   1. Prova de 2020/2021 - Parte I — `fo_fe91140f33e831e8`
-   1. Prova de 2024/2025 — `fo_797937f0baf58a0e`
-   1. Prova de 2025/2026 - 1º — `fo_3f3307280be17f5a`
-   1. UFPR 2024/2025 — `fo_f5575081e9dfb4f0`
-   2. Prova de 2018/2019 — `fo_4b61fd106a7d6400`
-   2. Prova de 2020/2021 - Parte II — `fo_f1493c344ca35f71`
-   2. Prova de 2023/2024 — `fo_ef72e4fc906cf139`
-   2. Prova de 2024/2025 - 2º — `fo_38c4061936c1aca7`
-   2. UFPR 2023/2024 — `fo_43c0e5cb62e5cf08`
-   3. Prova de 2017/2018 — `fo_4ab0569d63a72f1b`
-   3. Prova de 2019/2020 - Parte I — `fo_bd63118ab6ef6f7c`
-   3. Prova de 2022/2023 — `fo_aea842b9f4cd3466`
-   3. Prova de 2024/2025 - 1º — `fo_2874f7f61b1b2dab`
-   3. UFPR 2022/2023 - Parte 1 — `fo_b9a19037e35da52b`
-   4. Prova de 2016/2017 — `fo_cc665ff12cb8bafc`
-   4. Prova de 2019/2020 - Parte II — `fo_53dfb902730c4446`
-   4. Prova de 2021/2022 — `fo_3820072ade23ccdb`
-   4. Prova de 2023/2024 - 2º — `fo_06cdac6dbd95d766`
-   4. UFPR 2022/2023 - Parte 2 — `fo_b3476a7362db4892`
-   5. Prova de 2015/2016 — `fo_790c7515bdd20f42`
-   5. Prova de 2018/2019 — `fo_4c3e664f676070d8`
-   5. Prova de 2020/2021 — `fo_76a79c7ae2ec6445`
-   5. Prova de 2023/2024 - 1º — `fo_739eee88a778fb28`
-   5. UFPR 2019/2020 - Parte 1 — `fo_2d8bf458d27121af`
-   6. Prova de 2017/2018 — `fo_73ddb98fd6435c1d`
-   6. Prova de 2019/20 20 — `fo_cbd1273dcec98333`
-   6. Prova de 2022/2023 - 2º — `fo_77cdf56a6daf1a34`
-   6. UFPR 2019/2020 - Parte 2 — `fo_f8ae4f38f1f24376`
-   7. Prova de 2016/2017 — `fo_0fc752e4870e2501`
-   7. Prova de 2018/2019 — `fo_bc47cc00f97d3f04`
-   7. Prova de 2022/2023 - 1º — `fo_385fadf92f8dcd1f`
-   7. UFPR 2018/2019 - Parte 1 — `fo_653b68fe148e9b96`
-   8. Prova de 2015/2016 — `fo_cd398c129c2df300`
-   8. Prova de 2017/2018 — `fo_28695e4bea468e34`
-   8. Prova de 2021 — `fo_bb3ae674b5dad451`
-   8. UFPR 2018/2019 - Parte 2 — `fo_d39909d8850547b6`
-   9. Prova de 2014/2015 — `fo_d785d6014d5b6c6a`
-   9. Prova de 2016/2017 — `fo_56e955b9f7220fc1`
-   9. Prova de 2020 — `fo_5d1ad4aaad4cedf0`
-   9. UFPR 2017/2018 - Parte 1 — `fo_18a4d7fdfb2a2d21`
-  10. Prova de 2015/2016 — `fo_fe36138ae31e7826`
-  10. Prova de 2019 — `fo_c816bef2ab5f66c9`
-  10. UFPR 2017/2018 - Parte 2 — `fo_ca909a6953e58113`
-  11. Prova de 2014/2015 — `fo_b815ff1b62d66750`
-  11. Prova de 2018 — `fo_5330cc454aa17ea3`
-  11. UFPR 2016/2017 - Parte 1 — `fo_71b8951ef8fab766`
-  12. Prova de 2013/2014 — `fo_42433c53f421680c`
-  12. Prova de 2017 — `fo_36a76e4c7d60f4f2`
-  12. UFPR 2016/2017 - Parte 2 — `fo_03bf915eabbb03da`
-  13. Prova de 2012/2013 — `fo_f05df6c2c6765ca0`
-  13. UFPR 2016/2017 - Parte 3 — `fo_e8beab8d08d6afc5`
-  14. Prova de 2011/2012 — `fo_5ec0c6c690e22e7e`
-  14. UFPR 2015/2016 - Parte 1 — `fo_072ec94eb2f412c0`
-  15. Prova de 2010/2011 — `fo_75994da79aa321c3`
-  15. UFPR 2015/2016 - Parte 2 — `fo_e6f8b4f7887acda3`
-  16. Prova de 2009/2010 — `fo_f4afed5ad7ec8f71`
-  16. UFPR 2014/2015 - Parte 1 — `fo_b50ee3035b64acb6`
-  17. UFPR 2014/2015 - Parte 2 — `fo_0ce4f697a5a6b062`
-  18. UFPR 2013/2014 - Parte 1 — `fo_732b7afac05dddf6`
-  19. UFPR 2013/2014 - Parte 2 — `fo_0fd358d7a46457ec`
-  20. UFPR 2012/2013 - Parte 1 — `fo_cae2152216fe62ca`
-  21. UFPR 2012/2013 - Parte 2 — `fo_408b9df5c26434e8`

#### Espanhol


##### Espanhol


**Espanhol** (39 aulas)

-   1. Prova de 2019/20 — `fo_5d3a668c9a7c5310`
-   1. Prova de 2019/2020 — `fo_7c247312cb4b0c13`
-   1. Prova de 2024/2025 — `fo_3a96263e0db9611b`
-   1. Prova de CR 2025/26 - 1º — `fo_e449e225ed1e47cf`
-   2. Prova de 2018/19 — `fo_5930b1826ba89029`
-   2. Prova de 2018/2019 — `fo_421c60819db61e2a`
-   2. Prova de 2023/2024 — `fo_fc7e4cb21284b003`
-   2. Prova de 2024/2025 - 2° — `fo_f18d37e29de16e29`
-   3. Prova de 2017/18 — `fo_65ae86ba3fc12bed`
-   3. Prova de 2017/2018 — `fo_beb524b5c34a5275`
-   3. Prova de 2022/2023 — `fo_ada2db1e025b4610`
-   3. Prova de 2024/2025 - 1° — `fo_5a7e32017a28cb14`
-   4. Prova de 2016/17 — `fo_ec915a0f4099a4c1`
-   4. Prova de 2016/2017 — `fo_5d2db29e10840b24`
-   4. Prova de 2021/2022 — `fo_61ea4b12b544dac3`
-   4. Prova de 2023/2024 - 2° — `fo_7d65f6b9d7605624`
-   5. Prova de 2015/16 — `fo_2965c9c89bcf276b`
-   5. Prova de 2015/2016 — `fo_b97a9757e6d12158`
-   5. Prova de 2020/2021 — `fo_2549ccb3ef9ff3e0`
-   5. Prova de 2023/2024 - 1° — `fo_83676d11ccf4d190`
-   6. Prova de 2014/15 — `fo_dd90a47b9923c1f3`
-   6. Prova de 2019/2020 — `fo_1708314fd0fd594b`
-   6. Prova de 2022/2023 - 2° — `fo_2995c59934db8868`
-   7. Prova de 2018/2019 — `fo_4064957d2e0f0cb2`
-   7. Prova de 2022/2023 - 1° — `fo_b4f9448217b230af`
-   8. Prova de 2017/2018 — `fo_c9cea338da07c556`
-   8. Prova de 2021 — `fo_eec0aa9d12664213`
-   9. Prova de 2016/2017 — `fo_a1c7588d78a7c49c`
-   9. Prova de 2020 — `fo_266151f3c9dceb79`
-  10. Prova de 2015/2016 — `fo_6a09e5131118c443`
-  10. Prova de 2019 — `fo_16988313aacd7b8c`
-  11. Prova de 2014/2015 — `fo_6046d569bf03bd0e`
-  11. Prova de 2018 — `fo_9576197cb777193b`
-  12. Prova de 2013/14 — `fo_a674c8b13dbd9c45`
-  12. Prova de 2017 — `fo_e5b73b545a43c1c0`
-  13. Prova de 2012/2013 — `fo_8be7199f37a48482`
-  14. Prova de 2011/2012 — `fo_dad38be327c9e22a`
-  15. Prova de 2010/2011 — `fo_3fce209ec0892840`
-  16. Prova de 2009/2010 — `fo_06323a28f847e754`

#### Física


##### Física


**Física** (43 aulas)

-   1. Prova 2025/2026 - 1 — `fo_4d9d87ffb5ca573e`
-   1. Prova de 2019/2020 — `fo_7c0fc80ec3a14211`
-   1. Prova de 2020/2021 - Parte I — `fo_6b35faa53253769e`
-   1. Prova de 2025/2026 — `fo_7fc581a0170556f8`
-   2. Prova 2024/2025 - 2° — `fo_14942191010ff55f`
-   2. Prova de 2018/2019 — `fo_7b8a217a13be21ee`
-   2. Prova de 2020/2021 - Parte II — `fo_d076fc18d11b3025`
-   2. Prova de 2024/2025 — `fo_af50d69e7cc6209a`
-   3. Prova 2024/2025 - 1° — `fo_893d6c120158ff5e`
-   3. Prova de 2017/2018 — `fo_65344aec4092e3d3`
-   3. Prova de 2019/2020 - Parte I — `fo_176afd542bbde375`
-   3. Prova de 2023/2024 — `fo_c651d5deaf982bbb`
-   4. Prova 2023/2024 - 2° — `fo_13ad5b9ccce9bb78`
-   4. Prova de 2016/2017 — `fo_d10dbdcf303ac981`
-   4. Prova de 2019/2020 - Parte II — `fo_cf08fb1b5d45e70b`
-   4. Prova de 2022/2023 — `fo_7d44976821fcc2cb`
-   5. Prova 2023/2024 - 1° — `fo_ca7bd1898014215c`
-   5. Prova de 2015/2016 — `fo_3586faed3eb0e86e`
-   5. Prova de 2018/2019 — `fo_bdba2cbd50f3e51c`
-   5. Prova de 2021/2022 — `fo_3415067f96d56f6c`
-   6. Prova 2022/2023 - 2° — `fo_eeccffeef5fa9766`
-   6. Prova de 2017/2018 — `fo_973cab628526d7ca`
-   6. Prova de 2020/2021 — `fo_25095d56605d19ce`
-   7. Prova 2022/2023 - 1° — `fo_4fe6637a8d5d0a68`
-   7. Prova de 2016/2017 — `fo_f477439fa660470c`
-   7. Prova de 2019/2020 — `fo_a4e1fb314a632e2b`
-   8. Prova 2021 — `fo_b28d77fd68f7525e`
-   8. Prova de 2015/2016 — `fo_753268fdd3270edd`
-   8. Prova de 2018/2019 — `fo_7fc823d0ba75c26d`
-   9. Prova 2020 — `fo_1f0ea579de3e3085`
-   9. Prova de 2014/2015 — `fo_d118a202e0ae7ef0`
-   9. Prova de 2017/2018 — `fo_ec3c8ed7de6450d1`
-  10. Prova 2019 — `fo_2ce82a45b4c02eef`
-  10. Prova de 2016/2017 — `fo_191b7173e23620dc`
-  11. Prova 2018 — `fo_7c21a79134e4c8b2`
-  11. Prova de 2015/2016 — `fo_0a75d09dd680d702`
-  12. Prova 2017 — `fo_a35ef3e943226ff5`
-  12. Prova de 2014/2015 — `fo_0675b8fc40340af3`
-  13. Prova de 2013/2014 — `fo_6b3c090304e1cd68`
-  14. Prova de 2012/2013 — `fo_6a7910e40c02b7c1`
-  15. Prova de 2011/2012 — `fo_62d633a209ae11e1`
-  16. Prova de 2010/2011 — `fo_73d705e2a06c61e1`
-  17. Prova de 2009/2010 — `fo_c100b8c5dcfc2bf7`

#### Geografia


##### Geografia


**Geografia** (40 aulas)

-   1. Prova de 2019/2020 — `fo_a1a748259222a9cd`
-   1. Prova de 2020/2021 — `fo_4f0919dcb0f67350`
-   1. Prova de 2024/2025 — `fo_fc4e68e6ce06b9fd`
-   1. Prova de 2025/2026 - 1° — `fo_a5fac5de5dcf9adf`
-   2. Prova de 2018/2019 — `fo_cd291d6c35578494`
-   2. Prova de 2019/2020 — `fo_08f971a317539c70`
-   2. Prova de 2023/2024 — `fo_4441f40c2c3d7757`
-   2. Prova de 2024/2025 - 2° — `fo_9c51d4fa077b2e33`
-   3. Prova de 2017/2018 — `fo_6f811f814c5ba446`
-   3. Prova de 2018/2019 — `fo_1c962244674f4c5c`
-   3. Prova de 2022/2023 — `fo_4dc2e98e42e73bbc`
-   3. Prova de 2024/2025 - 1° — `fo_a70ae2705005345e`
-   4. Prova de 2016/2017 — `fo_86893184bf27003c`
-   4. Prova de 2017/2018 — `fo_37b699d2f090f098`
-   4. Prova de 2021/2022 — `fo_b0897234a922ece9`
-   4. Prova de 2023/2024 - 2° — `fo_25d010097ade464a`
-   5. Prova de 2015/2016 — `fo_81e0314fb3f1a2cf`
-   5. Prova de 2016/2017 — `fo_3d0a9ddd685295c2`
-   5. Prova de 2020/2021 — `fo_5a7e7cc89e990fee`
-   5. Prova de 2023/2024 - 1° — `fo_eaa8ee60cf4e81bb`
-   6. Prova de 2015/2016 — `fo_6f209e44fa22b324`
-   6. Prova de 2019/2020 — `fo_0dcb0b7472fb2b00`
-   6. Prova de 2022/2023 - 2° — `fo_f769b8a6ce8b0f06`
-   7. Prova de 2014/2015 — `fo_8dd97244613274c2`
-   7. Prova de 2018/2019 — `fo_bc9908e2842cc2da`
-   7. Prova de 2022/2023 - 1° — `fo_f76a1af1f0f1c800`
-   8. Prova de 2017/2018 — `fo_dfb928ec0fbb73ea`
-   8. Prova de 2021 — `fo_25e2dbfc30921a32`
-   9. Prova de 2016/2017 — `fo_f8e2b0a202029ba1`
-   9. Prova de 2020 — `fo_efc726ac66e9c396`
-  10. Prova de 2015/2016 — `fo_9f885ae79a7eea6c`
-  10. Prova de 2019 — `fo_b1eabacafd777595`
-  11. Prova de 2014/2015 — `fo_db7e8c076fe88476`
-  11. Prova de 2018 — `fo_e0eb8e63d9104b03`
-  12. Prova de 2013/2014 — `fo_a3f17da7b966ccdf`
-  12. Prova de 2017 — `fo_eb01f7efcda61ac9`
-  13. Prova de 2012/2013 — `fo_b308402c08d43fcf`
-  14. Prova de 2011/2012 — `fo_53dae7a9754131c0`
-  15. Prova de 2010/2011 — `fo_917cfd898b9541c1`
-  16. Prova de 2009/2010 — `fo_094b8ad215f33e78`

#### História


##### História


**História** (31 aulas)

-   1. Prova de 2025/2026 — `fo_f5e3dffd84237421`
-   1. Prova de 2025/2026 - 2° — `fo_7afcbe2ae8db0fef`
-   2. Prova de 2024/2025 — `fo_d529e4b019c39d8e`
-   2. Prova de 2025/2026 - 1° — `fo_15a49bb36e9ccb19`
-   3. Prova de 2023/2024 - Parte I — `fo_c6d0fbaf80f14e58`
-   3. Prova de 2024/2025 - 2° — `fo_29c16536c7f25291`
-   4. Prova de 2023/2024 - Parte II — `fo_05ee0687ddbf3bc4`
-   4. Prova de 2024/2025 - 1° — `fo_adb8edf1329339c0`
-   5. Prova de 2022/2023 — `fo_e86163a08a1459cd`
-   5. Prova de 2023/2024 - 2° — `fo_dbb912be9443aee9`
-   6. Prova de 2021/2022 — `fo_10edbf48e074a706`
-   6. Prova de 2023/2024 - 1° — `fo_170d7a916f872ce1`
-   7. Prova de 2020/2021 — `fo_6956f702db0b5da1`
-   7. Prova de 2022/2023 - 2° — `fo_14cd50ec488c263f`
-   8. Prova de 2019/2020 — `fo_cf44d9b3075628cb`
-   8. Prova de 2022/2023 - 1° — `fo_73f59a00fdc4ac47`
-   9. Prova de 2018/2019 — `fo_e682097c3214a1b2`
-   9. Prova de 2021 — `fo_1f3a74cb71e98be4` ✓validada
-  10. Prova de 2017/2018 — `fo_72869f1c8c410c7e`
-  10. Prova de 2020 — `fo_10f2729462656fd5`
-  11. Prova de 2016/2017 — `fo_4f7653a7cbd66b33`
-  11. Prova de 2019 — `fo_4189f5ae22f76fbf`
-  12. Prova de 2015/2016 — `fo_73a6c97bcd8eaa1b`
-  12. Prova de 2018 — `fo_2f2c2906ccfb89b6`
-  13. Prova de 2014/2015 — `fo_3cec01e9a3321d02`
-  13. Prova de 2017 — `fo_881c61091c4f38ac`
-  14. Prova de 2013/2014 — `fo_5ee7fd174ee1754c`
-  15. Prova de 2012/2013 — `fo_763f1f36f999ccca`
-  16. Prova de 2011/2012 — `fo_fb10c6c17b4cf086`
-  17. Prova de 2010/2011 — `fo_fb0c69af609f535a`
-  18. Prova de 2009/2010 — `fo_fa9877e72ceb7897`

#### Inglês


##### Inglês


**Inglês** (40 aulas)

-   1. Prova de 2019/2020 — `fo_37ac5e04bf7404fe`
-   1. Prova de 2020/2021 — `fo_ee36a0d905e00242`
-   1. Prova de 2024/2025 — `fo_812da3d3361be318`
-   1. Prova de 2025/2026 - 1º — `fo_1e7c1b0dee65748d`
-   2. Prova de 2018/2019 — `fo_ff8469ebb57ea81d`
-   2. Prova de 2019/2020 — `fo_d53da7f8bd4d58d4`
-   2. Prova de 2023/2024 — `fo_296049a8a72ade8d`
-   2. Prova de 2024/2025 - 2º — `fo_a3f6194bd68270ae`
-   3. Prova de 2017/2018 — `fo_ef0d6dc19380acca`
-   3. Prova de 2018/2019 — `fo_c0188be88209bdd7`
-   3. Prova de 2022/2023 — `fo_770ec7b40bbbf7c5`
-   3. Prova de 2024/2025 - 1º — `fo_99efb795ccbb2c0b`
-   4. Prova de 2016/2017 — `fo_dfa265a5ab55f290`
-   4. Prova de 2017/2018 — `fo_ae6b435b8c67f809`
-   4. Prova de 2021/2022 — `fo_d5e49cd0d90bb1f7`
-   4. Prova de 2023/2024 - 2º — `fo_4a68ebddc1aca8fd`
-   5. Prova de 2015/2016 — `fo_5953ea4bb6383cc4`
-   5. Prova de 2016/2017 — `fo_e792d29f6db26a07`
-   5. Prova de 2020/2021 — `fo_5be2fe43534021f5`
-   5. Prova de 2023/2024 - 1º — `fo_8ee69de976d3504c`
-   6. Prova de 2015/2016 — `fo_c0f7cb3c5a8446c0`
-   6. Prova de 2019/2020 — `fo_06eaf065c0fdd9c5`
-   6. Prova de 2022/2023 - 2º — `fo_9a9a6d76d8019ce9`
-   7. Prova de 2014/2015 — `fo_b9cbe4d54fe507c7`
-   7. Prova de 2018/2019 — `fo_4cb1a5b26f2a8212`
-   7. Prova de 2022/2023 - 1º — `fo_14a55ef97e216994`
-   8. Prova de 2017/2018 — `fo_f36bcdefc753be6c`
-   8. Prova de 2021 — `fo_a68845eedf0df057`
-   9. Prova de 2016/2017 — `fo_4b916c6f65c30090`
-   9. Prova de 2020 — `fo_5e46dd4771b53160`
-  10. Prova de 2015/2016 — `fo_602c6bb6b5d9b678`
-  10. Prova de 2019 — `fo_e028c8eb01424543`
-  11. Prova de 2014/2015 — `fo_9b5293b27f6d379c`
-  11. Prova de 2018 — `fo_c58b486ff624cdba`
-  12. Prova de 2013/2014 — `fo_7f5424eb4b06107e`
-  12. Prova de 2017 — `fo_2acdac975bc2ea37`
-  13. Prova de 2012/2013 — `fo_c18df6ea0a28b89a`
-  14. Prova de 2011/2012 — `fo_ed0d23c0ff27f7b3`
-  15. Prova de 2010/2011 — `fo_e3399646603e26d4`
-  16. Prova de 2009/2010 — `fo_3cc9369a2d832762`

#### Matemática


##### Matemática


**Matemática** (46 aulas)

-   1. Prova de 2019/2020 — `fo_d15d9ec46efa16ef`
-   1. Prova de 2020/2021 - Parte I — `fo_94b953bdf82ae4ea`
-   1. Prova de 2025/2026 — `fo_2a1c7be19dfed715`
-   1. Prova de 2025/2026 - 2° — `fo_7a0da83872ddc0e0`
-   2. Prova de 2018/2019 — `fo_211e2118babdca8b`
-   2. Prova de 2020/2021 - Parte II — `fo_838063f15af8bcf0`
-   2. Prova de 2024/2025 — `fo_5db49aec073dd137`
-   2. Prova de 2025/2026 - 1° — `fo_c1fe7349eb880c54`
-   3. Prova de 2017/2018 — `fo_354df42619fd98cd`
-   3. Prova de 2019/2020 - Parte I — `fo_532b047ef055e73e`
-   3. Prova de 2023/2024 - Parte I — `fo_54e8191dc0a09f1d`
-   3. Prova de 2024/2025 - 2° — `fo_6323cae3e7c89b0f`
-   4. Prova de 2016/2017 — `fo_d94c241480757e2d`
-   4. Prova de 2019/2020 - Parte II — `fo_15629a681d042f00`
-   4. Prova de 2023/2024 - Parte II — `fo_45ef6d83151b581f`
-   4. Prova de 2024/2025 - 1° — `fo_0c24fb40a15b7a70`
-   5. Prova de 2015/2016 — `fo_d6b2e094a16bb4d3`
-   5. Prova de 2018/2019 - Parte I — `fo_1791c5a5384a6886`
-   5. Prova de 2022/2023 — `fo_94a5296293b2976a`
-   5. Prova de 2023/2024 - 2° — `fo_a281e390a6fdc26f`
-   6. Prova de 2018/2019 - Parte II — `fo_d6d4c4e8699535f1`
-   6. Prova de 2021/2022 — `fo_6efeac675c694375`
-   6. Prova de 2023/2024 - 1° — `fo_a134818a0a53f428`
-   7. Prova de 2014/2015 - Parte I — `fo_45b9b9b3c3aad11b`
-   7. Prova de 2020/2021 — `fo_df752994fb5e93d6`
-   7. Prova de 2022/2023 - 2° - Parte I — `fo_5f7735d9406056de`
-   8. Prova de 2014/2015 - Parte II — `fo_64ae7f653a2bf808`
-   8. Prova de 2019/2020 — `fo_1a67122689dafc15`
-   8. Prova de 2022/2023 - 2° - Parte II — `fo_c4894020b6fb2491`
-   9. Prova de 2018/2019 — `fo_27d83d8655c28652`
-   9. Prova de 2022/2023 - 1° — `fo_a21cd154f700e34d`
-  10. Prova de 2017/2018 — `fo_371f5f3bce6323a3`
-  10. Prova de 2021 — `fo_2e071618444c3be6`
-  11. Prova de 2016/2017 — `fo_22751ff9a1b606b0`
-  11. Prova de 2020 — `fo_5ca836712b0ab181`
-  12. Prova de 2015/2016 — `fo_c59f6b945f432145`
-  12. Prova de de 2019 — `fo_f3a49d6218ee2be2`
-  13. Prova de 2014/2015 — `fo_b2fe03ad07547167`
-  13. Prova de 2018 — `fo_d76114d52791ae4f`
-  14. Prova de 2013/2014 — `fo_ebbe69bc133346be`
-  14. Prova de 2017 — `fo_4433c406d3f7eedd`
-  15. Prova de 2012/2013 — `fo_c8800716b1463ba4`
-  16. Prova de 2011/2012 — `fo_3d1928ebaee215c5`
-  17. Prova de 2010/2011 — `fo_e35096d321ae107a`
-  18. Prova de 2009/2010 - Parte I — `fo_45af473522641ed6`
-  19. Prova de 2009/2010 - Parte II — `fo_296d08b97fc20e21`

#### Português


##### Português


**Português** (51 aulas)

-   1. Prova de 2019/2020 — `fo_1210f1aba93fc35e`
-   1. Prova de 2020/21 - Parte I — `fo_25dea33eed52d970`
-   1. Prova de 2025/2026 — `fo_34705dcecc295f93`
-   1. Prova de 2025/2026 - 2° — `fo_f1320ccbdf540925`
-   2. Prova de 2018/2019 — `fo_01fcc25b900ec64d`
-   2. Prova de 2020/21 - Parte II — `fo_c44162f50e7cb71f`
-   2. Prova de 2024/2025 — `fo_b34f9207249b0420`
-   2. Prova de 2025/2026 - 1° — `fo_2f868a4e284f2aff`
-   3. Prova de 2017/2018 — `fo_d88b3e623d933e47`
-   3. Prova de 2019/20 - Parte I — `fo_acab38fa72dada92`
-   3. Prova de 2023/2024 — `fo_88cebaebe17cfd50`
-   3. Prova de 2024/2025 - 2° — `fo_6b4f642bf65b66d6`
-   4. Prova de 2016/2017 — `fo_1802b8aeb47e614d`
-   4. Prova de 2019/20 - Parte II — `fo_12e38e2e6edcf990`
-   4. Prova de 2022/2023 — `fo_93ef588452789333`
-   4. Prova de 2024/2025 - 1° — `fo_cf31d29fd65db72d`
-   5. Prova de 2015/2016 — `fo_d965af06f9fc9acd`
-   5. Prova de 2018/19 - Parte I — `fo_6004b64e968011a2`
-   5. Prova de 2021/2022 — `fo_efe49d210cd25670`
-   5. Prova de 2023/2024 - 2° — `fo_b05bfaa63ae1bdc5`
-   6. Prova de 2018/19 - Parte II — `fo_10f14969f4dc61cf`
-   6. Prova de 2020/2021 — `fo_da892ec28c5286e4`
-   6. Prova de 2023/2024 - 1° — `fo_2a98606fba1b16d5`
-   7. Prova de 2017/18 - Parte I — `fo_9a1048a8f6bd17df`
-   7. Prova de 2019/2020 - Parte II — `fo_0dc8ccd948b93abb`
-   7. Prova de 2022/2023 - 2° — `fo_d7c33ce10e1c4237`
-   8. Prova de 2017/18 - Parte II — `fo_f7ee8d0fb25e3f5c`
-   8. Prova de 2019/2020 - Parte I — `fo_31a7419b6734be25`
-   8. Prova de 2022/2023 - 1° — `fo_6d9d751f40b25061`
-   9. Prova de 2016/17 — `fo_bfb6fded51a6e329`
-   9. Prova de 2018/2019 - Parte II — `fo_99879f3695f5181a`
-   9. Prova de 2021 — `fo_56734d4c373328b9`
-  10. Prova de 2015/16 - Parte I — `fo_11e88284c15339d9`
-  10. Prova de 2018/2019 - Parte I — `fo_93a2d15061e63363`
-  10. Prova de 2020 — `fo_cd5440ddc3b4e94e`
-  11. Prova de 2015/16 - Parte II — `fo_efad77228c46b2e4`
-  11. Prova de 2017/2018 - Parte II — `fo_9700cee59ecd16f8`
-  11. Prova de 2019 — `fo_37c961f07baf735a`
-  12. Prova de 2014/15 - Parte I — `fo_8cbad69f2df97a3c`
-  12. Prova de 2017/2018 - Parte I — `fo_c02b9e2f9df56c60`
-  12. Prova de 2018 — `fo_55bf870b88d15cf8`
-  13. Prova de 2014/15 - Parte II — `fo_41c4b1cd8639a654`
-  13. Prova de 2016/2017 — `fo_cee01beb41af71ea`
-  13. Prova de 2017 — `fo_3c2666a684518725`
-  14. Prova de 2015/2016 — `fo_95c6e35f3a7df72a`
-  15. Prova de 2014/2015 — `fo_0a78983645ba0843`
-  16. Prova de 2013/2014 — `fo_695de1a1ae7403d6`
-  17. Prova de 2012/2013 — `fo_29d59464a0568899`
-  18. Prova de 2011/2012 — `fo_1ba797713a1ae0f0`
-  19. Prova de 2010/2011 — `fo_03e30cbf6e434921`
-  20. Prova de 2009/2010 — `fo_52b5b44694329f57`

#### Química


##### Química


**Química** (67 aulas)

-   1. 2019/2020 - Parte 01 — `fo_eeb07e35883425e9`
-   1. Prova 2025/2026 - 2° — `fo_6400532579016e8f`
-   1. Prova de 2020/2021 — `fo_63e12cf30fd32546`
-   1. Prova de 2025/2026 — `fo_e9091aeccb627a90`
-   1. UFPR 2024/2025 — `fo_14328ced9a43f8de`
-   2. 2019/2020 - Parte 02 — `fo_0fda58d6c4e066f7`
-   2. Prova 2025/2026 - 1° — `fo_809e787c50636c1a`
-   2. Prova de 2019/2020 — `fo_87d3a0410a29770e`
-   2. Prova de 2024/2025 — `fo_9111d1bf97c64217`
-   2. UFPR 2023/2024 - Parte 1 — `fo_fcb0da47c8e9287f`
-   3. 2018/2019 - Parte 01 — `fo_cc00a503d5d2de12`
-   3. Prova 2024/2025 - 2° — `fo_9a51c173385b3961`
-   3. Prova de 2018/2019 — `fo_ed549a1427f33a1f`
-   3. Prova de 2023/2024 -Parte I — `fo_a73fb7a0d9a17dca`
-   3. UFPR 2023/2024 - Parte 2 — `fo_a8489c98e27ba718`
-   4. 2018/2019 - Parte 02 — `fo_0518cc1f8a913a58`
-   4. Prova 2024/2025 - 1° — `fo_70149467a33c5004`
-   4. Prova de 2017/2018 — `fo_fa6877ed2dec685f`
-   4. Prova de 2023/2024 - Parte II — `fo_8e9a7417379e1b8c`
-   4. UFPR 2022/2023 - Parte 1 — `fo_30581bc5346a3dc4`
-   5. 2017/2018 - Parte 01 — `fo_dba086317d6be17d`
-   5. Prova 2023/2024 - 2° — `fo_e99d8bbdea8c5279`
-   5. Prova de 2016/2017 — `fo_c9067f8d1fb792d1`
-   5. Prova de 2022/2023 — `fo_db03ef5173119270`
-   5. UFPR 2022/2023 - Parte 2 — `fo_c16e34eb0230bea3`
-   6. 2017/2018 - Parte 02 — `fo_28caa6f2e137bb2d`
-   6. Prova 2023/2024 - 1° — `fo_e57be2cba908425f`
-   6. Prova de 2015/2016 — `fo_274a502fcd798765`
-   6. Prova de 2021/2022 — `fo_c9585af9554c6c3e`
-   6. UFPR 2019/2020 - Parte 1 — `fo_0bea10947a70c316`
-   7. 2016/2017 - Parte 01 — `fo_3b04d89b43dbd74b`
-   7. Prova 2022/2023 - 2° — `fo_37cb2577290dcecb`
-   7. Prova de 2014/2015 — `fo_49a30bc82af17a62`
-   7. Prova de 2020/21 — `fo_ba90bb7fb5b94e53`
-   7. UFPR 2019/2020 - Parte 2 — `fo_cdffb7ffade280b2`
-   8. 2016/2017 - Parte 02 — `fo_9efd3ae6bd38ce71`
-   8. Prova 2022/2023 - 1° — `fo_499cc9ccd3bcfea6`
-   8. Prova de 2019/20 — `fo_21599601a44491fa`
-   8. UFPR 2018/2019 - Parte 1 — `fo_4c19a7a7d997e215`
-   9. 2015/2016 - Parte 01 — `fo_b12c9d76068b32c8`
-   9. Prova 2021 — `fo_bc41386b84d61019`
-   9. Prova de 2018/19 — `fo_df1396535a79f526`
-   9. UFPR 2018/2019 - Parte 2 — `fo_e48b7b8fe7337f68`
-  10. 2015/2016 - Parte 02 — `fo_38ed04dedaaec04b`
-  10. Prova 2020 — `fo_2c31f265b30aa63c`
-  10. Prova de 2017/2018 — `fo_00daf5009ab3065f`
-  10. UFPR 2017/2018 - Parte 1 — `fo_c39ff4f83f9648d6`
-  11. Prova 2019 — `fo_13e990842c053842`
-  11. Prova de 2016/2017 — `fo_e162a8c637ee220c`
-  11. UFPR 2017/2018 - Parte 2 — `fo_1a04c5df4f97976c`
-  12. Prova 2018 — `fo_54d2c626ae710009`
-  12. Prova de 2015/2016 — `fo_053d62948b3bb782`
-  12. UFPR 2016/2017 - Parte 1 — `fo_2a54ee0e7529dc2c`
-  13. Prova 2017 — `fo_9b90c5a227a0414b`
-  13. Prova de 2014/2015 — `fo_7d18630bc0db46bd`
-  13. UFPR 2016/2017 - Parte 2 — `fo_e09867c19bc3fd45`
-  14. Prova de 2013/2014 — `fo_5751114c35a55e3b`
-  14. UFPR 2015/2016 - Parte 1 — `fo_3930966d6e018b26`
-  15. Prova de 2012/2013 — `fo_73b2f34d2a6cb8a0`
-  15. UFPR 2015/2016 - Parte 2 — `fo_6cd0b9478a0887a1`
-  16. Prova de 2011/2012 — `fo_c596337d37fc0ee1`
-  16. UFPR 2014/2015 - Parte 1 — `fo_3e457d52b0d920dd`
-  17. Prova de 2010/2011 — `fo_34b63283685221ef`
-  17. UFPR 2014/2015 - Parte 2 — `fo_a2fd0f4355f3515e`
-  18. Prova de 2009/2010 — `fo_4ce0e98ecccd040a`
-  18. UFPR 2013/2014 — `fo_a950a0fbfcbae4e8`
-  19. UFPR 2012/2013 — `fo_c057e088f96f26b7`

#### Sociologia


##### Sociologia


**Sociologia** (2 aulas)

-   1. Prova 2023/24 - Parte 1 — `fo_e5cb97fa3eaf2d1a`
-   2. Prova 2023/24 - Parte 2 — `fo_5d66dfb4bf27853f`

### Simuladão UFPR #01 - Gratuito


#### Simuladão UFPR #01


##### Simuladão UFPR #01


**Simuladão UFPR #01** (2 aulas)

-   1. Instruções do Simuladão — `fo_28b01365771744de`
-   2. Como digitalizar as redações? — `fo_b36899ebc311e87d`

## Validação e reconciliação

- IDs exportados == SQLite present=1: **True** (3027 exportados / 3027 no banco).
- Unicidade de lesson_id atual: **True**.
- CSV e JSONL contêm as mesmas 3027 aulas canônicas (sem amostragem).
- Aliases protegidos (8) mantêm associação a transcrição validada/review: **True**.
- Recuperação de metadados sobreviveu à sincronização (renamed=0, created=0, missing=0); 38 aliases retirados, 8 backfilled.
- Aulas com metadados incompletos: **0** (0 títulos/disciplinas/módulos mascarados).
- Vazamento de informação privada: **nenhum** (caminhos OneDrive, URLs assinadas, extensões de mídia e identificadores de portal verificados ausentes).
- Caminhos privados do OneDrive, URLs assinadas e credenciais não são exportados; identificadores de curso baseados em URL são neutralizados para slug.
- `pdf_count=null`: materiais são de nível disciplina, sem vínculo por aula; `order=null` quando o snapshot não fornece ordem verificável.
