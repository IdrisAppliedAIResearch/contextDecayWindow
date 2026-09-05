# DA-099 Indexed Sentinel Runtime

**Status:** `REGISTERED; MECHANICAL RUNTIME STUDY`
**Date:** September 1, 2026
**Parent:** DA-098 registration commit `9eb38e89`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can DA-034's exact sentinel codec and DA-098's frozen nested allocation be
executed within a production-oriented latency envelope without changing one
encoded segment, charge, admission, skip or selected-member order?

## Frozen Semantics

The existing `encode_members` implementation is the semantic oracle. Preserve
its shortest absent sentinel, minimum four-character match, greedy longest
backward match, earliest `(member_index,start)` tie-break, strict
`match_length > reference_code_length` rule, member boundaries, sequential
within-payload references, role charge, fit-on-`<= budget`, skip-on-overflow,
identity deduplication and frozen candidate/member order.

Replace repeated reconstruction of the history substring index with one online
member-separated index per allocation. Only admitted members may update the
persistent state. Speculative payloads must use isolated temporary state and
leave the persistent index byte-for-byte unchanged when rejected. No evidence,
outcome, score, rank, threshold or allocation policy may enter the codec.

## Equivalence Gates

Before DA-098 outcomes are opened, require:

1. Exact encoded-segment, decoded-text and charge equality against the legacy
   oracle on fixed synthetic boundary, repetition, tie, sentinel and sequential
   payload cases.
2. Exact equality on a deterministic blind LoCoMo subset containing every
   conversation and fixed low/median/high prefix-charge strata: actions,
   action costs, selected members and order, final charge and allocation hash.
3. Exact DA-035 prefix decode/order/charge, zero duplicates, `<=32,000` final
   characters, positive admissions and overflows, deterministic replay and zero
   cache misses or calls on all 1,098 DA-098 rows.

Any mismatch stops the optimized replay. The legacy implementation remains the
authority; do not repair or reinterpret a mismatch after observing outcomes.

## Runtime Gates

Measure warm-process optimized `allocate_32` time with pair order and member
payloads already resident, using `perf_counter_ns`, on all 1,098 blind rows.
Report machine and Python version, p50, p95, p99, maximum and total allocation
time. Report dataset/cache loading, ranking, serialization and deterministic
replay wall time separately.

Report `INDEXED_SENTINEL_PRODUCTION_SIGNAL` only if all equivalence gates pass
and optimized allocation latency is p50 `<=25 ms`, p95 `<=100 ms`, and maximum
`<=200 ms`. Report `INDEXED_SENTINEL_RUNTIME_SIGNAL` if equivalence passes,
p95 `<=200 ms`, maximum `<=500 ms`, and total double LoCoMo replay is `<=12
minutes`. Otherwise report `NO_INDEXED_SENTINEL_RUNTIME_SIGNAL`.

The registered bars characterize this Python implementation on the recorded
machine. They do not include embedding/model latency and do not establish
reader use, fresh transfer, production adoption or native-runtime performance.
