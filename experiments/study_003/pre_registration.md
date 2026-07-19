# Study 003 — Pre-Registration
## contextDecayWindow
**Idris Applied AI Research**
**Date:** July 2026
**Status:** Pre-registered — commit SHA pending
**Study 002 SHA:** 0a87fb1
**Preceding decision record:** DECISION_consolidation_threshold_study003.md
**Revision note:** v2 — pre-commit review revisions (trigger sequencing corrected, merge-relabel guard added, boundary conditions aligned). No design changes to filters, weights, bars, or scope.

---

## Summary

Study 003 introduces the first component of the brain pipeline target architecture: a two-tier memory system with an active STM → LTM promotion mechanism. Promotion fires at every topic change, evaluating outgoing STM episodes against four biologically-grounded filters (Novelty, Repetition, Association, Emotional Valence) using a weighted threshold. The LTM store is write-path only in this study — promoted episodes are stored and analyzed but not yet used for context construction. LTM retrieval is deferred to a future study.

Alongside the new component, Study 003 corrects the two architectural failures documented in Study 002: topic consolidation (52 topics, failure threshold > 20) and the rule detection system prompt confound.

The comparison baseline changes from Study 002. Compaction and full-context conditions are retired — both are empirically settled after Studies 001 and 002. From Study 003 onward, progress is measured by self-comparison: Study 003 Condition C vs Study 002 Condition C (13.0/13.0 overall, 3.0/3.0 Cat 2).

---

## Research Questions

**Primary:** Do the Study 002 architectural fixes (consolidation threshold, propagation bug, rule detection) restore and maintain Study 002's perfect rubric score (13.0/13.0) without regression?

**Secondary (observational):** How does the STM → LTM promotion mechanism behave under a 120-turn, four-topic conversation? Which filters trigger most frequently? What proportion of STM episodes are promoted per topic?

---

## Retired Conditions — Rationale

Condition A (full context loading) and Condition B (summarization compaction) are retired after Study 002.

**Full context:** Lost-in-the-middle attention degradation confirmed. Speed degraded from 58 → 11 tok/s as context grew to 132k tokens. KV cache pressure hypothesis confirmed. No new information would be produced by repeating this condition.

**Compaction:** Catastrophic forgetting confirmed across both studies. Study 001: 3.5/10.0. Study 002: 2.0/13.0 with 36 zero-token output turns including 16 consecutive turns. No new information would be produced by repeating this condition.

From Study 003 onward, the iterative architecture is developed against its own prior performance. Each study's Condition C is the floor the next study must meet or exceed.

---

## Changes from Study 002

| Parameter | Study 002 | Study 003 | Reason |
|-----------|-----------|-----------|--------|
| Merge threshold | 0.60 | 0.45 | Never fired in Study 002 — centroids too granular at 0.50 assignment threshold |
| Propagation bug | Present | Fixed (one line, runner.py) | Consolidation passes ran but results never recorded |
| Rule detection | Via system prompt | Via detection mechanism only | System prompt pre-loads rules, preventing detection signal in Condition C |
| LTM store | None | Active (write path) | First brain pipeline component — promotion fires, retrieval deferred |
| Baseline conditions | Conditions A + B | Retired | Empirically settled — see rationale above |
| Comparison baseline | Study 002 Condition A | Study 002 Condition C | Self-comparison model adopted Study 003 onward |

**Note on Study 002's Bar 2 (token efficiency):** Study 002's "C < A every turn" criterion failed on two negligible violations (59 tokens; rule-detection overhead). The calibration lesson — success criteria must include a meaningful violation margin — is recorded here as a standing methodology lesson. With baseline conditions retired, Study 003 carries no token-efficiency bar. Per-turn context token counts are still logged for observational continuity.

---

## Method

### Condition

**Condition C — Iterative Construction v3**

Active context constructed dynamically per turn from STM episodic memory store. Same N+K retrieval architecture as Study 002 with the following changes applied: merge threshold 0.45, propagation bug patched, rule detection without system prompt pre-load, LTM write path active.

### Model

| Parameter | Value |
|-----------|-------|
| Inference model | Qwen3.6 27B Q6_K |
| Runtime | llama.cpp |
| Hardware | RTX 5090 32GB VRAM |
| Context cap | 147,000 tokens |
| Embedding model | Qwen3-Embedding-0.6B |
| Embedding dimensions | 1,024 |

### Script

Same 120-turn script as Study 002. Four semantically unrelated topics (civil engineering, Renaissance art history, monetary policy, marine biology), 30 turns each with abrupt switches. Three planted fact positions: early (turns 3–5), middle (turns 55–60), late (turns 100–110). Late-session probes at turns 112–120.

