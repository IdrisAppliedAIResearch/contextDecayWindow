# Study 010 — Sprint Plan
## contextDecayWindow
**Idris Applied AIResearch**
**Pre-registration:** `experiments/study_010/pre_registration.md`
**Sprints:** S10_001–S10_008 · **Green light at S10_005** (gates + rehearsal GO)

**Contract:** the pre-registration wins; stop and flag on divergence. Scope: no new architecture — this is a scale test of Study 009's Arm S composition vs the accepted Study 007 treatment (branch-resolved). The script/rubric/plant-key triple is the study's long pole and its quality ceiling; it is authored and hash-locked before any calibration so no gate can tune the script.

**Parallelism note:** S10_001 (script authorship) has **no Study 009 dependency** and starts immediately. S10_002's branch resolution waits for 009's verdict. Everything else follows the diagram.

---

## Dependency overview

```
S10_001  1,000-turn script + rubric + plant key (authored, reviewed, hash-locked)   ── starts now
   │
S10_002  branch resolution (digest carry, Arm L config) + lock + decision records   ── waits for 009
   │
S10_003  scale infrastructure: checkpoint/resume, ctx-size re-derivation, interim-probe guards
   │
S10_004  scale gates: G1 retrieval-at-scale · G2 consolidation-at-scale · G3 digest-at-scale (if carried) · G4 resume correctness
   │
S10_005  G5 200-turn timed rehearsal per arm + GO/NO-GO   ◄── GREEN LIGHT
   │
S10_006  two-arm 1,000-turn execution
S10_007  blinded scoring (terminal + interim) → fact matrices → Bar 1 verdict + curves
S10_008  report + memory files
```

---

## Sprint S10_001 — Script, Rubric, Plant Key (starts immediately)
- **S10-T-001 — Author the 1,000-turn script.** 12 domains × ~80 turns, established plant grammar, early/middle/late plants per domain, terminal probe block + interim checkpoints at ≈250/500/750 (3 questions each: early-era targeted, recent targeted, breadth). Deterministic, committed as `script_1000.json`.
- **S10-T-002 — Author `q_facts_key_1000.md`** (per-domain rubric-critical facts with source turns) and **`rubric_1000.md`** (criteria per question, 0/0.5/1.0 grammar). Sealed from the retrieval path by the standing leakage audit.
- **S10-T-003 — Review pass and hash-lock.** Researcher review of script/rubric/key coherence (every rubric question answerable from planted content; every plant probed at least once). Commit and record SHA-256 of all three. **Acceptance:** hash-lock precedes any calibration activity (git-ordered); interim probes marked for emission-guard exclusion.

## Sprint S10_002 — Branch Resolution + Lock (waits for Study 009)
- **S10-T-004 — Resolve Branch 1 (digest) and Branch 2 (Arm L config)** from 009's committed verdicts; record in `DECISION_branches_study010.md` with author authorization.
- **S10-T-005 — Lock the pre-registration** with resolved branches, re-derived parameters marked pending S10_003, SHA recorded.

## Sprint S10_003 — Scale Infrastructure
- **S10-T-006 — Checkpoint/resume.** Full-state snapshot (stores, logs, RNG state) every 100 turns; resume from last checkpoint. Acceptance: unit tests + G4 (below) is the integration proof.
- **S10-T-007 — ctx-size re-derivation** per the stage-interface contract: project peak context from 009 per-turn measurements scaled to 12-topic digest and ~1,000-episode store; set ceiling ≥ 2× projection; 80% monitor carried. Recorded in the decision record.
- **S10-T-008 — Interim-probe emission guards.** Dreaming/promotion emission excluded at all probe checkpoints (extends the carried probe-guard discipline). Acceptance: unit test per checkpoint window.
- **S10-T-009 — B_digest re-derivation at 12 topics** (if Branch 1 carried the digest). Never assume the 4-topic value.

