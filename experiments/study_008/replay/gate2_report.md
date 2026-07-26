# Study 008 — Gate 2 Four-Arm Replay

**Tasks:** S8-T-012 through S8-T-014
**Arm A byte fidelity:** PASS
**Proceed verdict:** STOP

## Arm A fidelity

| Probe | Predicted SHA-256 | Actual SHA-256 | Equal |
|---:|---|---|---|
| 120 | `f78f91fea54b535494437ce43f10278ced4720001dd78346be238c9c6b75180a` | `f78f91fea54b535494437ce43f10278ced4720001dd78346be238c9c6b75180a` | True |
| 121 | `4b338017ab877cb6a2bc90ff2a62222b69a8129eec8359a8be007dbf4a87c61d` | `4b338017ab877cb6a2bc90ff2a62222b69a8129eec8359a8be007dbf4a87c61d` | True |

## Calibration sweep

| c_fill | A 4/4 | B 4/4 | C 4/4 | D 4/4 | Capture prevented | Gate 3 |
|---:|---|---|---|---|---|---|
| 1 | FAIL | PASS | FAIL | FAIL | True | FAIL |
| 2 | FAIL | FAIL | FAIL | FAIL | True | FAIL |
| 3 | FAIL | FAIL | FAIL | FAIL | True | FAIL |
| 4 | FAIL | FAIL | FAIL | FAIL | True | FAIL |
| 5 | FAIL | FAIL | FAIL | FAIL | True | FAIL |
| 6 | FAIL | FAIL | FAIL | FAIL | True | FAIL |
| 8 | FAIL | FAIL | FAIL | FAIL | True | FAIL |
| 10 | FAIL | FAIL | FAIL | FAIL | True | FAIL |
| 15 | FAIL | FAIL | FAIL | FAIL | True | FAIL |
| 20 | FAIL | FAIL | FAIL | FAIL | True | FAIL |
| 30 | FAIL | FAIL | FAIL | FAIL | True | FAIL |
| 40 | FAIL | FAIL | FAIL | FAIL | True | FAIL |
| 50 | FAIL | FAIL | FAIL | FAIL | True | PASS |

No jointly admissible value exists in the sweep. Per the locked
proceed condition, do not run.

## Integrity

- Study 007 artifacts unchanged: **True**
