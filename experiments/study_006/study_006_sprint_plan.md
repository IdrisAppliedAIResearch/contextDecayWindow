# Study 006 — Sprint Plan
## contextDecayWindow
**Idris Applied AI Research**
**Date:** July 2026
**Pre-registration:** `experiments/study_006/pre_registration.md`
**Task numbering:** S6-T-001 onward
**Sprint numbering:** S6_001–S6_009
**Green light at S6_006** (ablation GO). S6_007–S6_009 are the post-authorization runs, scoring, and close.

**Reading order for the coding agent:** the pre-registration is the design contract. Where this plan and the pre-registration appear to differ, the pre-registration wins — stop and flag. Introduce no parameters or architectural choices not stated in one of the two documents.

**Scope discipline for this study:** Study 006 changes the dreaming **selection policy only**. It adds no pipeline component. If implementation pressure suggests touching the read path, arbitration, tagging, cadence, the raw store, or the extractive constraint — stop and flag. Those are carried, not under test.

---

## Dependency overview

```
S6_001  pre-reg lock + decision record + runtime/seed confirm
   │
S6_002  span segmentation + eligibility + offsets          ── the new selection substrate
   │
S6_003  density + source-aware salience; dedup/cap/floor rewired to spans
   │
S6_004  adversarial fixture  ── must FAIL under 005 policy, PASS under 006
   │
S6_005  retrospective replay gate over Study 005's preserved raw store  ── 4/4 required
   │
S6_006  35-turn ablation + GO/NO-GO   ◄── GREEN LIGHT
   │
S6_007  same-seed Study 005 control + full v6 run
S6_008  scoring + formation checks + bars
S6_009  report + memory files
```

**Order rationale.** Segmentation is the substrate everything else scores, so it lands first. The two cheap, decisive gates — the adversarial fixture (does the policy handle the failure *shape*?) and the replay (does it select the *actual* plants from real data?) — run **before** the ablation, because either can invalidate the policy at near-zero cost. Spending a 121-turn run on a policy that fails offline replay would be the avoidable version of Study 005's outcome.

---

## Sprint S6_001 — Pre-Registration Lock, Decision Record, Runtime
**Goal:** Commit the locked pre-registration and plant key, record the selection-policy decision, confirm the carried runtime and seeding.

#### S6-T-001 — Commit pre-registration and plant key
Copy the pre-registration to `experiments/study_006/pre_registration.md`. Re-verify `q_facts_key.md` against the script (per-domain rubric-critical facts and their source turns); carry Study 005's key forward if unchanged, otherwise amend and note the diff. Commit together; record the SHA in the header.
- **Acceptance:** both files under `experiments/study_006/`; plant key lists ≥1 target fact per domain with source turns; SHA recorded; no implementation files in the commit.

#### S6-T-002 — Decision record
`DECISION_selection_policy_study006.md`: the Study 005 finding (whole-turn absolute-count salience selected verbosity; plants ranked 11–28), the three changes (span granularity, density normalization, source weighting), rejected alternatives (raise C; keep whole turns and tune weights) with one line each, the 3/4→4/4 bar rationale from the control's natural experiment, and the source-weight script-correlation caveat. Author-authorization line required.
- **Acceptance:** committed with authorization; pre-registration reference resolves.

#### S6-T-003 — Runtime and determinism confirm
Launch with the exact pre-registered flag set (no speculative decoding, fixed `--seed`). Record command and server build hash. Confirm embedding model unchanged. Speed test > 30 tok/s single-slot. Determinism spot-check: same seed, ~10-turn prefix twice, turn-identical.
- **Acceptance:** flags + seed recorded; speed floor met; prefix replay identical; context-ceiling monitor active.

**Complete when:** pre-reg + key committed, decision record committed, runtime deterministic.

---

## Sprint S6_002 — Span Segmentation, Eligibility, Offsets
**Goal:** Build the span substrate. No scoring yet.

