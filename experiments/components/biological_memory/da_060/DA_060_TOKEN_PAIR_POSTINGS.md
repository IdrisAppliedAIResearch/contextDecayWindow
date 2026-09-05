# DA-060 Exact Token-Pair Session Postings

**Status:** `COMPLETE; BROAD_TOKEN_PAIR_SESSION_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-059 result commit `0c61ef00`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Does requiring exact co-occurrence of two query tokens make the session directory
selective without destroying required-session addressability?

## Blind Route

Reuse DA-059 lowercase `[A-Za-z0-9]+` unique query tokens in first-appearance
order. Generate every unordered query pair `(i,j)` with `i<j` in nested query
order. A session posting exists when both tokens occur anywhere in that source
session's accepted episode text.

Traverse pair postings in query-pair order and session source order, appending
unseen session heads. There is no singleton fallback, score, count, weight, IDF,
threshold, fitted parameter, reranking, or cap.

Seal pair keys, matched/unmatched pairs, and routed heads for all 465 questions
before evidence. Require locked inputs, canonical pair order, deterministic
deduplication, exact replay, positive matched/unmatched and empty/nonempty route
populations if present, zero payload mutation, leakage-clean source, and zero
model/embedding/cache calls.

After sealing, report complete and any required-session coverage, routed count
and fraction, and required ranks. Use DA-059's dispositions: selective requires
coverage >=.90 and p50 fraction <=.25; broad requires coverage >=.90; otherwise
`NO_TOKEN_PAIR_SESSION_SIGNAL`.

Coverage is not delivery. Reader use, stopping, runtime, fresh transfer, and
adoption remain untested.

## Result

Pair postings preserve complete required-session coverage 465/465 but route
p50 43 sessions and p50 .909 of each corpus. DA-059 singleton union routed 44
and .918. First/last required ranks remain p50 13/24. Unordered pair
co-occurrence is still broad; exact contiguous bigram postings are next.
