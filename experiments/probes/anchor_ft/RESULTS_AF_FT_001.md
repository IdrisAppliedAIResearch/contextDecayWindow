# AF-FT-001 RESULTS — retrain the anchor cross-encoder: **DEAD on the registered anchor bar; the data fix reverses the model; abstention works** (plan `f9e75e9c`)

20 trainings (4 configs × 5 seeds), 20/20 evaluated, zero LLM calls.
Headline metric per the registration: sample2 (120, frozen) ungated **any-gold** top-1, paired vs
same-seed R0 (champion reproduction).

## Numbers

| config | exact | any (ungated) | gated any | E-17 | any-net vs R0 (5 seeds) |
|---|---|---|---|---|---|
| **R0** champion repro | **56.80 ±1.30** | **67.00 ±1.00** | 62.00 | 17×5 | — |
| V1 gold-in-pool + multi-positive | 33.20 ±1.48 | 36.40 ±2.19 | 59.00 | 17×5 | **[−33,−31,−29,−31,−29], p≈0 all** |
| V1H control (−120 held-out) | 32.00 ±1.87 | 34.40 ±2.70 | 60.00 | 17×5 | [−32,−34,−36,−28,−33], p≈0 all |
| V2 V1H + null head + null rows | 59.40 ±0.89 | 66.00 ±0.71 | **63.60** | 17×5 | [0,−1,−2,−2,0] |

V2 exact-net vs R0: [+4,+3,0,+2,+4], p 0.29–1.0 — direction positive, **not significant**; registered
comparability criterion (no worse than R0−2) met.

## Dispositions (as registered; no reinterpretation after seeing numbers)

- **PF2 instrument check passed emphatically:** R0 seed 20261011 reproduced the champion's recorded
  56 exact / gated 54 / E 17/17 item-identically close (seeds 56/57/58/58/56 across 5 seeds).
- **Seed variance, the arc's never-measured quantity, is small: ±1.3 exact, ±1.0 any-gold at n=120.**
  The program can now detect ≥4-item effects with 5-seed means. "53 beats 48" was always noise;
  "−31" is not.
- **WORKS (≥+8 any) and SIGNAL (≥+4 any): not met by any config → DEAD** for the anchor-accuracy
  objective this round. The data-fix story ("pool-insert 519 discarded golds, credit all golds")
  is not merely unproven — **it reverses the model.**
- **Abstention head (descriptive, no bar): works.** Held-out P(null) AUROC **0.936** (calib 0.889),
  coverage–risk: answer-coverage 93% of anchored questions at 22% null-leak; 65% at 5% leak; head
  non-degenerate (never/always-null both false). **The user's native-confidence requirement is now
  implementable at no anchor-side cost** (V2 ungated ≈ R0 within noise, gated +1.6).
- Cat-5 descriptive: mean P(null) 0.11 — adversarial questions do **not** read as null. Consistent
  with the PF-1 finding that cat-5 items carry evidence pointers to related-topic turns. "Not
  mentioned in conversation" is a statement about the *answer*, not the topic; the anchor head is
  correct not to fire.

## The mechanism finding: V1's collapse is a landscape failure, not a ranking failure

V1 loses only ~3 items **inside the frozen BM25 pool** (gated −3) and ~31 **across the whole
conversation** (ungated −31). The model trained on gold-inserted rows still ranks pool candidates
correctly; what broke is the *score landscape over non-pool turns*: adding 519 items whose golds
BM25 never saw teaches that high anchor score can live on lexically unrelated turns, and on the
650-turn ungated set the top-1 lands on arbitrary non-pool turns everywhere. This is the same nerve
AF-PRE-005 struck — **the training contract, not the data quantity, governs ungated behavior** —
in mirrored form: 005 found pool-matched positives *create* a working landscape; 001 finds
hard-gold insertion *destroys* it.

V2 — the same collapsed data plus 800 cross-conversation null rows (with reject margin and smoothing
as one bundled config) — **restores the landscape** (any −1, exact +2.6) *and* calibrates. The
registered design cannot decompose null-rows vs margin vs smoothing (stated in PF8); the next probe
should. What null rows plausibly restore: a trained representation of "nothing here fits," which is
exactly the information ungated scoring needs to suppress junk.

## What is closed, what is not (§9.1)

Closed by this study: (a) gold-in-pool insertion under pool-softmax as a *drop-in* data fix, on
LoCoMo, ungated scoring; (b) multi-positive uniform-mass targets as a standalone lever (inseparable
from the insertion, so closed jointly); (c) "more negative-free rows help because they're more data."
Not closed: (i) the 519 items themselves — a **filtered or curriculum** reintroduction is untested
(teacher-score filtering: keep only hard rows where the gold's zero-shot score beats its pool
negatives); (ii) null-row vs margin vs smoothing decomposition; (iii) any *reader-value* claim about
abstention — availability only, the reader arm is the next, call-spending study; (iv) LoRA/LR/epoch
optimization (deliberately untouched this round — R0's small SD says the measured axis can carry
such a probe).

## Follow-ups, in order

1. **V1 landscape forensics** (zero-GPU + one checkpoint): where V1's ungated top-1 falls (pool
   rank distribution, lexical-overlap profile) to test the poisoned-landscape account against the
   alternatives.
2. **Filtered hard-row reintroduction**: champion rows + teacher-score-filtered subset of the 519,
   5 seeds, same bars.
3. **V2 bundle decomposition** (null-rows only / +margin / +smoothing), 3 seeds.
4. **Reader arm for abstention value** — needs explicit call budget; threshold policy read off the
   coverage–risk curve above.

Artifacts: `af_ft001.py`, `artifacts/build2.json`, `artifacts/results.json` (per-item raw for all
20 models), `artifacts/grid_train.log`, `artifacts/eval.log`. Checkpoints (`ckpt_*`, 20×90MB) are
reproducible from `(config, seed)` and intentionally not committed.
