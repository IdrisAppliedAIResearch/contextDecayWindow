# DA-051 Scratchpad

## 2026-08-31 - Registration

- Reproduce DA-050=332.
- Partition residual dependency topology by member, episode, and session count.
- Measure exact grouped-episode frame fit at 2,048 chars.
- Zero model/embedder/cache calls; no selection or outcome change.

## 2026-08-31 - Result

- Topology: 55 one-member, 2 one-episode multi-member, 6 same-session
  multi-episode, 70 multi-session.
- Both grouped episode frames overflow 2,048 chars; simple grouping is closed.
- Distributed episode counts: k2=47, k3=18, k4=8, k5=3.
- Next test a protected exact retained set with capacity five.