## Sprint S10_004 — Scale Gates
- **S10-T-010 — G1 retrieval-at-scale.** Synthesized ~1,000-episode store from the script's embedded turns; measure K latency and planted-fact precision vs the 120-turn baseline; commit the prediction the live run must meet.
- **S10-T-011 — G2 consolidation-at-scale.** Replay assignment/consolidation over the embedded script; purity instrumentation must recover ~12 domains without mass merging or fragmentation. On failure: recalibrate thresholds **before lock finalization**, decision-recorded.
- **S10-T-012 — G3 digest-at-scale** (conditional): 12 × `d` spans within the re-derived `B_digest` at exact serialized cost.
- **S10-T-013 — G4 resume correctness.** Kill a seeded prefix run at a checkpoint; resumed run turn-identical to an unkilled reference.
- **Acceptance:** all gate reports committed; any parameter changed by a gate is locked before S10_005 (git-ordered).

## Sprint S10_005 — Rehearsal + GO/NO-GO — GREEN LIGHT
- **S10-T-014 — G5: 200-turn timed rehearsal per arm.** Validates the 6–8 h/arm projection, monitoring protocol, checkpoint cadence, log volumes, context trajectory vs projection, determinism (prefix identical across arms), leakage audit re-run.
- **S10-T-015 — GO/NO-GO** committed before any full run. **← GREEN LIGHT**

## Sprint S10_006 — Two-Arm 1,000-Turn Execution
- **S10-T-016 — Arm L** (checked-out branch-resolved config, separate worktree, full guard set) and **S10-T-017 — Arm S** (009's minimal composition): 1,000 turns each, all logs open before turn 1, checkpoints every 100 turns, interim probes at 250/500/750, terminal probe block, carried monitoring rules. Any resume event logged as a protocol note.
- **Acceptance:** both arms complete (resume permitted, logged); cross-arm prefix equality; logs sealed unread; wall-clock recorded.

## Sprint S10_007 — Scoring, Matrices, Verdict
- **S10-T-018 — Blinded inputs** (two arms × terminal + 3 interim checkpoints), sealed mapping.
- **S10-T-019 — Human rater, ~46 scorings**, dual scoring, rationale per question, **scores before any mechanism log** (git-verified).
- **S10-T-020 — Fact matrices** per checkpoint per arm; formation/store integrity checks; K-precision live vs G1's prediction.
- **S10-T-021 — Bar evaluation.** Bar 2 (endurance integrity), Bar 3 (curves complete), then **Bar 1's decision rule applied exactly as registered** — retain / cut / suspend, with the fact-matrix mechanism account. The consequence executes as written; no post-hoc reinterpretation.
- **S10-T-022 — Degradation analysis.** Per-arm curves by plant age and store size; divergence points; the confusability hypothesis adjudicated against G1's prediction.

## Sprint S10_008 — Report + Memory
- **S10-T-023 — Report.** Leads with the Bar 1 verdict and its executed consequence; degradation curves as the second headline; the honest comparability note (new script, no cross-chain score comparison); protocol notes (resumes, wall-clock).
- **S10-T-024 — Memory files.** The verdict and what the architecture now is; pipeline table updated (LTM retained/cut/suspended; dreaming's role resolved); next horizon (interleaved-topic scripts if LTM survives; open-dialogue ceiling otherwise).
- **S10-T-025 — Close.** All artifacts committed; SHA in report header.

---

| Sprint | Gate |
|---|---|
| S10_001 | script/rubric/key hash-locked before any calibration |
| S10_002 | branches resolved from 009; lock |
| S10_003 | resume built; ctx re-derived; guards in |
| S10_004 | G1–G4 committed; params locked |
| **S10_005** | **G5 rehearsal · ← GREEN LIGHT** |
| S10_006 | 1,000 × 2 complete; prefix equality |
| S10_007 | scores before logs; Bar 1 rule applied as registered |
| S10_008 | close |
