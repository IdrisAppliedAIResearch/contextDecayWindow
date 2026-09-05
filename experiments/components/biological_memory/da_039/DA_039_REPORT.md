# DA-039 Report

## Verdict

`DOMINANT_PRIOR_SENTINEL_ATOMIC_CONSUMPTION`

Seventeen of the 18 one-hop-reachable misses remaining after DA-038 fit at the
initial sentinel-recovered boundary and become unaffordable only after earlier
append-only atomic payloads. One is too large at the boundary. There are no
unaccounted cases.

| Residual class | Count |
|---|---:|
| Prior sentinel atomic consumption | 17 |
| Initial sentinel atomic size | 1 |

Initial slack is 765 characters at the median. Final slack falls to 41.5 while
the median missing-member cost is 239. No residual member fits after the full
DA-038 pack.

The implication is structural: the remaining gap is caused by eagerly
materializing linked payloads into a scarce suffix. Another relevance score
would only choose a different displaced member. The next justified probe is a
compact dependency frontier that preserves all DA-038 payloads and represents
additional linked members as reversible references before materialization.

The classification artifact replays byte-identically at
`b12532da99fe17d713a1918dc64fc553ab0872cf980425bd1763bf3893cd4727`.
Model, embedding and cache calls: zero.
