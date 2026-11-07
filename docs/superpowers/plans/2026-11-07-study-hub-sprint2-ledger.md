# Study Hub Sprint 2 — ledger

Spec: owner's AFK Sprint 2 request, 2026-11-07.
Base: b18823f; branch feat/study-hub-migration.

Ruling: study.gatssby.com.br exclusively supersedes the prior apex/www plan. No root/www DNS or redirect changes.
Ruling: execute in the owner-selected dirty feature worktree with exclusive path ownership and selective staging, rather than moving unrelated Anki work to a worktree.
Ruling: independent transcription, web/observer and PDF workstreams run in parallel; parent owns shared ingress, retention, integration and final review. No child may restart production services or commit.
Ruling: proportional targeted tests plus one final integrated run follow the owner's explicit testing budget rather than repeated whole-suite runs.

Baseline 2026-11-07 19:55–20:00 UTC:
- n8n container e479101ea8aafe73f6651c7616d6c7c2513ff66a5d7aa87a71606f2bac8fa603, start 2026-11-01T04:01:04.053050276Z, PID740519, restarts0, root/healthz200.
- Nginx PID1911615; Whisper PID3143673; FO API PID3138706. Active, restarts0.
- Anki404; Sales307; Verbo200 on root paths. Not service errors inferred.
- Existing vhost/cert hashes captured privately at ~/.hermes/cache/scratch/study-sprint2/before.json.
- DNS authoritative b.sec.dns.br/c.sec.dns.br and public1.1.1.1/8.8.8.8: study A137.131.191.66 TTL3600, no AAAA. VPS external IP same. No DNS writes.
- Notion hosted connector disconnected; no routine AFK interactive authorization requested.

Storage audit:
- Five SQLite historical files, each639631360 bytes. No live process references observed by lsof.
- previous-hub contains3245 material IDs/147693 pages absent from live: preserve.
- pre-bioq-rerun has178 historical focused review keys absent from live: preserve pending relevance classification.
- pre-index-cycle, pre-ocr and pre-catalog: every primary key exists in live; immutable materials/transcript/segments/revision payloads covered. PDF text differences exclusively empty historical text now nonempty (523/523/520), current structural metadata and originals identical. Final guards pending before deletion.
