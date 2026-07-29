# Amendment 001 - Historical Measurement Classification

**Date:** 2026-07-29
**Applies to:** DR-001 at `094cbea2`
**Status:** LOCKED by the commit that first adds this file

## Trigger and evidence

Before implementation, a dry reconstruction loaded the immutable Study 010 Arm
L database and the historical `ltm_context_episodes.csv` identity/order list,
then rendered those rows with the unmodified production renderer.

The reconstruction matched the committed prompt blocks character-for-character:

| Probe | Historical charged chars | Actual serialized block chars |
|---|---:|---:|
| Q13, turn 999 | 31,991 | 53,726 |
| Q14, turn 1000 | 31,847 | 53,839 |

The 31,991 and 31,847 values are the sum charged by
`retrieval_budget.rendered_cost`: user-message plus assistant-message
characters. They are not the lengths of the `<retrieved_ltm>` blocks in the
constructed prompts.

DR-001 section 1.1 inherited the supplied draft's incorrect classification of
those values as block lengths. The values themselves are present and correct in
the historical logs; their label and budget-saturation interpretation are not.

## Change

For DR-001 execution:

1. Treat 31,991 and 31,847 as **historical charged content characters**.
2. Treat 53,726 and 53,839 as the authoritative **actual serialized block
   characters**, subject to formal G-R1 reproduction.
3. Evaluate the accounting defect against actual serialized length: the
   historical blocks exceeded `B_ltm = 32,000` by 21,726 and 21,839 characters.
4. Record an `ERRATA.md` correction for published Study 010 statements that
   describe the charged values as the delivered block filling a 32,000-character
   budget.

## Rationale

This repairs a measurement-unit classification before renderer implementation
and before any post-fix output exists. It makes the correctness gate stricter:
the fix must account for every serialized character rather than preserving the
appearance of near-perfect utilization.

## Exclusions

No historical run artifact, score, selected identity, budget value, renderer,
or decision branch changes. The locked DR-001 file remains unedited.

## Authorization

The author authorized amendments on 2026-07-29. This amendment is required by
the standing rule to repair a measurement-unit error without silently changing
the locked design.

