# Retired transcription index

O indexador do corpus antigo não é usado pela produção Study Hub. Textos e índices antigos foram excluídos na VPS, sem backups. Não executar `services/anki-api/rebuild_fo_search_index.py`: permanece somente como dependência de regressões legadas até sua classificação junto ao backend local com alterações anteriores.

O candidato MVP usa `whisper_mvp_v1` no SQLite existente, servido pela API FO e pelo MCP read-only, sem espelho OneDrive de derivados. O reset de produção e os resultados do piloto ainda não foram comprovados; `generated_v2` é legado. Para pré-requisitos, limites e operação autorizada, consultar `federal-online/transcription/ACTIVATION.md`.
