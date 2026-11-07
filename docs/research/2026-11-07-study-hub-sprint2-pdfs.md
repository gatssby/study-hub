# Study Hub Sprint 2 — PDF recovery and retention evidence (2026-11-07)

Read-only audit of `oracle-vps` (DB opened `mode=ro`; no writes, deletes, unit changes, OCR runs or inference). Only aggregate counters, hashes and prefixes recorded. Whisper was left running.

## Deployed code parity

The local and VPS SHA256 hashes match (local tree b18823f plus the change below, which is **not deployed**):

| file | sha256 |
|---|---|
| fo_hub/pdf_privacy.py | 56ec5080d0fdc8797bd467d7d0d486a756d948e8298d4402fc7a8e470b6010df |
| fo_hub/ocr.py (pre-change) | d20201183c36dae626ef3980fea76689930e65b3bb1f23d5b5ae0af0b5de0ccd |
| fo_hub/pdf_extract.py | e16da922bfd7be1b87f2e0f0f50482f00776f4599001260672a47fb5aad78ff0 |

## Page categories (policy v5, all rows)

174 materials, 8457 pages, matching the baseline.

| quality | exposure | pages | materials |
|---|---|---|---|
| text | text_only | 7908 | 173 |
| low_text | text_only | 4 | 1 |
| ocr_review | blocked | 523 | 144 |
| blocked | blocked | 20 | 16 |
| ocr_empty | blocked | 1 | 1 |
| ocr_pending | blocked | 1 | 1 |

545 pages are blocked (523+20+1+1), the same total as the baseline.

### Causes

- **blocked (20):** stored text is empty by design. In `pdf_page_structure.flags_json`, 14 are `residual_pii`, 5 are `reading_order_uncertain + residual_pii` and 1 is `watermark_unproven`. The extractor discards blocked text, so this DB has nothing to recover. Recovery would need the original from OneDrive, re-extraction in a private cache and a privacy fix specific to each case. That is out of scope here.
- **ocr_pending (1):** `pdf_ocr_jobs` attempts=3 with last_error `ValueError`. The material has `relative_path` NULL and 0 `material_originals` rows, so the error is the expected "private source unavailable". It can only be recovered once a verified original is rediscovered. Leave it blocked and don't invent provenance.
- **ocr_empty (1):** tesseract returned no text. It has 3 originals rows.
- **ocr_review (523):** OCR text is present but blocked by design for visual/privacy review. Content-free triage using the new `triage_ocr_review` gave:
  - lanes: visual_check_math 192, visual_check_text 188, visual_check_noisy 134, privacy_review 9
  - reasons (they overlap): short<200 363, math_or_numeric 197, low_alpha 124, contact_hint 5, identity_hint 4 (CPF-shaped)

**Conclusion:** none of the 545 can be honestly released by rule. The 9 privacy pages need redaction review. The 192 math pages need a visual comparison: OCR can garble formulas, and stripping them is forbidden. The 134 noisy pages are probably figures or diagrams. The 188 text-lane pages are the cheapest candidates for a human reviewer to approve first. This sprint makes no automatic approval.

## Code change (tested, not deployed, not committed)

- `fo_hub/ocr.py`: new pure function `triage_ocr_review(text) -> {lane, reasons, chars, words, approved: False}`. It does not change text and does not touch the DB. It treats formulas and signed numbers as content to keep, and routes identity or contact hints, including invalid CPF-shaped numbers, to privacy review.
- `tests/test_ocr_review_triage.py`: 4 tests using synthetic data only.
- Run: `PYTHONPATH=federal-online services/anki-mcp-v2/.venv/bin/python -m pytest federal-online/tests/test_ocr_review_triage.py federal-online/tests/test_ocr_incremental.py federal-online/tests/test_pdf_extract.py federal-online/tests/test_pdf_academic_preservation.py federal-online/tests/test_pdf_index.py -q` gave **43 passed**.

## Originals and retention

- `material_originals`: 508 rows. All have a SHA256 and an `onedrive:` path, covering 508 distinct hashes and 172 of the 174 materials. Two materials have indexed pages but no originals row (one of them is the ocr_pending material above).
- OneDrive `onedrive:Federal Online PDFs`: 517 objects, 3,189,769,181 bytes (`rclone size`).
- Archive receipt `state/missions/20261106-pdf-archive/receipt.json`, sha256 `0ecdd14230f9239e75f85d9002e108e9ac7b52ab86121f11eaba6d252dd82a07`:
  - covers 3 unattributed originals under `onedrive:Federal Online PDFs/_unattributed`
  - verified with `rclone check --one-way --download`
  - `c0a1551b9a25…` (7,622,464 B) and `e2c56a04fa1a…` (3,450,766 B): `unlinked=true`, from `materials-sources`
  - `003404871ac5…` (15,451,322 B): `unlinked=false`
- `failed-snapshots-cleanup.json` sha256 `c1abf20e…affe659`: 2 records. Only empty owned failed targets were removed (`original_bytes_removed` is recorded per record).
- `20261107-pdf-privacy-final/readback.json` sha256 `a6478bba…e1`: read-only check of 172 docs and 7818 pages, 0 rejected releases, `academic_quality_certified=false`.
- Failed units `study-hub-fo-mission-pdf-archive{,-v2}-20261107` are in failed state. v2 failed on a `%PDF-` header assertion. A `fo_archive_residual_pdfs_v3.py` exists in tmp, but no v3 unit is listed. The parent should check what v3's state is.

### Residual local cleanup candidate (exactly one)

`materials/.build_extensivo-ufpr-2026/Física/…Lista de Exercícios.pdf`:
- 15,451,322 B, inode 1297200, nlink 1, mtime 2026-10-28
- `%PDF-` magic
- sha256 `003404871ac5da94e45da70ba4b331d1553958e9cff829784ca6600e5e9bc9de`
- not referenced by `materials` or `material_originals`
- the remote object named after its full SHA exists under `_unattributed`, with an identical size and QuickXor (`f64fdfb8a8898b2fff9de86ba246…`, local `rclone hashsum quickxor` equals remote)

It is the only `*.pdf` under `materials/` (16 MB total). The other files there are 10 manifests plus checkpoint/courses JSON.

**Removal preconditions (for the parent):**
1. Hold the materials lock, and no materials or index job may be running.
2. Recompute sha256 immediately before removal and require it to equal the receipt value.
3. Run `rclone check --one-way --download` again for this single object (or rely on the receipt's download check plus the matching QuickXor).
4. Unlink only this file. Remove the `.build_*` dir only if it is empty afterwards, and keep the manifests if any reference it.
5. Write a receipt that updates `unlinked` without rewriting the old receipt.

## Not done / blockers

- No production reclassification and no OCR approval. Any release needs a human visual review, recommended in the order text lane, then math, with privacy pages last.
- The 20 `blocked` pages keep no text, so recovering them needs a fetch from OneDrive and re-extraction. A design is still needed.
