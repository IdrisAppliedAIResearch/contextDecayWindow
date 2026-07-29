# T1.3 N/K Reinforcement Supplement

**Amendment:** `39ba9175`  
**Implementation:** `835671e602f56c28ad3f2d601f607a00df5cb199`  
**Hypothesis:** `H_T1.3_NK_REINFORCEMENT`  
**Verdict:** **NOT_CONFIRMED**

## Results

| Corpus | K candidates | K in N | Q1 overlap | Q4 overlap | Delta | OLS slope | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| study_009_arm_s | 127 | 77 | 79.01% | 35.29% | -43.72% | -0.887553 | DOES_NOT_SUPPORT |
| study_010_arm_s | 25654 | 525 | 5.54% | 1.18% | -4.37% | -0.153149 | DOES_NOT_SUPPORT |

The registered hypothesis is confirmed only if both corpora have a positive Q4-minus-Q1 micro-overlap delta and a positive per-turn OLS slope. These are deterministic census summaries; no p-value is used.

## Integrity

- `study_009_arm_s`: 121 contiguous turns, 59 with K candidates, all accounting and temporal invariants PASS; source SHA-256 `c948eaca81450cad14283b57591cdc2355011d797c885c84688d94acc37a9ddb`.
- `study_010_arm_s`: 1000 contiguous turns, 968 with K candidates, all accounting and temporal invariants PASS; source SHA-256 `e57dd5d170421da699abd094f304df3e783c559ca7997f183e4ad118b9e3f414`.

This supplement is descriptive and does not alter the completed T1.3 similarity result or any method-advancement decision.
