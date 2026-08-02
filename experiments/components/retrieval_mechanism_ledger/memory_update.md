# Retrieval Mechanism Ledger Memory Update

**Status:** REOPENED on 2026-08-01 for Family CS. Family QR remains closed.

## E005 diversity-aware selection - PROMOTION_ELIGIBLE offline

Design anchor `ebbf384e18f38c5af017464e4723a3c77d81e73b`. Set-level selection is
the first mechanism here to move breadth materially at the enforced budget
without costing anything elsewhere. All 146 swept configurations beat A0's 6/17.
Primary `A3_l0.1_r0.0_k16`: **12/17 across 4/4 domains, 31,569 chars, 16/16
targeted preserved, 4/5 oracle episodes recovered.** 35 configurations passed
every gate.

**Still short.** 12/17 is below the 14/17 rubric threshold and the 15/17 oracle.
This is offline availability only; no live run is authorized and no answer was
generated or scored.

Carry forward:

1. **The highest count can be the worst selector.** Facility location scored
   13/17, best in the sweep, with monetary 0/4 at every `r`, and passed no gate.
   Scoring on the total alone would have promoted a three-domain payload as a
   breadth result. The per-domain diagnostic caught it, as registered.
2. **"The budget is slack" describes the optimum, not the selector.** AR-001's
   15/17 costs 5,455 of 32,000, which made cost scaling look inert. The greedy
   frame fills the budget, so every arm spent 31,000-plus characters and the
   knapsack constraint was active throughout: `r` changed the fact count in 44
   of 44 A3 cells. Check what the mechanism does, not what the optimum costs.
3. **A pre-filtered pool can decide the result before the mechanism runs.** On
   the deployed N-cap union K pool, zero configurations covered four domains.
   The oracle's episodes rank 14, 21, 22, 86 and 112 of 119 by cosine, so any
   similarity pre-filter drops the ones carrying the missing domains. Measure
   pool reachability against a known optimum before locking a pool.
4. **Greedy near its bound relocates the gap.** Optimality ratios ran
   0.955-0.9996, so 12/17 against 15/17 is the surrogate objective topping out,
   not search suboptimality. Tuning the sweep harder will not close it.
5. **Prior-answer hazard is live and unresolved.** The primary configuration
   draws 5 of 15 episodes from prior probe answers (range 0.100-0.333 across
   passing configurations). Four of AR-001's five optimum episodes are prior
   answers too, so this is where the facts sit. Study 004's error cascade is the
   risk: availability is not correctness, and nothing offline separates them.
6. **MMR is non-monotone submodular, not non-submodular.** Lin and Bilmes (2011)
   Theorem 2. The greedy guarantee fails on monotonicity. The scan's conclusion
   survived; its reason did not.

**Measurement correction (Amendment 004):** the no-regression gate keyed
availability on `(turn, item)` while the denominator counted rows, and Q7/Q10
share two turn-118 items. Preservation was capped at 14/16 for every selector,
making the gate unsatisfiable and flipping E005 to `REJECT_NO_REGRESSION` until
found. This also lifts E002's published 14/16 to 16/16 without disturbing its
KILL. Seventh instance of the count-unit failure class.

## DX-001 turn-90 miss - NO CHANGE, closed 2026-08-01

Registration `a30d3bcca53248fe75b7901c2ff74a8aa28f5e1a`. The whole remaining gap
between E005's 12/17 and the 15/17 oracle is **one episode**: turn 90, monetary,
four items, cosine rank 112 of 119, 2,862 characters. It sits inside the
registered pool and **no configuration of the 146 selects it.**

Carry forward:

7. **A cause is not a remedy, and the registered no-change branch is a real
   outcome.** Three mechanisms fire (cost discount, relevance floor, budget
   exhaustion) and none of them is actionable: `r` moves the episode's best rank
   from 16 to 8 to 4 and never to 1, and a marginal-gain termination rule
   subtracts episodes rather than adding this one. Shipping 12/17 with the miss
   characterized beats tuning a parameter to a single known test case.
