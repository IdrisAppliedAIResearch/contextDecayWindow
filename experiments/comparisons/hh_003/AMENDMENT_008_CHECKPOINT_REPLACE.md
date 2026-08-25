# HH-003 Amendment 008 - transient checkpoint replacement

**Date:** August 24, 2026
**Timing:** After the burst judge stopped, before resume
**Pre-registration anchor:** `ea5cf2b6`

## Observed stop

The resumed eight-worker judge completed 600 post-resume calls in about 40
seconds, then stopped while replacing `judged_r1.json` with its temporary file.
Windows returned `PermissionError: [WinError 5] Access is denied`. This was a
local checkpoint filesystem failure, not an API failure. The last sealed state
contains 685 default-arm and 8 ASPECT-arm judgements. No labels or scores were
inspected.

## Correction

Checkpoint only the arm changed by each completed call. On transient
`PermissionError`, retry the same local atomic replacement for up to five
seconds with 100 ms sleeps. This does not resend, regenerate, inspect, or alter
any model output. Failure after the local retry window still stops the run.
The existing stable-key resume rule, eight workers, immediate per-call
checkpoint, and no API retry remain unchanged.