#### S6-T-004 — Sentence segmentation with offsets
Split in-scope raw episodes into sentence-level spans. spaCy `en_core_web_sm` sentencizer if available, else the documented regex fallback (split on `.!?` + whitespace + capital/digit, with abbreviation and decimal protection). Record the segmenter in the run header. Each span carries source episode_id, source turn, role, and **character offsets** into the source text.
- **Acceptance:** unit tests — a multi-sentence turn yields the expected spans; decimals (`2.3%`) and abbreviations do not split; offsets round-trip (`source_text[start:end] == span_text`) for every span; segmenter recorded.

#### S6-T-005 — Eligibility filter
A span is eligible iff word count is 4–60 inclusive **and** it contains ≥1 named entity or numeric token. Ineligible spans are excluded from candidacy and logged with a reason; they remain in the raw store.
- **Acceptance:** unit tests — a 2-word fragment is rejected (length); a 70-word run-on is rejected (length); a prose span with no entity or number is rejected (content); a planted fact is accepted. Rejection reasons logged.

**Complete when:** segmentation produces offset-accurate spans and eligibility behaves per spec.

---

## Sprint S6_003 — Density + Source-Aware Salience; Selection Rewired
**Goal:** Implement the new scoring and rewire dedup/cap/floor to operate on spans.

#### S6-T-006 — Salience
```
base(s)     = named_entity_count(s) + 2 × numeric_token_count(s)
density(s)  = base(s) / word_count(s)
salience(s) = density(s) × source_weight(role)     # user 1.5, assistant 1.0
```
NER via spaCy if available, else the capitalized-sequence fallback (recorded). Numeric tokens via regex (integers, decimals, years, measurements, percentages).
- **Acceptance:** unit tests — a short dense planted fact outranks a long diffuse span with a *higher absolute* count (the core correction, asserted directly); a user span outranks an otherwise identical assistant span by exactly 1.5×; the ×2 numeric weight is observable; extractor recorded.

#### S6-T-007 — Dedup, cap, floor, marker on spans
Within a topic's eligible span set: collapse pairwise cosine ≥ 0.95 (keep higher salience, record collapsed ids); rank by salience; take top C = 3; apply floor F — write records if the top span ≥ F, else a single `present_no_salient_fact` marker referencing the highest-salience span.
- **Acceptance:** unit tests — near-duplicate spans collapse; cap limits to 3; an all-sub-F topic yields a marker not a forced record; a clearing topic yields ≥1 real record.

#### S6-T-008 — Write records + span-level extractive assertion
Records store distilled_id, topic, verbatim span text, provenance (episode_id, turn, role, character offsets), base/density/salience, dream_event. Mark sources `dreamed=true`. Assert every record's text matches its source **at the recorded offsets**, and that the dream pass made **zero inference calls**.
- **Acceptance:** provenance resolves; offset-verbatim assertion passes on valid data and **trips** on a deliberately mangled record (both directions tested); inference-call counter is zero across a dream pass.

**Complete when:** span selection scores, dedups, caps, floors, and writes offset-faithful records with zero inference calls.

---

## Sprint S6_004 — Adversarial Fixture
**Goal:** Prove the policy handles the failure *shape* that defeated Study 005.

#### S6-T-009 — Author the fixture
`tests/adversarial_selection_fixture.json`: within one topic — at least three long, number-rich generated-style spans each with a **higher absolute** entity+numeric count than the plant; one short user-planted fact with **higher density**; one sub-floor acknowledgment span.
- **Acceptance:** committed fixture-only; absolute/density relationships asserted in the test itself so the fixture cannot silently drift.

#### S6-T-010 — Run the fixture both ways
Run the fixture under the Study 006 policy and under the Study 005 policy.
- **Acceptance:** **Study 006 policy: the plant is selected, decoys do not crowd it out, the acknowledgment is excluded. Study 005 policy: the plant is NOT selected.** Both directions required — a fixture that passes under both does not test the change and must be rewritten.

**Complete when:** the fixture demonstrably discriminates between the old and new policies.

---

## Sprint S6_005 — Retrospective Replay Gate
**Goal:** Validate the policy against real conversational data before spending a run.

#### S6-T-011 — Build the replay harness
Replay the Study 006 selection policy offline over Study 005's preserved raw store (`study_005_full_001`), simulating the same four dream events over the same episodes. Read-only: the harness must not mutate Study 005 artifacts.
- **Acceptance:** harness runs end-to-end on the preserved store; Study 005 artifacts unchanged (hash-verified before/after); selected-span report emitted per event.

