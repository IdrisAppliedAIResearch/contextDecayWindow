# Retrieval Bakeoff Holdout Lock Validation

**Status:** PASS before any registered retrieval test  
**Registration anchor:** `b60b7084741eb5d30298261076b4bca78abe713a`

## Structure

- `lineage_121_preprobe`: 12 lookup, 8 chained, 4 enumeration queries.
- `study_010_preterminal`: 12 lookup, 8 chained, 4 enumeration queries.
- Query IDs are unique and appear in identical order in each manifest and its measurement-only key.
- Every query names at least one registered fact; every named fact exists in its key.

## Temporal And Source Validation

- Every 121-lineage source turn is in the registered range 1–111.
- Every Study 010 source turn is in the registered range 1–986.
- Every required term occurs in every declared user-authored source turn.
- All 28 121-lineage facts are captured in both the Study 007 treatment raw store and Study 009 Arm S raw store.
- All 48 Study 010 facts are captured in both Arm S and Arm L raw stores.

## Disjointness

- No required term in the 121-lineage key occurs in `experiments/study_007/q_facts_key.md`.
- No required term in the Study 010 key occurs in `experiments/study_010/q_facts_key_1000.md`.
- All 48 queries are fact-disjoint from their corpus's burned rubric key; the committed overlap matrix records zero overlaps per query.
- Query wording is new and does not reuse a registered probe.

## Leakage Boundary

`queries_121.json` and `queries_1000.json` are mechanism-visible. The two
`answer_key_*.json` files and `overlap_matrix.csv` are measurement-only. Retrieval,
indexing, routing, graph construction, and runtime context assembly may not read
or import the measurement-only files.
