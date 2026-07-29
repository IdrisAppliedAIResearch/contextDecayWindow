# Retrieval Bakeoff Tier 2 Report

**Status:** COMPLETE_WITH_PROVENANCE_VIOLATIONS

| Method | Class | Recall | Coverage | Precision | Chars | Latency ms |
|---|---|---:|---:|---:|---:|---:|
| M1 | lookup | 0.6667 | 0.6667 | 0.0425 | 31709.5 | 200.213 |
| M1 | chained | 0.4792 | 0.5729 | 0.0965 | 31576.2 | 225.899 |
| M1 | enumeration | 0.2396 | 0.2396 | 0.1088 | 31504.6 | 215.208 |
| M2 | lookup | 0.8750 | 0.8750 | 0.0664 | 31607.3 | 203.540 |
| M2 | chained | 0.5938 | 0.6562 | 0.1082 | 31654.6 | 225.225 |
| M2 | enumeration | 0.1875 | 0.1875 | 0.0590 | 31471.1 | 215.622 |
| M3 | lookup | 0.9583 | 0.9583 | 0.0839 | 31703.3 | 2.091 |
| M3 | chained | 0.7812 | 0.8125 | 0.1439 | 31755.5 | 2.116 |
| M3 | enumeration | 0.3542 | 0.3542 | 0.1805 | 31740.8 | 2.250 |
| M4 | lookup | 0.9167 | 0.9167 | 0.0729 | 31717.3 | 203.700 |
| M4 | chained | 0.7812 | 0.8125 | 0.1382 | 31729.9 | 228.922 |
| M4 | enumeration | 0.3438 | 0.3438 | 0.1506 | 31494.9 | 224.531 |
| M5_span | lookup | 0.7500 | 0.7500 | 0.0087 | 31927.0 | 215.792 |
| M5_span | chained | 0.5938 | 0.6562 | 0.0153 | 31913.8 | 232.722 |
| M5_span | enumeration | 0.6458 | 0.6458 | 0.0515 | 31925.1 | 224.702 |
| M6 | lookup | 0.8750 | 0.8750 | 0.0664 | 31607.3 | 202.617 |
| M6 | chained | 0.5938 | 0.6562 | 0.1082 | 31670.4 | 629.253 |
| M6 | enumeration | 0.2396 | 0.2396 | 0.0882 | 31438.8 | 1884.920 |

## Advancement

- `M2`: DOES NOT ADVANCE; wins=lookup,chained; regressions=enumeration.
- `M3`: ADVANCES; wins=lookup,chained,enumeration; regressions=none.
- `M4`: ADVANCES; wins=lookup,chained,enumeration; regressions=none.
- `M5_span`: ADVANCES; wins=lookup,chained,enumeration; regressions=none.
- `M6`: ADVANCES; wins=lookup,chained,enumeration; regressions=none.
