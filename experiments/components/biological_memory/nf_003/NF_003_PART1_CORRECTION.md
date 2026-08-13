# NF-003 Part 1 Correction - Evaluated Population and Residual

**Status:** `CORRECTION TO INTERPRETATION; COMMITTED ARTIFACTS UNCHANGED`
**Part 1 commit:** `a96630ea5557456987bb81cb03f1c43400040e2b`
**Part 1 artifact:** `artifacts/part1_record.json`
**Date:** August 13, 2026

## What changed

Part 1 reports the treatment as `445/470` and describes 25 remaining items as
deep episode-ranking misses. The analysis function actually skips five items
before ranking because none of their turns carries LongMemEval's `has_answer`
flag. It emits 465 rows, not 470.

All five skipped items are `single-session-assistant` questions. NF-002's
session-inherited episode arm misses all five, but NF-003 never ran its treatment
on them. Counting them as treatment misses is a conservative lower bound, not an
observed treatment result.

## First correction: evaluated population

- Evaluated population: 465 items with turn-level evidence flags.
- Baseline: 396/465 have any evidence session delivered.
- Treatment: 445/465 have any evidence session delivered.
- Paired comparison: 49 gains, 0 losses, 416 ties. This is unchanged.
- Measured treatment residual: 20 items. Their best evidence-episode rank ranges
  from 12 to 168, with median 50.5 and p90 148.7.
- Unmeasured population: five items lacking turn-level flags. Their NF-003
  treatment outcome and evidence-episode rank are unknown.

The earlier `445/470` is valid only if explicitly labelled a lower bound formed
by treating every unrun item as a miss. It is not the treatment's measured
recall. The claim that all 25 residual items have deep episode ranks is
withdrawn; only 20 were ranked.

## Second correction: the paired effect is a surrogate

The population correction is not the final reading. A subsequent PF9 audit
found that touching an annotated answer session can pass without delivering
the episode marked `has_answer`. That happens on 8 baseline items and 94
treatment items.

Measured like-for-like at the answer-episode unit, baseline delivery is 388/465
and treatment delivery is 351/465, with 26 gains and 63 losses. The 49-gain,
zero-loss pair survives only as an exact description of session-touch, not as a
mechanism finding about evidence delivery. See
`NF_003_PREFLIGHT_SURROGATE_AUDIT.md` and `artifacts/surrogate_audit.json`.

No locked registration, score, or run artifact is edited. The proposed NF-003
registration stopped before lock because its primary instrument failed the
surrogate audit. The five omitted items all belong to the old holdout and remain
unmeasured.
