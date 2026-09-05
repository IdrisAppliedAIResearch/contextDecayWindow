# DA-024 Backreference Residual Blocker Audit

**Status:** `POST-OUTCOME CAUSAL AUDIT PROTOCOL`
**Date:** August 30, 2026
**Parent:** DA-023 result commit `f964b68d`
**Standing:** diagnostic audit on spent NF-004 and LongMemEval
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question and Population

What prevents the remaining one-hop-reachable direct misses from completing
after DA-023's immutable backreference capacity?

Audit exactly the DA-023 treatment misses inside the fixed one-hop ceilings:
10 NF-004 items (976 of 986) and 48 LongMem items (202 of 250). Retain all rows
for reproduction, but assign a blocker only to this residual population.

## 2. Fixed Evidence-Aware Classifier

For each residual item, map every still-missing target identity to exposed
neighbor pairs and members. Classify in this priority order:

1. `MULTI_PAIR_CONJUNCTION`: no single exposed neighbor pair contains all
   still-missing target identities, but their union does.
2. `WRONG_FROZEN_MEMBER`: one pair can complete the item; its frozen singleton
   omits required evidence, while the evidence-complete singleton would fit at
   the carrier's actual arrival state.
3. `INITIAL_BACKREF_SIZE`: the cheapest evidence-complete materialization of a
   single carrier pair does not fit in DA-023's recovered capacity before any
   additive admissions.
4. `PRIOR_ADDITIVE_CONSUMPTION`: that materialization fits initially but not at
   its actual arrival state after earlier additive admissions.
5. `UNACCOUNTED`: none of the locked predicates applies.

For conjunctions, additionally report whether every required materialization
fits jointly at initial capacity and whether prior consumption blocks the set.
Do not force conjunctions into a single-payload size class.

Initial and arrival costs use DA-023's exact prefix, prior-member history,
longest-match codec, role state, pair/member identities and 16k charging. A
rejected payload never enters history. No alternative member/order is used
outside the named evidence-aware diagnostics.

## 3. Outputs and Decision

Reproduce 935/970/976/986 and 164/188/202/250. Report blocker counts by corpus
and group; initial/arrival slack and required-cost distributions; carrier seed
rank/order position/action/member; conjunction set sizes; and exact replay.

Name `DOMINANT_<BLOCKER>` per corpus only when one class contains at least 60%
of residual items. Otherwise name `MIXED_RESIDUAL_BLOCKERS`. A shared successor
is supported only if the same class dominates both corpora. This audit does not
authorize an intervention, threshold, reader or adoption.

## 4. Preflight and Stops

- **PF1:** seal DA-023 blind/result, source populations and edge artifacts.
- **PF2:** test target-to-pair/member mapping, set-cover conjunction predicate,
  initial and arrival replay, correct-member counterfactual and priority order.
- **PF3:** commit protocol before constructing residual evidence joins.
- **PF4:** require exact residual populations 10/48 and at least one finite
  classification on each corpus.
- **PF5:** preserve every question, target, pair, member, action, history, cost
  and blocker key.
- **PF6:** reproduce all control/treatment/ceiling anchors and zero DA-023 losses.
- **PF7:** require byte-identical audit replay.
- **PF8:** retain all 1,563 outcomes and classify all 58 residuals.
- **PF9:** availability blockers do not establish reader behavior.
- **PF10:** no live run or production claim.

Stop on hash/anchor drift, missing carrier join, inconsistent cost replay,
overlapping final classes, unclassified residual, nondeterminism or any fresh
model/embedding/cache call. Do not tune codec, order, member choice or priority.

