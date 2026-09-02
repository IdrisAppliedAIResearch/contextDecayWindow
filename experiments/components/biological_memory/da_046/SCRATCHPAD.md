# DA-046 Scratchpad

## 2026-08-30 - Registration

- Seal current/retained/next/keep/answer semantics before evidence.
- Keep prompt immutable and each register <=2,048 chars.
- Use evidence only afterward for explicit oracle retention sufficiency.
- Recognition and stopping remain untested. Zero calls.

## 2026-08-31 - Result

- Blind contract passes with immutable DA-038 prompt/stream hashes, exact
  replay, guarded `KEEP`, 2,048-char registers and 4,096 general peak cap.
- Oracle retention raises complete availability 232->250: 18 gains, 0 losses,
  p=7.63e-6, reaching the frozen one-hop ceiling.
- Oracle path peak is <=2,047 chars; retained payload p50 is 355 chars.
  Cumulative traversal remains p50 5,569 and p90 17,692 chars.
- One exact retained frame is mechanically sufficient. Recognition, `KEEP`
  choice, stopping and reader use remain untested.
