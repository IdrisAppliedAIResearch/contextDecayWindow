# EC-002 memory update

- A same-store, same-vector offline replay changed only exact packing priority:
  A0 recency -> K -> coverage; A1 K -> recency -> coverage.
- Any evidence-session recall rose 109/470 -> 261/470: 152 paired gains, zero
  losses. Exact-turn-any rose 79/470 -> 196/470: 119 gains, two losses.
- K deliveries rose 26 -> 476 while every block remained truncated and median
  block size stayed 31,920 characters. Recency-first budget exhaustion is a
  confirmed causal gate, not merely a post-hoc association.
- K-first is not authorized for production or Tier 2 without a separately
  registered live test. Residual misses leave threshold and granularity open.
- EC-001's original vector cache is unrecoverable. Its A0 is an amended
  aggregate reproduction under recomputed embeddings, not a bit replay.
- CC-006 protects retained post-contract caches only. A1 reused 96,585 bound
  vectors read-only with zero misses and zero model calls.

