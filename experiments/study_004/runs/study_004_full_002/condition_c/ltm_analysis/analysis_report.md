# Study 004 A005 — Arbitration and LTM Observational Analysis

**Run:** `study_004_full_002`

**Condition:** Condition C v4 (`iterative`)

**Sequence:** The rubric was locked at commit `8e097c0` before this analysis
opened probe-turn arbitration or provenance content.

**Scope:** Pre-registered observational measures. Confirmatory bar outcomes are
recorded separately in `rubric/success_bars.md`.

## Run integrity

| Measure | Result |
|---|---:|
| Completed turns | 121 |
| Turn / performance / context-size / arbitration rows | 121 / 121 / 121 / 121 |
| Root response entries | 121 |
| Empty responses / 2,048-token caps | 0 / 0 |
| Maximum response | 1,393 tokens |
| Peak constructed context | 11,376 estimated tokens at turn 116 |
| Final topic count | 5 |
| Promotion events | 4 (31, 61, 91, 111) |
| LTM rows at run end | 12 unique episode IDs |
| Cross-domain consolidation events | 0 |

No assistant response contained a literal v4 context tag, rule-detection tag,
or residual thinking tag.

## Arbitration contribution and overlap

LTM became available after the turn-31 transition. It contributed at least one
episode to every subsequent context.

| Measure | Result |
|---|---:|
| Turns with ≥1 LTM-provenance final episode | 90 / 121 (74.38%) |
| Eligible turns with LTM contribution (turns 32–121) | 90 / 90 (100.00%) |
| LTM candidates across all turns | 450 |
| LTM-or-both episodes in final arbitration sets | 450 |
| Duplicates removed | 1 |
| Aggregate dedup rate | 1 / 450 (0.22%) |
| Turns with tier overlap | 1 (turn 116) |
| Candidate-displacement turns | 0 |

Turn 116 was the sole overlap: episode turn 35 appeared in both tiers and was
emitted once with `both` provenance. On every turn, final-set size equaled
`stm_candidates + ltm_candidates - duplicates_removed`; no unique candidate was
dropped by the arbitration cap. Therefore no LTM episode displaced a
next-ranked active-topic STM candidate.

The arbitration-union provenance profile (the separate recency/N block is not
part of this profile) was:

| Provenance | Episodes | Share |
|---|---:|---:|
| STM | 23 | 4.86% |
| LTM | 449 | 94.93% |
| Both | 1 | 0.21% |
| **Total** | **473** | **100.00%** |

Correctness checks found zero provenance-count mismatches, zero LTM row-count
mismatches, zero duplicate final IDs, and zero turns where a unique candidate
was silently dropped.

## Breadth-turn retrieval anatomy

### Q11 — turn 120

The one STM arbitration candidate was turn 114 (rule recall), similarity
0.500125. The five LTM candidates/final episodes were:

| Episode turn | Content | Similarity | Promoted | Route |
|---:|---|---:|---:|---|
| 1 | Behavioral rules | 0.497029 | 31 | weighted threshold |
| 2 | Behavioral-rule confirmation | 0.463740 | 31 | weighted threshold |
| 3 | Halcyon Crossing plant | 0.315660 | 31 | weighted threshold |
| 35 | Generic egg-tempera versus oil discussion | 0.274867 | 61 | repetition bypass |
| 76 | Generic adaptive/rational-expectations discussion | 0.238818 | 91 | repetition bypass |

The recency/N block contained turns 119 and 4–9. Thus Q11 had extensive bridge
material, a recent marine answer, and generic art/economics material, but no
planted art turns 55–56, monetary turns 61/62/65, or marine turns 100–102 from
LTM. The response consequently looked broad while remaining far below the
locked planted-fact key.

### Q14 — turn 121

There were no STM arbitration candidates. The five LTM candidates/final
episodes were:

| Episode turn | Content | Similarity | Promoted | Route |
|---:|---|---:|---:|---|
| 1 | Behavioral rules | 0.442600 | 31 | weighted threshold |
| 2 | Behavioral-rule confirmation | 0.421992 | 31 | weighted threshold |
| 3 | Halcyon Crossing plant | 0.242500 | 31 | weighted threshold |
| 76 | Generic adaptive/rational-expectations discussion | 0.182654 | 91 | repetition bypass |
| 8 | Bridge cable-fatigue discussion | 0.169921 | 31 | weighted threshold |

The recency/N block contained turn 120 plus bridge turns 4–7 and 9. The Q14
answer's art and marine details were therefore inherited from the preceding
Q11 response, not recovered from planted LTM episodes. No planted Renaissance
episode reached Q14, and no planted monetary or marine episode reached it via
LTM.

