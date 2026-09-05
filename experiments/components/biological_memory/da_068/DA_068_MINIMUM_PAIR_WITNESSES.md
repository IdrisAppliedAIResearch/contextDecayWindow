# DA-068 Minimum Query-Pair Witnesses

**Status:** `COMPLETE; NO_MINIMUM_PAIR_WITNESS_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-067 result commit `b22a11f1`
**Control prefix:** sealed DA-066
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can exact pair postings identify a compact structural witness for an otherwise
unreached session, avoiding DA-067's unigram enumeration flood?

## Blind Stream

Freeze the complete DA-066 stream as an immutable prefix. Use DA-059 unique
query tokens in first-appearance order and DA-060 unordered pair order `(i,j)`
for `i<j`. For each pair and source session containing both tokens, enumerate
the episode orders containing each token. Select the pair of episode orders
with minimum absolute distance; break ties by lower interval start, then lower
end, then the first-token order, then second-token order.

Emit the selected witness endpoints in ascending episode order, then for each
endpoint emit same-session neighbors in fixed order `previous 1, next 1, ...
previous 5, next 5`. A same-episode witness emits one endpoint. Traverse pairs
in query order and sessions in source order. Deduplicate episodes by first
appearance and reject session boundaries.

The witness is a deterministic structural minimum, not a fitted relevance
score. DA-066 remains entirely first. There is no cosine, IDF, frequency
threshold, rerank, fit, cap, fallback, outcome-dependent stopping, or
cross-session edge.

Expose one episode and one <=2,048-char frame at a time. Seal all 465 streams
before answer markers. Require locked inputs, exact witness/tie replay, prefix
identity, positive same-episode and cross-episode witnesses, boundary rejection,
deduplication, zero payload mutation, leakage-clean source, and zero model,
embedding, or cache calls.

`MINIMUM_PAIR_WITNESS_SIGNAL` requires complete required-episode reachability
>=.98, zero protected-payload mutations, and median added episodes through
completion among DA-066-incomplete questions <62, DA-067's observed median.
Otherwise report `NO_MINIMUM_PAIR_WITNESS_SIGNAL`.

Reachability is not delivery. Reader recognition, stopping, overflow chunk
reconstruction, runtime, fresh transfer, and adoption remain untested.

## Result

Minimum pair witnesses retain 465/465 reachability and zero displacement, but
the 27 gain cases require median 62 additional episodes, exactly tying rather
than beating DA-067's registered reference. Their p90 is 125.4; median full
stream size is 227 versus DA-067's 228. Pair intervals remove one median stored
episode but do not reduce median work-to-target. The pair-witness family closes.
Next is a score-free maximal conjunctive session-signature representation.
