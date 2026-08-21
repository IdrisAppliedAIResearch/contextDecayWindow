# HH-002 results

Arms scored: A_FULL, A_CDW, A_CDW_NOTS, A_RAG, A_NONE

## Judge run-to-run variance

Same 1540 sealed answers from `A_RAG`, judged twice.

- Rates: {'1': 45.7792, '2': 45.7143}
- Spread: **0.06 points**
- Items that flipped: 3 (0.19%)

Registered rule: ±3.0 points or the measured spread, whichever is wider. **Tolerance = ±3.00 points.**

## G-CTRL: did this rig reproduce the published rows?

| Arm | Published | Measured | Delta | Within tolerance |
|---|---:|---:|---:|:--:|
| `A_FULL` | 72.90% | **72.47%** | -0.43 | yes |
| `A_RAG` | 60.53% | **45.78%** | -14.75 | **NO** |

**G-CTRL FAILED.**

## G-FLOOR: contamination

`A_NONE` scored **26.30%** on 1540 questions with no memory block at all. Bar is below 5%. **FAILED.**

## The table

| System | LLM-as-a-Judge | n | Source |
|---|---:|---:|---|
| **A_CDW** | **79.09%** | 1540 | measured here |
| A_FULL | 72.47% | 1540 | measured here |
| **A_CDW_NOTS** | **71.56%** | 1540 | measured here |
| Mem0g | 68.44% | 1540 | arXiv:2504.19413 Table 2, not re-run here |
| Mem0 | 66.88% | 1540 | arXiv:2504.19413 Table 2, not re-run here |
| Zep | 65.99% | 1540 | arXiv:2504.19413 Table 2, not re-run here |
| OpenAI memory | 52.90% | 1540 | arXiv:2504.19413 Table 2, not re-run here |
| A-MEM | 48.38% | 1540 | arXiv:2504.19413 Table 2, not re-run here |
| A_RAG | 45.78% | 1540 | measured here |
| A_NONE | 26.30% | 1540 | measured here |

Five rows are the Mem0 authors' reproductions of other people's systems, not those systems' own reports.

## Paired contrasts

Item-level, against arms this run produced. No paired test is possible against an inherited row: their per-item answers were never published.

| Contrast | Endpoint | Delta | Gains | Losses | p (one-sided) |
|---|---|---:|---:|---:|---:|
| A_CDW vs A_RAG | llm_score | +33.31 | 558 | 45 | 6.61e-114 |
| A_CDW vs A_RAG | f1 | +24.16 | 433 | 61 | 1.95e-70 |
| A_CDW vs A_NONE | llm_score | +52.79 | 852 | 39 | 1.48e-200 |
| A_CDW vs A_NONE | f1 | +43.96 | 738 | 61 | 6.97e-149 |
| A_FULL vs A_CDW | llm_score | -6.62 | 108 | 210 | 1 |
| A_FULL vs A_CDW | f1 | -15.32 | 103 | 339 | 1 |
| A_CDW vs A_CDW_NOTS | llm_score | +7.53 | 185 | 69 | 1.02e-13 |
| A_CDW vs A_CDW_NOTS | f1 | +9.09 | 218 | 78 | 8.72e-17 |

## What each arm spent to answer

| Arm | Mean prompt tokens | Mean context chars | Units delivered | Median retrieval ms |
|---|---:|---:|---:|---:|
| A_FULL | 25,405 | 96,241 | 1.00 | 0.00 |
| A_CDW | 4,243 | 15,978 | 47.62 | 1.00 |
| A_CDW_NOTS | 3,696 | 15,987 | 60.30 | 0.90 |
| A_RAG | 570 | 1,838 | 1.00 | 193.20 |
| A_NONE | 84 | 0 | 0.00 | 0.00 |

## By question category

LoCoMo category 2 is temporal, 5 is adversarial and never scored.

| Arm | cat 1 | cat 2 | cat 3 | cat 4 |
|---|---|---|---|---|
| A_FULL | 67.4% | 49.5% | 55.2% | 84.9% |
| A_CDW | 71.6% | 68.5% | 55.2% | 88.3% |
| A_CDW_NOTS | 72.3% | 32.1% | 57.3% | 88.0% |
| A_RAG | 33.0% | 29.9% | 42.7% | 56.5% |
| A_NONE | 21.3% | 11.2% | 38.5% | 32.3% |

## Where the evidence sits

| Quartile | Depth | n | A_CDW | A_RAG | Delta |
|---|---|---:|---:|---:|---:|
| 1 | [0.0, 0.25] | 522 | 75.67% | 42.91% | +32.76 |
| 2 | [0.25, 0.5] | 350 | 78.00% | 47.43% | +30.57 |
| 3 | [0.5, 0.75] | 326 | 82.21% | 46.63% | +35.58 |
| 4 | [0.75, 1.0] | 333 | 82.28% | 47.15% | +35.14 |