Reusing Study 002's script eliminates script variance as a confound. Score differences between studies are attributable to architectural changes only.

### Evaluation

Same 13-question rubric as Study 002 across 5 categories, scored manually before analysis. Scoring criteria are defined in `experiments/study_002/rubric_filled.md` and are used unmodified.

| Category | Questions | Tests |
|----------|-----------|-------|
| Cat 1 | Q1–Q3 | Early plant survival |
| Cat 2 | Q4–Q6 | Middle plant survival |
| Cat 3 | Q7–Q8 | Late plant survival |
| Cat 4 | Q9–Q11 | Topic bleed |
| Cat 5 | Q12–Q13 | Rule pinning |

---

## STM → LTM Promotion Architecture

### Trigger

**Definition.** A topic change is a genuine topic transition detected at the consolidated-topic level — not a raw per-episode assignment change. With four scripted topics across 120 turns, promotion fires exactly three times (at the boundaries between topics, approximately turns 31, 61, and 91). This prevents micro-reassignments within the same conversation domain from triggering spurious promotions.

**Sequencing.** Topic change cannot be detected until the first episode of the new topic has been stored and consolidated — the detection compares the current episode's consolidated topic against the previous episode's. Therefore promotion fires immediately *after* the first episode of the incoming topic is stored and its consolidation pass completes. At that point, all STM episodes belonging to the outgoing consolidated topic are evaluated against the four filters. The incoming topic's first episode is excluded from the outgoing batch.

**Merge-relabel guard.** Topic consolidation can rename or merge consolidated topic labels. A label change caused by consolidation relabeling the *previous* episodes' topic (a merge event) is not a topic transition and must not fire promotion. The trigger fires only when the current episode is assigned to a different underlying topic cluster than the previous episode — i.e., the previous episode's topic (under its current, post-merge label) differs from the current episode's topic. Implementation detail: resolve both episodes' topics through the consolidation mapping to their canonical cluster identity before comparing. A comparison on raw label strings is insufficient once merges are active. This guard is newly relevant in Study 003 because the 0.45 threshold is expected to make merges fire for the first time.

**Last topic limitation.** The final topic (marine biology, turns 91–120) has no subsequent topic change and its episodes are never evaluated for LTM promotion. Three of four topics are evaluated. Marine biology will show zero LTM promotions in the observational data — this is a structural property of the trigger design, not a failure condition. The observational measure "Promotion count per topic" will reflect this. Study 004 should address end-of-session promotion via either a final promotion pass at run end or a turn-based fallback for the active topic.

### Filters

| Filter | Method | Score (0.0–1.0) |
|--------|--------|-----------------|
| Novelty | 1 - cosine_similarity(episode_embedding, LTM_centroid) | High distance from LTM = high novelty |
| Repetition | normalize(retrieval_count, max=5) | Retrieval count is scoped to the episode's home topic window — retrievals occurring while the episode's assigned consolidated topic was active. 5+ retrievals within that window = 1.0 |
| Association | cosine_similarity(episode_embedding, LTM_centroid) | High similarity to LTM = strong association |
| Emotional Valence | LLM scoring call | "Does this episode contain emotionally significant content?" |

**Empty LTM behavior:** When the LTM store has no centroid (start of study, before first topic change), all episodes receive maximum novelty score (1.0) and association score 0.0. The all-or-nothing exception is suspended when LTM is empty — a novelty score of 1.0 under these conditions reflects a structural default, not a high-intensity encoding event, and should not bypass the weighted threshold. First-topic episodes are evaluated via the weighted threshold only: weighted_score = (0.35 × 1.0) + (0.30 × repetition) + (0.20 × 0.0) + (0.15 × emotional) = 0.35 + (0.30 × repetition) + (0.15 × emotional). An episode with zero repetition and zero emotional valence scores 0.35 — below the 0.60 promotion threshold and not promoted. Promotion of first-topic episodes requires meaningful repetition or emotional content in addition to the default novelty.

**Emotional Valence suspension scope:** the empty-LTM suspension applies to the all-or-nothing bypass for *all* filters, including a hypothetical 0.90+ emotional score on a first-topic episode. Suspension is a property of the store state, not the filter. This keeps the first-batch rule simple and uniform; if the observational data suggests genuinely high-intensity first-topic content is being missed, Study 004 can revisit.

**Novelty and Association independence:** Both filters use the LTM centroid but pull in opposite directions. They are treated as independent gates — high scores on both are possible and valid. A highly novel episode that also happens to connect to an existing LTM pattern scores well on both.

**Post-promotion STM residency:** Promoted episodes remain in the STM store after promotion and continue to participate in N and K retrieval normally through Study 003. They are not removed from STM at promotion time. Study 004's LTM retrieval design should account for potential double-retrieval of promoted episodes if both STM and LTM retrieval are active simultaneously.

