# DA-056 Session-Local Materialization

**Status:** `COMPLETE; SESSION_LOCAL_CAPACITY_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-055 result commit `7bee9b67`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Once a session head is known, can exact local dereference materialize and retain
distributed residual evidence without changing the strongest payload?

## Blind Contract

Freeze the DA-055 directory and DA-052 five-slot retained-set semantics. Define
`OPEN_SESSION(head)`, `NEXT_EPISODE`, `MATERIALIZE(member_offset)`, `KEEP`, and
`ANSWER`. Opening sets a control-plane cursor and renders no payload. Episode
movement follows exact `next` pointers only. Materialization resolves one source
member and renders DA-044's canonical frame into replaceable `current`.

Each current/retained frame is capped at 2,048 characters; at most five retained
frames, retained cap 10,240, total auxiliary cap 12,288. Overflow rejects
materialization without mutating cursor or retained state. No prompt or prior
stream changes. Admission reads only typed handles, pointers, offsets, hashes,
frame cost, and free slots; no question, evidence, score, similarity, or model.

## Gates And Oracle Audit

Seal transition ledgers and exact member rendering before evidence. Exercise
unknown head, session boundary, bad offset, overflow, duplicate, full set, and
retained survival. Require exact replay, zero payload mutation, and zero calls.

After sealing, an evidence-aware oracle may open the DA-055 coordinate for each
DA-052 residual member, traverse locally, materialize, and retain up to five
frames. Report complete availability over DA-052=363, gains/losses, frame count,
pointer hops, payload and peak capacity. `SESSION_LOCAL_CAPACITY_SIGNAL` requires
>=20 gains, zero losses, all types nonnegative, and cap compliance.

Head selection is oracle-only. Recognition, session choice, stopping, reader
use, runtime, fresh transfer, and adoption remain untested.

## Result

Session-local oracle materialization raises complete availability 363->459:
96 gains, zero losses, p=2.52e-29. Gains use one/two/three new frames in
68/23/5 rows; sessions opened p50 1, pointer hops p50 4, retained chars p50
409.5, peak p50 2,029.5. Six questions remain, all exact-member overflow.
