# Study 007 — Sprint Plan
## contextDecayWindow
**Idris Applied AI Research**
**Date:** July 2026
**Pre-registration:** `experiments/study_007/pre_registration.md`
**Task numbering:** S7-T-001 onward
**Sprint numbering:** S7_001–S7_009
**Green light at S7_006** (ablation GO). S7_007–S7_009 are the post-authorization runs, scoring, and close.

**Reading order for the coding agent:** the pre-registration is the design contract. Where this plan and the pre-registration appear to differ, the pre-registration wins — stop and flag. Introduce no parameters or architectural choices not stated in one of the two documents.

**Scope discipline for this study:** Study 007 changes the **LTM retrieval budget and arbitration assembly only**. Formation (span segmentation, salience, C = 50, floor, dedup, verbatim extraction) is carried **unmodified** and is diff-reviewed to prove it. STM retrieval (N + K) is untouched. If implementation pressure suggests changing selection, salience, C, or STM — stop and flag.

---

## Dependency overview

```
S7_001  pre-reg lock + decision record + Correction 1 (UTF-8 in code) + runtime/seed
   │
S7_002  information budget + floor/fill selection            ── the new component
   │
S7_003  containment dedup + arbitration assembly + logging
   │
S7_004  targeted-retrieval fixture   ── floor must not starve narrow queries
   │
S7_005  retrieval replay gate over Study 006's preserved store  ── 4-domain coverage at Q11 and Q14; calibrate B_ltm and k_min
   │
S7_006  35-turn ablation + GO/NO-GO   ◄── GREEN LIGHT
   │
S7_007  same-seed Study 006 control + full v7 run
S7_008  blinded scoring → formation checks → bars
S7_009  report + memory files
```

**Order rationale.** The two offline gates (S7_004, S7_005) run *before* the ablation because either can invalidate the policy at near-zero cost, and because they jointly **calibrate** `B_ltm` and `k_min` — the study cannot lock its parameters without them. They must pass *simultaneously*: the replay gate pushes the floor up, the targeted fixture pushes it down, and resolving that tension offline is the point. This is the direct analogue of Study 006's replay gate, which caught the cap-scaling defect before a run was spent.

---

## Sprint S7_001 — Lock, Decision Record, Encoding Correction, Runtime
**Goal:** Commit the locked pre-registration, record the component decision, fix the encoding fragility in code, confirm runtime and determinism.

#### S7-T-001 — Commit pre-registration and plant key
Copy the pre-registration to `experiments/study_007/pre_registration.md`. Carry `q_facts_key.md` forward from Study 006 and re-verify per-domain target facts and source turns. Commit together; record the SHA in the header.
- **Acceptance:** both files under `experiments/study_007/`; plant key verified; SHA recorded; no implementation files in the commit.

