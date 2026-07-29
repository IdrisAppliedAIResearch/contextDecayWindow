# Amendment 009 - Tier 6 New-Arm Adjudication Triggers

**Date:** 2026-07-29
**Status:** Authorized before the Tier 6 live run
**Amends:** T6.1 scoring under `PROTOCOL_scoring_integrity.md`

## Trigger and evidence

Tier 6 creates a new context-matched STM arm. It has no prior or "original"
score. The standing scoring-integrity audit defines H3 as a difference from an
original score and defines H5 eligibility as agreement between the blind AI
score and an original score. Those comparisons are undefined for this arm.

This contradiction was identified after the ablation gate and before live
inference. No Tier 6 rubric answer or score exists.

## Change

1. H3 is reported as `NOT_EVALUABLE_NO_ORIGINAL_SCORE`; it is not counted as a
   pass or a failure.
2. H5 remains a deterministic 10% independent-adjudication sample. Its eligible
   population is the Tier 6 items that:
   - received identical primary and strict scores in all three blind passes;
   - did not trigger H1 or H2; and
   - are not already selected by H4.
3. Eligible items are ordered by SHA-256 of
   `retrieval-bakeoff-t6-h5-2026-07-29-v1:{anonymous_item_id}`. The first
   `ceil(0.10 * eligible_count)` items are selected. If the eligible population
   is empty, H5 selects zero items and the report states that fact.
4. H4 remains mandatory for every Q11 and Q14 item. H1 and H2 are unchanged.
5. The fourth clean-context AI adjudicator and all calibration, blinding,
   rationale, completeness, fact-presence, and commit-order requirements remain
   unchanged.

## Rationale

Inventing an original score would create false evidence. Dropping H5 would
weaken the audit. Sampling otherwise self-consistent items preserves H5's role
as a check on apparently uncontroversial ratings without using an unavailable
comparison.

## Exclusions

This amendment does not change any rubric byte, expected fact, score threshold,
response, runtime setting, retrieval setting, decision threshold, or the
mandatory Q11/Q14 adjudication. It does not authorize opening mechanism logs
before the final score commit.

## Author authorization

The author explicitly allowed amendments when needed in the retrieval-bakeoff
execution request. This amendment is limited to the pre-answer protocol
contradiction above.
