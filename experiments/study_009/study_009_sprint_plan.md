# Study 009 — Sprint Plan
## contextDecayWindow
**Idris Applied AI Research**
**Pre-registration:** `experiments/study_009/pre_registration.md`
**Sprints:** S9_001–S9_007 · **Green light at S9_004** (gates + ablation GO)

**Contract:** the pre-registration wins over this plan; stop and flag on any divergence. Scope: the null-test arm compositions and the digest. Nothing touches formation, the rubric, the budget values of Arm L, or the runtime. The leakage audit is a standing tripwire in every sprint.

**Final disposition (Amendment 001):** S9_001-S9_004 completed; the original
S9_005 parity rule stopped as registered and was superseded before full
execution. The accepted Study 007 artifact was reused as Arm L, Arm S completed
121 turns, two arms were blindly scored, and S9_006-S9_007 completed. S+D was
dropped at G1, so its live run, 14 scores, and digest Bars 1-2 are not
evaluable. Final null-test result: L 12.0 versus S 10.5; LTM retirement
cancelled.

---

## Dependency overview

```
S9_001  lock + decision record + Arm S minimal composition
   │
S9_002  topic digest component (build, render, budget, containment)
   │
S9_003  gates: G1 digest replay (calibrate d/B_digest) · G2 Arm L fidelity · G3 Arm S sanity
   │
S9_004  35-turn ablations (S, S+D; L covered by fidelity) + GO/NO-GO   ◄── GREEN LIGHT
   │
S9_005  three-arm execution
S9_006  blinded scoring → fact matrices → null-test verdict + bars
S9_007  report + memory files
```

---

## Sprint S9_001 — Lock, Decision Record, Arm S
- **S9-T-001 — Commit pre-registration + plant key.** Carry `q_facts_key.md`; verify the 17-fact list. SHA recorded; no implementation files.
- **S9-T-002 — Decision record.** `DECISION_null_test_study009.md`: the control-failure finding (only Study 004 ever compared STM vs LTM; controls since were prior LTM versions), the structural duplication argument, the decision rules and their consequences, the digest rationale (breadth is a query-type mismatch, not a tier problem), rejected alternatives (fifth retrieval iteration; 2×2 with L+D) one line each. Author-authorized.
- **S9-T-003 — Arm S minimal composition.** Build S as its own composition: N + K retrieval, pinned rules, tagged blocks, **no LTM/digest modules on the import graph** (structural absence, not flags — the Study 004 control lesson applied to subtraction). Acceptance: import-graph proof; retrieval matches a hand-derived N + K fixture; carried STM tests pass; context assembly renders `<retrieved_ltm>` absent (not self-closing-empty — absent, since the tier does not exist in this arm; snapshot fixture).
- **S9-T-004 — Runtime + determinism.** Carried flags, fixed seed, spot-check, prefix hash match against Study 007's records.

## Sprint S9_002 — Topic Digest
- **S9-T-005 — Digest build.** Per dream-cadence point, per canonical topic: top-`d` density spans (imported density implementation), eligibility + 0.95 dedup carried, verbatim + provenance, zero inference calls (assertion carried). Acceptance: unit tests incl. the sparse-topic floor (one span per topic minimum, word-boundary truncation with ellipsis marker, never omission).
- **S9-T-006 — Digest render + budget.** `<topic_digest>` after `<pinned_rules>`, every turn, charged at **exact serialized cost** (production renderer as single authority — the 008 A001 lesson, applied from day one). Round-robin span drops from largest topics under pressure. Acceptance: budget never exceeded; serialized-cost regression test; snapshot fixture.
- **S9-T-007 — Containment.** Digest span dropped (no refill) when its source episode is in the STM block. Acceptance: drop logged; frame semantics (no refill) tested.

## Sprint S9_003 — Gates
- **S9-T-008 — G1 digest replay.** Build the digest offline from Study 007's preserved raw store (read-only, hash-verified). Fact-aware check: ≥1 rubric-critical fact per domain within `B_digest` at exact cost. Calibrate `d`/`B_digest` smallest-sufficient; lock values in the pre-registration. If no setting reaches 4/4: invoke the pre-registered contingency (S+D dropped; study reduces to the null test) — record, do not amend criteria.
- **S9-T-009 — G2 Arm L fidelity.** Replay reproduces Study 007's probe blocks to the character.
- **S9-T-010 — G3 Arm S sanity.** Fixture-verified N + K behavior; import-graph proof committed.
- Acceptance for the sprint: all gate reports committed; parameters locked before ablation (git-ordered).

## Sprint S9_004 — Ablations + GO/NO-GO — GREEN LIGHT
- **S9-T-011 — 35-turn ablations, arms S and S+D** (L covered by G2 fidelity + its own launcher guards). Per-arm checks: speed, determinism, post-decode hash, digest rebuild at ~31 (S+D), digest budget respected, containment behavior, leakage audit re-run, context ceiling, logs populated.
- **S9-T-012 — GO/NO-GO.** Explicit decision committed before any full run. **← GREEN LIGHT**

## Sprint S9_005 — Three-Arm Execution
- **S9-T-013 — Arm L** on checked-out Study 007 code, separate worktree, full guard set, byte-fidelity data captured.
- **S9-T-014 — Arms S and S+D** on their compositions, configs asserted at startup. All logs open before turn 1; carried monitoring rules; Q14 at 121; cross-arm prefix equality verified.
- Acceptance: 121 turns × 3; logs sealed unread.

## Sprint S9_006 — Scoring, Matrices, Verdicts
- **S9-T-015 — Blinded inputs.** Three anonymized directories, sealed mapping, randomized order.
- **S9-T-016 — Human rater, 42 scorings**, dual scoring, rationale per question, **scores before any mechanism log** (git-verified), mapping unsealed after.
- **S9-T-017 — Fact matrices + integrity checks** per arm × probe, after the score commit.
- **S9-T-018 — Verdicts.** Null-test decision rule applied and recorded with its pre-registered consequence (retirement at 120-turn scale, or cancellation). Bars 1–3 evaluated. P1 adjudicated. **Study 010 branch inputs recorded:** digest carry (Bar 1/2 outcome) and LTM config (unchanged: 007 treatment). Replay-vs-live digest fidelity checked.
- **S9-T-019 — Mechanism analysis** (observational measures per pre-registration).

## Sprint S9_007 — Report + Memory
- **S9-T-020 — Report.** Leads with the null-test verdict and its consequence; then the digest bars; per-question S-vs-L differences explained by delivered facts; the control-failure finding stated as program history so it cannot recur silently.
- **S9-T-021 — Memory files.** Null-test verdict, digest verdict, Study 010 branch inputs, pipeline status.
- **S9-T-022 — Close.** All artifacts committed; SHA in report header.

---

| Sprint | Gate |
|---|---|
| S9_001 | Arm S structurally minimal; audits standing |
| S9_002 | digest exact-cost + floor semantics |
| S9_003 | G1 4/4 (or contingency) · G2 to-the-character · G3 proof |
| **S9_004** | **← GREEN LIGHT** |
| S9_005 | 121 × 3, prefix equality |
| S9_006 | scores before logs; decision rule applied as registered |
| S9_007 | close |
