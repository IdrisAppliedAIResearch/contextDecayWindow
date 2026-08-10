# E006 Part 2 Rev 5 S3 Parameter Lock

**Date:** August 10, 2026
**Design anchor:** `764396b2`
**Authorization commit:** `ac81d8e1`
**PF11 artifact commit:** `90677655`
**Preflight artifact commit:** `5973989e`
**Decision:** **LOCKED FOR S4**

This file restates, without modification, the authoritative grid registered in
Rev 5 Section 3. It adds no parameter, arm, threshold, tie-break, or outcome
criterion.

| Parameter | Locked values |
|---|---|
| `D` | `{0, 1, 2, 3}` |
| `m` | `{3, 5}` |
| `W_Q` | `{0.3, 0.5, 0.7}` |
| `W_C` | `1 - W_Q` |
| `RHO` | `{0.5, 0.7}` |
| `BETA` | `1 - RHO` |
| budget | exactly 32,000 serialized characters |

Cartesian product: **48 cells**. `D=0` is X1; `D=1,2,3` are X2-X4. X0 is the
committed deployed reference and is not part of the Cartesian product.

Ranking ties use canonical episode-content SHA-256 ascending after score
descending. `seen` excludes previously retrieved content identities. Final
packing ranks the cumulative `seen` set by the cue used on the final inclusive
retrieval iteration, then applies the authoritative exact compact-XML packer in
that order with skip-on-overflow behavior.

S4 reports Q11 facts, domains, characters, selected episodes, candidate counts,
payload hashes, and final-cue cosine to the original query for every cell.

The binding kill remains: **no chained arm (`D>0`) exceeds X0's committed 6/17
Q11 availability in any cell.** X1 must remain byte-identical to single-shot
`top_m`. Every outcome remains capped at `CHARACTERIZED`; no targeted
no-regression, live run, promotion, or adoption is authorized.
