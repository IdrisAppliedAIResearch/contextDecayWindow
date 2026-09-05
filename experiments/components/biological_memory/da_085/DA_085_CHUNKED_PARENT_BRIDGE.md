# DA-085 Exact Chunked Parent Bridge

**Status:** `COMPLETE; CHUNKED_PARENT_BRIDGE_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-084 result commit `3d4e21a3`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can exact chunking fully materialize every orphan parent-to-child chain within
replaceable 2,048-character frames while leaving DA-078 untouched?

## Fixed Codec And Sequence

Use the five sealed DA-084 bridges. Preserve parent and child identities, role
order, source text, direction, and typed edge. Emit parent member 0 as DA-044's
canonical block. Split parent member 1 into consecutive 1,900-character source
chunks, preserving every character. Encode each chunk with sentinel, episode
role, one-based chunk index, total chunks, and exact payload. Then emit the
required child as a canonical DA-044 block.

Every frame replaces the prior frame. Require each frame <=2,048 characters;
concatenated decoded parent chunks must equal the source assistant text byte for
byte. No alternate chunk size, semantic boundary, compression, score, answer,
retry, or member reorder is allowed.

Report complete bridge count, frame count, peak/cumulative characters, and
parent feature state inherited from DA-084. `CHUNKED_PARENT_BRIDGE_SIGNAL`
requires 5/5 complete bridges, zero DA-078 mutation, and exact decode.

This is structural exposure only. Require byte-identical replay and zero model,
embedding, and cache calls. No reader, retention, stopping, transfer, delivery,
runtime, or adoption claim.

## Result

All 5/5 orphan bridges decode completely with zero DA-078 mutation. Every
assistant requires exactly two chunks, yielding four frames per bridge: parent
user, two assistant chunks, and required child. Peak frame characters are p50
1,916 and p90 1,919.2; cumulative characters are p50 2,804 and p90 3,984.6.

The codec removes the representation overflow while preserving every source
character, role, identity, edge, and order. It does not solve cross-frame
retention or recognition. A smaller simultaneous endpoint frame is now
mechanically plausible because parent user plus required child are both short.
Replay is byte-identical; zero calls.

Artifacts:

- `artifacts/analysis/result.json`
- `artifacts/analysis/bridges.jsonl.gz`
