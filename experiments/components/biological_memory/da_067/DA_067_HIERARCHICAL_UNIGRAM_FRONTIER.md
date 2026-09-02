# DA-067 Hierarchical Unigram Frontier

**Status:** `COMPLETE; HIERARCHICAL_UNIGRAM_FRONTIER_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-066 result commit `b371a81a`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can a lower-specificity exact posting layer recover sessions absent from the
bigram frontier while preserving the entire stronger structural order?

## Blind Stream

Freeze the complete sealed DA-066 episode stream as an immutable prefix. Then
tokenize the query with DA-059's lowercase `[A-Za-z0-9]+` rule, deduplicating
tokens by first appearance. For each token in query order and each exact
occurrence episode in session/episode source order, emit the occurrence and its
same-session neighbors in fixed order `previous 1, next 1, ... previous 5,
next 5`. Deduplicate episodes by first appearance and reject session boundaries.

The unigram layer is strictly append-only after the stronger pack and bigram
frontier. It cannot reorder or replace any prior item. Radius and direction are
inherited from DA-065/066. There is no score, IDF, frequency threshold, rerank,
fit, cap, fallback within the layer, or outcome-dependent stopping.

Expose one episode and one <=2,048-char member frame at a time. Replacement of
the current item cannot mutate the DA-038 payload, retained frames, or DA-066
order. Seal all 465 streams before opening answer markers. Require locked
inputs, prefix identity, deterministic replay, positive unigram anchors and
new admissions, boundary rejection, deduplication, zero payload mutation,
leakage-clean source, and zero model, embedding, or cache calls.

`HIERARCHICAL_UNIGRAM_FRONTIER_SIGNAL` requires complete required-episode
reachability >=.98 with zero protected-payload mutations. Otherwise report
`NO_HIERARCHICAL_UNIGRAM_FRONTIER_SIGNAL`. Report completion positions,
additional episodes, total stream size, and cumulative expansion.

Reachability is not delivery. Reader recognition, stopping, overflow chunk
reconstruction, runtime, fresh transfer, and adoption remain untested.

## Result

The append-only unigram layer reaches 465/465 required-episode sets, passing
the .98 bar with zero displacement. Median stream size is 228 episodes. The 27
questions newly recovered beyond DA-066 require p50 62/p90 128 additional
episodes and finish at p50 position 158. Thus replaceable traversal removes the
simultaneous capacity ceiling but degenerates into cumulative flooding. The
next structural probe compresses pair postings into deterministic witness
interval coordinates rather than enumerating unigram neighborhoods.
