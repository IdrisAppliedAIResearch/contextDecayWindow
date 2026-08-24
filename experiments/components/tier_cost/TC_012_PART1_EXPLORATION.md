# TC-012 Preflight Part 1 — dynamic ASPECT cues

**Status:** complete; label-blind exploration only  
**Date:** 2026-08-24  
**Artifact:** `artifacts/tc012/part1_exploration.json`  
**Artifact SHA-256:** `a87edd6d8f6f39acd58c5a32946b1922fb92b89887b56e1b76bef94493a40289`

## Boundary and identities

All 871 blind questions ran at 16,000 and 32,000 characters with frozen CC80,
ASPECT facets and the 50/50 allocator. The exploration used 2,236 cache hits,
zero misses, zero new embedding calls and zero LLM/generative calls.

`DYNAMIC_PROMPT` recomputes dense cosine after every admitted item against
`normalize(.3*q + .7*c_t)`, where `c_t` is the growing selected-context
centroid under TC-011's carried `.5/.5` recurrence. It then rebuilds CC80 as
`.8*dynamic_dense_normalized + .2*frozen_BM25_normalized` and recomputes ASPECT
coverage under those scores.

`RESIDUAL_ASPECT` extracts the question's registered ASPECT facets, removes
those already represented by selected candidates, and forms an IDF-weighted
centroid of remaining candidates carrying an uncovered question facet. Its cue
is `.3*q + .7*residual_centroid`; if no candidate binds an uncovered facet, it
falls back exactly to `q`. CC80 and ASPECT are then recomputed as above.

## Distributions

| Budget | Arm | Median steps | Median selected | Median spread CC80 rank | Median cue/query cosine |
|---:|---|---:|---:|---:|---:|
| 16k | Dynamic prompt | 22 | 48 | 128 | .744 |
| 16k | Residual aspect | 23 | 49 | 78 | 1.000 |
| 32k | Dynamic prompt | 44 | 97 | 170 | .729 |
| 32k | Residual aspect | 47 | 100 | 126 | 1.000 |

Dynamic prompt differs from static ASPECT and residual ASPECT on 871/871
selected sets at both budgets. It is an active growing-cue mechanism.

Residual ASPECT differs from static ASPECT on only 146/871 sets at 16k and
71/871 at 32k. Its median fallback count equals its median step count at 16k
and is 46 fallbacks over 47 steps at 32k. The exact-facet residual cue is
therefore usually unavailable: initial CC80 already covers the match or no
remaining candidate shares the normalized question facet. The arm is not fully
inert, but a broad result primarily measures static ASPECT.

Every arm has a nonempty spread on every trace. Dynamic prompt stops on capacity
842/838 times and zero marginal 29/33 times at 16k/32k. Residual ASPECT stops on
capacity 848/845 and zero marginal 23/26. Both are absorbing states because
capacity only decreases and a zero-marginal state returns slack without further
updates.

## Design consequence

The outcome may test DYNAMIC_PROMPT broadly. RESIDUAL_ASPECT must be reported
with its active-set count and may support only a narrow statement about this
exact lexical facet binder. It cannot adjudicate the broader idea of
question-obligation-aware dynamic retrieval. No coefficient, parser, facet,
budget or share sweep is justified.
