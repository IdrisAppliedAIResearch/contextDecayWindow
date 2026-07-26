# Study 007 — Pre-Registration (DRAFT v1)
## contextDecayWindow
**Idris Applied AI Research**
**Date:** July 2026
**Status:** LOCKED at commit — SHA recorded in a follow-up commit, as in Studies 005 and 006.
**Amendments:** `experiments/study_007/amendments/` — registered amendments are binding and are listed here as they are made.
- `AMENDMENT_001_delivered_information.md` — corrects the delivered-information premise in *Summary* and §1, and re-derives `B_ltm` against measured rendered output.
- `AMENDMENT_002_floor_cost_criterion.md` — re-derives the Targeted-Retrieval Fixture's criterion 3 in characters; locks `B_ltm = 32,000` and `k_min = 1`; records the pre-run finding that the floor is **not** what delivers four-domain coverage at these parameters.
**Study 006 report:** `experiments/study_006/study_006_report.md` (COMPLETE, PARTIAL)
**Study 006 pre-registration SHA:** `5def302` (+ `amendments/AMENDMENT_001_selection_scale.md`)
**Study 006 accepted treatment:** `runs/study_006_full_001` (Bar 1 PASS 4/4 · Bar 2 FAIL 0.0/0.0 · Bar 3 FAIL 10.5 vs 11.0)

---

## Summary

Study 007 changes how much and what kind of long-term memory reaches the model. It introduces **one new component: an information-expressed, diversity-floored retrieval budget.** It does not touch formation.

Study 006 solved memory formation. All four domains formed for the first time in the program, at 100% offset-verbatim fidelity, zero non-content records, zero inference calls, and better compression than Study 005 (6.55% vs 10.81% of raw). Then both breadth probes scored 0.0 — worse than a control whose store was demonstrably poorer. At Q11 the treatment's store held `Annunciation`, `Melozzo`, `1483`, `Priya Mehta`, `2.3%`, and `reverse repurchase`, and the model answered that its context contained no Renaissance art or monetary policy episodes.

The cause is isolated and is not the selection policy. Retrieval returns a fixed **count** of records. Study 006 made each record a sentence rather than a whole turn — a 17× increase in record count and roughly a 28× reduction in characters per record — while leaving the retrieval budget expressed as "top-M records." The delivered information per turn fell by roughly an order of magnitude (≈ 584 characters for the treatment's 4 records versus ≈ 20,700 for the control's 5), and the few slots available were consumed by spans clustered in a single topic. **A formation success was converted into a retrieval regression by an unstated contract between two stages.**

That contract is the program-level lesson. The retrieval budget silently assumed "a record is roughly a domain's worth of content." Whole-turn granularity had been supplying per-domain diversity *accidentally*, because each record bundled many facts from one domain into a single slot. Study 007 makes explicit what coarse granularity was doing implicitly:

1. **Budget expressed in information, not record count.** The LTM block is filled to a character budget, so record granularity no longer silently determines how much memory the model receives.
2. **Per-domain diversity floor.** Each canonical topic present in distilled LTM is guaranteed a minimum allocation, with the remaining budget filled by pure similarity. Coverage for broad queries is structural rather than incidental.

Formation is carried forward **unmodified** — same span segmentation, density-normalized source-weighted salience, C = 50, floor, dedup, verbatim extraction, zero inference calls. Study 006's changes are not revisited.

Because Study 006 preserved its distilled store and its probe-turn retrieval logs, the new retrieval policy can be evaluated **offline against real data before any run is spent** (see Retrieval Replay Gate). This is the direct analogue of the gate that caught Study 006's cap-scaling defect at zero cost.

---

## Research Questions

**Primary (confirmatory):** Does an information-expressed, diversity-floored retrieval budget recover four-domain breadth from a store that demonstrably contains all four domains' facts?

**Secondary (confirmatory):** Does the revised budget preserve targeted recall — i.e., does guaranteeing coverage for broad queries cost accuracy on narrow ones?

**Tertiary (confirmatory):** Does formation remain intact (4/4, faithful, junk-free) when only retrieval changes?

**Observational:** How does delivered LTM information per turn, per-domain composition, and context size change? What is the smallest selection cap C that would still form 4/4 (offline, for future studies)?

