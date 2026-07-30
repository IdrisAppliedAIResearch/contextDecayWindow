# Decision 001 - Invalidate AS-001 Branch D Interpretation

**Date:** 2026-07-29
**Type:** post-result invalidation and diagnostic continuation
**Authorization:** user review after AS-001 output commit `f6d5d79c`

## Timing

This decision was raised after the packing output was opened and after the
report applied Branch D. It is therefore not an amendment to the locked AS-001
rule and must not be described as a pre-result repair. The committed analysis
artifacts remain unchanged as evidence of the rule failure.

## Trigger

AS-001 assumed compact exact-cost rendering might recover fitted slots. The
opened result showed the opposite:

- historical widened-STM payload: 15 episodes at 59,708 serialized characters;
- compact exact-cost point: 9 episodes at 31,742 characters;
- compact exact-cost sweep maximum: 16 episodes at 63,086 characters; and
- target episode: rank 27, absent throughout the locked 16k-64k sweep.

The locked rule has no interpretive branch for a slot count below the historical
15. Branch D syntactically catches every failure to deliver rank 27, including a
budget too small to approach that rank, and then labels all such outcomes
`PRIMACY MECHANISM LIVE`. Branch A required at least 29 fitted episodes at 32k,
although the pre-output DR-001 re-derivation already showed exact charging
reduced fitted counts in the carried probes. The null was not capable of
firing in the tested regime, while Branch D was nearly foreordained.

This is the standing surrogate failure one level up: the decision rule could
certify a distinct primacy mechanism when it had only demonstrated that rank 27
was unreachable under the joint N-first packing and character budget.

## Decision

1. Preserve `artifacts/analysis/` unchanged and classify it as diagnostic.
2. Withdraw `PRIMACY MECHANISM LIVE` and the proposed pinned-tier consequence.
3. Retain only the descriptive result: compact exact-cost N-first packing does
   not deliver turn 55 anywhere in the locked 16k-64k sweep.
4. Attribute that exclusion jointly to ranking/packing and budget. AS-001
   cannot identify primacy as a separate mechanism.
5. Do not authorize CC-001 or another architecture study from this result.

## Post-Result Diagnostic

Add a deterministic, separately labeled reachability calculation over the
preserved candidate order. It may report the minimum exact character budget at
which rank 27 enters under the unchanged packer. This calculation describes the
joint rank/budget boundary only; it cannot restore the invalid Branch D verdict
or become confirmatory evidence.

