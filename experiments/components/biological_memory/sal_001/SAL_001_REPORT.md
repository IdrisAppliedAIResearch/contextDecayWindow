# SAL-001 - Independent Surprisal-Proximity Diagnostic Report

**Pre-registration anchor:** `15b718e3456027a60f370790588b976df6353f02`  
**Implementation anchor:** `9a5d58ad4c19936152533b2459a996de32c12642`  
**Seal anchor:** `665b021e03bd622488018977f2739b07eb1a3765`  
**Label-blind score anchor:** `8700fbfc543beb511dba062cf05f6cefba98fac5`  
**Final design anchor:** `b4302374`  
**Passing Preflight anchor:** `63a79415`  
**Outcome anchor:** `95a51905`  
**Date:** August 11, 2026  
**Status:** `NO_INDEPENDENT_PROXIMITY - CHARACTERIZED`

## Result

SAL-001 tested F2 from
`HYPOTHETICAL_001_MECHANICAL_BIOLOGICAL_MEMORY_MODEL.md`: whether the pinned
Qwen reader's token surprisal could stand in for reward and confer value on an
independent neighboring exchange. It used a deterministic 60-history
LongMemEval holdout, 93 eligible evidence sessions, 545 exchanges, 98 marked
evidence exchanges, and 92 session-level AUC replications.

G1 passed. G2 failed first and stopped promotion.

| Measure | Result | Binding bar |
|---|---:|---:|
| Adjusted symmetric-neighbor AUC | **0.41599** | >=0.60 |
| One-sided permutation p | **0.99134** | <=0.01 |
| Descriptive session-bootstrap 95% interval | **[0.35132, 0.48388]** | descriptive |
| Raw symmetric-neighbor AUC | **0.29984** | >=0.55 |
| Adjusted prior-neighbor AUC | **0.39929** | >=0.55 |
| Adjusted next-neighbor AUC | **0.47705** | >=0.55 |

Five of six strata were below chance. `single-session-preference` was 0.50381;
the others ranged from 0.29750 for temporal reasoning to 0.46000 for knowledge
updates. G3, G4, and G5 also failed, but G2 owns the disposition.

This is not a weak positive or an underpowered null. The registered effect is
in the opposite direction: later-needed exchanges tended to sit beside less
surprising user turns than their within-session controls.

## What it means

The proposed text analogue of synaptic tagging and capture does not survive
its first decisive test. Model surprisal is not a useful content-blind resource
signal for neighboring conversational material under this design. Therefore:

- The surprisal-driven P1-P4 tag/capture path is killed for this program.
- No minimal accessibility-separation study follows from F2.
- No threshold tuning, wider window, new aggregator, c121 rerun, ablation, or
  live run is authorized.
- P5/P9 supersession remains open because it does not depend on surprisal,
  tagging, or capture.

The result does not show that every notion of salience is useless. It shows
that this architecture's specific move - transfer importance from an
independently surprising neighbor without reading the target - is unsupported.

## Post-result explanation

A registered disposition was already fixed, then one descriptive analysis
asked why the sign was negative. It changed no gate or authorization.

Boundary placement is not the explanation. Sessions with evidence at a first
or last exchange had neighbor AUC 0.41478 across 53 sessions; interior-only
evidence had 0.41764 across 39 sessions.

The informative contrast is local versus transferred surprise:

| Descriptive signal | AUC |
|---|---:|
| Evidence exchange's own adjusted user-turn surprisal | **0.62096** |
| Independent adjacent-exchange surprisal | **0.41599** |

The model often finds the evidence exchange's own incoming user text unusual,
but that signal does not extend to the preceding or following exchange. In
plain language, surprise can mark the thing itself; it does not make nearby
things important. That is a conventional content-based importance signal,
not P2's content-blind temporal capture.

## Integrity and limits

The pre-registration committed before implementation. A sealer reproduced
EC-001 ranks 1-20 before selecting held-out ranks 21-30. The model scorer saw
only a label-free manifest; labels opened only after the complete score output,
fresh-process repeat, final design lock, and passing PF1-PF10 were committed.
All 18 repeated raw rows were byte-identical. The full 545-row score had 545
distinct NLL values. The pinned synthetic anchor repeated exactly.

The adjustment removed registered effects of token count, model-token IDF,
exchange position, and preceding context length. Residual correlations were
approximately `10^-16`. This does not establish causal capture, complete
LongMemEval labeling, natural conversation ecology, or generality beyond one
model and one benchmark. Marker incompleteness can make some controls false
negatives, although that noise does not explain a robust inverse as a positive.

No generation, answer scoring, embedding, retrieval, packing, memory state,
35-turn ablation, or live inference occurred.

## Verification

Focused SAL-001 tests: 17 passed. Full repository suite: 1,561 passed and 11
inherited Windows/hash-anchor failures, exactly the prior failure set plus the
17 new passing tests. No historical locked hash was changed to hide them.

Primary artifacts:

- `artifacts/sal001_seal/seal_report.json`
- `artifacts/sal001_scores/part1_report.json`
- `artifacts/sal001_preflight/preflight.json`
- `artifacts/sal001_analysis/analysis.json`
- `artifacts/sal001_analysis/posthoc_characterization.json`

