# DA-036 LongMem Protected Atomic Residual Audit

**Status:** `COMPLETE; DOMINANT_INITIAL_ATOMIC_SIZE`
**Date:** August 30, 2026
**Parent:** DA-035 result commit `30496924`
**Standing:** spent evidence-aware causal accounting only
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

What mechanically blocks the 28 LongMem one-hop-reachable dependencies left
after DA-033 appends every fitting atomic member to the immutable DA-031 order?

The audit must preserve DA-033's strongest order. It may inspect evidence only
to classify remaining misses; it cannot select, replace, reorder or admit any
payload.

## 2. Locked Inputs

Use DA-033's sealed blind allocation and outcomes and DA-032's residual
identities. Reproduce DA-033 complete delivery 222/250, remove its 11 gains
from DA-032's 39 residuals, and audit exactly 28 remaining items.

Replay the complete DA-031 protected sequence and every DA-033 atomic attempt
in frozen order with the selected exact codec. No evidence-dependent state may
enter that replay.

## 3. Exhaustive Classes

For each item, subtract identities delivered by DA-033 from DA-032's missing
set, then assign one class in this order:

1. `MULTI_CARRIER_CONJUNCTION`: no single exposed carrier covers all remaining
   missing identities.
2. `MULTI_MEMBER_CONJUNCTION`: one carrier covers all remaining identities but
   requires more than one absent member.
3. `INITIAL_ATOMIC_SIZE`: a single required member does not fit immediately
   after the complete immutable DA-031 pack.
4. `PRIOR_ATOMIC_CONSUMPTION`: it fits after DA-031 but not at its frozen
   DA-033 attempt arrival.
5. `RETAINED_CODEC_NO_TAIL`: the row has no applicable atomic attempt.
6. `UNACCOUNTED`: none of the above.

Record required carrier/member identities, initial and arrival slack, exact
member costs, final slack and whether each requirement fits after the complete
DA-033 pack.

## 4. Gates and Reporting

Require exact artifact hashes and joins, 28-item cardinality, complete exposed
union coverage, exact DA-031 and DA-033 cost replay, one class per item, zero
unaccounted cases, byte-identical audit replay and zero calls.

Report class counts and cost/slack distributions. Dominance requires >=60%.
This is diagnostic only. Any protected evidence-blind substitution near the
capacity boundary requires a separately registered successor and must retain
the complete DA-033 sequence byte-identically.
