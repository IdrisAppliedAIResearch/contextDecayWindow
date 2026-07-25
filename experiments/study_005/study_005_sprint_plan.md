# Study 005 — Sprint Plan
## contextDecayWindow
**Idris Applied AI Research**
**Date:** July 2026
**Pre-registration:** `experiments/study_005/pre_registration.md`
**Task numbering:** S5-T-001 onward
**Green light at S5_007** (ablation GO). S5_008–S5_010 are post-authorization run, scoring, close.

**Reading order for the coding agent:** the pre-registration is the design contract. Where this plan and the pre-registration appear to differ, the pre-registration wins — stop and flag. Do not introduce parameters or architectural choices not stated in one of the two documents. The dreaming specification is the load-bearing new work; implement it to the letter, especially the extractive constraint and the coverage salience floor.

---

## Dependency overview

```
S5_001  pre-reg lock + decision records + seeding infra + runtime confirm
   │
S5_002  permissive raw store + retire promotion filters          ── write path becomes append-only
   │
S5_003  extractive dreaming component (salience/dedup/select/coverage/provenance)   ── the new component
   │
S5_004  dream cadence integration + read path retargeted to distilled LTM
   │
S5_005  facts-in-LTM + faithfulness + non-content harnesses + scoring wiring
   │
S5_006  synthetic mini-script end-to-end (incl. sparse-topic floor case, determinism)
   │
S5_007  35-turn ablation + GO/NO-GO   ◄── GREEN LIGHT
   │
S5_008  seeded control run (004 v4 arch) + full v5 run
S5_009  scoring + facts-in-LTM + faithfulness + bars
S5_010  report + memory files
```

Order rationale: the write path becomes permissive (S5_002) before dreaming is built (S5_003), because dreaming reads the raw store. Cadence and read-path retargeting (S5_004) sit on top. The measurement harnesses (S5_005) that make the study's central disentanglement possible are verified before the synthetic run. Nothing verifiable in isolation waits for the ablation.

---

## Sprint S5_001 — Pre-Registration Lock, Decision Records, Seeding, Runtime
**Goal:** Commit the locked pre-registration and plant key. Record the inversion and seeding decisions. Stand up deterministic seeding. Confirm the carried runtime.

#### S5-T-001 — Commit pre-registration and plant key
Copy the pre-registration to `experiments/study_005/pre_registration.md`. Author and commit `q_facts_key.md` — the per-domain list of rubric-critical planted facts (drawn from the Q4/Q5/Q7/Q8/Q10 and breadth-probe scoring keys) that Bar 1 checks distilled LTM against. Commit together; record the pre-registration SHA in its header.
- **Acceptance:** both files under `experiments/study_005/`; plant key enumerates ≥1 target fact per domain with the source turn(s); SHA recorded.

#### S5-T-002 — Decision records
`DECISION_promotion_inversion_study005.md` (permissive store + extractive dreaming replaces promotion; the four filters and association-decoupling retire; rationale = Study 004 promotion-selectivity failure) and `DECISION_seeding_study005.md` (mandatory seeding, single-slot, rationale = self-feedback property). Author-authorization line on each.
- **Acceptance:** both committed with authorization.

#### S5-T-003 — Seeding infrastructure and runtime confirm
Launch the llama.cpp server with the exact pre-registered flag set (`--ctx-size 50000 --parallel 1 --cache-type-k/v q8_0 --flash-attn on --jinja --metrics --temp 1 --top-p 0.95 --top-k 20 --min-p 0.0 --presence-penalty 0.0 --repeat-penalty 1.0 --seed 5005`; **no speculative-decoding flags**). Record the full command and the server build hash in the run header. Confirm the embedding model is unchanged. Run the GPU speed test comparing tok/s at 120k vs 50k ctx-size (>30 tok/s floor, single-slot); retain the faster, record the chosen ctx-size. Run the **determinism spot-check**: same seed, run a ~10-turn prefix twice, assert turn-identical output.
- **Acceptance:** exact flags + `--seed` recorded, no spec-decoding flags present; speed floor met and ctx-size choice recorded; prefix re-run is turn-identical; context-ceiling monitor active (alert if any turn > 80% of ctx-size). If the spot-check fails, confirm the seed and single-slot, then diagnose serving/batch before continuing.

**Complete when:** pre-reg + plant key committed, decision records committed, seeding verified deterministic on a prefix.

---

## Sprint S5_002 — Permissive Raw Store; Retire Promotion
**Goal:** Turn the write path into an append-only raw episodic store and remove the promotion machinery. Keep topic assignment and purity instrumentation.

