# AF-FT-002 / AF-FT-003 RESULTS — forensics confirm the poisoned landscape; the filter finds nothing to add; the V2 repair does not decompose (plan `3f841945`)

Zero LLM calls. 19 trainings, 12 eval models, plus two zero-cost diagnostics.

## AF-FT-002 Part A — V1's collapse is exactly the predicted landscape failure

sample2, seed 20261011, ungated top-1 (R0 = champion repro, V1 = collapsed data fix):

| | pred BM25 rank (med) | pred in train-pool % | pred-question Jaccard (med) | gold's rank (med) |
|---|---|---|---|---|
| R0 | **6** | 64.2 | 0.071 | **0** |
| V1 | **329** | 25.0 | **0.000** | 15 |

V1 doesn't rank badly — it ranks *junk*: its top-1 sits at BM25 rank 329 of ~650 with zero lexical
overlap. On V1's 87 misses: 4.6% in-pool, BM25 rank 423, Jaccard 0.000. The gold itself is pushed to
median rank 15. The 519 gold-inserted rows taught the model that anchor score lives away from lexical
relevance, and ungated scoring then chases arbitrary turns. Accounted for; no alternative survives.

## AF-FT-002 Part B — teacher-filtered reintroduction: DEAD, plus an interaction finding

Champion (ckpt2) teacher scores the 519 excluded items: **156/519 survivors** (gold top-1);
363 rejected (141 of them rank-7+). Above the 30-item underpower flag.

| config | exact | any | gated any | E-17 | any-net vs R0 |
|---|---|---|---|---|---|
| **F1** champ + 156 survivors | 53.6 | 63.2 | 62.4 | 17×5 | [−3,−2,−6,−6,−2], p .15–.77 |
| **F2** F1 + null head (V2 recipe) | **59.2** | **67.8** | 61.6 | **0×5** | [1,1,1,1,0] |

- **F1: DEAD.** Survivor rows add nothing (−3.8 any, direction negative, p 0.15+; far from −2 exact
  floor but no bar met either way). 30% recoverable — and unrecoverable *usefully*.
- **F2: DEAD on the registered no-trade bar — E-17 = 0/17, every seed.** Its sample2 numbers are the
  best ever seen (exact 59.2, any 67.8, null AUROC 0.931) — and it loses the E-gap anchor task
  entirely. Verified not-eval-bug: same scorer, gold at rank 1 for R0/V2/F1 and rank 108 for F2.

**The interaction, stated precisely.** F2 differs from V2 by exactly one thing: removing the 337
teacher-rejected rows. With them, under the null head, V2 holds E-17 at 17/17 (and sample2 at
66 any). Without them, the null head collapses E anchors to zero — while *improving* sample2 exact.
The rejected rows are simultaneously the ungated-landscape poison (they make V1 score junk) and the
only training data teaching **cross-lexical anchor behavior**, which is exactly what the E-gap items
are (low-overlap event-marker anchors). Data hygiene cannot be decided corpus-generically: the same
rows are poison for one failure mode and load-bearing for the product's core task. Any future filter
must be judged on *both* slices, never on LoCoMo sample2 alone.

## AF-FT-003 — the V2 repair is an interaction effect: neither component alone works

Data frozen at V1H; single-knob variants, 3 seeds each:

| config | margin | LS | exact | any | E-17 | null fires? |
|---|---|---|---|---|---|---|
| V1H (ref) | — | — | 32.0 | 34.4 | 17 | n/a |
| **N1** null rows only | 0 | 0 | 42.0 | 48.3 | 17 | **no** (leak 1.00 at all thresholds ≤ .8) |
| **N2** rows+margin | .5 | 0 | 42.3 | 49.0 | 17 | no (leak 1.00) |
| **N3** rows+LS | 0 | .05 | 42.7 | 47.7 | 17 | no (leak .99–1.00) |
| **V2** rows+margin+LS | .5 | .05 | **59.4** | **66.0** | 17 | yes (AUROC .936, 93%@22%) |

The plan's pre-stated interpretations both fail: null rows alone do not carry the repair (48.3, and
the head *cannot abstain* — leak ≈ 1.0 everywhere), and neither single regularizer does. Each single
component buys a partial landscape lift (34→48, p≈0) and a rank signal without usable separation
(AUROC ~0.71). The full recipe's repair and its abstention firing are **emergent from
null-rows × margin × smoothing together**. "Null rows are the mechanism" is not the story the
decomposition tells; it is the bundle, and bundle it stays — registered as a limitation now resolved
into knowledge: the working recipe is one object, not a mechanism claim.

## What is closed, what carries

Closed: hard-row reintroduction as a lever (raw *and* teacher-filtered); "the 519 are recoverable
data"; single-component simplifications of the V2 recipe; the anti-lexical-poison hypothesis is
CONFIRMED (forensics), replacing hypothesis with measurement.

Carrying: **V2 remains the only working abstention recipe** — and it is load-bearing on exactly the
hard data that any cleaning pass would delete. The E-gap 17/17 no-trade bar did real work in this
study: without it, F2's sample2 numbers would have shipped a model that cannot do the product's
task. All follow-up training paths from this branch are now exhausted; the registered next step is
the **reader arm** (needs the user's call-budget authorization), where V2's threshold is read off
the coverage–risk curve.

Artifacts: `af_ft002.py`, `af_ft003.py`, `dbg_e17.py`, `artifacts/ft002/{forensics,filter,results}.json`
(F1/F2), `artifacts/ft003/results.json` (N1–N3), training logs under `artifacts/ft00{2,3}/`;
19 checkpoints reproducible from (tag, seed).
