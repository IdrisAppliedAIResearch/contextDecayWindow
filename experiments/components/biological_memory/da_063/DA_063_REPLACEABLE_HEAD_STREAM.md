# DA-063 Replaceable Session-Head Stream

**Status:** `POSTHOC_REPLACEABLE_HEAD_STREAM_CHARACTERIZED`
**Date:** August 31, 2026
**Parents:** DA-061 and DA-062
**Planned embedding calls:** 0
**Planned model calls:** 0

## Scope

DA-062's pack-activated frontier is narrow but incomplete. Posthoc synthesis
already established that union with DA-061 reaches 438/465 and is broad when
simultaneous. Consequently this study has no inferential disposition and cannot
rescue either parent. It measures whether the known union has a bounded-peak
structural representation.

## Deterministic Stream

For each question, emit DA-062 pack-activated session heads in sealed order,
then append unseen DA-061 contiguous-bigram heads in sealed order. Deduplicate
by first appearance. There is no reranking, score, threshold, fit, cap, or
outcome-dependent stopping.

Use the sealed DA-055 directory only to attach each emitted head's episode and
member counts. These counts do not affect order, admission, or stopping.

The stream exposes one head at a time. Opening a new head replaces the prior
current head and current session-local frame; it never changes the immutable
DA-038 payload or any retained frame. Charge one current DA-056 frame at its
registered maximum 2,048 chars. Do not simultaneously render the head list or
session payloads.

Seal the composed stream before measuring required-session positions. Verify
parent hashes, prefix identity with DA-062, exact replay, first-appearance
deduplication, zero payload mutation, and zero model, embedding, or cache calls.

Report reachable questions, additional streamed heads required through the
last required session, total heads examined, and cumulative episode/member
traversal burden through that position.
This is address exposure only. Reader recognition, stopping, delivered
evidence, runtime, fresh transfer, and adoption remain untested.

## Result

The stream reaches every required session for 438/465 questions (.942) while
holding one head and one <=2,048-char current frame; protected payload mutations
remain zero. Last required head is p50 3/p90 14.3. Additional heads beyond the
pack prefix are p50 0/p90 6. Cumulative traversal through completion is p50 32
members and p90 168, so peak capacity is solved but scanning remains expensive.
