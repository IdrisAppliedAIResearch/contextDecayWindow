# Retrieval Bakeoff Tier 5 Report

**Status:** COMPLETE

## T5.0 Budget Multiples

| Budget | Recall | Coverage | Chars | Selected |
|---:|---:|---:|---:|---:|
| 32000 | 115/144 | 0.8090 | 31726.9 | 27.1 |
| 64000 | 253/288 | 0.8785 | 63786.1 | 54.0 |
| 160000 | 547/576 | 0.9497 | 159740.6 | 133.9 |
| 320000 | 35/36 | 0.9722 | 319721.8 | 277.8 |

Fact-recall collapse above 2x: **False**.

## T5.1 ANN

| Scale | Synthetic | R@10 | R@50 | Exact ms | HNSW ms | Build ms | Index MiB |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 120 | 0 | 1.0000 | 0.9758 | 0.011 | 0.025 | 6.9 | 0.49 |
| 1000 | 14 | 1.0000 | 0.9583 | 0.061 | 0.043 | 184.7 | 4.05 |
| 10000 | 9014 | 0.9125 | 0.5250 | 0.359 | 0.039 | 1666.8 | 40.48 |
| 100000 | 99014 | 0.8583 | 0.3167 | 8.049 | 0.068 | 18363.0 | 404.80 |

## T5.2-T5.3 Progressive Search

| Arm | Queries | Recall | Old miss | Latency ms |
|---|---:|---:|---:|---:|
| P_recency | 48 | 41/576 | 1 | 251.370 |
| P_recency_rules | 24 | 0 | 1 | 229.321 |
| P_recency_topic | 24 | 0 | 1 | 235.459 |
| P_recency_topic_rules | 24 | 0 | 1 | 233.778 |

### Axis Validation

- `c121_l` topic: `VALID`; pinned rules: `VALID`.
- `c1000_l` topic: `NOT_EVALUABLE`; pinned rules: `NOT_EVALUABLE`.

## T5.4 Tiering Comparison

Any depth configuration matches or beats a partition arm on recall, latency, and old-fact miss jointly: **True**.
