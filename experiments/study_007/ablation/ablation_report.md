# Study 007 — 35-Turn Ablation and GO/NO-GO (S7_006)

**Status:** GO
**Tasks:** S7-T-018 (ablation), S7-T-019 (authorization)
**Run:** `experiments/study_007/ablation/runs/study_007_ablation_001/condition_c`
**Locked parameters:** `B_ltm = 32,000`, `k_min = 1`
**Duration:** 10m 09s, 35 turns

---

## Checks

| Check | Expected | Actual | Pass |
|---|---|---|---|
| Speed (single-slot) | > 30 tok/s | min **35.8**, median 43.0 | ✓ |
| Determinism | prefix replay identical | 10/10 within study, 10/10 vs Study 006 (S7-T-005) | ✓ |
| Script hash post-decode | matches pre-registered | `d8ba73fd…` asserted at startup | ✓ |
| Formation unchanged | spans, salience, C = 50 diff-review clean | empty diff vs `origin/main` on all formation files | ✓ |
| First dream pass | fires at ~31; records offset-verbatim | fired at **31**; 50 records, **0** offset failures | ✓ |
| Extractive assertion | zero inference calls in dreaming | **0** | ✓ |
| Budget respected | `ltm_chars_used` ≤ 32,000 every turn | max **31,382**; 0 turns over | ✓ |
| Single-topic floor | degenerate case handled | topics = 1, floor = 1, no error | ✓ |
| Containment dedup | drops logged; refill preserves floor | 5 drops/turn logged; floor intact | ✓ |
| Floor protection | no floor selection evicted | 4/4 turns: logged floor count == floor entries in block | ✓ |
| `retrieval_budget.csv` | populated, split sums correctly | 35 rows; per-domain split sums to `ltm_chars_used` on every row | ✓ |
| STM untouched | N + K path diff-review clean | zero diff hits on `_k_retrieve`, `_n_retrieve`, `_score_stm_rows`, `K_SIMILARITY_THRESHOLD`, `N_RETRIEVAL_CAP` | ✓ |
| Context ceiling | peak well under 80% of ctx-size | **15,573 tokens = 31.0%** of 50,176 | ✓ |

## Formation is bit-for-bit the Study 006 policy

The dream event at turn 31 reproduces Study 006's figures exactly:

| Measure | Study 007 ablation | Study 006 full run, event 31 |
|---|---:|---:|
| Segmenter | `spacy:en_core_web_sm:3.8.0:sentencizer` | same |
| Spans evaluated | 798 | 798 |
| Spans eligible | 320 | 320 |
| Salience floor | 0.15 | 0.15 |
| Records written | 50 | 50 |
| Offset-verbatim failures | 0 | 0 |
| Non-content records | 0 | 0 |

Formation is carried, not reimplemented, and this is the evidence.

## Retrieval budget behaviour

LTM is empty until the first dream pass, so turns 1–31 log zero-valued rows —
present, not missing, which is what makes "the budget never bound early" a
checkable claim rather than an absence.

| Turn | Topics | Floor | Fill | Containment drops | Chars used | Utilization |
|---:|---:|---:|---:|---:|---:|---:|
| 32 | 1 | 1 | 6 | 5 | 28,750 | 89.8% |
| 33 | 1 | 1 | 7 | 5 | 31,382 | 98.1% |
| 34 | 1 | 1 | 6 | 5 | 28,944 | 90.5% |
| 35 | 1 | 1 | 7 | 5 | 31,382 | 98.1% |

Three things worth naming:

**The degenerate single-topic case behaves.** Only `civil_engineering` exists in
distilled LTM at turn 32, so the floor admits its single top span and the fill
takes the rest. No division by topic count, no starvation, no error — the case
the replay gate could not reach.

**Containment dedup is doing real work.** Five LTM entries per turn are dropped
because their source episode is already in the STM block. At this point in the
script the store is small and recent, so overlap is at its maximum; the drops
are exactly the duplication Amendment 001 predicted would be large, since the
read path renders whole episodes rather than spans.

**Utilization is high but the budget is never breached.** 89.8–98.1% means the
budget is the binding constraint, which is the point — it is a budget, not a
ceiling that never applies.

## Context

Peak 15,573 tokens against a 50,176 capacity — 31.0%, well under the 80% alert
and under the replay gate's 60% projection limit. Study 006's treatment peaked
at 12,169 over the full 121 turns; this is 35 turns with a deliberately larger
LTM block, and the full run is projected at 13,741 by the replay.

## Decision

```
DECISION: GO — all applicable checks passed. The retrieval replay gate
(four-domain coverage at Q11 and Q14) and the targeted-retrieval fixture both
passed at the locked B_ltm = 32,000 / k_min = 1 before this ablation ran.
Formation reproduces Study 006 exactly. Control + full v7 run authorized.
```

Two things are carried into the run as pre-registered predictions rather than
open questions, both recorded before any full run is spent:

1. **A Bar 1 pass will be attributable to the information-expressed budget, not
   to the diversity floor** (Amendment 002 §6). At `B_ltm = 32,000`, `k_min = 0`
   also reaches four-domain coverage.
2. **Q5 and Q8 cannot reach full credit**, because `art_pigment` and
   `marine_photophores` are unformed and formation is unchanged. A sub-13
   Q1–Q13 is a formation ceiling, not a retrieval failure.
