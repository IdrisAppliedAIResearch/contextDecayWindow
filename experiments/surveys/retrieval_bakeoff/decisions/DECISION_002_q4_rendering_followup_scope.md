# Decision 002: Q4 Rendering Follow-Up Scope

**Date:** 2026-07-29

## Trigger

After the corrected bakeoff result and Q4 mechanism trace were committed, the
author supplied two draft follow-up designs:

- `DR-001 - Rendering Expansion Defect and Fix`
- `AS-001 - Q4 Packing Re-Analysis`

The author asked whether they belong in the retrieval-bakeoff pull request.

## Evidence And Limitation

The committed bakeoff artifact establishes that the turn-55 Q4 bundle ranked
27th within the widened-STM N cap of 32, while only 15 N episodes fit the
60,595-character payload. It does not establish whether a leaner renderer would
have admitted rank 27.

Study 010 separately records a 290-record store containing 18,951 raw span
characters and rendered LTM blocks of 31,991 and 31,847 characters at Q13 and
Q14. Those are store-level quantities, not matched per-episode measurements,
so their ratio cannot estimate how many Q4 candidates a renderer fix recovers.

## Decision

The follow-up designs do **not** belong in PR #22:

1. DR-001 changes a carried production subsystem and must ship in its own
   correctness-fix PR. It must measure per-episode expansion and pass a
   byte-identical pre-fix replay before the renderer changes, then prove the
   selected episode identity set is unchanged after the fix.
2. AS-001 depends on the completed renderer fix and must ship separately. Its
   branch decision rule must be committed before any post-fix Q4 packing output
   is opened.
3. PR #22 may qualify its causal framing, but its observed score, Q4 delivery
   trace, and formation-blind positive result remain unchanged.
4. A pinned primacy study is not the immediate next study. It may be scoped only
   if the pre-committed post-fix analysis leaves Q4 structurally excluded. A
   budget or packing result leads to that cheaper mechanism instead.

No 1,000-turn run is authorized by this decision.

## Authorization

The author supplied both drafts on 2026-07-29 and explicitly requested a ruling
on whether they should be completed in PR #22.
