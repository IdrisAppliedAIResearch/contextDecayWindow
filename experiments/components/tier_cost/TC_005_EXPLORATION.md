# TC-005 Preflight Exploration — carried relevance rankers

**Status:** `PREFLIGHT PART 1 + PF4 COMPLETE — NO LABELLED ARM OUTCOME OPENED`  
**Date:** August 23, 2026  
**Design commit:** `7be4d7b7`  
**Part 1 artifact:** `tc005_preflight_part1.json`, SHA-256 `2687d48812d8862f7c0ff2ebe5abe6bd8011f136deb38efaacf34958296ba584`  
**PF4 artifact:** `tc005_preflight_pf4_reachability.json`, SHA-256 `c44a96b52ec796f06a9507b31b987d6bb1f9d17976f8134823a485d707c67b4d`  

## 1. What the three names actually do

- **Dense** orders all adjacent-turn pairs by the carried normalized float32
  query/candidate matrix product, descending, with conversation order as the
  stable tie-break.
- **BM25** tokenizes the same pair text with the carried Unicode-casefold
  tokenizer, scores with `k1=1.2, b=0.75`, orders descending, and uses the same
  conversation tie-break. There is no threshold or pool cut.
- **Hybrid** converts the complete dense and BM25 orders to one-based ranks,
  adds `1/(60+dense_rank) + 1/(60+bm25_rank)`, orders descending, and uses the
  same conversation tie-break. It is RRF, not score averaging.

The rankers are pure functions of the frozen query and candidate store. There
is no feedback state and therefore no absorbing state across questions.

## 2. Population and transfer anchors

The four LoCoMo development conversations contain 1,365 adjacent-turn pairs
and 871 unique questions. The prospective TC-007 split resolves to 704 targeted
questions, 44 breadth questions, 120 other eligible questions, and 3 ineligible
questions. The question-visible diagnostic contains 169 `surface_literal` and
702 `paraphrase` questions.

Both transfer anchors passed:

- TC-001 dense reproduced 1,742 question-budget payloads at 16k/32k by exact
  delivered count and serialized cost; the replay payload digest is
  `f540ae0b4292a61d9faa03e630ca82817e84601a7ff37306f5c1fd5c2c51b11c`.
- The unmodified retrieval-bakeoff M2/M3/M4 code reproduced all 288 committed
  selected-identity lists and payload SHA-256 values. Its full ranking digest
  is `cf7dcc61a68c81b834d80cb22774afaea0ef8974eba51e4be626f70af3c9eec8`.

The prior replay used 192 embedding calls. The LoCoMo cache had 2,247 hits and
zero misses. There were zero LLM/generative calls; this is model-free under the
programme's definition.

## 3. Distribution, not a pooled winner

Evidence rank distributions were measured without computing complete-delivery
contrasts:

| Ranker | p50 evidence rank | p75 | p95 | mean |
|---|---:|---:|---:|---:|
| Dense | 4 | 23 | 160 | 27.81 |
| BM25 | 5 | 73 | 281 | 55.31 |
| Hybrid | 3 | 20 | 165 | 27.01 |

Dense and BM25 genuinely disagree: their per-question Spearman correlation has
median 0.118, p05 -0.079, p95 0.387, and minimum -0.270. Hybrid sits between
them: median correlation 0.705 with dense and 0.714 with BM25.

All three packers bind at every 8k, 16k, and 32k question. Median delivered
candidate counts at 8k/16k/32k are dense 26/54/111, BM25 24/47/94, and hybrid
25/49/101. Similar character use therefore does not imply equal information or
equal candidate count.

## 4. Degenerate and precision states

On real traces there are no all-zero BM25 queries, no three-arm complete-order
agreements, no everything-fits cases, and no individually oversized candidate
at the three budgets. Dense has exact score ties on 5/871 queries; RRF score
ties occur on 410/871. The common conversation tie-break is therefore active,
especially for RRF. Synthetic controls exercise all-zero BM25, dense and RRF
ties, everything-fits, and oversized-skip behavior.

The original design's metric-alias sentence needed narrowing. Float64 dot and
Euclidean orders agree on 871/871 queries, with maximum algebraic relation
error `2.45e-15`. The carried float32 matrix-product order agrees with that
float64 order on 868/871. The three residual differences are numerical
near-ties. They do not create a distinct retrieval objective, but they do mean
"byte-identical under any implementation" would have been false.

## 5. PF4 and the instrument band

Dense-only ±0.5% and ±1% budget shams on the targeted complete-evidence endpoint
produce maximum absolute net movement of 1 at 8k, 2 at 16k, and 0 at 32k. These
are the budget-specific instrument bands available to the registration.

PF4 never reads an evidence label when comparing arms. At every budget and for
both BM25 and hybrid, all 704 targeted questions contain at least one candidate
delivered exclusively by the treatment and at least one delivered exclusively
by dense. The same is true on all 868 combined eligible questions. Thus either
direction, the practical band, the statistical bar, the dense fallback, and a
full-budget guardrail failure are mechanically reachable.

## 6. Mandatory checklist

| Check | Evidence |
|---|---|
| PF1 | Dataset, 1,365 pairs, 871 questions, cache, manifests, prior result file, renderer/packer, and BM25/RRF sources are counted and SHA-bound in Part 1 `inputs`. |
| PF2 | Sections 1, 3, and 4; 871 real traces, formula constants, tie behavior, and metric residuals are executed, not inferred from names. |
| PF3 | Only exploration/PF4 entry points exist before registration. The registered study must refuse outcome generation until a committed passing G0 artifact exists. |
| PF4 | Both directional candidate-exclusive populations exist at all budgets; the four prospective decision branches and all budget bands are reachable. |
| PF5 | Candidate and question content hashes are the comparison keys; no path, timestamp, or generated identifier enters a comparison. |
| PF6 | TC-001 1,742-payload replay and bakeoff 288-row selected-identity/payload replay both pass. |
| PF7 | No feedback; repeated calls are pure. Synthetic constant/tie states and real nonconstant orders are recorded. |
| PF8 | The full 871-question offline population is used. It cannot establish reader use, unseen-corpus transfer, adaptive budgets, or larger-store behavior. |
| PF9 | Rank, score, overlap, candidate count, characters, and any-evidence can all improve while complete required evidence does not. None is allowed to select the arm. |
| PF10 | This study can freeze an input order for TC-007 only. Reader benefit requires TC-006 after the dual-route contexts are frozen. |

## 7. Design consequences before registration

The three objective arms remain dense, BM25, and RRF. Numerical precision
variants are excluded. The primary population is now fixed at 704 targeted
questions, the combined guardrail population at 868, and the diagnostic breadth
population at 44. The `surface_literal` regex is frozen as a descriptive split,
not a selection endpoint. The registration may use only complete required
evidence to select a ranker and must use the observed 8k/16k/32k bands without
relaxation.
