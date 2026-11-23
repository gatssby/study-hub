# Federal Online — operação de transcrição MVP

## Estado e escopo

Estado do corte em 23/11/2026 UTC: o candidato foi iniciado em um piloto real isolado, com três aulas em série. O worker legado foi parado e desabilitado; serviço, timer e runtime Parakeet foram removidos. O banco e a API de produção ainda não foram migrados. Confirme o estado real antes de operar. Os relatos anteriores de `generated_v2`, QA v4/v5 e revisor acústico são histórico, não instruções vigentes.

O candidato usa um único Whisper large-v3 FP16 por vez, modelo fixado por SHA-256 `64d182b440b98d5203c4f9bd541544d84c605196c4f7b845dfa11fb23594d1e2`, segmentos de 600 s com sobreposição de 2 s e checkpoints vinculados à identidade. O corpus aceito após reset é `whisper_mvp_v1` no SQLite existente. A API FO e o MCP Anki real são as interfaces de consulta; publicação exige revisão/fonte atuais e QA aprovado. Reviews permanecem privadas. Não há espelho OneDrive de derivados de transcrição; nunca tocar nos originais de vídeo ou PDF. Não interpretar QA aprovado como medida de precisão lexical.

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

## Reset de transcrições — destrutivo e único

Somente durante corte autorizado, depois de validar o piloto: identifique os leitores/escritores do SQLite; pare a transcrição e confirme ausência de decoder/lock ativo. Pause o indexador e o sincronizador OneDrive durante a troca de código/inventário, preservando os demais coletores. Confira a DB e o state root. Se necessário, use uma única cópia temporária consistente e privada para recuperação; verifique-a e remova-a após o corte. Registre contagens e fingerprints das tabelas de catálogo, fontes e PDFs; nunca substitua a DB compartilhada por uma DB vazia. Use um inventário novo (até uma hora), coletado exclusivamente por listagem. No diretório de trabalho do FO:

```sh
python -m fo_hub.onedrive --reset-inventory "$PRIVATE_INVENTORY"
python -m fo_hub.transcription --reset --db "$STUDY_HUB_FO_DB" --state-root "$FO_STATE_ROOT" --inventory "$PRIVATE_INVENTORY" --dry-run
```

Revise `delete_rows`, `queue_seed`, `corpus` e `already_reset`; `unverified_sources` deve ser zero. O piloto criado de uma cópia do banco removeu 147 transcrições, 48.953 linhas de segmentos e 3.847 jobs legados; semeou 2.828 vínculos novos e 2.828 evidências QuickXor, mantendo Inglês/Espanhol excluídos. Os números da produção podem mudar. Refaça o preview no destino exato, depois aplique com as mesmas variáveis e units transcritoras paradas:

```sh
python -m fo_hub.transcription --reset --db "$STUDY_HUB_FO_DB" --state-root "$FO_STATE_ROOT" --inventory "$PRIVATE_INVENTORY" --confirm-reset
```

O reset adquire `locks/transcription-worker.lock` e o lock adjacente à DB canônica sem esperar, registra recibo único e recusa repetição. Vincula QuickXor apenas a observações existentes cujo ID, tamanho, ModTime e revisão conferem; não infere mapeamentos nem remapeia aulas. Conflito de lock, DB ou escopo inesperado: abortar, não forçar. Verifique `PRAGMA quick_check`, a igualdade do conjunto de jobs com as identidades elegíveis, a preservação das outras tabelas e os fingerprints; nas observações de fonte só podem mudar o checksum acrescentado e seu `checked_at`. Verifique 404 do sentinela legado e zero resultados em busca pela API e MCP.

Para a primeira sincronização após o corte, o novo `fo_hub.onedrive` precisa publicar `remote-videos.json` com hashes antes de retomar `study-hub-fo-index.timer`. Não volte a rodar o produtor de inventário sem hashes. Implante somente os arquivos e a unit de transcrição deste release; não reinstale unidades de materiais/Anki/n8n. Após `systemd-analyze verify`, `daemon-reload` e preflight, habilite `study-hub-fo-transcription.service` para boot. Confirme um único decoder, progresso/recuperação e leitura de uma nova aprovação pelo MCP sem deploy extra. Limpe apenas alvos obsoletos comprovados; não remova cópias de recuperação mistas de outros componentes.

## Piloto, operação e recuperação

O piloto limitado utiliza somente os IDs autorizados, serialmente: `fo_1237714a067b1889` (Redação, 269 s), `fo_45b723d540cd9106` (Matemática, 726 s) e `fo_868214e019681924` (Química Polímeros, 1197 s). Durações são metadados de seleção, não resultados. Para uma execução autorizada após reset e preflight, o worker aceita seleção explícita repetida:

```sh
python -m fo_hub.worker --run --lesson-id fo_1237714a067b1889 --lesson-id fo_45b723d540cd9106 --lesson-id fo_868214e019681924
```

Não inicie outra cópia enquanto o piloto estiver ativo. Use unit transitória do systemd no diretório isolado com `FO_STATE_ROOT`, `STUDY_HUB_FO_DB` e `TRANSCRIPTION_ENABLED=true` explícitos. Não carregue o `EnvironmentFile` de produção no piloto: esse arquivo sobrescreve a DB isolada. Registre estados, checkpoints, QA, tempos ativos e consultas reais à API FO e MCP. Na operação contínua, `--run --loop` usa os mesmos locks; `--loop` e `--lesson-id` não podem ser combinados. A recuperação após interrupção deve ser verificada com checkpoint e resultado reais, não apenas pelo PID. Para retry autorizado, `python -m fo_hub.worker --retry LESSON_ID`; consulte o motivo antes e não force publicação.

Primeiro resultado real (23/11/2026 UTC): Redação `fo_1237714a067b1889`, 269,931 s de áudio, `APPROVED` sem avisos. Tempo ativo: 2,647 min por min de áudio (download 8,523 s; processamento 697,602 s; QA 0,027 s; publicação 8,331 s). O adaptador Anki MCP instalado, apontado à API isolada, recuperou todos os 29 segmentos com timestamps e confirmou busca/citações; a transcrição legada de controle permaneceu ausente. Produção ainda não migrada; Matemática e Química ainda não tinham resultado nesse registro.

WER de palavras requer referência independente e protocolo de normalização; sem referência, registre WER como não medido, nunca zero. Smoke técnico, QA e concordância de modelos não substituem referência humana.
