# Amendment 001 - Study 001 Variants

**Date:** 2026-07-26  
**Scope:** `fact_variants.json` only

The SIA_001 lock listed the Study 001 rubric as a source and included Study 001 in
scope, but accidentally omitted its distinct Meridian and CRISPR variant entries.
The defect was found during accepted-arm inventory after the lock commit and before
Layer 1 was run.

The added variants were derived only from
`experiments/study_001/rubric_filled.md`. No Study 001 answer text was consulted to
choose them. The main operator had opened a Study 001 score sheet during inventory,
so strict pre-answer git ordering is not claimable for this amendment even though
scores, rather than answer wording, were exposed. Study 001 fact-presence results
must carry this timing limitation.

No Study 002-009 variant changed.

