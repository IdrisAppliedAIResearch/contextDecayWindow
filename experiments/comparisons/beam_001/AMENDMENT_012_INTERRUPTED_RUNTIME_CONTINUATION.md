# BEAM-001 Amendment 012 - Interrupted runtime continuation

**Status:** authorized deviation before continuation; no judgment or outcome
opened  
**Date:** 2026-08-28  
**Amends:** Amendment 011 runtime handling only  
**Deviation:** `DEVIATION_002`

## 1. Interruption record

The Amendment 011 synchronous process started at Unix time
`1787942201.2423203`. It was later found absent without a Python exception,
`failure.json`, judgment, result, or score artifact. The last durable activity
was 236 unique reader answers at 14:26:22 local time. Their stable ids and body
digests pass the registered checkpoint adoption checks; they are retained and
must not be resent.

The process termination was external to the runner's handled failure path. Its
cause is not identified. The stale `progress.json` value `RUNNING` was
incorrectly treated as process status during earlier checks. The original
five-hour wall-clock deadline now cannot contain the remaining registered
schedule.

## 2. Prospective continuation rule

The user directed the interrupted run to continue. This continuation restores
only unused active runner time; it does not restart a fresh five-hour budget.
The first segment is conservatively charged 55 minutes, exceeding the interval
from runner start through the last durable answer. The continuation receives
14,700 seconds (4 hours 5 minutes), beginning immediately before its first
resumed request.

The 236 checkpointed reader answers remain blinded and unchanged. The remaining
844 reader calls and all 360 bundled blind judge calls retain their registered
bodies, models, caps, rate buckets, retry policy, parsing, and scoring. No
completed id may be sent again. The continuation stops without scoring if its
14,700-second budget expires.

A memory-only supervisor inherits `OPENAI_API_KEY`, starts the unchanged runner,
and waits for it. If the child is hard-terminated without writing
`failure.json`, completing, or exhausting the continuation deadline, the
supervisor restarts it from the durable checkpoint. It never records the key.
Handled runner failures remain terminal and are not restarted.

## 3. Claim boundary

`G-RUNTIME` from Amendment 011 has failed because the registered wall-clock cap
was exceeded. Any completed result is therefore `CHARACTERIZED` under
`DEVIATION_002`, regardless of its numerical disposition. It is not reported
as the original confirmatory result. All other gates and inferential outputs
remain descriptive diagnostics of the frozen schedule.

## 4. Continuation gates

- **G-CHECKPOINT-RESUME:** 236 unique checkpoint rows pass stable-id and body
  digest validation before the first resumed request.
- **G-NO-RESEND:** no API request uses one of those 236 completed ids.
- **G-ACTIVE-RUNTIME:** the continuation admits no new request after 14,700
  seconds.
- **G-SUPERVISOR:** an unhandled hard child exit is restarted only when no
  terminal artifact exists and continuation time remains.
- **G-CLAIM:** every report and summary labels the result `CHARACTERIZED` and
  records `DEVIATION_002`; the original `G-RUNTIME` is never marked passed.
