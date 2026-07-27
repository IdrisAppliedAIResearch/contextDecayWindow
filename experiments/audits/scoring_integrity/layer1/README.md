# Layer 1 Mechanical Sweep

**Run:** 2026-07-26  
**Coverage:** 17 canonical arms, 222 scored items  
**Artifact drift:** none

## Census

All 222 expected score rows parsed. Study 001 turn 20 was recovered read-only from
the canonical runtime database/log where it was absent from the rubric-response
bundle. Study 003's accepted bundle uses question headings rather than turn
headings and was parsed by question.

## Results

- `NO_ANSWER`: 16 items.
- Truncation or unclosed reasoning: 24 items.
- Unclosed reasoning blocks: 23 items.
- Any F1-F5 flag: 37 items.
- F1: 7.
- F2: 13.
- F3: 8.
- F4: 21.
- F5: 0.

Flags are routing evidence, not automatic corrections except where the locked
protocol makes completeness decisive. String matching is deliberately
conservative; F2-F4 items require blind scoring/adjudication rather than accepting
the mechanical interpretation as judgment.

## Known Regression Case

Study 002 C Q11 is mechanically classified `NO_ANSWER` with an unclosed reasoning
block. It contains 5 of 17 Q11 facts somewhere in the raw artifact, all inside
unscoreable reasoning, and 0 of 17 in scoreable final content. Its original score
is 1.0 and it raises F1, F2, F3, and F4.

## Integrity Notes

`artifact_hashes_pre.json` and `artifact_hashes_post.json` are byte-identical in
content. No source artifact changed.

The Study 001 variant list was completed after the initial lock but before this
sweep. That timing deviation is documented in Amendment 001 and limits the
blinding claim for Study 001 fact extraction. Amendment 002 records the analogous
behavioral-rule variant omission.

The detailed record is `items.jsonl`; `items.csv` is the compact review surface.
