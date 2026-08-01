# Library Extraction Memory Update

**Status:** CC-002 COMPLETE, 2026-08-01. Registration `b6c31de4`.

The deployable memory component lives in the installable `episodic`
package (`episodic/` at the repository root, three-symbol API). The
harness imports the library; the direction of dependency is the point.
Extraction is certified behavior-preserving: 132/132 committed A3
selection payload SHAs and 3/3 committed DR-001 rendered blocks reproduce
byte-for-byte through the library (T3/T4), the suite is green at 804 with
the harness consuming it (T6), and `context()` is byte-identical across
processes (T7).

Carry forward:

1. **A refactor gets a replay gate, same as a study.** T3 was registered
   as "if the number moves, the extraction changed behavior, and the PR
   does not merge until the cause is found." Byte-identity over committed
   artifacts is what makes "extraction moves code; it does not improve
   it" checkable rather than aspirational.
2. **Hazards ship as gates, not documentation.** H1 (embedder call-shape
   dependence, from DX-001) is a sentinel-vector assertion on every store
   open; H2 (pool-trimming brittleness, from DR-002) is a default plus an
   `unsafe_` name whose docstring carries the finding. A README footnote
   would have been silent in exactly the deployments that matter.
3. **SHA-pinning tests must pin commits, not working trees.** DX-001's B7
   guard hashed the live `e005.py` against the committed integrity
   record; an authorized move necessarily breaks that form. Re-anchoring
   it to `git show` at the DX-001 close commit preserves the certified
   invariant through legitimate refactors. Expect this pattern whenever a
   mechanism file is pinned by hash.
4. **The spec's own numbers age.** CC-002 was drafted before DX-001
   landed: it says "suite green (778)" and "PRs #25, #26 merged"; reality
   at execution was 792 tests (778 + 14 DX-001) and #26/#27 still open,
   stacked. Executing a spec includes reconciling its snapshot against
   the tree, on the record.
5. **What did not move is as deliberate as what did.** A1/A2 (O(n^2)
   similarity), span rendering (distillation output), the batched
   `embed_many` path (the committed call shape - reproduction machinery,
   not production), and the graveyard all stay in the harness. The
   library serializes only what it can produce.

Authoritative files:

- `CC_002_library_extraction.md` (registration `b6c31de4`)
- `../../../episodic/README.md` - measured claims with artifact hashes
- `artifacts/cc002/t3_e005_replay.json`
- `artifacts/cc002/t4_render_replay.json`
- `../../../scripts/verify_cc002_t3.py`, `verify_cc002_t4.py`
- `../../../tests/test_cc002_extraction.py` (T2, T5, T7)

Queued behind this: CC-003 budget enforcement/truncation semantics,
CC-004 restart persistence as a tested guarantee, CC-005 eviction,
the LongMemEval identity slice, E006 (proposed, unauthorized).
