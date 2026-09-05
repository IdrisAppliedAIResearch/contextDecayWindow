# DA-059 Sparse Session Posting Index

**Status:** `COMPLETE; BROAD_SPARSE_SESSION_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-058 result commit `fab65084`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can exact symbolic postings route a question to the right DA-055 session heads
without a model, embedding, similarity score, or evidence label?

## Blind Index And Route

Use DA-013's frozen token family: lowercase `[A-Za-z0-9]+`. For each question,
index every source session by the set of tokens in all accepted user/assistant
episode text. A posting list contains session heads in corpus source order.

Tokenize the question and keep unique tokens in first-appearance order. Traverse
each token's posting list in that order and append unseen session heads. The
route is the exact union traversal; there is no count, weight, IDF, threshold,
similarity, fitted coefficient, reranking, or cap.

The blind artifact stores query tokens, matched tokens, ordered routed heads,
and total sessions. It reads no answer flag, evidence identity, outcome, prior
measurement, model output, or embedding.

## Gates And Audit

Seal all 465 routes before evidence. Require locked corpus/directory, canonical
tokens, source-order postings, deterministic deduplication, exact replay,
positive matched/unmatched tokens, positive empty/nonempty routes if present,
zero payload mutation, and zero calls.

After sealing, map exact evidence members to required session heads. Report
complete required-session coverage, any-session coverage, routed-session count
and fraction, first/last required rank, and question type.

Report `SELECTIVE_SPARSE_SESSION_SIGNAL` if complete required-session coverage
is >=.90 and routed-session fraction p50 <=.25; `BROAD_SPARSE_SESSION_SIGNAL` if
coverage is >=.90 without selectivity; otherwise `NO_SPARSE_SESSION_SIGNAL`.

Posting coverage is not reader delivery. Materialization, recognition, stopping,
fresh transfer, runtime, and adoption remain untested.

## Result

Exact token union covers all required sessions for 465/465 questions, but routes
p50 44 sessions and p50 .918 of each corpus. First required rank is p50 13 and
last p50 28. This is control-plane flooding, not selective routing. Singleton
union closes; exact token-pair postings are next.
