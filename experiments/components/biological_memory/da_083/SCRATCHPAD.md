# DA-083 Scratchpad

## 2026-08-31 - Diagnostic Lock

- Graph: frozen DA-045 baseline `seed_id -> neighbor_id` edges.
- Roots: episodes with any member in immutable DA-078.
- Exact source-order BFS; no reversed or added adjacency.
- States: root member, linked path, or orphan parent.
- No feature, score, answer, or path tuning.
- Zero model/embedder/cache calls.

## 2026-08-31 - Result

- States: 7 linked paths, 1 root member, 5 orphan parents.
- Every linked path has depth one; child degree p50 1/p90 2.
- Combined descriptively with lexical novelty, structural coverage is 11/13.
- The two uncovered rows are redundant-at-arrival plus orphan-parent.
- Next signal: bounded transient parent-to-child bridge with explicit edge identity.
- Byte-identical replay; zero calls.
