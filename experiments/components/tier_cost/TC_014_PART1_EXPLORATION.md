# TC-014 traversal controls — Part 1 exploration

**Status:** complete; label blind  
**Date:** 2026-08-25  
**Artifact:** `artifacts/tc014/part1_exploration.json`  
**Artifact SHA-256:** `d22fe26de2aa88edf1f574a7e59620a8c298255f7e3067f2e53540b489e91f84`

## Behavioral identities

- **Parent binding:** TC-013's one-hop sequential ownership, multiplying each
  edge's frozen ASPECT utility by `max(0, parent-child cosine)`.
- **Global assignment:** maximum-total frozen ASPECT utility one-to-one
  parent/child assignment; matched children remain in parent order.
- **Utility packing:** unchanged TC-013 parent/child edges, reordered by
  descending frozen ASPECT edge utility before protected packing.
- **Opportunity admission:** unchanged TC-013 edges in parent order, retained
  only when raw ASPECT edge value covers the exact semantic identities lost in
  a counterfactual insertion through the real allocator.
- **Combined:** parent-bound maximum-weight assignment, then descending bound
  utility packing.

All arms remain one hop deep. Children never become parents. All use the same
CC80 roots, deterministic facets, 50/50 protected allocator, exact character
costs and slack return as TC-013.

## Name-to-behavior and distributions

The 1,742 question-budget traces reproduce TC-013 edge ownership, selected
identities and payload digests exactly before applying a new mechanism.

| Budget | Arm | Traces with selected-set change | Median proposed/admitted | Median chosen parent cosine |
|---:|---|---:|---:|---:|
| 16k | Parent binding | 871/871 | 25/22 | .69 |
| 16k | Global assignment | 818/871 | 25/22 | .58 |
| 16k | Utility packing | 565/871 | 25/22 | .58 |
| 16k | Opportunity admission | 871/871 | 17/17 | .58 |
| 16k | Combined | 870/871 | 25/22 | .71 |
| 32k | Parent binding | 871/871 | 52/46 | .68 |
| 32k | Global assignment | 859/871 | 52/45 | .56 |
| 32k | Utility packing | 687/871 | 52/46 | .56 |
| 32k | Opportunity admission | 871/871 | 36/36 | .56 |
| 32k | Combined | 871/871 | 52/46 | .71 |

Global matching changes the proposed child set on 618/871 traces at 16k and
715/871 at 32k. Its larger selected-set change includes ownership-driven order
changes when the same child set is assigned to different parents.

Opportunity admission rejects a median 8/25 edges at 16k and 16/52 at 32k
because the child's raw facet value is below the exact CC80 value displaced.
It has zero capacity rejections after filtering and admits every retained edge.
The median counterfactual loses one semantic identity per considered child.

## Degenerate and absorbing states

Every real parent has at least one positive feasible child in all arms, so the
optional no-child state is absent on real traces but is reached by the unit
control. Parent binding does not collapse similarities to zero. Matching emits
unique children or an explicit dummy; utility sorting preserves edge identity;
opportunity admission terminates after one exact decision per TC-013 edge.
No recurrence or child-generated child exists.

The protected half binds for the unguarded arms. The opportunity guard removes
enough edges that its retained list always fits. These alternatives establish
that both capacity-binding and non-capacity stopping states exist.

## Surrogate audit

Higher parent cosine can select coherent but answer-irrelevant children.
Maximum assignment utility can improve the sum while harming a specific
question. Utility-first packing can prioritize redundant edges. The
opportunity guard compares ASPECT value in common units, not answer evidence;
it can preserve the wrong semantic identities. Counts, cosine, summed utility,
facet gain and exact displacement therefore remain mechanism diagnostics, not
outcomes.

The exploration used 2,236 cache hits, zero misses, zero embedding calls and
zero LLM/generative calls. No evidence labels or answer artifacts were opened.

