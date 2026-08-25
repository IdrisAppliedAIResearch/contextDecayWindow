# HH-003 Amendment 006 - full judging request pacing

**Date:** August 24, 2026
**Timing:** After all 3,080 answers were sealed, before full judging
**Pre-registration anchor:** `ea5cf2b6`

## Observed state

The full answer stage completed 3,064 post-pilot synchronous calls with zero
retries. The account's measured 10,000-request-per-24-hour limit required the
6.6 requests/minute bucket registered in Amendment 005. Full judging has 3,064
post-pilot calls remaining against the same account and therefore cannot be
treated as an unpaced eight-worker workload merely because each request is
small.

## Correction

Every remaining judgement request is admitted through the same existing
HH-002 `RateBucket` at 6.6 requests/minute. Eight workers remain to overlap
admitted calls. Every successful judgement is checkpointed immediately by
stable item key. The token bucket is not applied because the measured binding
constraint for these small judge prompts is request count, and the paid pilot
already established their response shape. API failures still stop the run;
there is no silent retry, Batch fallback, prompt change, score inspection, or
partial-result interpretation.
