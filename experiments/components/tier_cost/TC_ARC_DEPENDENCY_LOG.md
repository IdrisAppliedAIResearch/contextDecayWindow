# TC Arc — Dependency Log

**Document type:** Standing procedure and running record
**Status:** `OPEN — no study has reported`
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

**Initial state, 2026-08-21.** All six dependency lines name artifacts that
exist, with one exception recorded here rather than as a block: TC-006's second
clause requires an instrument whose resolution is finer than the margin it
tests, and that instrument's spread has never been measured. That measurement is
scoped as TC-006's own first task, so TC-006 is `RUNNABLE` — it may begin, and
its first result may be that it cannot proceed. That is a study outcome, not a
dependency.

No study is blocked by any other study. If that ever ceases to be true, the
change is recorded here with the naming artifact, or it is not a block.