---

## What is and is not changing

**Changed (retrieval only):**

| Element | Study 006 | Study 007 |
|---|---|---|
| LTM budget unit | Count of records (top-M = 5) | **Character budget `B_ltm`** |
| Coverage across domains | Incidental (none by design) | **Per-domain floor `k_min`, then similarity fill** |
| Arbitration cap | Count-based (`K_stm + M`) | **Information-based; LTM floor selections are protected from eviction** |
| Span/episode redundancy | Dedup on identifier only | **Containment dedup added** (a span whose source episode is already in the STM block is dropped) |

**Carried forward unchanged:** the entire formation stage (permissive raw store; span segmentation with character offsets; eligibility window; density-normalized, source-weighted salience; C = 50; salience floor; dedup at 0.95; verbatim extraction with zero inference calls; provenance-to-source; dream cadence at ≈31/61/91 plus the turn-111 flush); topic assignment and consolidation purity instrumentation; XML-tagged context blocks; STM retrieval (N + K, unchanged); runtime, response budget, and the full determinism protocol.

**Explicitly NOT in this study:**
- **Any change to selection.** Formation is solved; Study 006's parameters ship as-is. Changing C or salience concurrently would confound the retrieval fix. The minimum-viable-C question is answered **offline as an observational measure only** and informs future studies, not this one.
- **Abstractive/generative dreaming.** Still deferred; extractive fidelity has never been the bottleneck.
- **1,000-turn stress test.** Still its own study type, deferred until end-to-end recall works.

---

## Baseline corrections carried in from Study 006

These are corrections, not the component under test.

### Correction 1 — UTF-8 in code, not in the environment

Study 006 ran with `PYTHONUTF8=1` because `src/study/script_loader.py` opens the script without an encoding argument; under the Windows cp1252 default the model silently receives mojibake. A study whose validity depends on an environment variable, with silent corruption as the failure mode, is fragile.

**Fix:** `script_loader.py` (and every study-path file open) specifies `encoding='utf-8'` explicitly. In addition, the runner asserts the loaded script's SHA-256 **after decode** against the pre-registered hash at startup and aborts on mismatch. The environment variable may remain set, but correctness must not depend on it.

### Correction 2 — Restore the scoring protocol

Study 006 deviated from the pre-registered procedure on two counts: the rater was an agent rather than a human, and formation results (Bar 1) had been computed before scoring. Both are restored:

- **Human rater.** Q1–Q14 for both arms are scored by a human rater.
- **Score before mechanism logs.** No formation, retrieval, arbitration, or dreaming output may be opened — by the rater or the runner — until scores for both arms are committed. Order is verifiable from git history and is an acceptance criterion.
- **Blinding.** Arm identity is masked during scoring: responses are extracted to arm-anonymized files (`arm_A/`, `arm_B/`) with the mapping held in a sealed file committed but not read until scores land. This is new, and it is cheap insurance given that Study 006's deviation cost the study a clean Bar 3.

### Correction 3 — Hedge-credit scoring sensitivity (dual scoring, rubric unchanged)

Study 006's Bar 3 turned on crediting a hedged guess — the control's "likely included azurite or early ultramarine for blues" earned 0.5 for surfacing one planted term while offering a wrong alternative. A criterion that rewards hedged guessing systematically favors the vaguer arm.

**The rubric is NOT changed** — it has been locked since Study 002 and altering it would break cross-study comparability. Instead, any answer where credit depends on a hedged or alternative-offering formulation is **scored twice**: the **primary** score under the locked criteria (which governs all bars), and a **strict** score in which a term offered as one of several alternatives earns no credit. Both are recorded per question. If the two scorings imply different bar verdicts, the report must state so explicitly. This surfaces the weakness without breaking the chain.

### Correction 4 — Stage-interface contract (process, program-wide)

Study 006's failure was an unstated contract: the retrieval budget assumed a record granularity that formation silently changed. To prevent recurrence, a standing pre-run checklist item is added from this study forward:

> **If any study changes the granularity, units, or size distribution of what a stage emits, every downstream stage's budget, cap, or threshold that consumes that output must be explicitly re-derived, and the re-derivation recorded in the pre-registration — even if the downstream stage is otherwise out of scope.**

