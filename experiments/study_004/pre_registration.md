# Study 004 — Pre-Registration (DRAFT v1)
## contextDecayWindow
**Idris Applied AI Research**
**Date:** July 2026
**Status:** LOCKED. Q14 authored; Study 003 SHA verified; all design decisions resolved.
**Study 004 pre-registration SHA:** 1b9eb204e32b6b7cb32dfce4cb647cfc7f0e4d0f
**Study 003 pre-registration SHA:** 4c9003176d0130540ae1f257d5140c9daa919415
**Study 003 accepted run:** study_003_full_002 (12.0/13.0, PARTIAL — 2 of 3 bars)
**Study 003 paper:** experiments/study_003/README.md

---

## Summary

Study 004 activates the LTM read path — the second component of the brain pipeline target architecture. Study 003 built a selective STM → LTM write path and left the store inert; Study 004 makes the store participate in context construction via **asynchronous parallel retrieval with arbitration**: on every turn, STM (N+K) and LTM are queried concurrently, and an arbitration layer merges, deduplicates, and ranks the combined candidate set before context assembly. Fallback (LTM-only-when-STM-empty) is the degenerate case of this design, not the design itself.

Alongside the new component, Study 004 corrects the three failures documented in Study 003: consolidation purity (the terminal cross-domain collapse that the count bar failed to detect), the structural exclusion of the final topic from promotion (end-of-session flush), and the structurally near-unreachable weighted promotion route.

The Q11 breadth failure — the single rubric failure of Study 003 — is deliberately **not** given a dedicated fix. The new component is the treatment: a broad multi-domain query that similarity retrieval cannot serve is precisely what a curated cross-topic store plus arbitration should catch. Study 004 tests that claim directly.

For the first time since Study 001, the component under test can change model outputs. Study 003's write path was observational by construction; Study 004's read path is confirmatory and carries pre-registered pass/fail bars.

---

## Research Questions

**Primary (confirmatory):** Does activating the LTM read path with parallel retrieval and arbitration recover breadth-query coverage — the failure mode that produced Study 003's single rubric failure — without regressing targeted recall?

**Secondary (confirmatory):** Do the Study 003 baseline corrections (purity-constrained consolidation, end-of-session promotion, revised weighted route) hold the architecture's targeted-recall performance?

**Observational:** How does arbitration behave in practice — how often does LTM contribute episodes STM missed, how often do the tiers overlap, and what does the dedup rate say about post-promotion STM residency?

---

## Changes from Study 003

| Parameter | Study 003 | Study 004 | Reason |
|-----------|-----------|-----------|--------|
| LTM read path | Inactive (write-only) | Active — parallel retrieval + arbitration | New component under test |
| Retrieval architecture | STM N+K only | STM N+K ∥ LTM top-M, async, arbitrated merge | [DECISION] Parallel-with-arbitration locked; non-biological substrate permits concurrent tier queries rather than serial fallback |
| Consolidation success criterion | Topic count ≤ 20 | Purity-aware criterion (see Success Criteria) | Count of 1 passed Bar 3 while triggering the pre-registered cross-domain-merge failure condition; count measures fragmentation, not purity |
| End-of-session promotion | None (final topic structurally unevaluated) | Final promotion pass at turn 111 for the active topic | Marine biology contributed zero promotions by structural design; deferred to 004 in the 003 pre-reg |
| Weighted promotion route | Novelty and Association scored against the same global LTM centroid | Association decoupled to per-topic LTM centroids (max similarity); Novelty unchanged | Complement structure caps combined novelty+association contribution at 0.35; zero weighted promotions occurred once LTM was non-empty. See Fix 3. |
| Script | 120 turns, Q1–Q13 | 120 turns unchanged + appended second breadth probe (Q14) | Second breadth probe prevents the targeted bar from resting on a single question; turns 1–120 remain byte-identical to preserve the comparison chain |
| Runtime | NVFP4 via local llama.cpp HTTP server | Qwen3.6 27B **UD-Q6_K_XL** via local llama.cpp HTTP server | NVFP4 showed measurable capability loss in offline testing vs Q6-class quantization. Reverted to the strongest quant that fits the 32 GB GPU so hardware does not cap study intelligence. Supersedes the earlier NVFP4-as-standing-baseline decision. Study 002 (Q6_K) and Study 004 (UD-Q6_K_XL) are Q6-class; Study 003 (NVFP4) is the odd one out. |
| Prompt structure | Untagged context blob | XML-tagged component blocks (see Condition C) | Second retrieval tier needs the model to distinguish provenance; also sets the pattern for future tiers. Folded in this study; confound accepted and noted (see Limitations). |

