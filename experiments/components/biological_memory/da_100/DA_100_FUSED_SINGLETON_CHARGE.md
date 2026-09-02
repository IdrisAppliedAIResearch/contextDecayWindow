# DA-100 Fused Singleton Charge

**Status:** `COMPLETE; NO_FUSED_SINGLETON_RUNTIME_SIGNAL`
**Date:** September 1, 2026
**Parent:** DA-099 full blind runtime result, allocation commit `31e80e15`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can fusing exact singleton parsing and charge accumulation remove DA-099's
large-conversation latency tail while preserving the complete sealed DA-098
allocation?

## Frozen Optimization

Freeze DA-099's suffix index, matching semantics and DA-098 order. For each
single-member tail attempt, traverse the same greedy matches but accumulate
literal and exact sentinel-varint reference lengths directly. Do not allocate
an `EncodedMember`, concatenate literal segments, decode the speculative member
or traverse its segments a second time. Prefix verification remains exact and
unchanged. Add a constant-time role-charge fast path only when every speaker is
already present; unfamiliar speakers retain the exact DA-099 path.

No candidate, member, order, sentinel, match, source coordinate, charge, fit,
skip, prefix or budget may change.

## Gates And Disposition

Require direct fused-length equality with legacy encoded wire length on fixed
and randomized cases; exact equality to all 18 sealed legacy allocation hashes;
all 1,098 rows byte-identical to committed DA-098 allocation SHA-256
`f5327a9b5946f217910f2de5df222da66bda59d5f7b18267f8154763f98d44f9`;
zero duplicates, cache misses or calls; and deterministic replay.

Report `FUSED_SINGLETON_PRODUCTION_SIGNAL` if p50 `<=25 ms`, p95 `<=100 ms`
and maximum `<=200 ms`. Report `FUSED_SINGLETON_RUNTIME_SIGNAL` if p95 `<=200
ms`, maximum `<=500 ms`, and the double replay is `<=8 minutes`. Otherwise
report `NO_FUSED_SINGLETON_RUNTIME_SIGNAL`.

This is exact mechanical runtime only. It does not test outcomes, reader use,
fresh transfer, native runtime or production adoption.

## Result

All 1,098 allocations retain sealed SHA-256 `f5327a9b5946f217910f2de5df222da66bda59d5f7b18267f8154763f98d44f9`,
with byte-identical replay, zero cache misses and zero model/embedding calls.

First-pass p50/p95/p99/max was 75.65/216.45/224.23/242.13 ms. Replay was
73.21/265.75/279.76/286.17 ms. Total double replay was 296.37 seconds. The
maximum and wall-time bars pass, but both p95 values exceed 200 ms; disposition
is `NO_FUSED_SINGLETON_RUNTIME_SIGNAL`.

Fusion reduced DA-099 first-pass p50 by 7.89 ms and p95 by 21.87 ms without
changing behavior. It did not remove the large-conversation tail. This closes
object-materialization fusion alone, not indexed exact charging.