#### S6-T-012 — Evaluate the gate
Record, for each domain, whether the rubric-critical planted fact is selected. Record the **new rank** of each Study 005 near-miss (art turns 55/56/60; marine turns 100/101/102) alongside its Study 005 rank. Verify zero non-content selections and offset-verbatim fidelity.
- **Gate criteria:** 4/4 domains' plants selected; zero non-content; 100% offset-verbatim.
- **On failure:** **do not proceed.** Revise the policy or re-derive F from replay data, record the revision in the decision record, re-replay. Parameters that ship must be justified by replay evidence, not tuned on a live run.
- **Acceptance:** replay report committed at `experiments/study_006/replay/replay_report.md` with the 4/4 verdict, the rank-movement table, and the final F value.

#### S6-T-013 — Lock F
If replay re-derived F, update the pre-registration's locked parameter and note it in the decision record **before** the ablation. F must be fixed before any run.
- **Acceptance:** final F recorded in the pre-registration and decision record; no post-run F changes permitted.

**Complete when:** replay passes 4/4 with committed evidence and F is locked.

---

## Sprint S6_006 — 35-Turn Ablation + GO/NO-GO — GREEN LIGHT
**Goal:** Real-script integration check, then the authorization decision.

#### S6-T-014 — 35-turn ablation
Turns 1–35 of the real script under v6, seeded. Reaches the first topic transition (~31), so the first dream pass fires with span selection live. Mechanisms not reachable by turn 35 (turn-111 flush, probe guard, breadth probes, sparse-topic marker) were covered by the fixture and replay.

| Check | Expected | Actual | Pass? |
|---|---|---|---|
| Speed (single-slot) | > 30 tok/s | | |
| Determinism | prefix replay identical | | |
| Raw store permissive | non-content turns stored | | |
| Segmentation | spans produced with round-trip offsets | | |
| Eligibility | rejections logged with reasons | | |
| First dream pass | fires at ~31 | | |
| Records written | ≥1, offset-verbatim, provenance resolves | | |
| Extractive assertion | passes; zero inference calls in dreaming | | |
| Civil plant formed | civil rubric-critical fact present after event 31 | | |
| Non-content in LTM | zero | | |
| Read path | ≥1 distilled span in a post-31 context, tagged with provenance | | |
| Purity | no cross-domain merge | | |
| Context ceiling | peak well under 80% of ctx-size | | |

- **Acceptance:** all applicable checks pass; `ablation/ablation_report.md` committed; any failure → diagnose, fix, re-run from scratch.

#### S6-T-015 — Go/No-Go (GREEN LIGHT)
```
DECISION: GO — all applicable checks passed; adversarial fixture and 4/4 retrospective replay passed pre-ablation. Control + full v6 run authorized.
```
or a NO-GO naming the failed check and reason. Commit before any full run.
- **Acceptance:** explicit GO/NO-GO committed. On GO, proceed to S6_007.

**Complete when:** ablation report committed with GO. **← GREEN LIGHT**

---

## Sprint S6_007 — Same-Seed Control + Full v6 Run
**Goal:** Run both arms under the fixed seed. Log everything. Do not score during runs.

#### S6-T-016 — Same-seed Study 005 control
Run the **accepted Study 005 treatment implementation** (whole-turn selection) from a **checked-out Study 005 worktree** at the Study 006 runtime and same seed, same 121-turn script, into `experiments/study_006/controls/whole_turn_seeded/run_001/`. Launcher must reject dirty worktree, unexpected diff, wrong script hash, import escape, or presence of the Study 006 selection engine; record module paths, server properties, command, and pid before inference.
- **Acceptance:** 121 turns, no truncation; guards verified active; module paths recorded; seed recorded.

#### S6-T-017 — Full v6 run
121 turns under v6, seeded, into `runs/study_006_full_001/`. All log handles open before turn 1 (dream events, span inventory, distilled snapshots, arbitration, context sizes, purity). Dream passes at 31/61/91/111; turn-111 completes before 112; Q14 at 121. Carried monitoring rules (≥3 consecutive empty/truncated → stop).
- **Acceptance:** 121 turns; four dream events logged; distilled snapshot per event; arbitration rows complete; peak context recorded; cross-arm prefix equality verified before divergence.