Runtime decision record: `experiments/study_004/decisions/DECISION_runtime_revert_study004.md`, committed before the pre-registration commit.

**Explicitly out of scope:** the 1,000-turn stress test. [DECISION] Endurance testing of the assembled architecture is a different study type from component isolation and will run as its own independently numbered study. Study 004 stays at 120 turns on the same script to keep the comparison chain clean.

---

## Method

### Condition

**Condition C — Iterative Construction v4**

Active context constructed per turn from two tiers queried in parallel:
- **STM tier:** N recency-ranked episodes + K similarity-retrieved episodes (unchanged from Study 003)
- **LTM tier:** top-M similarity-retrieved promoted episodes against the query embedding

Both tier queries are issued asynchronously and awaited jointly. The arbitration layer then produces the final retrieval set (see Arbitration Architecture). Pinned rules, topic assignment, consolidation, and the STM → LTM write path all carry forward from Study 003 with the amendments 001–004 baked in as the standing baseline.

### Constructed-context structure (XML-tagged blocks)

New in Study 004: the constructed context is delivered to the model as explicitly tagged blocks rather than a flat concatenation. This gives the model a provenance signal (what each piece of context *is* and where it came from), makes the arbitration logs legible against what the model actually saw, and establishes the structural pattern for future pipeline tiers. Block order and schema are fixed for the study:

```
<pinned_rules>
  <rule id="..." set_at_turn="...">...</rule>
</pinned_rules>

<recent_context>              <!-- the N recency block -->
  <episode turn="..." topic="...">...</episode>
</recent_context>

<retrieved_stm>              <!-- the K similarity block from STM -->
  <episode turn="..." topic="..." similarity="...">...</episode>
</retrieved_stm>

<retrieved_ltm>              <!-- the M block from the LTM store -->
  <episode turn="..." topic="..." promoted_at_turn="..." trigger_type="..." similarity="...">...</episode>
</retrieved_ltm>

<current_turn>
  <user_message>...</user_message>
</current_turn>
```

Specification notes, binding on implementation:
1. **Deduplicated placement.** An episode surviving arbitration with provenance `both` appears once, in `<retrieved_ltm>`, carrying its LTM metadata. It must not be duplicated into `<retrieved_stm>`. Provenance `stm` → `<retrieved_stm>`; provenance `ltm` or `both` → `<retrieved_ltm>`. This makes the tagged context a faithful rendering of the post-arbitration set.
2. **Empty blocks.** A block with no members is emitted as a self-closing tag (e.g. `<retrieved_ltm/>`) rather than omitted, so the model sees a consistent frame every turn and the empty-LTM case is explicit rather than silent.
3. **Recency vs retrieval separation.** An episode that qualifies for both the N recency block and the K similarity block is placed in `<recent_context>` only (recency takes precedence), preventing intra-STM duplication.
4. **No scored content in tags.** Attribute values are metadata only (turn, topic, similarity, promotion provenance). No filter scores or arbitration internals are exposed to the model; those live in logs, not context.
5. **The tagging change is not ablated.** Per design decision, XML restructuring is folded into Condition C v4 alongside the read path; the resulting attribution confound on the non-regression bar is accepted and documented (Limitations). The targeted bar is protected independently by its provenance-attribution requirement (Bar 1).

### Model and runtime (pre-registered)

| Parameter | Value |
|-----------|-------|
| Inference model | Qwen3.6 27B UD-Q6_K_XL (Unsloth dynamic 6-bit, extra-large) |
| Runtime | Local llama.cpp HTTP server, /completion endpoint |
| Context capacity | 262,144 tokens |
| Hardware | NVIDIA RTX 5090, 32 GB VRAM |
| Embedding model | Qwen3-Embedding-0.6B Q8_0 GGUF |
| Embedding dimensions | 1,024 |
| Response budget | 1,024 tokens |

### Script

Turns 1–120: byte-identical to the Study 002/003 script. Four scripted domains (civil engineering 1–30, Renaissance art 31–60, monetary policy 61–90, marine biology 91–120), planted facts at early/middle/late positions, probes at turns 112–120.

