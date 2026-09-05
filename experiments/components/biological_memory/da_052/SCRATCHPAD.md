# DA-052 Scratchpad

## 2026-08-31 - Registration

- Compose sealed one-hop, distance-2, and distance-3-to-5 streams in order.
- At most five immutable exact retained frames; one replaceable current frame.
- Structural guards only; evidence-aware KEEP after contract seal.
- Zero model/embedder/cache calls.

## 2026-08-31 - Result

- Complete availability 332->363, +31/0, p=9.31e-10.
- Required frames: k2=24, k3=4, k4=1, k5=2.
- Retained chars p50 646; peak auxiliary p50 2,223/max 3,272.
- Cumulative traversal p50 27,333, p90 34,820: stopping is now the cost boundary.
- Next audit 102 residuals for partial versus absent stream reachability.
