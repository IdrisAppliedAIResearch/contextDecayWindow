# CC-006 — Embedding vector cache contract report

**Registration SHA:** `d2ddc1ca0a2c12cf7cdae2ae6f6a10d567c3a0fc`
**Implementation SHA:** `ef5164127462dc7e7f86ac02db3bb4a010f06af4`
**Outcome:** PASS
**Date:** 2026-08-05

## Result

`episodic.EmbeddingCache` now makes exact vector bytes a retained, asserted
run artifact rather than an assumption derived from model identity.

- Populate mode persists exact solo-call `float32` vectors by complete text
  and reuses repeated texts without another model call.
- Reuse mode requires both the SQLite file SHA-256 and a canonical SHA-256
  binding every UTF-8 text to its vector bytes.
- Reuse opens SQLite read-only, refuses misses, and has no model-call fallback.
- Model SHA-256, call shape, dtype, and dimension are asserted.
- The public provenance record includes both hashes, entries, hits, misses,
  model identity, call shape, dtype, and dimension.

## Gates

| Gate | Result |
|---|---|
| C1 repeated populate text makes one delegate call | PASS |
| C2 read-only reuse is byte-identical with zero model calls | PASS |
| C3 one altered vector byte fails canonical-content assertion | PASS |
| C4 wrong file hash fails before SQLite open | PASS |
| C5 reuse miss is fatal without a delegate call | PASS |
| C6 metadata mismatches fail loudly | PASS |
| C7 canonical digest is independent of insertion/database layout | PASS |
| C8 H1, persistence, extraction, and full suite remain green | PASS — 1,028 tests |
| C9 retained EC-002 cache adopts read-only | PASS |

## EC-002 adoption

The existing cache was inspected and then reopened through the public contract
without changing it:

- entries: 96,585;
- bytes: 1,050,013,696;
- file SHA-256:
  `e8a31513700a0a5d1cfe34b4703bbe3c8c85dc3ca29188d7cc480c2e2417a7ad`;
- canonical content SHA-256:
  `d60d723dea787b0d5bbd25a3c89f2a1c20b92a2a79813f34688a12e7c346a180`;
- read-only hits: 1;
- misses: 0;
- model calls: 0 by construction; and
- file and content hashes before and after: identical.

Artifact:
`artifacts/cc006/ec002_legacy_adoption.json`
(`baadf6cced1c1728860dbe635bd5fc314587a7a1d85272db6acec9ec51883f24`).

## What the contract does not repair

This guarantee begins when exact vectors are retained. It does not regenerate
missing historical bytes.

EC-001's original cache is unrecoverable, so EC-001 remains permanently
unreplayable at bit granularity. Its Tier 1 headline values reproduce in
aggregate under EC-002 Amendment 001, but neither this contract nor the
retained EC-002 cache can reconstruct the vectors EC-001 originally used.

EC-002 is different: its recomputed A0 cache still exists, is now bound by both
hashes, and can be reused exactly for A1.

## Surrogate audit

A model hash plus call-shape sentinel can pass while other vector bytes move;
the canonical digest covers the complete retained cache. A file hash can pass
while offering no semantic account of which text owns which vector; the
content digest binds both. A zero-miss count can pass if nothing is requested;
C9 performs an actual read-only sentinel lookup and the unit gates cover every
fixture vector.

## Scope

No retrieval, ranking, selector, threshold, packing, rendering, or budget code
changed. No EC-001 artifact changed. No A1 result was produced on this branch.

