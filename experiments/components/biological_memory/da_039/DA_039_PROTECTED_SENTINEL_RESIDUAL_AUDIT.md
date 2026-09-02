# DA-039 Protected Sentinel Residual Audit

**Status:** `COMPLETE; DOMINANT_PRIOR_SENTINEL_ATOMIC_CONSUMPTION`
**Date:** August 30, 2026
**Parent:** DA-038 result commit `08437483`
**Standing:** spent evidence-aware causal accounting only
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

What mechanically blocks the 18 LongMem one-hop-reachable dependencies left
after DA-038 protects the complete DA-033 pack, sentinel-encodes it, and appends
every fitting atomic member in frozen order?

The audit may inspect evidence only after replaying DA-038 exactly. It cannot
select, replace, reorder or admit any payload.

## 2. Locked Inputs

Use DA-038's sealed blind allocation and outcomes and DA-036's residual
identities. Reproduce DA-038 complete delivery 232/250, remove its 10 gains
from DA-036's 28 residuals, and audit exactly 18 remaining items.

Replay the complete protected DA-033 identity/member sequence under DA-038's
selected codec and every DA-038 atomic attempt in frozen order. No evidence-
dependent state may enter that replay.

## 3. Exhaustive Classes

Subtract identities delivered by DA-038 from each DA-036 residual, then assign
one class in this order:

1. `MULTI_CARRIER_CONJUNCTION`: no single exposed carrier covers all remaining
   missing identities.
2. `MULTI_MEMBER_CONJUNCTION`: one carrier covers all remaining identities but
   requires more than one absent member.
3. `RETAINED_DA033_NO_TAIL`: sentinel did not strictly reduce the protected
   DA-033 charge, so no append-only tail ran.
4. `INITIAL_SENTINEL_ATOMIC_SIZE`: a single required member does not fit at the
   recovered-capacity boundary before any DA-038 additions.
5. `PRIOR_SENTINEL_ATOMIC_CONSUMPTION`: it fits at that boundary but not at its
   frozen DA-038 arrival after earlier append-only additions.
6. `UNACCOUNTED`: none of the above.

Record required carriers/members, initial and arrival slack, exact member costs,
final slack, and whether each requirement fits after the complete DA-038 pack.

## 4. Gates and Reporting

Require exact hashes and joins, 18-item cardinality, complete exposed-union
coverage, exact protected-sequence and tail charge replay, one class per item,
zero unaccounted cases, byte-identical audit replay and zero calls.

Report class counts and cost/slack distributions. Dominance requires >=60%.
Diagnostic only. Any successor must preserve the complete DA-038 identity/member
sequence and may only add exact evidence-blind capacity or a stronger structural
dependency representation.
