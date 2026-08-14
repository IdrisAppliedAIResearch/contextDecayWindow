# NF-007 Supplemental Registration - Sealed T1 Cluster Coverage

**Status:** `REGISTERED - NOT RUN`  
**Authorization:** user instruction in the NF-006 successor thread, August 13,
2026  
**Scope:** outcome-blind anti-vacuity control only; no selector, Q11 key,
domain label, fact availability, targeted score, or full-study bar is opened

## Question

How many of the carried `k=16` clusters does NF-006's already sealed T1
selection touch at the Q11 probe?

Part 1 established that the partition can separate art-labelled from
monetary-labelled regions. It did not establish that a one-per-nonempty-cluster
floor can change the existing selection. This supplemental control tests that
missing condition before the NF-007 selector or full registration is written.

## Frozen inputs

| Input | Commit or SHA-256 |
|---|---|
| NF-006 G6/G7 selection seal | commit `ef074cda8753b594cd970dd4e4c83f0b7b8e04c1`; SHA-256 `3dc22122d4cae27af29d642cee68918e4f683ecdac6885691b44a0bf39786686` |
| NF-007 Part 1 artifact | SHA-256 `bc51b33796c45b5d9db2b804ba9989f2b7cafce689b761bd2f07be3b3fb5f71d` |
| parent assignment digest | `29c026e653ab7f65b032b0b3104a6b24194d951d0fe740c913c5406b0756f9ca` |
| expanded statement assignment digest | `be4fc93ed80e5ff582074177729a1d60dcfb3897f758cb8cfdae4d99889ade14` |

The control must also re-verify all frozen hashes and cache seals inherited by
Part 1. It makes zero embedding and generation calls.

## Locked procedure

1. Reconstruct the 119-parent `k=16` assignment and expand it to the same 791
   statement identities used by NF-006. Require both assignment digests above.
2. Read exactly one record from the committed selection seal: arm
   `T1_OWN_STATEMENT`, `probe_turn=120`. Require 80 unique selected identities
   and require every identity to exist in the expanded assignment.
3. Map those identities to clusters without loading any domain label, Q11 fact
   key, or availability artifact.
4. Emit the sorted touched and missing cluster IDs, selected-unit counts by
   cluster, and `16 - touched_cluster_count` as the number of forced admissions
   required by a one-per-nonempty-cluster floor.
5. Record the existing selected statements' serialized character-cost
   distribution. The missing-cluster count is the exact number of forced
   admissions, not an assumed count of realized displacements: variable
   statement costs under a 32,000-character budget can displace a different
   number of incumbents. A later registered selector must report actual
   treatment-only admissions, control-only removals, and character deltas.

No alternate arm, probe turn, cluster count, selection size, or floor size is
computed.

## Binding branch

| Condition | Disposition |
|---|---|
| T1 touches all 16 clusters | `FLOOR_INERT_STOP`; stop NF-007 before full registration or selector implementation |
| T1 touches fewer than 16 clusters | `FLOOR_CAN_BIND`; a full NF-007 registration may be written with floor size 1 per nonempty cluster |
| Any frozen hash, population, assignment, arm, turn, or selected-count check fails | named integrity stop; no reachability claim |

`FLOOR_CAN_BIND` establishes only that the floor can alter candidate identities.
It does not establish that it fits the budget, recovers art, preserves monetary
facts, preserves targeted items, or improves reader answers. Those remain
separate preflight and outcome gates.

## Anti-vacuity rule

A stopping gate is not trusted merely because it returned its stopping branch.
Its tested population and positive alternative must be shown to exist. This
control is the anti-vacuity check for the proposed hard floor, just as the
preserved Part 1 invalid artifact demonstrates why a vacuous stopping result
cannot be interpreted as mechanism failure.
