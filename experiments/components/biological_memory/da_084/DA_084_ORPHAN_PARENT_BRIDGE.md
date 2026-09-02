# DA-084 Orphan Parent-to-Child Bridge

**Status:** `POSTHOC_ORPHAN_PARENT_BRIDGE_CHARACTERIZED`
**Date:** August 31, 2026
**Parent:** DA-083 result commit `69769d4b`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can the five orphan-parent residuals be represented as a bounded transient
parent-to-child chain without modifying or displacing DA-078?

## Fixed Bridge

Use the five sealed DA-083 `ORPHAN_PARENT` rows. Resolve each target's unique
frozen baseline seed as its parent. Emit exactly three replaceable attempts in
order: parent member 0, parent member 1, then the required child member. Render
each with DA-044's canonical block and a local ordinal 1-3. Admit a frame only
when its exact block is <=2,048 characters; continue after overflow.

Store one typed out-of-band edge containing parent episode identity, child
episode identity, required child member, and direction from the frozen baseline
action. It adds no rendered characters and carries no source text or score.

Report parent-member exposure, child exposure, peak/cumulative characters, and
whether parent members add DA-074 exact role/query features relative to the
immutable DA-078 prompt. Classify complete, partial, or absent parent bridge.
No alternate member order, score, threshold, answer text, or retry is allowed.

Require exact five-row joins, canonical decode, unchanged DA-078, byte-identical
replay, and zero model, embedding, and cache calls. Exposure and provenance are
not reader recognition, retention, stopping, transfer, delivery, or adoption.

## Result

All five orphan rows are `PARTIAL_PARENT_BRIDGE`. The parent user member and
required child fit in every case, but the parent assistant member overflows in
all five. User blocks cost 148-325 characters; assistant blocks cost
2,215-3,304; child blocks cost 228-426. Peak admitted frame p50 is 284 and
cumulative admitted characters p50 539, with zero DA-078 mutation.

Exposed parent members add zero DA-074 query features relative to DA-078 in all
five cases, including the two previously uncovered rows. Parent provenance is
mechanically available but creates no lexical stop. The isolated boundary is
oversized parent-assistant representation. Byte-identical replay; zero calls.

Artifacts:

- `artifacts/analysis/result.json`
- `artifacts/analysis/bridges.jsonl.gz`
