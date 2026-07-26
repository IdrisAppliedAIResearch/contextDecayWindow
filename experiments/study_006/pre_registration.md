# Study 006 — Pre-Registration (LOCKED v1)
## contextDecayWindow
**Idris Applied AI Research**
**Date:** July 2026
**Status:** LOCKED — 2026-07-25. Commit SHA recorded below.
**Pre-registration SHA:** `5def302`
**Plant key:** `experiments/study_006/q_facts_key.md` (carried from Study 005, one amendment — see that file's *Diff from Study 005*)
**Segmenter (locked):** spaCy `en_core_web_sm` 3.8.0 sentencizer (spaCy 3.8.14, Python 3.13.13)
**NER extractor (locked):** spaCy `en_core_web_sm` 3.8.0
**Study 005 paper:** `experiments/study_005/study_005_report.md` (COMPLETE, PARTIAL)
**Study 005 accepted treatment:** `study_005_full_001` (11.0/13.0, Q14 0.5, 2/4 domains formed)
**Study 005 seeded control:** `promotion_seeded_001` (12.0/13.0, Q14 0.0, 3/4 domains formed)

---

## Summary

Study 006 fixes the selection policy inside extractive dreaming. It introduces **no new pipeline component.**

Study 005 established the architecture: a permissive append-only raw episodic store, with extractive dreaming as the selective stage that distills raw episodes into a compact long-term store. Every mechanical property passed — 100% provenance faithfulness, zero non-content records, zero inference calls, 10.81% compression, and reliable retrieval of distilled records at both breadth probes. One thing failed: **which spans dreaming chose.**

The Study 005 salience function scored whole user/assistant turns by absolute counts (`named_entities + 2 × numeric_tokens`). Long generated answers contain many incidental names and numbers, so the top-3-per-topic cap systematically preferred verbose model output over concise user-planted facts. Planted facts ranked 11th, 16th, 17th, 18th, 19th, and 28th within their dream events; only two of eleven were selected. The algorithm behaved exactly as specified — **the proxy for factual salience was the failing assumption.**

Study 006 replaces that proxy with three changes, all inside the existing extractive dreaming stage:

1. **Span granularity.** Selection operates on sentence-level spans rather than whole turns, so a compact fact competes on its own merits instead of being buried inside a long turn.
2. **Density normalization.** Salience is entity/numeric content *per unit length*, so a short dense fact outranks a long diffuse answer — the correction deferred as a "tunable" in the Study 005 design and now empirically motivated.
3. **Source awareness.** User-authored spans are weighted above model-generated spans, on the principle that in a conversation the user is the source of ground truth and the model's own prior output is derivative.

Everything that worked in Study 005 is carried forward untouched: verbatim extraction (zero inference calls in dreaming, so fabrication remains structurally impossible), provenance-to-source, deduplication, the per-topic cap, the salience floor with its sparse-topic marker, dream cadence, the read path, and the full determinism protocol.

Because Study 005 preserved its raw episodic store, the new selection policy can be validated **offline against real data before any run is spent** (see Retrospective Replay Gate). This is a pre-run gate, not an observational nicety.

---

## Research Questions

**Primary (confirmatory):** Does span-level, density-normalized, source-aware selection form a distilled store containing the rubric-critical planted fact for **all four** domains, faithfully and without junk?

**Secondary (confirmatory):** Given successful formation, does retrieval from that store recover four-domain breadth — the first opportunity in this program to test the read path against a store that actually contains the answers?

**Tertiary (confirmatory):** Does the revised policy hold targeted recall relative to a same-seed Study 005 control?

**Observational:** How do span-level records change store compactness, context size, and retrieval composition relative to whole-turn records?

---

## What is and is not changing

**Changed (the selection policy only):**

| Element | Study 005 | Study 006 |
|---|---|---|
| Selection unit | Whole user/assistant turn episode | Sentence-level span |
| Salience | `entities + 2×numbers` (absolute) | `(entities + 2×numbers) / words` (density) |
| Source | Source-blind | User spans weighted above assistant spans |
| Eligibility | Any episode | Span must meet length window + minimum content |
| Formation bar | 3 of 4 domains | **4 of 4 domains** |

**Carried forward unchanged:** permissive append-only raw store; extractive-only dreaming with zero inference calls and the verbatim assertion; provenance-to-source; dedup at 0.95 cosine; per-topic cap C = 3; salience floor with `present_no_salient_fact` marker; dream cadence at topic transitions (≈31/61/91) plus the turn-111 flush; the read path (parallel STM∥LTM, tier-neutral arbitration, episode-ID dedup, XML-tagged blocks, top-M = 5); topic assignment and consolidation purity instrumentation; runtime, response budget, and the full determinism protocol.

**Explicitly NOT in this study:**
- **Abstractive/generative dreaming.** Extractive fidelity was never the bottleneck (100% faithful in Study 005). Adding generation would introduce a fabrication failure mode on top of an unsolved selection problem.
- **Retrieval diversity.** Its pre-registered trigger was Bar 1 pass + Bar 2 fail, which did not occur in Study 005. Formation is still first.
- **1,000-turn stress test.** Endurance testing of the assembled architecture remains its own study type, deferred until selection quality is established.

---

## Why the formation bar moves to 4 of 4

Study 005's control produced an unplanned natural experiment. The promotion-based control formed **3 of 4** domains (civil, art, marine — missing monetary) and still scored **Q11 = 0.0**. Q11 requires enumeration across all four domains; a store missing any domain cannot support it. Therefore a 3-of-4 formation bar is **logically insufficient** to enable the breadth bar that depends on it — the two bars were internally inconsistent in Study 005.

Bar 1 is therefore raised to 4 of 4. The sparse-topic `present_no_salient_fact` marker path remains implemented and is retained as an honest general-purpose mechanism, but on this script all four domains contain planted facts, so a marker in any domain is a formation failure for the purposes of Bar 1.

---

## Method

### Condition

**Condition C — Iterative Construction v6.** Identical to v5 except for the dreaming selection policy specified below.

### Runtime and seeding (pre-registered, carried from Study 005)

| Parameter | Value |
|---|---|
| Inference model | Qwen3.6 27B UD-Q6_K_XL |
| Runtime | Local llama.cpp HTTP server, /completion |
| Context capacity | 50,000 tokens (`--ctx-size 50000`) |
| Response budget | 2,048 tokens |
| Embedding model | Qwen3-Embedding-0.6B Q8_0, 1024 dims |
| Server slots | Single (`--parallel 1`) |
| Speculative decoding | Off |
| Seed | Fixed, recorded in run header; identical across arms |

Launch command (both arms, identical; server build/commit hash recorded alongside):

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

The determinism spot-check (re-run a fixed prefix under the same seed, assert turn-identical output) is a pre-run gate. Arms sharing a seed are turn-identical until their constructed contexts first diverge.

### Script

121 turns, unchanged: turns 1–120 hash-identical to Studies 002–005, Q14 at turn 121. Script SHA-256 recorded in the run header and asserted equal to the Study 005 script hash.

### Evaluation

Manual scoring, single rater, on the locked 14-question rubric (Q1–Q13 `study_002/rubric_filled.md`; Q14 `study_004/q14_criteria.md`). Scores committed before any dreaming, retrieval, or arbitration logs are opened. The facts-in-LTM, faithfulness, and non-content structural checks are computed from the distilled store and committed alongside scores.

---

## Revised Selection Policy — full specification

This section is the implementation contract. Dreaming remains **extractive**: it selects and copies existing text and makes **zero inference-model calls**. No interpretive latitude is delegated.

### 1. Span segmentation

At each dream event, for each in-scope raw episode (topic-assigned, `dreamed == false`):

1. Split the episode text into sentence-level spans. Segmenter: spaCy `en_core_web_sm` sentencizer if available; else a documented regex fallback splitting on `.!?` followed by whitespace and a capital letter or digit, with protection for common abbreviations and decimal points. The chosen segmenter is recorded in the run header.
2. Each span retains: source episode_id, source turn, role (`user` | `assistant`), character offsets into the source text.
3. Spans are the unit of scoring, selection, and storage from this point forward. Turn-level episodes are never selected as a whole.

**Character offsets are mandatory** — they are what makes the verbatim assertion checkable at span granularity.

### 2. Eligibility filter

A span is eligible for scoring only if **all** hold:
- Word count between **4 and 60** inclusive. The lower bound prevents fragment gaming (a two-token span like "3 m" would otherwise achieve maximal density); the upper bound excludes run-on spans that reintroduce the whole-turn problem.
- Contains **at least one** named entity or numeric token.

Ineligible spans are discarded for selection purposes and logged with the reason. They remain in the raw store; only their candidacy is affected.

### 3. Salience

For an eligible span `s`:

```
base(s)     = named_entity_count(s) + 2 × numeric_token_count(s)
density(s)  = base(s) / word_count(s)
salience(s) = density(s) × source_weight(role)

source_weight(user)      = 1.5
source_weight(assistant) = 1.0
```

- `numeric_token_count`: numeric tokens via regex (integers, decimals, years, measurements, percentages).
- `named_entity_count`: spaCy `en_core_web_sm` NER if available; else the documented capitalized-sequence fallback (excluding sentence-initial tokens and a stoplist). Extractor recorded in the run header.
- The **×2 numeric weight** is carried unchanged from Study 005 (planted facts are number-dense; numerals are rarer and more distinctive than capitalized nouns).
- **Density, not absolute count**, is the core correction: it makes a short dense fact outrank a long diffuse answer, which is precisely the Study 005 failure.
- The **1.5 user weight** encodes that the user is the source of ground truth in a conversation and the model's own prior output is derivative. It is a tiebreaker-scale weight, not a domination weight: a genuinely dense assistant span can still outrank a sparse user span.

All parameters (×2 numeric weight, 1.5 source weight, 4–60 word window) are locked design choices, flagged tunable in Limitations.

### 4. Deduplicate, select, coverage floor

Within each topic's eligible span set at the dream event:

1. **Dedup.** Collapse near-duplicate spans (pairwise cosine ≥ **0.95**); keep the higher-salience member; record collapsed ids as provenance on the survivor.
2. **Select.** Rank survivors by salience; take the top **C = 3** per topic.
3. **Coverage floor.** Let **F = 0.15** (minimum density-scaled salience to count as a salient fact). If the topic's top span has salience ≥ F, write the selected records. If **no** span in the topic clears F, write a single `present_no_salient_fact` marker record referencing the highest-salience span — do not promote a sub-floor span to satisfy coverage.

**Note on F:** the Study 005 floor (F = 2) was on an absolute-count scale and is not transferable to a density scale. F = 0.15 corresponds roughly to one entity-or-number per ~7 words for a user span, or ~10 words for an assistant span — a threshold that a bare acknowledgment cannot reach and a genuine planted fact clears comfortably. **F must be validated by the Retrospective Replay Gate before lock** (see below); if replay shows it excludes real plants or admits junk, F is re-derived from replay data and the revised value recorded before commit.

### 5. Write to distilled LTM

Each distilled record stores: distilled_id, topic, **verbatim span text**, provenance (source episode_id, source turn, role, character offsets), base/density/salience components, dream_event. Source episodes are marked `dreamed = true` once processed.

### 6. Extractive assertion (carried, strengthened for spans)

The dream pass makes **zero inference-model calls** (asserted programmatically). Every distilled record's text must match its source episode **exactly at the recorded character offsets**. A record whose text does not match its source span verbatim is a hard failure — stop, do not run.

### Locked parameters

| Parameter | Value | Note |
|---|---|---|
| Selection unit | sentence-level span | new |
| Word window | 4–60 | new; prevents fragment gaming and run-on spans |
| Numeric weight | ×2 | carried from 005 |
| Source weight | user 1.5 / assistant 1.0 | new |
| Salience | density (per word) | new; the core correction |
| Per-topic cap C | 3 | carried |
| Salience floor F | 0.15 | new scale; **validated/re-derived by replay before lock** |
| Dedup threshold | 0.95 cosine | carried |

---

## Retrospective Replay Gate (pre-run, mandatory)

Study 005's raw episodic store is preserved, and its plant turns and per-event salience ranks are documented. The revised selection policy can therefore be evaluated against real conversational data **before spending a run.**

**Procedure.** Replay the Study 006 selection policy offline over Study 005's preserved raw store (`study_005_full_001`), simulating the same four dream events over the same episodes, and record which spans would be selected.

**Gate criteria (all must hold to proceed):**
1. The rubric-critical planted fact is selected for **4 of 4** domains.
2. Zero non-content spans among the selected set.
3. Every selected record is verbatim from source at the recorded offsets.
4. The specific Study 005 near-misses — the plant turns that ranked 11, 16, 17, 18, 19 (marine turns 100/101/102, art turns 55/56/60) — are examined individually and their new ranks recorded, whether or not selected.

**If the gate fails:** do not run. Revise the policy (or re-derive F) against replay data, record the revision in a decision record, and re-replay. Parameter values that ship must be justified by replay evidence, not by post-hoc tuning on a live run.

**Interpretive limit (important, and stated up front):** the replay validates the policy against data the policy was designed after. It demonstrates that the mechanism *can* select the right spans from realistic conversational text; it does **not** independently confirm generalization, because the same data informed the design. Its role is to prevent spending a run on a policy that provably cannot work — not to substitute for the confirmatory run. The adversarial fixture (below) is the complementary check that the policy handles the failure *shape* rather than these specific sentences.

---

## Adversarial Fixture (pre-run, mandatory)

A synthetic fixture in which a **long, number-rich generated-style answer** competes directly against a **short user-planted fact** within the same topic — the exact shape that defeated Study 005.

**Requirements:**
- The verbose span must have a *higher absolute* entity+numeric count than the planted fact (so it would win under the Study 005 policy).
- The planted fact must have higher density.
- Multiple decoys: at least three verbose spans, so the plant must beat all of them for a top-3 slot alongside other content.
- A sub-floor acknowledgment span, to confirm junk exclusion at span granularity.

**Gate criterion:** the planted fact is selected; the verbose decoys do not crowd it out; the acknowledgment is excluded. **This fixture must fail under the Study 005 policy and pass under the Study 006 policy** — both directions are asserted, so the fixture demonstrably tests the change rather than passing trivially.

---

## Success Criteria

Baseline for non-regression is a **same-seed Study 005 control** — the Study 005 accepted treatment architecture (whole-turn selection), re-run at the Study 006 runtime and the same fixed seed. This isolates the selection-policy change: the two arms differ only in how dreaming chooses spans.

### Bar 1 — Formation (the direct target)
**The rubric-critical planted fact is present in distilled LTM for all 4 of 4 domains, every distilled record verbatim-faithful to its source span, and zero non-content records.**
- Checked directly against the distilled store, independent of retrieval, using `q_facts_key.md`.
- Study 005 result: 2/4. Study 005 control: 3/4 (and still failed breadth — see rationale above).
- All three clauses must hold: 4/4 coverage, 100% faithfulness, zero non-content.

### Bar 2 — Breadth Recovery, conditional on Bar 1
**Q11 ≥ 0.5 AND Q14 ≥ 0.5 AND (Q11 + Q14) ≥ 1.5, with the probe-turn arbitration log showing distilled records from the recovered domains.**
- **Store-content precondition (carried):** Bar 2 is evaluated only if Bar 1 passes. If the facts are not in the store, Bar 2 is recorded as **not evaluable — read path untested**, never as "failed."
- **Disentanglement (carried):** Bar 1 pass + Bar 2 fail isolates the cause to retrieval and is the pre-registered trigger to build the deferred breadth-diversity mechanism.
- This is the first study in the program in which the read path can be functionally validated, because it is the first with a plausible path to a store that contains all four domains' facts.

### Bar 3 — Targeted Recall Non-Regression
**Q1–Q13 ≥ the same-seed Study 005 control's Q1–Q13 score, with Cat 1–3 not below the control's per-category totals.**
- Study 005 treatment scored 11.0 and its control 12.0; the regression concentrated in the two domains where formation failed (Q5 art, Q8 marine). If formation succeeds in all four domains, this bar should clear — that expectation is itself informative.
- Category-analysis caveat carried: any failure is analyzed by category before verdict.
- **Judgment-call sensitivity note (carried from the Study 005 analysis):** Q5 and Q8 partial credit are the softest calls in the rubric. Where a Bar 3 verdict turns on a single 0.5, the report must state the verdict's sensitivity to that judgment rather than presenting it as a clean margin.

All three bars pass → VALIDATED. Bar 1 pass + Bar 2 not-evaluable is reported as such, not as failure. Mixed outcomes → PARTIAL, criteria unchanged.

---

## Auxiliary Control Run

**Configuration.** The **accepted Study 005 treatment implementation** (whole-turn extractive dreaming) run at the Study 006 runtime and the same fixed seed, same 121-turn script.

**Code discipline (binding, carried).** The control runs on **checked-out Study 005 code in a separate worktree**, never the Study 006 runner with span selection disabled by flag. The launcher must reject a dirty worktree, unexpected diff, wrong script hash, import escape, or the presence of the Study 006 selection engine, and must record module paths, server properties, command, and process id before inference.

**Scoring.** Full 14-question rubric, same rater. Both arms scored before any mechanism logs are opened.

---

## Observational Measures (No Pass/Fail)

| Measure | Description |
|---|---|
| Span inventory | Spans produced, eligible, ineligible (by reason) per dream event |
| Compression | Raw episodes → eligible spans → distilled records; ratio vs Study 005's 10.81% |
| Rank movement | New rank of each Study 005 plant near-miss (turns 55, 56, 60, 100, 101, 102) vs its Study 005 rank |
| Source composition | User vs assistant provenance among selected records; effect of the 1.5 weight |
| Density profile | Salience distribution of selected vs rejected spans |
| Record compactness | Mean distilled record length vs Study 005; peak context vs Study 005's 16,171 (treatment) and 10,006 (control) |
| Faithfulness | Fraction verbatim at recorded offsets (must be 100%) |
| Non-content rate | Sub-floor / acknowledgment-class records reaching LTM (must be zero) |
| Marker records | Count of `present_no_salient_fact` markers |
| Breadth retrieval anatomy | Full candidate lists + provenance for Q11 and Q14 |
| Determinism | Prefix replay identity; cross-arm prefix equality before divergence |

---

## Pre-Run Checklist (Mandatory)

- [ ] Pre-registration + `q_facts_key.md` committed; SHA recorded
- [ ] Decision record for the selection-policy revision committed with author authorization
- [ ] Server launched with the exact pre-registered flag set (no speculative decoding); command + build hash recorded
- [ ] `--seed` fixed and recorded; determinism spot-check passes
- [ ] GPU speed test > 30 tok/s, single-slot
- [ ] Segmenter and NER extractor recorded in the run header
- [ ] Span unit tests: segmentation, offsets, word window, eligibility, density, source weight, dedup, cap, floor, marker path
- [ ] Extractive assertion at span granularity: verbatim at recorded offsets; zero inference calls in dreaming
- [ ] **Adversarial fixture passes under Study 006 policy and fails under Study 005 policy**
- [ ] **Retrospective Replay Gate passes 4/4 on Study 005's preserved raw store; F validated or re-derived and recorded**
- [ ] facts-in-LTM, faithfulness, non-content harnesses verified on synthetic data
- [ ] Read path, arbitration, dedup, tagged-block carried tests pass against span records
- [ ] Consolidation purity instrumentation + probe-bridge guard carried
- [ ] Context-ceiling monitor active (alert > 80% of ctx-size)
- [ ] 35-turn ablation passes; GO/NO-GO committed

---

## Failure Conditions

| Condition | Meaning | Next action |
|---|---|---|
| Replay gate fails | Policy provably cannot select the plants | Do not run. Revise policy/F against replay data, record decision, re-replay |
| Adversarial fixture passes under the 005 policy | Fixture does not test the change | Rewrite the fixture before it can serve as a gate |
| Bar 1 fails: a domain's plant absent | Selection still misses that domain | Inspect that plant's span rank and eligibility; check segmentation split it badly |
| Bar 1 fails: non-content records present | Floor too low on the density scale | Re-derive F from data; do not tune mid-study |
| Bar 1 fails: faithfulness < 100% | Offsets or copying are wrong | Stop; extraction integrity is non-negotiable |
| Bar 1 passes, Bar 2 fails | Facts in store, retrieval buries them | **Build the deferred breadth-diversity retrieval fix** — clean, attributable trigger |
| Bar 3 fails | Span records hurt targeted recall | Examine whether short spans lost context that whole-turn records carried |
| Determinism spot-check fails | Seeding ineffective | Confirm seed and single-slot; diagnose serving/batch |
| Peak context near ctx-size | Unexpected growth | Stop, raise ctx-size, re-run |

---

## Limitations

- Single scripted run per arm, single rater, one fixed seed. A controlled paired result, not population-level performance.
- **Source weighting is script-correlated.** Weighting user spans above assistant spans is defensible in general (the user supplies ground truth; model output is derivative), but in *this* script the planted facts are user-authored, so the weight is also conveniently aligned with the answer key. This study cannot separate "user content is genuinely more valuable" from "user content happens to be where this script hid the answers." A script with model-authored target facts would be needed to disentangle, and is out of scope.
- **The replay gate uses data the policy was designed after.** It prevents spending a run on a broken policy; it does not independently establish generalization.
- Parameters (×2 numeric, 1.5 source, 4–60 word window, C = 3, F, dedup 0.95) are locked design choices, not tuned values.
- Sentence segmentation is imperfect; a fact split across two sentences may be weakened by span boundaries. Rank-movement observation should surface this if it occurs.
- The capitalized-sequence NER fallback is weaker than a trained model and can overcount formatted text (carried from Study 005).
- Extractive selection cannot fabricate, but can still mis-select; provenance catches mangling, not poor judgment.
- Context estimates are character-based approximations.
- The read-path-vs-tagging attribution gap from Study 004 remains unresolved (third arm still deferred).
- Dreaming remains extractive only; abstractive dreaming is a separate future study.

---

## Open Decisions — RESOLVED AT LOCK (2026-07-25)

All five decisions are resolved below. Resolutions 3–5 are supported by an executable pre-lock probe of all plant-key rows against `experiments/study_005/script.json` under the locked segmenter; see the decision record `decisions/DECISION_selection_policy_study006.md`.

1. **Salience floor F.** **RESOLVED — provisionally 0.15, final value deferred to the Retrospective Replay Gate (S6-T-013).** F is *not* locked at this commit. The pre-lock probe scored each planted span in isolation and found that all four domains retain at least one plant clearing 0.15 (civil 0.19/0.38, art 0.31, monetary 0.18/0.31, marine 0.41), but that 8 of 14 rows fall below it. Isolation scoring does not model competition for the top-3 slots, so replay remains the authority. F is fixed before the ablation and never after a run.
2. **Source weight magnitude.** **RESOLVED — 1.5, as recommended.** The script-correlation limitation is disclosed verbatim in Limitations and carried into the report.
3. **Word window bounds.** **RESOLVED — 4–60, as proposed, validated.** Pre-lock probe: every planted span falls inside the window (observed range 7–39 words). No planted fact is excluded by either bound.
4. **Segmenter.** **RESOLVED — spaCy.** spaCy 3.8.14 and `en_core_web_sm` 3.8.0 install cleanly on this box under Python 3.13.13, so the preferred option is taken and the regex fallback is not used. This differs from Study 005, which locked the fallback only because neither installed at the time. Recorded in the run header. The same model supplies NER, replacing the capitalized-sequence fallback.
5. **`q_facts_key.md`.** **RESOLVED — carried with one amendment.** All 13 Study 005 rows re-verified against the script: every required term appears in its stated source turn, 4 domains covered. One row, `civil_span`, is **unmatchable at span granularity** — turn 3 segments `Halcyon Crossing` and `847` into different sentences, so no single span can satisfy it. It is split into `civil_project` (Halcyon Crossing) and `civil_span` (main span; 847). All 14 resulting rows are single-span satisfiable. Full diff and rationale in `q_facts_key.md`.

### Known risks recorded at lock (not blocking)

These were surfaced by the pre-lock probe and are carried into the study as declared risks rather than resolved by parameter changes, so that replay evidence — not pre-run tuning — governs any revision:

- **`marine_photophores` is rejected at the eligibility filter.** spaCy tags no entity in it (Latin binomials such as *Vampyroteuthis infernalis* are not NER entities) and it contains no numeric token, so it scores 0.0 and never becomes a candidate. Marine-domain formation therefore rests entirely on `marine_identity`. Art rests entirely on `art_identity` for the same reason (`art_pigment` 0.05, `art_patron_role` 0.09).
- **Bar 3 regression risk is concentrated where Study 005 already failed.** Study 005's Q1–Q13 shortfall was Q5 (art) and Q8 (marine); the facts those questions depend on (`art_pigment`, `marine_photophores`) are the two lowest-scoring rows under this policy. Bar 1 may reach 4/4 while Bar 3 fails for the same reason as Study 005. This expectation is recorded before the run so that the outcome is confirmatory rather than post-hoc.

---

## Appendix

- Study 005 report: `experiments/study_005/study_005_report.md`
- Study 005 pre-registration: `experiments/study_005/pre_registration.md`
- Study 005 preserved raw store (replay input): `experiments/study_005/runs/study_005_full_001/`
- Study 004 report and A005: `experiments/study_004/`
- Authoritative rubric (Q1–Q13): `experiments/study_002/rubric_filled.md`
- Q14 criteria: `experiments/study_004/q14_criteria.md`
- Plant key: `experiments/study_006/q_facts_key.md`
- Pre-registration path: `experiments/study_006/pre_registration.md`
