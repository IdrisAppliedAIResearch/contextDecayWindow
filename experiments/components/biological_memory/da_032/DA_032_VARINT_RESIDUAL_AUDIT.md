# DA-032 Varint Residual Dependency Audit

**Status:** `COMPLETE; CORPUS-SPECIFIC SUCCESSORS`
**Date:** August 30, 2026
**Parent:** DA-031 result commit `efdb1820`
**Standing:** spent evidence-aware causal accounting only
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

What mechanically blocks the final 3 NF and 39 LongMem one-hop-reachable
dependencies after self-delimiting varint capacity?

DA-031 resolves every NF prior-consumption and conjunction case identified by
DA-029. The apparent remainder is three wrong-member cases, but DA-030 showed
that arrival-fit labels can change after a stronger protected suffix.

## 2. Locked Inputs

Use DA-031's sealed blind allocation and outcomes. Reproduce NF 983/986 and
LongMem 211/250. Start from DA-029's 9/42 residual identities, remove DA-031
gains, and audit exactly 3/39 remaining items.

## 3. Exhaustive Classes

Replay the selected codec and exact arrival state for each required carrier.
Assign one class in this order:

1. `MULTI_CARRIER_CONJUNCTION`: no single exposed carrier covers all missing
   identities.
2. `WRONG_FROZEN_MEMBER`: a single required member differs from the frozen
   member and fits at its varint arrival state.
3. `INITIAL_VARINT_SIZE`: required materialization does not fit immediately
   after the immutable DA-028 sequence is varint encoded.
4. `PRIOR_VARINT_CONSUMPTION`: it fits at that initial state but not at frozen
   arrival after earlier DA-031 additions.
5. `RETAINED_CODEC_NO_TAIL`: DA-031 retained DA-028 and ran no varint tail.
6. `UNACCOUNTED`: none of the above.

Also record whether the required member fits after the complete DA-031 pack.
This `postpack_fits` field is diagnostic and does not change class order.

## 4. Gates and Reporting

Require exact hashes and joins, 3/39 cardinality, complete exposed-union
coverage, exact varint cost replay, one class per item, zero unaccounted cases,
byte-identical audit replay and zero calls.

Report class counts, initial/arrival/postpack fit counts and cost/slack
distributions by corpus. Dominance requires >=60%. A shared successor requires
the same dominant class in both corpora. Diagnostic only; any intervention or
composition requires a new registration.
