# DA-096 Bound-Node Local Span Stream

**Status:** `COMPLETE; NO_BOUND_NODE_SPAN_CAPACITY_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-095 result commit `fdc3d907`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can DA-095's one-node dependency be represented more compactly by binding its
source node once and omitting the repeated source distance from every span?

## Frozen Representation

Use all 3,499 DA-095 selected children and reconstruct the committed node-local
parse. Emit one canonical header containing the immutable source-member distance.
Encode each retained reference thereafter as sentinel-delimited unsigned
`start,length`; literals remain exact. The bound source may not change.

Serialize and packetize with DA-093's fixed 1,800-character body and 2,048 frame
cap. Select bound-node encoding only when cumulative charge is strictly below
DA-095 and peak does not increase; otherwise retain DA-095 exactly. No target,
order, edge, source node, literal or referenced span may change.

## Gates And Disposition

Require exact wire parse and source-byte decode, exactly one bound source per
selected child, 3,499 exact joins, no expansion, unchanged protected controls,
byte-identical replay and zero calls.

Report `BOUND_NODE_SPAN_CAPACITY_SIGNAL` if at least 90% select the bound form
and selected median incremental cumulative savings versus DA-095 are >=1%.
Otherwise report `NO_BOUND_NODE_SPAN_CAPACITY_SIGNAL`.

This tests a compact dependency manifest, not reader use, delivery, runtime,
fresh transfer or adoption.

## Result

The bound form is smaller on 3,458/3,499 rows (98.83%), clearing the activity
bar, but incremental savings versus DA-095 are p10/p50/p90
0.44%/0.956%/2.13%. The median misses the registered 1% bar, so the disposition
is `NO_BOUND_NODE_SPAN_CAPACITY_SIGNAL` without rounding.

Absolute savings versus DA-091 literal streams are 3.09%/7.30%/16.54%, an
increment over DA-095's 2.50%/6.36%/14.83%. All selected rows bind one source;
exact decode, protected controls and byte-identical replay pass with zero calls.

The local coordinates save bytes, but the rendered source-binding header absorbs
enough of the gain to miss the bar. The next structural test moves that already
typed source identity to protected control-plane metadata and renders local spans
only.
