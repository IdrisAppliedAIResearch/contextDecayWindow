# DA-035 Scratchpad

## 2026-08-30 - Registration

- Freeze DA-031 at 983; use DA-034 sentinel savings but not DA-034 additions.
- Traverse the same carriers and attempt missing members independently. This
  isolates dependency granularity inside newly added capacity.
- Strong bar >=2/0; weak exactly 1/0; every conversation nonnegative.
- Zero model, embedding and cache calls.

## 2026-08-30 - Result

- Blind gate: DA-031 immutable on all 1,098 rows; sentinel capacity admits
  3,401 members independently, with 274 overflows and exact replay.
- Delivery rises 983 -> 986: +3/0, reaching the full one-hop ceiling. Conv-43
  gains one and conv-49 gains two; every conversation is nonnegative.
- All gains are DA-032 wrong-frozen-member residuals. Median admitted member
  cost is 95 chars; median carrier position 8.
- DA-034 used the same sentinel capacity at carrier granularity and gained 0.
  DA-035 gains 3 at atomic granularity. Dependency representation, not raw
  capacity alone, carries the final NF result.

