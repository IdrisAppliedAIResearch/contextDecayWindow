# Amendment 004 - Targeted Item Identity In The No-Regression Gate

**Date:** 2026-08-01
**Applies to:** E005 no-regression measurement; corrects a published E002 number
**Type:** Measurement-unit correction
**Status:** APPLIED before the E005 outcome was accepted

## Trigger And Evidence

The first E005 execution returned `REJECT_NO_REGRESSION` with a maximum of
**14 of 16** committed-available targeted items preserved, across all 146
configurations and all three candidate pools. No configuration reached 16.

The per-item breakdown contradicted that aggregate. Summed over 146
configurations there were only 21 individual item losses, concentrated in two
items at turn 119, so the great majority of configurations lost nothing at all
yet still scored 14/16.

Inspection of the committed E002 artifact
`artifacts/e002/targeted_no_regression.csv` showed the same signature from the
other direction: **every** committed-available row has `preserved = True`, and
E002 nonetheless reported 14/16.

## Cause

`TARGETED_ITEMS` contains two questions that probe the same turn and share two
items:

- `Q7` at turn 118 includes `vampyroteuthis infernalis` and `kenji watanabe`;
- `Q10` at turn 118 includes the same two items.

The availability map was keyed on `(turn, item)`. That key collapses the Q7 and
Q10 rows into two entries, so the numerator can reach at most **14** distinct
keys. The denominator, `targeted_required`, was computed by summing
`committed_available` over the committed **row list**, which counts the
duplicated rows separately and therefore equals **16**.

Numerator and denominator were measured in different units. The gate
`preserved == required` was unsatisfiable by construction, independent of any
selector's behavior.

This is the program's recurring count-unit failure: a budget or tally breaks
silently when the unit it counts changes size or multiplicity.

## Change

Availability is keyed on question-scoped identity, `(question, turn, item)`, so
that the two Q10 rows are measured and counted separately, exactly as the
denominator counts them. Implemented as `targeted_key` in
`src/analysis/e005_diversity_selection.py` and gated by a regression test that
asserts the naive key yields 14 distinct entries, the scoped key yields 16, and
the required count is 16.

## Effect On E005

The E005 outcome changes from `REJECT_NO_REGRESSION` to `PROMOTION_ELIGIBLE`.

The change is a measurement repair, not a relaxation. No threshold, gate
definition, arm, parameter, or tie-break was altered. The corrected measurement
was applied to every configuration uniformly and before the outcome was
accepted, and the arms themselves were not re-run: selection is unchanged and
byte-identical, only the fact-counting layer differs.

## Effect On E002

E002's published targeted figure of **14/16 is corrected to 16/16**. E002's
committed artifact already shows zero unpreserved items; only the summary
count was wrong.

**E002's KILL verdict is unaffected.** E002 was killed on its primary gate,
reaching at most 10/17 Q11 items against a locked 14/17 requirement. Its
no-regression result was never the binding constraint. The correction means
E002 passed the no-regression gate it was previously recorded as failing.

Recorded in `ERRATA.md`. The committed E002 artifacts are not edited.

## Exclusions

- No E002 artifact, score, or verdict is rewritten.
- No E005 threshold is changed.
- The correction does not make any criterion easier after results are known; it
  makes an unsatisfiable criterion satisfiable in the way it was always written.

## Authorization

Raised and applied by the implementing agent under the standing rule that
amendments may correct measurement units. The defect makes a registered gate
unsatisfiable, which is a genuine blocker rather than a preference.
