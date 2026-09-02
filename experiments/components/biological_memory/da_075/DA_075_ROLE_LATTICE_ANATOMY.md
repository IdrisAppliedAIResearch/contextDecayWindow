# DA-075 Role-Lattice Anatomy Audit

**Status:** `POSTHOC_ROLE_LATTICE_ANATOMY_CHARACTERIZED`
**Date:** August 31, 2026
**Parent:** DA-074 result commit `e1265a7d`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Scope

DA-074 outcomes and DA-072 target identities are open. This diagnostic has no
inferential disposition. It measures how role provenance changed target-node
identifiability and traversal anatomy.

## Fixed Analysis

Use the same 31 DA-072 target sessions. Rebuild DA-074's exact augmented
signatures and Hasse graph. For each target session report:

- role-signature group size and source-order rank;
- role-lattice depth, depth width, and BFS node position;
- parent and child counts; and
- whether DA-072 classified it as an equal-signature collision or unique branch.

Classify the DA-074 state as `ROLE_SIGNATURE_COLLISION` when the augmented
signature group has more than one session, otherwise `ROLE_SIGNATURE_UNIQUE`.
Report the 2x2 transition from DA-072 class to DA-074 state, plus distributions
and changes in BFS position where comparable.

No new class, selector, branch rule, or stopping criterion may be introduced.
This cannot support transfer or adoption. Zero model, embedding, and cache
calls.

## Result

Role features make 26/31 target sessions unique and leave 5 collisions. Eleven
of DA-072's 16 collisions split; all 15 previously unique sessions remain
unique. Target depth is p50 1/p90 2/max 2, but depth width grows to p50 14 and
BFS position to p50 15 (change p50 +3). Provenance improves identity while
widening shallow branches. Next audit whether ordered per-episode role-feature
sequences split the five residual collisions that session union cannot.
