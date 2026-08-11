# TA-001 Amendment 001 - Query Vector Cache Correction

**Date:** August 11, 2026
**Design anchor:** `23cff2d8da6e864363b05d2438398f9b60c8893b`
**Authorization anchor:** `43d4e764ef95cd1b89a6037d925824a686221991`
**Status:** AUTHORIZED PROSPECTIVE INPUT REPAIR

## Trigger and evidence

Pre-implementation PF1 inspection found that the registered
`experiments/surveys/retrieval_bakeoff/cache/c121_l_span_embeddings.sqlite`
contains 2,759 span-text embeddings but zero exact rows for the 24 sealed query
texts. It therefore cannot supply the registered holdout query vectors.

The already committed E006 Tier-4A query capture contains exactly one 1,024
dimensional float32 solo-call vector for each of the 24 sealed query texts. Its
schema is `cache(text TEXT PRIMARY KEY, embedding BLOB NOT NULL)` and it contains
48 total query rows plus five metadata rows.

## Change

Replace only the read-only query-vector cache input in Section 2:

| Input | Bytes | SHA-256 |
|---|---:|---|
| E006 Tier-4A query-vector cache | 249,856 | `D9741EDB0545D8CFE050663340599A31813D6025C38F0467E0EC7671573A1E6A` |
| E006 Tier-4A capture manifest | 17,131 | `2C24EA75D7551BEB6658D8B9208225B985E25A9111CFD3766EC4F7980A7F18E4` |

The cache metadata must equal:

```text
cache_version = episodic-embedding-cache-v1
model_sha256 = 06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439
call_shape = solo
dtype = float32
dimension = 1024
```

PF1 now requires 24/24 exact text hits in this cache and a manifest-consistent
file identity. The originally registered span cache remains an immutable
audited input proving the trigger, but it is not read by the mechanism.

## Rationale

This repairs an input-path mismatch discovered before implementation or
outcome inspection. It does not add vectors, make an embedding request, change
the query population, or alter any arm, parameter, threshold, gate, or metric.

## Exclusions

This amendment does not authorize cache writes, fallback embedding calls,
query normalization changes, relevance-label access, a parameter sweep, or any
change to the locked temporal-adjacency policy.

## Author authorization

The author's August 11 instruction assigned end-to-end responsibility for the
preregistered temporal-adjacency study. That authorization includes genuine
blocker amendments that preserve the registered design and fail closed. This
amendment is bound to the design and authorization anchors above and is
committed before implementation.
