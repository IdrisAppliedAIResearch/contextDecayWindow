# NF-006 Report - Internal Statement Ranking

**Status:** `INTERNAL_DILUTION_RESCUES_Q11 - CHARACTERIZED`
**Pre-registration:** `ebb3ebf3d103e7ceaa62576879e0825fbfc11ee1`
**Amendment 001:** `dfea8c9691358b6a53826f6514833ee03a08ab3c`
**Corpus:** corrected internal 121-turn store, 119 Q11-eligible episodes
**Budget:** 32,000 serialized characters
**Generation calls:** 0
**Embedding calls during measurement:** 0
**Date:** August 13, 2026

## Result

NF-006 passes its registered internal information-dilution tier. On Q11,
ranking statement candidates by their own cosine raises exact item availability
to **14/17**, compared with **12/17** for whole-episode ranking and **7/17**
when statements merely inherit their parent score. The treatment exceeds the
packing-only control, gains monetary evidence, and reaches the locked 14/17
threshold.

| Arm | Total | Civil | Art | Monetary | Marine | Selected units | Parents | Chars |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| C0 episode rank / episode pack | 12/17 | 5/5 | 2/4 | 1/4 | 4/4 | 15 | 15 | 31,569 |
| C1 inherited rank / statement pack | 7/17 | 3/5 | 2/4 | 1/4 | 1/4 | 51 | 15 | 31,931 |
| **T1 own-statement rank / statement pack** | **14/17** | **5/5** | **1/4** | **4/4** | **4/4** | **80** | **57** | **31,991** |

Against C0, T1 gains Taylor Rule, Dr. Priya Mehta, and 2.3%, and loses Melozzo
da Forli: three gains, one loss, net +2. Against C1 it gains eight items and
loses one, net +7. Fine packing alone is not the cause: inherited statement
ranking falls five items below the episode control.

The binding targeted gate passes at its strictest grain. C0 and T1 both deliver
**21/21** targeted item rows, with **0 gains, 0 losses**, no lower probe, and no
lower domain. Q7 and Q10 remain separately scored from their shared turn-118
selection, as required by Amendment 001.

## Mechanism boundary

The result supports information dilution/localization inside the program's own
store: statement vectors carry useful query signal that parent episode vectors
do not, and own-statement ranking clears a threshold neither episode ranking nor
inherited statement packing clears.

It does **not** establish the anticipated direct turn-90 route. The registered
T1 trace selects no statement whose source turn is 90, even though all four
monetary items are present in its final payload. NF-006 therefore supports the
store-level moderator but does not show that splitting DX-001's characterized
turn-90 episode caused the rescue. That exact carrier remains unresolved.

The one Q11 loss also matters. Own-statement ranking restores monetary 4/4 but
reduces art from 2/4 to 1/4 versus C0. The registered targeted gate catches no
regression because all 21 targeted rows tie; this is a breadth composition
trade, not a universal dominance result.

## Gates and integrity

| Gate | Result | Evidence |
|---|---|---|
| G0 registration | PASS | registration `ebb3ebf3`; amendment `dfea8c96`; lock contains no implementation |
| G1 inputs | PASS | locked database, turn log, E005, IC-001, model, 121 parents, 119 eligible |
| G2 leakage | PASS | outcome-blind mechanism; planted measurement import detected |
| G3 C0 reproduction | PASS | selected ids, payload hashes, and chars exact at all eight prefixes |
| G4 statements | PASS | 791 units: 119 user, 672 assistant; Part 1 identities and distribution exact |
| G5 vectors | PASS | 8/8 query and 791/791 statement hits, zero misses; all seals pass |
| G6 determinism | PASS | two full 24-record selection passes byte-identical |
| G7 selection seal | PASS | outcome-blind selections committed at `ef074cda` |
| G8 targeted | PASS | 21/21 versus 21/21; zero item, probe, or domain regressions |
| G9 Q11 | PASS | 12/7/14; locked positive disposition applied once |

Capture used one lexicographically sorted eight-text probe batch followed by
791 sequential exact-solo statement calls, CPU-only with one thread. The cache
is 4,063,232 bytes, file SHA-256
`e6a2a6687fb5ee6694a43dd3ebe7a957f7bd9852418657f78274c64d38c4f391`,
and canonical content-manifest SHA-256
`967c73113ff926e360578ff65d0f7443cb99f5b4ce015ef0571c9115891eea37`.

## Amendment

Amendment 001 corrected the registered probe-vector cardinality from nine to
eight. The scored population did not change: nine scored probe labels including
Q11, eight targeted labels, 17 Q11 rows, and 21 targeted rows. Q7 and Q10 share
one turn-118 query and selection but remain separate scored probes. The
correction was authorized and committed before capture.

## Boundaries

This is availability on one exhausted internal breadth probe. It does not
identify raw character length separately from semantic localization, establish
reader correctness, validate a universal statement unit, or confirm the result
on fresh data. No live run, promotion, or adoption follows.

## Integrity trail

| Artifact | Commit | SHA-256 |
|---|---|---|
| registration | `ebb3ebf3` | LF `134822f97bcc6286` |
| amendment 001 | `dfea8c96` | `c1482324dcdea2e9` |
| G0-G4 preflight | `c298e5f1` | `17759052b4ce0450` |
| vector manifest | `768ba5ce` | `214dd342c391f016` |
| G5 integrity | `0273a1b8` | `0bd1048f2f12ebe8` |
| G6-G7 selection seal | `ef074cda` | `3dc22122d4cae27a` |
| G8-G9 measurement | `0af32ee0` | `d20dffd563e5777e` |
