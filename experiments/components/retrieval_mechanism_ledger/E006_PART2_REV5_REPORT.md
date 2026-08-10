# E006 Part 2 Rev 5 Chained Retrieval Report

**Date:** August 10, 2026
**Outcome:** **SURVIVES KILL - CHARACTERIZED**
**Design anchor:** `764396b2`
**Authorization commit:** `ac81d8e1`
**PF11 artifact commit:** `90677655`
**Preflight artifact commit:** `5973989e`
**Parameter lock commit:** `91b25e8c`
**S4 execution commit:** `b101f040`
**Results:** `artifacts/e006_rev5_s4/results.json`
**Results SHA-256:** `BBEAE9CC6CB6EF830EF8CFEB7D4FE9F8BD710361927AC6ED1816DFAE1C86EC00`
**Manifest SHA-256:** `57EB11DE34091236D80FFCB639490CA91A23C00D44E23F6209D217220D63D051`
**Calls:** zero model calls; zero embedding calls

## 1. Gate Record

Rev 5 repaired Rev 4's missing hit-mean norm term without changing the vector
mechanism. PF11 then passed all 12 cells with maximum score error
`9.49240686054509e-15`, identical full rankings, and identical next `top_m`.

The remaining Preflight passed PF1-PF10. X0 reproduced its committed payload at
8 episodes and 31,946 characters; all 12 `D=0` cells reproduced single-shot
`top_m`; all 48 feedback cells had no repeated hit set, no context fixed point,
and positive per-step novelty. The fixed 48-cell grid was committed before S4.

## 2. Offline Result

| D | Arm | Q11 range | Best domains | Candidates | Selected | Characters | Final cue cosine |
|---:|---|---:|---:|---:|---:|---:|---:|
| 0 | X1 | 0-3/17 | 1/4 | 3-5 | 3-5 | 2,080-6,890 | 1.000000 |
| 1 | X2 | 3-7/17 | 3/4 | 6-10 | 6-10 | 11,315-28,957 | 0.945888-0.998202 |
| 2 | X3 | 5-9/17 | 3/4 | 9-15 | 9-12 | 20,673-31,957 | 0.926454-0.996240 |
| 3 | X4 | 6-9/17 | 3/4 | 12-20 | 11-12 | 28,995-31,957 | 0.881820-0.993239 |

X0's committed reference is `6/17` across 3/4 domains, 8 selected episodes,
and 31,946 characters. Four chained cells reach the maximum `9/17`:

| Configuration | D | Facts by domain (civil/art/monetary/marine) | Chars | Selected/candidates | Cue cosine |
|---|---:|---|---:|---:|---:|
| `D2_m5_wq0.3_rho0.5` | 2 | 5/0/1/3 | 28,562 | 12/15 | 0.932892 |
| `D3_m5_wq0.3_rho0.5` | 3 | 5/0/1/3 | 29,940 | 12/20 | 0.888826 |
| `D3_m5_wq0.3_rho0.7` | 3 | 5/0/1/3 | 29,732 | 12/20 | 0.962620 |
| `D3_m5_wq0.5_rho0.5` | 3 | 5/0/1/3 | 29,732 | 12/20 | 0.946652 |

The binding kill says to stop if no `D>0` cell exceeds X0's `6/17`. It does not
fire: depth 1 reaches `7/17`, and depths 2-3 reach `9/17`.

## 3. Interpretation

Chaining improves the registered single-shot `top_m` control from at most
`3/17` to `9/17` and exceeds deployed X0 by three available facts. It remains
below E005's `12/17` and the AR-001 oracle's `15/17`.

The gain does not establish better ranking. X0 selected 8 episodes; the best
chain cells considered 15-20 candidates and selected 12. They recover every
civil item, three marine items, and one monetary item, but **zero art items**.
The result is still a three-domain payload, and much of the apparent advantage
is consistent with returning more material through an always-nonempty `top_m`
path rather than improving the deployed sparse thresholded-K ranking.

Cue drift is modest relative to the prediction: even at depth 3 the minimum
cosine to the original query is `0.881820`, never below `0.7`. Additional depth
helps through depth 2 and then plateaus at `9/17`; depth 3 does not reduce the
best count, though it increases candidates and generally approaches the budget.

## 4. Registered Predictions

| Prediction | Result |
|---|---|
| PF11 passes | Correct |
| Preflight passes without cycles | Correct; 48/48 cells pass PF7 |
| Depth 1 helps, depth 3 hurts | Mixed; depth 1 helps, depth 3 ties depth 2 at the maximum |
| Best reaches 8-11/17, below E005 12/17 | Correct; best is 9/17 |
| Cue cosine falls below 0.7 by depth 2 | Incorrect; depth-2 minimum is 0.926454 |
| Chain beats X0 while returning more candidates | Correct; 9/17 vs 6/17, with 15-20 candidates in best cells |

## 5. Integrity and Ceiling

- Every S4 selection digest reproduces the committed Preflight selection trace.
- All 12 X1 cells reproduce their committed single-shot payload hashes.
- Two complete in-process evaluations are deterministic.
- All 48 stored payload files match their recorded raw UTF-8 SHA-256 and decoded
  exact character count.
- `configuration_sweep.csv` records facts, domains, exact characters, selected
  episodes, candidates, cue drift, payload hashes, and selection hashes for all
  48 cells.
- The mechanism source cannot import or read fact keys or rubric artifacts;
  Q11 measurement is loaded only after selection identities and payloads exist.

**Ceiling: CHARACTERIZED.** The eight targeted probes lack committed full cosine
traces, so no targeted no-regression arm was possible. This result makes no
answer-correctness claim and authorizes no live run, promotion, or adoption.
