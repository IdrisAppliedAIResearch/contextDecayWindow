# NF-007 Report - Hard Cluster Floor

**Status:** `STOP - FLOOR_INERT`  
**Interpretation:** the registered instrument cannot distinguish treatment from
control; this is not a failure of a binding hard-floor mechanism  
**Part 1 registration:** `66d1684da7e83a2c1e156d035b410b457899db7f`  
**Supplemental coverage registration:**
`9360eb9556a04009407e71a07b57dae0913a4851`  
**Calls:** zero embedding calls, zero generation calls

## Result

NF-006's sealed own-statement T1 selection at probe turn 120 already touches
all 16 of the carried `k=16` clusters. A floor of one statement per nonempty
cluster therefore forces zero admissions and displaces zero incumbents. The
registered `FLOOR_INERT_STOP` branch fires before a full NF-007 registration or
selector implementation.

| Cluster | Selected statements |
|---:|---:|
| 0 | 30 |
| 1 | 4 |
| 2 | 6 |
| 3 | 2 |
| 4 | 1 |
| 5 | 1 |
| 6 | 2 |
| 7 | 1 |
| 8 | 1 |
| 9 | 4 |
| 10 | 1 |
| 11 | 5 |
| 12 | 14 |
| 13 | 5 |
| 14 | 2 |
| 15 | 1 |

The proposed mechanism prediction concentrated recovery in art-heavy clusters
15, 5, and 8. Each is already represented once in the sealed control. Because
the locked floor cannot change those identities, that prediction was neither
registered as a treatment outcome nor evaluated.

## What Part 1 established

The parent-derived partition itself is not blocked: 119 parent episodes expand
to 791 statements across 16 nonempty clusters, and seven art-occupied clusters
contain no monetary statements. Renaissance-art episodes contribute 194 of 791
statement candidates (24.5%), while NF-006 T1 delivered only 1 of 4 art facts.
The missing art is therefore not explained by absent art-labelled candidate
mass or absent cluster coverage.

The floor result narrows the ceiling one step further. A one-per-cluster rule
cannot alter the selection because A3 already enters every cluster; the
remaining loss is within-cluster candidate choice or another finer allocation
property. No alternate floor size, `k`, sweep, or Q11-guided successor was run.

## Integrity

The control reads exactly the committed NF-006 `T1_OWN_STATEMENT` seal at turn
120, requires 80 unique identities, reproduces the parent and statement
assignment digests, and maps IDs without loading domain labels, the Q11 key, or
availability artifacts. The 4,228-byte result artifact has SHA-256
`91804a13049253a62a30e2e55f505f90d4dcb0b40d06718deee54634ded68f05`.
A second execution is byte-identical. The selected payload remains 31,991 of
32,000 characters with 9 residual characters; this cost does not affect the
inertness result because the floor admits nothing.

## Gate lesson

The first Part 1 execution had returned the stopping branch only because its
evaluator searched for nonexistent short domain labels. The invalid artifact
was preserved and corrected by standalone amendment before the valid run. The
supplemental control applies the same anti-vacuity principle to the proposed
floor: a gate is trusted to stop only after showing that its tested population
and its non-stopping alternative were capable of existing.

NF-007 closes without a full pre-registration, selector, availability result,
live run, promotion, or adoption.
