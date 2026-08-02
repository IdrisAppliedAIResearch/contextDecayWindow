# E005 DR-002 - Candidate-Pool Prior Diagnostic

**Status:** COMPLETE - rule committed `fd53591f`, results in
`artifacts/e005/dr_002/DR_002_report.md`
**Verdict:** **COSINE ORDERING IS THE WRONG PRIOR.** Worst fact-bearing cosine
rank is 86 of 119, and both art contributors sit at ranks 50 and 86 while the
four highest-cosine episodes carry no Q11 facts at all. Widening the pool from
34 to 119 moves the frozen configuration from 5/17 at 2/4 domains to 12/17 at
4/4. Selection over the full store costs 1.28 ms against 0.45 ms, a 2.84x ratio
on 3.5x the candidates.
**Type:** Diagnostic read-out on committed E005 artifacts plus two new measurements
**Parent:** `E005_diversity_selection_protocol.md`, `E005_POSTHOC_INTERPRETATION.md`
**Frozen configuration:** A3, `lambda = 0.1`, `r = 0.0`, `k = 16`, budget 32,000,
same store, same renderer, same carried embedding model. One variable: the
candidate pool.

**This diagnostic cannot change E005's committed outcome, gates, or thresholds.**

## Premise Correction

The requested rerun - A3 at the primary configuration with the pool widened to
the full 119 candidates - **is the committed primary result.** E005's registered
primary pool is the complete eligible store, so `A3_l0.1_r0.0_k16` at 12/17
across 4/4 domains, 31,569 characters, 16/16 targeted preserved and 4/5 oracle
overlap was already measured at pool 119. Re-executing it reproduces that row by
construction; determinism is already gated by byte-identical rerun.

The comparison the decision rule needs is therefore the same frozen
configuration across the three registered pools, which is a read-out of
`configuration_sweep.csv`, not a new run.

## Contamination Disclosure

The pool comparison is **not** a prospective test and is not presented as one.
The sweep was committed on 2026-08-01 and its aggregate was already reported:
zero deployed-pool configurations reach four domains. The "still 3/4 on the
deployed pool" branch is therefore known to be settled before this file was
written. The per-configuration cells for the frozen configuration had not been
read at the time of writing, but the branch outcome was already implied.

Recording the pool comparison under a decision rule written afterwards would
misrepresent a read-out as a registered test. It is reported below as a
read-out and labelled as one.

## Registered Decision Rule - Cosine-Rank Prior

**Uncontaminated. The winning selections' cosine ranks have not been computed.**

For the frozen configuration at pool 119, record every selected episode's rank
in the Q11 cosine ordering over all 119 eligible episodes, and separately the
ranks of the fact-bearing selections.

- **Any fact-bearing selection at cosine rank 80 or worse** -> cosine ordering is
  the wrong prior for breadth. A candidate pool built by similarity cannot reach
  the evidence the selector needs, and pool construction becomes a scoped
  workstream with a measured payoff.
- **All selections inside cosine rank 34** -> the ordering is adequate and the
  deployed pool's failure is a cap-size problem, not an ordering problem. Widen
  the existing N cap; do not replace the prior.
- **Selections spread over ranks 34 to 79 with none at 80 or worse** ->
  the ordering is directionally right but the deployed cap is too small.
  Escalate as a cap-sizing question, not a prior-replacement question.

## Registered Measurement - CC-001 Wall Clock

Per-selection wall-clock for the frozen configuration at pool 119 against pool
34, everything else identical, reported as the median of repeated timed runs
with the count of runs stated. Embedding is excluded and stated separately: the
query and episode vectors are already resident, so the measured quantity is
selection cost, not retrieval cost.

**No threshold is registered.** This is a cost figure owed to CC-001, not a
gate. It is reported whatever it shows.

## Interpretation Boundary

One probe, one store, one frozen configuration. Availability and cost only. No
answer-correctness claim, no general breadth claim, and no live run is
authorized by this diagnostic.
