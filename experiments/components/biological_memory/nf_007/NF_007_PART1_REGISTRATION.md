# NF-007 Part 1 Registration - Hard Cluster-Floor Reachability

**Status:** `REGISTERED - NOT RUN`
**Authorization:** user instruction in the NF-006 successor thread, August 13,
2026
**Scope:** exploration only; no selector, query, Q11 item key, availability
measurement, or full-study bar is opened

## Question

Can the carried A3 `k=16` partition support a hard cluster floor at statement
packing granularity, or does every cluster containing art statements also
contain monetary statements?

This is the required Part 1 exploration before a full NF-007 design can be
locked. A passing result establishes only structural reachability. It does not
establish Q11 recovery, targeted safety, reader value, or adoption.

## Behavioral identity to test

NF-006 does not cluster 791 statement vectors. It deterministically clusters
the 119 eligible parent episode vectors with farthest-first initialization and
Lloyd iterations at `k=16`, then gives every statement its parent's assignment.
NF-007 Part 1 preserves that construction exactly. Re-clustering statement
vectors would change a second component and is excluded.

The proposed successor changes only the coverage term from soft credit to a
hard allocation phase. Part 1 does not implement that phase; it tests whether
the carried partition can express the intended separation before any selector
or result bar is designed.

## Frozen inputs

| Input | Bytes | SHA-256 |
|---|---:|---|
| corrected `c121_l` database | 1,978,368 | `5da47ea3fc2c8e3dcc50fa380ff65202d82557905d9976117e9e5d82e55c1c41` |
| NF-006 sealed vector cache | 4,063,232 | `e6a2a6687fb5ee6694a43dd3ebe7a957f7bd9852418657f78274c64d38c4f391` |
| NF-006 vector manifest | 891 | `214dd342c391f0165aca9a5f8495a705a8ff5aa91ffb52cb63303599d9a4a1e9` |
| NF-006 statement identity artifact | 2,105 | `ea4f6779e24c0be828a04404bb81a211a34b2c5297d0c6c2e6dc91cf82cf94e2` |
| E005 result anchor | 2,466 | `07b714389697c6e58d6c539d1181a976e1f2d9b42a189a3c7629a9895362f1ff` |
| DX-001 report | 5,303 | `ba4d55feee804cc16f4f6cda6c8a5afdecfda67d9cdc2efb05d8991f5dc50a7c` |
| NF-006 carried mechanism | 10,255 | `8a2daa1c2cc753ea4de3651af0aa9c37c88738b631979b81e1348df90ac407ab` |
| deterministic clustering implementation | 11,702 | `990e7f84e7690c55350ff24bcc41e4486254c72145320da0bc08ae509e597265` |

The cache is opened read-only and must pass its committed manifest before use.
Part 1 makes zero embedding calls and zero generation calls.

## Locked parameter and scale audit

`k=16` is frozen. It is E005's committed primary configuration and the exact
partition used by DX-001. No other cluster count is computed.

The count is not scale-invariant. E005 assigned 119 parents to 16 clusters,
an arithmetic mean of `7.4375` parents per cluster. Statement packing assigns
791 candidates through those parent memberships, an arithmetic mean of
`49.4375` statements per cluster, or `6.6454x` as many selectable candidates
per cluster. This is a candidate-load change, not a new centroid geometry.

The artifact must report all 16 rows, including:

- parent and statement member counts;
- user and assistant statement counts;
- per-domain statement counts, including blank labels;
- minimum, median, maximum, and full sorted distributions;
- empty clusters, if any;
- the cluster containing turn 90 and its parent and statement membership;
- digests of parent and expanded statement assignments; and
- the arithmetic means and candidate-load ratio above.

## Registered reachability rule

Domain labels are evaluation-only. They are read after assignments are fixed
and may not affect clustering, ordering, or any future selection.

Let an *art-occupied cluster* contain at least one statement whose inherited
measurement label is `art`. Part 1 passes only if at least one art-occupied
cluster contains zero statements labelled `monetary`.

| Condition | Disposition |
|---|---|
| At least one art-occupied cluster has zero monetary statements | `CLUSTER_FLOOR_REACHABLE`; Part 1 may inform a later full pre-registration |
| Every art-occupied cluster also contains monetary statements | `NO_CLUSTER_REACHABILITY`; stop NF-007 before selector implementation |
| Any frozen hash, cache seal, population count, `k`, or assignment reproduction fails | named integrity stop; no reachability claim |

If `NO_CLUSTER_REACHABILITY` fires, no `k=64`, alternate `k`, sweep, merge,
split, or relabelling is run. A successor may derive `k` from a separately
registered scale rule such as preserved members per cluster, but it must do so
before observing its own Q11 outcome and may not select a value from a sweep
against this probe.

## Construction caveat

A hard floor guarantees cluster coverage by construction. If a later registered
study recovers art, that would demonstrate that the budget had room for an
allocation constraint; it would not demonstrate that global similarity found
art. A later design must keep the floor a pre-committed minority allocation,
retain similarity fill, and carry NF-006's targeted `21/21` item-level
no-regression gate. Availability would still require live evaluation.

## Preflight boundary

This registration itself is the outcome-blind Part 1 protocol required by
`PREFLIGHT.md`. The full NF-007 pre-registration does not exist yet and cannot
be written until this exploration is committed. Part 1 records mechanism
identity, name-to-behavior, full distributions, scale transfer, and empty or
degenerate cluster states. The later spec, if authorized by a pass, must still
complete PF1-PF10 before any selection run.
