# DA-095 Exact Node-Local Child Stream

**Status:** `COMPLETE; NODE_LOCAL_CHILD_CAPACITY_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-094 result commit `58e3aef0`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can a child retain useful exact capacity while depending on only one immutable
prompt node rather than DA-093's fragmented 24-member median topology?

## Frozen Transformation

Use all 3,499 DA-093 selected children and reconstruct their committed optimal
parse. Sum referenced characters by prior prompt member. Select the member with
the largest sum, breaking ties by lowest immutable history index. Retain only
references to that member; replace every other reference with its exact source
substring and merge adjacent literals.

Serialize and packetize with DA-093's exact wire format. Select the node-local
form only when it is strictly smaller cumulatively than the corresponding
DA-091 literal stream and does not increase peak frame charge. Otherwise retain
DA-091. DA-093 remains the strongest capacity control and is not mutated.

## Gates And Disposition

Require exact source decode, at most one referenced prompt member, 3,499 exact
joins, no expansion, unchanged target/order/edge, unchanged noneligible rows,
zero DA-078/DA-091/DA-093 mutation, byte-identical replay and zero calls.

Report `NODE_LOCAL_CHILD_CAPACITY_SIGNAL` if at least 20% select node-local
encoding and selected median cumulative savings versus DA-091 are >=5%.
Otherwise report `NO_NODE_LOCAL_CHILD_CAPACITY_SIGNAL`.

This is reversible representation capacity and topology only. No reader,
delivery, runtime, fresh-transfer or adoption claim.

## Result

All 3,499 children selected the exact node-local form. Savings against DA-091
literal streams are p10/p50/p90 2.50%/6.36%/14.83%, clearing both registered
bars. The node-local form retains p10/p50/p90 15.78%/27.87%/50.81% of DA-093's
larger but fragmented capacity gain.

Pointer count falls from DA-094's p50 123 to 25, with p10/p90 12/46, and every
child references exactly one immutable prompt member. Exact decode,
byte-identical replay and all protection gates pass with zero calls.

This establishes a sparse node dependency at a measurable capacity gain. Its
wire format still repeats the same source-member distance in every pointer; the
next structural opportunity is a one-time node binding followed by local span
coordinates.
