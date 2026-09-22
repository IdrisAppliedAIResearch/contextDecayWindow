# AMENDMENT 001 to AF-READ_002_PLAN — ring unit = deployed adapter element

Status: registered with implementation; plan body left untouched (locked-file rule).

## Trigger and evidence (PF1 Part 1, run before implementation)

`experiments/locomo_relevance_timeline/artifacts/` revealed the deployed content
unit is the **adapter pair record** (`<record session=... date=...
dialogue_ids=...>` over two speaker-prefixed turns), not a raw turn: 3,011
elements across the 10 primary conversations; per-question per-element frozen
cosines in `selections.jsonl.gz`; cached Qwen3-Embedding vectors
(sha 06507c…) cover all 3,011 pair texts and all 120 H120 questions — **zero
embedding calls required**; every V2 anchor turn is contained in exactly one
element (120/120 verified). The plan's turn-level rings with a re-rendered
envelope would introduce a rendering difference from the deployed arm for no
benefit.

## Change (unit and mechanics only; budgets, bars, protocol unchanged)

1. **Ring unit:** adapter element. The seed turn maps to its containing element
   (deterministic, verified 120/120). Growth is a contiguous chronological
   window: ends tried alternately (after, before); a side stops growing when the
   next whole element would exceed the cap; whole elements only.
2. **Envelope:** concatenation of the adapter `element` strings in source order
   — byte-identical to deployed rendering content. This supersedes the plan's
   re-rendered session-contiguous grouping for this study.
3. **CC80 (arm C):** `episodic._retrieval.retrieve_long_term`,
   `EpisodicConfig(read_policy='legacy_cc80')` — frozen dense 0.8 / BM25 k1=1.2
   b=0.75, aspect off; episodes = adapter elements with cached vectors,
   `searchable_text` = pair text, `turn_number` = source index; excluded_ids =
   anchor-block ids; budget 8,000 charged by the packer's own exact_serialized
   metric.
4. **Arm C cap enforcement:** anchor block ≤ 8,000 (own metric) and final merged
   chronological block ≤ 16,000, enforced by dropping lowest-ranked CC80 ids
   (never anchor ids); drops recorded per item.

## Not changed

Reader BASE/server/calibration; judge passes and seeds; PF-J reuse validation;
item set; both disposition tiers; commit ordering.
