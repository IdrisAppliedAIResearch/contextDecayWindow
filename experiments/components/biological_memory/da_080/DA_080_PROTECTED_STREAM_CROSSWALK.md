# DA-080 Protected Stream Crosswalk

**Status:** `PROTECTED_STREAM_CROSSWALK_COMPLETE`
**Date:** August 31, 2026
**Parent:** DA-079 result commit `06c918e2`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Do DA-079's 13 residual dependencies already have exact bounded-frame
materializations in the sealed DA-045 replaceable stream, allowing the stronger
DA-078 prompt to remain fully immutable?

## Fixed Crosswalk

Join the 13 sealed DA-079 rows to DA-045's 18 sealed exposure rows by question
identity. Do not rebuild, reorder, rescore, truncate, or reinterpret either
artifact. Require exact 13/13 joins and `exposed=true` to count a structural
materialization.

Report exposed count, frame count, cumulative characters through requirement,
peak frame characters, and DA-079 blocker cells. DA-078 remains byte-for-byte
untouched because DA-045 frames are separate replaceable capacity.

This is architecture convergence only. Exposure is not reader recognition,
retention, stopping, or answer use. Byte-identical replay and zero model,
embedding, and cache calls are required.

## Result

All 13/13 DA-079 residuals join to exact DA-045 materializations. Every
requirement is one node and no DA-078 payload is mutated. Peak frame characters
are p50 1,968 and p90 2,040.6, within the sealed 2,048 frame bound.

The unresolved burden is sequential: frames through requirement are p50 13 and
p90 16; cumulative exposed characters are p50 5,781 and p90 19,264.2. Thus
separate replaceable capacity structurally exposes every remaining dependency,
but an effective reader must recognize relevance, retain the node, and stop.

Replay is byte-identical; model, embedding, and cache calls are zero.

Artifacts:

- `artifacts/analysis/result.json`
- `artifacts/analysis/crosswalk.jsonl.gz`
