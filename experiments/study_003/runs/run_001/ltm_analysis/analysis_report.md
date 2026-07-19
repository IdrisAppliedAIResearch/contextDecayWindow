# Study 003 LTM Observational Analysis

**Run:** `study_003_full_002`

**Condition:** iterative

**Scope:** Pre-specified observational measures from Sprint S3_007. This report records measurements without interpreting them as pass/fail.

## Run integrity

| Measure | Result |
|---|---:|
| Completed turns | 120 |
| STM episodes | 120 |
| Final topic count | 1 |
| Persisted rules | 1 |
| Promotion events | 3 |
| Promotion event turns | 31, 61, 91 |
| Consolidation passes | 12 (turns 10–120, every 10 turns) |
| Peak constructed context | 9,189 estimated tokens at turn 80 |

## Promotion volume

The scripted domain corresponding to each event is determined by its fixed boundary turn. Database topic labels are reported parenthetically; consolidation reused `topic_2` as the surviving label for the first two outgoing domains.

| Outgoing scripted domain | Event turn | Stored topic label | Evaluated | Promoted | Rate |
|---|---:|---|---:|---:|---:|
| Civil engineering | 31 | `topic_2` | 30 | 12 | 40.00% |
| Renaissance art | 61 | `topic_2` | 30 | 7 | 23.33% |
| Monetary policy | 91 | `topic_3` | 30 | 2 | 6.67% |
| Marine biology | None | N/A | 0 | 0 | N/A |
| **Total** | — | — | **90** | **21** | **23.33%** |

Marine biology has no outgoing transition under the pre-registered design and therefore receives no promotion evaluation.

## Filter-score distributions

All 90 evaluated episode rows are included.

| Filter or score | Minimum | Maximum | Mean | Median |
|---|---:|---:|---:|---:|
| Novelty | 0.6541 | 1.0000 | 0.8707 | 0.8414 |
| Repetition | 0.2000 | 1.0000 | 0.3578 | 0.2000 |
| Association | 0.0000 | 0.3459 | 0.1293 | 0.1586 |
| Emotional valence | 0.0000 | 0.2000 | 0.0728 | 0.1000 |
| Weighted score | 0.3655 | 0.6650 | 0.4489 | 0.4100 |

## Promotion trigger behavior

| Trigger route | Promoted episodes | Share of promotions |
|---|---:|---:|
| Weighted threshold | 12 | 57.14% |
| All-or-nothing | 9 | 42.86% |
| **Total** | **21** | **100.00%** |

All-or-nothing filter frequency:

| Triggered filter | Count | Share of all-or-nothing promotions |
|---|---:|---:|
| Novelty | 7 | 77.78% |
| Repetition | 2 | 22.22% |
| Association | 0 | 0.00% |
| Emotional valence | 0 | 0.00% |

Novelty is the most frequent all-or-nothing trigger.

## Transition guard

| Measure | Result |
|---|---:|
| Logged merge-relabel events ignored by the guard | 0 |
| Promotion events observed | 3 |
| Genuine scripted transitions expected | 3 |
| Event turns match expected boundaries | Yes — 31, 61, 91 |

No merge-relabel comparison met the guard-log condition during the eligible promotion window. No promotion event occurred during the turn 112–120 rubric-probe block.

## LTM store at run end

| Measure | Result |
|---|---:|
| LTM rows | 21 |
| Distinct promoted STM episode IDs | 21 |
| Duplicate promoted episode IDs | 0 |
| STM → LTM ratio | 21 / 120 (17.50%) |
| Highest promotion rate | Civil engineering (40.00%) |
| Lowest evaluated-domain promotion rate | Monetary policy (6.67%) |
| Lowest rate including structurally unevaluated domain | Marine biology (0 promoted; rate N/A) |

## Source artifacts

- `promotion_events.csv`: event volume and rates
- `episode_scores.csv`: filter and weighted-score distributions
- `filter_triggers.csv`: trigger route and all-or-nothing filter counts
- `merge_relabel_events.csv`: transition-guard event count
- `study.db`: STM, topic, rule, LTM, and promotion-log row counts
- `logs/turns.jsonl`: turn count, context peak, final topic count, and consolidation turns
