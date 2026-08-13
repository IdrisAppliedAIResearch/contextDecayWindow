# Ranking and Budget Development Control Report

**Status:** `COMPLETE - CORPUS-SPECIFIC REGISTRATION JUSTIFIED`
**Specification:** `RANKING_BUDGET_CONTROL_PLAN.md`, commit `cddb1a86`
**Implementation:** commit `7eeee27f`
**Artifact:** `artifacts/ranking_budget_controls.json`
**Artifact SHA-256:** `8ff8bd529f1af00331147b345915dc128ef45acf6c633d04be9d0f9243a79e3b`
**Model calls:** 0
**Embedding calls:** 0
**Date:** August 13, 2026

## 1. Verdict

The no-ranking control refutes the slack-budget explanation. At 32k, source
order delivers all exact evidence on **279/868** LoCoMo development questions,
versus **773/868** for session ranking and **826/868** for pair ranking. The
session-ranked baseline beats source order by 494 items, far outside the
predeclared within-five non-discrimination interval.

The budget sweep finds no LoCoMo sign reversal. Pair ranking beats session
ranking at every truncated budget from 4k through 80k, then ties when 96k admits
every candidate. The off-ceiling baseline budgets fixed by the plan are 8k,
12k, 16k, and 20k.

The proposed cross-corpus binding-ratio rule does not survive. LongMemEval
development all-evidence changes sign between 16k and 24k, but LoCoMo remains
positive over overlapping oversubscription ranges. Binding ratio alone cannot
explain or transfer the ranking direction.

## 2. LoCoMo controls

Primary measure: all exact evidence pairs, 868 unique fully resolvable QA
records. The table reports pair ranking against session ranking.

| Budget | Median store/budget | Source | Session rank | Pair rank | Gains/losses | Net |
|---:|---:|---:|---:|---:|---:|---:|
| 4k | 19.85x | 46 | 503 | 626 | 178/55 | +123 |
| 8k | 9.92x | 77 | 613 | 701 | 145/57 | +88 |
| 12k | 6.62x | 97 | 664 | 746 | 125/43 | +82 |
| 16k | 4.96x | 139 | 702 | 773 | 104/33 | +71 |
| 20k | 3.97x | 174 | 732 | 791 | 89/30 | +59 |
| 24k | 3.31x | 214 | 756 | 809 | 76/23 | +53 |
| 28k | 2.84x | 250 | 765 | 818 | 71/18 | +53 |
| 32k | 2.48x | 279 | 773 | 826 | 71/18 | +53 |
| 40k | 1.98x | 364 | 801 | 837 | 50/14 | +36 |
| 48k | 1.65x | 446 | 817 | 842 | 39/14 | +25 |
| 56k | 1.42x | 535 | 836 | 854 | 25/7 | +18 |
| 64k | 1.24x | 634 | 846 | 860 | 18/4 | +14 |
| 80k | 0.99x | 805 | 865 | 868 | 3/0 | +3 |
| 96k | 0.83x | 868 | 868 | 868 | 0/0 | 0 |

At 32k every development conversation is net positive on all-evidence: +13,
+22, +6, and +12. Both ranked arms spend a median 31,992 characters, so the
difference is ordering rather than unused budget. Pair ranking delivers a
median 146 candidates against 135 because its order also interacts more
favorably with skip-on-overflow character costs; that packing consequence is
part of the treatment, not a separately isolated mechanism.

## 3. LongMemEval moderator control

This control uses only the original 185-item NF-002 development split. The 32k
anchor first reproduces 388 versus 351 on all 465 labelled items.

| Budget | Median store/budget | Session all | Episode all | Gains/losses | Net | Any-evidence net |
|---:|---:|---:|---:|---:|---:|---:|
| 8k | 58.16x | 50 | 58 | 17/9 | +8 | -9 |
| 16k | 29.08x | 65 | 73 | 23/15 | +8 | -16 |
| 24k | 19.39x | 91 | 77 | 14/28 | -14 | -12 |
| 32k | 14.54x | 106 | 85 | 13/34 | -21 | -14 |
| 40k | 11.63x | 111 | 86 | 10/35 | -25 | -17 |
| 48k | 9.69x | 120 | 91 | 11/40 | -29 | -18 |
| 64k | 7.27x | 136 | 96 | 9/49 | -40 | -20 |
| 80k | 5.82x | 144 | 103 | 7/48 | -41 | -16 |
| 96k | 4.85x | 148 | 109 | 5/44 | -39 | -12 |

The all-evidence sign satisfies the predeclared stable-crossover definition:
two positive cells before 16k/24k and at least two negative cells after it.
Any-evidence never crosses and always favors session ranking. The endpoint
therefore matters: at severe truncation, episode ranking assembles complete
multi-episode evidence more often while still losing the broader question of
whether it delivers any answer episode.

## 4. Scope condition rejected

The planned relative rule required matching signs over overlapping p10-p90
store/budget ranges on both corpora. Seven overlapping cells have opposite
all-evidence signs. The clearest is LoCoMo 4k at median 19.85x, net +123 for
pair ranking, versus LongMemEval 24k at median 19.39x, net -14.

This is not a failed instrument. Both arms discriminate, both signs are
reachable, and the LongMemEval grid exhibits a stable crossover. It is a
mechanism result: oversubscription moderates LongMemEval all-evidence, but does
not by itself determine ranking direction across corpora. Session structure,
query/evidence form, or both remain necessary explanatory variables.

## 5. Registration decision

The holdout registration will not claim a universal `rank coarse, pack fine`
direction or a cross-corpus binding-ratio law. Development directly contradicts
both on LoCoMo.

It will instead test the prospective corpus-specific prediction that, on the
six sealed LoCoMo conversations, **pair-level ranking improves all-evidence
delivery over session-level score inheritance** with identical pair candidates
and packing. The primary budget will be 16k: it is the middle fixed grid point
whose baseline is off ceiling (702/868, 80.9%) and whose median binding ratio is
4.96x. It was not selected for the largest treatment effect; all four eligible
off-ceiling budgets are positive and 16k is the interior point nearest the
center of the registered 60%-85% interval.

All-evidence is primary because it is stricter, has more headroom, and is the
endpoint the user authorized. Any-evidence, source order, 32k, and the remaining
fixed budgets are diagnostic only. Exact canonical-QA deduplication remains
binding. The inherited NF-002 disposition tiers remain the proposed bars:
`WORKS` at gains >= 2x losses and one-sided exact p <= .05; `CARRIES_SIGNAL` at
gains > losses and p <= .20. The final pre-registration must still inventory
the holdout mechanically, prove these bars reachable at its actual N, and bind
a separate live answer-quality stage before the holdout can open.

## 6. Integrity

Both 32k anchors ran before any sweep output. LoCoMo recorded 2,236 read-only
cache hits and zero misses; LongMemEval recorded 106,877 hits and zero misses.
The run made zero model and embedding calls. A complete second run is
byte-identical. No LoCoMo holdout conversation was adapted, embedded, counted,
or scored.