---

## Sprint S6_008 — Scoring, Formation Checks, Bars
**Goal:** Score both arms; run structural checks; evaluate bars — scores committed before mechanism logs are opened.

#### S6-T-018 — Score both arms
Q1–Q14 for control and v6 against the locked rubric and Q14 criteria, single rater. Commit before opening dream/retrieval/arbitration logs.

#### S6-T-019 — Formation, faithfulness, non-content
Run facts-in-LTM (against `q_facts_key.md`), offset-faithfulness, and non-content harnesses on the v6 distilled store. Commit outputs with the scores.

#### S6-T-020 — Evaluate bars

| Bar | Criterion | Observed | Result |
|---|---|---|---|
| 1 | 4/4 domains' plant present, 100% offset-verbatim, zero non-content | | |
| 2 | (if Bar 1) Q11 ≥ 0.5 ∧ Q14 ≥ 0.5 ∧ sum ≥ 1.5, distilled records in probe contexts; else NOT EVALUABLE | | |
| 3 | v6 Q1–Q13 ≥ same-seed control; Cat 1–3 not below control | | |

Record the confirmatory outcome. Apply the category caveat before any Bar 3 verdict, and state sensitivity if the verdict turns on a single 0.5 judgment call. If Bar 1 passes and Bar 2 fails, record the retrieval-diversity trigger explicitly as the next study's mandate.

#### S6-T-021 — Mechanism analysis
Observational measures: span inventory, compression vs Study 005's 10.81%, **rank movement for the six Study 005 near-misses**, source composition (user vs assistant among selected), density profile, record compactness and peak context vs Study 005 (16,171 treatment / 10,006 control), breadth retrieval anatomy for Q11/Q14, determinism evidence. Document in `ltm_analysis/analysis_report.md`. No pass/fail interpretation.

---

## Sprint S6_009 — Report + Memory Files
**Goal:** Write the report; update memory; close.

#### S6-T-022 — Report
`experiments/study_006/study_006_report.md`, carried structure: summary, questions, changes from 005, method (runtime, seeding, replay/fixture gates), the selection policy as run, results (14-question rubric both arms, three-bar table, formation/faithfulness/non-content), discussion, limitations, next steps, appendix. The discussion must state plainly: (a) whether formation reached 4/4 and which change carried it (density vs source weight vs granularity, using the rank-movement data); (b) **whether the read path is now functionally validated** — the first study able to answer that; (c) whether the retrieval-diversity trigger fired. Carry the source-weight script-correlation limitation verbatim.

#### S6-T-023 — Memory files
Update `MUZAFFER_PROFILE.md` and `CLAUDE_CONTEXT.md`: Study 006 result; whether formation is solved and the read path validated; the next component per the pipeline (retrieval diversity if triggered; otherwise abstractive dreaming with faithfulness bars, or the 1,000-turn endurance study if the architecture is now sound). Update timestamps and the brain-pipeline status table.

#### S6-T-024 — Close
Report, memory files, both arms' run logs, dream/span/distilled snapshots, replay report, adversarial fixture results, ablation report, decision record, formation outputs — all committed. Pre-registration SHA in the report header.

---

## Summary

| Sprint | Scope | Output | Gate |
|---|---|---|---|
| S6_001 | Pre-reg lock, decision record, runtime | Plant key, record, deterministic prefix | speed + determinism |
| S6_002 | Span segmentation + eligibility | Offset-accurate spans | offset round-trip |
| S6_003 | Density/source salience; selection on spans | New selection policy | dense-short beats long-absolute |
| S6_004 | Adversarial fixture | Fixture results | passes under 006, **fails under 005** |
| S6_005 | Retrospective replay | Replay report, locked F | **4/4 plants selected** |
| **S6_006** | **35-turn ablation + GO/NO-GO** | **Ablation report** | **← GREEN LIGHT** |
| S6_007 | Same-seed control + full v6 run | Both arms' logs | 121 turns each |
| S6_008 | Scoring + formation + bars | Bar verdicts | scores before logs |
| S6_009 | Report + memory | Study closed | all committed |
