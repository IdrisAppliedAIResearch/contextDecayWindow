# Study 008 — Pre-Registration (DRAFT v1)
## contextDecayWindow
**Idris Applied AI Research**
**Date:** July 2026
**Status:** LOCKED at registration commit; `c_fill` remains the single gate-calibrated parameter and must be locked before ablation.
**Amendments:** `experiments/study_008/amendments/` — blocker-driven amendments registered before affected work are binding.
**Study 007 report:** `experiments/study_007/study_007_report.md` (COMPLETE, PARTIAL, with post-run correction `fd78018`)
**Study 007 pre-registration SHA:** `d920fd8` (+ Amendments 001–003)
**Study 007 accepted treatment:** `runs/study_007_full_001` (Bar 3 PASS · Bar 1 FAIL 0.0/0.5 · Bar 2 PASS 12.0 vs 10.5)
**Correction commit:** `fd78018` — the "model ignores context" diagnosis was refuted; the model used 10/17 available facts and invented nothing. The block contained only 10/17.

---

## Summary

Study 008 is a **2×2 factorial** over the two retrieval-side decisions that Study 007's corrected diagnosis showed jointly determine whether rubric-critical facts reach the model:

- **Factor R — rendering unit:** what a selected LTM record renders as in `<retrieved_ltm>`: its whole **source episode** (Study 007 behavior, mean ≈ 4,000 chars) or its selected **span** (mean ≈ 146 chars).
- **Factor F — floor policy:** how per-topic floor picks are ranked: by **query similarity** (Study 007 behavior) or by **general informativeness** (formation's own density score), plus a **per-topic fill cap**.

| | F₀: similarity floor, uncapped fill | F₁: informativeness floor + fill cap |
|---|---|---|
| **R₀: episode rendering** | **Arm A** — reproduces Study 007 treatment | **Arm B** |
| **R₁: span rendering** | **Arm C** | **Arm D** |

**Why a factorial rather than two sequential studies: the factors interact through the budget.** At episode rendering, `B_ltm = 32,000` holds ~8 items, so `k_min = 2` across four topics consumes the whole budget — floor parameters are barely affordable. At span rendering the same budget holds ~200 items and floor parameters are nearly free. Sequential studies would calibrate each factor under the other's artifact: a floor tuned against episode-scarcity, or a rendering evaluated under a floor known to pick overviews. The factorial measures the interaction instead of assuming it away. Each factor remains separately evaluable — this is stronger isolation than sequencing, not weaker, provided all four arms run. **Running only the both-on arm is the failure mode; four arms or it is not a factorial.**

**What Study 007's correction established (the evidence this design answers):**
1. The model **used every fact it was given and invented nothing** — 10/17 rubric-critical facts in the block, the same 10/17 in the answer, zero unused, zero fabricated. The "background knowledge substitution" claim was false; that content was real conversation material from the block.
2. Lost-in-the-middle was tested and refuted — content was used at 7%–93% of a 33,406-char block, including dead centre.
3. The real failure: **the similarity floor picked topic overviews, not fact-bearing episodes** (art got the turn-31 patronage survey; its facts live in 55/56/60; monetary got turn 69; facts in 61/62/65), and **uncapped fill let the largest topic take every remaining slot** (all three went to civil). For a breadth query, similarity ranking is structurally anti-correlated with informativeness: the query embeds near the topic centroid, and the episode nearest the centroid is the summary, not the fact.
4. Bar 1's "four-domain coverage" attribution and the replay gate shared a broken surrogate — "≥1 planted term per domain" was satisfiable without rubric-critical facts (art passed on `Julius II`, monetary on `Federal Reserve`). Under the rubric's own standard the block covered two domains. This was the fifth instance of the program's recurring failure class.

Formation ships unmodified from Study 006 (third consecutive study). The budget remains `B_ltm = 32,000` characters in **all four arms** — character parity, not item parity, because context is the scarce resource; item parity would let span arms consume ~27× the context and confound both factors with budget.

---

## The recurring failure class, named and made a standing check

Study 007 produced five instances of one failure shape, four caught before the run and one after. The earlier framing ("a budget expressed as a count of variably-sized items") does not cover the fifth. The general form:

> **A surrogate that can be satisfied without the property it certifies being true.**

Instances to date: record count for delivered information (007 A001); slot count for floor cost (007 A002); `LTM_TOP_M` truncation silently defeating the floor; Study 004's arbitration cap; "any planted term" for "rubric-critical fact" (007 post-run). Retrospectively, the same shape: novelty for importance (003), absolute entity count for salience (005).

**Standing rule (extends Correction 4, applies from this study forward):** every pre-run gate criterion and every bar's attribution clause must be audited with the question *"can this check pass while the property it certifies is false?"* — and the audit recorded in the pre-registration. This document's own gates are audited in §Gate Criteria below.

---

## Research Questions

**Primary (confirmatory):** Which combination of rendering unit and floor policy delivers rubric-critical facts from all four domains to the model at the breadth probes, and does breadth recall follow?

**Secondary (confirmatory):** What does each factor cost or gain on targeted recall — in particular, does span rendering lose the accidental episode-carriage benefit that gave Study 007 full credit on Q5?

**Interaction (confirmatory):** Is the floor policy's effect dependent on the rendering unit, as the budget arithmetic predicts?

**Observational:** Delivered-fact coverage per arm; per-topic composition; containment behavior under span rendering; whether any arm's block covers all 17 rubric-critical facts.

---

## Pre-Registered Prediction Ledger

Recorded before any gate or run, so the study is falsifiable in more than one dimension. Each prediction names its refutation consequence.

| # | Prediction | If refuted |
|---|---|---|
| P1 | The corrected (fact-aware) re-derivation of Study 007's sweep shows **no** `k_min` at episode rendering reaches genuine four-domain fact coverage at `B_ltm = 32,000` — i.e., Arm B improves coverage over Arm A but does not fully solve it | Episode rendering is more viable than the diagnosis implies; the rendering factor matters less than predicted |
| P2 | Span arms (C, D) achieve strictly higher rubric-critical fact coverage in the probe blocks than their episode counterparts (A, B) | The rendering factor is not the coverage lever; revisit the delivered-unit analysis |
| P3 | **Q5 loses full credit under span rendering** (C, D score < 1.0 on Q5), because `art_pigment` is unformed and reached the model in Study 007 only via whole-episode carriage | The episode-carriage mechanism is not understood; the Study 007 Q5 explanation is wrong and must be re-derived |
| P4 | Arm D achieves the highest breadth score; Arm A the lowest | The factors do not compose as modeled |
| P5 | The informativeness floor (B, D) selects fact-bearing episodes/spans over overviews within each topic — verifiable directly in the floor-pick logs against known fact locations (art 55/56/60, monetary 61/62/65) | Density does not separate facts from overviews; the ranking hypothesis fails independent of scores |

Amendment 002 §6's claim that the floor was causally inert (`k_min = 0` also reached 4/4) was measured under the broken surrogate and is **void pending the corrected re-derivation**. It is not carried as a premise.

---

## What is and is not changing

**Changed (retrieval side only, per factor):**

**Factor F — informativeness floor + fill cap (arms B, D):**
- Floor picks within each topic are ranked by **density** — formation's own general informativeness score, `(named_entity_count + 2 × numeric_token_count) / word_count`, computed over the *rendered* unit — instead of query similarity. Similarity is the tiebreaker.
- Fill is capped at **`c_fill` per topic** (proposed 2, calibrated by replay), preventing the largest topic from consuming every remaining slot. Within the cap, fill remains pure global similarity.

**Factor R — span rendering (arms C, D):**
- `<retrieved_ltm>` renders the selected record's **span text verbatim** (with provenance attributes: source turn, role, topic, dream_event), not its source episode.
- Containment dedup inverts naturally: a span is dropped if its text is contained in an episode already present in the STM block (string containment via recorded offsets), same refill rules.
- All other read-path behavior (tags, floor protection, identifier dedup, budget accounting in characters) unchanged.

**Leakage boundary (binding, audited in code review):** the informativeness ranking must be a **general** property of the text. It is the density score and nothing else. **No component of selection, ranking, or gating may read, import, or derive from `q_facts_key.md` or any rubric artifact at any point in the retrieval path.** The distinction between "prefer dense episodes" (legitimate) and "prefer episodes containing tested facts" (leakage that voids the study) is invisible in outcomes and must be enforced structurally: the retrieval modules may not have the plant key on their import path, and the pre-run checklist includes a grep-level audit.

**Carried unchanged and diff-verified:** formation (span segmentation, density salience, C = 50, floor F, dedup, verbatim extraction, zero inference calls — third study running); STM retrieval (N + K); `B_ltm = 32,000` characters in all arms; `k_min = 1` in all arms (the floor *policy* varies, not its quota — one factor per factor); topic assignment; consolidation purity instrumentation; runtime, seed, response budget, determinism protocol; Corrections 1–4 from Study 007 (UTF-8 in code with post-decode hash assertion; human-rater/score-first/blinded protocol; dual scoring on hedge-dependent credit; stage-interface contract).

**Explicitly NOT in this study:** any formation change; abstractive dreaming; the 1,000-turn endurance study; prompting/context-presentation interventions (the corrected diagnosis showed the model uses what it receives — there is no grounding failure to fix).

---

## Method

### Arms and execution

Four arms, same fixed seed, same 121-turn script (hash asserted post-decode), same runtime and launch flags as Study 007 (recorded verbatim in each run header). All arms are byte-identical through turn 31 (empty-LTM prefix); divergence begins at turn 32 where the retrieval policies first act. Cross-arm prefix equality is verified.

Arm A runs on the **checked-out accepted Study 007 treatment implementation** in a separate worktree with the full launcher guard set — it is simultaneously the factorial's baseline cell and a reproduction check of Study 007 (target: probe blocks reproduced to the character, as Study 007's control reproduced Study 006). Arms B, C, D run on the Study 008 runner with the respective factor settings; the factor configuration of each run is recorded in its header and asserted at startup.

