# Study 008 — Sprint Plan
## contextDecayWindow
**Idris Applied AI Research**
**Date:** July 2026
**Pre-registration:** `experiments/study_008/pre_registration.md`
**Task numbering:** S8-T-001 onward
**Sprint numbering:** S8_001–S8_009
**Green light at S8_006** (ablation GO). S8_007–S8_009 are the four-arm execution, scoring, and close.

**Reading order for the coding agent:** the pre-registration is the design contract. Where this plan and the pre-registration appear to differ, the pre-registration wins — stop and flag. Introduce no parameters or architectural choices not stated in one of the two documents.

**Scope discipline for this study:** two factors and nothing else. Factor F (informativeness floor + fill cap) and Factor R (span rendering) are the entire change surface. Formation, STM, `B_ltm = 32,000`, `k_min = 1`, runtime, and seed are carried and diff-verified. If implementation pressure suggests touching formation, salience, C, STM, the budget value, or the floor quota — stop and flag.

**The leakage boundary is a standing tripwire for every sprint:** no retrieval-path module may read, import, or transitively depend on `q_facts_key.md` or any rubric artifact. Gates and harnesses (offline measurement) may. Every sprint's acceptance includes not violating this; S8_001 establishes the audit and it re-runs at the ablation.

---

## Dependency overview

```
S8_001  lock + decision record + leakage/surrogate audits + Gate 1 (corrected re-derivation)
   │
S8_002  Factor F: informativeness floor + per-topic fill cap
   │
S8_003  Factor R: span rendering + containment inversion
   │
S8_004  Gate 3: targeted fixture (fact-aware, character-costed), per arm
   │
S8_005  Gate 2: four-arm replay on Study 007's preserved store; calibrate c_fill; record block predictions
   │
S8_006  35-turn ablations (arms B, C, D) + GO/NO-GO   ◄── GREEN LIGHT
   │
S8_007  four-arm execution (A = checked-out 007 reproduction; B, C, D on the v8 runner)
S8_008  blinded 4-arm human scoring → fact matrices → bars + factor contrasts
S8_009  report + memory files
```

