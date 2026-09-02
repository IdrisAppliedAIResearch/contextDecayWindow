# DA-036 Report

## Verdict

`DOMINANT_INITIAL_ATOMIC_SIZE`

The exact 28 LongMem one-hop-reachable misses remaining after DA-033 were
replayed and exhaustively classified. Eighteen are too large before the atomic
tail starts, nine fit at that boundary but are blocked after earlier blind
atomic additions, and one requires multiple carriers. No case is unaccounted.

## Capacity Boundary

The protected pack has median initial slack 87.5 characters and median final
slack 23 characters. The median finite missing-member cost is 253 characters.
No remaining required member fits after the complete DA-033 pack.

This rules out another carrier score as the primary next step. The dominant
constraint is exact representation capacity. A successor may strengthen the
codec while preserving the selected order, then append only fitting
evidence-blind atomic members. It may not substitute against protected content.

The classification artifact replays byte-identically at
`9e5fff17f02a5576593c84629b2c2d73641485d645609e02301ec56f2b3b94ef`.
Model, embedding and cache calls: zero.
