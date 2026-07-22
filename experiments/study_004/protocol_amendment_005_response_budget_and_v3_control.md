# Study 004 - Amendment A005
## Response budget 1,024 -> 2,048; same-settings v3 control run
## contextDecayWindow - Idris Applied AI Research

**Amends:** `experiments/study_004/pre_registration.md` (locked)
**Status:** authorized and locked before implementation
**Trigger commit:** `7f451e9` (`protocol_deviation_full_001_truncation.md`)
**Authorized by:** Muzaffer Ozen - July 21, 2026, via the instruction
"Go ahead and implement the amendment and continue the study."

This amendment stands alongside the locked pre-registration; the
pre-registration body is not edited. Where the two differ, this amendment
governs the affected parameters (response budget, Bar 1, Bar 2, baseline) and
nothing else.

---

## 1. Trigger

Full-run attempt `study_004_full_001_failed_truncation` reached the mandatory
truncation stop threshold on completion of turn 10. Turns 8-10 were the first
three consecutive responses truncated at the 1,024-token response budget. The
diagnostic process had reached turn 13 by the time its full process tree was
terminated. Diagnostic commit `7f451e9` classified the truncation as
**genuinely longer, clean output**: coherent numbered lists cut off
mid-sentence, zero context-tag or rule echoes across all 13 responses, zero LTM
context (pure-STM regime - LTM empty until approximately turn 31), and no
repetition loops or resets. Cause: UD-Q6_K_XL produces longer well-formed
answers than the 1,024-token budget retained from the prior studies
accommodates.

The partial execution is preserved and committed under
`experiments/study_004/runs/study_004_full_001_failed_truncation/`. It is not
scored and is not a confirmatory run. The canonical `run_001` path remains free
for a future accepted execution.

---

## 2. Change 1 - Response budget

Response budget raised from **1,024 to 2,048 tokens.**

Sufficiency was verified before this amendment was committed by replaying the
exact archived turns 8-10 constructed prompts at a 4,096-token ceiling. The
replay reconstructed the production model input, including the rule-detection
suffix and closed-think prefill, and omitted sampling parameters exactly as the
production request does so the same server defaults applied.

| Turn | Natural completion | Stop | Margin below 2,048 |
|---:|---:|---|---:|
| 8 | 1,225 tokens | EOS | 823 tokens |
| 9 | 1,277 tokens | EOS | 771 tokens |
| 10 | 1,050 tokens | EOS | 998 tokens |

All three completed naturally below the approximately 1,800-token target. None
crossed the 1,900-token reconsideration threshold. The raw server responses,
request metadata, prompt hashes, and generated summary are preserved under
`experiments/study_004/verification/response_budget_a005/`.

---

## 3. Change 2 - Baseline replaced by a same-settings v3 control run

The Bar 2 comparison baseline is no longer Study 003's historical 12.0/13.0
(NVFP4, 1,024-token budget - three configuration deltas from v4). It is
replaced by an auxiliary **v3 control run**.

### Configuration

Study 003 architecture (v3) - selective write path, v3 consolidation, **no LTM
read path, no arbitration, no XML tagging** - executed at the exact v4 runtime
and generation configuration:

- Model: Qwen3.6 27B UD-Q6_K_XL
- Response budget: 2,048 tokens
- Identical generation settings (temperature and sampling) to the v4 run
- Same 121-turn script, including Q14 at turn 121
- v3 untagged context

### Code discipline (binding)

The control runs from the accepted Study 003 implementation at commit
`c4120a40ab19912a6c5d04826d11385d59cbc272`, checked out separately. It does
not run from the v4 runner with features flagged off. Module review at amendment
draft time found zero arbitration/LTM-read symbols and no XML context tags in
that commit.

Only two control-worktree adaptations are permitted and must be diff-reviewed:

1. Change the response ceiling from 1,024 to 2,048 in the local and HTTP
   inference paths.
2. Add an execution wrapper that points the v3 runner to the locked 121-turn
   Study 004 script and preserves the turn-121 response for Q14 scoring.

No memory, retrieval, topic, consolidation, context-construction, promotion,
rule, or scoring implementation may change.

### Scope of the control

