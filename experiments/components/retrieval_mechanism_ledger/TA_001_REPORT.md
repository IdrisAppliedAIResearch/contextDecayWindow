# TA-001 - Temporal-Adjacency Bridge Retrieval Report

**Date:** August 11, 2026
**Status:** COMPLETE - `TARGETED_REGRESSION`; `CHARACTERIZED`
**Pre-registration:** `23cff2d8da6e864363b05d2438398f9b60c8893b`
**Authorization:** `43d4e764ef95cd1b89a6037d925824a686221991`
**Amendment 001:** `6ffe9b7c382b486e0d77dcd170e966b8aa507670`
**Part 1:** `0ea39da6fa66b23773593fdff36bdc28a433bad5`
**Final design:** `6e3e839f62fa0cb37f09e5900bf16e5ef841e22e`
**Preflight:** `a4b80e613090b151ef2402e27dd9d3e26c5c4276`
**Offline result:** `c6173c45c6ad7f6ff5d557a704c1850d0ac28180`

## Result

The temporal bridge worked on the motivating broad query and failed its
general no-regression requirement.

Under exactly 15 candidates per arm, the same whole-episode representation,
the same skip-overflow packer, and the same 32,000-character ceiling:

| Measure | C0 fixed query | T1 adjacency | Change |
|---|---:|---:|---:|
| Q11 candidate facts | 9/17 | 10/17 | +1 |
| Q11 packed facts | 7/17 | 9/17 | +2 |
| Q11 candidate art | 0/4 | 4/4 | +4 |
| Q11 packed art | 0/4 | 4/4 | +4 |
| Selected episodes | 11 | 13 | +2 |
| Delivered characters | 31,957 | 28,808 | -3,149 |

G1-G4 pass. G5 fails because the 24 targeted queries contain two gains, six
losses, and 16 ties. The first binding disposition is `TARGETED_REGRESSION`.
The conditional 35-turn ablation is therefore not authorized and was not run.

## What happened mechanically

T1 processes direct-query seeds in rank order and places each seed's immediate
stored neighbors directly behind it. On Q11, direct rank 6 is turn 54. T1
therefore admitted and packed turns 54, 53, and 55; turn 55 supplied all four
art facts.

That local success consumed candidate slots. Across the 25 traces, T1 used
only 5-7 direct-query seeds and 8-10 temporal neighbors. Q11 candidate coverage
gained all four art facts but lost three marine facts. After packing it also
gained two civil facts, while losing three marine facts and one monetary fact:

- Gains: `S460ML`, `92.4`, and all four art facts.
- Losses: `Federal Reserve`, `Vampyroteuthis infernalis`, `600`, and
  `marine snow`.

The net broad count rose because six gains exceeded four losses. The mechanism
did not become generally better at retrieval; it exchanged semantic seed
breadth for local conversational continuity.

The targeted losses make that exchange explicit:

| Query class | C0 macro recall | T1 macro recall |
|---|---:|---:|
| Lookup | 0.5833 | 0.5000 |
| Chained | 0.5625 | 0.5625 |
| Enumeration | 0.3125 | 0.1250 |

Six queries regress: `h121_l04`, `h121_c02`, `h121_c08`, `h121_e01`,
`h121_e02`, and `h121_e03`. Two improve: `h121_c06` and `h121_c07`.
Art, marine, and structural domain aggregates regress; monetary improves.

## Gate record

| Gate | Result | Evidence |
|---|---|---|
| G1 integrity and reproduction | PASS | Part 1 and PF1-PF10 pass; C0 identity and 7/17 exact |
| G2 matched opportunity | PASS | 15 candidates each; all 25 paired payloads at or below 32,000 chars |
| G3 broad discovery | PASS | Candidate 9->10 and packed 7->9 |
| G4 art recovery | PASS | Candidate and packed art both 4/4 |
| G5 targeted no regression | **FAIL** | 2 gains, 6 losses, 16 ties; five class/domain aggregates regress |

Availability remains distinct from answer quality. No model answer was
generated, no score was produced, and no inference run occurred.

## Integrity and amendment

Part 1 was label-blind and produced the same deterministic digest in two fresh
processes:
`54983E565475AFD17862C9AEE46D12018DC344206ED9CCB3A60C2E3774DA50A5`.
It reproduced the committed Q11 C0 candidate, packed-identity, payload, and
character identities exactly. PF1-PF10 all passed before measurement.

Amendment 001 corrected one prospective input path. The registered span-vector
cache had zero exact query-text hits; the already committed Tier-4A cache had
24/24. The amendment changed no vectors, arm, parameter, gate, or threshold and
was committed before implementation.

## Verification

- Focused TA-001 suite: `20/20` pass.
- Full repository suite: `1529` pass, `8` fail.
- The eight failures are inherited working-tree byte-identity checks in
  BA-001, PS-001, and PS-003. On this Windows checkout, Git materialized CRLF
  bytes while those locked checks expect committed LF blob hashes. TA-001 did
  not edit those files, and their integrity checks were not weakened.
- Model-generation calls: 0. New embedding calls: 0. Live runs: 0.

No published number changed, so `ERRATA.md` requires no update.

## Decision

TA-001 closes as a useful negative result. Radius-1 adjacency is a real route
to locally associated evidence, including the previously missing art bundle,
but unconditional interleaving is too blunt under a fixed candidate quota. It
cannot advance to ablation, live evaluation, promotion, or adoption.

Any attempt to make adjacency conditional, reserve semantic seed slots, use
spare budget, or choose neighbors by another signal is a new selection policy
and requires a separate prospective study. It may not be repaired in TA-001.

## Artifacts

- `artifacts/ta001_exploration/`
- `artifacts/ta001_preflight/`
- `artifacts/ta001_measurement/results.json`
- `artifacts/ta001_measurement/query_comparisons.csv`
- `artifacts/ta001_measurement/targeted_fact_matrix.csv`
- `artifacts/ta001_measurement/q11_fact_matrix.csv`
- `artifacts/ta001_measurement/payloads/`
