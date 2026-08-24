# TC-011 four protected-spread mechanisms

**Type:** registered lightweight offline evidence-availability probe  
**Status:** pre-registration; not yet runnable  
**Date:** 2026-08-24  
**Authorization:** user requested all four proposed spread arms, including both
chained variants, behind the locked semantic method and 50/50 protection

## 1. Question and boundary

With frozen CC80 filling the semantic half first, does any of four deterministic
spread objectives improve breadth evidence without losing direct semantic
retrieval: residual log determinant, structured aspect coverage, query-anchored
chaining, or pure chaining?

This is a lightweight availability probe on already-used LoCoMo development
conversations. It makes no answer calls and cannot establish reader accuracy,
unseen-corpus transfer, production adoption, an optimal objective, or an optimal
budget share.

## 2. Frozen inputs and population

- Corpus SHA-256:
  `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`.
- Conversations: `conv-41`, `conv-42`, `conv-47`, `conv-48`.
- Same 1,365 adjacent-turn candidates, text, carried float32 vectors, renderer,
  containment deduplication and skip-on-overflow packing.
- 871 unique questions; 868 eligible, comprising 704 targeted, 44 breadth and
  120 other questions under TC-007's frozen definitions.
- Budgets: 16,000 and 32,000 serialized characters.
- Part 1 artifact SHA-256:
  `0584366c067ddd2686de5b4a1de67bd1f472c548e7b7b4f3c6f3d3ab10fea952`.
- Stable keys are question and candidate content identities. Generated ids,
  timestamps and paths are forbidden.

## 3. Locked semantic route and allocator

`CC80` query-wise min-max normalizes carried dense cosine and BM25 candidate
scores and ranks the complete store by
`r_i = 0.8*dense_i + 0.2*BM25_i`, using the frozen deterministic tie-break.
There is no coefficient sweep, query expansion, reranker or new embedder.

For total budget `B`, initial CC80 and spread each receive solo allowance
`H=B/2`:

1. Initial CC80 admits complete candidates fitting `H`.
2. A spread arm excludes those admitted identities and fills its solo `H`.
3. Merge in phase order, serialize once and containment-deduplicate by stable
   candidate identity.
4. CC80 resumes its unchanged order and fills actual remaining capacity.
5. Unused spread allowance and wrapper savings return only to CC80.
6. No identity serializes twice and exact serialized length may not exceed `B`.
   Overflow candidates are skipped, never truncated.

“50/50” is two maximum solo allowances, not guaranteed final composition.
Only a candidate that fits and is admitted may change a spread arm's state.

## 4. Common definitions

Candidate embeddings `v_i` and query embedding `q` are unit-normalized. `r_i`
is the frozen CC80 score in `[0,1]`. Exact additive character cost is the
carried packer's cost for appending the complete candidate. At every step an
arm considers every unadmitted candidate that still fits the remaining spread
allowance. Exact objective ties prefer better CC80 rank, then conversation
order and content identity. The recurrence stops when no complete candidate
fits; an objective with no positive marginal gain also stops and returns slack
to CC80.

## 5. Arms

### Controls

- `A_CC80_FULL`: CC80 receives all `B` characters. This is the binding
  comparison.
- `A_CC80_A3`: byte-identical reproduction of the prior 50/50 convex+A3 arm.
  It is descriptive and carries no decision bar.

### T1 — residual log determinant

Seed `S` with initial CC80 admissions. Define

`K_S[a,b] = delta(a,b) + sqrt(r_a*r_b) * dot(v_a,v_b)`.

For each feasible candidate `i`, compute

`Delta_i = logdet(K_(S union {i})) - logdet(K_S)`

and choose the greatest `Delta_i / additive_char_cost_i`. Append the candidate
to `S` and update the exact Cholesky residual. No pool cutoff, diagonal jitter,
similarity coefficient or candidate-count cap is permitted.

### T2 — deterministic aspect coverage

Parse candidate text once with `en_core_web_sm` 3.8 and its tagger, parser,
lemmatizer and NER. Normalized phrases case-fold lemmas, omit whitespace,
punctuation and stop words except number-like tokens, and join with `_`.
Extract exactly these facets:

- `entity:<NER label>:<normalized entity>` and a separate `date:<value>` for
  `DATE` entities;
- `number:<lower surface>` for every number-like token;
- `noun:<normalized noun chunk>`;
- `event:<verb lemma>` for every `VERB`; and
- `relation:<head lemma>:<dependency>:<normalized dependent subtree>` when
  the dependent is `dobj`, `obj`, `pobj`, `attr`, `oprd`, `dative` or
  `nsubjpass` and its head is `VERB` or `AUX`.

