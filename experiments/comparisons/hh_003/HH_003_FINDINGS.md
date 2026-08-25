# HH-003 Findings

## Scores

| Arm | Correct | LLM score | F1 | Exact match |
|---|---:|---:|---:|---:|
| `A_EPISODIC` | 1191/1540 | 0.7734 | 0.4537 | 0.0117 |
| `A_EPISODIC_ASPECT` | 1205/1540 | 0.7825 | 0.4534 | 0.0156 |

## Paired Contrasts

Positive net favors the left arm. HH-002 comparisons are cross-date.

| Left | Right | Gains | Losses | Ties | Net | Two-sided p |
|---|---|---:|---:|---:|---:|---:|
| `A_EPISODIC_ASPECT` | `A_EPISODIC` | 46 | 32 | 1462 | +14 | 0.140538 |
| `A_EPISODIC` | `A_CDW` | 107 | 134 | 1299 | -27 | 0.0937667 |
| `A_EPISODIC` | `A_RAG` | 559 | 73 | 908 | +486 | 1.07995e-93 |
| `A_EPISODIC` | `A_FULL` | 189 | 114 | 1237 | +75 | 1.94081e-05 |
| `A_EPISODIC_ASPECT` | `A_CDW` | 121 | 134 | 1285 | -13 | 0.452436 |
| `A_EPISODIC_ASPECT` | `A_RAG` | 564 | 64 | 912 | +500 | 6.73896e-101 |
| `A_EPISODIC_ASPECT` | `A_FULL` | 201 | 112 | 1227 | +89 | 5.54487e-07 |

## Interpretation

HH-003 registers no directional success bar and no automatic adoption decision. The primary judge endpoint, deterministic F1, category results, and operational distributions are recorded in `artifacts/run/report.json`.

LoCoMo is spent, and comparisons with HH-002 controls are cross-date. This run does not establish general superiority or current Mem0 product performance.
