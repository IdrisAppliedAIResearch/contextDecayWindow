# TC-009 convex relevance with protected-breadth probe

**Type:** descriptive feasibility diagnostic; not TC-010  
**Status:** minimal design lock before implementation  
**Date:** 2026-08-23  
**Parent:** TC-007 protected spread and TC-009 convex-fusion probe

## 1. Question and boundary

Test whether the fixed 80/20 normalized dense/BM25 ranker improves complete
evidence when it replaces only TC-007's relevance order inside the unchanged
50/50 relevance-plus-A3 protected allocator.

This is offline availability on used LoCoMo development data. It cannot select
an architecture, tune a coefficient or share, create TC-010, or authorize
reader answers.

## 2. Label-blind exploration

Run before this lock on all 871 blind questions with zero cache misses. The
unchanged allocator gives the treatment median protected-spread admissions of
28 at 16k and 57 at 32k; initial relevance medians are 25 and 52, returned
relevance medians are 1 and 1, and total selected medians are 54 and 111.
Protected spread is nonempty on 871/871 at both budgets.

Treatment selected sets differ from the original dense+A3 split on 685/871
questions at 16k and 601/871 at 32k. They differ from full-budget dense on
871/871 and 870/871. Thus both protection and the relevance substitution are
active. The allocator means 50% solo allowance per arm, containment dedup, then
unused merged capacity returned only to relevance; it is not a final 50/50
character composition guarantee.

## 3. Frozen arms and budgets

Same 1,365 complete pair candidates, vectors, renderer, containment dedup and
skip-on-overflow packer at 16,000 and 32,000 characters:

- `A_DENSE`: full-budget dense relevance.
- `A_CC80`: full-budget query-wise min-max
  `0.8*dense + 0.2*BM25` relevance.
- `A_DENSE_A3`: TC-007's exact 50/50 dense relevance plus frozen A3 spread.
- `A_CC80_A3`: exact same allocator and A3 order, changing only relevance to
  the frozen 80/20 order.

There is no alternate spread strategy, coefficient/share sweep, threshold,
fallback, candidate change, or rendering change.

## 4. Population, endpoints and disposition

Run all 871 unique questions; measure the 868 eligible, targeted 704, breadth
44 and other 120 populations. At each budget report treatment versus every
control for combined/targeted/breadth/other complete gains and losses, breadth
required-identity net, all four conversation nets, selected counts, phase
counts and characters.

`DESCRIPTIVE_POSITIVE_SIGNAL` requires `A_CC80_A3` versus `A_DENSE` at both
budgets to have: combined gains greater than losses; targeted gains at least
losses; breadth complete gains at least losses; breadth identity net
nonnegative and positive at one or both budgets; and every conversation net
nonnegative with at least two positive. Otherwise `NO_POSITIVE_SIGNAL`.
Contrasts to full CC80 and dense+A3 explain attribution but cannot rescue a
dense failure.

## 5. Minimal Preflight — before outcome join

- **PF1:** hash/count corpus, blind manifest, cache, predecessor selections and
  labels.
- **PF2:** reproduce §2 distributions and prove solo allowances, dedup and
  relevance-only slack return on planted and real traces.
- **PF3:** freeze and hash all orders/payloads before any label-bearing artifact
  opens; planted early access fails.
- **PF4:** synthetic rows make both dispositions reachable.
- **PF5:** blind keys and pair content identities only.
- **PF6:** reproduce all accepted TC-007 dense/dense+A3 and convex-probe
  dense/CC80 selected-id and payload digests at both budgets.
- **PF7:** not applicable; no feedback state.
- **PF8:** four conversations do not establish transfer.
- **PF9:** A3 coverage, phase counts and availability can pass without breadth
  completeness or reader use; report each residual.
- **PF10:** availability only; reader work requires separate registration.

Preflight may read sealed vectors with zero misses and zero embedding/LLM
calls. Outcome uses sealed selections with zero ranking, cache or model calls.

## 6. Execution order

Commit this design alone; implement and commit passing Preflight; run the frozen
outcome; report and open a stacked diagnostic PR. Do not start TC-010 or reader
answers.
