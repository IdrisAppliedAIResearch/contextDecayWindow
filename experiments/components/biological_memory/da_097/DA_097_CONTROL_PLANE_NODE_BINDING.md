# DA-097 Control-Plane Node Binding

**Status:** `REGISTERED; DEFERRED BY USER PIVOT`
**Date:** August 31, 2026
**Parent:** DA-096 result commit `e7ad107e`
**Planned embedding calls:** 0
**Planned model calls:** 0

DA-097 was registered but not implemented or run. The user stopped incremental
codec work and authorized a frozen LoCoMo 16k/32k replay instead. No DA-097
result or inference exists.

## Question

Does separating deterministic source-node identity from rendered child payload
make the one-node dependency representation materially smaller than DA-095?

## Frozen Representation

Use all 3,499 DA-095 selected children and reconstruct the same node-local parse.
Place its immutable dominant source member in typed out-of-band metadata. Render
only exact literals and sentinel-delimited unsigned `start,length` spans. The
metadata is an address, not evidence, and carries zero prompt charge.

Packetize with DA-093's fixed 1,800-character body and 2,048 frame cap. Select
the control-plane-bound form only when cumulative charge is strictly below
DA-095 and peak does not increase; otherwise retain DA-095 exactly. No source,
span, target, edge, order or payload may change.

## Gates And Disposition

Require exact parse and source-byte decode using the typed binding, exactly one
source per selected child, 3,499 joins, no expansion, unchanged controls,
byte-identical replay and zero calls.

Report `CONTROL_PLANE_NODE_BINDING_SIGNAL` if at least 99% select and selected
median incremental cumulative savings versus DA-095 are >=1%. Otherwise report
`NO_CONTROL_PLANE_NODE_BINDING_SIGNAL`.

This tests payload/graph-metadata separation. Reader access to typed metadata,
delivery, runtime, fresh transfer and adoption remain untested.
