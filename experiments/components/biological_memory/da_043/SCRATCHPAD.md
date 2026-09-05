# DA-043 Scratchpad

## 2026-08-30 - Registration

- Measure exact frontier depth and transient payload size for all 18 residuals.
- Do not change the graph, prompt, order or payloads.
- No fitted policy, score, reader, model, embedding or cache calls.

## 2026-08-30 - Result

- All 18 residuals resolve uniquely to one node each; there are no conjunctions.
- Required depth is p50 15, p90 21.9, max 30. One node is first, four are at
  depths 2-8, and thirteen are at 9-32.
- Rendered payload size is p50 351 chars, p90 463.5, max 1,906. Sixteen fit
  512 chars, 17 fit 1,024 and all fit 2,048.
- A fixed first-32 frontier page is the next evidence-blind materialization
  probe. It must use auxiliary capacity and keep DA-038 immutable.
