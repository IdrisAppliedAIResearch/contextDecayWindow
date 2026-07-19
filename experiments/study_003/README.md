# Study 003 — contextDecayWindow

**Idris Applied AI Research**

**Date:** July 2026

**Pre-registration commit:** `4c9003176d0130540ae1f257d5140c9daa919415`

**Accepted run:** `study_003_full_002`

**Status:** Complete — PARTIAL

## Summary

Study 003 tested whether the Study 002 consolidation and rule-detection failures could be corrected while preserving perfect targeted recall, and introduced an observational STM-to-LTM promotion write path. The accepted 120-turn iterative run passed two of three pre-registered success bars. Category 2 middle-plant recall remained perfect at 3.0/3.0, and topic count fell from Study 002's 52 to 1, passing the `<= 20` consolidation bar. Overall rubric performance was 12.0/13.0 rather than the required 13.0/13.0 because Q11, the full four-domain enumeration, omitted the Renaissance and monetary-policy domains. The result is therefore PARTIAL.

The LTM mechanism emitted exactly three promotion events at the scripted boundaries (turns 31, 61, and 91). It evaluated 90 STM episodes and promoted 21 unique episodes, for an overall rate of 23.33%. The LTM path remained write-only, as pre-registered.

## Research questions

1. Do the Study 002 architectural fixes restore and maintain its 13.0/13.0 iterative rubric score?
2. Does topic consolidation reduce the final topic count to 20 or fewer?
3. How does the four-filter STM-to-LTM promotion mechanism behave across a 120-turn, four-domain conversation?

## Changes from Study 002

| Component | Study 002 | Study 003 accepted run |
|---|---|---|
| Topic assignment representation | User + assistant episode embedding | User-message embedding |
| Assignment threshold | 0.50 | 0.45 |
| Consolidation threshold | 0.60 | 0.45 |
| Consolidation propagation | Existing implementation | In-memory topic mapping updated after merges |
| Rule detection | Model metadata tag only | Model tag plus conservative explicit-rule fallback |
| LTM | None | Four-filter promotion write path |
| Promotion trigger | N/A | Canonical topic transitions through turn 111 |
| LTM retrieval | None | None; deferred to Study 004 |

The transition-residence safeguard requires at least three episodes in an outgoing topic. Rubric turns 112–120 remain normal retrieval/storage turns but cannot emit promotion events because the locked protocol defines them as probes within the final scripted phase.

## Method

### Condition and script

The study ran only Condition C, Iterative Construction v3. It reused the locked Study 002 script: 120 turns spanning civil engineering, Renaissance art, monetary policy, and marine biology, with 30 scripted turns per domain. Planted facts occurred early (turns 3–5), middle (turns 55–60), and late (turns 100–110). Rubric probes occupied turns 112–120.

### Models and runtime

| Parameter | Actual run value |
|---|---|
| Inference model | Qwen3.6 27B NVFP4 |
| Inference server | Local llama.cpp HTTP server |
| Context capacity | 262,144 tokens |
| Hardware | NVIDIA RTX 5090 |
| Embedding model | Qwen3-Embedding-0.6B Q8_0 GGUF |
| Embedding dimensions | 1,024 |

The NVFP4 quantization/server configuration differs from the pre-registered Q6_K setup and is recorded in `protocol_deviation_nvfp4_server.md`.

### Evaluation sequence

The 13-question Study 002 rubric was reused without modification. Responses were scored before observational LTM analysis. The invalid first full run was not scored. The accepted retry completed 120 turns, persisted one opening rule, and emitted exactly the three expected promotion events.

## Results

### Rubric

| Category | Score |
|---|---:|
| Cat 1 — Early plant survival | 3.0 / 3.0 |
| Cat 2 — Middle plant survival | 3.0 / 3.0 |
| Cat 3 — Late plant survival | 2.0 / 2.0 |
| Cat 4 — Topic bleed | 2.0 / 3.0 |
| Cat 5 — Rule pinning | 2.0 / 2.0 |
| **Overall** | **12.0 / 13.0** |

Q1–Q10 and Q12–Q13 scored full credit. Q11 scored 0.0 because the response omitted the required Renaissance and monetary-policy values and entities and incorrectly stated that those domains had not been discussed.

### Success bars

