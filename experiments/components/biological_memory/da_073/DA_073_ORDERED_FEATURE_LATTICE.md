# DA-073 Ordered-Feature Signature Lattice

**Status:** `COMPLETE; NO_ORDERED_FEATURE_LATTICE_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-072 result commit `97ae81a2`
**Control prefix:** sealed DA-066
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can exact local word order enrich lattice identity enough to split session
collisions and reduce branch work without introducing a relevance score?

## Blind Features And Graph

Freeze the complete DA-066 episode stream as an immutable prefix. Build the
query feature universe from:

- unique lowercase unigram tokens in first-appearance order; and
- unique adjacent lowercase query bigrams in first-appearance order.

Prefix feature identities by type so unigrams and bigrams cannot collide. For
each accepted episode, record query unigrams occurring in its token set and
query bigrams occurring as exact adjacency inside that episode; never bridge
episode boundaries. A session signature is the union of its episode features.

Group equal signatures, construct the exact Hasse diagram under strict set
inclusion, and breadth-first traverse from maximal nodes using DA-070's source
order and feature-bit-vector tie break. For every session in traversal order,
emit its shortest contiguous episode interval covering its full ordered-feature
signature, then fixed radius-five endpoint neighborhoods. Deduplicate episodes
by first appearance.

Set membership and exact adjacency are structural. There is no cardinality
ranking, cosine, IDF, weight, threshold, fit, cap, outcome-dependent stopping,
or cross-session content edge. Expose one episode and one <=2,048-char frame at
a time; the DA-066 prefix cannot be reordered or mutated.

Seal all graphs and streams before answer markers and DA-072 target-session
classes. Require locked inputs, exact feature replay, positive bigram features,
synthetic and real cover edges, complete nonempty-node BFS, prefix identity,
deduplication, zero payload mutation, leakage-clean source, and zero model,
embedding, or cache calls.

`ORDERED_FEATURE_LATTICE_SIGNAL` requires all three:

1. complete required-episode reachability >=.98;
2. median added episodes through completion among DA-066-incomplete questions
   <37, DA-070's reference; and
3. fewer than 16 DA-072 target sessions in equal-signature collisions.

Otherwise report `NO_ORDERED_FEATURE_LATTICE_SIGNAL`. Reachability is not
delivery. Reader recognition, stopping, runtime, transfer, and adoption remain
untested.

## Result

Ordered features preserve 465/465 reachability and reduce DA-072 target-session
collisions 16->13, but gain-only median added episodes is 38 versus the required
`<37`; p90 is 130.4. Median full stream remains 228. Exact adjacency improves
node identity but worsens central work by one episode, so the combined bar
fails. The next structural probe role-types exact occurrences to represent
source provenance rather than adding more lexical specificity.
