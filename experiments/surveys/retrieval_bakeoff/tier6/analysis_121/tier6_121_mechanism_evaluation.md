# Tier 6 121-Turn Mechanism Evaluation

**Blinded score commit:** `39423b02`  
**Arm-mapping commit:** `35af70a4`  
**Sequencing amendment:** `c87de99e`  
**Sealed mechanism artifact commit:** `a3c80b07`

## Verdict

The observed 6.5/13.0 score is preserved, but it is **not valid evidence that a correctly widened STM arm stalls below Study 009 Arm L**. The live N ordering diverged from the ordering committed for calibration. That divergence locked the payload onto early civil episodes and starved K, so the run tested character volume under a different selection process.

**Recommendation: do not run the 1,000-turn extension with this implementation.** First decide whether to authorize a corrected 121-turn rerun whose live N order is mechanically proven identical to the registered calibration order. No 1,000-turn implementation or inference is authorized by this report.

## Character Match

| Window | Live median | Arm L median | MAE | Max error | Median APE | <=5% |
|---|---:|---:|---:|---:|---:|---:|
| Turns 92-111 (registered gate) | 59,530 | 60,595 | 1,146.8 | 2,945 | 1.79% | 20/20 |
| Turns 112-121 (observational) | 59,905 | 59,776 | 1,762.0 | 3,538 | 2.80% | 7/10 |

The registered volume gate genuinely passed. This is precisely why character count is insufficient as a surrogate for useful delivery: the resource amount matched while its allocation collapsed.

## Ordering Divergence

- Registered/calibration toy order: `never -> old -> new`.
- Production toy order: `never -> new -> old`.
- Contract result: **DIVERGENCE_PRODUCTION_REINFORCES_RECENT_RETRIEVAL**.
- K found 167 candidates on 74 turns, but delivered 0 K-only episodes on 0 turns.
- Source turns 1-18 were retrieved 103-120 times each; the registered art, monetary, and marine plant turns were each retrieved only once.

The calibrator orders unretrieved episodes first and then the least recent retrieval generation. The live engine sorts an exponentially decayed elapsed-time score in descending order, placing newly retrieved episodes ahead of older retrieved episodes. Rewriting retrieval timestamps after each turn therefore reinforces the same early set.

## Targeted Delivery

| Question | T6 | Study 009 S | Study 009 L |
|---|---:|---:|---:|
| Q1 | 2/2 | 2/2 | 2/2 |
| Q2 | 2/2 | 2/2 | 2/2 |
| Q4 | 0/4 | 4/4 | 4/4 |
| Q5 | 0/2 | 0/2 | 2/2 |
| Q6 | 0/2 | 2/2 | 2/2 |
| Q7 | 0/5 | 5/5 | 5/5 |
| Q8 | 0/2 | 0/2 | 1/2 |
| Q10 | 0/2 | 2/2 | 2/2 |

Relative to corrected Study 009 S, widened STM lost Q4, Q6, and Q7, totaling 2.5 points. Those are exactly the probes where S delivered the required source facts and T6 delivered none. This is retrieval displacement, not a context-capacity or scorer effect.

## Breadth Delivery And Use

| Arm | Probe | Delivered / 17 | Recalled | Unused | Invented | Absent |
|---|---|---:|---:|---:|---:|---:|
| T6 | Q11 | 7 | 7 | 0 | 0 | 10 |
| T6 | Q14 | 7 | 4 | 3 | 0 | 10 |
| S | Q11 | 6 | 6 | 0 | 0 | 11 |
| S | Q14 | 6 | 3 | 3 | 0 | 11 |
| L | Q11 | 10 | 10 | 0 | 0 | 7 |
| L | Q14 | 14 | 6 | 8 | 0 | 3 |

T6 used every atomic item it received at Q11 (7/7), with no atomic invention. Only 5 of those seven items had their registered plant source selected; 2 were available only through earlier probe answers. At Q14 it used 4/7 delivered atoms. The model generally used available evidence; missing source delivery was the binding failure.

At Q11 the 25 delivered episodes comprised 19 civil episodes, one generic art episode, and five prior probes. No original monetary or marine episode was present. Similarity found the turn-100 marine plant at Q7 and Q8, but N-first packing skipped it after the cap was consumed.

## Non-Causes

- Maximum estimated context was 15,423 tokens at turn 31, below the 40,000-token monitor.
- Empty responses: 0; responses at the 2,048-token budget: 0.
- One pinned rule remained at 147 estimated tokens; Q3, Q12, and Q13 all scored full credit.
- Forbidden memory-tier modules loaded: 0.
- Mechanism seal verification: **PASS**, 265 files, aggregate `8f131532e3f63918babd77d6c01bae4030848553c9fd9fcac4a8f88ceb523462`.

## Interpretation

The run establishes a narrower negative result: adding volume to this live most-recently-retrieved/N-first implementation made pure STM worse than the corrected Study 009 S baseline (6.5 versus 9.0), because extra N displaced useful K. It does not distinguish whether LTM's 12.0 advantage comes from the tier itself or from the diverse selection behavior that the registered widened-STM calibration intended but the live engine did not execute.

A 1,000-turn run would magnify the same lock-in and cannot serve as the planned confirmation. The economical next step, if the owner wants further evidence, is one corrected 121-turn rerun with an exact offline/live N-order equivalence gate and otherwise unchanged score threshold, seed, script, budget, and scorer.