**Addition — turn 121 (Q14):** a second breadth probe, phrased differently from Q11 but demanding the same coverage: a concrete planted specific from each of the four domains. Full text and locked scoring criteria are authored in `experiments/study_004/q14_criteria.md`, committed with this pre-registration. Summary of constraints met there:
- Must require at least one specific planted value or entity from each of the four domains for full credit
- Must not share surface phrasing with Q11 (different verbs, different framing) so the two probes are not trivially the same embedding
- Scored 0 / 0.5 / 1.0: full credit = all four domains with specifics; half credit = all four domains named but specifics missing from one; zero = any domain omitted

Rationale for appending rather than editing: any change inside turns 1–120 would break comparability with Studies 002 and 003. Q14 runs after Q13 and after all scored 003-equivalent probes, so its presence cannot influence the Q1–Q13 comparison. The rubric becomes 14 questions, but non-regression is evaluated on the original 13 only.

### Evaluation

Q1–Q13: same rubric, same authoritative criteria (`experiments/study_002/rubric_filled.md`), unmodified. Q14: criteria authored and committed with this pre-registration. Manual scoring by a single rater, scoring completed before any arbitration-log analysis is opened.

---

## Arbitration Architecture (New Component)

### Parallel retrieval

On each turn, after the user message is embedded:
1. STM query: N + K as in Study 003 (unchanged parameters).
2. LTM query: top-M promoted episodes by cosine similarity to the query embedding. **M = 5** (locked). Chosen relative to N=10 recency so the LTM tier augments rather than floods; noted as a tunable in Limitations.
3. Both queries issued asynchronously; context construction awaits both.

Fallback behavior is subsumed: if STM returns nothing beyond recency (K empty), the merged set is simply LTM-weighted. No special-case code path — the degenerate case must fall out of the general mechanism correctly, and this is verified by a dedicated pre-run test.

### Deduplication (mandatory, before ranking)

Promoted episodes remain resident in STM (Study 003 design, unchanged). Therefore the same episode can arrive from both tiers. Arbitration must dedupe on **episode_id** before any ranking occurs — a promoted episode must never receive two votes. The surviving record carries a provenance tag: `stm`, `ltm`, or `both`.

### Merge and ranking

After dedup, candidates are ranked by cosine similarity to the query embedding, tier-agnostic — an LTM episode and an STM episode with equal similarity are equal citizens. The final retrieval set takes the top **K_total = K_stm + M** ranked candidates (capped at the current context budget), then context assembly proceeds into the tagged blocks defined in Condition C.

**Design note — why similarity-only ranking:** introducing a tier bias (e.g., LTM boost) would confound the study; if LTM helps, it must help by containing the right episodes, not by being favored. Tier weighting is a future-study parameter, not a Study 004 parameter.

### Logging (per turn)

- `arbitration_events.csv`: turn, stm_candidates, ltm_candidates, duplicates_removed, final_set_size, ltm_episodes_in_final_set, provenance list
- Every LTM episode that reaches the constructed context is logged with its promoted_at_turn and trigger_type — this is what makes the Q11/Q14 outcome attributable

---

## Baseline Corrections (Fixes from Study 003)

### Fix 1 — End-of-session promotion

A final promotion pass fires at turn 111 (last turn before the probe block) for the currently active topic, using the standard filter evaluation against the current LTM centroid. Turns 112–120 remain excluded from event emission (Amendment 004 carried forward). This gives marine biology a promotion batch and — critically for this study — makes marine-biology episodes *available to the read path* during the probes.

**Sequencing note:** the turn-111 flush must complete before the turn-112 probe begins, so probe-time LTM retrieval sees the full four-domain store.

### Fix 2 — Consolidation purity criterion

The count-only bar is retired. See Success Criteria Bar 3. The consolidation *mechanism* is unchanged (0.45 merge threshold, user-message embeddings per Amendment 002) — what changes is what counts as success, plus one guard:

**Probe-turn consolidation guard (ratified):** episodes generated during the probe block (turns 112–121) are excluded from acting as merge bridges — they may be assigned to topics but a merge whose connecting similarity runs through a probe-turn episode is rejected. Rationale: the Study 003 collapse was induced by the turn-120 breadth query forming a mixed-domain episode that bridged all four clusters. Breadth probes are measurement instruments; they must not restructure the thing being measured. This keeps Bar 3 a test of the consolidation mechanism rather than of the probe's side effect.

### Fix 3 — Weighted route revision: Decoupled Association [DECISION: Option A locked]

