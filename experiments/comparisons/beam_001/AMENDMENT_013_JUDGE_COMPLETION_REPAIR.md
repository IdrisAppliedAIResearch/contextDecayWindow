# BEAM-001 Amendment 013 - Judge completion repair

**Status:** authorized post-failure repair; no judgment content or outcome
opened  
**Date:** 2026-08-28  
**Amends:** Amendments 011-012 judge completion handling only  
**Audit anchor:** `525ae76a`  
**Deviation:** `DEVIATION_003`

## 1. Observed terminal state

The continued run sealed all 1,080 reader answers and durably checkpointed 238
of 360 bundled blind judgments. Stable id
`33c2b09a0f2bab25631122351fcae938a65ee2f5389a95d58a463a0972214d22`
then failed the bundled parser twice, firing the registered one-retry stop.
The runner did not retain either invalid response, so truncation versus malformed
matrix output is not identifiable. Only the failure string and corresponding
blind surface metadata were inspected. The item has 10 criteria, requiring 30
slot-criterion cells, a prompt count of 886, and the original 4,096-token output
cap.

No judgment content, slot mapping, score, result, or outcome comparison was
opened. The 238-row checkpoint SHA-256 is
`50346c6707cd084ddc4570a8a8eec5bd6ea46882f68e3e6a161175637ee52682`.
Its complement in the sealed 360-request surface is exactly 122 stable ids.
Their ascending-id, LF-terminated SHA-256 is
`f9a0e6344da7afb1bf6b35612b9316803bc185c75795426469e6d3b0dd8a4902`.

## 2. Frozen repair

The user explicitly directed the failed run to be fixed and continued. Preserve
the 238 completed judgment rows byte-for-byte and never resend their ids. For
the frozen 122-id complement only:

- retain the exact model snapshot, messages, prompt, temperature, JSON-object
  response format, blind slots, parser and scoring;
- raise `max_tokens` from 4,096 to the model ceiling of 16,384;
- permit at most four attempts with the identical repaired body; and
- durably record invalid-attempt finish reason, usage, error metadata and text
  digest before another attempt.

No invalid output is repaired, partially scored or inferred. Four invalid
repaired attempts stop the run without scoring. Existing checkpoint rows must
match either their original body digest or, after a later interruption, the
repaired-body digest. Any other digest stops before a request.

The larger cap changes the transport body and can change behavior even when the
response ends below 4,096 tokens. It is therefore an instrument deviation, not
a transparent retry of Amendment 011.

## 3. Runtime continuation

At the handled failure, 1,782 whole seconds remained under Amendment 012's
active-runtime budget. Re-arm exactly 1,782 seconds immediately before the first
repaired request. Time after the handled stop is not charged. No request is
admitted after this repaired deadline, and no fresh five-hour allowance is
created.

The original `failure.json` is preserved as `failure_001.json`. A new handled
failure may write a new terminal artifact. The memory-only supervisor and
checkpoint adoption rules remain in force.

## 4. Claim boundary and gates

Any completed result remains `CHARACTERIZED`. It records both
`DEVIATION_002` and `DEVIATION_003`; neither the original runtime gate nor the
original judge-completion gate is reported as passed.

- **G-REPAIR-PREFIX:** the 238-row checkpoint count and SHA-256 match before
  failure archival or runtime re-arm.
- **G-REPAIR-SET:** the frozen complement is 122 ids with the registered set
  hash.
- **G-NO-RESEND:** none of the 238 original ids is submitted again.
- **G-BODY:** pending and repaired checkpoint rows use only the 16,384-token
  body; original rows retain the 4,096-token body.
- **G-DIAGNOSTIC:** every invalid repaired attempt is durably recorded before a
  subsequent attempt.
- **G-REPAIR-RUNTIME:** no repaired request is admitted after 1,782 seconds.
- **G-CLAIM:** the report is `CHARACTERIZED` and names both deviations.
