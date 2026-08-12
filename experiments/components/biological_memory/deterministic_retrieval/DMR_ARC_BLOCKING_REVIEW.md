# DMR Arc — Blocking Review

**Document type:** Review of which stages are actually blocked, and by what
**Status:** `REVIEW — NO STATUS CHANGED BY THIS FILE`
**Trigger:** The author challenged the claim that four of six stages are blocked
**Date:** August 12, 2026

The roadmap repeated in every spec says:

> If DMR-001 stops, DMR-002 through DMR-006 are blocked because there is no
> validated event substrate.

That was true the day DMR-001 stopped. DMR-001B and DMR-001C then happened, and
the clause was never re-read against them. This file re-reads it, stage by
stage, against each spec's own dependency line.

## The correction

**I carried DMR-001's blanket blocking claim forward after the evidence under
it had changed.** DMR-001B passed all five of its gates, and DMR-001C put its
operating point on a sealed holdout and confirmed transfer at a 1.67× fire-rate
ratio. DMR-001B's report said it "does NOT unblock DMR-002" and gave two
reasons: no sealed holdout, and `DEVIATION_001`. DMR-001C supplied the sealed
holdout. The stated reason expired and I did not revisit it.

This is the second time in this arc I have over-applied a blocking claim; the
first was asserting DMR-004 was blocked when its own header says it is
independent of DMR-001 through DMR-003.

## Stage by stage

### DMR-002 — typed event-bound pattern completion: **RUNNABLE**

Dependency line: *"A passing, frozen DMR-001 event map."*

Its question is a **utility** question: do `MEMBER_OF_EVENT` edges recover other
elements of an encoded event better than generic adjacency or recursive cosine,
at matched candidate opportunity?

That does not require the event boundaries to match human-annotated session
seams. DMR-001C's G5 measured boundary **provenance** — whether the rule's
seams line up with real conversation seams — and it failed on recall. G4
measured whether the rule holds a stable operating point across unseen
corpora, and it **confirmed**. DMR-002 needs coherent co-encoded groupings, not
correct ones.

A DMR-002 run on the frozen DMR-001B former would earn a narrower claim —
event-bound completion beats adjacency *given events formed by the adaptive
drift rule* — and that is a real result, and it is exactly the kind of evidence
the arc was built to accumulate.

### DMR-003 — retrieved-context recurrence: **RUNNABLE**

Dependency line: *"A passing, frozen DMR-001 event/context snapshot; DMR-002 is
carried only if it independently passed."*

It consumes the **encoding-context vectors**, not the boundary claim, and the
roadmap already anticipates DMR-002 failing without taking DMR-003 with it.
Same reasoning as above; the 001B snapshot supplies what it names.

### DMR-005 — deterministic route and stopping controller: **BLOCKED**

Dependency line: *"Passing frozen DMR-004 plans and whichever of DMR-002/DMR-003
independently passed."*

DMR-004 stopped, so there are no passing frozen plans. This block is the arc's
own dependency text, not my judgement, and it holds.

It is unblockable in exactly one honest way: a different sufficiency signal,
designed and tested on its own. `NF-001` asks whether one exists on the
retrieval side. `NF-001` does not unblock DMR-005 and does not claim to.

### DMR-006 — single-reader integration: **BLOCKED**

Dependency line: DMR-001, DMR-004, DMR-005, and one passing alternate route.
It is last by construction and needs DMR-005.

## Summary

| Stage | Blocked? | By what |
|---|---|---|
| DMR-002 | **no** | my stale reading, corrected here |
| DMR-003 | **no** | my stale reading, corrected here |
| DMR-005 | yes | its own dependency line; DMR-004 produced no passing plans |
| DMR-006 | yes | needs DMR-005 |

Two of the four were blocked by me and should not have been. Two are blocked by
the arc's own text and still are.

## What this file does not do

It changes no status. DMR-002 and DMR-003 remain `DESIGN ONLY — NOT
PRE-REGISTERED`, as every unrun stage in this arc does, and running either
needs the author's authorization and its own Part 1 and pre-registration. The
point of this review is that the authorization is available to give, which it
was not while the blocking claim stood unexamined.

The honest caveat on both: they would be tested against an event substrate whose
boundaries are known **not** to beat periodic chopping on real session seams.
Any claim either earns has to carry that sentence.
