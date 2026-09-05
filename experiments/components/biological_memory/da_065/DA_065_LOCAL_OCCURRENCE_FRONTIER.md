# DA-065 Local Occurrence Frontier

**Status:** `COMPLETE; NO_LOCAL_OCCURRENCE_FRONTIER_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-064 result commit `dc5eb16c`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Do exact lexical occurrences identify the local neighborhood of an evidence
dependency even when they do not identify the evidence episode itself?

## Blind Stream

Preserve DA-064's immutable represented-episode prefix. For each adjacent query
bigram in query order and each exact occurrence episode in source order, emit
the occurrence, then its same-session episode neighbors in the fixed order
`previous 1, next 1, previous 2, next 2, ... previous 5, next 5`. Reject
session-boundary coordinates and deduplicate episodes by first appearance.

Radius five is frozen from the previously characterized DA-048/050 local
continuation range; it is not fitted here. There is no score, rerank, threshold,
fallback, cap, outcome-dependent stopping, or crossing between sessions.

Expose one episode and one <=2,048-char member frame at a time. Replacement of
the current item cannot change the immutable DA-038 payload or retained frames.
Seal all 465 streams before opening episode answer markers. Require locked
inputs, exact coordinates, prefix identity, deterministic replay, positive
anchors and boundary rejections, deduplication, zero protected-payload mutation,
leakage-clean source, and zero model, embedding, or cache calls.

`LOCAL_OCCURRENCE_FRONTIER_SIGNAL` requires complete required-episode
reachability >=.90 with zero protected-payload mutations. Otherwise report
`NO_LOCAL_OCCURRENCE_FRONTIER_SIGNAL`. Report first/last required position,
additional episodes, and stream size regardless.

Reachability is not delivery. Reader recognition, stopping, overflow chunk
reconstruction, runtime, fresh transfer, and adoption remain untested.

## Result

Complete required-episode reachability rises from DA-064's 382 to 416/465
(.8946), narrowly below the registered .90 bar; any is 449. Last required
position is p50 24.5/p90 129, with zero displacement. Residual audit finds 72
missing episodes: 35 in unreachable sessions and 37 in reachable sessions with
no lexical anchor; none are beyond radius five. Larger radius is closed. The
next structural edge expands around immutable pack episodes themselves.