---

## Known ceiling on Q1–Q13 (interpretation note, set before the run)

Six planted facts were not selected at any defensible cap in Study 006 and remain absent from the store: `art_pigment`, `art_patron_role`, `monetary_taylor`, `monetary_fed`, `marine_photophores`, `marine_feeding`. Q5 and Q8 depend on two of them.

Since formation is unchanged in Study 007, **these facts will be absent again, and Q5 and Q8 cannot reach full credit regardless of how well retrieval performs.** The maximum achievable Q1–Q13 is therefore bounded below 13.0 by formation, not by retrieval. Bar 3 is set as a non-regression criterion against a same-seed control precisely because an absolute target would be measuring the formation ceiling rather than the retrieval change. This is recorded now so that a sub-13 score is not later misread as a retrieval failure.

---

## Method

### Condition

**Condition C — Iterative Construction v7.** Identical to v6 except for the LTM retrieval budget and arbitration assembly specified below.

### Runtime and seeding (pre-registered, carried unchanged)

| Parameter | Value |
|---|---|
| Inference model | Qwen3.6 27B UD-Q6_K_XL |
| Runtime | Local llama.cpp HTTP server, /completion (build recorded in run header) |
| Context capacity | 50,000 tokens (`--ctx-size 50000`) |
| Response budget | 2,048 tokens |
| Embedding model | Qwen3-Embedding-0.6B Q8_0, 1024 dims |
| Server slots | Single (`--parallel 1`) |
| Speculative decoding | Off |
| Seed | Fixed (5005 unless changed and recorded); identical across arms |

Launch command (both arms, identical; build/commit hash recorded alongside):

```
--ctx-size 50000
--parallel 1
--cache-type-k q8_0
--cache-type-v q8_0
--flash-attn on
--jinja
--metrics
--temp 1
--top-p 0.95
--top-k 20
--min-p 0.0
--presence-penalty 0.0
--repeat-penalty 1.0
--seed <FIXED_VALUE>
```

Determinism spot-check (re-run a fixed prefix under the same seed, assert turn-identical output) is a pre-run gate. Arms sharing a seed are turn-identical until their constructed contexts first diverge.

### Script

121 turns, unchanged: turns 1–120 hash-identical to Studies 002–006, Q14 at turn 121. Script SHA-256 asserted **after UTF-8 decode** at startup against the pre-registered hash.

### Evaluation

Human rater, blinded to arm, on the locked 14-question rubric (Q1–Q13 `study_002/rubric_filled.md`; Q14 `study_004/q14_criteria.md`), with dual scoring on hedge-dependent credit per Correction 3. Scores for both arms committed before any mechanism log is opened. Formation checks (facts-in-LTM, faithfulness, non-content) are computed **after** scores are committed.

---

## New Component — Information-Expressed, Diversity-Floored Retrieval

This section is the implementation contract. No interpretive latitude is delegated.

### 1. Budget expressed in information

The LTM block is filled to a **character budget `B_ltm`**, not a record count. Records are admitted until adding the next record would exceed `B_ltm`; the budget is never exceeded.

- Characters, not tokens, are the unit — records are stored as text and character counts are what the existing logs carry.
- `B_ltm` **proposed at 4,000 characters** (≈ 1,000 tokens), to be **calibrated by the Retrieval Replay Gate before lock** (see below).
- Rationale for the proposed magnitude: Study 006's treatment delivered ≈ 584 characters of LTM per turn (4 records × ≈ 146 chars); its control delivered ≈ 20,700 (5 × ≈ 4,149). A 4,000-character budget raises delivered information ≈ 7× over the treatment while staying ≈ 5× below the control, keeping projected peak context near the treatment's 12,169 tokens and far below the 50,000 ceiling. If replay shows breadth requires more, `B_ltm` is re-derived from replay evidence and the revised value recorded before commit.

### 2. Per-domain diversity floor, then similarity fill

Let `T` be the set of canonical topics present in distilled LTM at the current turn (resolved through the current canonical consolidation mapping, as in prior studies).

