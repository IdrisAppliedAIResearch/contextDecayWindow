# DA-094 Scratchpad

- Recompute DA-093 parses exactly; do not optimize or retune them.
- Count source members, pointers and referenced-character concentration.
- Coherent -> manifest. Fragmented -> constrained exact node-local codec.
- Zero model, embedder and cache calls.

## Pre-Run Join Correction

- DA-093's 3,499 selected rows span 455 questions. The implementation's first
  assertion incorrectly carried DA-091's broader 461-question count.
- Corrected the assertion to 455 before any topology parse or result existed.
  Population, metrics, bars and encoding are unchanged.

## Result

- Pointer count p10/p50/p90: 79/123/162.
- Unique prior members: 18/24/29.
- Largest-source share: 14.72%/23.43%/42.16%.
- Reference coverage: 39.34%/54.07%/68.64%; median distance 23 members.
- Fragmented, not a coherent dependency graph. Pivot to exact one-node-local
  encoding; preserve DA-093 as the capacity control.
- Exact accounting and replay; zero calls.
