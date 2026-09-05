# DA-035 NF Sentinel Capacity With Atomic Dependencies Report

**Status:** `NF_SENTINEL_ATOMIC_SIGNAL`
**Date:** August 30, 2026
**Protocol commit:** `6d849b73`
**Blind allocation commit:** `92d74be1`
**Standing:** spent NF exact-availability result

## Result

Atomic member materialization inside sentinel-recovered capacity closes NF's
entire one-hop-reachable gap.

| Control | Treatment | Gains | Losses | One-hop ceiling |
|---:|---:|---:|---:|---:|
| 983 | **986** | **3** | 0 | **986** |

Conv-43 gains one and conv-49 gains two. Every conversation is nonnegative.
All three gains are DA-032 wrong-frozen-member residuals.

## Causal Contrast

DA-034 and DA-035 use the same sentinel codec and recover the same immutable
capacity from the same DA-031 control:

- DA-034 spends it on full carriers then frozen members: 389 admissions, 0 gains.
- DA-035 spends it on independent members: 3,401 admissions, 3 gains.

The control payloads, order, budget and evidence-blind traversal remain fixed.
Only the unit represented in newly available capacity changes. This isolates
atomic dependency identity as the mechanism that converts capacity into final
evidence delivery.

The result supports the linked-structure interpretation developed earlier:
facts remain immutable nodes; temporal/session links expose candidate carriers;
compact pointers preserve traversal capacity; atomic member references select
the smallest dependency unit without displacing established evidence.

## Boundary

NF reaches its frozen one-hop availability ceiling, not a reader-performance
ceiling. The sentinel syntax and atomic references remain unvalidated with a
live reader and have no runtime optimization. No claim extends beyond the spent
NF holdout or beyond evidence availability.

Blind allocation SHA-256 is
`97ecf4eb74b0c88914dafa6f063643249662e0b264d623a9c311a2b20e35ebd7`;
outcomes replay byte-identically at
`1bfb4d2eaad834229016d88a66d4f96950b1bb6029a5a9b5240b55f3fc2dd43e`.
There were zero model, embedding and cache calls. No adoption follows.

