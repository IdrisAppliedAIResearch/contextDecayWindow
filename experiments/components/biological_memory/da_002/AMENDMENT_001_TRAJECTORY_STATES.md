# DA-002 Amendment 001 - Reachable Trajectory States

**Status:** `PRE-IMPLEMENTATION STRUCTURAL REPAIR`
**Date:** August 29, 2026
**Applies to:** `DA_002_MECHANISM_PROTOCOL.md` at commit `d6ee1f93`

## Trigger

Section 3.3 named `gain-then-loss` and `loss-then-gain` trajectory classes.
Before implementation, reachability review found both are impossible under the
fixed comparison. Every treatment depth is compared with the same `DIRECT`
outcome. An item failing under `DIRECT` may be a treatment gain or tie but can
never be a treatment loss. An item passing under `DIRECT` may be a treatment
loss or tie but can never be a treatment gain.

No DA-002 provenance or joined mechanism artifact exists.

## Repair

Replace the trajectory classes with the reachable exhaustive set:

- `ALWAYS_TIED`;
- `PERSISTENT_GAIN_FROM_m`;
- `GAIN_THEN_REVERT`;
- `MULTIPLE_GAIN_TIE_REVERSALS`;
- `PERSISTENT_LOSS_FROM_m`;
- `LOSS_THEN_RECOVER`;
- `MULTIPLE_LOSS_TIE_REVERSALS`.

Report the exact five-state gain/tie or loss/tie sequence and every transition
depth beside the class. The fixed seed depths, arms, outcomes, and all other
decompositions remain unchanged.

## Interpretation

This amendment repairs PF4 reachability. It does not merge reversals into a
monotonic class or make a nonmonotonic trajectory disappear.
