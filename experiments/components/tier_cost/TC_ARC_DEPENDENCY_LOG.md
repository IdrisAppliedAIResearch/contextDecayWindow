# TC Arc — Dependency Log

**Document type:** Standing procedure and running record
**Status:** `OPEN — TC-001 through TC-005, TC-007 and TC-008 have reported; reader work has not`
**Governs:** `TC_ARC_ROADMAP.md` Rule 4

---

## Why this file exists

The DMR arc stalled, and the post-mortem in
`../biological_memory/deterministic_retrieval/DMR_ARC_BLOCKING_REVIEW.md` names
the cause precisely:

> **I carried DMR-001's blanket blocking claim forward after the evidence under
> it had changed.** … This is the second time in this arc I have over-applied a
> blocking claim.

A blocking claim is cheap to write and expensive to re-read. Nobody re-reads it,
because re-reading it is nobody's job at any particular moment. DMR's review was
written *after* four stages had sat blocked; two of them turned out not to be.

This file makes the re-read somebody's job at a defined moment.

## The procedure

**Trigger.** Any TC study reporting a verdict — pass, fail, stop or withdrawn.

**Action, before the next study is registered:**

1. Read every other study's `Dependency line` and `Expiry` in
   `TC_ARC_ROADMAP.md`, in full, from the file rather than from memory.
2. For each, record one of exactly three verdicts in the table below:
   - `RUNNABLE` — its dependency is satisfied.
   - `BLOCKED` — its dependency is unsatisfied, **and the specific missing
     artifact is named**. A verdict of `BLOCKED` without a named artifact is
     invalid and the study is treated as `RUNNABLE`.
   - `WITHDRAWN` — the question is no longer worth asking, with the reason.
3. A study may only be marked `BLOCKED` by an artifact it does not have. It may
   **never** be marked blocked by another study's verdict. If a re-read produces
   the sentence "blocked because TC-00n failed", that sentence is the defect,
   not the finding.

**A blocking claim expires when the artifact it names appears.** It does not
survive on the authority of whoever wrote it.

## The rule that would have caught DMR

> If a study's own dependency line does not name the missing artifact, the study
> is runnable.

DMR-004's header said it was independent of DMR-001 through DMR-003, and it was
declared blocked anyway. Under this rule that declaration is inadmissible on its
face, without needing anyone to relitigate the science.

---

## Record

| Date | Trigger | TC-001 | TC-002 | TC-003 | TC-004 | TC-005 | TC-006 |
|---|---|---|---|---|---|---|---|
| 2026-08-21 | Arc drafted | RUNNABLE | RUNNABLE | RUNNABLE | RUNNABLE | RUNNABLE | RUNNABLE |
| 2026-08-22 | TC-001 reported `D3 FLAT_WINS` | REPORTED | RUNNABLE | RUNNABLE | RUNNABLE | RUNNABLE | RUNNABLE |
| 2026-08-22 | TC-001B reported `C1 D3 FLAT_WINS` | REPORTED | RUNNABLE | RUNNABLE | RUNNABLE | RUNNABLE | RUNNABLE |
| 2026-08-22 | TC-002 reported `C1 D1 K_FIRST_WINS` | REPORTED | REPORTED | RUNNABLE | RUNNABLE | RUNNABLE | RUNNABLE |
| 2026-08-22 | TC-003 reported `C1 D1 FLOORS_WINS`; C5 `D3 RANKED_WINS` | REPORTED | REPORTED | REPORTED | RUNNABLE | RUNNABLE | RUNNABLE |
| 2026-08-23 | TC-004 reported `NO_PREDICTIVE_SIGNAL` | REPORTED | REPORTED | REPORTED | REPORTED | RUNNABLE | RUNNABLE |
| 2026-08-23 | TC-005 reported hybrid `TREATMENT_CARRIES_SIGNAL`; dense fallback selected | REPORTED | REPORTED | REPORTED | REPORTED | REPORTED | RUNNABLE |
| 2026-08-23 | TC-007 reported `NO_SPLIT_SELECTED`; dense fallback retained | REPORTED | REPORTED | REPORTED | REPORTED | REPORTED | RUNNABLE |
| 2026-08-23 | TC-008 reported `DENSE_CARRIES_SIGNAL`; dense fallback retained | REPORTED | REPORTED | REPORTED | REPORTED | REPORTED | RUNNABLE |