### Promotion Logic

**All-or-nothing exception:** If any single filter score >= 0.90 and the LTM store is non-empty, the episode is promoted immediately regardless of other filter scores. Represents high-intensity events that encode without reinforcement.

**Standard weighted threshold:**
```
weighted_score = (0.35 × novelty) + (0.30 × repetition) + (0.20 × association) + (0.15 × emotional_valence)
if weighted_score >= 0.60 → promote
```

**Centroid update policy:** The LTM centroid is computed once at the start of each topic change evaluation and held fixed for the duration of that batch. All episodes in the batch are scored against the same centroid snapshot. The centroid is updated after all promotions from the batch are written to the LTM store. This prevents intra-batch feedback where early-promoted episodes would shift the centroid for later episodes in the same evaluation pass.

### LTM Schema

Each promoted episode is written to the LTM store with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| episode_id | str | Foreign key to STM episode |
| promoted_at_turn | int | Turn number when promotion fired |
| topic | str | Consolidated topic label at time of promotion |
| trigger_type | str | "all_or_nothing" or "weighted_threshold" |
| novelty_score | float | Filter score at promotion time |
| repetition_score | float | Filter score at promotion time |
| association_score | float | Filter score at promotion time |
| emotional_score | float | Filter score at promotion time |
| weighted_score | float | Final weighted score |
| triggered_filter | str | Filter that triggered (all_or_nothing only) |
| embedding | vector | Episode embedding (1024 dims) |
| content | str | Full episode content |
| timestamp | datetime | Wall clock at promotion |

---

## Success Criteria

Three pre-registered success bars. All three must pass for Study 003 to be rated VALIDATED.

### Bar 1 — Middle Plant Survival (Non-Regression)
**Condition C Cat 2 score >= Study 002 Condition C Cat 2 score**
- Study 002 baseline: 3.0/3.0
- Rationale: Middle plant survival was the primary finding of Study 002. Architectural changes must not regress this result.

### Bar 2 — Overall Rubric (Non-Regression)
**Condition C overall rubric score >= Study 002 Condition C overall rubric score**
- Study 002 baseline: 13.0/13.0
- Rationale: Study 002 achieved a perfect score. This is a non-regression bar — architectural changes (consolidation, rule detection, LTM write path) must not degrade retrieval quality.
- **Caveat:** Study 003 removes formatting rules from the system prompt and relies on the detection mechanism for Cat 5 scoring. A detection miss at Turn 1 could reduce Cat 5 from 2/2 to 1/2, yielding 12.0/13.0 and failing this bar. If Bar 2 fails, the failure must be analyzed by category: a Cat 5-only failure indicates rule detection variance and does not constitute retrieval regression in Cat 1–4. A failure in Cat 1–4 constitutes architectural regression and should be treated as a study failure.

### Bar 3 — Consolidation Fix Verified
**Final topic count ≤ 20 at turn 120**
- Study 002 result: 52 topics
- Rationale: The 0.45 merge threshold change is the primary structural fix of Study 003. This bar confirms the fix works.
- Boundary: exactly 20 topics passes. The corresponding failure condition is topic count > 20 — the bar and the failure condition partition all outcomes with no gap.

---

## Observational Measures — LTM Promotion (No Pass/Fail)

The LTM write path is new territory. No success bar is pre-registered for this component. The following measures are pre-registered for observation and analysis. Findings will inform Study 004's LTM retrieval design.

| Measure | Description |
|---------|-------------|
| Promotion count per topic | How many episodes from each of the four topics were promoted |
| Filter score distributions | Histogram of each filter's scores across all evaluated episodes |
| Trigger frequency by filter | How often each filter was the primary trigger (all-or-nothing events) |
| Weighted score distribution | Distribution of weighted scores for promoted vs non-promoted episodes |
| LTM store size at run end | Total episodes in LTM at turn 120 |
| STM → LTM ratio | Proportion of STM episodes that were promoted |
| Topic change promotion timing | Which topic changes produced the most promotions |
| Merge-relabel events | Count of consolidation label changes correctly ignored by the trigger guard (verifies the guard; expected ≥ 0) |

**Interpretive scope note:** Study 003 tests whether this *class* of promotion mechanism produces sensible, analyzable behavior — not whether the specific pre-registered weights are correct. The weights encode an ordering derived from the neuroscience grounding; the numeric values are design choices. Observational findings (e.g., a filter contributing little under this script) will be interpreted with the script's properties in mind — a flat emotional profile in a scripted technical conversation is a property of the script, not evidence against the filter.

---

## Pre-Run Checklist (Mandatory)

