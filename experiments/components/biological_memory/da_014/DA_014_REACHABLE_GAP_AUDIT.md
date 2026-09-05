# DA-014 Reachable Compact-Link Gap Audit

**Status:** `POST-OUTCOME CAUSAL AUDIT PROTOCOL`
**Date:** August 30, 2026
**Parent:** DA-013 result commit `c959fca`
**Standing:** descriptive audit on spent LongMemEval
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Why does DA-013 recover only 7 of the 86 direct-incomplete items whose complete
evidence exists within its fixed one-hop edge set?

The audit changes no retrieval or outcome. It accounts for each of the 79
reachable misses under the frozen temporal allocation and identifies the first
mechanical blocker.

## 2. Locked Population and Terms

Use DA-013's 465 outcomes and exact blind allocations. The audit population is
the 86 items where `DIRECT_ORIGINAL=0` and `ONE_HOP_ORACLE=1`; the miss
population is the 79 where `TEMPORAL_ORDER=0`.

For each missing target turn, identify every fixed edge whose neighbor contains
it. Reconstruct the frozen source-turn choice, initial compact slack, actual
arrival state, full-pair cost, both singleton costs and admitted action.

## 3. Exclusive First-Blocker Classes

Assign each reachable miss in this order:

1. `MULTI_CARRIER_CONJUNCTION`: completion requires target turns from at least
   two distinct neighbor episodes.
2. `WRONG_MEMBER_CHOICE`: a single carrier episode suffices, an evidence member
   fits at its arrival, but the fixed coverage rule chooses another member.
3. `PRIOR_CONSUMPTION`: the required fixed payload fits initial compact slack
   but not its actual arrival slack.
4. `INITIAL_PAYLOAD_TOO_LARGE`: no evidence-carrying payload from the sufficient
   carrier fits initial compact slack.
5. `UNACCOUNTED`: none of the above; any occurrence stops interpretation.

For conjunctions, additionally compute whether the cheapest evidence-complete
set fits initial slack and actual order, but do not reclassify or propose an
allocator from opened labels.

## 4. Fixed Analysis

Report class counts, question-type cells, initial and arrival slack, carrier
seed rank/direction, pair and evidence-member costs, selected-member agreement,
number of required carrier episodes and minimal evidence-complete cost.

Reproduce DA-013 164 direct, 171 temporal, 250 oracle and 7/0 exactly. Require
every gain and all 79 misses to receive complete carrier accounting.

Report `PAYLOAD_SELECTION_BLOCKER` if wrong-member choice is the modal
non-conjunction class; `CAPACITY_BLOCKER` if initial size or prior consumption
is modal; `CONJUNCTION_BLOCKER` if conjunction is modal; otherwise
`MIXED_BLOCKERS`. This is descriptive, not a design or adoption decision.

## 5. Preflight and Stops

- **PF1:** verify DA-013 allocation/outcome hashes and 465/164/171/250.
- **PF2:** test turn identity reconstruction, carrier enumeration, actual
  arrival replay, cost reconstruction, exclusive precedence and conjunctions.
- **PF3:** commit this protocol before writing the evidence-aware audit.
- **PF4:** require all declared classes to be mechanically reachable in tests;
  corpus classes may be empty.
- **PF5:** preserve question, episode, turn, edge, action and target keys.
- **PF6:** require 86 reachable items, 7 gains and 79 misses.
- **PF7:** require byte-identical audit replay.
- **PF8:** audit all 86 reachable items and every missing target carrier.
- **PF9:** this is post-outcome spent-data diagnosis, not a selector.
- **PF10:** no allocator, threshold, reader or adoption is authorized.

Stop on hash drift, incomplete carrier maps, action/cost replay mismatch,
overlapping item classes, any `UNACCOUNTED` item, or nondeterminism. Commit the
audit, report, scratchpad and digest without tuning a successor here.

