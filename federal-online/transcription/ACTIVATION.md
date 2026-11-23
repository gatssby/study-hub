# Federal Online — operação de transcrição MVP

## Estado e escopo

Produção desde 23/11/2026 UTC: `study-hub-fo-transcription.service` executa `--run --loop`, ativo e habilitado no boot do Oracle ARM64. Release implantado: `787f6c9266ed20236a2c840d21c4657578b653cd`. SQLite `/home/ubuntu/study-hub-state/federal-online/hub.sqlite3`, state root `/home/ubuntu/study-hub-state/federal-online`. O piloto foi encerrado; há somente um worker e um decoder durante a inferência. Os fluxos e resultados das gerações anteriores são histórico, não instruções vigentes.

O worker usa um único Whisper large-v3 FP16, modelo fixado por SHA-256 `64d182b440b98d5203c4f9bd541544d84c605196c4f7b845dfa11fb23594d1e2`, janelas de 600 s com sobreposição de 2 s e checkpoints vinculados à identidade. O único corpus aceito é `whisper_mvp_v1` no SQLite existente. A API FO e o MCP Anki GPT vNext são as interfaces de consulta; publicação exige revisão/fonte atuais e QA aprovado. Resultados em revisão permanecem privados. Não há espelho OneDrive de derivados de transcrição; nunca tocar nos originais de vídeo ou PDF.

No Oracle ARM64: whisper.cpp `1.9.5-dev` (checkout `231638a`), modelo FP16, CPU, `-l pt -t 3 -bs 5 -bo 5 -mc 0 -tp 0 -tpi 0 -nth 0.6 -et 2.4 -lpt -1 -ng -ojf -nf`, sem VAD ou fallback. FFprobe e FFmpeg conferem duração e PTS dos frames PCM. QA checa cobertura em trechos não explicados por silêncio medido, validade dos timestamps, texto vazio/corrompido, loops/repetição grave, contradições fortes de silêncio e costura. Repetições plausíveis ficam no texto. `APPROVED` e `APPROVED_WITH_WARNING` publicam automaticamente; `REVIEW_REQUIRED` guarda o motivo e não publica. Somente o fim incompatível por padding comprovado pode ser corrigido, sem mudar palavras.

## Antes de operar

- Trabalhe na VPS somente após autorização explícita para a ação e janela pretendidas; confira código implantado, DB, `FO_STATE_ROOT`, serviço e processos efetivos. Não altere Anki, n8n, originais ou coletores para executar este procedimento.
- O worker exige `TRANSCRIPTION_ENABLED=true`, Linux, marker de plataforma e arquivo de autorização com o conteúdo exigido pelo código; verifique também binário, modelo, ferramentas e espaço. Não publique segredos.
- A partir do diretório do código FO e com o ambiente apropriado, por exemplo:

```sh
/home/ubuntu/study-hub-venv/bin/python -m fo_hub.worker --check-only
/home/ubuntu/study-hub-venv/bin/python -m fo_hub.worker --status
```

`--check-only` verifica dependências, SHA do modelo, reserva e estado, relatando `authorized` e `reset_applied`; não executa inferência. `--status` lê contagens e leases. Ambos exigem DB existente; sucesso não prova que o piloto ou a publicação passaram.

## Reset de transcrições — concluído em produção, não repetir

O procedimento abaixo documenta o corte aplicado; não é uma etapa de recuperação, deploy ou reinício normal. Em um corte autorizado e com piloto validado, identifique os leitores/escritores do SQLite; pare a transcrição e confirme ausência de decoder/lock ativo. Pause o indexador e o sincronizador OneDrive durante a troca de código/inventário. Preserve o catálogo, os demais coletores, PDFs e o banco compartilhado. Se necessário, use uma única cópia temporária consistente e privada para recuperação; verifique-a e remova-a após o corte. Registre contagens e fingerprints. Use um inventário novo (até uma hora), coletado exclusivamente por listagem. No diretório de trabalho do FO:

