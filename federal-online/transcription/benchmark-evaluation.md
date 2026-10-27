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

`anchors` must be a list of objects with unique nonempty string `id` and `reference_start_s`, `reference_end_s`, `hypothesis_start_s`, `hypothesis_end_s`. All times are finite, ordered and inside the segment. Start/end errors are pooled for linear-interpolated median and p90. Signed drift is final end-offset minus first start-offset (not absolute end error); at least two anchors are required. Anchor matching is manual, never guessed from text similarity.

## Metric definitions and limits

- Normalization v2: NFC + casefold; words, signed decimal numbers and scientific operators (`= < > ± × ÷ % + −`) are preserved. Other punctuation is removed, accents remain and numbers are not spelled out. Thus `-5` versus `5`, and `<` versus `>`, remain errors. CER includes inter-word spaces. WER/CER use exact Levenshtein distance; empty-gold WER/CER are null, not zero. Do not mix old normalization-v1 scores into v2 comparisons.
- WER/CER and glossary aggregates use **speech only**, never full-lesson stability rows, even when those have references; valid individual row metrics remain available. Aggregation sums edit counts and reference denominators, not a mean of segment rates. WER/CER percentile IC95 resamples speech segments with replacement using a fixed seed; one segment gives a degenerate interval, not evidence of certainty. Correlated segments from the same lesson limit this segment-level interval.
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

## Authorized collection procedure (not executed in this mission)

There is no automatic corpus runner. After explicit authorization covering the benchmark, and only on the VPS:

1. Complete/review the manifest, freeze the selected source revisions and glossary, and create a private run directory below FO state. Use one source video at a time. Record its actual SHA-256; do not use a signed URL as a log identifier. Preserve existing files; use unique output names.
2. Convert each manually accepted window once, e.g. `ffmpeg -nostdin -threads 1 -ss START_SECONDS -i SOURCE_MP4 -t DURATION_SECONDS -ar 16000 -ac 1 -c:a pcm_s16le -threads 1 INPUT_WAV`. Substitute the annotated bounds, require a new output path, and record the actual command and WAV SHA-256. All configs consume those same bytes. A proposed metadata window is not an accepted noise/silence label.
3. Load the authorized FO environment, then require `gate(Config.from_env())['allowed']` and preflight readiness before launching each runtime call. Run inside a CPU 300%/12 GiB/128-task cgroup (same `systemd-run` pattern as the activation runbook), not an uncapped shell. A false gate is an abort, never a reason to edit it automatically.
4. Baseline decoder args are `-m /home/ubuntu/study-hub-models/ggml-large-v3.bin -f INPUT_WAV -l pt -t 3 -bs 5 -bo 5 -mc -1 -tp 0 -tpi 0 -nf -nth 0.6 -et 2.4 -lpt -1 -ng -ojf -of UNIQUE_PREFIX`. For fallback comparison remove `-nf` and use `-tpi 0.2`; for the separate beam comparison keep no-fallback and change only `-bs 10`. Do not enable VAD merely by flags. Record failures, including empty hypotheses; never invent output after an error.
5. Wrap each call with `/usr/bin/time -v -o UNIQUE_RESOURCE_LOG`; capture wall time, convert maximum RSS KiB to MiB, and separately record cgroup MemoryPeak and filesystem free/minimum bytes before/after. The scorer does not sample these. For full-lesson stability use the worker's chunking/stitching rather than an unbounded decoder invocation, with an isolated benchmark-only metadata DB/state, never the production queue/state; keep stability rows outside speech aggregates. Do not publish comparison runs to production `generated_v2` or OneDrive.
6. Preserve raw decoder JSON and exact configuration/model/runtime/library hashes privately. Supply verbatim hypotheses, measured resources and manually aligned anchors in the batch contract above, then run `score-batch`. Keep `synthetic=false` only for independently measured real runs. Retain failures and annotation provenance. Do not infer teacher identity, fill gold gaps, or normalize away scientific signs to improve scores.

The installed Silero v6.2.0 hash/load/zero-PCM probe passed (see `benchmark-matrix.json` and `vad_synthetic_probe.py`). Retention of actual speech, music/noise behavior and ASR original-time mapping remain unmeasured; production VAD stays off.
