# TC-011 Research Memory Update

TC-011 is complete at `REGISTERED-OFFLINE` with family disposition
`NO_CANDIDATE`. Frozen CC80 filled the semantic half first; four treatments
filled protected spread at 16k/32k: CC80-weighted residual log determinant,
deterministic aspect saturation, query-anchored growing-centroid chaining and
pure chaining. The chain constants were carried from E006 (`W_Q=.3`,
`rho=.5`); no arm, coefficient or share was swept.

Full CC80 combined/targeted/breadth is 771/666/17 at 16k and 819/689/24 at
32k. LOGDET is 726/636/8 and 797/675/22. ASPECT, the least harmful, is
749/645/15 and 810/680/23. Anchored chain is 717/627/9 and 780/669/19; pure
chain is 717/628/10 and 778/670/18. Every arm is `NO_POSITIVE_SIGNAL`.

Mechanism behavior is differentiated. LOGDET admits median 44/75 spread items;
ASPECT 23/47; anchored chain 31/57; pure chain 32/57. Pure chain reaches median
CC80 ranks 126/159 against anchored 91/129. Their sets differ on 871/871 traces
at both budgets but both lose badly. Generic association is coherence, not
missing-evidence coverage. ASPECT comes closest but at 32k still has breadth
4 gains/5 losses, identities 10/11, and targeted 5/14.

Preflight reproduced 3,484 parent payloads, checked 316,786 state updates, and
used 2,236 cache hits with zero misses and zero embedding/LLM calls. Canonical
facet traversal was required for fresh-process determinism; two independent
replays match selection SHA `9f4ae9ab...`. Full CC80 remains fallback. No
reader, tuning, deployment or adoption is authorized.
The final repository suite is 2,251 passed.
