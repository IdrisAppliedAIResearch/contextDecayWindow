# TC-014 — one-hop traversal component ablation

**Type:** registered lightweight offline evidence-availability probe  
**Status:** pre-registration; not yet runnable  
**Date:** 2026-08-25  
**Authorization:** user requested separate tests of the proposed TC-013
traversal improvements and one combined parent-binding/assignment/packing arm

## 1. Question and boundary

Which evidence-blind traversal control, if any, improves TC-013's one-hop
CC80-parent ASPECT fan-out: explicit parent binding, global unique assignment,
utility-first packing, or exact semantic opportunity admission? Does the
requested combination of parent binding, global assignment and utility-first
packing improve more than its isolated components?

This is an offline LoCoMo development evidence-availability ablation. It makes
no embedding or answer-model calls and cannot establish reader accuracy,
unseen-corpus transfer, deployment adoption, an optimal score, or an optimal
budget share.

## 2. Frozen inputs and population

- Part 1 artifact SHA-256:
  `d22fe26de2aa88edf1f574a7e59620a8c298255f7e3067f2e53540b489e91f84`.
- TC-013 selection SHA-256:
  `117784d28859eb336cdd185598f8a132e6e52bfac045590ddb2a29e093ce920e`.
- Frozen corpus, four conversations, 1,365 adjacent-turn candidates, carried
  float32 vectors, CC80 orders/scores, deterministic facets, exact renderer,
  containment deduplication and skip-on-overflow packing are unchanged.
- Same 871 unique questions and 868 eligible outcome questions: 704 targeted,
  44 breadth and 120 other.
- Budgets remain 16,000 and 32,000 serialized characters with the unchanged
  50/50 solo allowances and CC80-only slack return.
- Stable keys are question and candidate content identities. Generated ids,
  timestamps and paths are forbidden.

## 3. Common edge definitions

Initial CC80 admissions under `H=B/2` are the ordered parents `p`. Children are
all non-parent candidates that individually fit `H`. Let `r_i` be frozen CC80
query relevance, `W_i` the sum of frozen TC-011 IDF weights over candidate
facets, `O_pi` the summed IDF of facets shared by parent and child, `a_i` exact
additive character cost, and `s_pi=dot(v_p,v_i)` carried-vector cosine.

The unchanged TC-013 edge values are:

`raw(p,i) = r_i*W_i - min(r_i,r_p)*O_pi`

`base(p,i) = raw(p,i)/a_i`.

Edges with `raw<=1e-12` are unavailable. Exact utility ties use better frozen
CC80 rank and then conversation/content order unless an arm specifies its
emission order. All children are globally unique within an arm. No child
becomes a parent; traversal depth is exactly one.

## 4. Arms

### Controls

- **C0 full CC80:** unchanged CC80 receives all `B` characters.
- **C1 TC-013 fan-out:** exact reproduction of sequential singleton-parent
  ASPECT proposals in parent order and unchanged protected packing.

### T2 parent binding only

Define `bound(p,i)=base(p,i)*max(0,s_pi)`. In unchanged CC80 parent order, each
parent claims its greatest remaining positive `bound` child. Emit children in
parent order and apply the unchanged allocator. Nothing else changes.

### T3 global assignment only

Use `base(p,i)` unchanged. Solve the deterministic maximum-total-weight
one-to-one assignment over every parent and every feasible non-parent child.
Each parent also has its own zero-weight no-child dummy. Emit real matched
children in CC80 parent order, then apply the unchanged allocator. There is no
top-m pool or approximation.

### T4 utility-first packing only

Keep C1's exact parent-child assignments. Sort those edges by descending
`base`, then parent order, then conversation/content order, and send that child
order to the unchanged protected allocator. Edge ownership does not change.

### T5 exact semantic opportunity admission only

Visit C1 edges in parent order while maintaining the already retained child
prefix. For edge `(p,i)`, run the unchanged allocator on the retained prefix
and on the prefix plus `i`. If `i` does not enter the trial spread phase,
reject it. Otherwise let `L` be identities selected without `i` but absent
with `i`, and define `displaced(i)=sum_{j in L}(r_j*W_j)`. Retain `i` iff
`raw(p,i) >= displaced(i)`. On retention the trial becomes the current state;
on rejection the current state is unchanged. Emit retained children in parent
order. There is no coefficient or threshold sweep.

### T234 requested combination

Use `bound(p,i)`, solve T3's exact one-to-one assignment, then sort real matched
edges by descending `bound`, parent order and conversation/content order before
unchanged protected packing. T5 is deliberately absent so T234 isolates the
requested combination of items 2–4.

## 5. Endpoints and component attribution

For every treatment versus C1 at both budgets, report complete-evidence paired
gains, losses and net for combined, targeted, breadth and other populations;
breadth required-identity gains/losses; zero/partial/complete states; and all
four conversation nets. Also report the same endpoints versus C0 for T234.

Mechanism diagnostics are parent/proposed/admitted/returned/final counts,
selected-set differences, parent cosine, edge utility, dropped children,
matching ownership changes, and T5 accepted/value-rejected/capacity-rejected
counts plus displaced identity/value distributions. McNemar exact p-values are
descriptive.

At each budget, a treatment is `HELPS` versus C1 iff combined complete gains
exceed losses, targeted and breadth complete gains are each at least losses,
and breadth required-identity net is nonnegative. It is `NEUTRAL` iff all four
nets are zero; otherwise it is `HURTS`.

An arm is `TRANSFERABLE_HELP` if both budgets are `HELPS`,
`BUDGET_SPECIFIC_HELP` if exactly one is `HELPS`, and `NO_HELP` otherwise.
These dispositions identify component direction only; they do not select a
winner or authorize adoption. T234 additionally reports whether it exceeds
full CC80 under the same cell rule with breadth complete and breadth identity
nets required positive. No post-result arm combination, coefficient, cap,
threshold, budget share, reader run or deployment change is authorized.

## 6. Preflight — binding before labels open

- **PF1:** hash/count registration, Part 1, corpus, blind manifest, vector
  cache, CC80 source, TC-013 controls and label artifact; reject missing, empty
  or zero-vector inputs.
- **PF2:** reproduce Part 1 behavioral identities and full distributions.
  Verify every named variable against the equations above.
- **PF3:** freeze and hash all treatment edges, ownership, admission phases and
  payloads before any label-bearing artifact opens; planted early access must
  fail.
- **PF4:** synthetic rows must reach `HELPS`, `NEUTRAL`, `HURTS` and all three
  arm dispositions. Part 1 must show every treatment changes real selected
  sets at both budgets and both T5 retention/rejection alternatives occur.
- **PF5:** content identities only; reject duplicate, missing and unstable
  joins.
- **PF6:** reproduce all 1,742 TC-013 edge/allocation traces and all 1,742
  full-CC80 selected identity sequences and payload digests: 3,484 controls.
- **PF7:** matching must be globally unique and equal an independent small
  exhaustive optimum; sorting must preserve edge identity; T5 must make one
  monotone retain/reject decision per C1 edge and reproduce its exact
  counterfactual. No child-generated recurrence exists.
- **PF8:** four development conversations can detect within-corpus direction
  but not reader effects or transfer.
- **PF9:** cosine, summed assignment utility, packing utility and ASPECT-valued
  semantic displacement can each improve while answer evidence remains false;
  only resolved evidence availability is the outcome.
- **PF10:** availability only; no answer or reader run is authorized.

Preflight and outcome use the existing cache read-only. Cache misses, embedding
calls and LLM/generative calls must all be zero.

