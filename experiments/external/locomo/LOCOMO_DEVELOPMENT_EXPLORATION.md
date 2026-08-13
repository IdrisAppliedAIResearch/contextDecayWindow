# LoCoMo Ranking-Granularity Development Exploration

**Document type:** Pre-registration Preflight Part 1, development data only
**Status:** `DEVELOPMENT SIGNAL; HOLDOUT REMAINS SEALED`
**Corpus lock:** `LOCOMO_CORPUS_LOCK.md`
**Analysis artifact:** `artifacts/development_analysis.json`
**Artifact SHA-256:** `d3621b30cae18e679cedf13811e1240a47eb565efe69fbb24583ce2af63b95ab`
**Model calls during analysis:** 0
**Embedding calls during analysis:** 0
**Date:** August 13, 2026

## 1. Boundary

This is exploration, not a study registration or disposition. It uses only the
four conversations assigned to development before QA content was opened. The
six locked holdout conversations have not been adapted, embedded, counted, or
scored. No threshold, success bar, lower signal bar, or holdout analysis was
chosen after seeing these results.

## 2. Mechanism identity

In one falsifiable sentence: the baseline gives every adjacent-turn pair the
maximum query cosine attained by any pair in its session, while the treatment
gives each pair its own query cosine; both then pack the same candidates with
the same 32,000-character skip-on-overflow rule.

The candidate called a pair is two adjacent turns within one session, except
that an odd final turn remains as a one-turn candidate. Development contains
1,365 candidates from 2,662 turns in 122 sessions. There are 68 singleton
candidates, and 34 resolved evidence references point to them; neither arm
drops or treats them specially.

The baseline name was checked against behavior: all pairs in a session inherit
one score and ties resolve by session and within-session order. The treatment
uses the carried cosine provider on the pair text itself. Packing charges the
exact candidate text length, skips candidates that do not fit, and continues
scanning. It is an offline candidate-text budget, not a serialized reader
prompt cost.

## 3. Development result

LoCoMo has 11 byte-identical duplicate QA records and no source QA identifier.
The primary development summary therefore keeps one copy of each canonical QA,
identified by a content SHA-256. Removing the duplicates changes no gain or
loss because all 11 are ties.

| Exact evidence measure | N | Baseline | Pair-ranked | Gains | Losses | Ties | Exact sign p |
|---|---:|---:|---:|---:|---:|---:|---:|
| Any evidence pair delivered | 871 | 820 | 855 | 44 | 9 | 818 | 1.22e-6 |
| All evidence pairs delivered | 868 | 773 | 826 | 71 | 18 | 779 | 1.30e-8 |

Three unique questions have one malformed evidence reference but retain two or
more resolvable references. They are evaluable for the any-evidence measure and
excluded from the all-evidence denominator. All four development conversations
have positive net movement on the any-evidence measure: gains/losses are 13/2,
15/2, 7/3, and 9/2.

These p-values describe development data only. They are not registered tests
and confer no disposition.

## 4. Distribution and degeneracy

| Quantity | Baseline p50 / p95 | Pair-ranked p50 / p95 |
|---|---:|---:|
| Delivered candidates | 135 / 149 | 146 / 169 |
| Packed characters | 31,992 / 32,000 | 31,992 / 32,000 |
| Best exact-evidence rank | 9 / 146 | 2 / 77 |

Candidate text ranges from 16 to 734 characters, with median 237 and p95 452.
Each development conversation contains 76,549 to 94,365 candidate characters,
or 2.39x to 2.95x the budget, so the budget binds rather than admitting the
whole store. The baseline's repeated session score is a real tie plateau: once
a session ranks, its full run of pairs is ordered by source position. The
treatment breaks that plateau by pair similarity.

There is no feedback or recurrent state, so PF7 has no absorbing state to test.
The relevant degenerate states were exercised instead: tied inherited scores,
overflow followed by a later fitting candidate, singleton candidates, exact QA
duplicates, and malformed evidence references.

## 5. Surrogate audit

Session-touch is not an admissible primary measure. On the 871 unique questions
it reports 830 to 870 with 40 gains and zero losses, while exact evidence-pair
delivery reports 44 gains and 9 losses. Session-touch has 10 baseline and 15
treatment false hits and hides every strict loss.

Any-evidence delivery is exact about availability but is still not answer
sufficiency: it can pass when only one of several required evidence pairs is
present, and availability can improve without reader correctness. All-evidence
delivery is the stricter offline diagnostic. A future registration must state
which property its primary endpoint certifies and must retain a live-evaluation
requirement for answer quality.

## 6. Reproduction

The source bytes, split, model, and vector cache are hash-bound. The development
cache contains 2,236 exact solo-call float32 vectors from the carried embedding
model. Analysis reopened it read-only, recorded 2,247 cache hits, zero misses,
zero model calls, and zero embedding calls. A second analysis was byte-identical.
The pre-outcome inventory also replays byte-identically at SHA-256
`629aa6b2b7a43a694051675c821eb6df06e6469b12538745b026c2aedf7feb78`.

The artifact retains all 882 source QA rows with content hashes and duplicate
ordinals so the 871-question deduplication is reproducible. The harness filters
to development sample IDs before adapting dialogue or QA fields.

## 7. Registration boundary

The development result supports writing a successor registration, not opening
the holdout. Before that commit, the human author must lock:

1. The study identifier and claim.
2. Whether the primary endpoint is any exact evidence or all exact evidence.
3. Exact-duplicate handling; deduplication by canonical QA content is the clean
   PF5 option because the source has no QA IDs.
4. Both the success bar and the separately numbered lower signal bar.
5. The live-evaluation stage and its answer-level bars.

No holdout command exists in this harness. Adding one belongs after the
registration and its complete PF1-PF10 checklist are committed.
