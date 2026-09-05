# DA-018 Frozen-Query Carrier Utility

**Status:** `POST-OUTCOME CROSS-CORPUS EXPLORATION PROTOCOL`
**Date:** August 30, 2026
**Parents:** DA-010 result `ef59203e`; DA-016 result `18820961`; TC-012
**Standing:** evidence-blind allocation study on spent NF-004 and LongMemEval
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Can a frozen-query, payload-level utility order spend scarce protected-link
capacity better than each corpus's strongest existing order without repeating
TC-012's growing-context semantic drift?

DA-018 changes only the order of already exposed linked carriers. Direct
evidence, candidate generation, links, codecs, payload fallback, exact 16k
budget and skip-on-overflow behavior remain fixed.

## 2. Locked Populations and Controls

- **NF-004:** all 1,098 primary questions. Reproduce DA-010's role-pattern
  direct rendering, `PAIR_THEN_TURN` payload and benefit order at 970 complete;
  direct remains 935 and the one-hop ceiling 986. Phrase coding is excluded
  because DA-017 failed its transfer bar.
- **LongMemEval:** all 465 DA-013 questions. Reproduce DA-016 phrase-coded
  direct and linked payloads in temporal order at 188 complete; direct remains
  164 and the one-hop ceiling 250.

The control for each corpus is its strongest supported corpus-specific variant,
not a forced common renderer.

## 3. Frozen Evidence-Blind Signals

For every exposed edge compute before evidence access:

- `payload_cosine`: cosine between the original question and complete neighbor
  pair. NF-004 uses sealed DA-003 `neighbor_query_cosine`; LongMemEval reads the
  already sealed exact-solo vector cache with no misses or new embeddings.
- `seed_confidence = 1 / seed_rank`.
- `payload_cost`: exact current full-pair cost when it fits, otherwise the exact
  frozen fallback-member cost. Cost is recomputed after each admission only for
  role syntax; payload identity and phrase dictionary never change.
- `uncovered_coverage`: IDF-weighted fraction of original-question token weight
  found in the proposed payload but not in direct text or previously admitted
  linked text. IDF, tokenizer and fallback-member choice are inherited from the
  parent corpus implementation.

No answer, evidence identity, question type, outcome, conversation identity,
reader, fitted label, new model, new embedder, query expansion or parameter
sweep may enter a score. Semantic similarity always remains anchored to the
original question.

## 4. Fixed Arms

Each treatment greedily selects the greatest current score among unattempted
edges, applies the parent's exact pair-then-turn action, updates only exact role
cost and lexical coverage after an admission, and continues after overflow.
Ties use seed rank, prior before next, then neighbor identity.

- `CONTROL`: exact DA-010 benefit order on NF-004 and DA-016 temporal order on
  LongMemEval.
- `PAYLOAD_COSINE`: `payload_cosine`.
- `COSINE_PER_CHAR`: `max(payload_cosine, 0) / max(payload_cost, 1)`.
- `MARGINAL_UTILITY`: `max(payload_cosine, 0) * seed_confidence *
  (1 + uncovered_coverage) / max(payload_cost, 1)`.

Scores are literal; there is no normalization, coefficient, threshold, blend,
alternate discount or post-result choice among variants.

## 5. Endpoint and Decision

Primary endpoint is exact complete evidence delivery. Report per corpus and arm:
complete items, gains/losses against control and direct, exact paired tests,
conversation or question-type cells, action counts, exact characters, carrier
ranks, decisive payload costs and causal carrier accounting.

Report `CROSS_CORPUS_CARRIER_UTILITY_SIGNAL` only if one predeclared treatment:

1. exceeds both corpus controls by at least one complete item;
2. has zero losses versus control on both corpora;
3. is nondecreasing in every NF-004 conversation and LongMem question type;
4. preserves every direct evidence identity; and
5. gives exact admitted-carrier accounting for every gain.

If different treatments win by corpus, any gain has a loss, or only one corpus
improves, report `NO_CROSS_CORPUS_CARRIER_UTILITY_SIGNAL`. Also report each
arm's descriptive corpus-specific result; do not select a new deployed winner.

## 6. Preflight

- **PF1 Inputs:** seal and reproduce every DA-010, DA-016 and source artifact,
  population, edge, direct-order, codec and allocation hash.
- **PF2 Identity:** test frozen query cosine, seed confidence, exact dynamic
  cost, uncovered-token updates, ties, duplicates, pair fallback and overflow.
- **PF3 Ordering:** commit this protocol, then commit all blind scores and
  allocations before opening evidence labels.
- **PF4 Reachability:** require all treatments to differ from control on both
  corpora, positive and zero lexical marginals, cost changes after admissions,
  and pair/turn/skip actions.
- **PF5 Keys:** preserve every corpus, question, edge, seed, neighbor, member,
  phrase, action and score key; reject missing or duplicate joins.
- **PF6 Reproduction:** require NF-004 935/970/986 and LongMem 164/188/250,
  byte-identical control allocation, exact codec decode and no direct drift.
- **PF7 Determinism:** require byte-identical blind and opened replay.
- **PF8 Length:** process all 1,098 and 465 questions and every eligible exposed
  edge; no outcome-based filtering.
- **PF9 Surrogate audit:** evidence availability is not answer use; both corpora
  are spent and a positive result is not fresh validation.
- **PF10 Live boundary:** no reader, latency, adoption or production claim.

Stop on any hash/cache miss, fresh embedding/model call, query-vector mutation,
codec drift, direct loss, undercharge, nondeterminism, incomplete population or
unexplained gain/loss. Commit protocol and blind allocation separately from the
result. Do not tune after outcomes open.

