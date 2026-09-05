# DA-083 Provenance-Path Anatomy

**Status:** `POSTHOC_PROVENANCE_PATHS_CHARACTERIZED`
**Date:** August 31, 2026
**Parent:** DA-082 result commit `d8843dcd`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Does the frozen seed-to-neighbor dependency graph provide a directed linked
path from an immutable DA-078 episode to each of the 13 residual carriers?

## Fixed Graph

Use each question's sealed DA-045 baseline actions as directed episode edges
`seed_id -> neighbor_id`. Deduplicate edges by first appearance and preserve
their source order. Define roots as episode identities with at least one member
in the sealed DA-078 prompt. For each sealed DA-079 carrier, run unweighted BFS
from all roots and report shortest depth, number of shortest parents, path edge
ordinals, and child degrees along the chosen source-order path.

Classify `ROOT_MEMBER` at depth zero, `LINKED_PATH` at positive finite depth,
or `ORPHAN_PARENT` when unreachable. Do not reverse edges, add corpus adjacency,
score paths, use text features, or inspect answers.

Require exact 13/13 joins, frozen graph/root identities, byte-identical replay,
and zero model, embedding, and cache calls. This is provenance anatomy only;
no reader, stopping, transfer, delivery, or adoption claim.

## Result

Seven residual carriers are `LINKED_PATH`, one is `ROOT_MEMBER`, and five are
`ORPHAN_PARENT`. Every finite non-root path has depth one. Path child degree is
p50 one and p90 two, so explicit provenance is shallow and usually narrow when
its parent is represented.

Provenance and DA-081 novelty are complementary: four lexically redundant
targets have linked paths, while three lexical-novel targets have orphan
parents. Their descriptive union covers 11/13. The two uncovered rows are both
lexically redundant orphan-parent cases, motivating a transient parent-to-child
bridge rather than another ranking score. Byte-identical replay; zero calls.

Artifacts:

- `artifacts/analysis/result.json`
- `artifacts/analysis/paths.jsonl.gz`
