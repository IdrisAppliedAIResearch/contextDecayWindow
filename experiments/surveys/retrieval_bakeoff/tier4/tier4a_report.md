# Retrieval Bakeoff Tier 4A Report

**Status:** COMPLETE

**T4B gate:** CLOSED_NOT_RUN_BY_BINDING_GATE

## Graph Structure

| Corpus | Edge | Nodes | Edges | Density | Build ms | Update ns |
|---|---|---:|---:|---:|---:|---:|
| c121_l | E1 | 111 | 110 | 0.018018 | 0.245 | 100.0 |
| c121_l | E2 | 111 | 1790 | 0.293202 | 49.970 | 8600.0 |
| c121_l | E3 | 111 | 671 | 0.109910 | 2.002 | 11200.0 |
| c121_l | E4 | 111 | 1515 | 0.248157 | 1.188 | 300.0 |
| c1000_l | E1 | 986 | 985 | 0.002028 | 2.325 | 200.0 |
| c1000_l | E2 | 986 | 154112 | 0.317361 | 1158.953 | 362850.0 |
| c1000_l | E3 | 986 | 4325 | 0.008906 | 50.878 | 29400.0 |
| c1000_l | E4 | 986 | 446860 | 0.920213 | 338.054 | 1300.0 |

## Advancement

| Method | Recall gate | Update gate | Advances | Wins | Regressions |
|---|---:|---:|---:|---|---|
| G_E1_E2_E3_d1 | False | True | False | lookup | chained,enumeration |
| G_E1_E2_E3_d2 | False | True | False | lookup | enumeration |
| G_E1_E2_E3_d3 | False | True | False | lookup | chained,enumeration |
| G_E1_E2_d1 | False | True | False | none | chained,enumeration |
| G_E1_E2_d2 | False | True | False | none | chained,enumeration |
| G_E1_E2_d3 | False | True | False | none | lookup,chained,enumeration |
| G_E1_E3_d1 | False | True | False | lookup | enumeration |
| G_E1_E3_d2 | False | True | False | lookup,chained | enumeration |
| G_E1_E3_d3 | False | True | False | lookup | chained,enumeration |
| G_E1_d1 | False | True | False | none | chained,enumeration |
| G_E1_d2 | False | True | False | lookup,chained | enumeration |
| G_E1_d3 | False | True | False | none | chained,enumeration |
| G_E2_E3_d1 | False | True | False | none | chained,enumeration |
| G_E2_E3_d2 | False | True | False | none | chained,enumeration |
| G_E2_E3_d3 | False | True | False | none | chained,enumeration |
| G_E2_d1 | False | True | False | none | lookup,chained,enumeration |
| G_E2_d2 | False | True | False | none | lookup,chained,enumeration |
| G_E2_d3 | False | True | False | none | lookup,chained,enumeration |
| G_E3_d1 | False | True | False | lookup | enumeration |
| G_E3_d2 | False | True | False | lookup,chained | enumeration |
| G_E3_d3 | False | True | False | lookup,chained | enumeration |
| G_E4_d1 | False | True | False | lookup,chained | enumeration |
| G_E4_d2 | False | True | False | lookup,chained | enumeration |
| G_E4_d3 | False | True | False | lookup,chained | enumeration |

## Update Slopes

| Edge | Log-log slope | Passes <= 1.10 |
|---|---:|---:|
| E1 | 0.060414 | True |
| E2 | -0.099207 | True |
| E3 | 0.896662 | True |
| E4 | 0.438692 | True |

All retrieval rows use the registered holdout, exact 32,000-character serializer, and nine measured rank-plus-pack repetitions after one warm-up. E4 is descriptive and cannot open T4B.
