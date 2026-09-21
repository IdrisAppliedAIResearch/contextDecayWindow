# AMENDMENT 001 — AF-PRE-001: disposition surface moves to the LoCoMo pool; gold rule set

**Date:** 2026-09-20. **Trigger and evidence:** Part 1 executed before any lock, as §6 requires. Findings that change the design:

1. **E-paraphrase surface void** (`part1d_paraphrase.json`): the generator's item name is a substring of its meeting name (`"Harbor-123"` in `"Harbor-123 review"`), so every gold anchor remains reachable by tokenized lexical matching even after name-stripping; strict quoted-span LEX has no span to hold. Registered void check §6(d) fired. §4's bars, written on that surface, cannot bind; a plan amendment, not a silent reinterpretation, moves them.
2. **Fixture gate results** (`fixture_gate_both.json`, committed before this amendment): LEX/BM25 reproduced their registrations exactly. CE scored 2/5 (passes F4/F5; fails F1, F2, F3) and QWEN-BI 3/5 (fails F2, F3). Margins show a working ms-marco ranker (F4/F5 ceilings +5.6/+12.6) with honest failure modes on question-echo (F2: +5.7 for the echo) and meta-commentary (F3: +6.6 for filler). The instrument floors (>=2/5) passed; the CE per-fixture *expectations* for F1/F3 were authoring guesses and are recorded as DEVIATION: the fixture file is not edited, this record carries the evidence, and no floor was changed.
3. **LoCoMo gold is deterministic** (`part1e_locomo_pool.json`): 1,527 category 1-4 questions carry evidence dia_ids resolving to dialogue turns; anchor gold = earliest-evidence turn, latest reported secondarily; 34/120 sampled items have earliest != latest and enter a user audit before interpretation (user ruling, 2026-09-20). Two-pass human gold is replaced by evidence-derived gold plus that targeted audit.

## Registered dispositions (supersede §4's bars; fixed now, before any sample scoring)

Surface: **LoCoMo sample-120** (`part1e_locomo_pool.json`, seed 20260920), gold = earliest-evidence turn, anchor accuracy = arm's top-1 exchange equals gold (deterministic tie-break: earliest turn). All numbers are characterization (partition ruling); E is retained for the fidelity replay only.

- **`WORKS`** — `CE` beats **every** baseline arm (`max(LEX, BM25, QWEN-BI)`) in net discordant top-1 pairs by >= +10 of 120 **and** paired exact McNemar p < .05 versus the best baseline. Binding successor unchanged (paired native-reader pilot, net >= +5, ~40 items x 2 contexts) and the word "adequate" remains out of bounds until it passes.
- **`SIGNAL`** — `CE` beats every baseline in net discordant pairs (any margin) with all pairwise directions non-negative, and the audit on the 34 ambiguous items does not overturn the direction under the latest-evidence variant.
- **`NO_SIGNAL`** — otherwise. Reading: zero-training discriminative localization not demonstrated over the deployed bi-encoder and lexical floor — an instrument statement (§9.2); the fixtures already name the mechanism failure class (discourse duplex, meta-commentary, temporal shift) any successor must attack.
- **E fidelity line (reported, not binding):** on the 17-anchor E gap, LEX/BM25/QWEN-BI/CE anchor recovery, with the pre-stated expectation that LEX and BM25 take 17/17 (surface proven lexically held) — a scoring bug shows up here as a baseline missing these.

Arms, models, pins, serial loading, and the no-reader-LLM constraint are unchanged from v2. Gold-adjacent audit items are excluded from no condition; ambiguous items stay in-scoring with both variants reported.
