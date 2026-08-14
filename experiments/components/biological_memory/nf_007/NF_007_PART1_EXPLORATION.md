# NF-007 Part 1 Exploration - Hard Cluster-Floor Reachability

**Status:** `PART 1 COMPLETE - CLUSTER_FLOOR_REACHABLE`
**Registration anchor:** `66d1684da7e83a2c1e156d035b410b457899db7f`
**Analysis source:** `src/analysis/nf007_exploration.py`, SHA-256
`86ebfa11f34a7b2919905561b2626eb81480047879b4db73e9ebf99f86697557`
**Amendments:** `AMENDMENT_001_domain_label_vocabulary.md`,
`AMENDMENT_002_candidate_load_ratio.md`
**Calls:** zero embedding calls, zero generation calls

## Result

The carried parent-derived `k=16` partition is structurally reachable for a
hard statement-level cluster floor. Eight clusters contain renaissance-art
statements. Seven of those clusters - 2, 3, 5, 7, 8, 14, and 15 - contain zero
monetary-policy statements. The registered positive branch therefore fires.

This does not show that a floor recovers a missing Q11 art item. No selector,
query, Q11 key, packing, targeted outcome, or availability measurement ran.
It establishes only that the carried partition contains art-occupied regions
that are not shared with monetary statements, so the proposed allocation phase
is not structurally blocked at `k=16`.

## Behavioral identity

The mechanism clusters 119 parent episode embeddings, not 791 statement
vectors. Each of the 791 statements inherits its parent's assignment. This
reproduces NF-006's actual A3 path and changes no cluster geometry; re-clustering
statement vectors remains excluded as a second component.

Assignments are deterministic across repeated calls. The valid artifact and
the preserved invalid-vocabulary artifact have identical assignment digests:

| Population | SHA-256 assignment digest |
|---|---|
| 119 parents | `29c026e653ab7f65b032b0b3104a6b24194d951d0fe740c913c5406b0756f9ca` |
| 791 statements | `be4fc93ed80e5ff582074177729a1d60dcfb3897f758cb8cfdae4d99889ade14` |

Domain labels enter only after those assignments are fixed. The evaluator uses
the database's exact `renaissance_art` and `monetary_policy` labels under
Amendment 001.

## Scale transfer

The count-based parameter is unchanged while selectable membership grows:

| Measure | Parent partition | Statement membership |
|---|---:|---:|
| Population | 119 | 791 |
| Mean per cluster | 7.4375 | 49.4375 |
| Minimum | 1 | 7 |
| Median | 5.5 | 40.0 |
| Maximum | 20 | 137 |
| Empty clusters | 0 | 0 |

The candidate-load ratio is **6.6471x**. This is not the same allocation grain
as E005 even though `k=16` has provenance. It is a membership expansion over
the same parent-derived geometry, not a statement-vector partition.

Turn 90 reproduces DX-001: cluster 12 contains 20 parents. At statement grain
that cluster contains 137 candidates: 132 monetary-policy and 5 marine-biology
statements, with zero renaissance-art statements.

## Full occupancy

| Cluster | Parents | Statements | Art | Monetary | Civil | Marine | Probe |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 16 | 91 | 0 | 0 | 82 | 0 | 9 |
| 1 | 6 | 42 | 0 | 42 | 0 | 0 | 0 |
| 2 | 19 | 126 | 13 | 0 | 13 | 96 | 4 |
| 3 | 6 | 32 | 24 | 0 | 0 | 0 | 8 |
| 4 | 1 | 7 | 0 | 0 | 0 | 7 | 0 |
| 5 | 3 | 21 | 14 | 0 | 0 | 7 | 0 |
| 6 | 2 | 14 | 0 | 14 | 0 | 0 | 0 |
| 7 | 5 | 41 | 6 | 0 | 21 | 14 | 0 |
| 8 | 2 | 14 | 7 | 0 | 0 | 7 | 0 |
| 9 | 15 | 94 | 88 | 6 | 0 | 0 | 0 |
| 10 | 2 | 10 | 0 | 0 | 0 | 4 | 6 |
| 11 | 5 | 39 | 0 | 14 | 25 | 0 | 0 |
| 12 | 20 | 137 | 0 | 132 | 0 | 5 | 0 |
| 13 | 7 | 52 | 0 | 0 | 52 | 0 | 0 |
| 14 | 9 | 64 | 35 | 0 | 23 | 0 | 6 |
| 15 | 1 | 7 | 7 | 0 | 0 | 0 | 0 |

## Instrument correction

The first execution looked for literal labels `art` and `monetary`, which do
not exist in the frozen database, and fired `NO_CLUSTER_REACHABILITY`
vacuously. It is preserved as
`artifacts/part1_cluster_reachability_invalid_v1.json` and is not a result.
Amendment 001 corrected only the evaluation vocabulary before the valid rerun;
assignment digests remained identical. Amendment 002 corrects the protocol's
candidate-load arithmetic from 6.6454x to 6.6471x and affects no branch.

## Construction caveat and boundary

A hard floor guarantees cluster coverage by construction. If a later
pre-registered selection recovers art, the supported claim would be that the
budget had room for an allocation constraint, not that global similarity found
art. The floor size must be locked before Q11 measurement, similarity fill must
remain, and NF-006's targeted `21/21` item-level no-regression gate must be
binding.

Part 1 authorizes no selector implementation or full-study run by itself. Its
machine-readable artifact is
`artifacts/part1_cluster_reachability.json` (9,299 bytes, SHA-256
`bc51b33796c45b5d9db2b804ba9989f2b7cafce689b761bd2f07be3b3fb5f71d`).
