# SR-001 Final Design Lock

**Date:** August 11, 2026
**Pre-registration:** `baa317db41cb45b90087f4ec1cb1d4bd558cf55a`
**Authorization:** `f99b86a4`
**Amendment 001:** `5828147c98afdd542a6fe4233af8e0e7220bb04a`
**Passing Part 1:** `bbef505c648371e7761e0bedb9a35da21f4ccda6`
**Deterministic digest:** `7f4f04fff4937e81a75a1c44b4cc219497943baff7288e379ebda835a5dd6776`
**Status:** FINAL DESIGN LOCKED - PF1-PF10 AUTHORIZED

## Locked intervention

C0 and T1 receive an identical complete ordered source-episode identity and
score sequence for each query. C0 packs whole episodes. T1 replaces each source
with every faithful non-empty sentence span, ordered by source rank, then user
before assistant, then ascending offsets. Spans inherit their source score.
Both arms use method tag `M2`, the same renderer, skip-overflow packer, eligible
population, and 32,000-character ceiling.

Amendment 001 anchors committed display scores for historically selected M2
sources in both arms. Assertions preserve the complete source identity order.
There is no span vector, span reranking, salience filter, deduplication,
adjacency, chain, domain floor, label read, or query-history state.

## Part 1 lock

- Twenty-five label-blind queries completed within budget.
- All 24 C0 holdout selected identities, character counts, and payload bytes
  reproduce committed M2 exactly.
- Every source has at least one faithful span and all offsets round-trip.
- Two fresh processes produced the same deterministic digest.
- The mechanism source audit and planted forbidden-path sentinel pass.
- C0 selects 7-11 whole episodes per query.
- T1 selects 85-95 spans spanning 3-7 unique sources per query.
- T1 ends with one partially delivered source on 23/25 queries and none on 2.

These are label-blind mechanics, not evidence availability or efficacy. The
lower T1 source breadth is retained rather than repaired because changing
within-source ordering, filtering, interleaving, or scoring would introduce a
different component after observing Part 1.

## Binding continuation

PF1-PF10 and sealed measurement must use the unchanged preregistered gates:
broad Q11 and total holdout improvement, zero per-query targeted losses, and
non-regression for every query class and required domain. Measurement stops at
the first failure. A 35-turn ablation is permitted only if all five gates pass;
a full live run remains unauthorized.

This lock contains no fact, domain, answer-key, recall, gain/loss, or art
outcome from SR-001.
