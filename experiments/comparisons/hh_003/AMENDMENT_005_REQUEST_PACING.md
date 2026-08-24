# HH-003 Amendment 005 - synchronous request pacing

**Date:** August 24, 2026
**Timing:** Before retrying the stopped full synchronous answer run
**Pre-registration anchor:** `ea5cf2b6`

HH-002 measured two synchronous account limits: 200,000 tokens/minute and
10,000 requests per 24 hours. Amendment 004 fixed the carried 170,000 TPM
target but omitted the request bucket. The same existing HH-002 `RateBucket`
also admits at 6.6 requests/minute, below the measured continuous refill of
about 6.9/minute. Both buckets bind every remaining answer request.

At 3,064 remaining answers, the request allowance alone implies a lower bound
of about 7.7 hours. This is account pacing, not model latency. Eight workers
remain to overlap admitted calls, but do not increase admission rate.
