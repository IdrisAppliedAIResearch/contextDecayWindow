# Tier 6 Corrected 121-Turn Mechanism Evaluation

**Blinded score commit:** `578107a5`  
**Arm-mapping commit:** `3af44138`  
**Run:** `tier6_live_121_corrected_001`

## Outcome

The corrected widened-STM arm scored **11.0/13** with **Q14 = 1.0**. Study 009 Arm S scored 9.0/13 and Arm L scored 12.0/13. Widening recovered 2.0 points over S but remained one point below L.

The registered character-match gate remained **PASS**. The corrected offline/live N-order equivalence gate was **PASS**. The run completed 121 turns with 0 empty answers and 0 responses at the output limit.

## Score Pattern

Relative to Study 009 S, the corrected arm lost on Q4 and gained on Q5, Q7, Q8, Q10, Q14. The targeted non-breadth losses were Q4.

The result rejects the simple claim that LTM's 12.0 was only a consequence of greater delivered character volume: matching that volume improved STM from 9.0 to 11.0, but did not reproduce LTM. Volume explains part, not all, of the observed advantage. This is consistent with relevance and selection policy still contributing.

## Decision

The registered score rule marks the 1,000-turn confirmation as eligible because the corrected score is below 12.0. It is not launched here: owner authorization explicitly requires reviewing this 121-turn result before committing that compute.

## Integrity

Mechanism seal verification: **PASS**, 265 files, aggregate `6d2f7dac4d998b6d6d5d62dd7fbabe3786e61533682f42d44cc81b16687dc31e`. The preserved invalid 6.5 run remains diagnostic-only and was neither deleted nor used for the architectural conclusion.