#### S5-T-004 — Append-only raw store
Every turn stored as an episode (episode_id, turn, role, text, embedding, assigned_topic, `dreamed=false`). No write-time filter. Non-content turns stored like any other.
- **Acceptance:** a synthetic "got it" turn is present in the raw store; store is append-only (no deletions/filters on the write path); topic assignment still populates `assigned_topic`.

#### S5-T-005 — Retire promotion filters
Remove/disable the four Study 003 filters, the weighted threshold, the all-or-nothing bypass, and the Study 004 association-decoupling. Retain topic assignment (user-message embeddings, canonical mapping) and consolidation purity instrumentation + probe-bridge guard.
- **Acceptance:** diff-review confirms no promotion-filter code executes on the write path; topic assignment and purity instrumentation still run; carried purity tests pass.

**Complete when:** raw store append-only and permissive; promotion retired; topic/purity infrastructure intact.

---

## Sprint S5_003 — Extractive Dreaming (New Component)
**Goal:** Implement dreaming to the pre-registration's letter. Extractive only — zero inference calls.

#### S5-T-006 — Salience scoring
`salience(e) = named_entity_count(e) + 2 × numeric_token_count(e)`. Numeric tokens via regex (integers, decimals, years, measurements). Named entities via spaCy `en_core_web_sm` if available, else the documented capitalized-sequence fallback; record which extractor was used.
- **Acceptance:** unit tests — a planted fact scores high; "got it" scores 0; a number-dense sentence outscores an equally long entity-only sentence (the ×2 weight is observable); extractor recorded in header.

#### S5-T-007 — Dedup, select, coverage-with-floor
Within a topic's `dreamed==false` snapshot: collapse pairwise cosine ≥ 0.95 (keep higher salience, record collapsed ids); rank by salience; take top C=3; apply coverage floor F=2 — guarantee ≥1 record iff the top episode ≥ F, else write a single `present_no_salient_fact` marker (do not promote a sub-floor episode).
- **Acceptance:** unit tests — dedup collapses a near-duplicate restatement; cap limits to 3; a topic with all sub-F episodes yields a marker, not a forced record; a topic with a clearing episode yields ≥1 real record.

#### S5-T-008 — Write distilled LTM + extractive assertion
Write records (distilled_id, topic, verbatim source text, provenance = source episode_id(s)/turn(s), salience, dream_event); mark sources `dreamed=true`. Assert every distilled record text is a verbatim span of a source episode; assert zero inference-model calls occurred in the pass.
- **Acceptance:** provenance resolves to real source episodes; extractive assertion passes on valid data and **trips** on a deliberately mangled record (test both); inference-call counter is zero across a dream pass.

**Complete when:** dreaming scores, dedups, selects, enforces floored coverage, writes verbatim provenance-bearing records, and provably makes no inference calls.

---

## Sprint S5_004 — Cadence Integration + Read Path Retarget
**Goal:** Fire dreaming during the run and point the read path at distilled LTM.

#### S5-T-009 — Dream cadence
Dream passes at topic transitions (≈31/61/91) and the turn-111 flush point. Turn-111 completes before turn 112. Probe-block turns (112–121) never dreamed. Distilled LTM non-empty before turn 112.
- **Acceptance:** on a synthetic multi-topic script, passes fire at the transitions and 111; assertion blocks turn 112 until the 111 pass writes; no dreaming on 112–121.

#### S5-T-010 — Retarget read path to distilled LTM
The LTM tier queries distilled LTM (top-M=5 by cosine). Arbitration, dedup, tier-neutral ranking, tagged blocks all carried unchanged; only the LTM source changes.
- **Acceptance:** carried arbitration/dedup/tagging tests still pass against the distilled store; `<retrieved_ltm>` renders distilled records with provenance metadata; empty-store turns render self-closing.

**Complete when:** dreaming populates distilled LTM on cadence and the read path retrieves from it with carried behavior intact.

---

## Sprint S5_005 — Measurement Harnesses + Scoring Wiring
**Goal:** Build the checks that make the study's disentanglement real.

#### S5-T-011 — facts-in-LTM harness
Given `q_facts_key.md`, check distilled LTM for each domain's rubric-critical fact (string/entity match against provenance text). Output per-domain present/absent and the Bar 1 verdict (≥3/4 with zero non-content records).
- **Acceptance:** on synthetic data with a known planted fact present, harness reports present for that domain; with it withheld, absent; non-content record in LTM flips the zero-non-content clause to fail.

#### S5-T-012 — faithfulness + non-content harnesses
Faithfulness: fraction of distilled records matching a source episode verbatim (must be 100%). Non-content: count of sub-F/acknowledgment-class records in LTM.
- **Acceptance:** faithfulness = 100% on valid data, < 100% flagged on a planted mangled record; non-content count correct on seeded junk.

