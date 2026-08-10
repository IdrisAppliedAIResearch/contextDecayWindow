# E006 Part 2 Rev 5 PF11 Computability Verification

**Date:** August 10, 2026
**Decision:** **PASS - CONTINUE PREFLIGHT**
**Design anchor:** `764396b2`
**Design SHA-256:** `6A674682DD60370631CAA834DE43FE07E59F2E0683E2D0C435DFC1003CEBE444`
**Authorization commit:** `ac81d8e1`
**Auditor execution commit:** `5be81e12`
**Machine artifact:** `artifacts/e006_rev5_pf11/pf11.json`
**Machine artifact SHA-256:** `A6F212FBDB1F84C90D79168ECB45E54B5E774BABAFFB2490BF43F493A643D62C`
**Calls:** zero model calls; zero embedding calls

## 1. Gate

Rev 5 PF11 requires the independent Section 5.1 vector route and registered
Section 2 recurrence to meet all three conditions in all 12 next-step cells:
maximum absolute score difference below `1e-10`, identical full rankings, and
identical next `top_m` sets.

The vector route is the unchanged file first committed for Rev 4. It imports
only `numpy`, directly executes the vector pseudocode, and neither reads nor
imports the Gram recurrence. The machine artifact records its content hash and
passes both the independence and leakage audits.

## 2. Result

| m | RHO | W_Q | Maximum score difference | Full ranking equal | Next `top_m` equal |
|---:|---:|---:|---:|---:|---:|
| 3 | 0.5 | 0.3 | 7.24421e-15 | Yes | Yes |
| 3 | 0.5 | 0.5 | 8.16014e-15 | Yes | Yes |
| 3 | 0.5 | 0.7 | 8.93730e-15 | Yes | Yes |
| 3 | 0.7 | 0.3 | 8.54872e-15 | Yes | Yes |
| 3 | 0.7 | 0.5 | 8.96505e-15 | Yes | Yes |
| 3 | 0.7 | 0.7 | 9.40914e-15 | Yes | Yes |
| 5 | 0.5 | 0.3 | 7.52176e-15 | Yes | Yes |
| 5 | 0.5 | 0.5 | 8.32667e-15 | Yes | Yes |
| 5 | 0.5 | 0.7 | 9.02056e-15 | Yes | Yes |
| 5 | 0.7 | 0.3 | 8.79852e-15 | Yes | Yes |
| 5 | 0.7 | 0.5 | 9.13158e-15 | Yes | Yes |
| 5 | 0.7 | 0.7 | 9.49241e-15 | Yes | Yes |

Summary:

- Score tolerance: **12/12 cells pass**.
- Full-ranking identity: **12/12 cells pass**.
- Next `top_m` identity: **12/12 cells pass**.
- Maximum absolute score difference: `9.49240686054509e-15`.

The reconstructed unit query matches all 119 committed Q11 cosines with maximum
absolute error `9.96425164601078e-15`. The registered Gram route therefore
reproduces the unchanged vector mechanism without a query vector or embedding
call.

## 3. Disposition

**PASS - CONTINUE PREFLIGHT.** Git order is design `764396b2`, authorization
`ac81d8e1`, and auditor `5be81e12`. The input inventory, counts, hashes, launch
command, source hashes, encoding, and zero-call boundary are recorded in the
machine artifact.

This pass authorizes PF1-PF10 only after this report and artifact are committed.
It does not pre-authorize the 48-cell run: the remaining Preflight must pass and
be committed first.
