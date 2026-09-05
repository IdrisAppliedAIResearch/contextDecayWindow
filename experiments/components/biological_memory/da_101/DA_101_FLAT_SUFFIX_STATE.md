# DA-101 Flat Suffix State

**Status:** `COMPLETE; FLAT_SUFFIX_RUNTIME_SIGNAL`
**Date:** September 1, 2026
**Parent:** DA-100 result commit `1785b16e`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can removing per-state Python objects and incidental cyclic-GC pauses bring the
exact DA-100 allocator's large-conversation tail below 200 ms?

## Frozen Optimization

Represent the same suffix automaton as parallel primitive lists for maximum
length, suffix link, transitions, first member and first end. Preserve the exact
construction, clone, transition and query order. Do not alter matching or
allocation semantics. Suspend cyclic garbage collection only inside one
allocation and restore its prior enabled state in `finally`; reference counting
remains active and no state survives the allocation.

No candidate, member, order, sentinel, source coordinate, charge, fit, skip,
prefix, budget or output field may change.

## Gates And Disposition

Require all DA-100 codec tests; exact equality to the 18 sealed legacy hashes;
all 1,098 rows byte-identical to committed allocation SHA-256
`f5327a9b5946f217910f2de5df222da66bda59d5f7b18267f8154763f98d44f9`;
GC state restored after success and forced exception; deterministic replay;
zero duplicates, misses or calls.

Report `FLAT_SUFFIX_PRODUCTION_SIGNAL` at p50 `<=25 ms`, p95 `<=100 ms`, max
`<=200 ms`. Report `FLAT_SUFFIX_RUNTIME_SIGNAL` if both passes have p95 `<=200
ms`, max `<=250 ms`, and double replay `<=6 minutes`. Otherwise report
`NO_FLAT_SUFFIX_RUNTIME_SIGNAL`.

This is Python mechanical runtime only, not outcomes, reader use, fresh
transfer, native performance or production adoption.

## Result

All 1,098 rows retain sealed allocation SHA-256
`f5327a9b5946f217910f2de5df222da66bda59d5f7b18267f8154763f98d44f9`,
with byte-identical replay, zero cache misses and zero model/embedding calls.
GC restoration passes on success and forced exception.

First-pass p50/p95/p99/max is 59.89/76.87/80.65/85.86 ms; replay is
59.76/64.68/67.66/95.89 ms. The double replay finishes in 153.42 seconds.
Both runs clear the registered runtime tier and the disposition is
`FLAT_SUFFIX_RUNTIME_SIGNAL`. The 25 ms median production tier is not met.

Compared with DA-100, first-pass p95 falls 216.45->76.87 ms and replay p95
265.75->64.68 ms. The prior tail was Python state layout and GC overhead, not
an inherent cost of exact indexed matching at this corpus scale.