#### S5-T-013 — Scoring wiring
14-question rubric harness (Q1–Q13 + Q14). Bar arithmetic: Bar 1 (facts-in-LTM), Bar 2 (breadth, conditional on Bar 1, with not-evaluable state), Bar 3 (≥ seeded control). Scores committed before logs opened.
- **Acceptance:** harness records all 14; Bar 2 correctly enters "not evaluable" when Bar 1 fails; Bar 3 reads the control score.

**Complete when:** all three harnesses verified and scoring wired with the conditional-Bar-2 logic.

---

## Sprint S5_006 — Synthetic Mini-Script End-to-End
**Goal:** Exercise every new mechanism before the real ablation — dreaming, the sparse-topic floor path, extractive assertion, facts-in-LTM readout, determinism.

#### S5-T-014 — Author synthetic script
`tests/synthetic_study005_script.json` (~24 turns): ≥3 topics; one topic seeded with a clear planted fact; **one deliberately sparse/non-content topic** (only acknowledgments) to exercise the F floor + marker path; a breadth query; a flush point; a probe-block bridge turn (purity guard); a near-duplicate restatement (dedup).
- **Acceptance:** script produces the multi-topic + sparse-topic + breadth + flush + bridge + duplicate conditions; committed fixture-only.

#### S5-T-015 — Run synthetic end-to-end
Real embeddings, real arbitration, real dreaming — no mocks. Verify:

| Check | Expected |
|-------|----------|
| Raw store permissive | Non-content turns stored |
| Salience/dedup/select | Duplicate collapsed; cap respected; ×2 weight visible |
| Coverage floor | Sparse topic → `present_no_salient_fact` marker, not a forced record |
| Extractive assertion | All distilled records verbatim; zero inference calls in dream passes |
| Cadence | Passes at transitions + flush; distilled LTM non-empty before probes |
| Read path | Distilled records reach `<retrieved_ltm>` with provenance |
| facts-in-LTM | Planted fact reported present; withheld fact reported absent |
| Non-content in LTM | Zero |
| Determinism | Re-run under same seed is turn-identical |
| Purity guard | Bridge-turn merge blocked and logged |

Document in `tests/synthetic_verification_report.md`.
- **Acceptance:** all checks pass; report committed; any failure → fix and re-run before the ablation.

**Complete when:** every new mechanism verified end-to-end and reported.

---

## Sprint S5_007 — 35-Turn Ablation + GO/NO-GO — GREEN LIGHT
**Goal:** Real-script ablation and the go/no-go.

#### S5-T-016 — 35-turn ablation
Turns 1–35 of the real script under v5, seeded. 35 turns reaches the first topic transition (~31), so the first dream pass fires and distilled LTM becomes non-empty. Mechanisms not reachable by turn 35 (turn-111 flush, probe guard, breadth probes, sparse-topic floor) were verified on the synthetic script in S5_006.

| Check | Expected | Actual | Pass? |
|-------|----------|--------|-------|
| Speed (single-slot) | >30 tok/s | | |
| Determinism | prefix re-run identical | | |
| Raw store append-only | non-content stored | | |
| Promotion absent | no filter code runs | | |
| First dream pass | fires at ~31 | | |
| Distilled records written | ≥1, verbatim, provenance resolves | | |
| Extractive assertion | passes; zero inference calls in dream | | |
| Read path from distilled LTM | ≥1 distilled record in a post-31 context | | |
| facts-in-LTM (civil) | civil planted fact present after event 31 | | |
| Non-content in LTM | zero | | |
| Arbitration/dedup | carried behavior intact | | |
| Purity | no cross-domain merge (n/a probe range) | | |

- **Acceptance:** all applicable checks pass; report `ablation/ablation_report.md` committed; any failure → diagnose, fix, re-run from scratch.

#### S5-T-017 — Go/No-Go (GREEN LIGHT)
Write the decision line:
```
DECISION: GO — all applicable checks passed; synthetic verification covered flush/guard/floor/breadth/determinism. Control + full v5 run authorized.
```
or a NO-GO with the failed check and reason. Commit before any full run.
- **Acceptance:** explicit GO/NO-GO committed. On GO, proceed to S5_008.

**Complete when:** ablation report committed with GO and all applicable checks passing. **← GREEN LIGHT**

---

## Sprint S5_008 — Seeded Control + Full v5 Run
**Goal:** Run both arms under the fixed seed. Log everything. Do not score during runs.

