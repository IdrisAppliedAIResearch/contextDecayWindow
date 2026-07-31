# E002 Post-Hoc Interpretation Note

**Date:** 2026-07-31
**Scope:** Interpretation and provenance only
**Outcome change:** None. E002 remains KILL under its locked criterion.

## Trigger

Closeout review identified that the report stated the registered 13/17 hurdle
without making its different budget regime prominent. This note traces the
comparison to committed artifacts and records the descriptive matched-budget
result without changing the criterion after output.

## Provenance

The corrected Tier 6 Q11 result made 13/17 atomic items available at turn 120.
Its exact widened-STM retrieval payload was 60,285 characters under the
prospectively locked 60,595-character cap. The often-cited 59,708-character
payload is Tier 6 turn 115 (Q4), not Q11.

E002 used post-DR-001 compact rendering and exact complete-block charging at an
enforced 32,000-character cap. Its unchanged-selector baseline made 6/17 items
available at 31,946 characters. The best segmented configuration made 10/17
available at 21,761 characters. Segmentation therefore added four items, a
66.7% increase over its matched-budget baseline, while remaining below the
locked 14/17 pass threshold and the registered 13/17 historical hurdle.

The 6/17 result is the first post-DR-001 compact-renderer baseline for this
selector, not the program's first exact-budget breadth measurement. Retrieval
bakeoff Tier 1 had already measured 8/17 at 31,861 exactly serialized
characters using its registered expanded renderer and M4 method. Those figures
use different selectors and renderers and must not be substituted for one
another.

## Interpretation

The procedural E002 KILL is unchanged. The corrected interpretation is that
mechanical segmentation did not reach a hurdle established at 1.884 times its
allowed payload, but it substantially improved the unchanged selector at the
same enforced budget. F1 therefore remains open, with segmentation the best
matched-budget improvement tested in the ledger.

## Per-Segment Diagnostics

The primary configuration (`S=4`, `o=1`, `b=2`) generated nine segments and 18
retrieval slots. Ten slots added unique episodes and eight returned duplicates.
Two segments added no unique episode, five added one, and two added two.

| Segment | Text | Unique episodes | Duplicate slots |
|---:|---|---:|---:|
| 0 | `List` | 1 | 1 |
| 1 | `every specific numerical value,` | 1 | 1 |
| 2 | `named entity, and technical` | 0 | 2 |
| 3 | `specification we established across` | 1 | 1 |
| 4 | `all four topics in` | 0 | 2 |
| 5 | `our entire conversation today` | 1 | 1 |
| 6 | `bridge engineering, Renaissance` | 2 | 0 |
| 7 | `art, monetary policy, and` | 2 | 0 |
| 8 | `marine biology.` | 2 | 0 |

These counts came back, but they do not validate an absence detector. Seven of
nine segments added at least one unique episode while the payload still missed
7/17 facts and the entire Renaissance-art domain. Duplicate or zero-unique
counts therefore do not certify whether the required information is complete.
F3 remains unclaimed.

## Evidence

- Tier 6 exact Q11 payload:
  `experiments/surveys/retrieval_bakeoff/tier6/analysis_corrected_121/probe_context_match.csv`
- Tier 6 Q11 availability:
  `experiments/surveys/retrieval_bakeoff/tier6/analysis_corrected_121/breadth_fact_delivery.csv`
- E002 matched baseline:
  `artifacts/e002/same_budget_baseline.json`
- E002 result:
  `artifacts/e002/e002_results.json`
- E002 segment outcomes:
  `artifacts/e002/primary_segment_selection.csv`
- Tier 1 exact-budget result:
  `experiments/surveys/retrieval_bakeoff/tier1/tier1_report.md`
