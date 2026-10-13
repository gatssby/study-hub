# Anki vNext Stage 9: editorial handling of the collection

Status: implemented with this document. Scope: API v2 + MCP v2 only. No legacy, no scheduling.

## Principle

Plugin -> MCP (thin adapter) -> API v2 (owns every rule) -> CollectionActor -> `anki.Collection`
(anki==26.9.3) -> official sync. The MCP never imports `anki`, never opens SQLite.
Every write: validate -> sync-before (fail closed on FULL_*) -> pace -> re-validate on fresh
state -> apply with the native op -> sync-after -> confirm -> report. Never FULL_UPLOAD/DOWNLOAD.

## Anki 26.9.3 facts measured (not assumed)

- Create: `col.new_note(nt)` + `col.add_note(note, deck_id)`. `add_note` does NOT validate
  cloze content, so `note.fields_check()` (EMPTY/DUPLICATE/MISSING_CLOZE/...) runs first.
- Delete notes: `col.remove_notes([ids])` (cards go with the note). Count = notes removed.
- Tags: `col.tags.all()`, `col.tags.rename(old,new)`, `col.tags.remove("a b")`. Both act on the
  tag AND its children (`pre` -> `pre::kid`) and return the affected NOTE count.
  Both are literal for `_`; `*` is a wildcard, so it is rejected by the API.
- Decks: `col.decks.add_normal_deck_with_name`, `.rename(id, name)`, `.remove([ids])`.
  Pitfalls handled by the API: blank components are silently rewritten to `blank`; renaming onto
  an existing name silently becomes `Name+`; `decks.remove` DELETES the deck's cards.
- Move: `col.set_deck(card_ids, deck_id)`. Scheduling fields (ivl/type/queue/due/factor/reps/
  lapses/memory_state) verified unchanged. An unknown card id in the list is skipped silently
  and an unknown deck raises, so the API validates every id first.
- `col.media.files_in_str` renders LaTeX (may write media files) and needs a real notetype;
  media refs are therefore extracted with a read-only regex mirroring Anki's `<img src>` and
  `[sound:]` rules.
- `col.sync_status(auth).required` is NO_CHANGES once the server has taken every local change
  (notes, cards, decks, tags, graves). It is the official way to confirm non-note writes.

## Preconditions (optimistic concurrency)

`revision` = `r1-` + sha256(note id, notetype id, ordered field values, sorted tags, sorted card
ids) truncated to 32 hex. Content based on purpose: `usn` changes when a sync merely carries the
note, which would raise false conflicts; `mod` has 1 s resolution. `mod` and `usn` are also
exposed for information. `card_ids` is part of the hash, so a delete is also guarded by it.

- `PATCH /v2/notes/{id}`: optional `expected_revision` (kept optional so the existing Plugin
  contract does not break; the tool description tells the model to pass it).
- `POST /v2/notes/delete`: `expected_revision` and `expected_card_ids` mandatory per note.
- Comparison happens AFTER sync-before, on the freshest state. Mismatch -> 409
  `stale_revision`, nothing written, no sync-after.

## Endpoints

| Method | Path | Notes |
|---|---|---|
| GET | /v2/notes/{id} | + `revision`, `mod`, `usn`, `deck_names`, `media` refs |
| PATCH | /v2/notes/{id} | + `expected_revision`; response + `revision` |
| POST | /v2/notes | create; 201 |
| POST | /v2/notes/delete | batch <= 10 notes |
| GET | /v2/note-types, /v2/note-types/{id} | read-only schemas |
| GET | /v2/tags | `prefix`, paginated |
| POST | /v2/tags/rename, /v2/tags/delete | `dry_run`, `expected_note_count`; <= 2000 notes |
| POST | /v2/decks | create (idempotent) |
| PATCH | /v2/decks/{id} | rename |
| DELETE | /v2/decks/{id}?expected_name= | only empty, no subdecks |
| POST | /v2/cards/move | <= 200 cards, all or nothing |
| GET | /v2/media/{filename} | + size cap, magic-byte MIME |

## Product decisions

- Create requires an existing, non-filtered deck and existing note type; unknown field -> 422;
  duplicate first field -> 409 unless `allow_duplicate`; no cards generated -> undo + 422.
- `delete_tag` removes the tag (and its children) from notes only. `expected_note_count` is
  mandatory; `dry_run` returns the count without writing.
- Deck delete: refuse if any card (subdecks included) -> 409 `deck_not_empty` with `card_count`;
  refuse if it has subdecks; never moves cards; Default and filtered decks are protected.
- Deck rename: renaming onto an existing name -> 409 `deck_exists`; subdecks follow natively.
- Move: filtered decks (as target or as the cards' current home) are refused.
- Images: `anki_get_note` returns refs only; `anki_get_media` returns one MCP `ImageContent`
  for jpeg/png/webp/gif up to 8 MiB. SVG/audio/video/other -> explicit
  `unsupported_media_type` error. API refuses files over 20 MiB.
- No merged tools: each operation keeps one clear intent for the model (a combined
  "delete_or_rename" would blur destructive vs. benign).
