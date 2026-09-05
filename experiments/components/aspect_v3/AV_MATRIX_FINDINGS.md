# AV-MATRIX — the channel decomposition, scored live

**Status:** `COMPLETE — no contrast reaches significance`
**Date:** September 2, 2026
**Cost:** 7,844 reader calls + 7,844 judge calls, ~5 h local GPU. No paid API.
**Runners:** `src/analysis/av_matrix.py` (build), `src/analysis/av_reader.py` (score)
**Artifacts:** `experiments/components/aspect_v3/artifacts/av_matrix/`

---

## 1. The result

Six compositions, two budgets, recency removed, 842 items common to all cells.

| cell | score | F1 | malformed |
|---|---:|---:|---:|
| `CC80` @16k | 70.67% | 0.5431 | 6 |
| `CC80+ASPECT` @16k | **69.71%** | 0.5379 | 6 |
| `CC80+ASPECT+DA` @16k | 70.90% | 0.5482 | 5 |
| `CC80` @32k | 71.50% | 0.5515 | 7 |
| `CC80+ASPECT` @32k | 71.50% | 0.5489 | 7 |
| `CC80+ASPECT+DA` @32k | **72.09%** | 0.5546 | 4 |

**Total spread across all six: 2.38 points — 20 answers out of 842.**

## 2. Not one contrast is significant

Exact two-sided sign tests on the discordant pairs:

| contrast | budget | gains | losses | net | discordant | p |
|---|---|---:|---:|---:|---:|---:|
| ASPECT vs CC80 | 16k | 14 | 22 | **−8** | 36 | .243 |
| ASPECT vs CC80 | 32k | 12 | 12 | **0** | 24 | 1.000 |
| DA-arm vs CC80 | 16k | 20 | 18 | +2 | 38 | .871 |
| DA-arm vs CC80 | 32k | 16 | 11 | +5 | 27 | .442 |
| DA-arm vs ASPECT | 16k | 21 | 11 | +10 | 32 | .110 |
| DA-arm vs ASPECT | 32k | 15 | 10 | +5 | 25 | .424 |
| CC80 32k vs 16k | — | 21 | 14 | +7 | 35 | .311 |

The smallest p in the table is **.110**. Nothing here is demonstrated.

## 3. What moves at all

Between 24 and 38 items are discordant in any pairing — **2.8% to 4.5% of 842.**

Rewrite the entire second half of the retrieval budget, or double the budget
outright, and **more than 95% of answers do not change**. The ones that do move
very nearly cancel.

This is the same shape Study 007 reported from the other direction — retrieval
delivering four-domain coverage while breadth still failed, with the bottleneck
in the model's *use* of context. It is now measured on the reader directly,
across three selection mechanisms and two budgets.

## 4. ASPECT-v1 does not replicate

HH-003 scored ASPECT **+14** over plain episodic (p=.14) on 1,540 items. Here,
on a recency-free composition:

- **16k: net −8** (p=.243) — nominally *harmful*
- **32k: net exactly 0** (12 gains, 12 losses)

This is consistent with the offline matrix, where ASPECT delivered 3.69 points
*less* complete evidence than plain CC80 at 16k and 1.79 less at 32k, and with
TC-011's original `NO_CANDIDATE`. Three independent measurements now point the
same way, and the one that pointed the other way was never significant.

**The registered action follows: ship `aspect_enabled=False`, which is already
the default.**

## 5. What this retires

**AV-000 is answered and should not be run.** It was scoped to replicate
HH-003's ASPECT-on/off contrast on the local reader, at ~4.5 h. This study ran
that contrast — twice, at two budgets, on a cleaner composition with the
untested recency block removed — and the +14 is gone. Spending the GPU time to
ask again on a *dirtier* composition buys nothing.

**The three-arm study is retired with it.** It was conditional on there being an
incumbent worth improving. There is not.

**AV-003 (the write-time facet cache) is retired.** The handoff called it "worth
doing whichever way they land." That was wrong: a 2,522 ms → 100 ms facet cache
has no value if the facets do not ship.

**The DA arm is nominally best at both budgets and still cannot ship.** The
DA-098 allocation exists only for the six NF-004 conversations, which this
programme designates as the development split, so `C` can never be confirmed on
held-out data — and its +5 at 32k is p=.442 regardless.

## 6. Limits — read these before quoting any number above

- **Absolute scores are not comparable to HH-003.** That run used
  `gpt-4o-mini-2024-07-18` for reader and judge; this used local
  Qwen3.8-27B-UD-Q4_K_XL, judged by itself. 70–72% here and 77–78% there are
  different instruments. Only the within-run contrasts are interpretable.
- **Same-model judging** is a known weakness, flagged in the thesis draft, not
  repaired here.
- **One sample per arm. No replicate, so no noise floor was measured.** This
  cuts one way only: an instrument band would make these contrasts *less*
  significant, never more. The programme's one measured band is 3.0 points on a
  13-point rubric, and every effect here is smaller in relative terms.
- **Temperature 0**, deviating from LV-009's registered `.6`. Justified by the
  contrasts resting on 24–38 moved items, where `.6` with one sample has a
  sampling floor larger than the effect. It does not make the runtime
  deterministic.
- **Thinking disabled** (`enable_thinking: false`). Qwen3.8 is a hybrid
  reasoning model; left on it spent the whole token budget on a `<think>` block
  and no answer arrived. Disabling it is also the closer match to
  `gpt-4o-mini`, which has no thinking mode.
- **Recency was removed from every arm**, so these are not the deployed
  compositions. That was deliberate — the 32-episode block is ~28% of every HH
  payload, positionally selected, and no study has ever contested it. Its own
  contribution remains unmeasured.
- 35 of 5,052 judgements were malformed (0.7%) and are counted as incorrect,
  not dropped.

## 7. The one thing still worth measuring

Every number in this programme sits on top of an untested 12k recency block.
Gold evidence lands *entirely* inside it for 9.6% of items — but those episodes
are excluded from CC80 admission only *because* recency already delivers them,
so its true unique contribution is probably far smaller and may be negative
(`A_FULL`, the whole conversation, scores below every retrieval arm).

That is one arm, no new mechanism, and it is the largest uncontested allocation
left in the payload.
