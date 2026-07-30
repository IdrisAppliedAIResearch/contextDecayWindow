# DR-001 Downstream Re-Derivation

**Status:** **PASS**  
**Embedding SHA-256:** `06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439`  
**Generative calls:** `0`

## Decisions

- `B_ltm`: KEEP at 32,000 characters. The existing allocation is not tuned from post-fix outcomes.
- N cap: KEEP at 32. The Q4 turn-55 episode remains rank 27 and inside the cap; post-fix Q4 packing was not opened.
- N-first packing: FLAG ONLY for AS-001.
- Per-domain floor: KEEP at `k_min = 1`; every topic retains its floor at the locked budget.
- Containment dedup: KEEP; source-episode identity remains the authority and the synthetic invariant passes.

## Locked Budget

| Corpus | Turn | Records | Serialized chars | Content chars | Floor protected |
|---|---:|---:|---:|---:|---|
| Study 007 | 120 | 8 | 31267 | 30670 | PASS |
| Study 007 | 121 | 9 | 31472 | 30806 | PASS |
| Study 010 | 999 | 69 | 31993 | 27134 | PASS |
| Study 010 | 1000 | 71 | 31796 | 26797 | PASS |

The complete 16k-64k frontier, selected identities, fact coverage, query hashes, and vector hashes are in `rederivation.json`.
