# DA-048 Scratchpad

## 2026-08-31 - Registration

- Continue each frozen one-hop temporal edge exactly one episode in direction.
- Dedupe by first baseline-edge occurrence; user then assistant; first 32.
- Preserve strongest payload and retained register; replace current only.
- Seal blind stream before `has_answer`; zero model/embedder/cache calls.

## 2026-08-31 - Result

- Blind preflight sealed 4,273 second-hop episodes and 8,546 members; 6,670
  frames fit, peak 2,048 chars, and DA-038 remained immutable.
- One-frame oracle raises the protected DA-046 ceiling 250->295: +45/0,
  p=5.68e-14. Every question type is nonnegative.
- Gains arrive at ordinal p50 5 and cost p50 309 chars; cumulative traversal
  through the useful frame is p50 1,361 and p90 5,801.2 chars.
- This is structural capacity only. Recognition/stopping/reader use untested.
