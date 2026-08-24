# TC-011 four protected-spread mechanisms — report

**Status:** `NO_CANDIDATE`; registered lightweight offline availability probe  
**Design commit:** `0fd774f6`  
**Registration SHA-256:** `9fa34962dca6b2600b098bccdeb4be4a7b65dd9bee20a7f6c1102fa09f62eead`  
**Preflight commit:** `4c5f70e1`  
**Outcome commit:** `aeda3eb1`  
**Date:** 2026-08-24

## Result

None of the four protected-spread objectives improves full-budget CC80. ASPECT
is the least harmful treatment, but it still loses combined, targeted and
breadth completeness at both budgets. Both chained routes are materially worse;
retaining the query anchor does not make chaining safe.

| Budget | Arm | Combined | Targeted | Breadth | Combined gains/losses vs CC80 |
|---:|---|---:|---:|---:|---:|
| 16k | Full CC80 | **771** | **666** | **17** | — |
| 16k | Prior CC80+A3 | 757 | 653 | 14 | — |
| 16k | LOGDET | 726 | 636 | 8 | 5 / 50 |
| 16k | ASPECT | 749 | 645 | 15 | 11 / 33 |
| 16k | Anchored chain | 717 | 627 | 9 | 3 / 57 |
| 16k | Pure chain | 717 | 628 | 10 | 5 / 59 |
| 32k | Full CC80 | **819** | **689** | **24** | — |
| 32k | Prior CC80+A3 | 818 | 686 | **27** | — |
| 32k | LOGDET | 797 | 675 | 22 | 9 / 31 |
| 32k | ASPECT | 810 | 680 | 23 | 15 / 24 |
| 32k | Anchored chain | 780 | 669 | 19 | 0 / 39 |
| 32k | Pure chain | 778 | 670 | 18 | 1 / 42 |

Every arm is `NO_POSITIVE_SIGNAL`; the family disposition is `NO_CANDIDATE`.
Full CC80 remains the fallback. The prior A3 control also remains better than
every new treatment on combined completeness at both budgets.

## What the four arms reveal

LOGDET admits the most items—median 44/75 spread steps at 16k/32k—and reaches
median CC80 rank 109/141. Geometric nonredundancy is active, but it exchanges
high-ranked evidence for embedding-space volume. Breadth completeness falls
17→8 and 24→22; the mathematical diversity objective is not evidence breadth.

ASPECT admits fewer, facet-rich candidates—median 23/47 steps—and is the closest
arm. At 32k it makes 4 breadth gains and 5 losses, with 10 required identities
gained and 11 lost. It also gains one “other” completion at each budget, but
targeted completeness loses 21 and 9. Deterministic entity/event/date/number/
noun/relation coverage is more conservative than geometry or chaining, yet it
is not sufficiently query-conditioned to pay for a protected half.

The two chains are distinct on every one of 871 question contexts at both
budgets. Pure chaining reaches deeper ranks than anchored chaining: median
126 versus 91 at 16k and 159 versus 129 at 32k. Their final selected sets have
median Jaccard overlap `.618/.679`, so the anchor meaningfully changes content.
It does not improve the trade: anchored/pure combined nets are -54/-54 at 16k
and -39/-41 at 32k. At 32k anchored chaining produces no complete gains in any
population and loses 39 questions. Growing similarity follows coherent
associations, but coherence is not missing-evidence coverage.

## Integrity notes

Preflight froze 871 contexts at two budgets for four treatments before labels
opened, reproduced 3,484 CC80/CC80+A3 identities and payload digests, and checked
316,786 recurrence updates. It used 2,236 cache hits with zero misses and made
zero embedding or LLM/generative calls. The outcome made zero ranking or model
calls.

Preflight found two implementation-check issues before outcome access:

1. The first gate incorrectly required every recurrence to stop on character
   capacity even though the registration also permits zero positive marginal.
   The corrected gate accepts exactly those two absorbing states. ASPECT stops
   on zero marginal in 17/29 traces at 16k/32k; LOGDET does so in 2/3; both
   chains always stop on capacity.
2. Unordered facet-set iteration changed selection bytes across fresh Python
   processes. Canonical facet traversal fixed it. Two fresh-process full
   replays then produced the identical selection SHA-256
   `9f4ae9abb57dfc76aecb3afdfcb62029056c10c6a412e42914d0c2294c2c9a0a`.

Neither correction changed a registered mechanism, parameter, endpoint or bar,
and labels remained sealed until both checks passed.

## Boundary

This closes these four exact objectives behind a fixed 50/50 allowance on the
used LoCoMo development conversations. It does not show that all protected
spread is harmful, that chaining cannot help another task, or that ASPECT has no
use at another share. It does show that generic geometric novelty, generic
structured coverage and growing semantic association do not make a protected
half pay for itself here. Availability is not reader use; no answer run,
coefficient/share tuning, deployment or adoption is authorized.

The final repository suite is 2,251 passed.