The control isolates architecture at fixed runtime and budget, but bundles the
two v4 additions (read path plus XML tagging) against their joint absence.
Neither was independently ablated. The control separates *v4 architecture as a
whole* from *v3 architecture as a whole*; it does not generally attribute an
effect between read path and tagging. Separating those components would need a
third arm (tagged, read-path-off), which is out of scope here.

### Sequence and scoring

The control runs and is scored **before** the fresh v4 run. It receives the
full 14-question rubric, using the same criteria and the same single rater as
the v4 run. Its scores are committed before v4 executes.

---

## 4. Re-scoped success bars

These supersede the corresponding bars in the locked pre-registration. Bar 3
is unchanged.

### Bar 1 - Breadth Recovery (Targeted) - amended

Unchanged core: Q11 >= 0.5 AND Q14 >= 0.5 AND (Q11 + Q14) >= 1.5, with
LTM-provenance episodes attributable in the Q11/Q14 contexts.

**Added condition - behavioral control:** the v3 control run must **fail**
breadth (miss Q11 and/or Q14) for a v4 breadth pass to be attributable to the
read path. If the control recovers breadth on its own - same stronger model,
same larger budget, no read path - then breadth recovery is not an LTM effect
and **Bar 1 is void regardless of v4's score.** The provenance log shows LTM
episodes were present; the control tests whether they were necessary.

**Operational attribution check:** for each v4 breadth item claimed as a
read-path effect, the required domain evidence must be absent from the v3
control's Q11/Q14 constructed context and present in the v4 context through
LTM provenance. If the control context already contains sufficient evidence
but its generated answer misses it, XML tagging remains a plausible explanation
for the v4 pass; Bar 1 is then void/indeterminate rather than attributable to
the read path.

### Bar 2 - Targeted Recall Non-Regression - amended

**Q1-Q13 >= 12.0/13.0 (absolute floor) AND >= the v3 control's Q1-Q13 score
(comparative), with Cat 1-3 >= 3.0/3.0/2.0 and Cat 5 >= 2.0.**

The absolute floor guards against outright regression below the historical
bar. It is the weaker condition because it compares against a 1,024-budget
score. The comparative guard exposes v4 scoring below a same-settings
no-read-path baseline. If the control scores 13.0 and v4 scores 12.0, the floor
passes but the comparative fails. The category-analysis caveat carries from
Study 003.

### Bar 3 - Consolidation Purity - unchanged

---

## 5. Confounds after this amendment

The control holds runtime and budget at the v4 values, so the v4-versus-control
comparison retires the runtime and budget confounds. The residual is the
read-path/tagging bundle described in Section 3.

**Bar 1 can survive the bundle only with the operational attribution check.**
XML tagging cannot supply evidence absent from the control context. Therefore,
a control breadth failure plus absence of the required evidence in its context,
paired with the evidence's LTM-provenance presence and use in v4, supports a
read-path attribution. If both contexts contain the evidence, the bundle is not
separable and Bar 1 is void/indeterminate.

**Budget/recall interaction.** A larger budget can lift recall independent of
memory, but the control shares the 2,048-token budget, so a budget-driven gain
appears in the control and nets out of the comparative. The absolute floor,
compared against a 1,024-budget historical score, is the weaker Bar 2 condition
for this reason.

---

## 6. Execution sequence

1. Verify 2,048-token sufficiency (completed; Section 2).
2. Commit this amendment with author authorization.
3. Re-run the 35-turn gate at 2,048. A budget change is a generation-config
   change; the gate must pass at the configuration that will run. Record a fresh
   GO/NO-GO.
4. Run the v3 control on the separately checked-out v3 code and score it on the
   14-question rubric.
5. **Gate:** if the control fails breadth, lock its Q1-Q14 scores as the Bar 1
   and Bar 2 reference and proceed to the v4 full run. If the control passes
   breadth, **STOP and escalate**; do not proceed on autopilot.

---

## 7. Preservation

`study_004_full_001_failed_truncation` is retained in commit `7f451e9` as a
failed diagnostic and is not scored. The canonical `run_001` path is unused.
`demo/` remains untouched. Prior amendments A001-A004 are recorded in the
Study 003 paper and are carried into the v4 baseline as documented by the
locked Study 004 pre-registration and decision records.