The following checks must pass before the full 120-turn run is initiated. No exceptions.

- [ ] CUDA PATH set permanently in system environment variables
- [ ] GPU speed test returns > 30 tok/s
- [ ] Run minimum 35-turn ablation (35 turns required to reach first topic change ≈ turn 31 and verify LTM promotion)
- [ ] Ablation: consolidation fires at least once
- [ ] Ablation: topic count trending toward ≤ 20 pace (no singleton proliferation)
- [ ] Ablation: no cross-domain merges in consolidation log
- [ ] Ablation: LTM promotion fires at first topic change
- [ ] Ablation: no spurious promotion fires on consolidation merge/relabel events (trigger guard verified)
- [ ] Ablation: LTM schema writes correctly (inspect DB — all fields populated)
- [ ] Ablation: rule detection fires without system prompt pre-load
- [ ] Propagation bug fix confirmed (consolidation_events.csv has rows after ablation)

If any check fails, stop. Diagnose and fix before proceeding.

---

## Failure Conditions

| Condition | Meaning | Next action |
|-----------|---------|-------------|
| Topic count > 20 at turn 120 | 0.45 threshold still insufficient | Try raising assignment threshold to 0.60 (Option B — deferred from Study 003 design) |
| Bar 1 or Bar 2 fail in Cat 1–4 (rubric regression) | Architectural changes degraded retrieval | Isolate which change caused regression via ablation |
| LTM promotion never fires | Topic change trigger broken | Diagnose topic detection mechanism |
| Promotion fires on a merge/relabel event | Trigger guard broken | Fix cluster-identity resolution, re-run ablation |
| Cross-domain merges in consolidation log | 0.45 threshold too permissive | Raise to 0.50, re-run ablation |

---

## Sprint Plan

| Sprint | Scope |
|--------|-------|
| S3_001 | Pre-registration commit. Propagation bug fix. Rule detection system prompt removal. |
| S3_002 | Consolidation threshold change (0.45). Runner.py updates. |
| S3_003 | LTM schema design and DB migration. |
| S3_004 | Promotion mechanism implementation (four filters, scoring logic, topic-change trigger with merge-relabel guard, synthetic-script trigger test). |
| S3_005 | Pre-run 35-turn ablation. Checklist verification. Go/no-go decision. |
| S3_006 | Full 120-turn run. |
| S3_007 | Rubric scoring. Observational LTM analysis. |
| S3_008 | Results write-up. Study 003 report. Memory file updates. |

---

## Limitations

**Single run, single rater.** Results reflect one run of the 120-turn script scored by a single rater. No inter-rater reliability check. Score differences of one question between studies may reflect run-specific variance rather than architectural change.

**Self-comparison baseline variance.** Study 002 Condition C scored 13.0/13.0 in a single run. With temperature > 0, a second run of Study 002's identical architecture may not reproduce exactly 13.0/13.0. The 13.0/13.0 floor carries run-specific uncertainty. A one-question difference (12.0/13.0) in Study 003 may reflect stochastic inference behavior rather than architectural regression.

**Weights are design choices, not measured quantities.** The filter weights encode a plausibility ordering from the neuroscience grounding; the numeric values are not empirically derived. This study characterizes the mechanism's behavior under these weights; it does not validate the weights themselves.

**Scripted conversation.** All findings are conditional on a scripted, cleanly-partitioned four-topic conversation with planted probe targets. Naturalistic conversations with blended topics and unannounced salient facts are out of scope for this study and remain an open validity question for the track.

**Emotional valence LLM call overhead.** The emotional valence filter requires one inference call per evaluated episode. At three topic changes × ~30 episodes per topic, this adds approximately 90 additional inference calls to the run at promotion time. These calls use the same inference model (Qwen3.6 27B Q6_K) and queue through the same asyncio.Lock as conversation turns. Wall-clock run time is extended accordingly. This does not affect result validity but should be noted in protocol.

**Last topic not evaluated for promotion.** Marine biology (turns 91–120) produces zero LTM promotions by structural design — see Trigger section. This limits the observational dataset to three of four topics.

**LTM retrieval inactive.** The LTM store accumulates promoted episodes but they are not used in context construction. Rubric scores reflect STM architecture only. The value of LTM write-path behavior cannot be evaluated on retrieval quality until Study 004.

---

## Appendix

- Study 002 pre-registration: `experiments/study_002/pre_registration.md`
- Study 002 SHA: 0a87fb1
- Consolidation threshold decision record: `DECISION_consolidation_threshold_study003.md`
- Script (reused from Study 002): `experiments/study_002/script.json`
- Rubric criteria (authoritative): `experiments/study_002/rubric_filled.md`
- Pre-registration path: `experiments/study_003/pre_registration.md`
