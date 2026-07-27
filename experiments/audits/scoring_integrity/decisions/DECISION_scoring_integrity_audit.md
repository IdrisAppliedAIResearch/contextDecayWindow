# Decision - Scoring Integrity Audit

**Date:** 2026-07-26  
**Status:** Author-authorized

## Trigger

A prior diagnostic found a committed positive score attached to a truncated,
reasoning-only response with no scoreable final answer. Because score totals anchor
later bars, the correction must cover the complete record rather than one item.

## Decisions

1. Only content outside reasoning blocks is scoreable.
2. Completeness and mechanical evidence precede judgment.
3. Rubric bytes remain locked; criteria-only guidance makes application explicit.
4. Every arm is audited uniformly and original artifacts are preserved.
5. Study 003 Bar 2 is governed by its literal `overall >= 13.0` criterion.
   Corrected-baseline non-regression is reported separately and cannot change FAIL.
6. This choice intentionally rejects a more favorable reconstructed-intent reading.
   It is evidence against using the audit as a rescue operation.
7. The ambiguity arose because prose said "non-regression" while the criterion froze
   a number. Standing Protocol R11 now requires cross-study references to cite the
   artifact SHA and be recomputed after corrections.
8. The author authorized an independent clean-context AI subagent in place of the
   draft's human adjudicator. This substitution must be disclosed and cannot be
   described as human review.

## Leakage Boundary

Plant keys and rubric facts are evaluation-only. No retrieval, formation, ranking,
dreaming, or context-assembly component may read them.

