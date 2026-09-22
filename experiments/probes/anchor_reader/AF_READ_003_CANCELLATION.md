# AF-READ-003 — CANCELLATION RECORD (run never started)

**Date:** 2026-09-22. **Decision:** cancel the AF-READ-003 reader run by user call.
**State at cancellation:** frozen build only (1,420-item contexts.json, gold.json,
build_report.json; PF6 byte-replay PASS). **Zero model calls made; zero answers
exist.** No stopped.json, no pilot — cancellation is total and leaves no partial
data to reason about.

## What was locked

AF-READ-003 was pre-registered (commit `e51d1907`, LOCKED) as the scale
replication of AF-READ-002: n=1,420 new LoCoMo dev items, same frozen arms
(A_DEPLOYED / B_ANCHOR / C_GATE), same server, registered proportional bars.
Implementation and frozen build followed (commit `70a63765`).

## Why cancelled

The scale question — does C_ANCHOR8K_CC80 hold at n=1,420 — was overtaken by
the committed error forensics on 002 (`scratch/audit002_*`, commits `65edf7ce`):

1. The A–C comparison at scale would have re-measured the same shared
   ~25% failure floor (gold noise, judge form, reader anchoring) that the 002
   anatomy fully characterized item by item; and
2. The remaining open question in this program is no longer *how much context
   to retrieve* but *which retrieval mechanism to run per question*. That is
   the topic of a separate research program (question triage / mechanism
   dispatch), opened on branch `study/triage-001-question-triage`.

## What survives in git history as valid artifacts (not deleted)

- Pre-registration `e51d1907` — a completed, valid pre-registration doc.
- Frozen build `70a63765` + runner `0565dfe3` — a complete, verified build
  (zero embedding calls, byte-replay PASS) available to any future run without
  modification. If the triage program ever needs a large eval set under this
  exact protocol, this build is reusable as-is.
- AF-READ-002 stays the endpoint result of this arc: C_ANCHOR8K_CC80 81/120 vs
  A 85/120 (net −4, p=.42) at 42.3% tokens — WORKS at the registered bar.

## Arc status: CLOSED

AF-READ-001 (negative endpoint), AF-READ-002 (positive at cost), forensics
(mechanism anatomy). This branch (`finding-the-anchor`) is the arc record; a PR
to `main` closes it. No further reader runs occur in this arc.
