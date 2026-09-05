# DA-092 Scratchpad

- Exact content identity only; no semantic deduplication.
- Preserve DA-091 rows and costs. This audit does not alter prompts.
- Separate shared-store reuse from per-question exposure capacity.
- Zero model, embedder and cache calls.

## Result

- 8,055 references -> 7,659 exact nodes; 396 reuse (4.92%).
- Shared storage saves 788,890 chars (6.26%), below the 10% node bar.
- Median/p90 references and questions per node are all 1; max references 4.
- Exact collision-free resolution; DA-091 and exposure unchanged.
- Dead end for capacity. Preserve content identity, pivot to prompt-relative
  exact child encoding.