8. **Refuting your own prediction is the cheap part of pre-registration.**
   Cluster collision was registered as the most likely mechanism at ~65%
   confidence. It does not fire at all: turn 90's k=16 cluster holds 20
   episodes and **no selection ever enters it**, so the diversity term was
   offering full credit at all 15 steps and no episode there was relevant enough
   to collect. The objective declined it on relevance alone, by 0.169.
9. **Pool and objective bind on different parts of the same gap.** DR-002 showed
   the pool decides what can be seen - widening 34 to 119 moved 5/17 at 2/4
   domains to 12/17 at 4/4. DX-001 shows the objective decides what is worth
   taking, and no amount of pool work recovers an episode already in the pool.
   Do not let one finding absorb the other.
10. **Reproducing a retrieval result requires reproducing the embedding call
    shape, not only the query text.** The Part 1 replay gate failed first time
    because the Q11 query was embedded alone rather than in E005's nine-query
    batch. The vectors agree to cosine 0.999837 and that is enough to flip 6 of
    146 committed payloads. One published DR-002 rank is corrected in
    `ERRATA.md`; no conclusion moves. Gate every diagnostic on byte-identical
    replay before reporting anything derived from it.

## Family QR, closed 2026-07-30

E002 remains KILL under its locked hurdle, but do not summarize it as no
movement. At an exact 32,000-character budget, segmentation raised the
unchanged selector from 6/17 to 10/17, a 66.7% improvement. F1 remains open,
with segmentation the best matched-budget improvement tested.

AR-001 proves the 14/17 bar is achievable under exact accounting: the exact
minimum is 5,058 characters, and 17/17 costs 7,592. Complete standalone domain
costs are civil 826, art 3,182, monetary 2,913, and marine 824 characters.
E002's absent art domain is a selection/ranking miss, not a 32k capacity limit.

Do not treat generator attention as a perfect-term oracle or a deployable
retrieval mechanism. E001 was an exploratory NF4 Q4-only diagnostic. Its best
cue raised cosine from 0.120421976 to 0.210318044 and descriptive similarity
rank from 24 to 20, but none of 714 rows reached K=0.48. The 0.210318044 value
is the best found across 335 cues, not a ceiling; the 266/384 selected heads
were non-discriminating relative to Wu et al.'s under-5% finding. F2 is closed
as a program disposition.

E003 late interaction is untested and not authorized for either an identity
repair or breadth. Opening a breadth test requires a new prospective bound,
measured storage multiplier, exact-budget policy, and targeted no-regression
test. E001 cannot supply that breadth bound.

E002 per-segment counts did return: 10 unique selections and eight duplicate
slots across nine segments, with two zero-unique segments. They did not certify
the seven missing facts or absent art domain, so F3 remains unclaimed.

Authoritative files:

- `E005_diversity_selection_protocol.md`
- `E005_POSTHOC_INTERPRETATION.md`
- `DX_001_turn90_diagnostic_and_fix.md`
- `DX_001_PART2_DISPOSITION.md`
- `artifacts/dx001/DX_001_report.md`
- `artifacts/dx001/dx001_results.json`
- `amendments/AMENDMENT_004_targeted_item_identity.md`
- `artifacts/e005/e005_results.json`
- `RETRIEVAL_MECHANISM_LEDGER_REPORT.md`
- `E002_POSTHOC_INTERPRETATION.md`
- `LITERATURE_LANDSCAPE.md`
- `AR_001_Q11_ACHIEVABILITY_PROTOCOL.md`
- `artifacts/ar_001/AR_001_report.md`
- `artifacts/e002/e002_results.json`
- `artifacts/e001/capture_001/capture_manifest.json`
- `artifacts/e001/analysis_001/e001_results.json`
