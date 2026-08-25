# HH-003 Amendment 009 - judge token pacing

**Date:** August 24, 2026
**Timing:** After the second burst judge stop, before resume
**Pre-registration anchor:** `ea5cf2b6`

## Observed stop

The hardened burst judge reached 1,540 default-arm and 193 ASPECT-arm sealed
judgements, then stopped on the first surfaced API 429. The response reported
the measured 200,000 TPM ceiling fully used and a 429-token request. This
establishes token throughput, not daily request count, as the binding judge
limit. No partial scores or labels were inspected.

## Correction

Admit each remaining judgement through the existing HH-002 token bucket at
170,000 estimated tokens/minute. Estimate each call with the unchanged
`judge_request` constructor used by the Batch harness. Do not apply the
discarded 6.6-RPM request bucket. Eight workers, stable-key resume, immediate
checkpointing, local replacement retries, and fail-closed API behavior remain
unchanged. There is no API retry or Batch fallback.
