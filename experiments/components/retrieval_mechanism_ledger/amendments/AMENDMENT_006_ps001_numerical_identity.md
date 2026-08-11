# Amendment 006 - PS-001 Numerical Identity

**Date:** August 11, 2026
**Applies to:** `PS_001_PATTERN_SEPARATED_ENGRAM_FORMATION.md`
**Design anchor:** `e20d0c0035fc96d0c9181df67d0a0c8eebd5c368`
**Design SHA-256:** `B525452743673BEC8FBD45E80E81AE2A6342872B2BB58D858F2C544CA315FC6A`
**Authorization anchor:** `90e88f86`
**Status:** PROSPECTIVE - REQUIRES EXACT STANDALONE AUTHORIZATION

## Trigger and evidence

The post-authorization implementation audit found four numerical literals that
the locked design requires before exploration but does not resolve:

- Section 4.1 requires the normalization and population-center summation order
  and dtype to be specified and rejects an unidentified BLAS reduction.
- Section 4.2 requires a repository-owned SHA-256 counter-mode projection but
  does not specify counter serialization or digest-bit mapping.
- Section 4.3 requires a real-state field tolerance fixed before exploration
  but does not provide its value.
- Section 8 requires any additional surrogate residual to be recorded before
  implementation.

Choosing these values in implementation would silently add design parameters
after the registered anchor. This amendment fixes identity and audit behavior
without changing a grid cell, equation, gate, threshold, or disposition.

## Change

The following resolutions are binding for PS-001:

1. Raw float32 vectors are converted to explicit little-endian float64. Each
   norm is `sqrt(sum_j x[j] * x[j])`, accumulated in ascending coordinate order
   from a float64 zero. Division is coordinate-wise float64.
2. Population rows are sorted lexicographically by their normalized C-order
   float64 bytes, independently of source identity and input order. The center
   starts from float64 zeros, adds rows in that order one row at a time, and
   divides coordinate-wise by the exact integer row count. Centered vectors use
   one float64 subtraction per coordinate.
3. The projection stream concatenates
   `SHA256(seed || uint64_be(counter))` for counters beginning at zero. Digest
   bytes and their bits are consumed in ascending order, most-significant bit
   first. Bit zero maps to `-1`; bit one maps to `+1`.
4. Projection activations start at float64 zero and accumulate coordinates in
   ascending index order as `activation += R[:, j] * y[j]`. Division uses the
   float64 value `sqrt(1024)`, exactly `32.0`. No BLAS reduction may replace
   this registered accumulation when code bytes are formed.
5. Persisted numeric arrays use explicit little-endian dtypes and C order.
   Array hashes include canonical dtype and shape headers before the bytes.
6. The production low-rank field operator is compared with an independent
   conceptual-weight implementation using absolute tolerance `1e-10` and zero
   relative tolerance. Every registered reference field must pass. Any active
   versus inactive boundary margin at or below `2e-10` is reported as
   numerically tie-sensitive; exact index tie-breaking remains binding.
7. The additional surrogate residual is: exact storage and recovery can pass
   because deterministic unit-index tie-breaking resolves zero or near-zero
   field margins while learned recurrent evidence is weak. The control is the
   complete field-margin distribution and tie-sensitive count. Such a pass is
   exact component behavior but cannot support a perturbation-robustness claim.

## Rationale

These rules make encoder bytes independent of input row order and remove
version-dependent pseudorandom streams and unidentified reduction trees. The
field tolerance is many orders above normal float64 accumulation error at the
registered dimensions while remaining far below a scientifically meaningful
competition margin. The margin residual prevents deterministic tie-breaking
from silently certifying robust attractor support.

## Exclusions

This amendment does not alter the 119 episodes, projection seed, nine cells,
activity counts, centered covariance equation, low-rank production operator,
recall update, corruption levels, G1-G5 bars, selection rule, resource limits,
zero-call boundary, outcome ceiling, or prohibited interpretations. It adds no
seed sweep, parameter search, query, label, retrieval, live run, or favorable
expected result.

## Author authorization

The program author authorized end-to-end PS-001 implementation and assigned
responsibility for prospective revisions required by the locked protocol. This
amendment records the narrow pre-output numerical resolutions needed to make
that implementation identifiable. It does not itself authorize affected code;
standalone authorization must bind its commit and SHA-256 first.
