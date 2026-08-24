# TC-010 relevance-qualified bottom spread

**Type:** registered offline evidence-availability study  
**Status:** pre-registration; not yet runnable  
**Date:** 2026-08-23  
**Authorization:** user locked CC80 semantic retrieval, the 50/50 allocator,
and the proposed relevance-qualified least-redundant spread route

## 1. Question and boundary

Can a 50/50 route preserve frozen CC80's direct retrieval while improving
complete breadth by spending the spread allowance on the least-redundant
candidates inside a relevance-qualified pool?

This tests availability on already-used LoCoMo development conversations. It
cannot establish answer accuracy, unseen-corpus transfer, production adoption,
an optimal pool fraction, or an optimal share.

## 2. Frozen inputs and population

- Corpus SHA-256:
  `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`.
- Conversations: `conv-41`, `conv-42`, `conv-47`, `conv-48`.
- Same 1,365 adjacent-turn candidates, text, carried float32 vectors, renderer,
  containment deduplication and skip-on-overflow packing.
- 871 unique questions; 868 eligible, comprising 704 targeted, 44 breadth and
  120 other questions under TC-007's frozen definitions.
- Budgets: 16,000 and 32,000 serialized characters.
- Stable comparison keys are question content identity and candidate content
  identity. Generated ids, timestamps and paths are forbidden.

## 3. Locked semantic route

`CC80` is the only relevance method: query-wise min-max normalize carried dense
cosine and BM25 candidate scores, then rank by
`0.8*dense_normalized + 0.2*BM25_normalized`, with the frozen deterministic
tie-break. It ranks the complete store. There is no coefficient sweep, dense
fallback inside a treatment, query expansion, reranker or new embedder.

The explicit user authorization freezes CC80 for this successor study. It does
not revise TC-005 or turn either earlier convex probe into a positive result.

## 4. Locked 50/50 allocator

For total budget `B`, initial CC80 and spread each receive solo allowance
`H=B/2`.

1. Initial CC80 admits complete candidates fitting `H`.
2. Spread excludes identities actually admitted by initial CC80 and admits
   complete candidates fitting its solo `H`.
3. Merge in phase order, serialize once and containment-deduplicate by stable
   candidate identity.
4. CC80 resumes its unchanged order and fills actual remaining capacity.
5. Unused spread allowance and wrapper savings therefore return only to CC80.
6. No identity serializes twice; every admission is attributed to initial
   relevance, protected spread or returned relevance.
7. Exact serialized length may not exceed `B`; overflow candidates are skipped
   and never truncated.

“50/50” is two maximum solo allowances, not guaranteed final character or
candidate composition.

## 5. Spread routes and arms

`A_CC80_FULL` is the binding control and gives CC80 all `B` characters.

`A_QUALIFIED_BOTTOM` is the treatment:

1. The qualified pool is the first `ceil(0.25 * candidate_count)` candidates
   in the question's complete CC80 order.
2. Remove candidates admitted by initial CC80.
3. Seed the selected set with initial CC80 admissions.
4. Repeatedly choose the remaining qualified candidate minimizing its maximum
   carried pair-vector cosine to the selected set.
5. After each choice, add it to the selected set and recompute. Exact ties
   prefer better CC80 rank, then conversation order.
6. Only this qualified pool may claim spread allowance. Once exhausted, spread
   stops and slack returns to CC80.

`A_GLOBAL_BOTTOM` is a negative mechanism control. It traverses the complete
CC80 order in exact reverse and otherwise uses the same allocator.

`A_CC80_A3` reproduces the parent 50/50 convex+A3 arm as a descriptive prior-
spread control. It carries no decision bar.

No alternate pool fraction, novelty metric, session penalty, cluster floor,
dynamic share or global-bottom variant is permitted.

## 6. Endpoints

Primary boolean: complete resolved required-evidence delivery. Report paired
gains, losses and net versus `A_CC80_FULL` for combined, targeted, breadth and
other populations at each budget. Also report breadth required-identity net,
all four conversation nets, zero/partial evidence, admission phase, selected
counts, qualified-pool exhaustion, CC80 ranks, characters and payload digests.

Report treatment against `A_CC80_A3` and `A_GLOBAL_BOTTOM` descriptively.
Availability is not reader use.

## 7. Frozen disposition

At each budget, a qualified-treatment cell passes only when versus full CC80:

- combined complete gains exceed losses;
- targeted gains are at least losses;
- breadth complete gains exceed losses;
- breadth required-identity net is positive; and
- every conversation net is nonnegative, with at least two positive.

Apply in order:

1. `QUALIFIED_SPREAD_WORKS` if the cell passes at both budgets and qualified
   combined complete exceeds global bottom at both budgets.
2. `QUALIFIED_SPREAD_CARRIES_SIGNAL` if exactly one budget passes, the other
   budget has nonnegative combined, targeted, breadth and breadth-identity
   nets, and qualified combined exceeds global bottom at both budgets.
3. `CONTROL_FAILURE` if qualified combined does not exceed global bottom at
   either budget.
4. `NO_SPLIT_SELECTED` otherwise.

Only `QUALIFIED_SPREAD_WORKS` selects the tested architecture for a separately
registered reader study. Every other branch retains full CC80 as fallback.
No branch tunes the pool or share.

## 8. Preflight — binding before outcome generation

- **PF1:** hash/count corpus, blind manifest, vector cache, parent CC80 orders,
  parent A3 selections and label artifact.
- **PF2:** reproduce Part 1's name-to-behavior distributions and prove that
  “bottom” is minimum redundancy inside CC80's top quarter, while the global
  control is reverse query relevance.
- **PF3:** freeze and hash all orders, phase admissions and payloads before any
  label-bearing artifact opens; planted early label access must fail.
- **PF4:** synthetic question rows must reach every disposition; real traces
  must make nonempty qualified/global spread and both pool-exhausted and
  budget-binding treatment alternatives must exist.
- **PF5:** content identities only; reject duplicate and missing joins.
- **PF6:** reproduce all parent CC80 full and CC80+A3 selected identities and
  payload digests at both budgets before measuring the new arms.
- **PF7:** run the greedy recurrence to complete pool exhaustion on all 871 real
  traces; verify no candidate repeats, score updates after every selection and
  no candidate outside the pool enters spread.
- **PF8:** four conversations can detect within-corpus availability changes but
  not transfer or reader effects.
- **PF9:** represented sessions, low redundancy, nonempty spread and identity
  gains can all pass while complete breadth is false; report those residuals.
- **PF10:** availability only; no reader run is included.

Preflight may use the sealed vector cache in read-only mode. Cache misses and
LLM/generative calls must be zero. Under the program convention, cached
embedding use is model-free; embedding calls are still reported.

## 9. Execution and closeout

Commit this registration alone; implement and commit passing Preflight; run the
sealed outcome; commit question-level results before mechanism interpretation;
then report, update README/AGENTS/memory and open a stacked TC-010 PR. Do not
run answers or alter the locked share after seeing results.
