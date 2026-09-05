# DA-090 Exact Component-Packet Fallback

**Status:** `COMPLETE; EXACT_PACKET_FALLBACK_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-089 result commit `87eb9625`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can a fixed exact packet fallback cover DA-089's 3,499 blind overflows while
preserving every already-complete envelope and leaving DA-078 unchanged?

## Immutable Control

Use all 8,055 sealed DA-089 targets. Rows classified `COMPLETE` retain route,
frame count, peak, cumulative charge, identity, and edge metadata exactly. The
fallback may run only on `FULL_CHILD_OVERFLOW` or `ANCHORED_SLICE_OVERFLOW`.

## Fixed Packet Fallback

Split each source component into consecutive 1,800-character chunks with a
canonical sentinel header carrying component type, one-based index/total, and
role. Store episode/member identity and edge in typed out-of-band metadata.

- Full-child overflow: packetize only the required child member.
- Anchored-slice overflow: packetize parent member 0, parent member 1, then the
  required child member, preserving component and source-text order.

Every packet replaces the prior frame and must be <=2,048 characters.
Concatenated decoded chunks must equal each source component byte-for-byte. No
alternate chunk size, compression, summary, route change, score, threshold,
answer, retry, or reallocation is allowed.

`EXACT_PACKET_FALLBACK_SIGNAL` requires all 8,055 targets complete, every
DA-089 complete row unchanged, zero DA-078 mutation, and exact bounded decode.
Report fallback route, frame, peak, and cumulative costs.

This is structural exposure only. Require byte-identical replay and zero model,
embedding, and cache calls. No reader, retention, stopping, delivery, runtime,
outcome-transfer, or adoption claim.

## Result

All 8,055/8,055 blind frontier targets are complete with exact bounded decode
and zero DA-078 mutation. Every one of DA-089's 4,556 complete rows retains its
route and cost fields unchanged. Fallback routes are 2,701 child packet streams
and 798 edge-component packet streams. Replay is byte-identical; zero calls.

Overall frames are p50 one and p90 three; peak characters p50 1,812 and p90
1,819; cumulative characters p50 2,033 and p90 3,537. Fallback-only rows use
p50 two/p90 four frames with cumulative p50 2,669/p90 4,482.4.

Fixed exact packetization closes blind full-frontier capacity without
displacement. It does so by moving long payloads through sequential frames;
reader recognition, retention, stopping, and use remain untested.

Artifacts:

- `artifacts/analysis/result.json`
- `artifacts/analysis/targets.jsonl.gz`
