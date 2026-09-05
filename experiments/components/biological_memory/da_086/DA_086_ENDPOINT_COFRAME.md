# DA-086 Parent-Child Endpoint Coframe

**Status:** `COMPLETE; ENDPOINT_COFRAME_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-085 result commit `6dc77f08`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can the short parent user endpoint and required child be made simultaneously
visible in one bounded exact frame, reducing linked-edge retention burden without
mutating DA-078 or dropping the complete parent stream?

## Fixed Treatment

Use the five sealed complete DA-085 bridges. Preserve the parent user frame and
all parent assistant chunks exactly and in order. Replace only the final
child-only frame with one endpoint coframe containing an exact repeat of parent
member 0 followed by the exact required child member. Label payloads `PARENT`
and `CHILD`; retain the typed out-of-band edge unchanged.

Use a canonical sentinel header, direction, roles, and exact source text. Decode
both endpoints byte-for-byte. The coframe must be <=2,048 characters. No source
summary, compression, alternate endpoint, score, threshold, answer, or order
change is allowed.

`ENDPOINT_COFRAME_SIGNAL` requires 5/5 exact coframes, zero DA-078 mutation, and
all prior parent frames retained. Report frame/cumulative costs and incremental
cost over DA-085.

This is structural exposure only. Require byte-identical replay and zero model,
embedding, and cache calls. No reader, retention, stopping, transfer, delivery,
runtime, or adoption claim.

## Result

All 5/5 endpoint coframes decode exactly and fit. Coframe characters are p50
549 and p90 724.4. The complete bridge remains four frames with the same peak
as DA-085 (p50 1,916); repeating the parent endpoint adds p50 265 cumulative
characters, raising cumulative p50 to 3,072. DA-078 remains unchanged.

The relation's short endpoints are now simultaneously visible, but parent
assistant context remains in separate chunks. The next structural variant can
anchor both endpoints around each assistant chunk so every frame is a complete
edge slice. Replay is byte-identical; zero calls.

Artifacts:

- `artifacts/analysis/result.json`
- `artifacts/analysis/coframes.jsonl.gz`