#### S7-T-002 — Decision record
`DECISION_retrieval_budget_study007.md`: the Study 006 finding (count-expressed budget × 17× record-count increase and ≈ 28× smaller records → ≈ 584 chars delivered vs the control's ≈ 20,700; single-domain coverage at Q11 while the store held all four), the two changes (information-expressed budget; per-domain floor + similarity fill), the named departure from Study 004's tier-neutral count-ranking, rejected alternatives (MMR with a tunable λ; raising M alone) with one line each, and the stage-interface contract (Correction 4) as a standing rule. Author-authorization line required.
- **Acceptance:** committed with authorization; pre-registration references resolve.

#### S7-T-003 — Correction 1: UTF-8 in code
Add explicit `encoding='utf-8'` to `src/study/script_loader.py` and every study-path file open. Add a startup assertion comparing the script's SHA-256 **after decode** to the pre-registered hash, aborting on mismatch.
- **Acceptance:** unit test — loading under a forced cp1252 default still yields the correct post-decode hash (i.e. correctness no longer depends on `PYTHONUTF8`); a deliberately corrupted script aborts at startup with a clear message.

#### S7-T-004 — Stage-interface contract check (Correction 4)
Enumerate every downstream consumer of retrieval output (arbitration cap, context assembly, ceiling monitor, logging schemas) and re-derive each for character-budgeted units. Record the enumeration and re-derivation in `decisions/DECISION_retrieval_budget_study007.md`.
- **Acceptance:** written re-derivation committed; no downstream consumer still assumes a record count.

#### S7-T-005 — Runtime and determinism confirm
Launch with the exact pre-registered flag set (no speculative decoding, fixed `--seed`). Record command and server build hash. Confirm embedding model unchanged. Speed test > 30 tok/s single-slot. Determinism spot-check: same seed, ~10-turn prefix twice, turn-identical.
- **Acceptance:** flags + seed recorded; speed floor met; prefix replay identical; context-ceiling monitor active.

**Complete when:** pre-reg + key committed, decision record committed, encoding correctness proven in code, interface contract recorded, runtime deterministic.

---

## Sprint S7_002 — Information Budget + Floor/Fill Selection
**Goal:** Build the new retrieval selection. Budget in characters; coverage by floor; relevance by fill.

#### S7-T-006 — Character budgeting
Fill the LTM block to `B_ltm` characters. Admit records until the next would exceed the budget; never exceed it.
- **Acceptance:** unit tests — budget never exceeded across randomized record-length sets; a single record larger than the whole budget is handled without deadlock (admitted only if it alone fits, else skipped and logged); budget utilization reported per selection.

#### S7-T-007 — Phase 1: per-domain floor
For each canonical topic present in distilled LTM (resolved through the current consolidation mapping), select its top `k_min` spans by cosine similarity to the query. Topics with fewer than `k_min` spans contribute all they have; the shortfall is not redistributed as a guarantee. Under budget pressure, admit floor selections **round-robin across topics** (highest similarity first within each topic).
- **Acceptance:** unit tests — each topic receives up to `k_min`; a sparse topic contributes what it has without error; under a deliberately tight budget, round-robin prevents any topic being starved by another's longer spans; canonical mapping is applied (two labels resolving to one topic share one floor).

#### S7-T-008 — Phase 2: similarity fill
Fill the remaining budget from all not-yet-selected spans by pure global cosine similarity, topic-agnostic, no per-topic cap.
- **Acceptance:** unit tests — fill order is strictly by similarity; a query concentrated in one domain is free to spend most of the remaining budget there; fill never displaces a floor selection.

**Complete when:** floor and fill produce a budget-respecting LTM block with guaranteed coverage and relevance-ordered remainder.

---

## Sprint S7_003 — Containment Dedup, Arbitration Assembly, Logging
**Goal:** Wire the new selection into arbitration without disturbing STM, and log what makes Bar 1 checkable.

#### S7-T-009 — Containment dedup + refill
Drop any LTM span whose `source_episode_id` is already present in the STM block; log as `containment_dedup`. Refill the freed budget under the same phase rules — a dropped floor selection is replaced by the same topic's next-ranked span, preserving the floor.
- **Acceptance:** unit tests — a span whose source episode is in STM is dropped and logged; the floor survives a containment drop (replacement comes from the same topic); identifier dedup (carried from Study 004) still works; budget respected after refill.

#### S7-T-010 — Arbitration assembly
Assemble blocks per the pre-registration: STM tier unchanged (N + K); LTM tier as selected; identifier dedup then containment dedup with refill; **floor selections protected from eviction**; render into the carried XML-tagged structure with distilled-record provenance metadata.
- **Acceptance:** carried read-path tests pass (tagged blocks, self-closing empties, provenance rendering); floor-protection asserted — no ranking path can evict a floor selection; STM path diff-reviewed as unmodified.

#### S7-T-011 — Retrieval budget logging
Write `retrieval_budget.csv` per turn: turn, topics_present, floor_selected_per_topic, fill_selected, containment_drops, refills, ltm_chars_used, ltm_records_used, budget_utilization, per-domain character split, and the full ordered selection (span id, topic, similarity, phase).
- **Acceptance:** one row per turn with all fields; per-domain split sums to `ltm_chars_used`; phase labels correct against a hand-checked turn; verified on synthetic data before the ablation.

**Complete when:** selection is wired end-to-end, the floor is provably protected, STM is provably untouched, and the log supports Bar 1 attribution.

---

## Sprint S7_004 — Targeted-Retrieval Fixture
**Goal:** Prove the diversity floor does not starve narrowly targeted queries — the mirror risk of the fix.

#### S7-T-012 — Author the fixture
`tests/targeted_retrieval_fixture.json`: at least one narrowly targeted query per domain, phrased like the targeted rubric questions, run against Study 006's preserved distilled store.
- **Acceptance:** committed fixture-only; queries documented with their intended domain.

#### S7-T-013 — Run and evaluate
For each targeted query, measure the per-domain character split and compare against a floor-disabled variant.
- **Gate criteria:** (1) majority of the character budget goes to the query's own domain; (2) that domain's top-similarity span is present; (3) versus floor-disabled, the targeted domain loses no more than `k_min × (|T| − 1)` slots.
- **On failure of criterion 1:** `k_min` is too large relative to `B_ltm` — reduce `k_min` or raise `B_ltm`, then **re-check this fixture and the replay gate together**.
- **Acceptance:** results committed at `experiments/study_007/tests/targeted_fixture_report.md` with per-query splits.

**Complete when:** the floor's cost to targeted retrieval is bounded, quantified, and within criteria.

---

## Sprint S7_005 — Retrieval Replay Gate + Parameter Calibration
**Goal:** Prove offline, on the exact store and probes that failed, that the new policy delivers four-domain coverage — and calibrate `B_ltm` and `k_min` to smallest-sufficient.

#### S7-T-014 — Build the replay harness
Load Study 006's preserved distilled store (200 records). Embed the Q11 (turn 120) and Q14 (turn 121) queries as the runner does. Execute Study 007 selection and emit the resulting LTM block. Read-only: the harness must not mutate Study 006 artifacts.
- **Acceptance:** harness runs end-to-end; Study 006 artifacts hash-verified unchanged before/after; block contents emitted with span ids, topics, similarities, phases.

#### S7-T-015 — Harness fidelity check
Run the harness configured with **Study 006's parameters** (`M = 5`, no floor, count-based) and confirm it reproduces Study 006's observed probe behavior — a single domain reaching the model at Q11.
- **Acceptance:** reproduction matches the Study 006 LTM analysis. **If it does not, stop — no replay evidence is trustworthy until the harness is faithful.**

#### S7-T-016 — Calibrate and evaluate the gate
Sweep `B_ltm` and `k_min`; record the frontier. Select the **smallest** values satisfying: at both probes, ≥1 planted term from each of the four domains present in the block; budget never exceeded; projected peak context < 60% of `--ctx-size`. Cross-check the selected values against the S7_004 targeted fixture — **both must pass at the same parameter values.**
- **Acceptance:** `replay/replay_report.md` committed with the sweep frontier, the four-domain verdict at both probes, projected context, and the chosen `B_ltm` / `k_min` with the smallest-sufficient justification.
- **On failure at all swept values:** do not run. Escalate — the store may need per-domain *selection* guarantees rather than retrieval-side ones, which would be a formation change and therefore a different study.

#### S7-T-017 — Lock parameters
Record final `B_ltm` and `k_min` in the pre-registration and decision record **before** the ablation. No post-run changes permitted.
- **Acceptance:** locked values recorded in both documents; git order shows lock precedes the ablation.

**Complete when:** the harness is faithful, the gate passes with four-domain coverage at both probes, both gates pass at the same parameters, and those parameters are locked.

---

## Sprint S7_006 — 35-Turn Ablation + GO/NO-GO — GREEN LIGHT
**Goal:** Real-script integration check, then authorization.

#### S7-T-018 — 35-turn ablation
Turns 1–35 under v7, seeded. Reaches the first topic transition (~31), so the first dream pass fires and LTM becomes non-empty — enough to exercise budgeting and the degenerate single-topic floor case. Mechanisms not reachable by turn 35 (four-topic floor, breadth probes, turn-111 flush) were covered by the replay gate and fixture.

| Check | Expected | Actual | Pass? |
|---|---|---|---|
| Speed (single-slot) | > 30 tok/s | | |
| Determinism | prefix replay identical | | |
| Script hash post-decode | matches pre-registered | | |
| Formation unchanged | spans, salience, C = 50 diff-review clean | | |
| First dream pass | fires at ~31; records offset-verbatim | | |
| Extractive assertion | zero inference calls in dreaming | | |
| Budget respected | `ltm_chars_used` ≤ `B_ltm` every turn | | |
| Single-topic floor | degenerate case handled (one topic present) | | |
| Containment dedup | drops logged; refill preserves floor | | |
| Floor protection | no floor selection evicted | | |
| `retrieval_budget.csv` | populated, per-domain split sums correctly | | |
| STM untouched | N + K path diff-review clean | | |
| Context ceiling | peak well under 80% of ctx-size | | |

- **Acceptance:** all applicable checks pass; `ablation/ablation_report.md` committed; any failure → diagnose, fix, re-run from scratch.

#### S7-T-019 — Go/No-Go (GREEN LIGHT)
```
DECISION: GO — all applicable checks passed; retrieval replay gate (four-domain coverage at Q11 and Q14) and targeted fixture passed at locked B_ltm / k_min before the ablation. Control + full v7 run authorized.
```
or a NO-GO naming the failed check and reason. Commit before any full run.
- **Acceptance:** explicit GO/NO-GO committed. On GO, proceed to S7_007.

**Complete when:** ablation report committed with GO. **← GREEN LIGHT**

---

## Sprint S7_007 — Same-Seed Control + Full v7 Run
**Goal:** Run both arms under the fixed seed. Log everything. Do not score, and do not open mechanism logs, during runs.

#### S7-T-020 — Same-seed Study 006 control
Run the **accepted Study 006 treatment implementation** (span selection, count-based top-M) from a **checked-out Study 006 worktree** at the Study 007 runtime and same seed, same 121-turn script, into `experiments/study_007/controls/count_budget_seeded/run_001/`. Launcher must reject dirty worktree, unexpected diff, wrong post-decode script hash, import escape, or presence of the Study 007 retrieval engine; record module paths, server properties, command, and pid before inference.
- **Permitted deviation (pre-registered, the only one):** the control inherits Correction 1 (explicit UTF-8 + post-decode hash assertion). Record this explicitly in the run header — a control receiving mojibake is not a valid baseline.
- **Acceptance:** 121 turns, no truncation; guards verified active; module paths and the permitted deviation recorded; seed recorded.

#### S7-T-021 — Full v7 run
121 turns under v7, seeded, into `runs/study_007_full_001/`. All log handles open before turn 1 (dream events, distilled snapshots, `retrieval_budget.csv`, arbitration, context sizes, purity). Dream passes at 31/61/91/111; turn-111 completes before 112; Q14 at 121. Carried monitoring rules (≥3 consecutive empty/truncated → stop).
- **Acceptance:** 121 turns; four dream events logged; `retrieval_budget.csv` 121 rows; distilled snapshot per event; peak context recorded; cross-arm prefix equality verified before divergence.

---

## Sprint S7_008 — Blinded Scoring, Formation Checks, Bars
**Goal:** Score blind and first; only then open mechanism logs and evaluate bars.

#### S7-T-022 — Prepare blinded scoring inputs
Extract each arm's probe responses into arm-anonymized directories (`evaluation/arm_A/`, `evaluation/arm_B/`). Commit a **sealed mapping** file that is not opened until scores are committed.
- **Acceptance:** anonymized responses committed; sealed mapping committed; git order shows both precede scoring.

#### S7-T-023 — Human rater scores both arms
A **human rater** scores Q1–Q14 for both arms against the locked rubric and Q14 criteria, blind to arm identity. Apply **dual scoring** on any answer whose credit depends on a hedged or alternative-offering formulation: a **primary** score under the locked criteria (governs all bars) and a **strict** score in which a term offered as one of several alternatives earns no credit. Record a written rationale per question.
- **Acceptance:** primary and strict scores plus rationales committed at `evaluation/rubric_scores.json`; **no formation, retrieval, arbitration, or dreaming output opened before this commit — verifiable from git history**; mapping unsealed only after.

#### S7-T-024 — Formation, faithfulness, non-content
Only now, run facts-in-LTM (against `q_facts_key.md`), offset-faithfulness, non-content, and inference-call checks on the v7 distilled store.
- **Acceptance:** outputs committed; git order confirms they follow the score commit.

#### S7-T-025 — Evaluate bars

| Bar | Criterion | Observed | Result |
|---|---|---|---|
| 3 | 4/4 domains form, 100% offset-verbatim, zero non-content, zero inference calls | | |
| 1 | (if Bar 3) Q11 ≥ 0.5 ∧ Q14 ≥ 0.5 ∧ sum ≥ 1.5, **with all four domains present in the probe-turn LTM block**; else NOT EVALUABLE | | |
| 2 | v7 Q1–Q13 ≥ same-seed control; Cat 1–3 not below control | | |

Evaluate Bar 3 first — it is Bar 1's precondition. Apply the category caveat before any Bar 2 verdict, state sensitivity where a verdict turns on a single 0.5, and report whether the strict scoring would change any verdict. If Bar 1 fails **with** four-domain coverage in the log, record explicitly that the bottleneck is neither formation nor retrieval — that is the pre-registered trigger for a context-presentation study.

#### S7-T-026 — Mechanism analysis
Observational measures: delivered LTM characters per turn (vs Study 006's ≈ 584 treatment / ≈ 20,700 control), budget utilization, floor-vs-fill composition, per-domain character split, containment dedup rate, probe retrieval anatomy for Q11/Q14, context size (vs 12,169 / 16,171), formation invariance (vs 200 records / 29,214 chars / 6.55%), determinism evidence, and the **offline minimum-viable-C sweep** (observational only — C is not changed in this study). Document in `ltm_analysis/analysis_report.md`. No pass/fail interpretation.

---

## Sprint S7_009 — Report + Memory Files
**Goal:** Write the report; update memory; close.

#### S7-T-027 — Report
`experiments/study_007/study_007_report.md`, carried structure: summary, questions, changes from 006, method (runtime, seeding, corrections, replay/fixture gates), the retrieval policy as run, results (14-question rubric both arms with primary and strict scores, three-bar table, formation checks), discussion, limitations, next steps, appendix. The discussion must state plainly: (a) whether breadth recovered and whether the retrieval log attributes it to four-domain coverage; (b) what the diversity floor cost targeted recall; (c) whether the replay gate's prediction matched the live run — and if not, where they diverged; (d) if Bar 1 failed despite four-domain coverage, that the bottleneck has moved to context use rather than memory. Carry the source-weight script-correlation and unformed-plants limitations verbatim.

#### S7-T-028 — Memory files
Update `MUZAFFER_PROFILE.md` and `CLAUDE_CONTEXT.md`: Study 007 result; whether end-to-end recall now works; the brain-pipeline status table; the next study per outcome (context presentation if Bar 1 failed with coverage; abstractive dreaming with faithfulness bars, or the 1,000-turn endurance study, if the architecture is now sound). Record the stage-interface contract as a standing rule. Update timestamps.

#### S7-T-029 — Close
Report, memory files, both arms' run logs, dream/distilled snapshots, `retrieval_budget.csv`, replay report, targeted fixture report, ablation report, decision record, sealed-mapping and scoring artifacts — all committed. Pre-registration SHA in the report header.

---

## Summary

| Sprint | Scope | Output | Gate |
|---|---|---|---|
| S7_001 | Lock, decision record, UTF-8 correction, runtime | SHA, record, encoding-proof, deterministic prefix | post-decode hash + determinism |
| S7_002 | Information budget + floor/fill | New selection | budget never exceeded; floor guaranteed |
| S7_003 | Containment dedup, assembly, logging | Wired retrieval + log | floor protected; STM untouched |
| S7_004 | Targeted-retrieval fixture | Fixture report | majority budget to queried domain |
| S7_005 | Retrieval replay + calibration | Replay report, locked params | **four-domain coverage at Q11 and Q14** |
| **S7_006** | **35-turn ablation + GO/NO-GO** | **Ablation report** | **← GREEN LIGHT** |
| S7_007 | Same-seed control + full v7 run | Both arms' logs | 121 turns each |
| S7_008 | Blinded scoring → formation → bars | Bar verdicts | **scores committed before any mechanism log** |
| S7_009 | Report + memory | Study closed | all committed |
