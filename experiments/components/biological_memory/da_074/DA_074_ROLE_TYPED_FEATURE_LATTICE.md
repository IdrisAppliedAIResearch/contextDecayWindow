# DA-074 Role-Typed Feature Lattice

**Status:** `COMPLETE; ROLE_TYPED_FEATURE_LATTICE_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-073 result commit `f56fd36e`
**Control prefix:** sealed DA-066
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can exact speaker provenance distinguish otherwise colliding sessions and
improve graph traversal without a relevance score?

## Blind Features And Graph

Freeze the complete DA-066 stream as an immutable prefix. Retain all DA-073
untyped exact unigram and adjacent-bigram features. Augment them with typed
copies for each occurrence:

- `USER_UNIGRAM` and `ASSISTANT_UNIGRAM`; and
- `USER_BIGRAM` and `ASSISTANT_BIGRAM`.

Typed features use the same query unigram/bigram universe. Detect typed features
inside the corresponding source member only; typed bigrams cannot cross the
user/assistant boundary. DA-073's untyped episode bigrams retain their existing
within-episode behavior.

Union episode features into session signatures. Group equal signatures, build
the exact Hasse diagram, and use DA-073's maximal-root BFS, source-order and
feature-bit-vector tie break. Emit each session's shortest contiguous interval
covering its complete augmented signature, then fixed radius-five endpoint
neighborhoods. Deduplicate episodes by first appearance.

Role provenance and exact adjacency are structural. There is no cardinality
ranking, cosine, IDF, weighting, threshold, fit, cap, outcome-dependent
stopping, or cross-session content edge. Expose one episode and one <=2,048-char
frame at a time; the DA-066 prefix cannot be reordered or mutated.

Seal graphs and streams before answer markers and DA-072 target classes.
Require locked inputs, exact typed-feature replay, positive features for all
four typed families, synthetic and real cover edges, complete BFS, prefix
identity, deduplication, zero mutation, leakage-clean source, and zero model,
embedding, or cache calls.

`ROLE_TYPED_FEATURE_LATTICE_SIGNAL` requires all three:

1. complete required-episode reachability >=.98;
2. median added episodes through completion among DA-066-incomplete questions
   <37; and
3. fewer than 13 DA-072 target-session collisions, DA-073's reference.

Otherwise report `NO_ROLE_TYPED_FEATURE_LATTICE_SIGNAL`. Reachability is not
delivery. Reader recognition, stopping, runtime, transfer, and adoption remain
untested.

## Result

Role provenance passes all bars: complete required-episode reachability is
465/465 with zero displacement; DA-066 residual median additions fall from
DA-070's 37 to 31 (p90 114.6); and DA-072 target-session collisions fall from
DA-073's 13 to 5. Median full stream remains 228 episodes. Exact user/assistant
provenance improves both identity and central work, but exhaustive traversal is
still broad. Next audit the remaining collisions and role-lattice branch depth.