```sh
python -m fo_hub.onedrive --reset-inventory "$PRIVATE_INVENTORY"
python -m fo_hub.transcription --reset --db "$STUDY_HUB_FO_DB" --state-root "$FO_STATE_ROOT" --inventory "$PRIVATE_INVENTORY" --dry-run
```

Revise `delete_rows`, `queue_seed`, `corpus` e `already_reset`; `unverified_sources` deve ser zero. No corte de produção, 2.315 objetos OneDrive verificados forneceram evidência QuickXor para cada um dos 2.828 jobs únicos de aula/revisão elegíveis; Inglês/Espanhol permaneceram excluídos. Refaça o preview no destino exato antes de qualquer aplicação autorizada, com as mesmas variáveis e unidades transcritoras paradas:

```sh
python -m fo_hub.transcription --reset --db "$STUDY_HUB_FO_DB" --state-root "$FO_STATE_ROOT" --inventory "$PRIVATE_INVENTORY" --confirm-reset
```

O reset adquire `locks/transcription-worker.lock` e o lock adjacente à DB canônica sem esperar, registra recibo único e recusa repetição. Vincula QuickXor apenas a observações existentes cujo ID, tamanho, ModTime e revisão conferem; não infere mapeamentos nem remapeia aulas. Conflito de lock, DB ou escopo inesperado: abortar, não forçar. Verifique `PRAGMA integrity_check`, a igualdade do conjunto de jobs com as identidades elegíveis, a preservação das outras tabelas e os fingerprints; nas observações de fonte só podem mudar o checksum acrescentado e seu `checked_at`. Verifique 404 do sentinela legado e zero resultados em busca pela API e MCP.

Após o corte, mantenha `remote-videos.json` com hashes e o produtor `fo_hub.onedrive` deste release. Ao trocar a unit de transcrição, valide com `systemd-analyze verify`, `daemon-reload` e preflight; verifique a habilitação em `multi-user.target`, o gate, o lease ativo e o avanço de checkpoints. A unit limita partidas a três em 15 min e não reinicia em saídas de autorização ou conflito de lock. Use `python3 ops/study-hub/fo_monitor.py --once` e o journal da unit. Não reinstale unidades não relacionadas nem remova cópias de recuperação mistas.

## Piloto, operação e recuperação

O piloto limitado utiliza somente os IDs autorizados, serialmente: `fo_1237714a067b1889` (Redação, 269 s), `fo_45b723d540cd9106` (Matemática, 726 s) e `fo_868214e019681924` (Química Polímeros, 1197 s). Durações são metadados de seleção, não resultados. Para uma execução autorizada após reset e preflight, o worker aceita seleção explícita repetida:

```sh
python -m fo_hub.worker --run --lesson-id fo_1237714a067b1889 --lesson-id fo_45b723d540cd9106 --lesson-id fo_868214e019681924
```

Não execute piloto e produção no mesmo host ao mesmo tempo; não pare a produção apenas para repetir o piloto. Em janela autorizada, use uma unit transitória do systemd no diretório isolado com `FO_STATE_ROOT`, `STUDY_HUB_FO_DB` e `TRANSCRIPTION_ENABLED=true` explícitos. Não carregue o `EnvironmentFile` de produção no piloto: esse arquivo sobrescreve a DB isolada. Registre estados, checkpoints, QA, tempos ativos e consultas reais à API FO e MCP. Em operação contínua, `--run --loop` não aceita `--lesson-id`. A recuperação após interrupção deve ser verificada com checkpoint e resultado reais, não apenas pelo PID. Para retry autorizado, `python -m fo_hub.worker --retry LESSON_ID`; consulte o motivo antes e não force publicação.

Piloto real (23/11/2026 UTC): Redação `fo_1237714a067b1889`, 269,931 s, `APPROVED`, 29 segmentos ordenados e 2,647 s ativos/s de áudio; cobertura PCM reconferida com o mesmo vídeo verificado. Consulta, busca e citações conferidas na API e no MCP isolados. Matemática `fo_45b723d540cd9106`, 726,848 s, 2,365 s ativos/s, ficou em `REVIEW_REQUIRED` por repetição, segmento inválido e lacunas de cobertura; nenhum texto ficou disponível em consulta ou busca. Química `fo_868214e019681924` foi interrompida ao encerrar o piloto, sem resultado publicado.

