# DA-062 Scratchpad

## 2026-08-31 - Registration

- Strongest DA-038 represented episodes activate their source session heads.
- Direct order first, then admitted DA-031/033/038 actions in frozen order.
- First-appearance deduplication; no query or relevance fallback.
- Strongest payload bytes and order remain immutable.
- Seal routes before required-session join.
- Zero model/embedder/cache calls.

## 2026-08-31 - Result

- Complete required-session coverage 350/465 (.753); any 426/465.
- Routed sessions p50 8; fraction p50 .170/p90 .224.
- Required first/last route position p50 1/2 when present.
- Selective topology, but registered coverage bar fails; no traversal.
- Posthoc DA-061 union reaches 438/465 but p50 fraction .509.
- Next development signal: replaceable head stream, never simultaneous union.
