# Amendment 007 - PS-001 Trace Identity

**Date:** August 11, 2026
**Applies to:** `PS_001_PATTERN_SEPARATED_ENGRAM_FORMATION.md`
**Design anchor:** `e20d0c0035fc96d0c9181df67d0a0c8eebd5c368`
**Authorization anchor:** `90e88f86`
**Amendment 006 anchor:** `3079316d0ee7172dc397a54425cf71ef1638fb63`
**Status:** PROSPECTIVE - REQUIRES EXACT STANDALONE AUTHORIZATION

## Trigger and evidence

The final pre-implementation trace audit found two remaining byte-identity gaps:

- Section 4.4 requires a descriptive registered quadratic score but gives no
  equation or sign convention.
- Sections 4.5 and 5.5 require SHA-derived coordinate permutations and random
  exact-sparsity states but do not fully specify conversion of counter bytes to
  a permutation or identify the four deterministic random-state seeds.

Neither value changes a registered gate threshold, but both change committed
trace bytes. They therefore must be fixed prospectively rather than selected in
code.

## Change

The following trace-identity rules are binding:

1. For binary state `s`, `v = s - a`, and the registered zero-diagonal
   operator, the descriptive quadratic score is
   `0.5 * dot(v, W_times(v))`. It is recorded at the initial state and after
   every completed synchronous sweep. It is descriptive only and is not a
   convergence or monotonicity gate.
2. A domain seed is `SHA256(ascii(domain) || content_sha256_bytes)`, where the
   domains are exactly `active`, `inactive`, and `random`.
3. To permute a sorted coordinate pool, concatenate blocks
   `SHA256(domain_seed || uint64_be(counter))` from counter zero. Consume each
   block as eight ascending four-byte big-endian unsigned integers. Reduce each
   integer modulo the pool length; append the coordinate at that pool position
   only if it has not already appeared. Continue until every pool coordinate
   appears. This carries Rev 4's unique modulo-selection serialization while
   adapting it to active and inactive pools.
4. The four random exact-sparsity degenerate states use the first four content
   SHA-256 identities in ascending content-hash order. For each identity, the
   first `K_ACTIVE` indices from the `random` permutation of `range(D_CODE)` are
   active.
5. The union-biased state activates the `K_ACTIVE` units with highest stored
   population activation count, breaking ties by ascending unit index. The
   lowest- and highest-index states use their literal ordered ranges.

## Rationale

These resolutions make every registered trace and degenerate cue reproducible
without a Python or NumPy random stream. The quadratic sign treats stronger
centered recurrent support as a larger score and avoids importing Rev 4's
inapplicable asynchronous Hopfield energy gate.

## Exclusions

This amendment changes no episode, projection, code, learned weight, recall
transition, corruption count, grid cell, gate, threshold, selection rule,
resource ceiling, disposition, or interpretation. The quadratic score cannot
rescue a wrong state, cycle, runtime exit, or failed exact recovery. No new cue,
seed sweep, model call, query, label, retrieval measure, or live work is added.

## Author authorization

The program author authorized end-to-end PS-001 implementation and assigned
responsibility for prospective revisions required by the locked protocol. This
amendment applies that authority narrowly to trace-byte identity discovered
before implementation. It does not itself authorize affected code; exact
standalone authorization must bind its commit and SHA-256 first.
