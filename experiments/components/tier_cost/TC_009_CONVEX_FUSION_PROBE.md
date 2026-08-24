# TC-009 normalized convex-fusion probe

**Type:** descriptive feasibility diagnostic; not TC-010  
**Status:** design lock before implementation  
**Date:** 2026-08-23  
**Parent:** TC-005 relevance efficiency and TC-009 post-close probes

## 1. Question and boundary

Test whether preserving score distances with a fixed normalized convex
combination of dense cosine and BM25 improves 16k/32k complete-evidence
delivery over dense and TC-005's rank-only RRF hybrid.

This is motivated by scholarly hybrid-retrieval work, but it is an offline
availability diagnostic on used LoCoMo development data. It cannot select or
ship an architecture, create TC-010, authorize reader answers, demonstrate
unseen-corpus transfer, or establish that 80/20 is optimal.

## 2. Label-blind exploration

Executed before this lock on the committed TC-009 blind manifest using the
sealed LoCoMo vector cache and TC-005's unchanged BM25 implementation:

- 871 questions; zero cache misses;
- dense score ranges are nonzero on 871/871, with min/median/max
  `.298346/.465743/.654688`;
- BM25 score ranges are nonzero on 871/871, with min/median/max
  `2.465141/11.611046/42.357531`;
- the 80/20 order differs from dense and RRF on 871/871 questions;
- selected sets differ from dense on 869/871 questions at 16k and 871/871 at
  32k, and from RRF on 871/871 at both budgets; and
- the top 20 have median 17 position-wise changes versus dense.

The treatment and both comparison states can therefore exist. The magnitude
also shows that 20% lexical weight is not a minor tie-break.

## 3. Frozen arms

All arms rank the same 1,365 complete adjacent-turn pairs and use the same
renderer, skip-on-overflow packer, and exact 16,000/32,000 character budgets.

- `A_DENSE`: accepted TC-005 dense cosine order.
- `A_RRF`: accepted TC-005 one-based RRF order,
  `1/(60+dense_rank) + 1/(60+bm25_rank)`.
- `A_CC80`: for each query and candidate store, independently min-max normalize
  dense and BM25 scores to `[0,1]`, then rank descending
  `0.8*dense_normalized + 0.2*bm25_normalized`.

For score vector `x`, normalization is `(x-min(x))/(max(x)-min(x))`. A zero
range is an instrument failure, not a fallback. Ties use
`(session_order, pair_order, candidate_identity)`. There is no coefficient
sweep, alternate normalization, clipping, threshold, query-adaptive weight,
reranker, candidate change, or span packing.

## 4. Population and endpoints

Run all 871 unique questions. Formal reads use the 868 eligible questions and
the frozen targeted (704), breadth (44), and other (120) populations.

At each budget, report `A_CC80` versus dense and RRF for:

- combined, targeted, breadth, and other complete-evidence gains/losses;
- breadth required-identity gains/losses and net;
- all four conversation-level combined complete nets;
- selected-set symmetric differences, evidence ranks, payload characters and
  selected counts; and
- score-range and dense/BM25 contribution distributions.

## 5. Frozen positive-feedback rule

`A_CC80` is `DESCRIPTIVE_POSITIVE_SIGNAL` only if all hold at **both** 16k and
32k against dense:

1. combined complete-evidence gains exceed losses;
2. targeted complete-evidence gains are at least losses;
3. breadth required-identity net is nonnegative, and it is positive at one or
   both budgets;
4. breadth complete-evidence gains are at least losses; and
5. every conversation's combined complete net is nonnegative, with at least
   two conversations positive at each budget.

Otherwise disposition is `NO_POSITIVE_SIGNAL`. RRF contrasts are descriptive
and cannot rescue a dense failure. No p-value, tuning, selection, or reader
claim follows either disposition.

## 6. Preflight — before label join

Part 1 must reproduce §2's full distributions and record score/order/selection
digests before any evidence import.

- **PF1:** hash/count corpus, blind manifest, vector cache, accepted TC-005
  run, sealed selection artifact, and labels.
- **PF2:** planted score vectors prove independent min-max normalization and
  exact 80/20 fusion; real distributions prove it is not a tie-break.
- **PF3:** all three orders and packed selections freeze before the evidence
  module or per-question labels can import; planted early access fails.
- **PF4:** synthetic paired rows demonstrate every clause and both dispositions
  reachable.
- **PF5:** blind question keys and pair content identities only.
- **PF6:** dense and RRF reproduce accepted TC-005 selected-id and payload
  digests on all 871 questions at 16k/32k.
- **PF7:** not applicable; no feedback state.
- **PF8:** four conversations can expose reversal but not new-corpus transfer.
- **PF9:** query-wise min-max can amplify weak BM25 differences, 80/20 can
  displace strong dense evidence, and availability can pass without reader
  use; report residuals directly.
- **PF10:** availability only; a reader test requires separate registration.

Preflight may read sealed cached vectors and must have zero misses and zero
embedding or LLM/generative calls. Outcome loads sealed selections with zero
cache, embedding, BM25, or LLM/generative calls. Use one process, explicit
UTF-8, and deterministic serialization.

## 7. Execution order

1. Commit this design alone.
2. Implement normalized fusion, selection freeze, measurement, and tests.
3. Commit passing PF1-PF10 and sealed selections before labels.
4. Run the frozen outcome, report, update repository memory, and open a stacked
   diagnostic PR. Do not create TC-010 or run answers.