Study 003 finding: Novelty and Association were complements off the same global LTM centroid (0.35N + 0.20(1−N) = 0.20 + 0.15N, capped at 0.35 combined), making the 0.60 weighted threshold structurally near-unreachable once LTM was non-empty. Zero weighted promotions occurred after batch one; all nine later promotions were all-or-nothing bypasses.

**Resolution:** Association is decoupled from the global centroid. Novelty is unchanged. Full specification follows — this section is the implementation contract; no interpretive latitude is delegated.

**Association (revised definition):**

```
A(e) = max over t in LTM_topics of cosine_similarity(embedding(e), centroid(t))
```

where `LTM_topics` is the set of canonical topic groups present in the LTM store at batch-snapshot time.

1. **Grouping rule.** Each LTM row's stored `topic` label is resolved through the *current* canonical consolidation mapping at evaluation time. Rows whose labels resolve to the same canonical topic pool into one group. One centroid per group = mean of member embeddings. Groups of size 1 are permitted (the centroid is that episode's embedding); no minimum group size.
2. **Maximum, not own-topic.** Association is the max similarity across all per-topic centroids. It is NOT scored against the outgoing episode's own topic — at promotion time the outgoing topic is by construction absent from LTM (its episodes are the ones being evaluated), so an own-topic definition would pin A to 0.0 permanently and kill the filter in the opposite direction from the Study 003 defect. Semantics: "does this episode connect strongly to any consolidated body of prior knowledge."
3. **Empty LTM.** A = 0.0 (unchanged from Study 003). Empty-LTM suspension of the all-or-nothing bypass carries forward unchanged for all filters.
4. **Snapshot discipline.** All per-topic centroids and the global centroid are computed once at the start of each promotion batch and frozen for the batch. Recompute only after all batch writes complete (Study 003 rule, extended to the per-topic set).
5. **Novelty unchanged.** N(e) = 1 − cosine_similarity(embedding(e), global LTM centroid). Weights and thresholds unchanged: 0.35/0.30/0.20/0.15, weighted ≥ 0.60, bypass ≥ 0.90.
6. **All-or-nothing scope (adopted — Association excluded).** Association is EXCLUDED from the all-or-nothing bypass. Under the decoupled definition, A ≥ 0.90 signals near-duplication of already-stored knowledge — a redundancy signal, not the high-intensity encoding the bypass models. Bypass-eligible filters: novelty, repetition, emotional valence. Association contributes through the weighted route only.
7. **Known degeneracy — single-topic LTM.** When LTM contains exactly one canonical topic (true at the second promotion event, ≈ turn 61, in this script), the global centroid equals the sole per-topic centroid and N/A are complements for that batch exactly as in Study 003. Decoupling takes structural effect only from the third event onward (≈ turn 91, plus the turn-111 flush). Batch-2 route composition must not be read as evidence for or against the fix; the report will analyze batches 3+ separately.
8. **Structural effect.** The combined N+A contribution cap rises from 0.35 (fixed complement) to a maximum of 0.55 (independent scores), making the weighted route reachable with moderate repetition. Whether it actually fires is the pre-registered observational measure "revised weighted-route activity."

**Required unit tests (pre-run checklist references these):**
- Empty LTM → A = 0.0
- Single-topic LTM → A = cos(e, c₁) and N = 1 − cos(e, c₁) (documented complement case)
- Two-topic LTM → A = max of the two similarities, not the mean
- Post-merge grouping: two LTM rows with different stored labels resolving to one canonical topic → one pooled centroid
- Snapshot: centroids identical for every episode within a batch even as promotions write mid-batch
- A = 0.95, all else 0, LTM non-empty → NOT promoted via bypass (if item 6 adopted); weighted score = 0.19 → not promoted

The revision applies to all promotion events in Study 004 including the turn-111 flush. Decision record: `experiments/study_004/decisions/DECISION_association_decoupling_study004.md`, committed before the pre-registration commit.

---

## Success Criteria

