# DMR-001B Deviation 001 - Implementation Preceded Pre-Registration

**Recorded:** August 12, 2026
**Severity:** Protocol violation. `AGENTS.md` section 7 lists
"Let implementation precede pre-registration" under **Never**, and section 4
requires that pre-registration commits contain no implementation files.
**Status:** Recorded, not repaired. Git history is not rewritten.

## What happened

In the DMR-001B working session the component
`src/biological_memory/adaptive_event_context.py` was written **before**
`DMR_001B_PRE_REGISTRATION.md`, and both were committed together in
`74690eda`. Two rules were broken at once:

1. The implementation preceded the design.
2. The pre-registration commit contains an implementation file, so git order
   cannot demonstrate that the design was fixed first.

This was an execution error by the agent, not an authorized decision.

## Why it is recorded rather than fixed

Amending or reverting would make the history look compliant while the file
content had already existed at that commit. A rewritten history that hides a
process failure is worse than a recorded one. `PF3` therefore reports the
ordering check as **FAILED** rather than passing, and the study report carries
this deviation.

## What the rule guards against, and whether it happened

The hazard is writing code, observing an outcome, then back-filling a design
that matches the outcome. Assessment:

- No DMR-001B gate result existed when either file was written. The gate
  modules did not exist yet and no formation run had been executed against the
  locked configuration.
- The locked parameters - percentile 0.975, window 16, warmup 16, cap 128 -
  were fixed from the **committed** Part 1 artifact
  (`8a8daeb7`, sweep of 100 configurations) and from the author's explicit
  decision on the cap, both of which precede `74690eda` in git order and in the
  session transcript.
- The gate bars in section 5 of the registration are transcribed into
  `src/analysis/dmr001b_gates.py`, which was written after the registration was
  committed, and a test asserts the two agree.

So the specific hazard the rule prevents did not materialize. That assessment
does not make the violation acceptable, and a reader is entitled to discount
DMR-001B's ordering guarantee accordingly.

## Consequence carried into the result

DMR-001B's disposition must state that its ordering guarantee is weaker than
DMR-001's. Its outcome ceiling was already `CHARACTERIZED` with no authority to
unblock DMR-002; this deviation gives a second, independent reason not to treat
its numbers as confirmatory.

## Corrective practice

For any successor: commit the pre-registration alone, verify with
`git show --stat` that it contains no file under `src/` or `tests/`, and only
then write the component.
