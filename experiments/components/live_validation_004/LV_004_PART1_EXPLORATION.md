# LV-004 — deterministic completion repair: Part 1

**Status:** `PART_1_COMPLETE; NOT REGISTERED`  
**Date:** 2026-08-26  
**Predecessor:** LV-003 preserved generation stop

## Behavioral identity

LV-004 does not rerun the live comparison. It proposes to retain LV-003's 168
naturally stopped responses and mechanically complete only the two records
whose `done_reason` is `length`, using the identical prompt, model, sampling and
seed with a larger output allowance.

The repair is valid only if each replacement begins byte-for-byte with its
preserved 512-token response. A prefix mismatch means the larger allowance
changed generation rather than continued it and stops the study.

## Observed distribution

- Complete schedule: 170/170 rows, 0 duplicates, 0 missing, 0 extra.
- Naturally stopped: 168.
- Truncated: 2, both at exactly 512 generated tokens.
- Both truncations concern `conv-42` source 79, an offline opportunity-gain
  breadth item.
- Arms are balanced across the defect: full CC80 replicate 2 and opportunity
  replicate 3.
- Prompt token counts are 8,416 and 8,447 respectively.

The responses begin with direct answer attempts and then continue auditing the
conversation. No correctness interpretation is attached; no judge or outcome
artifact exists.

## Proposed repair and degenerate states

Use `num_predict=2048` only for the two identified records. Preserve originals
and replacements separately. Stop before judging if a replacement truncates,
does not reproduce the original text prefix, changes prompt/seed identity, or
if any record other than those two is replaced.

The 2,048 limit is selected before repair output exists and is four times the
failed cap, leaving the original 168 responses untouched. This is an instrument
repair, not best-of-N or answer selection. It cannot change the first 512 tokens
when determinism holds.

No new reader, judge, embedding or retrieval call was made in Part 1.
