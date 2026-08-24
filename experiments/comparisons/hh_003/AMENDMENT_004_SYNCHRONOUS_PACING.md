# HH-003 Amendment 004 - synchronous pacing and checkpoint granularity

**Date:** August 24, 2026
**Timing:** After the first full synchronous attempt stopped, before its retry
**Pre-registration anchor:** `ea5cf2b6`

## Observed stop

The synchronous pilot completed 16/16 judgements in 13.5 seconds wall time,
with zero retries and zero malformed outputs. The first full answer attempt
then stopped on the first surfaced HTTP 429. The response reported a 200,000
tokens/minute ceiling, 200,000 used, 11,230 requested, and a 3.369-second retry
interval. The stop required by Amendment 003 worked.

The runner checkpointed every 25 completions. Fewer than 25 calls may have
completed before the 429, but none reached a checkpoint and their exact count
and bytes are unavailable. Those requests cannot be adopted and will be sent
again. This is an instrument failure, not a model result.

## Correction

Remaining synchronous answer calls are admitted through the existing HH-002
token bucket at 170,000 estimated tokens/minute, below the measured 200,000 TPM
ceiling. Eight workers remain, but the shared bucket controls admission. Every
successful response is checkpointed immediately by stable key before another
completion is interpreted. API 429 or other call failure still stops; there is
no silent retry and no Batch fallback.

Judgements are small enough that the 16-call synchronous pilot passed without
pacing. Full judging retains eight workers and immediate per-call checkpoints;
if it reaches a limit, it stops and requires another pre-result amendment.
