# Study 005 35-Turn Ablation Report

**Date:** July 22, 2026
**Status:** PASS - GO
**Pre-registration SHA:** `20aa7707e780543ccbe462efadf3bb1263b3813e`
**Run implementation SHA:** `f4fe23253d3643805a6007dee05b9fb3ef6c59a0`
**Gate verifier SHA:** `eeafa6bc99e03e2acf677f9a253059d463daa4e3`
**Run ID:** `study_005_ablation_001`
**Server PID:** `20648`

## Gate results

| Check | Expected | Actual | Pass? |
|---|---|---|---|
| Speed (single-slot) | >30 tok/s | minimum 33.77; average 39.41 tok/s | PASS |
| Determinism | Prefix re-run identical | 10/10 prompts and responses identical | PASS |
| Raw store append-only | Non-content stored | 35/35 turns stored under unique episode IDs | PASS |
| Promotion absent | No filter code runs | 0 promoted-LTM rows; dreaming path active | PASS |
| First dream pass | Fires at about turn 31 | one transition event at turn 31 | PASS |
| Distilled records written | At least 1, verbatim, provenance resolves | 3 records from source turns 4, 17, 20 | PASS |
| Extractive assertion | Passes; zero inference calls in dream | 3/3 faithful; 0 dream inference calls | PASS |
| Read path from distilled LTM | At least 1 post-31 context | LTM present and arbitrated into final set at turns 32-35 | PASS |
| facts-in-LTM (civil) | Civil planted fact present | S460ML and 92.4 metric-ton axle targets present from turn 4 | PASS |
| Non-content in LTM | Zero | 0 | PASS |
| Arbitration/dedup | Carried behavior intact | 35 events; final set cap respected; LTM contribution at 32-35 | PASS |
| Purity | No cross-domain merge | 0 purity violations; probe range not reached | PASS |
| Active art topic | Not dreamed in this slice | all turns 31-35 remain undreamed | PASS |
| Context ceiling | Below 80% of 50k | peak 9,423 tokens (18.85%) | PASS |

The turn-31 event evaluated the 30-episode outgoing civil topic, wrote exactly the cap of three records, and made no inference call. The locked formation harness reports civil engineering present, faithfulness 1.0, and zero non-content records. The art topic begins at turn 31 and remains in the raw store for its later registered transition.

At the turn-20 consolidation, the two-turn rules topic merged into the civil topic. Both carried the same registered civil ground-truth label, so this was not a cross-domain purity event. No probe turn occurs in the ablation range.

The machine-readable gate output is `ablation_verification.json`. Raw database, prompt, and JSONL artifacts remain local under the ignored ablation run directory.

## Decision

**DECISION: GO — all applicable checks passed; synthetic verification covered flush/guard/floor/breadth/determinism. Control + full v5 run authorized.**