**Re-read of 2026-08-22.** Triggered by TC-001 reporting. Every line below was
read from `TC_ARC_ROADMAP.md` rather than from memory or from this file's
previous row.

| Study | Dependency line, as written | Verdict | Why |
|---|---|---|---|
| TC-002 | A second store with evidence labels where both orders can be replayed over frozen candidate identities | `RUNNABLE` | The internal 121-turn store and LoCoMo development both supply it, and TC-001 consumed neither in a way that removes it. TC-001 additionally demonstrates that both packing orders are replayable over LoCoMo development at frozen candidate identities |
| TC-003 | The tier boundaries must be identifiable in the delivered block | `RUNNABLE` | Satisfied by `ContextReport`, and now demonstrated: TC-001 reports delivered composition per tier on all 871 questions and attributes carried evidence to a tier |
| TC-004 | A corpus with span-level evidence labels | `RUNNABLE` | LongMemEval turn labels and LoCoMo evidence dialogue ids both persist. Untouched by TC-001 |
| TC-005 | A pool-size-versus-latency series over the current implementation | `RUNNABLE` | `PAPER_002.md` §10's 50-to-1,000 series persists. TC-001's Preflight adds a second, independent point at pools of 323 to 355 |
| TC-006 | Two frozen contexts of known margin, and an instrument finer than that margin | `RUNNABLE` | Unchanged. EC-002's replay artifacts satisfy the first clause; the second is TC-006's own first task, exactly as the initial state recorded |

**No study is `BLOCKED`, and none was a candidate to be.** TC-001's verdict
names no missing artifact, and under the procedure above a verdict cannot block
anything: a `BLOCKED` entry is valid only when it names an artifact the study
does not have. The sentence "blocked because TC-001 found against the tiers"
would be the defect, not the finding.

**One thing worth writing down so it is not mistaken for a block later.** TC-001
found the flat arm ahead by 435 questions on delivery. That is a reason to read
TC-003 and TC-005 differently — TC-003 now asks whether allocation explains the
gap, and TC-005's latency target now belongs to a component that carried
evidence on 8 of 871 questions — but it is not a reason to stop either of them,
and it changes no dependency line. Under Rule 1 there is no arc-level clause to
inherit.

**Re-read of 2026-08-22, second.** Triggered by TC-001B reporting. TC-001B is
a successor registered under `amendments/AMENDMENT_001_dual_arm_escalation.md`,
not a numbered arc stage, so it appears in the trigger column rather than as a
column of its own. Every line below was read from `TC_ARC_ROADMAP.md` again,
from the file rather than from the row above it.

| Study | Dependency line, as written | Verdict | Why |
|---|---|---|---|
| TC-002 | A second store with evidence labels where both orders can be replayed over frozen candidate identities | `RUNNABLE` | Unchanged and now further demonstrated: TC-001B replayed four orders over frozen identities on LoCoMo development. Nothing was consumed that TC-002 needs |
| TC-003 | The tier boundaries must be identifiable in the delivered block | `RUNNABLE` | Satisfied by `ContextReport`, and TC-001B attributes carried evidence to a tier on all 871 questions for three separate configurations |
| TC-004 | A corpus with span-level evidence labels | `RUNNABLE` | LongMemEval turn labels and LoCoMo evidence dialogue ids both persist. Untouched by TC-001B |
| TC-005 | A pool-size-versus-latency series over the current implementation | `RUNNABLE` | `PAPER_002.md` §10's series persists; TC-001B adds per-question latency for two further configurations at pools of 323 to 355 |
| TC-006 | Two frozen contexts of known margin, and an instrument finer than that margin | `RUNNABLE` | Unchanged. EC-002's replay artifacts satisfy the first clause; the second is TC-006's own first task |

**No study is `BLOCKED`, and TC-001B's verdict could not block one.** A verdict
is not an artifact.

