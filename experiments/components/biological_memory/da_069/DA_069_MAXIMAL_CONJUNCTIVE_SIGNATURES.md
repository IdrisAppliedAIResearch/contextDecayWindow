# DA-069 Maximal Conjunctive Session Signatures

**Status:** `COMPLETE; NO_MAXIMAL_CONJUNCTIVE_SIGNATURE_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-068 result commit `5adec9f8`
**Control prefix:** sealed DA-066
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can a logical inclusion lattice identify specific dependency-bearing sessions
without ranking them by a relevance score?

## Blind Stream

Freeze the complete DA-066 stream as an immutable prefix. Tokenize the query
with DA-059 unique lowercase tokens in first-appearance order. For each source
session, define its signature as the subset of query tokens occurring anywhere
in its accepted episodes. Exclude empty signatures. Retain a session iff no
other session has a strict superset signature. Equal signatures remain separate
sessions and preserve source order.

For each retained session, find the shortest contiguous episode interval whose
union contains every token in that session's signature. Break equal-width ties
by lower start then lower end. Emit every episode in the interval in source
order, then same-session neighbors around the interval endpoints in fixed order
`previous 1, next 1, ... previous 5, next 5`. Traverse retained sessions in
source order and deduplicate episodes by first appearance.

Set inclusion and shortest exact cover are structural operations, not fitted
scores. There is no cardinality ranking, cosine, IDF, frequency threshold,
rerank, fit, cap, fallback, outcome-dependent stopping, or cross-session edge.

Expose one episode and one <=2,048-char frame at a time. Seal all 465 streams
before answer markers. Require locked inputs, exact signature and interval
replay, prefix identity, positive strict-subset exclusions and equal-signature
retentions, boundary rejection, deduplication, zero payload mutation,
leakage-clean source, and zero model, embedding, or cache calls.

`MAXIMAL_CONJUNCTIVE_SIGNATURE_SIGNAL` requires complete required-episode
reachability >=.98, zero protected-payload mutations, and median added episodes
through completion among DA-066-incomplete questions <62. Otherwise report
`NO_MAXIMAL_CONJUNCTIVE_SIGNATURE_SIGNAL`.

Reachability is not delivery. Reader recognition, stopping, overflow chunk
reconstruction, runtime, fresh transfer, and adoption remain untested.

## Result

The maximal-signature frontier adds only 2,335 episodes and recovers 8 of
DA-066's 27 residual questions at median 1 added episode, but complete
reachability is 446/465 (.959), below .98. Median stream size is 141. Logical
specificity is highly efficient when the target session is maximal, but strict
subset pruning removes 19 needed sessions. The next structural probe preserves
this compact frontier and traverses explicit signature-subset edges rather than
restoring excluded sessions as a flat list.
