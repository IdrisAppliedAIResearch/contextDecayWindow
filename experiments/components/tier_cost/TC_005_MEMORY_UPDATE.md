# TC-005 Research Memory Update

TC-005 is complete at `REGISTERED-OFFLINE`. It compared carried dense cosine,
BM25, and dense-plus-BM25 reciprocal-rank fusion over the same 1,365 LoCoMo
adjacent-turn-pair candidates. Primary budgets were 8k and 16k characters,
which are the relevance arm's half-shares inside TC-007's 16k and 32k total
contexts. The run evaluated 871 questions, 3 arms, and 3 unique budgets.

Hybrid carries a real but operating-point-specific signal. On 704 targeted
questions it changes complete evidence from dense's 593 to 624 at 8k: 58 gains,
27 losses, net +31, p=.000508 against band 1. At 16k it changes 643 to 657: 36
gains, 22 losses, net +14, p=.0435 against band 2. Because the frozen rule
requires `WORKS` at both budgets, the disposition is
`TREATMENT_CARRIES_SIGNAL`, not `TREATMENT_WORKS`.

BM25 alone is worse: 557 at 8k and 581 at 16k, nets -36 and -62 against dense.
Dense's 8k one-sided p=.002057 clears the signal alpha but misses the works
alpha; its 16k p=4.05e-8 clears works. The registered combined disposition is
`DENSE_CARRIES_SIGNAL`.

Hybrid's full-budget eligible guardrails do not fire: it is +6 complete
deliveries at 16k and -6 at 32k, with adverse p=.2257 at 32k. BM25 is -119 and
-127 there. Descriptive hybrid breadth complete delivery is 8/13/18 at
8k/16k/32k versus dense 7/16/27. This does not select the spread strategy.

The frozen selection rule chooses `A_DENSE` for TC-007 because neither
treatment works at both primary budgets. `CARRIES_SIGNAL` cannot be promoted by
interpretation. TC-007's intended next comparison is therefore full-budget
dense relevance versus a dual route with ranked dense relevance and protected
spread, 50/50 floors, and unused spread budget returned to relevance. TC-005
does not start or pre-register TC-007.

Preflight's numerical limit persists: float64 dot and Euclidean orders agree on
871/871 questions, but the carried float32 matrix order agrees on 868/871.
Normalized cosine/dot/Euclidean are the same exact-arithmetic objective; numeric
precision can still move near-ties.

G0 reproduced 1,742 TC-001 payloads, 288 retrieval-bakeoff identity/payload
rows, and 2,613 implementation orders. Two fresh run processes reproduced all
7,839 arm-budget cells exactly. The run had 2,247 cache hits, zero misses, zero
embedding calls, and zero LLM/generative calls. G0 made 192 allowed embedding
calls for the prior replay and zero LLM/generative calls. In this programme,
model-free means zero LLM/generative calls; embeddings are reported separately.

This is evidence availability only. It establishes no reader benefit, optimal
budget, enterprise scaling rule, or global ranking optimum. TC-006 reader
validation remains after TC-007, using contexts frozen only after TC-007
reports.
