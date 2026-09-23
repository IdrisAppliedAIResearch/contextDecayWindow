# AF-PRE-005 (registered before any retrain, 2026-09-20): pipeline-matched fine-tune + event gate, tested on a fresh held-out sample

## What the three prior probes established (the "behavioral understanding" this design spends)
1. **AF-PRE-002:** score-mixing event-ness into BM25 kills answers (29→17); anchors are event-
   enriched (+24 pp coverage).
2. **AF-PRE-003:** one model trained on full pools with mixed supervision learns to distrust
   answer-overlap *everywhere* (8/120) while nailing events (17/17).
3. **AF-PRE-004:** gating the candidate pool converts that same checkpoint from catastrophic
   (8) to best-in-program (44, net +15, p=.017), E stays 17/17 — but that was the descriptive
   arm; the registered arm (zero-shot reranker) died (E 0/17). Pool ceiling 73/120; **the
   reranker is not the binding constraint, the pool contract is.**

**Behavioral hypothesis for the retrain (registered now):** AF-PRE-003's collapse was a
*train/test contract mismatch* — the model was trained to select over the full conversation
(with event supervision forcing global answer-overlap suppression) but should be trained on
the task it will actually run: **select within the gated pool.** Distribution-matched
training should keep both skills without a global distrust prior. This is testable and
falsifiable by the bars below.

## Part 0 — fresh eval sample, frozen before any training data exists
`sample2.json`: n=120, seed **20260921**, drawn from the eligible category 1-4 pool
(the 1,527 of Part 1e) **excluding all sample-120 qids**, stratified proportionally by
category across all 10 conversations. Gold = earliest-evidence turn (unchanged rule).
This sample is never in any training set of this probe. sample-120 stays clean too (also
excluded) for a secondary consistency read.

## Part 1 — pipeline-matched training data
For every training query, the pool is built with the **frozen AF-PRE-004 pool rule**
(BM25 top-20 ∪ event-branch ≤30, frozen lexicon, frozen entity rule):
- **LoCoMo items:** all eligible except sample-120 and sample2 qids (≈1,287).
  Positive = gold turn — **only if in pool**; if not in pool the item is skipped and the
  skip is counted and reported (skip > 30% ⇒ instrument flag, no silent continuation).
  Negatives = remainder of pool, BM25-descending order capped at 6 — so the model sees, as
  negatives, exactly the event distractors and near-miss answers it must reject in production.
- **E event items:** the 143 training curves (17 gaps excluded), positive = template anchor;
  same pool rule; skip-and-count if anchor not in pool. Oversampled ×3.
- No other supervision. Loss, optimizer, schedule identical to AF-PRE-003 (pairwise CE over
  pool columns, AdamW 2e-5, wd 0.01, warmup 10%, 3 epochs, batch 16 queries, max_len 256,
  fp32, final checkpoint, seed 20260920). **The only changed factor vs AF-PRE-003 is the
  pool-matched task contract; everything else is frozen so the comparison is attributable.**

## Part 2 — evaluation arms and bars (binding)
Surfaces: E-17 gaps; sample2-120 (primary). Secondary consistency: sample-120 (reported, no bar).

| arm | role |
|---|---|
| BM25 (sample2) | reference |
| **gated-newFT** | the system under test |
| ungated-newFT (full pool) | contribution-of-gating control |
| gated-zero-shot-CE | prior registered-arm failure control |

- **PASS:** E ≥ 15/17 **and** gated-newFT net vs BM25 on sample2 ≥ +10 with McNemar p < .05.
- **SIGNAL:** E ≥ 15 and net > 0.
- **DEAD:** otherwise; report which half died (event regression vs rerank regression vs gate ceiling).

## Pre-stated failure-of-nerve clauses
- If gated-newFT ≈ BM25, distribution-matched training did not recover the reranking gain;
  AF-PRE-004's 44 was checkpoint luck on that sample, and this probe says so.
- If ungated-newFT now *also* does well, the 8/120 collapse was a data-mixture artifact, not
  interference; reported as such, no reinterpretation of AF-PRE-003's registered verdict.
- The gate is frozen; pool ceiling (~61% gold-in-pool measured) caps everything and improving
  it is a separate probe. A PASS here is a PASS **conditional on gate recall**, said in the report.
- No bar movement, no checkpoint selection, final model only, sample2 frozen at Part 0 SHA.

No LLM readers; serial GPU (BERT-class only); seeds 20260920; contamination asserts in build.
