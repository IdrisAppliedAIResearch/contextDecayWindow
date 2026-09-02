# DA-045 Scratchpad

## 2026-08-30 - Registration

- Traverse the fixed first 32 dependency nodes.
- Expose one canonical <=2,048-char frame at a time; replace prior frames.
- Keep DA-038 prompt and DA-042 graph immutable.
- Report peak and cumulative cost separately. Zero calls.

## 2026-08-30 - Result

- Blind stream passes: 4,905 frames, 3,101 oversized-node overflows, immutable
  DA-038 prompt, byte-identical replay. Peak is capped at 2,048 chars.
- All 18 residual payloads are exactly exposed in a frame, across every type.
- Through the required node, cumulative chars are p50 5,569 and p90 17,692;
  frames p50 7/p90 16; peak frame p50 1,851.5.
- This removes simultaneous flood but not cumulative processing. The remaining
  boundary is reader recognition/retention and stopping, which zero-call
  availability analysis cannot establish.
