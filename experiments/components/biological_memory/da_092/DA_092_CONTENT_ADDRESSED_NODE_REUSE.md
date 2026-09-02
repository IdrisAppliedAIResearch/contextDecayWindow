# DA-092 Content-Addressed Exact Node Reuse

**Status:** `COMPLETE; NO_CONTENT_ADDRESSED_NODE_REUSE_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-091 result commit `2ee1d1ce`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Does the 8,055-target frontier repeatedly materialize identical child payloads
that can be stored once as exact content-addressed nodes, without changing the
strongest order or any per-question exposure?

## Frozen Population And Identity

Use all sealed DA-091 targets. Resolve each target's exact source member. Define
the node key as SHA-256 over UTF-8 `speaker`, one NUL byte, and exact `text`.
Reject any key collision with unequal speaker or text. Preserve question,
target, member, parent, direction, route, order and all DA-091 costs.

## Fixed Measurements

Report total references, unique exact nodes, reuse count and ratio, repeated
versus unique source characters, references and questions per node, and reuse by
DA-091 route. Verify every key resolves to byte-identical source content.

`CONTENT_ADDRESSED_NODE_REUSE_SIGNAL` requires at least 10% fewer unique nodes
than references and exact collision-free resolution. Otherwise report
`NO_CONTENT_ADDRESSED_NODE_REUSE_SIGNAL`.

This is shared-store architecture only. Do not count node reuse as prompt
capacity, evidence delivery or runtime savings. Reader fetch, cache residency,
latency, retention, fresh transfer and adoption remain untested. Require
byte-identical replay and zero calls.

## Result

The 8,055 references resolve to 7,659 unique exact nodes: 396 reused references,
or 4.92%, below the locked 10% bar. Exact shared storage removes 788,890 of
12,593,382 repeated source characters, a 6.26% reduction. Median and p90 reuse
are both one reference and one question per node; the maximum is four.

All hashes resolve collision-free to exact source bytes, DA-091 rows and
per-question exposure remain unchanged, replay is byte-identical and no calls
were made. Exact node identity remains a sound graph primitive, but corpus-level
deduplication is too sparse to be the next capacity mechanism.
