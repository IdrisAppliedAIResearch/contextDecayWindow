# BERT-SWAP Stage 0b — Option 2 (shadow-as-retrain on replay buffer)

**Type:** exploratory probe, continuation of `STAGE0_SPEC.md` (which closed
Option 1: G1 DEAD, G3 NO_SIGNAL). Offline, CPU, seed 5005. No reader calls.

## Difference from Option 1

The shadow does NOT warm-continue. Every swap cycle it is re-initialized from
the base checkpoint and trained on the replay buffer = raw user texts of turns
1..u (u = swap turn; strictly past-only, no future leakage), 2 epochs, lr 2e-5,
fresh optimizer state per retrain. Swap cadence: every 10 turns
(10, 20, …, 120) plus a final swap at 121. Between swaps the serving model is
frozen and identity-cosine is exactly 1 by construction.

This tests the consolidation end of the hypothesis: with an honest
replay budget (10–20 steps per planted fact instead of 1–2), does the model
bind conversation facts (Q1) and/or does its cosine beat the frozen encoder
(Q3)? The retrain wall-clock per swap is a headline cost measurement: Option 2
abandons "train every turn is cheap" and buys consolidation instead.

## Unchanged from Stage 0

Stream (Study 005 script, SHA `D8BA73FD…0752F01`), models (bert-small ~28.9M,
bert-base ~110M), cloze probes/controls, pseudo-likelihood scorer, mean-pooled
embeddings, Q3 items (checkpoints {10,61,65,102,121} × 7 queries, materialized
when any gold ≤ checkpoint), leakage boundary (mechanism never reads the key;
scoring consumes `probes.json`), determinism (seed 5005, threads 16,
deterministic masking/order; smoke double-run byte-identical).
Frozen controls = Stage 0 `small_notrain` / `base_notrain` artifacts (harness
measurement path unchanged since; recorded reuse).

## Registered dispositions (same bars, retrain-aware offsets)

- "post" for a fact = first swap turn ≥ its source; +10/+50 = readings at
  turn coordinates as in Stage 0.
- **G1b** WORKS: mean post-plant accuracy ≥ 0.50 AND pre ≤ 0.30 AND net ≥ +2
  vs frozen; SIGNAL: >0.25 with margin Δ ≥ +0.10; else DEAD.
- **G3b** paired hit@3 vs frozen: WORKS ≥ +3 with no checkpoint ≤ −2;
  SIGNAL ≥ +1; else NO_SIGNAL.
- **Q2b:** identity cosine previous-gen → new-gen at each swap; slice-MLM loss;
  novel **plant-margin gate log** (mean margin over planted-so-far probes per
  swap vs previous gen — the gate Q2 found missing; logged, not fed back).
  Retrain wall-seconds per swap reported (the cost curve of Option 2).
- Kill logic: G1b DEAD + G3b NO_SIGNAL ⇒ both consolidation extremes
  (stream and replay-retrain) closed for MLM-objective parametric retrieval;
  arc closes definitively. Any partial pass reopens the adapted-scorer line
  with an objective-design successor.

## Artifacts

`runs/opt2_{small,base}.{metrics,q3,timing,meta}`, logs;
`analyze_stage0b.py`; results appended to `REPORT.md` as a Stage 0b section.