**What did change, and it is not a block.** TC-003 proposes reserved floors so
that allocation stops depending on tier order. TC-001B measured a competitor to
that explanation: of TC-001's 435-question deficit, **158** is attributable to
the recency tier's share and **276** to the order the K tier delivered its own
members in. Reserved floors address the first and not the second. That makes
TC-003 more interesting to run and changes no dependency line — under Rule 1
there is no arc-level clause to inherit, and TC-003's own expiry condition
(Rule 3) reads `none`, so there is nothing outstanding for it to wait on.

**Re-read of 2026-08-22, third.** Triggered by TC-002 reporting. Every line
below was read from `TC_ARC_ROADMAP.md` again, from the file rather than from
the two rows above it.

| Study | Dependency line, as written | Verdict | Why |
|---|---|---|---|
| TC-003 | The tier boundaries must be identifiable in the delivered block | `RUNNABLE` | Satisfied by `ContextReport`, and TC-002 attributes carried evidence to a tier on all 871 questions for four separate configurations, at two budgets |
| TC-004 | A corpus with span-level evidence labels | `RUNNABLE` | LongMemEval turn labels and LoCoMo evidence dialogue ids both persist. Untouched by TC-002 |
| TC-005 | A pool-size-versus-latency series over the current implementation | `RUNNABLE` | `PAPER_002.md` §10's series persists; TC-002 adds per-question latency for five configurations at pools of 323 to 355, including the first measurement of what reordering the fill costs (1 to 3 ms) |
| TC-006 | Two frozen contexts of known margin, and an instrument finer than that margin | `RUNNABLE` | Unchanged for the second clause, which is TC-006's own first task. The first clause is now easier to satisfy than it was: TC-002 supplies four frozen delivered contexts per question over the same query set, separated by measured margins of 45, 110 and 111 questions |

**No study is `BLOCKED`, and TC-002's verdict could not block one.** A verdict
is not an artifact.

**What changed, and none of it is a block.**

**TC-003** proposes reserved floors so that allocation stops depending on tier
order. TC-002 measured what changing that order is worth on this corpus and got
**45 questions**, against **111** for changing the order *within* the K tier.
Floors address the first quantity. TC-003 is now the third study in a row to
find the between-tier lever smaller than the within-tier one, which makes it
more worth running and changes no dependency line.

**TC-006's** first clause is closer to satisfied than the roadmap assumed. It
requires "two frozen delivered contexts over the same query set that differ in
evidence availability by a known margin," and it named EC-002's replay
artifacts. TC-002's per-question CSVs now supply five arms over 871 questions at
two budgets with registered margins, which is a wider choice of contrast pair
than EC-002 alone offered. This does not touch the second clause — the
instrument's spread is still unmeasured, and measuring it is still TC-006's own
first task.

**One decision is now closed rather than open.** `TC_ARC_ROADMAP.md` §10 item 4
asked whether TC-002's result, if positive, ships immediately or waits for
TC-003. TC-002's registration §0 decided it before the run: **it does not ship
on this result.** The result is positive and the decision stands. That item is
retired, not deferred.

**Re-read of 2026-08-22, fourth.** Triggered by TC-003 reporting. Every other
unreported study's dependency and expiry line was read again from
`TC_ARC_ROADMAP.md`, not carried from the row above.

| Study | Dependency line, as written | Verdict | Why |
|---|---|---|---|
| TC-004 | A corpus with span-level evidence labels so “the material answering the query” is identifiable within a unit | `RUNNABLE` | LongMemEval's turn labels and LoCoMo's evidence dialogue ids still supply the named artifact. TC-003 consumed neither and its verdict cannot remove them |
| TC-005 | A pool-size-versus-latency series over the current implementation | `RUNNABLE` | `PAPER_002.md` §10's 50-to-1,000 series persists. TC-003 Preflight additionally measured candidate-state and allocator cost at pools of 323 to 355; no required artifact is missing |
| TC-006 | Two frozen delivered contexts over the same query set with a known availability margin, and an instrument finer than that margin | `RUNNABLE` | The first clause now has another committed choice: TC-003's floor and N-first contexts differ by 342 complete-evidence questions at 16,000. The fact-use instrument's spread remains unmeasured, exactly as the roadmap says, and measuring it is TC-006's own first task rather than an upstream dependency |

