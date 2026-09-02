# DA-087 Anchored Edge Slices

**Status:** `COMPLETE; ANCHORED_EDGE_SLICE_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-086 result commit `c3675f88`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can every orphan dependency be rendered as a short stream of self-contained
edge slices, each simultaneously carrying parent endpoint, assistant context,
and required child, without changing DA-078?

## Fixed Codec

Use the five sealed DA-086 bridges. Split the exact parent assistant text into
consecutive 1,200-character chunks. For each chunk render one canonical frame
containing, in order: exact parent user member, exact assistant chunk with
one-based index/total, and exact required child member. Repeat both endpoints in
every frame. Retain the typed parent-to-child edge and direction unchanged.

Concatenated assistant chunks must decode byte-for-byte to source. Every frame
must be <=2,048 characters and replaces the previous frame. Do not emit separate
endpoint frames, tune chunk size, summarize, compress, reorder, score, inspect
answers, or retry.

`ANCHORED_EDGE_SLICE_SIGNAL` requires 5/5 exact complete bridges, zero DA-078
mutation, and every frame within cap. Report frame count, peak/cumulative chars,
and contrasts with DA-085/086.

This is structural exposure only. Require byte-identical replay and zero model,
embedding, and cache calls. No reader, retention, stopping, transfer, delivery,
runtime, or adoption claim.

## Result

All 5/5 orphan bridges decode completely as self-contained edge slices with
zero DA-078 mutation. Bridges use p50 two and p90 three frames, down one to two
frames from DA-086. Peak frame characters are p50 1,771 and p90 1,946.4;
cumulative characters are p50 3,362 and p90 5,473.8.

Repeating endpoints costs p50 306 characters versus DA-086 and 571 versus
DA-085, but each frame now includes exact parent user, assistant context chunk,
required child, direction, and edge identity simultaneously. This is the
strongest structural orphan representation so far. Replay is byte-identical;
zero calls.

Artifacts:

- `artifacts/analysis/result.json`
- `artifacts/analysis/slices.jsonl.gz`
