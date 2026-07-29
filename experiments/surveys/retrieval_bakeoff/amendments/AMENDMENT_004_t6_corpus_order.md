# Amendment 004: Tier 6 Corpus Order

**Date:** 2026-07-28  
**Status:** Authorized before Tier 6 implementation or inference  
**Applies to:** T6.1 only

## Trigger And Evidence

The locked T6.1 language specifies a context-matched rerun of Study 009 Arm L:
the same seed and script, widened pure-STM retrieval, and comparison against the
committed 121-turn scores of 9.0 for Arm S and 12.0 for Arm L. Elsewhere, the
pre-registration makes Study 010's 1,000-turn stores the primary corpus wherever
the test permits. That later corpus-priority decision did not update T6.1 and
left its intended live-run horizon ambiguous.

The author clarified that T6.1 was intended to match Study 009 Arm L at 121
turns and recommended running that version first. It is an order of magnitude
cheaper and preserves the clean same-seed 9.0-versus-12.0 comparison that
motivated the test.

## Change

T6.1's registered live test is the **121-turn Study 009 Arm L match**. It uses
the Study 009 script and seed and matches Arm L's exact serialized delivered
retrieval characters under the widening rule already locked in the
pre-registration.

The 1,000-turn Study 010 Arm L match is not substituted for this test. It is a
conditional confirmatory extension:

- If the 121-turn widened-STM score is at least the committed Study 009 Arm L
  score of 12.0, do not run the 1,000-turn extension.
- If the 121-turn widened-STM score is below 12.0, run the 1,000-turn
  context-matched extension after committing the 121-turn score and before
  opening its mechanism logs.

The 1,000-turn extension, if triggered, is reported separately and does not
retroactively alter the registered interpretation of the 121-turn result.

## Rationale

The short run directly tests whether LTM's observed three-point advantage was
only added context volume. A score of at least 12.0 answers that question
without paying for an unrelated longer-horizon generation. A lower score leaves
some or all of the LTM advantage intact; only then does the 1,000-turn run earn
its cost as confirmation at the deployment horizon rather than exploration.

## Exclusions

This amendment does not change the retrieval-character matching rule, seed,
script, generation settings, scoring protocol, score-before-logs order, or any
offline tier. It does not change either historical arm or its committed score.
Calibration remains development-only and must be committed before inference.

## Authorization

The repository owner authorized this clarification on 2026-07-28 and explicitly
recommended the 121-turn version first, followed by the 1,000-turn version only
when the short result leaves LTM's advantage intact.
