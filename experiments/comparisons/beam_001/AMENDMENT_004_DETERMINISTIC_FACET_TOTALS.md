# BEAM-001 Amendment 004 - deterministic facet totals

**Status:** `AUTHORIZED BLOCKER REPAIR - PRE-RUN`  
**Date:** August 28, 2026  
**Author direction:** amend, fix and rerun without repeating completed embeddings

## 1. Trigger

The first BEAM T1 context stopped before producing a treatment row. The frozen
TC-013 helper computed facet totals by iterating each `frozenset`, but computed
the overlap diagonal by visiting globally sorted facet postings. On the first
real BEAM conversation, 25 of 62 eligible episodes differed by more than the
helper's absolute `1e-12` assertion tolerance. The maximum absolute difference
was `5.4569682106375694e-12`; the maximum relative difference was
`2.203658927189418e-15`.

This is a floating-point accumulation-order discrepancy, not missing facets or
a changed objective. Relaxing the assertion would preserve a hash-order-
dependent total and is therefore not an acceptable repair.

## 2. Frozen repair

BEAM-001 T1 alone will use a study-private deterministic overlap helper:

1. visit facet postings in lexicographically sorted facet order;
2. accumulate the pairwise overlap matrix in that order, unchanged from the
   carried postings implementation;
3. define each candidate's total facet weight as an exact copy of the resulting
   overlap diagonal; and
4. require finite, non-negative totals and an exactly equal diagonal.

The diagonal is the candidate's self-overlap and therefore the same mathematical
sum as its total facet weight. Deriving one from the other removes duplicate
floating-point accumulation rather than introducing a tolerance, coefficient,
rounding rule or alternate selector.

The shared `analysis.tc013_fanout` implementation remains unchanged. No public
`episodic-chat` source or configuration changes.

## 3. Binding gates

Before BEAM T1 resumes:

1. replay all 871 committed TC-014 opportunity cases;
2. require identical ordered selected identities and payload SHA-256 values on
   all 871 cases;
3. demonstrate exact diagonal/total equality on the failing first BEAM trace;
4. rerun the focused BEAM, TC-013 and TC-014 tests; and
5. resume from completed question-arm checkpoints only after gates 1-4 pass.

Any historical identity or payload mismatch stops as
`DETERMINISTIC_REPAIR_CHANGED_MECHANISM`.

## 4. Embedding boundary

The completed cache of 61,011 bindings and 60,990 unique vectors is retained.
Its SQLite integrity check, GPU sentinel SHA-256 and longest-input GPU SHA-256
have passed. This amendment does not change text, model, runtime, call shape,
vector width or cache bindings, so no episode or question is re-embedded.

The resumed exploration is cache-only and does not load the local embedding
model. GPU idleness during exploration is expected. Part 1 still makes zero
generation, judge or OpenAI API calls.
