# LV-002 — live reader validation of TC-014 opportunity admission

**Status:** `STOPPED_AT_GENERATION; OUTPUT_LIMIT_AND_PRESERVATION_FAILURE`  
**Registration commit:** `2e8bc7fa`  
**Preflight commit:** `9d863953`  
**Date:** 2026-08-26

## Result

LV-002 has no reader outcome. Its amended Preflight passed, but the registered
five-replicate C0/T1 generation reached the 192-token reader limit on at least
one response. `G-PROMPT` therefore failed before judging or unblinding.

The runner exposed a second instrument defect: it accumulated all 170 answers
in memory, checked truncation, and only then wrote the batch. The failure path
raised before serialization, so neither the valid nor truncated answers were
preserved and the exact truncation count is unknowable. No answer content,
judge verdict, arm score or directional result exists.

## What passed before the stop

- All 34 frozen TC-014 contexts reproduced exactly.
- The Qwen 3.5 27.3B Q6_K reader was loaded 100% on the RTX 5090.
- An 8,451-token seeded prefix replayed byte-identically.
- The no-memory floor scored 0/16.
- Amendment 001's closed-think prefill removed the raw-thinking truncation that
  had stopped the first Preflight attempt.

Those checks establish that retrieval, contamination, determinism and GPU
placement were usable. They do not repair the outcome batch.

## Consequence

The registration forbids scoring truncated answers and no committed answers
exist. LV-002 is closed as an instrument failure. A successor may reuse the
frozen comparison only by registering a larger carried output allowance and
write-before-validation behavior before any replacement generation.