Per design discussion: two separate confirmatory bars — a targeted bar isolating the read path's specific job, and a non-regression bar catching collateral damage — plus the revised consolidation bar. Comparison baseline is **Study 003 Condition C (12.0/13.0)**, the direct architectural predecessor. Study 002's 13.0/13.0 is reported as a reference point only. Note the runtime is not constant across the chain: Study 002 was Q6_K, Study 003 NVFP4, Study 004 UD-Q6_K_XL — so the non-regression comparison to 003 crosses a quantization boundary (see Limitations for why this does not threaten the bar's purpose).

### Bar 1 — Breadth Recovery (Targeted)
**Both breadth probes — Q11 and Q14 — score ≥ 0.5, with combined breadth score ≥ 1.5/2.0.**
- Study 003 result: Q11 = 0.0 (two of four domains omitted; retrieval log showed no middle-domain episode reached context)
- Rationale: this is the read path's specific job. Requiring both probes prevents a single-question fluke in either direction; requiring ≥ 1.5 combined means at least one fully-covered enumeration plus one no-worse-than-half.
- Attribution requirement: for the bar to be interpreted as an LTM effect, the arbitration log for Q11/Q14 turns must show LTM-provenance episodes from the domains that STM retrieval missed. A pass with zero LTM episodes in the probe-turn context would be recorded as a pass with unattributed cause and flagged in the report.

### Bar 2 — Targeted Recall Non-Regression
**Q1–Q13 overall ≥ 12.0/13.0, with Cat 1–3 ≥ Study 003 (3.0 / 3.0 / 2.0) and Cat 5 ≥ 2.0.**
- Rationale: activating a second retrieval tier changes every turn's context. The risk is topic bleed and displacement of relevant STM episodes by LTM episodes. Cat 1–3 and Cat 5 must hold outright; the overall floor is Study 003's 12.0. If Q11 recovers under Bar 1, overall will exceed 12.0 — but Bar 2 deliberately does not *require* 13.0, so that Bar 1 (benefit) and Bar 2 (no harm) remain independently evaluable. A 13.0/13.0 outcome is reported as exceeding both bars.
- Category-analysis caveat carried from Study 003: any Bar 2 failure is analyzed by category before verdict.

### Bar 3 — Consolidation Purity
**At turn 121: final topic count in [3, 10] AND zero cross-domain merges, where a cross-domain merge is any consolidation merge joining episodes whose script-assigned ground-truth domains differ.**
- Study 003 result: count = 1 via four cross-domain merges at similarities 0.45–0.54 — passed the old count bar while triggering the pre-registered failure condition.
- Rationale: the band's lower bound (3) makes total collapse an automatic fail; the upper bound (10) preserves the anti-fragmentation intent of the old bar with margin below Study 002's 52. Four scripted domains means the honest target is 4; the band gives cushion for legitimate sub-topic splits without admitting either collapse (<3) or fragmentation (>10). The zero-cross-domain-merge clause measures purity directly against ground truth available from the script and does the primary work; the band is the anti-fragmentation backstop.

All three bars must pass for VALIDATED. Mixed outcomes reported as PARTIAL without altering criteria.

---

## Observational Measures (No Pass/Fail)

| Measure | Description |
|---------|-------------|
| LTM contribution rate | Fraction of turns where ≥ 1 LTM-provenance episode reached the final context |
| Dedup rate | duplicates_removed / ltm_candidates per turn — measures the cost of post-promotion STM residency |
| Tier overlap profile | Distribution of provenance tags (stm / ltm / both) across all retrieved episodes |
| Displacement events | Turns where an LTM episode entered the final set and the displaced next-ranked candidate was an STM episode from the active topic |
| Breadth-turn retrieval anatomy | Full candidate lists, similarities, and provenance for Q11 and Q14 turns |
| Turn-111 flush behavior | Marine-biology batch: evaluated, promoted, route composition, under the revised weighted route |
| Revised weighted-route activity | Weighted vs all-or-nothing promotion counts under the chosen Fix 3 option — did the weighted route come back to life? |
| Latency delta | Per-turn context-construction wall time vs Study 003 (parallel query cost) |

**Interpretive scope note (carried forward):** single run, single rater, scripted conversation. Arbitration findings characterize this mechanism class under this script; they do not validate parameter values.

---

## Pre-Run Checklist (Mandatory)

- [ ] GPU speed test > 30 tok/s on the UD-Q6_K_XL server
- [ ] Synthetic mini-script test: parallel retrieval returns candidates from both tiers on a store seeded with known LTM rows
- [ ] Dedup test: an episode present in both tiers appears exactly once in the final set, provenance = both
- [ ] Degenerate-case test: with K_stm empty, arbitration output equals LTM-only ranking (fallback correctness — "make sure the fallback is correct")
- [ ] Turn-111 flush fires on the synthetic script's final active topic; probe-block emission still suppressed
- [ ] Revised weighted route: unit tests for the chosen Fix 3 option
- [ ] Purity instrumentation: cross-domain merge detection verified against ground-truth labels on synthetic data
- [ ] 35-turn ablation on the real script: all checks above plus Study 003's carried checks; GO/NO-GO documented

---

## Failure Conditions

| Condition | Meaning | Next action |
|-----------|---------|-------------|
| Bar 1 fails with zero LTM episodes in probe-turn contexts | Read path never engaged on breadth queries | Diagnose LTM query path; check M and similarity floor |
| Bar 1 fails with LTM episodes present | LTM engaged but promoted set lacks the needed episodes | Promotion selectivity problem — feeds weighted-route analysis, not retrieval analysis |
| Bar 2 fails in Cat 1–3 | LTM tier displaced relevant STM episodes | Examine displacement events; consider M reduction before any tier-weighting discussion |
| Topic count < 3 | Collapse recurred | Purity guard insufficient; raise merge threshold to 0.50 (the standing deferred option) |
| Any cross-domain merge | Purity failure | Same as above |
| Dedup violation in logs | Arbitration correctness bug | Stop; fix; re-ablate |

---

## Limitations

Carried forward: single run, single rater, self-comparison baseline variance, scripted conversation ceiling, weights as design choices.

**Confound stack on the non-regression bar.** Study 004 moves three things relative to Study 003: the LTM read path (the component under test), the XML prompt restructuring (folded in, not ablated), and the runtime quantization (NVFP4 → UD-Q6_K_XL). Bar 2 (non-regression) therefore cannot cleanly attribute its outcome to the read path alone. This is accepted for a principled reason: Bar 2 is a *floor* guarding against regression, and both added factors — a cleaner prompt and a stronger quantization — push away from regression, not toward it. Neither can cause the failure the bar exists to catch. The targeted bar (Bar 1) is protected separately by its provenance-attribution requirement: a breadth-recovery pass counts as an LTM effect only if the arbitration log shows LTM-provenance episodes filled the gap STM missed, which a smarter model and cleaner prompt cannot fabricate.

**Runtime discontinuity.** The comparison chain crosses quantization boundaries (Q6_K → NVFP4 → UD-Q6_K_XL). NVFP4 was reverted after offline testing showed capability loss; UD-Q6_K_XL is the strongest quant fitting the 32 GB GPU. The intent is that hardware constraints not cap study intelligence. Quantization deltas across studies to date have not been the driver of any reported finding, but strict same-runtime continuity does not hold and the 12.0 baseline was produced on a weaker (NVFP4) model, making it a soft floor.

**Other.** The two breadth probes share a query *type* even with distinct phrasing — breadth-query generalization beyond enumeration remains untested. The 12.0 baseline inherits Study 003's amendment stack as the de facto architecture. M = 5 is a fixed design choice, not a tuned value.

---

## Resolved Decisions (all locked)

1. **Fix 3 — weighted route:** Option A, Association decoupled to per-topic LTM centroids (max similarity). Full spec in Fix 3.
2. **Association bypass:** excluded from all-or-nothing; weighted route only.
3. **Bar 3 band:** [3, 10] plus zero cross-domain merges.
4. **Probe-turn consolidation guard:** ratified.
5. **Baseline:** Study 003 Condition C (12.0/13.0) as the bar; Study 002 as reference only.
6. **M (LTM top-M):** 5.
7. **XML tagging:** folded into Condition C v4; confound accepted and documented.
8. **Runtime:** Qwen3.6 27B UD-Q6_K_XL; supersedes NVFP4-as-standing-baseline.

**Pre-commit requirements completed:** Q14 text and scoring criteria authored; Study 003 SHA verified against the Study 003 report header; association-decoupling and runtime-revert decision records written and committed.

---

## Appendix

- Study 004 pre-registration SHA: 1b9eb204e32b6b7cb32dfce4cb647cfc7f0e4d0f
- Study 003 paper: `experiments/study_003/README.md`
- Study 003 pre-registration SHA: 4c9003176d0130540ae1f257d5140c9daa919415
- Study 003 LTM analysis: `experiments/study_003/runs/run_001/ltm_analysis/analysis_report.md`
- Authoritative rubric (Q1–Q13): `experiments/study_002/rubric_filled.md`
- Q14 criteria: `experiments/study_004/q14_criteria.md`
- Association decision: `experiments/study_004/decisions/DECISION_association_decoupling_study004.md`
- Runtime decision: `experiments/study_004/decisions/DECISION_runtime_revert_study004.md`
- Pre-registration path: `experiments/study_004/pre_registration.md`
