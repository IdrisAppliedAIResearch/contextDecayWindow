# AF-PRE-001 Part 1b — instrument identity fixtures, expected outcomes committed BEFORE instrument code

**Date:** 2026-09-20. Registered per plan §6(b) after Part 1a/1d/1e. Because Part 1d voided the E surface (the item name is a substring of the meeting name, so lexical arms trivially hold every E anchor), the identity fixtures are natural LoCoMo pairs where the lexical floor demonstrably fails. Gold anchors are the Part 1e evidence-derived turns (earliest-evidence rule, registered below). BM25 scores below were computed with the reference implementation in `fixture_bm25_check.py` and committed sight-unmodifed by any model arm.

**Registered gold rule (Part 1e):** anchor = the turn whose dia_id equals the earliest evidence id of the question (session-major, turn-minor order); latest-evidence anchor reported secondarily; category 5 and evidence-less items excluded; pool = seed 20260920, n=120 across all 10 conversations (characterization per user partition ruling).

## Fixtures (planted positive = gold turn; hard negative = named-entity/duplex competitor)

| id | question | gold (planted positive) | hard negative | BM25 (gold/neg) | registered BM25 outcome |
|---|---|---|---|---|---|
| F1 | When did Caroline attend a pride parade in August? | conv-26 D11:4 (attended "last Friday") | D10:7 ("I missed it") | 15.55 / 18.80 | **must fail** (neg ranks above gold) |
| F2 | What was one of Jolnie's favorite games … nintendo wii? | conv-48 D24:10 (Monster Hunter: World) | D24:9 (the question-echo asking it) | 13.82 / 39.73 | **must fail** |
| F3 | What special memories does Audrey have with her childhood dog, Max? | conv-44 D13:10 (walks, sharing worries) | D13:8 ("lots of great memories" filler) | 18.77 / 35.81 | **must fail** |
| F4 | What fuels Calvin's soul? | conv-50 D7:11 (performing live) | D1:2 (car event) | 19.24 / 3.54 | must pass |
| F5 | What inspired Joanna to take a picture of the sunset near Fort Wayne? | conv-42 D28:22 | D22:9 (film, sisterhood) | 47.73 / 18.11 | must pass |

F2 typo note: "Jolnie" above preserves the pool's exact question text ("Jolene"); the authoritative string is `part1e_locomo_pool.json`.

## Registered expectations, fixed before any model runs

- `LEX` (strict quoted-span): expected **no hits on all five** — natural questions carry no quoted spans. Fails informatively; retained only to document the floor.
- `BM25`: reproduces the committed scores above exactly; must fail F1-F3 and pass F4-F5. Any deviation is an instrument failure of BM25, not a finding.
- `CE` (pinned `cross-encoder/ms-marco-MiniLM-L-6-v2` @ `233902d25c440f23af6f7d6e94d2946bac0bee0a`, single-window, `torch>=2.11+cu128`): registered expectation **passes F1, F3, F4, F5; expected to fail F2** (question-echo negatives are the known cross-encoder failure mode; requiring it would hide the instrument's real limit). **Hard instrument floor:** any arm (CE or QWEN-BI) scoring < 2/5 on the five pairs is broken — no scoring run proceeds; an arm passing 2/5 but with a broken-looking pattern is recorded, not silenced.
- `QWEN-BI` (carried Qwen3-Embedding-0.6B GGUF via `src/embeddings/provider.py`, CPU): same hard floor of 2/5; no per-fixture expectation asserted (it is the incumbent, measured, not presumed).
- Any arm that **passes all five including F2** is recorded as suspecting an implementation shortcut and is manually inspected before results.

Committed before: `arms.py`, any CE scoring, any QWEN-BI scoring. Model pins in `model_pins.json`.
