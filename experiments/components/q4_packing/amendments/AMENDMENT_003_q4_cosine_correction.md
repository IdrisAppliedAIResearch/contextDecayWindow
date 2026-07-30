# AS-001 Amendment 003 - Q4 Cosine Correction

**Date:** 2026-07-29
**Authorization:** The author explicitly allowed amendments for these follow-up
documents.
**Timing:** Raised after two pre-output source gates stopped and before any
post-fix packing output was generated or opened.

## Trigger and Evidence

The committed Q4 exclusion trace reports the turn-55/Q4-query cosine as
`0.16612689197063446`. Amendment 001 required deterministic reconstruction to
reproduce that value.

Reconstruction from the committed turn log produced a turn-55 embedding whose
bytes exactly match the ignored local database vector:

- candidate vector SHA-256:
  `cb56d92738f305e58fb794ea489f0e8d841f21b90bbdb7aeb239c34b674ba6b8`;
- source user and assistant strings: exact equality;
- stored episode identity: exact equality.

Embedding the exact committed turn-115 user query produced query-vector
SHA-256
`81d69c52b538a5a4e33e3f68972980bbab781b30f6e3c7eca55a454b0ded93f4`.
The resulting cosine is `0.12042197585105896`.

The `0.16612689197063446` value first appears in commit `d808307b` and has no
committed generating code. It is not reproducible from the committed query and
the original stored candidate vector.

## Change

1. Correct the authoritative turn-55/Q4-query cosine from
   `0.16612689197063446` to `0.12042197585105896`.
2. Require deterministic replay to reproduce the corrected value within
   `1e-7`.
3. Preserve the superseded value in the AS-001 result and `ERRATA.md`.
4. Continue AS-001 because both values are below the unchanged registered
   `K=0.48` threshold; the K-ineligibility classification is unchanged.

This supersedes Amendment 001's requirement to reproduce the incorrect value
and AS-001's corresponding locked-input row.

## Rationale

This is a derived-statistic correction with stronger evidence than the
superseded artifact: exact source strings, exact original candidate-vector
bytes, a hash-identified query vector, and a deterministic recomputation. It
does not make any AS-001 decision branch easier because cosine does not control
the N-first packing replay.

## Exclusions

This amendment does not edit the historical trace, change K, add a K candidate,
alter N order, change rendering or budget, score an answer, or authorize
inference. If the corrected value fails to reproduce, AS-001 stops.