Within each conversation store, define
`idf_f = log((N+1)/(df_f+1)) + 1`. Seed facet coverage from initial CC80 as
`C_f = max(r_i*idf_f)` over seed candidates containing `f`. A feasible
candidate's marginal is
`sum_f max(0, r_i*idf_f - C_f) / additive_char_cost_i`.
Choose the greatest marginal and update maxima. No parser alternative, facet
weight, cap, threshold or expansion is permitted.

### T3 — query-anchored chain

Initialize `c_0` as the unit-normalized unweighted mean of initial CC80
candidate vectors. At step `t`, use cue
`u_t = normalize(0.3*q + 0.7*c_t)`, choose the feasible candidate maximizing
`dot(u_t,v_i)`, admit it, then update
`c_(t+1) = normalize(0.5*c_t + 0.5*v_i)`.

### T4 — pure chain

Use the same seed and update as T3, but `u_t = c_t`: the original query has no
direct term after semantic seeding. T3's `0.3` query weight and both arms'
`0.5` recurrence are carried from E006's selected development constants. There
is no depth, beam, top-m or coefficient sweep; the exact character allowance is
the stopping rule.

## 6. Endpoints

Primary boolean: complete resolved required-evidence delivery. For every new arm
versus `A_CC80_FULL`, report paired gains, losses and net for combined,
targeted, breadth and other populations at both budgets. Also report:

- breadth required-identity gains/losses/net;
- zero, partial and complete evidence states;
- all four conversation nets;
- initial, spread, returned and final candidate counts;
- exact characters and payload digests;
- spread CC80 ranks and pairwise arm identity overlap;
- LOGDET marginal/residual distributions;
- ASPECT marginal, covered-facet and facet-family distributions; and
- chain length, selected cosine, centroid-to-query drift and stopping reason.

McNemar exact p-values are descriptive. No arm is selected by the smallest
p-value or largest observed net.

## 7. Frozen dispositions

Evaluate each treatment independently against full CC80. A budget cell passes
only when:

- combined complete gains exceed losses;
- targeted complete gains are at least losses;
- breadth complete gains exceed losses;
- breadth required-identity net is positive; and
- every conversation net is nonnegative, with at least two positive.

For each arm, apply in order:

1. `WORKS` if both budget cells pass.
2. `CARRIES_SIGNAL` if exactly one cell passes and the other has nonnegative
   combined, targeted, breadth-complete and breadth-identity nets.
3. `NO_POSITIVE_SIGNAL` otherwise.

The family outcome is `CANDIDATE_IDENTIFIED` if any arm is `WORKS`,
`SIGNAL_ONLY` if none works but at least one carries signal, and
`NO_CANDIDATE` otherwise. Multiple qualifying arms remain multiple candidates;
this probe may not rank or adopt them post hoc. Only `WORKS` authorizes a
separately registered reader study. Full CC80 remains the fallback in every
other branch.

## 8. Preflight — binding before outcome generation

- **PF1:** hash/count corpus, blind manifest, cache, CC80 orders, parent A3,
  labels, parser package and Part 1 artifact; reject missing/zero vectors and
  empty initial semantic seeds.
- **PF2:** reproduce Part 1's behavioral identities and full distributions,
  including 871/871 anchored-versus-pure and LOGDET-versus-ASPECT set
  differences at each budget.
- **PF3:** freeze and hash every order, state trace, phase admission and payload
  before any label-bearing artifact opens; planted early label access must fail.
- **PF4:** synthetic rows must reach all three arm dispositions and all three
  family outcomes. Real traces must produce nonempty spread for every arm and
  both distinct chain alternatives.
- **PF5:** content identities only; reject duplicate and missing joins.
- **PF6:** reproduce all parent CC80 full and CC80+A3 selected identities and
  payload digests at both budgets: 3,484 checks.
- **PF7:** execute every recurrence to its absorbing state on all 1,742
  question-budget traces; prove no repeat, state changes only after admission,
  capacity never increases and no-fit cannot reopen. LOGDET residual and ASPECT
  coverage must be monotone within numerical tolerance.
- **PF8:** four conversations can detect within-corpus availability changes but
  not reader effects or transfer.
- **PF9:** geometric novelty, facet coverage, associative coherence, item count,
  represented sessions and identity gains can each pass while answer evidence
  or reader use is false; report these residuals rather than treating them as
  endpoints.
- **PF10:** availability only; no answer or reader run is authorized.

Preflight may use the sealed vector cache read-only. Cache misses, new embedding
calls and LLM/generative calls must all be zero. Under the program convention,
cached embeddings do not count as model calls, but all call counts are reported.

## 9. Execution and closeout

Commit this registration alone. Then implement and commit passing Preflight,
run the sealed outcome, commit question-level results before mechanism
interpretation, report the frozen dispositions, update README/AGENTS/memory and
open a stacked TC-011 PR. Do not tune any arm or run answers after seeing the
outcome.