### Evaluation

Human rater, blinded across **four** arms (arm-anonymized directories, sealed mapping committed before scoring, opened only after scores land), locked 14-question rubric, dual scoring on hedge-dependent credit, written rationale per question. **Scores for all four arms committed before any mechanism log is opened**, verifiable from git order. Fact-coverage and formation checks computed only after the score commit.

The scoring load is 4 × 14 = 56 question-scorings — double any prior study. This is the design's real cost; the rater confirms availability before lock, and the study waits rather than substituting an agent rater (Study 007's Amendment 003 deviation is not repeated).

---

## Gate Criteria (fact-aware, audited)

All gates use the corrected standard: **a domain counts as covered only if at least one of its rubric-critical facts (per `q_facts_key.md`) is present in the delivered block text.** "Any planted term" is retired.

**Surrogate audit of this criterion (per the standing rule):** can it pass while the property it certifies is false? The certified property is "the model received the facts the rubric tests." The check searches the rendered block text for the rubric-critical fact strings — the same strings the rater will look for in answers. Residual gap: a fact present but split across a span boundary would count as absent (conservative, fails safe); a fact string present in a semantically garbled context would count as present (accepted; extraction is verbatim so garbling cannot occur by construction). Audit recorded; criterion accepted.

**Note:** the *gates* may read `q_facts_key.md` — they are measurement, not mechanism. The leakage boundary bars the *retrieval path* from it. The distinction is: anything that runs at query time inside an arm is mechanism; anything that runs offline to evaluate an arm is measurement.

