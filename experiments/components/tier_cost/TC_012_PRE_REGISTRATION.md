# TC-012 dynamic ASPECT matrix probe

**Type:** registered lightweight offline evidence-availability probe  
**Status:** pre-registration; not yet runnable  
**Date:** 2026-08-24  
**Authorization:** user requested a targeted matrix-multiplication probe of
per-hop prompt recomparison and the proposed residual-question-facet cue

## 1. Question and boundary

Can ASPECT improve when its semantic relevance is recomputed after every
admission rather than frozen once—either from the growing selected context or
from still-uncovered question facets?

This uses already-observed LoCoMo development conversations and is descriptive
availability work. It makes no answer calls and cannot establish transfer,
reader accuracy, production adoption, or optimal parameters.

## 2. Frozen inputs

Carry TC-011's 871 blind questions, 868 eligible outcomes, 1,365 complete
candidates, vectors, deterministic ASPECT facets, exact renderer/packer,
16,000/32,000-character budgets and 50/50 allocator. Frozen CC80 remains
query-wise `.8*dense_normalized + .2*BM25_normalized`. Stable content identities
are the only join keys.

Part 1 artifact SHA-256 is
`a87edd6d8f6f39acd58c5a32946b1922fb92b89887b56e1b76bef94493a40289`.

## 3. Common dynamic scoring

Initial CC80 first fills solo allowance `B/2`. Spread excludes admitted
identities. At every spread hop, an arm constructs unit cue `u_t`, computes all
candidate cosines by the existing vector matrix `V @ u_t`, query-wise min-max
normalizes them, and sets

`r_i(t) = .8*dynamic_dense_i(t) + frozen_.2_BM25_i`.

For the currently selected set, recompute every facet maximum as
`C_f(t)=max r_j(t)*idf_f`. Choose the feasible candidate maximizing

`sum_f max(0, r_i(t)*idf_f - C_f(t)) / exact_additive_chars_i`.

Ties use frozen CC80 rank then content order. Only an admitted candidate updates
state. Stop when no complete candidate fits or no positive marginal remains;
merge phases and return slack to CC80 exactly as TC-011.

## 4. Arms

- `CC80_FULL`: binding full-budget control.
- `ASPECT_STATIC`: byte-identical TC-011 ASPECT control.
- `DYNAMIC_PROMPT`: the user's recomparison proposal. Initialize context `c_0`
  as the normalized mean of initial semantic vectors. At every hop use
  `u_t=normalize(.3*q+.7*c_t)` and, after admission,
  `c_(t+1)=normalize(.5*c_t+.5*v_i)`. Constants are carried from TC-011/E006.
- `RESIDUAL_ASPECT`: the assistant proposal. Parse the question with TC-011's
  exact facet extractor. Remove facets represented by selected candidates.
  Weight every store candidate by the sum of conversation-store IDF for its
  intersection with uncovered question facets; their weighted vector centroid
  is `a_t`. If total weight is positive, use
  `u_t=normalize(.3*q+.7*a_t)`; otherwise use exact fallback `u_t=q`.

No coefficient, parser, facet, recurrence, share or budget sweep is permitted.

## 5. Part 1 instrument limitation

`DYNAMIC_PROMPT` differs from static ASPECT on 871/871 selections at both
budgets. `RESIDUAL_ASPECT` differs on only 146/871 at 16k and 71/871 at 32k;
its median hop uses query fallback because the exact lexical binder has no
remaining residual match. Residual outcome counts are descriptive only and
may characterize this binder, not residual-obligation retrieval broadly.

## 6. Endpoints and frozen disposition

Report complete evidence, paired gains/losses/net versus both full CC80 and
static ASPECT for combined, targeted, breadth and other populations. Also
report breadth identity changes, conversation nets, zero/partial/complete
states, selected counts/ranks, cue-to-query cosine, fallback rate, payload
digests and calls.

`DYNAMIC_PROMPT_WORKS` requires the TC-011 full-CC80 cell to pass at both
budgets: combined gains exceed losses, targeted gains at least losses, breadth
gains exceed losses, breadth-identity net positive, and all conversation nets
nonnegative with at least two positive.

`DYNAMIC_PROMPT_CARRIES_SIGNAL` requires, versus static ASPECT at both budgets:
combined gains exceed losses; targeted and breadth gains are at least losses;
breadth-identity net is nonnegative and positive at one or more budgets; and all
conversation nets are nonnegative. Otherwise disposition is
`NO_DYNAMIC_PROMPT_SIGNAL`.

Residual ASPECT receives `RESIDUAL_BINDER_LIMITED` regardless of outcome; raw
counts cannot be promoted into a signal claim after Part 1 found broad fallback.
Full CC80 remains fallback unless `DYNAMIC_PROMPT_WORKS`. A carries-signal result
authorizes only a separately registered successor on an untouched corpus.

## 7. Preflight

- **PF1:** hash/count corpus, blind manifest, cache, TC-011 selections, CC80
  scores, labels, parser and Part 1; reject missing vectors or seeds.
- **PF2:** reproduce Part 1 distributions, 871/871 dynamic-prompt differences
  and residual active-set counts 146/71.
- **PF3:** freeze all dynamic orders, traces and payloads before label access;
  planted early access fails; mechanism imports are label-free.
- **PF4:** synthetic rows reach works, carries and no-signal; real traces make
  every arm nonempty and both stop branches occur.
- **PF5:** stable content keys; reject duplicates and missing joins.
- **PF6:** reproduce CC80 full and static ASPECT identities/digests at both
  budgets: 3,484 checks.
- **PF7:** every recurrence reaches a registered absorbing state with no repeat,
  admission-only updates and nonincreasing capacity.
- **PF8:** four used conversations cannot detect transfer or reader effects.
- **PF9:** dynamic semantic change, facet coverage and deeper rank can pass
  while complete evidence is false; residual fallback can hide absence of the
  proposed mechanism.
- **PF10:** availability only; no answer run authorized.

Cache misses, new embedding calls and LLM/generative calls must be zero.

## 8. Execution

Commit this registration alone; implement and pass Preflight; commit outcomes
before interpretation; then report, update README/AGENTS/memory and open a
stacked TC-012 PR. No post-result tuning is authorized.
