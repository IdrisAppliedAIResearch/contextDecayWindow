# DA-082 Unary Dependency-Edge Anatomy

**Status:** `POSTHOC_UNARY_DEPENDENCY_EDGES_CHARACTERIZED`
**Date:** August 31, 2026
**Parent:** DA-081 result commit `63a229f5`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can a residual dependency be addressed without ranking because it is either the
missing sibling of a partially present carrier or the sole frontier child of an
already-present seed?

## Fixed Anatomy

Use the 13 sealed DA-079 residual requirements, sealed DA-078 prompt members,
and sealed DA-045 frontier actions. Join each required carrier/member to the
frozen baseline edges that produced it. For each matching seed report whether
the seed is represented in DA-078 and its number of unique DA-045 frontier
member targets.

Classify `PRESENT_SIBLING` when the carrier's other member is in DA-078;
otherwise `UNARY_PRESENT_SEED` when a represented matching seed has exactly one
frontier target; otherwise `BRANCH_AMBIGUOUS`. Report matching-seed and branch
degree distributions. No feature, score, threshold, answer text, or alternate
edge order is allowed.

Require exact 13/13 joins, frozen identities, byte-identical replay, and zero
model, embedding, and cache calls. This is structural anatomy only; no reader,
stopping, transfer, delivery, or adoption claim.

## Result

Twelve of 13 requirements are `BRANCH_AMBIGUOUS`; one is the known
`PRESENT_SIBLING`; none is `UNARY_PRESENT_SEED`. Matching-seed count is exactly
one throughout, but represented seeds have minimum frontier degree p50 two and
p90 four. Some matching seeds are not represented in DA-078 at all.

The sibling case overlaps DA-081's novelty cases. The six lexically redundant
requirements are all branch-ambiguous, so combining the two structural states
adds no coverage. A payload-only frame has discarded the parent relation needed
to interpret why it was reached. Replay is byte-identical; zero calls.

Artifacts:

- `artifacts/analysis/result.json`
- `artifacts/analysis/edges.jsonl.gz`
