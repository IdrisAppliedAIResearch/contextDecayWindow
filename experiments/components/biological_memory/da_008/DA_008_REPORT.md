# DA-008 Reversible Compact Direct Rendering Report

**Status:** `RANKED_COMPACT_SIGNAL`
**Protocol commit:** `9c9f5bca`
**Blind-selection commit:** `32aaa821`
**Standing:** post-outcome architecture diagnostic on spent NF-004 LoCoMo
**Calls:** 0 embedding, 0 model, 0 cache access
**Date:** August 30, 2026

## Result

Reversible speaker-dictionary rendering creates capacity without removing or
altering direct evidence. All 1,104 blind contexts decode to the original pair
serialization byte-for-byte, retain the exact direct identity sequence, and
are non-expanding. On the 1,098 primary questions, direct evidence remains
935/1,098 complete.

Median direct-rendering savings are 504 characters (p10 402, p90 916; minimum
337). Because the original pack also had small residual slack, median usable
slack is 520 characters (p10 414, p90 936).

Using only that protected slack gives:

| Link order | Complete | Gains | Losses | Net |
|---|---:|---:|---:|---:|
| DA-004 grouped benefit model | **961** | 26 | 0 | **+26** |
| Added-set query coverage | 956 | 21 | 0 | +21 |
| Unlearned temporal order | 956 | 21 | 0 | +21 |

The benefit arm is nonnegative in every conversation: gains are 12, 2, 4, 1,
4, and 3 across `conv-26/30/43/44/49/50`. Direct versus benefit-ranked links is
26/0 discordant, exact two-sided p=2.98e-8. This supports protected compact
capacity on this spent availability corpus, not reader use.

## What Did What

The architecture carries the main result. Direct selection and evidence are
held fixed, while repeated speaker names are replaced by numeric references to
a reversible dictionary. The benefit arm then spends a median 480 characters
on links and finishes at 15,958 characters, leaving median slack 42. It admits
2,561 link instances across all questions.

Ranking contributes a smaller increment. The DA-004 model reproduces grouped
OOF benefit AUC .8234 and finishes five items above each control. Against query
coverage it has 8 model-only and 3 control-only complete items (p=.227); against
temporal order it has 11 and 6 (p=.332). Neither contrast is statistically
differentiated. The registered descriptive status passes because the model is
strictly higher than both controls, but ranking remains an unconfirmed lead.

## Ceiling

The one-hop candidate set contains all missing evidence for 51 direct misses,
so complete delivery could reach 986 if every eligible pair fit. The current
benefit arm recovers 26/51 reachable gains. Gain-carrying links appear early:
rank depth p10/p50/p90 is 1/1/2. Yet available characters usually fit only a
small number of full pairs, and the allocator already consumes nearly all
slack.

This identifies the present ceiling mechanism: not token flooding, and not an
observed exhaustion of useful links. Reversible metadata compaction creates a
fixed amount of real capacity; full linked pairs consume it. More lossless
direct compression could test the remaining 25 reachable gains without
weakening direct protection. Threshold tuning on NF-004 is not justified.

## Integrity and Boundary

The blind artifact replayed byte-identically at SHA-256
`73901fe02011f81f29fa97bcaf6da8a2ab68f9e6155143d8f0d50da4cb1b9e72`.
The result SHA-256 is
`48483e9ce2755f6ecbea430374fc731d6d0d7d6ece0b54ad3218b2c8c482bae5`.
Every gain is carried by an appended neighbor dialogue; no arm loses direct
evidence. Availability does not establish that a reader interprets the compact
speaker dictionary, and the ranking comparison is on spent data.

