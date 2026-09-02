# DA-066 Dual-Anchor Local Frontier

**Status:** `COMPLETE; DUAL_ANCHOR_LOCAL_FRONTIER_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-065 result commit `c818dbd9`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can immutable represented episodes serve as structural dependency anchors for
sessions where the query has no exact lexical occurrence?

## Blind Stream

Preserve every DA-064 represented episode as one contiguous immutable prefix.
After the prefix, visit those represented episodes again in prefix order and
emit their same-session neighbors in fixed order `previous 1, next 1, ...
previous 5, next 5`. Then process DA-065's exact-bigram occurrence anchors in
query and source order, emitting each anchor and the same radius-five neighbor
order. Deduplicate all episodes by first appearance and reject session-boundary
coordinates.

Radius and direction order are inherited unchanged from DA-065. There is no
score, rerank, threshold, fit, fallback, cap, outcome-dependent stopping, or
cross-session edge. Pack-anchor expansion occurs before lexical-anchor
expansion because the represented prefix is the protected strongest order.

Expose one episode and one <=2,048-char member frame at a time. Replacement of
the current item cannot mutate the immutable DA-038 payload or retained frames.
Seal all 465 streams before opening episode answer markers. Require locked
inputs, exact coordinates, contiguous prefix identity, deterministic replay,
positive pack and lexical anchor populations, boundary rejection,
deduplication, zero payload mutation, leakage-clean source, and zero model,
embedding, or cache calls.

`DUAL_ANCHOR_LOCAL_FRONTIER_SIGNAL` requires complete required-episode
reachability >=.90 with zero protected-payload mutations. Otherwise report
`NO_DUAL_ANCHOR_LOCAL_FRONTIER_SIGNAL`. Report completion positions, added
episodes, and stream size regardless.

Reachability is not delivery. Reader recognition, stopping, overflow chunk
reconstruction, runtime, fresh transfer, and adoption remain untested.

## Result

Dual anchors raise complete required-episode reachability from 416 to 438/465
(.942), passing the .90 bar with zero payload mutations; any is 458. Last
required position is p50 21/p90 78.3. Residual accounting is exact: all 35
missing episodes across 27 questions are in sessions absent from DA-063; zero
misses remain inside a reached session. Local dependency representation is
complete conditional on head reachability. Next is hierarchical unigram head
and occurrence fallback after the full protected DA-066 order.
