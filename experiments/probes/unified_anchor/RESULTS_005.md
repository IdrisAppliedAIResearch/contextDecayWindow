# AF-PRE-005 RESULTS — pipeline-matched fine-tune: **PASS** (verdict registered before retrain, plan `9018e653`)

Fresh sample2 (seed 20260921, drawn and frozen before training data existed; never in any
training set), E gaps held out, single factor changed vs AF-PRE-003: **the task contract**
(model trained to select gold *within the pool*, items whose gold is outside the pool skipped
— 772 kept / 519 skipped; skip flag raised and recorded per plan, consistent with the
61% gold-in-pool ceiling measured in AF-PRE-004).

## Numbers

| arm | E-17 anchors | sample2 (fresh) | sample-120 (secondary) |
|---|---|---|---|
| BM25 | 0 | 30 | 29 |
| gated zero-shot CE | 0 | 36 | — |
| gated newFT | **17/17** | **54** (net +24, p=3e-6) | **56** |
| ungated newFT (full pool) | **17/17** | **56** (net +26, p=6e-6) | not run |

Bars: PASS required E ≥ 15 and net ≥ +10, p < .05 on the fresh sample → **PASS, by a wide margin.**

## The pre-stated nerve clause fired
The plan anticipated: *"if ungated-newFT now also does well, the 8/120 collapse was a
data-mixture artifact, not interference."* It did — 56/120. **AF-PRE-003's registered verdict
INTERFERENCE stands as recorded, but its mechanism reading is corrected by this probe:**
the collapse was not capacity sharing between skills. It was the full-pool training contract:
forcing the model to find gold anywhere in a conversation taught a global "answer tokens are
untrustworthy" prior. Training on pool-matched candidates — where for answer questions the
gold is among the candidates and event turns appear *as negatives*, and for event questions
record lines appear as negatives — teaches the conditional discrimination directly. One
model, one score, both skills, no global suppression.

## What the architecture now is (and isn't)
- **The user's position, validated:** one fine-tuned BERT-class cross-encoder holds both
  skills — 17/17 where the regex held and nearly 2× BM25 on natural questions, on data it
  never saw, with McNemar p ≈ 1e-6.
- **The gate became unnecessary:** ungated ≥ gated (56 vs 54; the gate now *loses* two items
  it could otherwise rerank). AF-PRE-004's dramatic rescue of the broken checkpoint is
  re-read as: the gate patched a broken contract that better training simply doesn't create.
  The regex keeps its role for free anyway (17/17, zero cost, auditable) but nothing above
  requires it.
- **Standing limits:** LoCoMo is characterization only (partition ruling) — this is the
  strongest characterization result in the arc, not a confirmation claim; gold is
  evidence-derived (the 34-item earliest/latest audit is still open); the product read path
  has not been changed or reader-scored with this model; "adequate" is still out of bounds.
  E is synthetic-templated: 17/17 proves the mapping is learnable, not event-generalization
  to unconstrained text.

## What this changes for the program
The anchor problem now has a candidate mechanism where every previous arm was 0 or luck:
**a trained (not zero-shot) reranker with pool-matched supervision**, ~120MB, minutes to
train, zero LLM calls. The open next steps are (a) honest generalization probes: train on a
conversation subset, test on held-out conversations; (b) product-boundary work: where such a
reranker would sit relative to the timeline selector and its availability semantics —
engineering and a study design, not a probe amendment.

Artifacts: `artifacts/sample2.json` (frozen first, SHA below), `pairs2.json`, `ckpt2/`, `results.json`.