| Bar | Criterion | Result | Outcome |
|---|---|---:|---|
| Bar 1 | Cat 2 >= 3.0 / 3.0 | 3.0 / 3.0 | Pass |
| Bar 2 | Overall >= 13.0 / 13.0 | 12.0 / 13.0 | Fail |
| Bar 3 | Topic count at turn 120 <= 20 | 1 | Pass |

**Overall result: PARTIAL (2 of 3 bars passed).**

### Consolidation

Consolidation ran every ten turns. Topic count remained aligned with the scripted domains through turn 110: one topic at turn 30, two at turn 60, three at turn 90, and four at turn 110. The turn-120 comprehensive query created a fifth topic and the final consolidation merged four pairs, reducing five topics to one. The final count passes Bar 3, but the last pass is an over-consolidation caveat: a cross-domain probe caused the four domain clusters to share one surviving topic identity.

### LTM promotion

| Outgoing domain | Evaluated | Promoted | Rate | Promotion route |
|---|---:|---:|---:|---|
| Civil engineering | 30 | 12 | 40.00% | 12 weighted-threshold |
| Renaissance art | 30 | 7 | 23.33% | 7 all-or-nothing |
| Monetary policy | 30 | 2 | 6.67% | 2 all-or-nothing |
| Marine biology | 0 | 0 | N/A | No outgoing transition |
| **Total** | **90** | **21** | **23.33%** | **12 weighted, 9 all-or-nothing** |

The final LTM store contained 21 rows with 21 distinct STM episode IDs. The STM-to-LTM ratio was 17.50% (21/120). Nine all-or-nothing promotions comprised seven novelty triggers and two repetition triggers. No association or emotional-valence score reached the all-or-nothing threshold.

Across all evaluated episodes, mean scores were 0.8707 novelty, 0.3578 repetition, 0.1293 association, 0.0728 emotional valence, and 0.4489 weighted score. Full distributions are recorded in the observational analysis report.

## Discussion

### Targeted recall remained strong; global enumeration did not

The iterative architecture retained perfect early, middle, and late targeted recall. Most importantly, Category 2 remained 3.0/3.0, preserving Study 002's primary result. The sole failure was the broad Q11 request to enumerate facts across all four domains.

The turn-120 retrieval record explains this split. Its 11 retrieved episodes came from turns 1–9, 114, and 119. No Renaissance-art or monetary-policy planting episode entered the constructed context, so the response had bridge and marine information but asserted that the other two domains were absent. Current retrieval works for semantically focused probes but does not guarantee coverage for a broad multi-domain query.

### Consolidation passed the count bar but became too aggressive at the final probe

The 0.45 consolidation threshold corrected Study 002's topic proliferation. Before the comprehensive probe, topic growth closely followed the four scripted domains. At turn 120, however, four merges collapsed five topics into one at similarities from 0.45 to 0.54. The topic-count bar measures upper-bounded fragmentation and therefore passes, but count alone does not detect domain collapse. Study 004 should track both maximum topic count and cross-domain merge purity.

### Promotion routes changed as LTM accumulated

Civil engineering had the highest promotion rate (40.00%) and all 12 promotions used the weighted threshold. This matches the pre-registered empty-LTM behavior: novelty defaults to 1.0, association to 0.0, and novelty cannot invoke the all-or-nothing exception in the first batch. Repetition therefore supplied the additional weight needed for promotion.

Renaissance art promoted 23.33% and monetary policy 6.67%, entirely through all-or-nothing triggers. Seven of those nine events were novelty-triggered and two repetition-triggered. Batch mean novelty declined from 1.0000 for civil engineering to 0.8424 for Renaissance art and 0.7697 for monetary policy while mean association rose from 0.0000 to 0.1576 and 0.2303. These measurements account for the observed rate ordering without requiring an emotional-valence explanation; emotional scores remained low in the technical script.

### Implications for the Study 004 LTM read path

The promoted set is selective—21 of 120 episodes—but its composition is route-dependent. The first batch consists of weighted-threshold promotions, while later batches are dominated by novelty exceptions. Study 004 should preserve trigger metadata during retrieval, deduplicate episodes that remain in both STM and LTM, and report retrieval coverage by scripted domain. A single global similarity threshold should be calibrated against the observed promoted set before it is used to construct context; this study did not test an LTM retrieval threshold.

