# DA-099 Scratchpad

- Freeze `encode_members` as the exact semantic oracle.
- Build one member-separated online index per allocation.
- Preserve earliest source coordinates and sequential payload references.
- Test exact subset equivalence before the full DA-098 replay.
- Time allocation separately from loading, ranking and serialization.

## Blind Equivalence Development

- The first exact 18-row oracle pass matched all legacy allocations. Indexed
  p50/p95/max was 281.28/358.92/374.85 ms versus legacy
  13,632.95/18,793.82/19,417.56 ms.
- Constant-time role charging and single-pass prefix indexing preserved all 18
  allocation hashes and reduced indexed p50/p95/max to
  156.35/186.30/210.43 ms.
- Fast exact varint-length charging preserved the sealed oracle hash on 18/18.
  Warm indexed replay was p50/p95/max 67.15/152.34/153.24 ms. These are blind
  mechanics; the registered full-population runtime gate remains unopened.
