# DA-080 Scratchpad

## 2026-08-31 - Diagnostic Lock

- Exact join: 13 DA-079 residuals to sealed DA-045 exposure rows.
- No stream rebuild, order change, scoring, truncation, or outcome inference.
- DA-078 prompt remains immutable; frames are separate replaceable capacity.
- Zero model/embedder/cache calls.

## 2026-08-31 - Result

- Exact crosswalk: 13/13 exposed, one required node each, zero DA-078 mutation.
- Peak frame chars p50 1,968, p90 2,040.6 under the 2,048 cap.
- Frames through target p50 13/p90 16; cumulative chars p50 5,781/p90 19,264.2.
- Offline capacity is available; reader recognition, retention, and stopping
  are the remaining uncertainties.
- Byte-identical replay; zero calls.