**Order rationale.** Gate 1 runs in the *first* sprint because it needs no new code (it re-runs Study 007's existing sweep under the corrected criterion) and its output prices P1 and sets Arm B's calibration start — it can reshape expectations before a line of factor code is written. Gates 2 and 3 must pass jointly at the same parameters; Gate 2 additionally emits per-arm block predictions that S8_007's live runs are checked against, so replay-vs-live fidelity is a designed measurement, not a post-hoc comparison.

---

## Sprint S8_001 — Lock, Audits, Gate 1
**Goal:** Commit the locked pre-registration; establish the leakage and surrogate audits; run the corrected re-derivation.

#### S8-T-001 — Commit pre-registration and plant key
Copy the pre-registration to `experiments/study_008/pre_registration.md`; carry `q_facts_key.md` forward and re-verify the 17 rubric-critical facts and their source turns against the correction commit `fd78018`'s item list. Commit together; record the SHA.
- **Acceptance:** both files committed; fact list matches the correction's 17-item enumeration; SHA recorded; no implementation files in the commit.

#### S8-T-002 — Decision record
`DECISION_factorial_study008.md`: the corrected Study 007 diagnosis (model used 10/10 available; floor picked overviews; fill uncapped; surrogate coverage criterion), the factorial rationale (budget-mediated interaction between rendering and floor policy), the character-parity decision, the leakage boundary, the surrogate-audit standing rule, and rejected alternatives (sequential studies; both-on single arm; prompting study) with one line each. Author-authorization line required.
- **Acceptance:** committed with authorization; references resolve.

#### S8-T-003 — Leakage audit apparatus
Implement the structural enforcement: retrieval-path modules must not read or transitively import `q_facts_key.md` or rubric artifacts. Deliver a grep-level scan plus an import-graph check, runnable as a single command, wired into the test suite so it runs continuously rather than once.
- **Acceptance:** audit passes on the current tree; a deliberately planted violation (test-only) is detected by both the grep and the import-graph check; audit output committed.

#### S8-T-004 — Surrogate audits
For each gate criterion and each bar attribution clause in the pre-registration, record the audit answer to "can this check pass while the certified property is false?" in `decisions/surrogate_audit_study008.md`.
- **Acceptance:** every gate and bar clause has a recorded audit; residual gaps explicitly accepted or fixed.

#### S8-T-005 — Gate 1: corrected re-derivation
Re-run Study 007's existing replay sweep (episode rendering, similarity floor, `B_ltm` × `k_min` grid) under the fact-aware coverage criterion. Record the retro-verdict on Amendment 002 §6's floor-inertness claim and the P1 verdict.
- **Acceptance:** `replay/gate1_rederivation_report.md` committed with the corrected frontier, the Amendment 002 §6 retro-verdict, and P1 priced (confirmed → Arm B predicted to miss coverage; refuted → Arm B's calibration start recorded). Read-only against Study 007 artifacts, hash-verified.

**Complete when:** lock committed, audits standing, Gate 1 verdict on record.

---

## Sprint S8_002 — Factor F: Informativeness Floor + Fill Cap
**Goal:** Build the F₁ policy. Floor ranks by density; fill capped per topic.

#### S8-T-006 — Density-ranked floor
Within each topic, rank floor candidates by the density score `(named_entity_count + 2 × numeric_token_count) / word_count` computed over the **rendered unit** (per open decision 2 as locked), query similarity as tiebreaker. `k_min = 1` unchanged.
- **Acceptance:** unit tests — a fact-bearing episode outranks a topic overview of equal similarity; equal-density candidates tie-break by similarity; the density function is the same implementation formation uses (imported, not duplicated — one source of truth); leakage audit still passes.

#### S8-T-007 — Per-topic fill cap
Cap fill at `c_fill` records per topic (value from Gate 2 calibration; parameterized until locked). Within the cap, fill remains pure global similarity. Floor picks do not count against their topic's fill cap.
- **Acceptance:** unit tests — a topic with many high-similarity records is limited to `c_fill` fill slots; remaining budget flows to other topics' next-ranked records; the Study 007 failure shape (all fill to one topic) is reproducible with the cap disabled and impossible with it enabled.

**Complete when:** F₁ selects dense floor picks and bounded fill, with the leakage audit clean.

---

## Sprint S8_003 — Factor R: Span Rendering
**Goal:** Build the R₁ rendering. `<retrieved_ltm>` delivers the selected span verbatim.

#### S8-T-008 — Span rendering
Render each selected record as its span text with provenance attributes (source turn, role, topic, dream_event). Character budgeting accounts the span's rendered length. Floor protection, identifier dedup, and tag structure unchanged.
- **Acceptance:** unit tests — rendered block contains span text, not episode text; budget accounting matches rendered lengths; provenance attributes present; a snapshot fixture of a rendered block matches expected output byte-for-byte.

#### S8-T-009 — Containment inversion
Under span rendering, drop a span whose text is contained (via recorded offsets) in an episode already present in the STM block; same refill rules; floor preserved through refill.
- **Acceptance:** unit tests — a span contained in an STM episode is dropped and logged; refill replaces a dropped floor pick from the same topic; episode-rendering containment (Study 007 direction) still works unchanged for arms A/B; both directions selected by the arm's R factor, asserted at startup.

#### S8-T-010 — Stage-interface re-derivation for R₁
Span rendering changes the delivered-unit size distribution (~146 vs ~4,000 chars). Per Correction 4, enumerate and re-derive every downstream consumer: budget utilization expectations, context-size projections, ceiling monitor thresholds, log schemas, containment semantics.
- **Acceptance:** written re-derivation appended to the decision record; no consumer still assumes episode-scale units in span arms.

**Complete when:** both rendering modes are selectable, correct, and downstream-re-derived.

---

## Sprint S8_004 — Gate 3: Targeted Fixture (Fact-Aware, Character-Costed)
**Goal:** Bound the floor/cap cost to targeted queries, per arm, under the corrected criteria.

#### S8-T-011 — Update and run the fixture
Carry Study 007's targeted fixture with both corrections: coverage by rubric-critical facts; cost in characters with one record of bin-packing slack. Run per arm configuration against Study 007's preserved store.
- **Gate criteria per arm:** the queried domain retains the majority of delivered characters; its top item (top-density for B/D, top-similarity for A/C) is present; floor+cap cost bounded per the character-costed criterion.
- **Acceptance:** `tests/targeted_fixture_report.md` committed with per-arm, per-query splits; failures route to `c_fill`/parameter adjustment jointly with Gate 2, never to criterion softening.

**Complete when:** the targeted cost of both factors is measured and within criteria per arm.

---

## Sprint S8_005 — Gate 2: Four-Arm Replay + Calibration + Predictions
**Goal:** Predict every arm's probe blocks offline; calibrate `c_fill`; establish the proceed condition.

#### S8-T-012 — Harness fidelity check
Replay the Arm A configuration against Study 007's preserved treatment store and the Q11/Q14 embeddings. It must reproduce Study 007's actual probe blocks **to the character**.
- **Acceptance:** byte-level reproduction confirmed. **If not, stop — no other cell's replay is trustworthy.** Study 007 artifacts hash-verified read-only.

#### S8-T-013 — Four-arm replay and c_fill calibration
Replay arms B, C, D. Calibrate `c_fill` (with Gate 3 jointly) to the smallest value preventing single-topic fill capture. Record each arm's predicted block contents and fact-aware coverage at both probes.
- **Acceptance:** `replay/gate2_report.md` committed with per-arm predicted blocks, coverage verdicts, the calibrated `c_fill`, and the P2/P5 replay-level verdicts (span arms' coverage vs episode arms'; density floor's picks vs known fact locations).

#### S8-T-014 — Proceed condition and parameter lock
Proceed iff ≥1 arm reaches fact-aware four-domain coverage at both probes. Lock `c_fill` and record all four arm configurations in the pre-registration before the ablation.
- **Acceptance:** proceed/stop decision committed; on proceed, locked parameters recorded; git order shows lock precedes ablation. On stop: escalation note (rendering economics or formation-side guarantees) — do not run.

**Complete when:** predictions are on record, parameters locked, proceed condition met.

---

## Sprint S8_006 — 35-Turn Ablations + GO/NO-GO — GREEN LIGHT
**Goal:** Real-script integration per new-code arm, then authorization.

#### S8-T-015 — Ablations for arms B, C, D
Turns 1–35 per arm, seeded. Reaches the first dream pass (~31) and two LTM turns — enough to exercise each arm's floor policy, rendering, containment, and budgeting on the degenerate single-topic case. Arm A needs no ablation (covered by Bar 0 reproduction). Per-arm checklist: speed; determinism (prefix identical across arms and to Study 007's recorded hashes); post-decode script hash; formation diff-clean; budget respected; factor configuration asserted in header; rendering/floor behavior per factor; containment direction correct; logs populated; leakage audit re-run clean; context ceiling.
- **Acceptance:** all applicable checks pass per arm; `ablation/ablation_report.md` committed; any failure → diagnose, fix, re-run that arm's ablation from scratch.

#### S8-T-016 — Go/No-Go (GREEN LIGHT)
```
DECISION: GO — Gates 1–3 passed and committed; per-arm ablations clean; parameters locked; predictions on record. Four-arm execution authorized.
```
or NO-GO naming the failed check. Commit before any full run.
- **Acceptance:** explicit GO/NO-GO committed. **← GREEN LIGHT**

---

## Sprint S8_007 — Four-Arm Execution
**Goal:** Run all four arms under the fixed seed. Log everything. No scoring, no mechanism-log reading.

#### S8-T-017 — Arm A (reproduction baseline)
Run the checked-out accepted Study 007 treatment implementation in a separate worktree, full launcher guard set (dirty worktree, unexpected diff, wrong post-decode hash, import escape, presence of the v8 engine), into `arms/arm_A/run_001/`. Permitted deviation: none beyond what Study 007's own runner already contains.
- **Acceptance:** 121 turns; guards recorded; probe blocks match Study 007's to the character (Bar 0 check data captured, not evaluated).

#### S8-T-018 — Arms B, C, D
Run each on the v8 runner with its factor configuration asserted at startup, into `arms/arm_{B,C,D}/run_001/`. All log handles (dream events, distilled snapshots, `retrieval_budget.csv`, fact-delivery capture, arbitration, context sizes, purity) open before turn 1. Dream passes 31/61/91/111; turn-111 before 112; Q14 at 121; carried monitoring rules.
- **Acceptance:** 121 turns per arm; cross-arm prefix equality through turn 31 verified; per-arm logs complete; peak context recorded per arm.

**Complete when:** four arms complete with logs sealed and unread.

---

## Sprint S8_008 — Blinded Scoring, Fact Matrices, Bars, Contrasts
**Goal:** Human scores first, blind, all four arms; then measurement; then bars and factor contrasts.

#### S8-T-019 — Blinded scoring inputs
Extract probe responses into four arm-anonymized directories with a sealed mapping (committed, unopened). Randomize arm order per question set so position does not leak identity.
- **Acceptance:** anonymized inputs + sealed mapping committed before any scoring; git order verifiable.

#### S8-T-020 — Human rater scores all four arms
Q1–Q14 × 4 arms (56 scorings), blind, locked rubric, dual scoring on hedge-dependent credit, written rationale per question. **No mechanism log opened by anyone before the score commit.**
- **Acceptance:** primary + strict scores + rationales committed at `evaluation/rubric_scores.json`; git order shows scores precede all mechanism reads; mapping unsealed only after.

#### S8-T-021 — Fact matrices and formation checks
Compute the 17-fact delivery matrix per arm × probe (in-block / in-answer / unused / invented — extending the correction's analysis to all cells); run formation, offset-faithfulness, non-content, and inference-call checks per arm.
- **Acceptance:** matrices and formation outputs committed after the score commit (git-verified).

#### S8-T-022 — Bars and factor contrasts
Evaluate Bar 0 (Arm A reproduction), Bar 3 per arm (formation), Bar 1 per arm (breadth, with fact-aware coverage precondition and per-arm not-evaluable states), Bar 2 (per-arm vs Arm A with the 0.5 tolerance; R and F contrasts with per-category breakdown). Score each prediction P1–P5 against the evidence, explicitly, each with confirmed/refuted and the pre-registered consequence. Check replay-vs-live block fidelity per arm; any divergence is analyzed before verdicts.
- **Acceptance:** `evaluation/study_008_results.json` committed: per-arm bar table, both factor contrasts, P1–P5 ledger verdicts, replay-fidelity check, and the sensitivity notes (judgment calls, strict scoring).

#### S8-T-023 — Mechanism analysis
Observational measures per the pre-registration: fact matrices, floor-pick anatomy vs known fact locations (P5), fill composition and cap binding, delivered characters/items and position-of-use, containment behavior under both units, Q5 mechanism trace (P3), store divergence, determinism evidence. `ltm_analysis/analysis_report.md`; no pass/fail interpretation.

**Complete when:** scores locked first, matrices computed second, bars and the prediction ledger adjudicated third.

---

## Sprint S8_009 — Report + Memory Files
**Goal:** Report the factorial; update memory; close.

#### S8-T-024 — Report
`experiments/study_008/study_008_report.md`, carried structure, leading with the factorial table of per-arm results. The discussion must state plainly: (a) which factor(s) a Bar 1 pass is attributable to, via the contrasts — or, if no arm passed, whether any arm produced the never-yet-observed delivered-but-not-recalled outcome; (b) the P1–P5 ledger with each prediction's verdict and consequence; (c) what span rendering cost on Q5 and whether the episode-carriage mechanism held (P3); (d) whether the density floor picked facts over overviews against the known locations (P5); (e) the interaction term — did the floor policy's effect depend on the rendering unit as the budget arithmetic predicted. Carry the source-weight and unformed-plants limitations verbatim. If the study validates, state explicitly what the first end-to-end breadth recovery in the program's history required, study by study.

#### S8-T-025 — Memory files
Update `MUZAFFER_PROFILE.md` and `CLAUDE_CONTEXT.md`: Study 008 result per arm; the corrected Study 007 diagnosis and the surrogate failure class as standing program knowledge; the brain-pipeline status; the next study per outcome (endurance study if breadth recovered; delivered-but-not-recalled follow-up if that outcome appeared; rendering-with-context work if P3's trade needs resolving). Update timestamps.

#### S8-T-026 — Close
Report, memory files, four arms' logs, gate reports (1–3), fact matrices, prediction ledger, scoring artifacts with sealed-mapping history, decision record, surrogate and leakage audits — all committed. Pre-registration SHA in the report header.

---

## Summary

| Sprint | Scope | Output | Gate |
|---|---|---|---|
| S8_001 | Lock, audits, Gate 1 | Re-derivation verdict, P1 priced | leakage + surrogate audits standing |
| S8_002 | Factor F (density floor + fill cap) | F₁ policy | overview-vs-fact test; cap kills capture |
| S8_003 | Factor R (span rendering) | R₁ rendering | budget parity; containment inversion |
| S8_004 | Gate 3 (targeted, fact-aware, char-costed) | Fixture report | majority-budget per queried domain |
| S8_005 | Gate 2 (four-arm replay) | Predictions, locked c_fill | Arm A to-the-character; ≥1 arm at 4/4 |
| **S8_006** | **Ablations B/C/D + GO/NO-GO** | **Ablation report** | **← GREEN LIGHT** |
| S8_007 | Four-arm execution | Four runs, logs sealed | prefix equality; 121 turns × 4 |
| S8_008 | Blinded scoring → matrices → bars | Results + P-ledger verdicts | **scores before any mechanism log** |
| S8_009 | Report + memory | Study closed | all committed |