The Q11 failure establishes a concrete read-path requirement: broad queries need domain coverage, not only the highest individual similarity or recency scores. The read path should be evaluated on whether it restores Renaissance and monetary-policy evidence to a turn-120-style comprehensive query without introducing topic bleed.

### Trigger behavior and guard activity

The accepted run produced exactly three events at turns 31, 61, and 91. There were zero logged merge-relabel guard events and no promotion during turns 112–120. Thus, the accepted run exercised the genuine transition path but did not produce a positive merge-relabel guard case. The invalid first run exposed the probe-boundary mismatch; Amendment 004 corrected it before the accepted retry.

## What I would do differently

1. Add a pre-run test covering late probes that revisit prior domains, not only the first 35-turn boundary.
2. Evaluate consolidation purity alongside topic count so an over-merged one-topic result cannot look unambiguously better than four clean topics.
3. Include a deterministic metadata channel or constrained grammar for rule detection instead of relying on an optional free-form tag.
4. Add a retrieval-coverage metric for broad queries, partitioned by scripted domain.
5. Replicate the accepted run before treating a one-question difference as stable.

## Protocol notes

- The pre-registered Q6_K model was replaced by a locally served Qwen3.6 27B NVFP4 model with a 262,144-token context.
- Three 35-turn remediation ablations were required before the full run was authorized.
- `study_003_full_001` completed but was invalidated before scoring because it emitted six rather than three promotion events and persisted no rule.
- Amendment 004 excluded the pre-declared rubric-probe block from promotion and added a conservative explicit persistent-rule fallback.
- `study_003_full_002` completed all 120 turns, persisted one rule, and emitted exactly three promotion events.
- Peak constructed context was 9,189 estimated tokens at turn 80.
- The score parser's Q10–Q13 substring bug was fixed during scoring; the score file now parses all 13 keys correctly.

## Limitations

- One accepted run and one rater; no replication or inter-rater reliability.
- One model family, one quantization, and one local hardware/runtime configuration.
- Scripted, cleanly partitioned domains do not represent natural blended conversations.
- The model/runtime deviation prevents a same-quantization comparison with Study 002.
- LTM was write-only, so no causal claim can be made about LTM improving recall.
- Marine biology had no outgoing transition and was not evaluated for promotion.
- The merge-relabel guard logged no positive case in the accepted full run.
- Final topic count hides a cross-domain over-merge at turn 120.
- Q11's failure may be run-specific; no replicate estimates its variance.

## Next steps: Study 004

The primary architectural addition is the **LTM retrieval read path**. Study 004 should retrieve from the 21-episode promoted store, deduplicate STM/LTM overlap, preserve promotion metadata, and evaluate both targeted recall and broad cross-domain coverage. It should also add topic-purity checks, a positive merge-relabel guard test, and explicit handling for end-of-session promotion of the final active topic.

Study 004 has not yet been pre-registered.

## Appendix: artifacts

- Pre-registration: `experiments/study_003/pre_registration.md`
- Sprint plan: `sprint-specs/study_003_sprint_plan.md`
- Script: `experiments/study_003/script.json`
- Authoritative rubric: `experiments/study_002/rubric_filled.md`
- Accepted rubric responses: `experiments/study_003/runs/run_001/condition_c/rubric/responses.md`
- Accepted rubric scores: `experiments/study_003/runs/run_001/condition_c/rubric/scores.md`
- Success bars: `experiments/study_003/runs/run_001/condition_c/rubric/success_bars.md`
- LTM observational report: `experiments/study_003/runs/run_001/ltm_analysis/analysis_report.md`
- Canonical run notes: `experiments/study_003/runs/run_001/run_notes.md`
- Condition C metrics: `experiments/study_003/runs/run_001/condition_c/metrics/`
- Ablation report: `experiments/study_003/ablation/ablation_report.md`
- Invalid-run deviation: `experiments/study_003/protocol_deviation_full_001.md`
- Runtime deviation: `experiments/study_003/protocol_deviation_nvfp4_server.md`
- Amendments: `experiments/study_003/protocol_amendment_001_ablation_remediation.md` through `protocol_amendment_004_probe_boundary_and_rule_fallback.md`
- Consolidation decision: `experiments/study_003/decisions/DECISION_consolidation_threshold_study003.md`
