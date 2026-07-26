# Study 010 Offline Scale Gate Report

**Overall:** FAIL

## G1 - Retrieval at scale

- Episodes: 986
- Threshold: 0.5
- Peak projected K tokens: 7,696
- Mean/max query scan: 52.25 / 58.60 ms
- All 12 targeted probes recover a target plant source: True

## G2 - Consolidation at scale

- Final topics: 135
- Cross-domain topics: 1
- No swept threshold pair passed
- Result: FAIL

## G3 - Digest at scale

- NOT APPLICABLE: Study 009 resolved digest carry false.

## G4 - Checkpoint/restore

- Result: PASS
- Tests: ..                                                                       [100%]
2 passed in 0.04s

## Leakage

- Result: PASS
- Files scanned: 25
