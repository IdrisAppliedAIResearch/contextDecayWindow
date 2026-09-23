# AF-PRE-006 (registered before build, 2026-09-20): anchor-hiding supervision — can teaching "what turn was removed?" make anchoring easier?

**User hypothesis:** training should show the model conversations with the anchor *hidden* and
make it identify the hidden turn; a model that has learned anchor-ness from conversational
context should anchor more easily than one trained only on question→candidate selection
(AF-PRE-005's contract, current best: 56/120 sample2, 17/17 E).

**Registered interpretation (frozen before code runs):** auxiliary task **AH** —
for each training item with gold anchor at turn g: context = the K=10 turns preceding g
(concatenated, the anchor itself absent); candidates = gold turn + 8 turns sampled from the
rest of the conversation (rng seed 20260920); target = pick the gold among candidates from
context alone — **no question is shown**. This is self-supervised-by-construction event
boundary learning: which turn follows as the event?

- **Mixing:** train one model on AF-PRE-005 rows (772 answer + 429 E) + AH rows (772) —
  same frozen config as 005 (AdamW 2e-5, wd .01, warmup 10%, 3 epochs, batch 16, max_len 256,
  final checkpoint).
- **Comparisons (all per-item paired where bars apply):**
  - `M-ungated` / `M-gated`: AF-PRE-006 model reranking sample2, vs `ckpt2-ungated`
    (the 005 model) recomputed per-item in the same run (005 stored only aggregates).
  - `AH-salience` (descriptive): for sample2 items, M picks the anchor from its own context
    (no question) among 8 sampled distractors — measures whether anchor-ness alone is
    learnable and how far above the 1/9 chance floor.
  - E gaps: M rerank, bar unchanged (must stay 17/17 — dropping below while claiming an
    answer-side gain would be the exact trade this program kills arms for).

## Bars (binding)
- **PASS-AH:** M-ungated net vs ckpt2-ungated on sample2 ≥ +5 with McNemar p < .05 **and** E 17/17.
- **SIGNAL-AH:** net > 0, E 17/17.
- **DEAD-AH:** net ≤ 0 — hidden-anchor supervision adds nothing to the question-trained model;
  reported with AH-salience numbers so we learn whether the task was learnable at all
  (high salience + no transfer = representation exists but doesn't serve ranking; chance =
  the task itself is unlearnable at 120 items/K=10).

## Contamination
sample2 and E gaps are eval-only, as in 005 (asserted). The user's literal "train on our
sample conversations" is honored at the only honest level — same 10 conversations, different
items — because training on the eval items would answer nothing.

No LLM readers; BERT-class serial GPU; seeds 20260920; final checkpoint only.
