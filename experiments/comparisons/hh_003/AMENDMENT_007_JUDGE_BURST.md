# HH-003 Amendment 007 - use available judge request capacity

**Date:** August 24, 2026
**Timing:** After 74 post-pilot judgements, before any score inspection
**Pre-registration anchor:** `ea5cf2b6`

## Observed stop

Amendment 006 applied the 6.6 requests/minute refill rate as a bucket whose
capacity was also only 6.6 requests. That models an exhausted daily quota and
discards already available request capacity. It projected about 7.7 hours for
3,064 small judgements even though the paid pilot completed 16 judgements in
13.5 seconds and the answer-plus-judge experiment requires about 6,160 total
requests, below the measured 10,000-request daily ceiling.

The paced judge was manually stopped at 82 default-arm and 8 ASPECT-arm sealed
judgements. No scores or labels were inspected. There were zero errors. The
completed stable keys remain adopted.

## Correction

Remove the artificial 6.6-RPM admission bucket from judging. Resume absent
stable keys with the registered eight workers and immediate per-call
checkpoints. This uses available capacity in the measured daily request bucket
instead of assuming it is empty. Any API 429 or other failure still stops the
run with no retry or Batch fallback. Prompts, model, population, ordering,
scoring, and answer artifacts remain unchanged.