**No study is `BLOCKED`, and TC-003's verdict could not block one.** The result
is evidence about allocation, not a missing artifact.

**What changed, and it is not a block.** TC-003's C1 is positive, but its
registered isolating C5 points the other way: the cosine contest, not the
reservation, carries the demonstrated gain. Exact service-order invariance
passes while ownership-order invariance fails. That narrows the floor proposal
and leaves the flat arm ahead; it changes how later architecture results should
be read and changes no dependency line.

**Re-read of 2026-08-23, fifth.** Triggered by TC-004 reporting. Every other
unreported study's dependency and expiry line was read again from
`TC_ARC_ROADMAP.md` rather than inherited from the prior row.

| Study | Dependency line, as written | Verdict | Why |
|---|---|---|---|
| TC-005 | A pool-size-versus-latency series over the current implementation | `RUNNABLE` | `PAPER_002.md` §10's 50-to-1,000 series persists. TC-004 neither changes cluster assignments nor consumes that series |
| TC-006 | Two frozen delivered contexts over the same query set with a known availability margin, and an instrument finer than that margin | `RUNNABLE` | The frozen contexts and known margins from EC-002 and TC-001 through TC-003 persist. The fact-use instrument's spread remains unmeasured exactly as the roadmap states, and measuring it remains TC-006's own first task |

**No study is `BLOCKED`, and TC-004's disposition could not block one.** Its
`NO_PREDICTIVE_SIGNAL` result closes one registered embedding-localization
predictor on one observed store. A negative result is not a missing artifact.

**What changed, and it is not a block.** TC-004 found 96 beneficial and 235
harmful one-parent splits. The predictor lost the paired AP comparison to
length on 31 questions against 21 wins, despite a higher outlier-driven mean.
This weakens the proposed operational test for “small enough” and changes no
dependency line. Under the then-current design, TC-005 still owned fixed-pool
cost and TC-006 still owned reader use; TC-005 was repurposed before its own
registration, as the next re-read records.

**Re-read of 2026-08-23, sixth.** Triggered by TC-005 reporting. The remaining
unreported study's dependency and expiry line was read again from
`TC_ARC_ROADMAP.md` rather than inherited from the prior row.

| Study | Dependency line, as written | Verdict | Why |
|---|---|---|---|
| TC-006 | Two frozen delivered contexts over the same query set with a known availability margin, and an instrument finer than that margin | `RUNNABLE` | TC-005 neither consumes the EC-002 and TC-001-through-TC-003 frozen contexts nor changes the requirement to measure the fact-use instrument's spread as TC-006's first task |

**No study is `BLOCKED`, and TC-005's disposition cannot block one.** Hybrid's
8k gain and unresolved 16k result select no new relevance arm under the locked
rule; that is a study result, not a missing artifact. Dense is frozen as the
TC-007 relevance input, satisfying that follow-on's predecessor choice without
starting its Preflight or registration. TC-006 remains runnable and remains
downstream in implementation order because its registered target contexts must
be frozen after TC-007, not because an artifact is currently missing.

**Design revision of 2026-08-23.** By author decision, the unregistered TC-005
clustering-cost placeholder is retired and TC-005 is repurposed as a transfer
comparison of dense cosine, carried BM25, and carried dense-plus-sparse RRF.
The historical 16,000- and 32,000-character budgets remain the comparison
points. Relative, adaptive, and enterprise token-budget design is deferred.

| Study | Revised dependency line | Verdict | Why |
|---|---|---|---|
| TC-005 | Evidence-labelled store on which dense cosine, carried BM25, and carried RRF rank identical candidates | `DESIGN ONLY — RUNNABLE AFTER PREFLIGHT AND REGISTRATION` | LoCoMo supplies identical adjacent-pair candidates and labels; the retrieval bakeoff supplies committed BM25 and RRF definitions |
| TC-006 | Two frozen contexts of known margin, and an instrument finer than that margin | `RUNNABLE` | Unchanged by the TC-005 redesign; TC-006 still requires its own Preflight and registration |

