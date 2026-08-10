# E006 Part 2 Rev 5 Preflight

**Date:** August 10, 2026
**Decision:** **PASS - CONTINUE TO PARAMETER LOCK**
**Design anchor:** `764396b2`
**Authorization commit:** `ac81d8e1`
**PF11 artifact commit:** `90677655`
**Preflight execution commit:** `bc1c7338`
**Machine artifact:** `artifacts/e006_rev5_preflight/preflight.json`
**Machine artifact SHA-256:** `AD83E88CCAFA1346B5BFF38565D3905683B00746F3B5C45D56DBDDEEC496920F`
**Calls:** zero model calls; zero embedding calls

## 1. Exploration

On the committed Q11 trace, the mechanism starts from 119 query-to-episode
cosines. Each inclusive hop ranks every unseen episode by the normalized blend
of the original query and recursive context, takes exactly `m`, adds those
content identities to a monotone exclusion set, and updates context with the
normalized retained-context/hit-mean blend.

The 48 registered cells produce the following distribution before packing:

| D | Cells | Candidate range | Distinct selections | Final cue cosine to Q11 |
|---:|---:|---:|---:|---:|
| 0 | 12 | 3-5 | 2 | 1.000000-1.000000 |
| 1 | 12 | 6-10 | 7 | 0.945888-0.998202 |
| 2 | 12 | 9-15 | 8 | 0.926454-0.996240 |
| 3 | 12 | 12-20 | 12 | 0.881820-0.993239 |

Across 120 executed steps, novelty is always exactly `m`: 60 steps retrieve 3
new episodes and 60 retrieve 5. Context-update cosine ranges from `0.891570` to
`0.984364`; hit-mean squared norm ranges from `0.352132` to `0.842650`. No update
is a fixed point.

The mechanism source imports only generic numerical and data-structure modules.
It accepts query cosines, the episode Gram matrix, canonical content hashes, and
registered scalars; it cannot read fact keys, rubrics, or targeted definitions.

## 2. Checklist

| Check | Result | Evidence |
|---|---|---|
| PF1 inputs | PASS | 119 cosine rows, 119 episode vectors, 119 by 119 Gram matrix; all files counted and hashed. Prior audit found 0/8 targeted query vectors, retained as a scope limit |
| PF2 identity | PASS | All named components executed across the real 48-cell trace; deployed X0 remains thresholded K plus N-first packing, not `top_m` |
| PF3 order | PASS | Design `764396b2` < authorization `ac81d8e1` < PF11 artifact `90677655` < Preflight `bc1c7338` |
| PF4 reachability | PASS | Candidate fact upper bound rises above X0's 6/17 at chained depths before packing |
| PF5 stable keys | PASS | Canonical episode-content SHA-256 for selection, tie-breaks, controls, and measurement joins |
| PF6 reproduction | PASS | X0 reproduces 8 episodes, 31,946 characters, payload `64b19b96...8afe478`; all 12 `D=0` cells match single-shot `top_m` by content sequence and payload digest |
| PF7 absorbing state | PASS | 48/48 cells: no repeated hit set, no context fixed point, positive novelty at every step |
| PF8 adequacy | PASS | Depth-local Q11 behavior only; cannot detect cross-turn behavior or live variance |
| PF9 surrogate | PASS | Candidate volume, cost, domains, and drift must accompany fact count; targeted regression remains unmeasurable |
| PF10 verdict | PASS | Availability is not answer correctness; no inference, score, promotion, or adoption authorized |

## 3. Maximum Reachability

This is a candidate-union upper bound before packing, not an S4 result:

| D | Maximum Q11 facts in candidates | Maximum domains in candidates |
|---:|---:|---:|
| 0 | 3/17 | 1/4 |
| 1 | 7/17 | 3/4 |
| 2 | 9/17 | 3/4 |
| 3 | 13/17 | 4/4 |

At least one chained depth can exceed X0's `6/17`, so the registered kill is
reachable and S4 is not dead on arrival. Exact packing remains unobserved at
this stage.

## 4. Boundaries

`cue_final` is the cue used on the final inclusive loop iteration. Therefore
`D=0` is exactly single-shot query ranking; its post-hit context update is used
only if another hop exists. This follows the registered pseudocode's variable
ordering and is confirmed by all 12 payload controls.

No targeted no-regression arm is possible because no committed targeted query
cosine traces exist. The one-probe, one-corpus, zero-variance result remains
capped at `CHARACTERIZED` regardless of S4.

**PASS.** The fixed Rev 5 parameter grid may now be recorded as the S3 lock.
