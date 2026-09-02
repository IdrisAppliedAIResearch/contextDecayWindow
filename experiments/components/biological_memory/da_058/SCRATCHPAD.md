# DA-058 Scratchpad

## 2026-08-31 - Registration

- Fixed 1,984-char contiguous chunks under the existing 2,048 frame cap.
- Exact typed ordinals, complete-chain decode, five protected retained slots.
- Seal all member decisions before checking six residuals.
- Zero model/embedder/cache calls; reader reconstruction untested.

## 2026-08-31 - Result

- Complete availability 459->465, +6/0, p=.03125; no residual remains.
- Every oversized member uses exactly two chunks.
- Total retained slots are 2-3; retained/peak p50 2,814, max 3,111 chars.
- Mechanical capacity ceiling reached. Next: evidence-blind session-head routing.
