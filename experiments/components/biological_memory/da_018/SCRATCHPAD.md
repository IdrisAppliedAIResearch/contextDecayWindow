# DA-018 Scratchpad

## 2026-08-30 - Registration

- User approved frozen-query linked-carrier rescoring using only the strongest
  corpus-specific parent variant.
- TC-012 is the relevant prior recomputation study. Its growing-context cue was
  harmful, so DA-018 freezes semantic similarity to the original question and
  updates only exact payload cost and uncovered lexical coverage.
- NF-004 control is DA-010 at 970. LongMem control is DA-016 at 188. DA-017
  phrase coding is not used on NF-004 because it missed its transfer bar.
- No model or embedding calls are authorized. LongMem may read only its sealed
  exact-solo cache to recover pre-existing query and neighbor vectors; all hits
  and misses must be reported.
- Next: commit protocol, implement and test mechanical scoring/allocation, then
  commit blind artifacts before opening evidence outcomes.

## 2026-08-30 - Blind allocation

- Protocol committed at `85d3046f`; blind implementation and allocations at
  `013a0304`.
- Preflight passed all 1,098 NF-004 and 465 LongMem questions. Allocation SHA is
  `3928700040ffe7931b5865414867b149595db67a431f32dc97a72d4e9f7ffcdb`.
- Deterministic replay is byte-identical. LongMem made 7,866 sealed-cache hits,
  zero misses, zero embedding calls and zero model calls.
- Every arm exercised pair, singleton and skip behavior on both corpora.

## 2026-08-30 - Outcome

- `NO_CROSS_CORPUS_CARRIER_UTILITY_SIGNAL`.
- NF control/cosine/cosine-per-char/marginal: 970/952/944/960. Marginal trades
  1 gain for 11 losses and is nonpositive in all six conversations.
- LongMem control/cosine/cosine-per-char/marginal: 188/179/189/191. Marginal is
  6 gains/3 losses, p=.508; cost ratio is 12/11.
- Frozen-query similarity avoids TC-012 drift but still confuses relevance and
  completion value. Global rescoring destroys useful parent-order priors.
- Result replay is byte-identical; outcome SHA is
  `daceb9e0204524705fab787447ae8a72cced0d68db3158f766e770989548bcfd`.
- No tuning, reader, adoption or fresh-validation claim.

