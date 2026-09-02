# DA-019 Protected Boundary Substitution Report

**Status:** `STOPPED_AT_PF4`
**Date:** August 30, 2026
**Protocol commit:** `8cbb2d52`
**Standing:** blind mechanical stop; evidence outcomes unopened

## Stop

The substitution rule is mechanically active: it executes 571 one-for-one
boundary swaps on 1,098 NF-004 questions and 188 on 465 LongMem questions.
Blind replay is byte-identical.

PF4 nevertheless requires observed fit, lexical, semantic **and duplicate**
rejections. The blind population contains 8,631 fit, 359 lexical and 6,786
semantic rejections, but zero duplicate rejections. Both parent edge builders
already deduplicate neighbor identities upstream, so the real allocation stream
cannot exercise the registered duplicate branch.

Under the protocol, missing any required rejection is a pre-evidence stop. No
evidence identities or completion outcomes were joined, and the 759 swaps were
not scored.

## Interpretation

This does not refute the boundary rule. It identifies a name-to-behavior test
that was incorrectly required from a population where upstream invariants make
that behavior unreachable. Removing the requirement inside DA-019 would be a
post-preflight repair, so it is not allowed.

A successor may reuse the exact frozen rule only if it registers duplicate
handling as a synthetic identity test and treats upstream deduplication as the
real-data invariant before opening outcomes. It must not alter the guard based
on the blind activity counts.

## Integrity

Blind selection SHA-256 is
`b418495e649c96befa33a738a9fda0f68e56127b76f881ccc71ac4c853acd31f`.
There were zero model, embedding and cache calls. Direct and earlier linked
actions remained fixed. No reader, result, tuning or adoption claim follows.

