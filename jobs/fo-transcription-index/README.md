# Retired transcription index

O indexador do corpus antigo não é usado pela produção Study Hub. Textos e índices antigos foram excluídos na VPS, sem backups. Não executar `services/anki-api/rebuild_fo_search_index.py`: permanece somente como dependência de regressões legadas até sua classificação junto ao backend local com alterações anteriores.

O único corpus novo aceito é `generated_v2`, servido pela API FO independente e pelo MCP read-only. Workers de transcrição aguardam autorização explícita; consultar `docs/migration/2026-10-21/REPORT.md`.
