# DA-034 NF Sentinel-Only Varint Pointers Report

**Status:** `NO_NF_SENTINEL_VARINT_SIGNAL`
**Date:** August 30, 2026
**Protocol commit:** `eebf2508`
**Codec commit:** `c2c96e4e`
**Blind allocation commit:** `818e82d5`
**Standing:** spent NF exact-availability result

## Result

Removing the per-reference opcode creates substantial exact capacity but no NF
delivery gain.

| Control | Treatment | Gains | Losses |
|---:|---:|---:|---:|
| 983 | 983 | 0 | 0 |

Sentinel encoding is strictly shorter on all 1,098 questions and saves median
823 characters beyond DA-031. It funds 371 full-pair and 18 frozen-member
admissions, with no expansion, displacement or replay drift.

## Why Capacity Did Not Convert

The new admissions occur late in the frozen traversal: median position 15,
versus 12 under DA-031. They preserve the same full-carrier-then-frozen-member
policy, so none emits the alternate members required by NF's final three items.

This is stronger than a generic capacity null. DA-031 proved denser pointers can
recover prior-consumption evidence. DA-034 then adds another 823 characters yet
does nothing because dependency materialization remains at the wrong unit. The
remaining ceiling is therefore a representation-of-dependency problem:
recovered capacity must address members, not only carriers.

The supported successor freezes all DA-031 evidence and spends only sentinel-
recovered capacity on evidence-blind atomic members in the same carrier order.
That changes no control payload and introduces no substitution score.

Blind allocation SHA-256 is
`3454fd7a148100b805a860b3a17d947eefb7c349fef721bf06e0b103b4f5d42f`;
outcomes replay byte-identically at
`672498f7b4aa80e05446cca1146c20425c5cbf5a8e0ac3fab1a2edd088c6eaff`.
There were zero model, embedding and cache calls. No reader/runtime/adoption
claim follows.

