# Study 008 — Gate 3 Targeted Fixture

**Task:** S8-T-011
**Criterion:** fact-aware, rendered-character-costed
**Verdict:** FAIL

| c_fill | Arm A | Arm B | Arm C | Arm D | Minimum own share |
|---:|---|---|---|---|---:|
| 1 | PASS | FAIL | PASS | FAIL | 0.115 |
| 2 | PASS | FAIL | PASS | FAIL | 0.185 |
| 3 | PASS | FAIL | PASS | FAIL | 0.231 |
| 4 | PASS | FAIL | PASS | FAIL | 0.239 |
| 5 | PASS | PASS | PASS | FAIL | 0.249 |
| 6 | PASS | PASS | PASS | FAIL | 0.252 |
| 8 | PASS | PASS | PASS | FAIL | 0.247 |
| 10 | PASS | PASS | PASS | FAIL | 0.242 |
| 15 | PASS | PASS | PASS | FAIL | 0.235 |
| 20 | PASS | PASS | PASS | FAIL | 0.254 |
| 30 | PASS | PASS | PASS | FAIL | 0.363 |
| 40 | PASS | PASS | PASS | FAIL | 0.490 |
| 50 | PASS | PASS | PASS | PASS | 0.507 |

No swept `c_fill` passes the registered targeted criterion in all four arms. The study may not proceed to ablation.

Per-query character splits, fact matches, top-item checks, and cost
bounds are recorded in `joint_gate_results.json`.