**Phase 1 — Floor.** For each topic `t ∈ T`, select that topic's top **`k_min`** spans by cosine similarity to the query embedding. These are the *floor selections*.
- `k_min` **proposed at 3**, calibrated by replay before lock.
- If a topic has fewer than `k_min` spans, take all of them; the shortfall is not redistributed as a guarantee (it simply leaves budget for fill).
- If the floor selections alone would exceed `B_ltm`, admit floor selections in round-robin order across topics (highest-similarity first within each topic) until the budget is reached, so no topic is starved by another's longer spans.

**Phase 2 — Fill.** The remaining budget is filled from all not-yet-selected spans by **pure global cosine similarity**, tier-agnostic and topic-agnostic. No per-topic cap is applied during fill: a query genuinely about one domain should be free to spend most of its remaining budget there.

**Design note.** The floor is what makes breadth structural rather than incidental; the fill is what preserves targeted performance. The floor is deliberately small relative to the budget (proposed 12 of ~27 slots) so that the majority of the budget still follows relevance. This is the explicit version of the coverage that whole-turn granularity supplied by accident.

### 3. Containment dedup

A distilled span is a substring of a source episode. If that source episode is already present in the STM block for this turn, the span is redundant — the fuller text already carries it.

**Rule:** during arbitration, drop the LTM span whose `source_episode_id` is already present in the STM block, and log the drop as `containment_dedup`. Budget freed by a containment drop is refilled by the next-ranked candidate under the same phase rules (a dropped floor selection is replaced by the same topic's next-ranked span, preserving the floor).

Identifier-based dedup (same span selected twice) is carried unchanged from Study 004.

### 4. Arbitration assembly

Arbitration in Study 004 ranked a merged pool tier-neutrally and capped by count. That design assumed both tiers emitted comparable units, which is no longer true.

**Revised assembly:**
1. STM tier produces N + K as before (**unchanged**).
2. LTM tier produces its selection under Phases 1–2 within `B_ltm`.
3. Identifier dedup, then containment dedup (§3), with refill.
4. **Floor selections are protected**: they may not be evicted by ranking. The LTM block is rendered as selected.
5. Blocks are assembled into the carried XML-tagged structure (`<pinned_rules>`, `<recent_context>`, `<retrieved_stm>`, `<retrieved_ltm>`, `<current_turn>`), with distilled-record provenance metadata as in Study 006.

**Named departure:** tier-neutral count-ranking is replaced by tier-budgeted assembly. This is part of the component under test and is recorded as an explicit change from Study 004's arbitration, not an incidental edit.

### 5. Logging (per turn)

`retrieval_budget.csv`: turn, topics_present, floor_selected_per_topic, fill_selected, containment_drops, refills, ltm_chars_used, ltm_records_used, budget_utilization, per-domain character split, and the full ordered selection list with span ids, topics, similarities, and phase (`floor` | `fill`).

This log is what makes Bar 1's attribution checkable.

### Locked parameters

| Parameter | Value | Note |
|---|---|---|
| `B_ltm` | **32,000 chars — LOCKED (S7-T-017)** | proposed 4,000; withdrawn by Amendment 001, calibrated by replay |
| `k_min` | **1 per topic — LOCKED (S7-T-017)** | proposed 3; reduced after raising `B_ltm` failed to satisfy the targeted fixture |
| Budget charged at | rendered cost, after identifier dedup | Amendment 001 §4.1 |
| Fill rule | pure global similarity, no topic cap | new |
| Floor protection | floor selections not evictable | new |
| Containment dedup | drop span if source episode in STM block | new |
| STM (N + K) | unchanged | carried |

---

## Retrieval Replay Gate (pre-run, mandatory)

Study 006 preserved its distilled store (200 records with known contents and topics) and its probe-turn retrieval logs. The new retrieval policy is therefore evaluable offline, against the exact store and the exact probe queries that failed.

**Procedure.** Load Study 006's preserved distilled store. Embed the Q11 (turn 120) and Q14 (turn 121) queries as the runner does. Execute the Study 007 selection (floor + fill within `B_ltm`, containment dedup) and record the resulting LTM block.

**Gate criteria (all must hold to proceed):**
1. At **both** probes, the selected LTM block contains at least one planted term from **each of the four domains** (checked against `q_facts_key.md`).
2. Budget is respected — the block never exceeds `B_ltm`.
3. Projected peak context remains below 60% of `--ctx-size`.
4. The same policy applied to Study 006's parameters (`M = 5`, no floor) reproduces Study 006's observed single-domain result — confirming the harness is faithful to what actually happened.

**Calibration.** `B_ltm` and `k_min` are set to the **smallest** values that satisfy criterion 1 at both probes, with a documented margin. Sweep both and record the frontier. Smallest-sufficient is the rule so that the budget is justified by evidence rather than set generously to be safe — an over-large budget would trade breadth against lost-in-the-middle risk and inflate context.

**If the gate fails:** do not run. Revise and re-replay; record the revision in a decision record.

**Interpretive limit (stated up front, carried from Study 006's lesson).** The replay validates against data the policy was designed after, and calibrating parameters on it means the replay cannot independently validate those parameters. Its role is to prevent spending a run on a policy that provably cannot work. The targeted-retrieval fixture below and the live run remain out-of-sample.

---

## Targeted-Retrieval Fixture (pre-run, mandatory)

The diversity floor's risk is the mirror image of the breadth failure: reserving budget for other domains could starve a narrowly targeted query and regress Bar 2.

**Fixture.** Using Study 006's preserved store, issue a set of narrowly targeted queries — at minimum one per domain, phrased like the targeted rubric questions (e.g. a civil-engineering-specific factual query).

**Gate criteria:**
1. For each targeted query, the **majority of the character budget** goes to the query's own domain (floor + fill combined).
2. The domain's own top-similarity span is present in the block.
3. Compared to a floor-disabled variant on the same query, the targeted domain loses no more than `k_min × (|T| − 1)` slots — i.e., the floor's cost is bounded and quantified, not open-ended.

**If criterion 1 fails**, `k_min` is too large relative to `B_ltm`; reduce `k_min` or raise `B_ltm` and re-check both this fixture and the replay gate. Both must pass simultaneously — this is the tension the calibration must resolve, and resolving it before the run is the point.

---

## Success Criteria

Baseline is a **same-seed Study 006 control** — the Study 006 accepted treatment architecture (span selection, count-based top-M retrieval) re-run at the Study 007 runtime and same fixed seed. The arms differ **only** in the retrieval budget and diversity policy.

### Bar 1 — Breadth Recovery (the direct target)
**Q11 ≥ 0.5 AND Q14 ≥ 0.5 AND (Q11 + Q14) ≥ 1.5**, with the probe-turn `retrieval_budget.csv` showing distilled records from **all four domains** in the LTM block at both probes.
- Study 006: Q11 = 0.0, Q14 = 0.0, with one term from one domain reaching the model.
- **Attribution requirement:** a pass counts as a retrieval-budget effect only if the log shows four-domain coverage in the block. A pass with single-domain coverage would be recorded as a pass with unattributed cause and flagged.
- **Store-content precondition (carried):** evaluated only if Bar 3 (formation non-regression) confirms 4/4 formation. If formation regressed, Bar 1 is **not evaluable**, not "failed."

### Bar 2 — Targeted Recall Non-Regression
**Q1–Q13 ≥ the same-seed Study 006 control's Q1–Q13, with Cat 1–3 not below the control's per-category totals.**
- This is the bar the diversity floor puts at risk: budget reserved for other domains is budget not spent on the asked-about one.
- **Ceiling note (see above):** Q5 and Q8 cannot reach full credit because their plants are unformed. A sub-13 score is a formation ceiling, not a retrieval failure.
- Category-analysis caveat carried. Judgment-call sensitivity must be stated where a verdict turns on a single 0.5, and the dual (strict) scoring reported alongside.

### Bar 3 — Formation Non-Regression
**4/4 domains still form, 100% offset-verbatim fidelity, zero non-content records, zero inference calls in dreaming.**
- Selection is unchanged, so this should hold trivially. It is a bar rather than an observation because it is the precondition for interpreting Bar 1, and because a silent regression here would invalidate the study's premise.

All three bars pass → VALIDATED. Mixed outcomes → PARTIAL, criteria unchanged.

---

## Auxiliary Control Run

**Configuration.** The **accepted Study 006 treatment implementation** (span selection with count-based top-M retrieval) at the Study 007 runtime and the same fixed seed, same 121-turn script.

**Code discipline (binding, carried).** The control runs on **checked-out Study 006 code in a separate worktree**, never the Study 007 runner with the budget disabled by flag. The launcher must reject a dirty worktree, unexpected diff, wrong script hash (post-decode), import escape, or presence of the Study 007 retrieval engine, and must record module paths, server properties, command, and process id before inference.

**One deliberate exception:** the control inherits **Correction 1** (explicit UTF-8 and post-decode hash assertion), because a control that silently receives mojibake is not a valid baseline. This is an encoding-correctness fix with no scientific parameter change, and is recorded as the single permitted deviation from pure Study 006 code.

**Scoring.** Full 14-question rubric, human rater, blinded, both arms scored before any mechanism log is opened.

---

## Observational Measures (No Pass/Fail)

| Measure | Description |
|---|---|
| Delivered LTM information | Characters of LTM per turn; vs Study 006 treatment (≈ 584) and control (≈ 20,700) |
| Budget utilization | Fraction of `B_ltm` used per turn; turns where the budget bound |
| Floor vs fill composition | Records and characters admitted by phase |
| Per-domain character split | Distribution across topics, per turn and at the probes |
| Containment dedup rate | Drops and refills per turn — measures span/episode redundancy |
| Probe retrieval anatomy | Full ordered selection with similarities and phase for Q11 and Q14 |
| Context size | Peak and per-turn; vs Study 006 (12,169 treatment / 16,171 control) |
| Formation invariance | Record count, characters, compression vs Study 006 (200 / 29,214 / 6.55%) |
| **Minimum-viable C (offline)** | Sweep C on the preserved Study 006 raw store; smallest C still forming 4/4. **Observational only — informs future studies; C is NOT changed in this study.** |
| Determinism | Prefix replay identity; cross-arm prefix equality before divergence |

---

## Pre-Run Checklist (Mandatory)

- [ ] Pre-registration + `q_facts_key.md` committed; SHA recorded
- [ ] Decision record for the retrieval-budget component committed with author authorization
- [ ] **Correction 1 verified in code:** explicit `encoding='utf-8'` on all study file opens; script SHA asserted post-decode; a deliberate cp1252-default run reproduces the correct hash
- [ ] **Stage-interface contract check performed and recorded** (Correction 4): downstream consumers of retrieval output re-derived for the new units
- [ ] Server launched with the exact pre-registered flag set; command + build hash recorded
- [ ] `--seed` fixed and recorded; determinism spot-check passes
- [ ] GPU speed test > 30 tok/s, single-slot
- [ ] Unit tests: character budgeting (never exceeded), floor selection, round-robin under budget pressure, fill ordering, floor protection, containment dedup + refill, empty-LTM and single-topic degenerate cases
- [ ] **Retrieval Replay Gate passes: four-domain coverage at Q11 and Q14 on Study 006's preserved store; `B_ltm` and `k_min` calibrated to smallest sufficient values and recorded**
- [ ] **Replay harness fidelity check: Study 006 parameters reproduce Study 006's observed single-domain result**
- [ ] **Targeted-Retrieval Fixture passes: majority of budget to the queried domain; floor cost bounded**
- [ ] Formation carried tests still pass (span selection untouched — diff-reviewed)
- [ ] Read-path carried tests pass (tagged blocks, provenance rendering, identifier dedup)
- [ ] Blinded-scoring apparatus ready: arm-anonymized response extraction + sealed mapping
- [ ] Context-ceiling monitor active (alert > 80% of ctx-size)
- [ ] 35-turn ablation passes; GO/NO-GO committed

---

## Failure Conditions

| Condition | Meaning | Next action |
|---|---|---|
| Replay gate fails at any `B_ltm`/`k_min` | Floor+fill cannot deliver four-domain coverage from this store | Do not run. The store may need per-domain *selection* guarantees, not just retrieval ones — escalate to design |
| Replay and targeted fixture cannot both pass | Budget and floor are in irreconcilable tension | Do not run. Raise `B_ltm` before reducing `k_min`; if neither resolves, redesign |
| Harness fidelity check fails | Replay does not reproduce Study 006's actual behavior | Fix the harness before trusting any replay evidence |
| Bar 3 fails (formation regressed) | Something outside scope changed | Stop; Bar 1 is not evaluable; diff-review the formation path |
| Bar 1 fails with four-domain coverage in the log | Memory reached the model and the model still failed to enumerate | **This is a genuinely new finding** — the bottleneck is neither formation nor retrieval but the model's use of provided context. Next study targets context presentation/prompting, not memory |
| Bar 1 fails without four-domain coverage | Budget or floor insufficient in the live run despite replay | Compare live retrieval log to replay prediction; the divergence is the diagnosis |
| Bar 2 fails | Diversity floor cost targeted recall | Examine per-domain splits on targeted turns; reduce `k_min` in a follow-up, do not tune mid-study |
| Peak context near ctx-size | Budget too large in practice | Stop, re-derive, re-run |
| Determinism spot-check fails | Seeding ineffective | Confirm seed and single-slot; diagnose serving/batch |

---

## Limitations

- Single scripted run per arm, one seed, one rater. A controlled paired result, not population-level performance.
- **`B_ltm` and `k_min` are calibrated on replay data**, so the replay cannot independently validate them. Mitigations: smallest-sufficient rule, the out-of-sample targeted fixture, and the live run.
- **The per-domain floor presumes topic assignment is correct.** Coverage guarantees are only as good as the canonical topic mapping; a mis-assigned span counts toward the wrong domain's floor. Consolidation purity instrumentation is carried, but topic quality is not itself under test.
- **Four domains is a small, balanced case.** A floor of `k_min` per topic scales linearly with topic count; with many topics the floor would consume the budget. This design is not validated beyond four canonical topics, and the scaling behavior is an open question for the endurance study.
- **Six plants remain unformed** (`art_pigment`, `art_patron_role`, `monetary_taylor`, `monetary_fed`, `marine_photophores`, `marine_feeding`), bounding Q1–Q13 below 13.0 regardless of retrieval.
- **Source weighting remains script-correlated** (carried verbatim from Study 006): the planted facts are user-authored, so the weight aligns with the answer key. Unresolved and out of scope here.
- Character budgeting is a proxy for information content; a character is not a fact. Two spans of equal length can differ greatly in usefulness.
- The read-path-vs-tagging attribution gap from Study 004 remains unresolved (third arm still deferred).
- Dreaming remains extractive only.

---

## Open Decisions Before Lock

1. **`B_ltm`** — proposed 4,000 characters; **must be calibrated by the Retrieval Replay Gate to smallest-sufficient before lock.** [DECISION]
2. **`k_min`** — proposed 3 per topic; calibrated jointly with `B_ltm` against both the replay gate and the targeted fixture. [DECISION]
3. **Fill topic cap** — proposed none (pure similarity). Alternative: a soft per-topic cap during fill to prevent one domain dominating. Recommendation: no cap; the floor already guarantees coverage and a cap would cost targeted recall. [DECISION]
4. **Containment dedup direction** — proposed: drop the LTM span, keep the STM episode. Alternative: keep the compact span and drop the fuller episode from STM. Recommendation: as proposed; STM is out of scope and should not be modified. [DECISION]
5. **Blinded scoring** — proposed as described. Confirm the human rater is available; if not, the study waits rather than repeating Study 006's deviation. [DECISION]
6. **`q_facts_key.md`** — carry forward from Study 006 unchanged; re-verify per-domain target facts and source turns. [DECISION]

---

## Appendix

- Study 006 report: `experiments/study_006/study_006_report.md`
- Study 006 pre-registration (SHA `5def302`) + `amendments/AMENDMENT_001_selection_scale.md`
- Study 006 preserved distilled store (replay input): `experiments/study_006/runs/study_006_full_001/`
- Study 006 LTM analysis: `runs/study_006_full_001/condition_c/ltm_analysis/analysis_report.md`
- Study 005 report: `experiments/study_005/study_005_report.md`
- Authoritative rubric (Q1–Q13): `experiments/study_002/rubric_filled.md`
- Q14 criteria: `experiments/study_004/q14_criteria.md`
- Plant key: `experiments/study_007/q_facts_key.md`
- Pre-registration path: `experiments/study_007/pre_registration.md`
