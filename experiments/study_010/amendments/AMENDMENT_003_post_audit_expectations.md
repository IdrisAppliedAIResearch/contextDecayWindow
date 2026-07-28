# Study 010 Amendment 003: Post-Audit Expectation Corrections

**Date:** July 26, 2026
**Authorized by:** Muzaffer Ozen
**Authorization:** Study 010 may be amended to incorporate information established by the completed Study 009 audits.
**Applies after:** the binding G2 stop
**Does not reopen:** gates, rehearsal, or live inference

## Trigger

Study 010 locked and stopped before the Study 009 scoring-integrity,
duplication, baseline, and breadth-regression audits were complete. Those
audits corrected one numeric premise and invalidated several causal
expectations quoted in the Study 010 registration and branch-resolution
records.

The locked files remain unchanged. This amendment governs their interpretation.

## Corrected Study 009 Result

Study 009 Arm L remains **12.0/13.0**. Arm S is corrected from **10.5/13.0**
to **9.0/13.0**, making the same-seed L-minus-S gap **3.0 points**, not 1.5.

This correction supersedes the Arm S value in Amendment 001 and
`decisions/DECISION_branches_study010.md`. It strengthens the descriptive
Study 009 contrast but does not change a Study 010 bar, gate, or outcome.

Source: `ERRATA.md` and
`experiments/audits/scoring_integrity/cascade_verdict_table.md`.

## Corrected Duplication Expectation

The pre-registration says that at 120 turns LTM "can only duplicate or
displace what STM already finds." The preserved Study 007 treatment used as
Study 009 Arm L does not support that expectation.

Across all 121 turns, the rendered LTM source-episode set had zero overlap with
the rendered STM-plus-recency set after containment dedup. At turns 120 and
121, containment removed five candidates and the resulting LTM block contained
zero duplicate characters. Its records were additional context, not rendered
duplicates.

Therefore Study 010 must not be interpreted as testing whether scale finally
makes a previously duplicative tier unique. LTM was already delivering unique
post-dedup material at 120 turns.

Source:
`experiments/study_009/analysis/duplication_and_baseline_audit.md`.

## Corrected STM Reach Expectation

The claim that a 120-turn raw store "never outgrows K retrieval's reach" is
also too strong. At the breadth probe, Study 009 Arm S had no K-only survivors,
while the accepted Study 007/Study 009 L trajectory delivered unique LTM
records. The baseline audit found unchanged registered N/K parameters but
shorter stored responses and different selected episodes in Arm S. Because
full candidate similarities and query embeddings were not preserved, the
cause of K collapse cannot be isolated without new inference.

The defensible expectation is:

> Retrieval breadth can degrade before 1,000 turns through trajectory-dependent
> episode text and embeddings, selection composition, and store growth. Scale
> may worsen that behavior, but store size alone is not an established cause.

Source:
`experiments/study_009/analysis/breadth_regression_audit.md`.

## Revised Study 010 Interpretation

Study 010 was not the "first environment in which STM-vs-LTM is a fair fight."
Study 009 was already a same-seed internal contrast and found a corrected
3.0-point LTM advantage. Had Study 010 reached live inference, its purpose
would have been to test whether that advantage persisted, grew, or reversed
across a larger store and older plants, while measuring trajectory-specific
degradation.

The following remain unchanged:

- Arm definitions and runtime parity;
- digest carry resolved false;
- the registered Bar 1 decision thresholds;
- the 1,000-turn script, rubric, plant key, and artifact lock;
- every gate result;
- the binding G2 stop before rehearsal and live inference.

## Outcome

This amendment corrects expectations only. G2 independently established that
the accepted TopicManager could not represent the locked 12-domain script
without mass merging or fragmentation. Study 010 remains **STOPPED AT G2
BEFORE LIVE INFERENCE**, with Bars 1-3 not evaluable.

No inference call is authorized or required by this amendment.
