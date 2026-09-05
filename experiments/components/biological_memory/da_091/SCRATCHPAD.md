# DA-091 Scratchpad

- Freeze DA-090 artifact SHA-256 and preserve all non-edge-stream rows.
- Typed metadata carries identity and relation; it is not charged as prompt
  payload and cannot replace any DA-078 material.
- Reuse DA-090 packet codec unchanged for exact child bytes.
- This tests structural provenance removal, not a selector or substitution
  score.

## Result

- 798/798 eligible edge streams strictly reduced cumulative charge.
- Median savings: 2,220.5 chars; p90: 3,264.3 chars.
- Child-only stream: p50 2 frames, 2,098 cumulative chars, 1,817 peak chars.
- All 7,257 noneligible rows preserved; zero DA-078 mutations.
- Byte-identical replay; zero model/embedder/cache calls.
