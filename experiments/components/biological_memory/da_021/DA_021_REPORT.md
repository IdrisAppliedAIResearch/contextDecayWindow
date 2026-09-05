# DA-021 Immutable-Pack Phrase Dictionary Report

**Status:** `NO_IMMUTABLE_PACK_CAPACITY_SIGNAL`; stopped unopened
**Date:** August 30, 2026
**Protocol commit:** `7c96c8a5`
**Standing:** blind mechanical result; evidence outcomes unopened

## Mechanical Result

The joint immutable-pack codec is active and nonexpanding on both corpora, but
LongMem misses the registered median 64-character capacity bar.

| Corpus | Joint renderer | Median recovered | Added pairs | Added turns | Remaining skips |
|---|---:|---:|---:|---:|---:|
| NF-004 | 1,098/1,098 | **480.5** | 1,544 | 1,038 | 7,687 |
| LongMem | 439/465 | **32.0** | 2 | 104 | 5,891 |

NF p10/p90 recovery is 306.7/660.3 characters. LongMem is 5.0/97.8.
Neither corpus expands; maximum final charge is exactly 16,000. Blind replay is
byte-identical.

## Stop and Mechanism

Section 4 requires median recovery of at least 64 characters on both corpora.
LongMem reaches only 32, so DA-021 stops before evidence access. No added
payload is scored.

The asymmetry is informative. NF-004's control has no phrase coding, leaving
substantial repetition across direct and admitted linked payloads. LongMem's
DA-016 control already uses a direct-derived dictionary that captures most
available repeated text; relearning jointly over admitted links adds little.

The no-displacement mechanism itself is mechanically sound: every baseline
payload remains exact and in order, joint coding never expands, and additions
consume only recovered slack. A separately registered NF-only continuation may
reuse the frozen selection without changing the codec or bar. LongMem needs a
different representation signal, not a relaxed threshold.

## Integrity

Blind allocation SHA-256 is
`2e1eb8795f9f8a06ec5900ff7297a6b962a5257c56fac2f8ac1925954c17aed9`.
All 1,563 questions replay byte-identically with zero model, embedding and cache
calls. No evidence outcomes, reader, tuning or adoption claim follows.

