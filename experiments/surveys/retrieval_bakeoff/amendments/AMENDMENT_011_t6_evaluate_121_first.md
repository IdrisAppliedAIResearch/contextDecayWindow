# Amendment 011: Evaluate Tier 6 121-Turn Result First

**Date:** 2026-07-29
**Status:** Authorized before opening Tier 6 mechanism logs
**Applies to:** Amendments 004 and 010 execution order and evidence label only

## Trigger And Evidence

The blinded 121-turn widened-STM score was committed at `39423b02` as
6.5/13.0. Amendments 004 and 010 require the triggered 1,000-turn extension
before anyone opens the 121-turn mechanism logs.

After seeing only the committed score and before any mechanism log was opened,
the repository owner directed that the 121-turn result be evaluated before
committing compute to a 1,000-turn run. The owner also clarified that a later
1,000-turn run would confirm the short-run finding rather than explore whether
the extension is worth running.

The 1,000-turn protocol was committed at `ed7caba0` before this sequencing
change and before 121-turn mechanism analysis. No extension implementation,
calibration, ablation, or inference has begun.

## Change

1. The automatic 1,000-turn execution is deferred. No extension implementation,
   calibration, ablation, or inference may begin without a new explicit owner
   instruction to proceed.
2. The committed 121-turn mechanism seal may now be verified and opened for
   analysis. Its score-before-logs order remains satisfied because the final
   blinded score and private arm mapping were committed before this amendment.
3. The 121-turn evaluation must report delivered-character match, N/K
   composition, fact presence, fact use, retrieval displacement, context
   capacity, rule behavior, and any failure that can explain the 6.5 score.
4. Amendment 010's label `conditional, post-stop exploratory result` is
   superseded. If later authorized and executed without changing its
   pre-analysis protocol, the 1,000-turn arm is a **conditional confirmation
   within the retrieval bakeoff**, compared with the committed post-stop
   Study 010 benchmarks. This does not retroactively make Study 010
   confirmatory.
5. Every parameter and gate committed in Amendment 010 remains frozen while
   the 121-turn logs are inspected. Mechanism findings may inform whether the
   owner authorizes the compute, but may not alter the extension's target,
   grid, script, seed, scoring denominator, or runtime protocol.
6. Any requested extension design change after the 121-turn logs are opened
   requires escalation as a new study or explicitly exploratory test; it
   cannot be represented as the pre-analysis conditional confirmation.

## Rationale

The 121-turn score is substantially below both the pure-STM and LTM historical
benchmarks. Understanding whether that result reflects character matching,
retrieval composition, fact delivery, or model use is decision-relevant before
spending an order of magnitude more compute.

The extension protocol was already committed before mechanism access. Freezing
it preserves a meaningful confirmation path while honoring the owner's choice
to decide on compute after evaluating the cheaper result.

## Exclusions

This amendment does not change the 121-turn script, seed, settings, answers,
rubric, score, interpretation thresholds, or committed artifacts. It does not
authorize a 1,000-turn run, alter any Amendment 010 parameter, rescore a
historical arm, or make Study 010's stopped confirmatory study valid.

## Authorization

On 2026-07-29, the repository owner explicitly preferred evaluating the
121-turn result before committing to the 1,000-turn study and confirmed that a
later long run, if authorized, would serve as confirmation rather than
exploration.
