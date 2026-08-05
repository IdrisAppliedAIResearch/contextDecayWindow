# CC-006 — Embedding vector cache contract

**Type:** Engineering correctness specification. Not a retrieval study.
**Repository:** `contextDecayWindow` · installable `episodic` package
**Branch:** `cc/006-embedding-vector-cache`
**Status:** PRE-REGISTERED — implementation must follow this commit
**Depends on:** CC-002 H1 call-shape sentinel · EC-002 amended A0 PASS
**Authorization:** Program author, August 5, 2026

## 1. Trigger

EC-002 could not reproduce EC-001 bit-for-bit even with the same dataset,
embedding model artifact, solo call shape, configuration, seed, and budget.
One evidence-session rank moved from 21 to 20 and one question delivered one
additional coverage episode. The original EC-001 embedding cache was not
retained and is unrecoverable.

This is the second recorded case in which nominally identical embedding
conditions moved downstream selection. A pinned model hash plus the H1
call-shape sentinel is therefore insufficient to reproduce a run's vectors.

## 2. Contract

Add a public `episodic.EmbeddingCache` wrapper with two modes:

### Populate

- Accept exactly one text per call and delegate misses to the pinned solo-call
  embedder.
- Persist the exact `float32` vector bytes keyed by the complete UTF-8 text.
- Return the persisted bytes on every repeated text without another model call.
- Refuse to overwrite an existing cache path.
- Store model SHA-256, call shape (`solo`), dtype (`float32`), and dimension.

### Reuse

- Open the SQLite cache read-only.
- Require and assert the recorded whole-file SHA-256 before opening.
- Require and assert a canonical content SHA-256 over cache metadata plus every
  text and exact vector byte string in sorted-text order.
- Return only persisted vectors; a missing text raises before any delegate call.
- Make zero model calls.
- Reject model, call-shape, dtype, or dimension metadata mismatch.

The wrapper exposes entry count, hit count, miss count, file SHA-256, and
canonical content SHA-256 for run provenance.

## 3. Canonical content digest

The digest is versioned as `episodic-embedding-cache-v1` and includes:

1. model SHA-256;
2. call shape;
3. dtype;
4. vector dimension; and
5. for every row in UTF-8 text sort order, length-prefixed text bytes followed
   by length-prefixed vector bytes.

The length prefixes prevent concatenation ambiguity. Hashing only SQLite file
bytes is not sufficient because database layout is not the vector contract;
hashing only vectors is not sufficient because it could detach a vector from
its text.

## 4. Relationship to H1 and store purity

H1 remains unchanged: `EpisodeStore` still checks the solo-call sentinel.
`EmbeddingCache` is an embedder wrapper, not a retrieval or store-policy
change. It does not alter ranking, selection, packing, rendering, budgets, or
the `EpisodeStore` schema.

In populate mode the cache mutates, but `EpisodeStore.context()` remains
non-mutating with respect to the episode store and remains byte-deterministic
for the same vector inputs. In reuse mode both the episode store and cache are
read-only.

## 5. Acceptance gates

| Gate | Requirement |
|---|---|
| C1 | Two calls with identical text in populate mode make one delegate call and return bit-identical vectors. |
| C2 | Reuse of a sealed fixture makes zero delegate calls and reproduces every vector byte-for-byte. |
| C3 | Altering one cached vector byte makes canonical-content assertion fail on open. |
| C4 | A wrong expected whole-file SHA-256 fails before SQLite is opened. |
| C5 | A reuse-mode cache miss fails with zero delegate calls. |
| C6 | Model, call-shape, dtype, and dimension metadata mismatches fail loudly. |
| C7 | Two independently populated caches from identical supplied vector bytes have the same canonical content digest, regardless of SQLite file layout. |
| C8 | Existing `EpisodeStore` H1 sentinel and all library/harness tests remain green. |
| C9 | EC-002 adopts its already-created cache read-only through this public contract, asserts its recorded file hash, and makes zero new model calls. |

## 6. Surrogate audit

- **A file hash alone can pass while the wrong text is bound to a vector.**
  C3 and the canonical text-plus-vector digest close that gap.
- **A cache hit rate can pass with missing required inputs.** C5 makes every
  miss fatal in reuse mode; EC-002 must record zero misses.
- **A sentinel can pass while other vectors move.** H1 continues to certify
  call shape; the cache digest certifies the complete vectors actually used.
- **A cache can make a result repeatable but not historically reproducible.**
  The limitation below is mandatory.

## 7. Historical limitation

This contract guarantees vector identity only for runs whose vectors are
retained in, and later reopened from, a hashed cache. It does not reconstruct
or repair earlier vectors.

EC-001 remains permanently unreplayable at bit granularity because its cache
is unrecoverable. Its headline Tier 1 values are reproducible in aggregate
under EC-002 Amendment 001, not bit-reproducible. EC-002's retained cache can
be adopted read-only because its exact file still exists and its A0 gate
records the file SHA-256.

## 8. Exclusions

- No EC-001 artifact is edited.
- No retrieval, selector, threshold, packing, renderer, or budget change.
- No A1 result is produced on this branch.
- No claim that model hash plus call shape reproduces uncached vectors.
- No transparent fallback to a model call in reuse mode.

## 9. Deliverables and order

1. Commit this specification alone.
2. Implement `EmbeddingCache`, public export, tests, and package documentation.
3. Commit gate evidence and a short CC-006 report.
4. Update root README, AGENTS digest (at most 400 characters), and memory.
5. Push and open a dedicated CC-006 pull request.
6. Only after this contract is committed may EC-002 consume it and run A1.
