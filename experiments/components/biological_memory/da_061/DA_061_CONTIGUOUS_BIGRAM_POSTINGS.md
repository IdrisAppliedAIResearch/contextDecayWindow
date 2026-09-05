# DA-061 Exact Contiguous Bigram Session Postings

**Status:** `COMPLETE; NO_CONTIGUOUS_BIGRAM_SESSION_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-060 result commit `cbd510b7`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can phrase-order structure make exact session postings selective while retaining
useful required-session coverage?

## Blind Route

Tokenize with DA-059 lowercase `[A-Za-z0-9]+`, preserving duplicates and source
order for this study. Generate adjacent query bigrams `(t_i,t_{i+1})` in order.
A session posting exists only when that exact adjacent bigram occurs in the
ordered token stream of its accepted user/assistant episode text. Do not bridge
episode boundaries.

Traverse bigram postings in query order and session source order, appending
unseen heads. There is no unigram/pair fallback, score, weight, threshold,
reranking, fitted parameter, or cap.

Seal all 465 routes before evidence. Require canonical ordered bigrams,
deterministic postings and deduplication, exact replay, positive matched and
unmatched populations, leakage-clean source, zero payload mutation, and zero
model/embedding/cache calls.

After sealing, report complete/any required-session coverage and route burden.
Selective requires complete coverage >=.90 and p50 routed fraction <=.25; broad
requires coverage >=.90; otherwise `NO_CONTIGUOUS_BIGRAM_SESSION_SIGNAL`.

Coverage is not delivery. Reader use, stopping, runtime, transfer, and adoption
remain untested.

## Result

Contiguous bigrams cover every required session for 401/465 questions (.862),
below the registered .90 bar, while routing p50 21 sessions and .447 of each
corpus. Any coverage is 432/465. Word order reduces DA-060's broad route but
does not yield a sufficiently selective, reliable substitution gate. The
strongest payload order remains immutable.
