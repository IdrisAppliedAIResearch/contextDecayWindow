# Amendment 008 - PS-001 Carried Normalization Identity

**Date:** August 11, 2026
**Applies to:** `PS_001_PATTERN_SEPARATED_ENGRAM_FORMATION.md`
**Design anchor:** `e20d0c0035fc96d0c9181df67d0a0c8eebd5c368`
**Amendment 006 anchor:** `3079316d0ee7172dc397a54425cf71ef1638fb63`
**Status:** PROSPECTIVE - REQUIRES EXACT STANDALONE AUTHORIZATION

## Trigger and evidence

Before implementation was committed or PS-001 output was generated, the real
input identity test showed that Amendment 006 item 1 changed a carried
subsystem. Its coordinate-by-coordinate norm produced normalized matrix
SHA-256 `66118A1D4D98743787C25A3535FB5CBD25ADBE4E42890E20919BC358E41F52B5`.
The immutable Rev 4 loader and artifact use
`2ED0CC29B0DE9B54BF80BBD800123938ECAAC2353B3E01ECE37E397B6844E27B`.
The maximum element difference is approximately `4.996e-16`, but byte identity
is binding and PS-001 carries the normalized population unchanged.

The discrepancy would violate G1, PF1, the single-component boundary, and the
standing rule against altering a carried subsystem. It cannot be accepted as a
numerically harmless implementation choice.

## Change

Amendment 006 item 1 is superseded only for row normalization:

1. Raw embeddings are read as committed little-endian float32 and converted
   element-wise to little-endian float64.
2. For each row matrix, squared values are formed by float64 element-wise
   multiplication. The coordinate reduction is NumPy float64 `add.reduce` over
   axis 1 in the committed runtime, followed by float64 square root and
   coordinate-wise division. This is byte-identical to the Rev 4
   `np.linalg.norm(..., axis=1, keepdims=True)` path in the committed runtime.
3. Before any encoding, the complete normalized matrix must equal SHA-256
   `2ED0CC29B0DE9B54BF80BBD800123938ECAAC2353B3E01ECE37E397B6844E27B`
   under the registered dtype-and-shape array header. A runtime or reduction
   implementation that does not reproduce those bytes fails G1; it is not an
   alternate encoder.

Amendment 006's byte-sorted population-center order, projection accumulation,
array serialization, field tolerance, and tie-sensitive residual remain
unchanged.

## Rationale

This restores the exact carried input rather than changing PS-001's new sparse
component. The digest assertion resolves cross-runtime reduction ambiguity and
implements the design's rule that a different reduction is not accepted unless
the bytes reproduce.

## Exclusions

This amendment changes no source episode, vector value relative to Rev 4,
population center rule, projection, code, recurrence, corruption, cell, gate,
threshold, selection rule, resource ceiling, or interpretation. It cannot make
a PS-001 outcome favorable; failure to reproduce the carried digest stops G1.

## Author authorization

The program author authorized end-to-end implementation and assigned
responsibility for prospective revisions. This amendment narrowly repairs a
pre-output conflict between Amendment 006 and the locked carried-input boundary.
It does not itself authorize affected implementation; exact standalone
authorization must bind its commit and SHA-256 first.
