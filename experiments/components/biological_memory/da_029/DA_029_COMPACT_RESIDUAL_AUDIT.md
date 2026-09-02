# DA-029 Compact Residual Dependency Audit

**Status:** `COMPLETE; MIXED RESIDUAL BLOCKERS`
**Date:** August 30, 2026
**Parent:** DA-028 result commit `51daaa95`
**Standing:** spent evidence-aware causal accounting only
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

After shortest-codec capacity is added without displacement, what mechanically
blocks the remaining one-hop-reachable evidence dependencies?

DA-028 leaves 9 NF and 42 LongMem questions below their frozen one-hop ceilings.
NF admits 2,599 extra actions for one completion, so raw added capacity no
longer explains the residual by itself.

## 2. Locked Inputs

Use DA-028's sealed blind allocation and byte-identical outcomes. Reproduce NF
977/986 and LongMem 208/250. Audit exactly the remaining ceiling-reachable
misses; do not introduce a new retrieval candidate, renderer, order or outcome.

## 3. Exhaustive Classes

For each residual, identify the frozen exposed carriers whose member identities
cover the missing evidence and assign exactly one class in this order:

1. `MULTI_CARRIER_CONJUNCTION`: no single exposed carrier covers all missing
   identities.
2. `WRONG_FROZEN_MEMBER`: one carrier covers the missing set in a member other
   than DA-023's frozen fallback, and that required member fits at its frozen
   compact arrival state.
3. `INITIAL_COMPACT_SIZE`: the required pair/member does not fit immediately
   after the immutable DA-023 compact pack.
4. `PRIOR_COMPACT_CONSUMPTION`: it fits immediately after the immutable pack but
   not at its frozen arrival after earlier DA-028 additions.
5. `RETAINED_CODEC_NO_TAIL`: DA-028 retained DA-023's codec by exact charge and
   therefore performed no compact tail pass on this question.
6. `UNACCOUNTED`: none of the above.

For conjunctions, record carrier count and required member count. For finite
single-carrier cases, record initial/arrival used, slack, exact required cost,
position, frozen and required member.

## 4. Gates and Reporting

Require exact corpus joins, 9/42 residual counts, complete exposed-union
coverage, one class per item, exact compact state replay, no unaccounted class,
byte-identical audit replay and zero calls. Stop on any mismatch.

Report class counts and distributions by corpus. Call a class dominant only if
it covers at least 60% of that corpus. A shared successor exists only if the
same class is dominant in both corpora. This audit authorizes no intervention,
threshold, reader run or adoption; any successor needs its own registration.
