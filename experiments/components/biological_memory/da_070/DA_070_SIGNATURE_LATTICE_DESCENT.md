# DA-070 Signature-Lattice Descent

**Status:** `COMPLETE; SIGNATURE_LATTICE_DESCENT_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-069 result commit `b66ff68a`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can explicit subset edges preserve DA-069's efficient maximal addresses while
recovering needed nonmaximal sessions without flat unigram enumeration?

## Blind Graph And Stream

Freeze the complete sealed DA-069 stream as an immutable prefix. Reconstruct
each nonempty session signature with DA-069's exact query-token rule. Group
sessions with equal signatures in source order. Create a directed edge from
signature `A` to signature `B` iff `B` is a strict subset of `A` and no observed
signature `C` satisfies `B < C < A`. Thus edges are the exact Hasse diagram of
the observed inclusion poset.

Start from all inclusion-maximal signature nodes. Traverse the graph breadth
first. Order roots and each node's children by the minimum source-session order
in the signature group, then by the signature's query-order bit vector. Visit
each signature once. DA-069 already renders root groups, so append only
nonroot groups in traversal order.

For every appended session, reuse DA-069's shortest contiguous episode interval
covering its signature, followed by fixed radius-five endpoint neighborhoods.
Deduplicate episodes by first appearance. Empty signatures remain absent.

The graph is exact set inclusion, not a relevance score. There is no cardinality
ranking, cosine, IDF, threshold, fit, cap, outcome-dependent stopping, or
cross-session content edge. Expose one episode and one <=2,048-char frame at a
time; the DA-069 prefix cannot be reordered or mutated.

Seal all graphs and streams before answer markers. Require locked inputs,
correct cover edges on synthetic and real nodes, complete nonempty-node BFS,
prefix identity, positive edges/depth/nonroot additions, exact replay,
deduplication, zero payload mutation, leakage-clean source, and zero model,
embedding, or cache calls.

`SIGNATURE_LATTICE_DESCENT_SIGNAL` requires complete required-episode
reachability >=.98, zero protected-payload mutations, and median added episodes
through completion among DA-066-incomplete questions <62. Otherwise report
`NO_SIGNATURE_LATTICE_DESCENT_SIGNAL`.

Reachability is not delivery. Reader recognition, stopping, overflow chunk
reconstruction, runtime, fresh transfer, and adoption remain untested.

## Result

Exact lattice descent reaches 465/465 required-episode sets with zero payload
mutation. For DA-066's 27 residual questions, added episodes through completion
fall from the flat unigram reference p50 62 to 37, passing the efficiency bar;
p90 is 113.6. Full stream size remains p50 228 because exhaustive descent is
still broad, but graph order materially improves work-to-target. The result
supports explicit dependency edges and replaceable traversal, not reader use
or stopping.

Posthoc depth audit: the 35 episodes missing from DA-066 occupy signature depth
0:11, 1:11, 2:8, and 3:5; none require depths 4-7. Question-level maximum depth
is 0/1/2 for eight questions each and 3 for three. A depth-three replay is
eligible only as posthoc burden characterization because the cutoff was opened
from these outcomes.
