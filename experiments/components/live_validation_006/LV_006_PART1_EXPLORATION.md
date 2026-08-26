# LV-006 — parse-safe blind-judge continuation Part 1

**Status:** exploration only; no repair is registered or runnable yet  
**Date:** 2026-08-26

LV-005 stopped before unblinding because one naturally stopped blind judge
response omitted its verdict. This exploration uses only the sealed blind
surface; it does not read the arm mapping.

The tested repair appends the literal `VERDICT:` cue after the already frozen
closed-think suffix. The original exact failed prompt/seed and the repaired
prompt/seed are each repeated twice. The repaired prompt is additionally tested
on 12 content-hash-selected blind answers under all three registered seeds.

The original exact prompt failed parsing twice with byte-identical responses.
The repaired exact prompt parsed and naturally stopped twice with byte-identical
responses. All 36 blinded sample calls parsed and stopped naturally. No arm
mapping was opened. The full artifact SHA-256 is
`34f4ee1c7e5fddad90709071a84a41740c377db3a1631e62fb9bf70b96068f72`.

The binding design consequence is all-or-nothing: if the repair is parseable,
naturally stopped and byte-identical on the exact failure and parseable on all
36 sample calls, a successor may regenerate all 960 judgments using the one
repaired prompt. It may not combine LV-005's 136 original-instrument judgments
with repaired-instrument judgments. The original partial file remains a stop
artifact and reproduction anchor.
