# DA-049 Scratchpad

## 2026-08-31 - Registration

- Reproduce 232/250/295 anchors.
- Exhaustively map residual target members onto frozen seed-direction rays.
- Separate singleton directional distance from multi-member and off-ray misses.
- Zero model, embedding, and cache calls.

## 2026-08-31 - Result

- Residuals: 37 singleton directional, 78 multi-member, 55 off-ray.
- Directional distances: d3=18, d4=10, d5=9; all 37 fit 2,048 chars.
- Extend the same frozen ray through distance 5 before changing representation.
