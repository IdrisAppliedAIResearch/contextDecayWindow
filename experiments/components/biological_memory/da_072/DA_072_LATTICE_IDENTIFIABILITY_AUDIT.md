# DA-072 Lattice Identifiability Audit

**Status:** `POSTHOC_LATTICE_IDENTIFIABILITY_CHARACTERIZED`
**Date:** August 31, 2026
**Parents:** DA-070 and DA-071
**Planned embedding calls:** 0
**Planned model calls:** 0

## Scope

DA-070/071 outcomes and target depths are already open. This audit has no
inferential disposition. It asks why deterministic shallow traversal still
requires substantial cumulative work.

## Fixed Classification

Use the 27 questions incomplete under sealed DA-066. For every required session
containing a DA-066-missing episode, rebuild DA-070's exact query-token
signature groups and Hasse graph. Report:

- signature group size and source-order rank within the equal-signature group;
- lattice depth and number of signature nodes at that depth;
- parent count, child count, and breadth-first node position;
- whether the target signature is unique among sessions.

Classify a target session as `EQUAL_SIGNATURE_COLLISION` when its exact
signature group has more than one session; otherwise classify it as
`UNIQUE_SIGNATURE_BRANCH_AMBIGUITY`. Do not add categories after outcomes.

Report counts by session, question, and question type plus distributions of
group size/rank, depth width, and BFS position. This diagnostic cannot select a
branch, validate a stopping rule, or support transfer/adoption. Zero model,
embedding, and cache calls.

## Result

Thirty-one target sessions underlie the 35 missing episodes. Sixteen are
`EQUAL_SIGNATURE_COLLISION`; fifteen are `UNIQUE_SIGNATURE_BRANCH_AMBIGUITY`.
At question level the split is 13/13 plus one mixed. Signature group size is
p50 2/p90 8/max 21; BFS node position p50 7/p90 24. The burden is not one
failure mode. Next test enriches lattice identity with exact adjacent query
bigrams; branch choice/stopping remains separately unresolved.
