# DA-059 Scratchpad

## 2026-08-31 - Registration

- Exact lowercase alphanumeric token -> source-order session postings.
- Traverse query tokens in first-appearance order; union/dedupe, no score or cap.
- Seal all routes before joining evidence sessions.
- Zero model/embedder/cache calls.

## 2026-08-31 - Result

- Complete required-session coverage 465/465.
- Routed sessions p50 44; routed fraction p50 .918, p90 .960.
- First/last required rank p50 13/28.
- Singleton union is broad control-plane flooding; next require token pairs.
