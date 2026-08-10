# E006 Part 2 Rev 4 PF11 Computability Verification

**Date:** August 10, 2026
**Decision:** **FAIL - STOP BEFORE REMAINING PREFLIGHT**
**Design anchor:** `71acbd35`
**Design SHA-256:** `2A516FCDF86744B47B2DF8BAB74794EDC73F8A66348CAA61997B1A572659C474`
**Authorization commit:** `595e0a71`
**Auditor execution commit:** `a85f1708`
**Machine artifact:** `artifacts/e006_rev4_pf11/pf11.json`
**Machine artifact SHA-256:** `3193DFB4D632C96E606C291E7A851BC2DBA39B9587A105355DEA655F2E2A85B3`
**Calls:** zero model calls; zero embedding calls

## 1. Registered Gate

Rev 4 PF11 requires the independently implemented Section 5.1 vector route and
the registered Section 2 Gram recurrence to satisfy all three conditions in all
12 next-step cells:

- maximum absolute score difference strictly below `1e-10`;
- identical full rankings; and
- identical next `top_m` sets.

Failure stops the work before PF1-PF10. PF11 fails, so the remaining Preflight,
parameter registration, and offline arms did not begin.

## 2. Route Independence

The vector route lives in `src/analysis/e006_rev4_vector_reference.py`. It
directly executes Section 5.1's vector pseudocode and imports only `numpy`; it
does not read or import the Section 2 recurrence, design, authorization, Gram
matrix, or committed query-cosine trace. The auditor records the vector source
SHA-256 and mechanically checks those import and token boundaries.

The unit-query reconstruction remains valid. Its maximum error against the 119
committed Q11 cosines is `9.96425164601078e-15`, with unit norm exactly `1.0`.

## 3. Result

| m | RHO | W_Q | Maximum score difference | Full ranking equal | Next `top_m` equal |
|---:|---:|---:|---:|---:|---:|
| 3 | 0.5 | 0.3 | 0.0118093 | No | Yes |
| 3 | 0.5 | 0.5 | 0.00692051 | No | Yes |
| 3 | 0.5 | 0.7 | 0.00342697 | No | Yes |
| 3 | 0.7 | 0.3 | 0.00331223 | No | Yes |
| 3 | 0.7 | 0.5 | 0.00185822 | No | Yes |
| 3 | 0.7 | 0.7 | 0.000850478 | No | Yes |
| 5 | 0.5 | 0.3 | 0.0330377 | No | Yes |
| 5 | 0.5 | 0.5 | 0.0188130 | No | Yes |
| 5 | 0.5 | 0.7 | 0.00881757 | No | Yes |
| 5 | 0.7 | 0.3 | 0.00925254 | No | Yes |
| 5 | 0.7 | 0.5 | 0.00506687 | No | Yes |
| 5 | 0.7 | 0.7 | 0.00219720 | No | Yes |

Summary:

- Registered score tolerance: **0/12 cells pass**.
- Full ranking agreement: **0/12 cells**.
- Next `top_m` agreement: **12/12 cells**.
- Maximum absolute score difference range: `0.000850478-0.0330377`.

The next sets happen to remain stable, but PF11 is conjunctive. Neither score
agreement nor full-ranking agreement passes in any cell.

## 4. Cause

Section 2.4 defines `mu` as the mean of unit hit vectors, then registers:

```text
|c'| = sqrt(RHO^2 + BETA^2 + 2*RHO*BETA*(c_hat dot mu))
```

For a mean that is not itself normalized, direct expansion requires the second
term to be `BETA^2 * ||mu||^2`. The committed trace gives
`||mu||^2 = 0.8426498393248191` for `m=3` and
`||mu||^2 = 0.5330802255471974` for `m=5`, not `1`.

This is why the recurrence described as corrected does not reproduce the
unchanged vector rule. The auditor intentionally evaluates the literal locked
equation; inserting the omitted factor would be an unauthorized repair after a
gate result.

## 5. Integrity and Disposition

- Git order is design `71acbd35`, authorization `595e0a71`, auditor `a85f1708`.
- Canonical episode-content SHA-256 values are the ranking comparison keys.
- The machine artifact records all 12 cells, route-independence evidence,
  reconstruction evidence, source hashes, launch command, and UTF-8 encoding.
- No targeted no-regression arm was possible because the eight targeted probes
  have no committed cosine traces; no outcome could have exceeded
  `CHARACTERIZED`.

**STOP BEFORE REMAINING PREFLIGHT.** Rev 4 provides no path past PF11 failure.
PF1-PF10, maximum-reachability analysis, parameter registration, PF7's 48-cell
sweep, and S4 were not run. Continuing requires another newly registered and
authorized design; the locked Rev 4 equations must not be edited.