### Gate 1 — Corrected re-derivation (runs first; may reshape the study)

Re-run Study 007's existing replay sweep (`B_ltm` × `k_min`, episode rendering, similarity floor) under the fact-aware criterion. This retro-validates or refutes Amendment 002 §6 and prices P1.
- **If some parameter setting reaches genuine 4/4 at episode rendering:** record it; Arm B's calibration starts there.
- **If none does (P1 confirmed):** Arm B is predicted to fail Bar 1's coverage precondition. **Arm B still runs** — the factorial needs the cell, and a confirmed prediction is evidence, not waste.

### Gate 2 — Four-arm retrieval replay

Replay all four arm configurations offline against the **Study 007 treatment's preserved distilled store** and the Q11/Q14 query embeddings. Harness fidelity check first: the Arm A configuration must reproduce Study 007's actual probe blocks to the character before any other cell's replay is trusted.
- **Calibrate `c_fill`** (arms B, D) to the smallest value at which fill cannot re-create the all-slots-to-one-topic failure, jointly with the targeted fixture below.
- **Record per-arm predicted fact coverage** at both probes — these become the run's block-level predictions, checked against the live runs.
- **Proceed condition:** at least one arm reaches fact-aware four-domain coverage at both probes. If **no** arm does, do not run — the store itself may not deliver the facts at any retrieval policy under this budget, which points back at rendering economics or formation and is a design escalation, not a tuning problem.

### Gate 3 — Targeted-retrieval fixture (fact-aware, character-costed)