Produção: recibo de reset às 01:26:11 UTC; 147 transcrições, 48.953 segmentos e 3.847 jobs anteriores removidos. A integridade SQLite e a preservação das 3.402 aulas, metadados de fontes e tabelas PDF foram conferidas na DB real. A unit permanente iniciou às 01:28 UTC com 2.828 jobs novos. Bioenergética (`fo_01c6dea4d18483ff`, rev. 2) saiu de 0% para 25,5%: primeiro checkpoint de 600 s PCM validado às 01:55 UTC, com o decoder já na janela seguinte. API FO e MCP serviram catálogo/PDFs da DB corrente e retornaram 404/sem resultados para consulta/busca do sentinela legado. A primeira publicação de uma aula nova em produção ainda não foi observada no fechamento do corte.

A remoção seletiva de artefatos de transcrição antigos, do piloto e da cópia temporária de recuperação liberou 1,77 GiB. Checkpoints atuais, originais e cópias de recuperação mistas com catálogo ou PDFs foram preservados.

WER de palavras requer referência independente e protocolo de normalização; sem referência, registre WER como não medido, nunca zero. Smoke técnico, QA e concordância de modelos não substituem referência humana.


## QA do MVP — calibração de 23/11/2026

A revisão dos arquivos de Bioenergética, Biologia molecular e Bioquímica (e dos quatro conjuntos de checkpoints originais) mostrou falsos positivos. Em especial, a soma de pequenas lacunas sem texto ou silêncio medido ultrapassava o limiar antigo de 5%, apesar de as aulas apresentarem segmentos coerentes até o final; as repetições do professor eram com frequência didáticas. Não houve transcrição humana de referência nem WER medido.

O commit `586b39c` mantém Whisper large-v3 como único ASR e adapta somente o QA:

- Lacunas agregadas acima de 5%: **aviso**; bloqueio apenas quando ultrapassam 30% da duração (mínimo de 20 s). Um único trecho inexplicado superior a 60 s, ou dominante em gravações curtas, continua bloqueando.
- Repetições curtas, duplicações de frases e pequenas sobreposições não são apagadas nem bloqueiam por si só. Loops extensos continuam bloqueados (pelo menos 30 palavras distribuídas por 12 s, ou 80 palavras em pelo menos 3 s).
- Texto de até 5 s inteiramente em silêncio medido torna-se aviso; conflito com silêncio medido de pelo menos 5 s continua bloqueando.
- Excesso de timestamp de até 50 ms no último segmento de um bloco só pode ser limitado ao fim medido com transcrição bruta conferida; não altera palavras.
- Integridade da fonte, áudio truncado, blocos ausentes, saída vazia, timestamps materialmente inválidos e exposição de texto rejeitado continuam protegidos.

Foram aprovados 86 testes focados. As quatro aulas que já estavam em review foram reavaliadas usando **16 checkpoints íntegros** vinculados a fontes e revisões atuais; não houve uma segunda inferência Whisper. Os quatro resultados tornaram-se `APPROVED_WITH_WARNING`, publicados em produção: Bioenergética (593 segmentos), Biologia molecular (580), Bioquímica (625) e Biotecnologia (629). A API FO confirmou HTTP 200, `qa.passed=true`, e o worker permanente foi religado (`active/enabled`), com um job ativo e nenhum lease obsoleto na verificação.

**Limitação externa, separada da API FO:** a conexão externa do Plugin apresentou `401 not_authorized_invalid_project` porque o projeto associado ao túnel está arquivado; API FO local, serviço MCP e worker seguem operacionais. Requer corrigir a autorização/configuração do projeto do túnel; não é erro do QA nem justificativa para recriar o banco.
