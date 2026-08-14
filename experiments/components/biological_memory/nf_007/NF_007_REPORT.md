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

The aggregate density is more informative than entry alone:

| Region | Candidate statements | Selected | Sampling density |
|---|---:|---:|---:|
| Cluster 0 (82/91 civil) | 91 | 30 | 33.0% |
| Cluster 12 (132/137 monetary) | 137 | 14 | 10.2% |
| Art-majority clusters 3, 5, 8, 9, 15 | 168 | 9 | 5.4% |

The selector spends 44 of 80 slots in clusters 0 and 12 while sampling the five
art-majority clusters at one sixth of cluster 0's density. It enters every art
cluster, generally once, and then keeps allocating elsewhere. Renaissance art
is therefore neither absent nor too small to matter; it is weakly matched by
the Q11-driven objective after entry.

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
cannot alter the selection because A3 already enters every cluster. NF-006 also
shows that own-statement ranking does not repair the art residual: art falls
from 2/4 under episode ranking and packing to 1/4 under own-statement ranking
and packing. On this exhausted probe, neither candidate subdivision nor
distinct-region entry makes art competitive under the Q11 similarity signal.

This is the third independent arrival at the same boundary. BA-001 found art
stored and directly recallable but not broadly cued. DR-002 found both art
contributors at cosine ranks 50 and 86 and fired its registered verdict that
cosine ordering is the wrong prior for breadth. TA-001 alone reached art 4/4 by
temporal adjacency rather than similarity, then failed targeted safety with two
gains and six losses. The supported interpretation is that Q11 does not broadly
match art in this embedding space; it is an inference across these artifacts,
not a universal claim about every embedding model.

The carried count-of-cluster-entry coverage family is therefore closed on this
store. A successor that merely counts distinct `k=16` regions touched is inert,
and no alternate floor size, `k`, sweep, or Q11-guided coverage successor is
run. NF-006's 14/17 availability result stands as the endpoint of this line;
the next decision-relevant question is whether its two-item availability gain
over the 12/17 episode arm changes reader fact use.

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
