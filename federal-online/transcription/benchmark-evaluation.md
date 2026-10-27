# Text-only benchmark evaluation (no ASR execution)

These commands consume supplied JSON/text only. They do not open audio, download weights, run a model, delete files, or grant execution authorization.

From repository root:

```sh
PYTHONPATH=federal-online services/anki-mcp-v2/.venv/bin/python -m fo_hub.benchmark score-batch federal-online/transcription/benchmark.synthetic.json --seed 20261021 --bootstrap-samples 2000
PYTHONPATH=federal-online services/anki-mcp-v2/.venv/bin/python -m fo_hub.benchmark check-manifest federal-online/transcription/benchmark-manifest.template.json
services/anki-mcp-v2/.venv/bin/python -m pytest federal-online/tests/test_benchmark.py -q
```

`benchmark.synthetic.json` contains **invented** text, timestamps and resources solely for testing. Its numbers are not model results. Keep `synthetic: true` in derived reports. Real scoring requires `synthetic: false` and independently collected hypotheses and measurements; the scorer itself always reports `inference_executed: false` because it performs no inference.

## Batch contract

Top level: explicit boolean `synthetic`, optional list `glossary`, nonempty `records` list. Each record requires unique `(config_id, segment_id)`, `kind` (`speech`, `nonspeech`, `full_lesson`), positive finite `duration_s`, text `hypothesis`, and text `reference`. Only full lessons may omit reference (no full gold required); this never makes them silence. Speech gold must be nonempty. Nonspeech gold must explicitly be empty. Missing gold is an error, not a zero error rate. Empty hypotheses are valid measured failures to transcribe.

Optional measurements: `wall_s`, `peak_rss_mb`, disk sizes and `failure` (preserved from input). Null/missing resources stay unavailable; no resource values are inferred. RSS uses MiB consistently with collection, and RTF is wall seconds / audio seconds. Preserve hardware, runtime commit, weight/binary hashes, exact command and effective settings in the run manifest.

`anchors` contains manually matched phrases with unique `id` and `reference_start_s`, `reference_end_s`, `hypothesis_start_s`, `hypothesis_end_s`. All times are finite, ordered and inside the segment. Start/end errors are pooled for linear-interpolated median and p90. Signed drift is final end-offset minus first start-offset (not absolute end error); at least two anchors are required. Anchor matching is manual, never guessed from text similarity.

## Metric definitions and limits

- Normalization v2: NFC + casefold; words, signed decimal numbers and scientific operators (`= < > ± × ÷ % + −`) are preserved. Other punctuation is removed, accents remain and numbers are not spelled out. Thus `-5` versus `5`, and `<` versus `>`, remain errors. CER includes inter-word spaces. WER/CER use exact Levenshtein distance; empty-gold WER/CER are null, not zero. Do not mix old normalization-v1 scores into v2 comparisons.
- Aggregation sums edit counts and reference denominators, not a mean of segment rates. WER/CER percentile IC95 resamples speech segments with replacement using a fixed seed; one segment gives a degenerate interval, not evidence of certainty. Correlated segments from the same lesson limit this segment-level interval.
- Glossary extraction is longest-first, nonoverlapping exact normalized phrase matching. Occurrence recall sums `min(gold_count, hypothesis_count)` per term / gold occurrences (not unique-term recall). Term errors/term WER are edit distance on the ordered extracted glossary-term sequence; this is a **restricted glossary-sequence metric**, not acoustically aligned term correctness. Multiword terms count as one occurrence. No glossary occurrences => recall/term WER null.
- Nonspeech characters/minute counts normalized text including spaces / duration in minutes. It is not raw-character scoring. Nonspeech annotation must be human verified.
- Repetition counts maximal contiguous runs of the same four-word block repeated at least three times. Rotations inside a run are not counted separately; not a semantic hallucination detector.
- Long insertions count contiguous insertion runs of at least five words in one deterministic minimum-edit alignment (tie preference diagonal, deletion, insertion). Alignment ambiguity can affect this count. Exact traceback uses quadratic memory; use five-minute gold segments, not a full lesson transcript. Full lessons without gold skip edit scoring and retain repetition, timestamps and resources.
- Comparisons are grouped by `config_id`; `comparison_ready` requires identical segment coverage across multiple configurations. Identical IDs must have identical gold, duration and kind. Review metric tables and ICs manually; the scorer never promotes a model. Missing measurements remain null. CI overlap alone does not establish statistical equivalence.

## Corpus and run readiness

`check-manifest` is a metadata checklist, not validation of file existence, acoustic content or authorization. It requires >=6 lessons, >=2 manually identified teachers, >=2 subjects, three manually selected >=5-minute gold strata per lesson (opening, middle_science, noise_interaction), >=90 minutes verified gold, >=2 verified >=3-minute nonspeech segments, and a full lesson. SHA-256 syntax is checked; actual audio hashes must be independently computed when authorized. Automatic plan windows **cannot establish teacher identity or noisy/nonspeech content**.

Before any real benchmark: manually confirm all annotations, mark one phrase every 30 seconds, second-annotator review >=20% with inter-annotator WER <=3%, record conversion to 16kHz mono once and input hashes, freeze glossary/normalization, and obtain explicit authorization. Record runtime/weight provenance and safe RAM/disk limits. Missing manual annotations block readiness.

`benchmark-matrix.json` makes FP16 large-v3 via whisper.cpp, Portuguese, three threads, beam 5 and temperature 0 the primary planned candidate. Compare **no temperature fallback** versus the verified runtime schedule 0/0.2/0.4/0.6/0.8/1, and beam 10 separately. VAD remains **off until separately verified**. Runtime commit, binary/model hashes, flags and thresholds were inspected on the VPS on 2026-10-27 without loading audio; effective temperature increment is zero with `-nf`. Neither the matrix nor readiness check runs inference. Compare quality first, resources second; no RTF elimination threshold. OOM/unsafe RAM/disk rejects a run; nonspeech hallucination >2x baseline requires human acoustic review, not heuristic text removal.

`benchmark-selection-2026-10-27.json` records six currently eligible lessons from live SQLite metadata, in Biology, Physics, Chemistry, Mathematics, History and Literature. The proposed 18 five-minute windows are not verified acoustic strata. Teacher identities, glossary, actual noise/music/silence windows, 30-second short probes, boundary probes, audio hashes, gold and anchor labels remain absent. Run at least one selected lesson in full (the selected biology lesson is 2,817 seconds); longer 1–3 h stability material may be added without claiming that such a run has occurred.

The batch JSON report is distinct from the legacy per-run `benchmark.schema.json`: it is a scored text evaluation artifact, not a claim that an authorized model run occurred.