#### S5-T-018 — Seeded promotion control
Run the accepted Study 004 v4 implementation at the v5 runtime, same fixed seed and sampling, same 121-turn script, into `experiments/study_005/controls/promotion_seeded/run_001/`. This is the real committed 004 architecture (not a flag-crippled v5).
- **Acceptance:** 121 turns, no truncation; logs preserved; seed recorded.

#### S5-T-019 — Full v5 run
Run all 121 turns under v5, seeded, into `runs/study_005_full_001/`. All log handles (arbitration, dream events, distilled-LTM snapshots, context sizes, purity) open before turn 1. Dream passes at 31/61/91/111; turn-111 before 112; Q14 at 121. Monitoring per carried rules (≥3 consecutive empty/truncated → stop).
- **Acceptance:** 121 turns; four dream events logged; distilled-LTM snapshot per event; `arbitration_events.csv` 121 rows; peak context recorded.

---

## Sprint S5_009 — Scoring, Formation Checks, Bars
**Goal:** Score both arms; run the structural checks; evaluate the bars — scores committed before logs opened.

#### S5-T-020 — Score both arms
Q1–Q14 for control and v5 against the locked rubric + Q14 criteria, single rater. Commit scores before opening dreaming/arbitration logs.

#### S5-T-021 — Formation + faithfulness + non-content
Run facts-in-LTM, faithfulness, and non-content harnesses on the v5 distilled store. Commit outputs.

#### S5-T-022 — Evaluate bars

| Bar | Criterion | Observed | Result |
|-----|-----------|----------|--------|
| 1 | ≥3/4 domains' planted fact in distilled LTM, faithful, zero non-content | | |
| 2 | (if Bar 1) Q11≥0.5 ∧ Q14≥0.5 ∧ sum≥1.5, distilled records in probe contexts; else NOT EVALUABLE | | |
| 3 | v5 Q1–Q13 ≥ seeded control Q1–Q13; Cat 1–3 held | | |

Record confirmatory outcome (VALIDATED / PARTIAL / NOT-EVALUABLE-per-bar). Apply the Bar 3 category caveat before verdict. If Bar 1 passes and Bar 2 fails, record the retrieval-diversity trigger explicitly.

#### S5-T-023 — Arbitration + compactness analysis
Observational measures: compression ratio, per-domain coverage, dedup activity, breadth retrieval anatomy (Q11/Q14 candidates + provenance), compactness-vs-diversity evidence, seeding determinism spot-check. Document in `ltm_analysis/analysis_report.md`. No pass/fail interpretation.

---

## Sprint S5_010 — Report + Memory Files
**Goal:** Write the report; update memory; close.

#### S5-T-024 — Report
`experiments/study_005/study_005_report.md`, carried structure: summary, questions, changes from 004, method (incl. seeding), the dreaming spec as run, results (14-question rubric both arms, three-bar table, formation/faithfulness/non-content), discussion (formation success/failure, the Bar 1→Bar 2 disentanglement outcome, whether retrieval diversity is now needed, compactness), what to do differently, limitations, next steps, appendix. State plainly whether the read path is now functionally validated (Bar 2 given Bar 1).

#### S5-T-025 — Memory files
Update `MUZAFFER_PROFILE.md` and `CLAUDE_CONTEXT.md`: Study 005 result; the inversion (promotion retired, dreaming is the selective stage); seeding now standard; next component per the pipeline (abstractive dreaming with faithfulness bars, and/or the deferred retrieval-diversity fix if Bar 1-pass/Bar 2-fail triggered it). Update timestamps.

#### S5-T-026 — Close
Report, memory, run logs (both arms), dream-event and distilled-LTM snapshots, formation/faithfulness outputs, ablation report, decision records, synthetic report — all committed. Pre-registration SHA in the report header.

---

## Summary

| Sprint | Scope | Output | Gate |
|--------|-------|--------|------|
| S5_001 | Pre-reg lock, decisions, seeding, runtime | Plant key, records, deterministic prefix | speed + determinism |
| S5_002 | Permissive store; retire promotion | Append-only raw store | promotion absent |
| S5_003 | Extractive dreaming | Dream component | extractive assertion + floor tests |
| S5_004 | Cadence + read-path retarget | Distilled LTM on cadence | carried tests pass |
| S5_005 | Measurement harnesses | facts-in-LTM / faithfulness / non-content | conditional Bar 2 wired |
| S5_006 | Synthetic end-to-end | Verification report | all mechanisms + determinism |
| **S5_007** | **35-turn ablation + GO/NO-GO** | **Ablation report** | **← GREEN LIGHT** |
| S5_008 | Seeded control + full v5 run | Both arms' logs | 121 turns each |
| S5_009 | Scoring + formation + bars | Bar verdicts | scores before logs |
| S5_010 | Report + memory | Study closed | all committed |
