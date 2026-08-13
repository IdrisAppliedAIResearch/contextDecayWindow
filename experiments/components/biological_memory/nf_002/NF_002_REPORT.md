# NF-002 Report — Candidate Granularity Under a Binding Budget

**Status:** `CARRIES_SIGNAL — CHARACTERIZED` (capped by Deviation 001)
**Pre-registration:** `NF_002_PRE_REGISTRATION.md`, committed at `aec39664`
**Deviation:** `amendments/DEVIATION_001_holdout_observed_before_registration.md`
**Part 1:** `NF_002_PART1_RECORD.md`, committed at `2b1c20ee`
**Artifacts:** `artifacts/part1_record.json`, `artifacts/gates.json`
**Corpus:** LongMemEval, 470 answerable items · **Model calls:** 0
**Date:** August 12, 2026

## 1. Result

Identical ranking, identical 32,000-character budget, identical skip-on-overflow
policy. The only difference between arms is the candidate **unit**.

| Split | measure | gains | losses | discordant | p (one-sided) | disposition |
|---|---|---|---|---|---|---|
| development (185) | any evidence | 8 | 0 | 8 | 0.0039 | **WORKS** |
| development (185) | all evidence | 23 | 0 | 23 | <0.0001 | **WORKS** |
| **holdout (285)** | **any evidence** | **14** | **6** | **20** | **0.0576** | **CARRIES_SIGNAL** |
| holdout (285) | all evidence | 34 | 6 | 40 | <0.0001 | **WORKS** |
| all (470) | any evidence | 22 | 6 | 28 | 0.0019 | WORKS |
| all (470) | all evidence | 57 | 6 | 63 | <0.0001 | WORKS |

Recall, all 470: sessions **380 (80.9%)** → episodes **396 (84.3%)**, against an
oracle ceiling of 470.

**The registered primary measure on the holdout is `CARRIES_SIGNAL`.** The loss
ratio passed — 14/6 = 2.33 against a bar of 2.0 — and the p value missed 0.05 by
0.008. One additional gain, or one fewer loss, would have read WORKS.

## 2. The mirror question was answered before the run, and it fired

§5 of the registration asked, per `AGENTS.md` §9.4, whether the gate could fail
while the property it certifies is true, and answered:

> With ~20 discordant pairs, an effect that is real but modest can miss p ≤ 0.05
> on sampling alone: 14 gains against 6 losses gives p = 0.058 and would land in
> CARRIES SIGNAL rather than WORKS on a difference of one item.

That is the observed result, to the item. The lower tier existed before the
number did, which is the only reason this can be reported as signal rather than
argued into a pass or rounded to a null.

## 3. All six losses are in one stratum

| stratum | n | gains | losses | p |
|---|---|---|---|---|
| multi-session | 121 | 6 | 0 | 0.016 |
| single-session-preference | 30 | 6 | 0 | 0.016 |
| single-session-user | 64 | 4 | 0 | 0.063 |
| knowledge-update | 72 | 3 | 0 | 0.125 |
| temporal-reasoning | 127 | 3 | 0 | 0.125 |
| **single-session-assistant** | **56** | **0** | **6** | **1.000** |

Five of six strata are **gains-only**. Every loss in the study sits in
`single-session-assistant`, which records zero gains — episode granularity is
strictly worse there and strictly better or neutral everywhere else.

That is a clean localization, and it is the finding worth carrying. These are
questions about what the *assistant* said. A plausible reading is that an
assistant answer is interpretable only against the session that prompted it, so
fragmenting the session delivers the text and destroys what made it findable —
but this study did not test that, and the reading is a hypothesis, not a result.

## 4. What Part 1 killed, restated

Marginal novelty filtering recovers **0** of the 90-item headroom at every floor
from 0.05 to 0.50, and does harm above it. On 470 items with a budget binding at
14.5×, that is a measured null. NF-001's suggestive +0.56 facts does not survive
an instrument that can price displacement.

Packing order is equally exhausted: `stop_at_first_overflow` 377,
`top_k_by_rank` 323–379, baseline 380. And **89 of 90 baseline misses** have
evidence within reach at median rank 7, skipped because a 13k–23k character
session would not fit once ranks 1–6 had consumed the budget.

The unit was the operative variable. Nothing else tested here was.

## 5. What this cannot claim

**Deviation 001 caps this at `CHARACTERIZED`.** The holdout discordant counts
were printed alongside the development counts before the bars were written, so
no bar here can support a confirmatory claim. The split was not redrawn
afterwards, because having seen the mechanism on all 470 items leaves no subset
sealed.

Also outside scope: this is offline availability against a frozen ranking. It
touches no reader, so it makes no answer-correctness claim, and `AGENTS.md` §4
is explicit that availability is not a verdict. No adoption, ablation, or live
run is authorized.

Finally, the ranking itself is untouched. The oracle sits at 470 and the
treatment reaches 396, so **74 items remain** that no unit or packing change
reaches.

## 6. What a successor would do

1. **Confirm on an untouched corpus.** Every LongMemEval item is now used.
2. **Gate `single-session-assistant` separately, or explain it.** A treatment
   with one strictly-harmed stratum out of six is a candidate for conditional
   application, and the condition is available without a model call — the
   stratum label is not, but "the question asks what the assistant said" may be
   recoverable from query text, which is the one thing DMR-004's compiler did
   at 0.800 recall.
3. **Attack the ranking.** 74 of the 90 missed items survive every unit and
   packing change tested. Cosine over session text put six candidates above the
   evidence at median rank 7.
