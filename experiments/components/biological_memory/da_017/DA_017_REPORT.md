# DA-017 NF-004 Phrase-Link Transfer Report

**Status:** `NO_CROSS_CORPUS_PHRASE_LINK_SIGNAL`
**Date:** August 30, 2026
**Standing:** frozen spent-corpus NF-004 availability replay

## Result

Phrase-coded links raise DA-010 complete evidence from **970** to **973** of
1,098: **3 gains, 0 losses**, two-sided exact `p=.25`. Direct reproduces 935 and
the fixed ceiling is 986.

The registered bar required at least five gains. DA-017 therefore reports
`NO_CROSS_CORPUS_PHRASE_LINK_SIGNAL` despite zero regression. Conversations 43,
49 and 50 gain one each; 26, 30 and 44 tie.

## Mechanism

The blind allocator exactly reproduces DA-004 benefit AUC .823401708567509 and
DA-010's mechanical control. Phrase coding increases pair admissions from 2,535
to 4,423 while fallback turns shift 1,176 to 1,120. Of 13,980 non-direct eligible
actions, 9,141 payloads reuse direct dictionary phrases.

Two new completions are pair-carried at costs 288 and 280 characters; one is a
248-character singleton. The expanded admission surface mostly contains no new
complete evidence because NF-004's baseline is already 970/986.

## Disposition

The combined evidence is mixed:

- Reversible phrase capacity transfers mechanically and strongly on both
  corpora.
- Delivery is strong on LongMemEval (+17/-0) but weak on NF-004 (+3/-0), failing
  the prospective cross-corpus bar.
- DA-004 benefit ranking does not transfer to LongMemEval and is not a general
  solution.

Retain DA-016 as a promising spent-corpus availability mechanism, not a validated
architecture. Do not tune NF-004. The remaining legitimate work is an
equivalence-preserving runtime optimization and a separately authorized reader
test on prospectively locked data.

