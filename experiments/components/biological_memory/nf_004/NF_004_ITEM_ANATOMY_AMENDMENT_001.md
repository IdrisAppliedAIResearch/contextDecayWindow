# NF-004 Item Anatomy Amendment 001 - Replay Anchor

**Status:** `PRE-FEATURE-RUN REPAIR`
**Date:** August 29, 2026
**Applies to:** `NF_004_ITEM_ANATOMY_EXPLORATION.md` at commit `05132cda`

## Trigger

Section 7 PF2 asked the exploration to reproduce NF-004's historical ranking
orders and packed candidate identities before extracting features. Inspection
after the protocol commit found that NF-004's committed G6 artifact retains
per-arm delivery metrics but not ranking orders or selected candidate
identities. G7 retains the byte-identical replay digest of G6, not a hidden
payload manifest. There is therefore no historical holdout payload against
which the requested identity comparison can run.

No item-anatomy feature artifact has been generated and no analysis process has
opened G6 outcomes on this branch.

## Repair

Replace PF2's unavailable historical payload comparison with both checks below:

1. Run the evidence-blind extractor twice from the locked corpus, retained
   vector cache, and committed NF-004 mechanism. Require byte-identical feature
   CSV files, including both arms' selected-identity digests.
2. After committing the sealed feature artifact, join G6 and require exact
   reproduction of the 1,098 primary population, 843 session passes, 935 pair
   passes, 140 pair gains, and 48 session rescues before any predictor result is
   emitted.

The feature module remains unable to import the measurement module or read G6.
The amendment changes no feature, model, fold, lambda, permutation count,
reporting rule, or claim boundary.

## Interpretation

This repair establishes current deterministic replay plus historical aggregate
identity. It cannot retroactively create candidate-identity artifacts NF-004
did not store. The final report must state that limitation rather than describe
the replay as a payload-level reproduction of the 2026-08-13 holdout run.
