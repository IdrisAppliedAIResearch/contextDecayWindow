# LV-003 — bounded-output successor: Part 1 exploration

**Status:** `PART_1_COMPLETE; NOT REGISTERED`  
**Date:** 2026-08-26  
**Predecessor:** LV-002 generation-instrument stop

## Mechanism identity

The memory comparison is byte-identical to LV-002: frozen 32k full CC80 versus
frozen 32k TC-014 opportunity admission on the same 17 availability-discordant
questions. The live reader and closed-think prompt are unchanged.

The only proposed successor changes are instrument controls:

1. raise the reader response allowance from 192 to the carried HH-001 allowance
   of 512 tokens; and
2. serialize every response immediately, then validate the completed artifact.

Neither change modifies retrieval, the question, the block, reader sampling,
the score, or the outcome bars.

## Empirical behavior

LV-002's amended Preflight showed that the closed-think prefill works: the
seeded full-context prefix stopped naturally and the no-memory floor had zero
truncations. Across the later 170-call outcome schedule, at least one response
reached 192 tokens. The exact count is unavailable because the runner wrote
only after its global validation.

Thus 192 has a demonstrated absorbing state at the intended schedule, while a
write-after-validation runner can erase the evidence needed to characterize
that state. The 512-token allowance is not tuned to an observed answer length;
it is the pre-existing HH-001 reader allowance and is selected before any
LV-002 answer was preserved or scored.

## Distribution carried from LV-002 Part 1

- 17 discordant prompts: 12 opportunity gains and 5 losses.
- 16 answerable primary items: 9 targeted, 5 breadth, 2 other.
- One adversarial refusal-only secondary.
- Block lengths remain 31,881–31,999 characters for CC80 and 31,891–31,998
  for opportunity.
- Selected-set symmetric differences remain 9–52 pairs, median 30.
- No prompt pair is identical.

## Degenerate states and boundary

The successor must stop without interpretation if any 512-token answer
truncates, but it must preserve that answer first. Empty, duplicate, missing or
out-of-schedule responses also stop. A larger cap cannot make a wrong answer
correct; it only makes the response observable rather than cut off.

This Part 1 uses no new reader, judge, embedding or retrieval call. It carries
the prior prompt characterization and the committed LV-002 instrument failure.
No live result, new outcome bar or adoption claim is introduced.
