# BEAM-001 Amendment 014 - Strict matrix closeout

**Status:** authorized one-request post-failure repair; no judgment content or
outcome opened  
**Date:** 2026-08-28  
**Amends:** Amendment 013 for one frozen request only  
**Audit anchor:** `ac2bc241`  
**Deviation:** `DEVIATION_004`

## 1. Identified failure

Amendment 013 produced 359 of 360 durable blind judgments. The same remaining
stable id,
`33c2b09a0f2bab25631122351fcae938a65ee2f5389a95d58a463a0972214d22`,
failed all four repaired parser attempts. Their finish reasons were all `stop`
and completion counts were 822, 818, 811 and 811 tokens. This identifies a
persistent matrix-shape violation rather than output truncation.

No response text, judgment content, slot mapping, score, result or outcome
comparison was opened. The 359-row checkpoint has SHA-256
`578adf3c37ece497401bc6caa9afd02d1b8860c09d2f54f94c4e2a0323e4754c`.
It contains 359 unique ids. Its complement in the sealed surface is exactly the
single stable id above.

## 2. Frozen structured repair

Preserve the 359 completed rows byte-for-byte and never resend them. Replace
only the remaining request's output contract with strict Structured Outputs.
The model snapshot, question, rubric, three blinded responses, slot order,
temperature, score values, substantive judging instructions and 16,384-token
cap remain unchanged.

The strict JSON schema requires one root `evaluations` object. It has exactly
the required properties `R0`, `R1` and `R2`; each slot has exactly the required
string properties `0` through `9`. Every slot-index value is an object with
exactly `score` and `reason`: score is one of 0.0, 0.5 or 1.0 and reason is a
nonempty string. All objects set `additionalProperties: false` and all named
properties are required.

The output-format paragraph is changed only to describe the keyed schema.
The parser converts the keyed object deterministically into the original
ordered slot/criterion representation before checkpointing. No score or reason
is changed, inferred or repaired. Two identical structured attempts are
allowed; each invalid attempt is durably diagnosed. A second invalid attempt
stops without scoring.

Structured output can change model behavior and this request uses a different
surface contract from the other 359. This is an instrument deviation, not a
transparent parser fix.

## 3. Runtime and completion

At the Amendment 013 handled failure, 688 whole seconds remained. Re-arm
exactly 688 seconds immediately before the structured request. Time after the
handled stop is not charged. Preserve the current `failure.json` as
`failure_002.json` and retain `failure_001.json` unchanged.

After one valid normalized judgment, run the unchanged judgment seal, scoring,
bootstrap, sign-flip test and report generation. The result remains
`CHARACTERIZED` and records `DEVIATION_002`, `DEVIATION_003` and
`DEVIATION_004`; no original completion gate is rehabilitated.

## 4. Gates

- **G-STRICT-PREFIX:** the 359-row count, unique-id count and registered
  checkpoint SHA-256 match before failure archival or runtime re-arm.
- **G-STRICT-ID:** the sealed-surface complement is exactly the registered one
  id.
- **G-NO-RESEND:** none of the 359 completed ids is submitted again.
- **G-SCHEMA:** the remaining body uses the exact required keyed matrix and
  strict JSON Schema; all substantive judge inputs remain unchanged.
- **G-NORMALIZE:** a fixture normalizes all 30 keyed cells to the original
  representation and rejects missing, extra, empty or invalid cells.
- **G-STRICT-RUNTIME:** no repaired request is admitted after 688 seconds.
- **G-CLAIM:** any report is `CHARACTERIZED` and names all three deviations.