Both breadth turns contained five LTM-provenance episodes, so the read path
engaged. The promoted set, rather than the query execution, lacked the facts
needed by the rubric.

## Promotion volume and store composition

| Outgoing scripted domain | Event | Evaluated | Promoted | Rate | Route composition |
|---|---:|---:|---:|---:|---|
| Civil engineering | 31 | 30 | 9 | 30.00% | 9 weighted |
| Renaissance art | 61 | 30 | 1 | 3.33% | 1 repetition bypass |
| Monetary policy | 91 | 30 | 1 | 3.33% | 1 repetition bypass |
| Marine biology (flush) | 111 | 21 | 1 | 4.76% | 1 novelty bypass |
| **Total** | — | **111** | **12** | **10.81%** | **9 weighted, 3 bypass** |

Final LTM composition was nine civil episodes (turns 1–9), one generic art
episode (35), one generic monetary episode (76), and one generic marine episode
(109). Each scripted domain was represented, but the later-domain planted
facts were not.

Critical selectivity examples:

| Domain | Planted turns and weighted scores | Promoted generic turn |
|---|---|---|
| Art | 55: 0.384445; 56: 0.361749 — neither promoted | 35: 0.631861 via repetition bypass |
| Monetary | 61: 0.384169; 62: 0.381790; 65: 0.372961 — none promoted | 76: 0.607085 via repetition bypass |
| Marine | 100: 0.380338; 101: 0.496761; 102: 0.438554 — none promoted | 109: 0.421938 via novelty bypass |

## Turn-111 flush behavior

The flush executed before turn 112, evaluated all 21 marine-domain episodes,
and promoted one. This retires Study 003's structural exclusion of the final
domain. The selected episode was turn 109, triggered by novelty 0.916769; the
three planted marine episodes at turns 100–102 remained below both routes.

The flush mechanism therefore ran as designed, while its filter selectivity did
not retain the rubric-critical marine facts.

## Revised weighted-route activity

| Event | Evaluated | Weighted triggers | Bypass triggers | A differs from global A |
|---:|---:|---:|---:|---:|
| 31 | 30 | 9 | 0 | 0 / 30 (empty LTM) |
| 61 | 30 | 0 | 1 | 0 / 30 (single-topic degeneracy) |
| 91 | 30 | 0 | 1 | 30 / 30 |
| 111 | 21 | 0 | 1 | 21 / 21 |

Association decoupling took structural effect in both eligible multi-topic
batches: mean absolute `association - global_association` was 0.009251 at turn
91 and 0.013943 at turn 111. It did not produce a unique weighted-route
promotion. The turn-76 item at event 91 exceeded 0.60 but was classified through
the repetition bypass; all other post-decoupling items stayed below 0.60.

## Targeted-probe context comparison with the v3 control

The same-settings v3 control retrieved planted episode 55 for Q4/Q5/Q6 and
episode 100 for Q7. The v4 contexts did not contain those plants:

| Probe | v3 control relevant K turns | v4 relevant context |
|---|---|---|
| Q4 (turn 115) | 55, 59 | No planted art turn; generic LTM turn 35 |
| Q5 (turn 116) | 55, 59 | K turns 39/57 plus generic/both turn 35; planted turn 56 absent |
| Q6 (turn 117) | 55, 59, 60 | Prior wrong answer 115 and generic turn 39; planted patron turns absent |
| Q7/Q10 (turn 118) | 100 | No planted marine turn and no marine LTM candidate |

There were no arbitration displacement events. The observed regression is
therefore associated with candidate coverage and context composition, not an
LTM episode replacing an already-qualified STM candidate. Because A005's
control compares the v3 implementation against the joint v4 read-path/tagging
bundle, and generation is stochastic, this single pair cannot apportion the
coverage change between tagging-mediated episode content, threshold crossings,
and read-path context effects.

## Latency delta

The pre-registered per-turn context-construction wall time was not emitted by
the runner. `model_performance.csv` measures inference generation only, so it
cannot supply the requested STM/LTM parallel-query delta. End-to-end runtime
was 44m54s versus 34m33s for the same-settings control, but v4 generated 95,170
tokens versus 75,102; that duration difference is not interpreted as retrieval
latency. The omission is recorded in
`protocol_deviation_full_002_context_latency_not_instrumented.md`.

## Source artifacts

- `logs/arbitration_events.csv`
- `logs/ltm_context_episodes.csv`
- `logs/consolidation_purity.csv`
- `ltm_analysis/promotion_events.csv`
- `ltm_analysis/episode_scores.csv`
- `metrics/context_sizes.csv`
- `metrics/consolidation_events.csv`
- preserved raw `logs/turns.jsonl` and constructed prompts