Carried from Study 007 with both corrections: coverage measured by rubric-critical facts, and floor/fill cost measured in **characters with one record of bin-packing slack** (Amendment 002's re-derivation), never in slots. Per targeted query, the queried domain retains the majority of delivered characters and its top-density (arms B/D) or top-similarity (arms A/C) item. Must pass at the same parameters as Gate 2, per arm.

---

## Success Criteria

The factorial is evaluated per-arm against shared bars, plus explicit factor contrasts. Arm A is the baseline cell.

### Bar 0 — Reproduction (Arm A)
**Arm A reproduces Study 007's treatment probe blocks to the character and its scores within judgment-call variance.**
- Not a scientific bar on the new factors; it is the validity precondition for every contrast. If Arm A does not reproduce Study 007, the factorial's baseline is unanchored — stop and diagnose before interpreting any other cell.

### Bar 1 — Breadth Recovery (per arm; the direct target)
**Q11 ≥ 0.5 AND Q14 ≥ 0.5 AND (Q11 + Q14) ≥ 1.5**, with the probe-turn logs showing **fact-aware four-domain coverage** in that arm's delivered block.
- **Coverage precondition (per arm):** if an arm's block does not achieve fact-aware four-domain coverage at a probe, that arm's Bar 1 is **not evaluable — retrieval did not deliver**, distinguishing "delivered but not recalled" (which, per Study 007's correction, has never yet been observed) from "never delivered."
- The study VALIDATES on Bar 1 if **at least one arm** passes with coverage attribution; the report identifies which factor(s) that arm's pass is attributable to via the contrasts.

### Bar 2 — Targeted Recall (factor contrasts)
**No arm scores Q1–Q13 below Arm A by more than 0.5, and the R contrast (mean of C,D vs mean of A,B) and F contrast (mean of B,D vs mean of A,C) are reported with per-category breakdown.**
- The 0.5 tolerance exists because P3 *predicts* span arms lose Q5's accidental credit — a predicted, mechanism-understood loss is reported as confirmation, not regression, but a loss beyond it is real.
- Judgment-call sensitivity and dual (strict) scoring reported as in Study 007.

### Bar 3 — Formation Non-Regression (all arms)
**4/4 domains form, 100% offset-verbatim, zero non-content, zero inference calls, in every arm.**
- Formation is identical code in all arms; per-arm stores may differ in content (arms diverge from turn 32) but must not differ in these properties.

Outcome vocabulary: VALIDATED (Bar 1 pass in ≥1 arm with attribution, Bars 0/2/3 clean) · PARTIAL (mixed) · per-arm NOT-EVALUABLE states reported as such. Criteria unchanged post-lock; deviations by amendment only.

---

## Observational Measures (No Pass/Fail)

| Measure | Description |
|---|---|
| Fact delivery matrix | Per arm × probe: which of the 17 rubric-critical facts are in the block; which appear in the answer (extending the correction's 10/17 analysis to all cells) |
| Floor-pick anatomy | Per arm B/D: floor selections vs known fact locations (art 55/56/60, monetary 61/62/65) — the direct test of P5 |
| Fill composition | Per-topic fill allocation; whether `c_fill` binds |
| Delivered characters & items | Per turn per arm; block position of used vs unused content (extending the position analysis) |
| Containment behavior | Drop/refill rates under both rendering units |
| Q5 mechanism trace | Whether `art_pigment` reaches the model in each arm, and via which unit — the direct test of P3 |
| Replay-vs-live fidelity | Predicted vs actual block contents per arm |
| Store divergence | Per-arm formation output differences (expected, from turn-32 divergence) |
| Determinism | Prefix identity across arms and against Study 007's recorded hashes |

---

## Pre-Run Checklist (Mandatory)

- [ ] Pre-registration + carried `q_facts_key.md` committed; SHA recorded
- [ ] Decision record (factorial rationale, leakage boundary, surrogate-audit rule) committed with author authorization
- [ ] **Leakage audit:** grep-level and import-graph verification that no retrieval-path module reads or transitively imports `q_facts_key.md` or rubric artifacts; recorded
- [ ] **Surrogate audit** of every gate criterion and bar attribution clause recorded (per the standing rule)
- [ ] Corrections 1–4 verified active (post-decode hash assertion; stage-interface re-derivation for both rendering units — span rendering changes the delivered-unit size distribution and every downstream consumer is re-derived)
- [ ] Runtime flags + seed recorded; determinism spot-check passes; prefix matches Study 007's recorded hashes
- [ ] Unit tests: density-ranked floor with similarity tiebreak; `c_fill` cap; span rendering with provenance; containment under both units; floor protection; budget parity in characters across arms
- [ ] **Gate 1 (corrected re-derivation) run and committed; Amendment 002 §6 retro-verdict recorded; P1 priced**
- [ ] **Gate 2 (four-arm replay) passed: Arm A fidelity to the character; ≥1 arm at fact-aware 4/4 both probes; `c_fill` calibrated; per-arm block predictions recorded**
- [ ] **Gate 3 (targeted fixture, fact-aware, character-costed) passed per arm at the same parameters**
- [ ] Human rater availability confirmed for 4-arm blinded scoring; anonymization + sealed mapping apparatus ready
- [ ] Context-ceiling monitor active in all arms
- [ ] 35-turn ablation per new-code arm (B, C, D) + GO/NO-GO committed

---

## Failure Conditions

| Condition | Meaning | Next action |
|---|---|---|
| Gate 2: no arm reaches fact-aware 4/4 | The store cannot deliver the facts under any tested retrieval policy at this budget | Do not run; escalate to design (rendering economics or formation-side per-domain guarantees) |
| Arm A fails Bar 0 | Baseline unanchored | Stop; diagnose before interpreting any cell |
| An arm's live block diverges from its replay prediction | Harness or runner infidelity | The divergence is the diagnosis; resolve before bar evaluation |
| Bar 1 fails in an arm **with** fact-aware coverage delivered | Delivered-but-not-recalled — the outcome Study 007's correction showed has never yet actually been observed | This would be the first true instance; it re-opens the context-use hypothesis with clean evidence, as its own study |
| P3 refuted (span arms keep Q5) | Episode-carriage mechanism misunderstood | Re-derive the Q5 explanation before trusting any rendering conclusion |
| Leakage audit failure at any point | Retrieval path touched rubric artifacts | The affected arm(s) are void; fix and re-run |
| Formation differs across arms in Bar 3 properties | Out-of-scope change leaked in | Stop; diff-review |
| Determinism spot-check fails | Seeding ineffective | Confirm seed/single-slot; diagnose serving |

---

## Limitations

- One seed, one script, one rater; four cells but n = 1 per cell. The factorial structures the comparison; it does not add statistical power.
- `c_fill` and the informativeness ranking are calibrated on replay data from the very store under test; the live runs and the pre-registered predictions are the out-of-sample checks.
- Density is a general informativeness proxy — the same proxy family that failed as *salience* in Study 005. Its use here is narrower (ranking within an already-formed topic, where the overview-vs-fact contrast is exactly an entity/number-density contrast), and P5 tests it directly against known fact locations; but it remains a surrogate, and the standing audit applies to it.
- Span rendering deliberately gives up episode-carriage of unformed facts (P3); if confirmed, span arms trade Q5 for breadth, and the right long-term resolution (e.g., rendering spans with minimal surrounding context) is future work, not this study.
- The six unformed plants persist in all arms; Q1–Q13 remains formation-bounded except where episode-carriage compensates.
- Source weighting remains script-correlated (carried verbatim; unresolved).
- Four balanced domains; floor and cap scaling with many topics untested.

---

## Open Decisions Before Lock

1. **`c_fill`** — proposed 2 per topic; calibrated by Gate 2 jointly with Gate 3. [DECISION]
2. **Density over rendered unit vs stored span** (arms B/D): proposed rendered unit (rank what will actually be delivered). Alternative: stored span only. Recommendation: rendered unit. [DECISION]
3. **Span rendering context** — proposed bare span verbatim. Alternative: span + one neighboring sentence. Recommendation: bare span; neighbor-context is a third level of Factor R and belongs to future work. [DECISION]
4. **Ablation scope** — proposed per new-code arm (B, C, D); Arm A is covered by its reproduction property. [DECISION]
5. **Rater logistics** — confirm human rater for 56 blinded scorings; the study waits if unavailable. [DECISION]

---

## Appendix

- Study 007 report + correction: `experiments/study_007/study_007_report.md`, commit `fd78018` (reproduction script included)
- Study 007 preserved treatment store (replay input): `experiments/study_007/runs/study_007_full_001/`
- Study 007 amendments 001–003: `experiments/study_007/amendments/`
- Study 006 report: `experiments/study_006/study_006_report.md`
- Authoritative rubric (Q1–Q13): `experiments/study_002/rubric_filled.md`
- Q14 criteria: `experiments/study_004/q14_criteria.md`
- Plant key (measurement only; barred from the retrieval path): `experiments/study_008/q_facts_key.md`
- Pre-registration path: `experiments/study_008/pre_registration.md`
