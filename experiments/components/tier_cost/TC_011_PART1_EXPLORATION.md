# TC-011 Preflight Part 1 — four protected-spread mechanisms

**Status:** complete; label-blind exploration only  
**Date:** 2026-08-24  
**Artifact:** `artifacts/tc011/part1_exploration.json`  
**Artifact SHA-256:** `0584366c067ddd2686de5b4a1de67bd1f472c548e7b7b4f3c6f3d3ab10fea952`

## Boundary

This exploration opened no resolved evidence, answer, rubric or question-class
label. It reused frozen CC80 orders, candidate vectors and the TC-007 allocator
over all 871 blind questions at 16,000 and 32,000 characters. It made zero
embedding calls, zero LLM/generative calls and zero cache misses; 2,236 cached
texts were read.

## Behavioral identities

- `LOGDET` greedily maximizes exact-cost-normalized marginal log determinant,
  quality-weighted by CC80 and conditioned on initial semantic admissions.
- `ASPECT` greedily maximizes exact-cost-normalized saturation of deterministic
  entity, date, number, noun, event and predicate-object facets, also weighted
  by CC80 and conditioned on initial admissions.
- `CHAIN_ANCHORED` starts from the normalized centroid of initial CC80
  admissions, retains `0.3` of the original query in every cue, and updates its
  state `0.5/0.5` with each admitted candidate.
- `CHAIN_PURE` uses the same initial centroid and `0.5/0.5` update but removes
  the original query after seeding.

Every arm is a protected-spread route behind the same initial CC80 half. Only a
successfully serialized candidate updates state. Each recurrence stops when no
remaining complete candidate fits the spread allowance.

## Name-to-behavior distributions

All values below are medians across 871 questions.

| Budget | Arm | Spread steps | Final selected | Spread CC80 rank |
|---:|---|---:|---:|---:|
| 16k | LOGDET | 44 | 70 | 109 |
| 16k | ASPECT | 23 | 49 | 77 |
| 16k | CHAIN_ANCHORED | 31 | 58 | 91 |
| 16k | CHAIN_PURE | 32 | 58 | 126 |
| 32k | LOGDET | 75 | 130 | 141 |
| 32k | ASPECT | 47 | 100 | 126 |
| 32k | CHAIN_ANCHORED | 57 | 111 | 129 |
| 32k | CHAIN_PURE | 57 | 111 | 159 |

The complete min/median/max distributions are in the artifact. The anchored
and pure chain selected sets differ on 871/871 questions at both budgets;
LOGDET and ASPECT also differ on 871/871. Thus neither comparison is a renamed
identity test.

The chain centroid's median query cosine moved from `.713` to `.517` anchored
and `.480` pure at 16k; at 32k it moved from `.690` to `.499` and `.481`.
Anchoring therefore measurably restrains but does not prevent semantic drift.
Pure chaining reaches materially deeper CC80 ranks.

ASPECT found 10,462 noun, 8,349 event, 4,016 predicate-object, 3,140 entity,
309 date and 255 number facet occurrences. It did not collapse to an empty or
single-facet selector. LOGDET retained positive unselected marginal gain after
packing on every trace; its stop was character capacity, not objective
exhaustion.

## Degenerate and absorbing states

- No arm was empty on any real trace.
- No recurrence repeated a candidate.
- All four arms reached the no-complete-candidate-fits absorbing state on every
  trace. Capacity only decreases, so that state cannot reopen.
- LOGDET's residual information state is monotone; ASPECT's saturated facet
  maxima are monotone; both chain states update only after admission.
- A zero-length or zero-vector semantic seed would make either chain undefined.
  The real population has neither state; Preflight must reject it explicitly.
- ASPECT can still favor verbose facet-rich text despite cost normalization;
  LOGDET can reward geometrically novel but irrelevant text; either chain can
  follow a coherent but answer-irrelevant association. These are outcome
  questions, not properties certified by this exploration.

## Design consequence

All four mechanisms are active, distinct and safe to compare. The locked study
must preserve the exact initial semantic seed, exact-character stopping,
CC80 tie-break, E006-carried chain constants (`W_Q=.3`, `rho=.5`), and the
label boundary. No parameter sweep is justified by Part 1.
