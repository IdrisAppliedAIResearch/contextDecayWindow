# TC-005 Report — relevance efficiency under a half-budget

**Standing:** `REGISTERED-OFFLINE`  
**Status:** `COMPLETE`  
**Pre-registration:** `TC_005_PRE_REGISTRATION.md`  
**Pre-registration commit:** `024e231f3def3e7c058a2a54ffcf74afde3c3dcc`  
**Pre-registration SHA-256:** `1b112802cdee5890e6e652039ac1afbf76908425417848f04f6d9ae86e35a170`  
**G0 commit:** `46880a6dca4ac26d8298babdfeed58f0d65561e1`  
**Run-artifact commit:** `e184cfd6`  
**Date:** 2026-08-23

## Verdict

The hybrid dense-plus-BM25 order improves targeted complete-evidence delivery
at 8,000 characters, but the gain does not repeat strongly enough at 16,000 to
clear the registered two-budget rule. Its disposition is
`TREATMENT_CARRIES_SIGNAL`, not `TREATMENT_WORKS`.

BM25 alone is worse than dense at both primary budgets. Its disposition is
`DENSE_CARRIES_SIGNAL`: the dense direction clears the signal rule, but its
8,000-character p-value does not clear the stricter works family.

Neither treatment is eligible to replace dense. The pre-locked selection rule
therefore chooses the fallback:

> **TC-007 relevance input: `A_DENSE` — `FROZEN_DENSE_FALLBACK_NO_TREATMENT_WORKS`.**

TC-005 consequently does not establish that better relevance ordering is
enough to make a protected 50/50 semantic allocation competitive. It does show
that a hybrid order is worth retaining as successor evidence: it is materially
better at the tighter operating point, but unresolved at the second one.

## Registered contrasts

The primary population is the 704 targeted questions. Gains are treatment-only
complete deliveries; losses are dense-only complete deliveries. The practical
bands are 1 at 8k and 2 at 16k. The works alpha is 0.00125 and the signal alpha
is 0.0125 over the eight directional tests.

| Treatment | Budget | Dense | Treatment | Gains | Losses | Net | Treatment p | Dense p | Registered reading |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| BM25 | 8k | 593 | 557 | 57 | 93 | -36 | 1.000 | .002057 | Dense clears signal, not works |
| BM25 | 16k | 643 | 581 | 36 | 98 | -62 | 1.000 | 4.05e-8 | Dense clears works |
| Hybrid | 8k | 593 | 624 | 58 | 27 | +31 | .000508 | 1.000 | Hybrid clears works |
| Hybrid | 16k | 643 | 657 | 36 | 22 | +14 | .04347 | 1.000 | Direction positive, bar not cleared |

The hybrid contrast is not rounded up from one successful operating point.
The registration requires treatment works at both 8k and 16k. The 16k result
has 58 discordant pairs and a positive net beyond the band, but its exact
one-sided p-value is 0.04347. That yields `TREATMENT_CARRIES_SIGNAL` under the
locked rule.

BM25's dense-direction result at 8k is also not rounded up. Its net is -36, but
the dense one-sided p-value of 0.002057 misses the works threshold of 0.00125.
Together with the 16k result it yields `DENSE_CARRIES_SIGNAL`.

## Full-budget guardrails

The guardrail population is all 868 eligible questions. An adverse dense
direction had to clear both the budget band and the works alpha to reject a
treatment.

| Treatment | Budget | Dense | Treatment | Gains | Losses | Net | Treatment p | Dense p | Guardrail |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| BM25 | 16k | 749 | 630 | 41 | 160 | -119 | 1.000 | 4.18e-18 | Adverse direction decisive |
| BM25 | 32k | 810 | 683 | 18 | 145 | -127 | 1.000 | 3.79e-26 | Adverse direction decisive |
| Hybrid | 16k | 749 | 755 | 45 | 39 | +6 | .2928 | 1.000 | Pass |
| Hybrid | 32k | 810 | 804 | 19 | 25 | -6 | 1.000 | .2257 | Pass |

Hybrid neither depends on a full-budget win nor hides a decisive full-budget
loss: it is +6 at 16k and -6 at 32k, and neither direction clears a guardrail.
BM25's full-budget losses agree with its primary result but do not change its
registered disposition.

## Secondary populations and packing

Breadth is descriptive because TC-005 selects only TC-007's relevance arm; it
does not choose or replace the spread strategy.

