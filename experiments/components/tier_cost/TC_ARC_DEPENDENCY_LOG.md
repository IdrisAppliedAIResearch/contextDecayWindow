# TC Arc — Dependency Log

**Document type:** Standing procedure and running record
**Status:** `OPEN — TC-001 has reported; TC-002 through TC-006 have not`
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

**Initial state, 2026-08-21.** All six dependency lines name artifacts that
exist, with one exception recorded here rather than as a block: TC-006's second
clause requires an instrument whose resolution is finer than the margin it
tests, and that instrument's spread has never been measured. That measurement is
scoped as TC-006's own first task, so TC-006 is `RUNNABLE` — it may begin, and
its first result may be that it cannot proceed. That is a study outcome, not a
dependency.

No study is blocked by any other study. If that ever ceases to be true, the
change is recorded here with the naming artifact, or it is not a block.