TC-005 is the preferred first step because it freezes the relevance input before
TC-007 tests protected allocation. This is a scoped design order, not permission
to bypass either study's required Preflight and standalone pre-registration.
The clustering-latency evidence remains valid but moves to later
enterprise-scale work; no published result is withdrawn.

**Author clarification of 2026-08-23.** TC-005 is not choosing a ranker for an
unrestricted context. Its primary operating points are **8,000 and 16,000
characters**, the relevance halves inside TC-007's 16,000- and
32,000-character totals. Full-budget 16,000 and 32,000 runs remain continuity
anchors and regression checks. TC-007 binds the frozen relevance strategy to
one route and A3 or facility location to the spread route; "hybrid" may describe
either dense-plus-sparse relevance fusion or the two differently optimized
routes working together.

| Study | Evidence dependency after clarification | State |
|---|---|---|
| TC-005 | Same LoCoMo candidates and labels; carried dense, BM25, and RRF strategies runnable at 8k/16k, with 16k/32k anchors | `DESIGN ONLY — PREFLIGHT NEXT` |
| TC-007 | One TC-005 relevance order frozen after half-budget evaluation; unmodified TC-003 C5 replay; carried A3 and facility spread orders | `DESIGN ONLY — WAITS FOR THE NAMED TC-005 ARTIFACT` |

TC-007's dependency is an artifact, not a verdict: it needs one frozen relevance
order and its half/full-budget anchors. TC-005 must lock a fallback, so a finding
that BM25 and RRF do not beat dense still supplies the artifact by retaining
dense. No outcome branch can stall the sequence.

**Re-read of 2026-08-23, seventh.** Triggered by TC-007 reporting. The only
remaining unreported study's dependency and expiry line was read again from
`TC_ARC_ROADMAP.md`.

| Study | Dependency line, as written | Verdict | Why |
|---|---|---|---|
| TC-006 | Two frozen delivered contexts over the same query set with a known availability margin, and an instrument finer than that margin | `RUNNABLE` | EC-002 and TC-001 through TC-003 still supply the first artifact. TC-007 adds frozen dense/A3/facility contexts with measured margins, but does not consume or select TC-006's reader pair. The fact-use instrument's spread remains TC-006's own first task |

**No study is `BLOCKED`, and TC-007's negative selection cannot block one.**
The 50/50 result is evidence about two frozen spread objectives, not a missing
reader artifact. TC-006 is not started by this re-read; it still requires its
own Preflight and standalone pre-registration.

**What changed.** TC-007 satisfies and consumes its named predecessor artifact:
dense was frozen by TC-005 and both spread routes replayed before outcomes. It
then retained dense full-budget retrieval. That supplies another possible
frozen reader contrast but does not retroactively choose one for TC-006.

**Re-read of 2026-08-23, eighth.** Triggered by TC-008 reporting. The remaining
reader dependency and expiry line were read again from `TC_ARC_ROADMAP.md`.

| Study | Dependency line, as written | Verdict | Why |
|---|---|---|---|
| TC-006 | Two frozen delivered contexts over the same query set with a known availability margin, and an instrument finer than that margin | `RUNNABLE` | TC-008 adds byte-frozen dense/A3/session contexts and exact availability margins. It does not satisfy or remove TC-006's second clause: reader-instrument resolution must still be measured as that study's own first task |

**No study is `BLOCKED`.** TC-008's negative session-spread result is not a
missing reader artifact and cannot block answer validation. It supplies more
frozen contexts while leaving the reader, prompt, replicates, scorer and bars
unselected. Reader work was not started by this re-read.

**Initial state, 2026-08-21.** All six dependency lines name artifacts that
exist, with one exception recorded here rather than as a block: TC-006's second
clause requires an instrument whose resolution is finer than the margin it
tests, and that instrument's spread has never been measured. That measurement is
scoped as TC-006's own first task, so TC-006 is `RUNNABLE` — it may begin, and
its first result may be that it cannot proceed. That is a study outcome, not a
dependency.

No study is blocked by any other study. If that ever ceases to be true, the
change is recorded here with the naming artifact, or it is not a block.