| Budget | Dense breadth complete / any | BM25 | Hybrid |
|---|---:|---:|---:|
| 8k | 7 / 39 | 1 / 31 | 8 / 40 |
| 16k | 16 / 41 | 4 / 37 | 13 / 41 |
| 32k | 27 / 41 | 8 / 42 | 18 / 42 |

Hybrid gives one additional complete breadth delivery at 8k, then trails dense
by 3 at 16k and 9 at 32k. Its any-evidence counts are similar or slightly
higher. This does not support binding the spread arm to the hybrid ranker; the
protected spread strategy remains a separate TC-007 component.

Across all eligible questions, complete / any evidence delivery is:

| Budget | Dense | BM25 | Hybrid |
|---|---:|---:|---:|
| 8k | 673 / 748 | 595 / 678 | 701 / 771 |
| 16k | 749 / 801 | 630 / 710 | 755 / 813 |
| 32k | 810 / 840 | 683 / 754 | 804 / 842 |

Mean delivered-candidate counts for dense / BM25 / hybrid are 26.79 / 23.60 /
24.80 at 8k, 54.16 / 46.84 / 49.83 at 16k, and 108.60 / 93.79 / 100.68 at
32k. These counts are diagnostics, not endpoints: fewer candidates can pass
while complete required evidence is worse.

## Preflight interpretation

Preflight found that dense and hybrid had similar evidence-rank summaries while
BM25 had a substantially worse tail: dense/hybrid/BM25 median worst-evidence
ranks were 4/3/5, while their p95 values were 160/165/281. That pattern is
consistent with BM25's losses but is not used as a verdict.

Exact float64 dot-product and Euclidean orders were identical on 871/871
questions. The carried float32 matrix order matched the float64 order on
868/871. Therefore cosine, dot product and Euclidean distance are the same
normalized-vector objective here, but implementation precision can reorder
near-ties. TC-005 tested the carried dense implementation, not an abstract
claim that every numerically equivalent implementation produces identical
payloads.

The question-visible `surface_literal` / `paraphrase` split and all rank
correlations remain descriptive. No diagnostic subgroup selected an arm.

## Integrity and execution

G0 passed before outcome generation and was committed separately. It reproduced
1,742 TC-001 dense payloads, 288 retrieval-bakeoff identity lists and payload
digests, and 2,613 implementation orders. The read-only cache recorded 2,247
hits and zero misses. The leakage audit rejected a planted violation. The full
suite passed with 2,184 tests.

The registered run evaluated all 7,839 arm-budget cells. Two fresh processes
produced identical per-question and diagnostic digests:

- `per_question.csv`: `d0ff30408ffba10afdaac6c49d5c13fb91d7466496bce2ecd0dc565444d45f39`
- `diagnostics.jsonl.gz`: `1da39937d08b5847722879f8fb35889a5290ea9a2fd0e72f2a2cd0d7fde78ca0`

The run made zero embedding calls, zero LLM/generative calls, and had zero
cache misses. Preflight/G0 used 192 allowed embedding calls to replay the prior
anchor and made zero LLM/generative calls. In this programme, "model-free"
means zero LLM/generative calls; embedding calls are reported separately.

Primary artifacts:

- `artifacts/tc005/preflight/tc005_preflight_part1.json`
- `artifacts/tc005/preflight/tc005_preflight_pf4_reachability.json`
- `runs/tc005/g0/g0_reproduction.json`
- `runs/tc005/run/per_question.csv`
- `runs/tc005/run/diagnostics.jsonl.gz`
- `runs/tc005/run/summary.json`
- `runs/tc005/run/verdict.json`
- `runs/tc005/run/determinism.json`

## Claim boundary and next handoff

This is availability, not reader accuracy. It does not show that any delivered
context produces a better answer, that cosine is globally optimal, that 8k or
16k is the right enterprise budget, or that hybrid cannot work on another
corpus. It tests three frozen rank orders over the same LoCoMo candidates,
renderer, greedy packer and character budgets.

TC-007 may now test the intended dual-route architecture with ranked dense
semantic retrieval and protected spread under a fixed 50/50 reservation. It
must not import hybrid on the strength of `CARRIES_SIGNAL`. TC-006 reader
validation remains downstream of TC-007 because its contexts must be frozen
only after the allocation study reports.
