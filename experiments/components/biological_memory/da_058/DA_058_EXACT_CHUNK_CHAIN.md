# DA-058 Exact Member Chunk Chain

**Status:** `COMPLETE; EXACT_CHUNK_CAPACITY_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-057 result commit `500f8c7e`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can oversized exact members be reconstructed from multiple bounded retained
frames without increasing frame capacity or displacing prior evidence?

## Blind Codec

Freeze DA-056 source-member coordinates and five-slot retained semantics. For
each member whose canonical frame exceeds 2,048 characters, split source text
into consecutive 1,984-character chunks. The 64-character reserve is fixed from
the frame cap before outcomes and covers the typed self-delimiting header.

Render each chunk as a canonical typed frame containing chunk ordinal, total
chunks, role, and exact contiguous text. Fitting members retain the unchanged
DA-056 frame. Decode by requiring one coordinate, complete ordinals `1..n`,
matching total/role, then concatenating chunks. No overlap, gap, reordering,
summary, or content change is permitted.

The choice is mechanical: literal when it fits, otherwise exact chunk chain.
It reads no question, answer flag, evidence, score, similarity, feature, model
output, or outcome.

## Gates And Outcome

Seal all 212,824 member decisions before residual evidence. Require exact decode,
every chunk <=2,048, canonical order, positive chunked/fitting populations,
byte-identical replay, and zero calls.

After sealing, append all chunks for each DA-057 residual member to the protected
retained set. Prior frames remain immutable. Report complete availability over
459, chunks/member, retained slots/chars and peak capacity. `EXACT_CHUNK_CAPACITY_SIGNAL`
requires >=3 gains, zero losses, <=5 total slots, <=12,288 peak, and all types
nonnegative.

Reader reconstruction, session-head choice, stopping, runtime, fresh transfer,
and adoption remain untested.

## Result

The exact chunk chain raises complete availability 459->465: 6 gains, zero
losses, p=.03125, reaching the full 465-item mechanical ceiling. Every residual
uses two chunks; total retained slots are 2-3, retained/peak chars p50 2,814 and
max 3,111. Capacity is solved mechanically; head choice and reader reconstruction
remain untested.
