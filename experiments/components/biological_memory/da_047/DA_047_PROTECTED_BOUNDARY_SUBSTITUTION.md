# DA-047 Protected Boundary Substitution Contract

**Status:** `REGISTERED; BLIND CONTRACT ONLY`
**Date:** August 31, 2026
**Parent:** DA-046 result commit `8e24d3be`
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Can substitutions be admitted near the capacity boundary without changing the
strongest delivered order or the one retained dependency frame?

DA-020 established that smaller, more query-similar replacements are not an
evidence-protection invariant. DA-047 therefore does not score substitutions or
permit them inside the strongest pack.

## 2. Frozen State

The DA-038 payload, DA-045 traversal order, and DA-046 retained register remain
immutable. Only DA-046's transient `current` frame is replaceable. A rejected
operation must leave all state byte-identical.

## 3. Evidence-Blind Rule

A replacement is admissible only when `current` contains a valid frame, the
replacement is exact and hash-verified, its cost is no greater than the current
frame, it fits 2,048 characters, and `retained` remains unchanged. The operation
is atomic. No question, answer, evidence identity, label, similarity, fitted
feature, outcome, or model output enters admission.

## 4. Gates

Tests exercise accepted, larger-cost, empty-current, malformed-hash, and
retained-frame cases. Require exact rollback after rejection, unchanged retained
bytes, nonincreasing current cost, and zero model or embedding calls.

## 5. Boundary

This permits replacement only in independently replaceable boundary capacity.
It does not claim that a blind rule chooses a useful frame or improves delivery.
The strongest order remains immutable; outcome analysis is not authorized.
