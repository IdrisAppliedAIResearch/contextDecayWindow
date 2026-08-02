# E005 Diversity-Aware Selection

**Design commit:** `ebbf384e18f38c5af017464e4723a3c77d81e73b`  
**Execution commit:** `dc9f090d9cf00d9dd7840048cf6027d2e5c9bd11`  
**Outcome:** **PROMOTION_ELIGIBLE**

## Result

The committed A0 baseline delivers **6/17** items across 3/4 domains, spending 31,946 of 32,000 characters on 8 episodes. The kill bar is 7/17.

The best set-level selector delivered **12/17** items across **4/4** domains (`A3_l0.1_r0.0_k16`), selecting 15 episodes for 31,569 characters at 3.801 facts per 10,000 characters. It recovered 4/5 of the carried oracle episodes.

### Best Q11 availability by arm, primary pool

| Arm | Selector | Best Q11 |
|---|---|---:|
| A0 | committed baseline | 6/17 |
| A1 | MMR | 12/17 |
| A2 | facility location | 13/17 |
| A3 | relevance plus cluster diversity | 12/17 |
| A4 | oracle, carried from AR-001 | 15/17 |

### Candidate pool, registered primary against secondaries

| Pool | Episodes | Best Q11 |
|---|---:|---:|
| `full_eligible_store` | 119 | 13/17 |
| `cosine_top_100` | 100 | 13/17 |
| `deployed_n_union_k` | 34 | 13/17 |

Targeted no-regression: the primary configuration preserved **16/16** committed-available items. Per-probe detail is in `targeted_no_regression.csv`.

## Integrity

Mechanism seal: **PASS**. Leakage audit: **PASS**. Source integrity: **PASS**. Byte-identical raw rerun: **PASS**. Inference calls: 0. Configurations swept per pool: 146.

## Interpretation Boundary

Availability only. Every arm is evaluated on one breadth probe, Q11, against one store, so no arm may claim general breadth capability from this result. A4 is AR-001's committed greedy set cover carried in as a reference point; it was not re-derived and is never deployable. This result makes no answer-correctness claim and authorizes no inference run.
