# Scoring Integrity Audit Report

**Status:** complete with disclosed protocol amendments  
**Scope:** 17 arms, 222 scored items, Studies 001-009  
**Study 010:** not read, written, hashed, contacted, or reconfigured

Study 010's exploratory 21.5/23 and 16.5/23 scores are outside this audit. They
must not be compared directly with the corrected Studies 001-009 series without
an explicit unaudited-results note.

## Executive Finding

The triggering Study 002 C Q11 score was not an isolated one-point error.
Study 002 C corrects from 13.0 to **8.5/13.0**. Its Q11 artifact is an unclosed
reasoning block with no scoreable final answer: 5/17 Q11 facts appear in raw
reasoning, 0/17 appear on the scoring surface, and the corrected score is 0.

Across the corpus, **19 of 222 scores change**. Study 001's headline verdict moves
from VALIDATED to **PARTIAL**. Other headline labels remain, though multiple totals
and margins change.

## Method

- Methodology and variants were committed before the mechanical sweep.
- Q11/Q14 guidance was committed from criteria only.
- Layer 1 covered all 222 items and hash-verified every source before and after.
- The valid blind corpus contained 79 selected items: every flag, every Q11/Q14,
  and a deterministic 15% unflagged control sample.
- Three clean-context passes each passed synthetic calibration 7/7.
- AI self-consistency was **97.47%** (77/79).
- Trigger counts: H1 16, H2 2, H3 20, H4 24, H5 4.
- Twenty-eight H4/H5 items were independently adjudicated before evidence reveal.
- Twenty H1-H3-only conflicts were adjudicated with evidence visible.
- H5 disagreement was **0/4**.
- Control-sample disagreement was **11.54%**, below the pre-registered full-rescore
  threshold of **22.97%**; escalation did not fire.

The residual-error figure is an extrapolation, not a measured count. The
control sample contained 3 disagreements in 26 items. Applying 11.54% to the
143 unreviewed items yields 16.5 expected residual errors, reported informally
as "about 20." Sampling uncertainty remains; no 16.5- or 20-item set was
observed.

The author amended the draft to use clean-context AI subagents as adjudicators.
These are not human ratings. The audit preserves the anchoring controls but cannot
claim human adjudication.

## Corrected Totals

| Study | Arm | Original | Corrected | Q14 corrected |
|---|---|---:|---:|---:|
| 001 | Iterative | 9.0/10 | 8.0/10 | - |
| 001 | Full context | 10.0/10 | 10.0/10 | - |
| 001 | Compaction | 3.5/10 | 2.5/10 | - |
| 002 | C iterative | 13.0 | **8.5** | - |
| 002 | A full context | 8.0 | 5.5 | - |
| 002 | B compaction | 2.0 | 2.0 | - |
| 003 | Accepted | 12.0 | **11.5** | - |
| 004 | Treatment | 7.0 | 6.5 | 0.0 |
| 004 | Control | 11.0 | 10.5 | 0.0 |
| 005 | Treatment | 11.0 | 11.0 | 0.5 |
| 005 | Control | 12.0 | 11.5 | 0.0 |
| 006 | Treatment | 10.5 | 9.0 | 0.0 |
| 006 | Control | 11.0 | 11.0 | 0.5 |
| 007 | Treatment | 12.0 | 12.0 | 0.5 |
| 007 | Control | 10.5 | 10.0 | 0.0 |
| 009 | L | 12.0 | 12.0 | 0.5 |
| 009 | S | 10.5 | 9.0 | 0.0 |

The Study 002 README displayed A as 8.5 while its committed score sheet sums to
8.0; the audit uses item-level committed scores and records the discrepancy.
This is the concrete failure Protocol R11 now prevents: cross-study totals must
cite artifact SHAs and be recomputed from the authoritative item-level record.

## Q11/Q14 Guidance

Q11 is binary. Its 17-item denominator requires at least 14 correctly attributed
items for 1.0; there is no 0.5. Q14 has a narrow 0.5: all four domains named and
exactly one missing/incorrect specific.

## Cascade

Study 003 Bar 2 remains FAIL under its literal `>= 13.0` wording. Its corrected
11.5 does exceed corrected Study 002 C (8.5), but reconstructed non-regression
intent is observational only. Protocol R11 now requires score references to cite
artifact SHAs and be recomputed after correction.

Study 009's null result strengthens numerically: S trails L by 3.0 rather than
1.5. This remains a confounded single-run comparison and does not repair the
digest bars, which remain not evaluable.

See `cascade_verdict_table.md` for every bar.

## Integrity Deviations

1. Study 001 and rule variants were omitted from the first lock and added before
   Layer 1; Amendments 001-002 disclose the timing.
2. The first Layer 2 sequence misread Study 003 cross-reference sections. It is
   invalidated in full by Amendment 003; no score from that sequence is reused.
3. Adjudicators were independent AI subagents, not humans, by author amendment.
4. Some Study 002 artifacts are git-ignored but preserved locally; provenance is
   the path and pre/post SHA registry.

No source artifact hash drift occurred.

