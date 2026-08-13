# NF-005 Exploration - Candidate Information Dilution

**Status:** `EXPLORATION COMPLETE - DESIGN NOT YET LOCKED`
**Artifact:** `artifacts/exploration.json`
**Model calls:** 0
**Embedding calls:** 0
**Date:** August 13, 2026

## Behavioral identity

A LongMemEval episode pairs a usually short evidence-bearing user turn with a
much longer assistant turn before one cosine is computed. Splitting the carried
episode back into its two source turns preserves an exact `has_answer` evidence
join while removing that forced aggregation.

The names were checked against behavior on the 465 NF-003 items. An `episode`
is exactly a valid user/assistant pair rendered by the carried formatter. A
`source turn` is one member of that pair with its role label retained. An
`evidence turn` is exactly a source turn whose corpus `has_answer` flag is true;
it is not inferred from answer-string overlap.

## Distributions

| Candidate population | n | p10 chars | p50 chars | p90 chars |
|---|---:|---:|---:|---:|
| LoCoMo adjacent pairs | 3,011 | 126 | 241 | 417 |
| LongMemEval episodes | 106,412 | 778 | 2,006 | 3,175 |
| LongMemEval evidence episodes | 878 | 1,307 | 2,550 | 3,358 |
| LongMemEval source turns | 212,824 | 116 | 435 | 2,570 |
| LongMemEval evidence turns | 881 | 190 | 298 | 472 |

The median evidence episode is 10.58 times the median LoCoMo pair and 8.56
times its own candidate class's median evidence turn. Of 881 exact evidence
flags, 831 are on user turns and 50 on assistant turns.

Longer evidence episodes rank worse by their own query cosine. Spearman's rho
between evidence-episode characters and best normalized evidence rank is
`0.484` overall and positive in all six question classes, ranging from `0.133`
to `0.792`. This is association, not identification: length, localization, and
semantic content all change together.

## Degenerate states and feasibility

The mechanism has no feedback. Full-store fit is its only absorbing delivery
ceiling. Four source-turn occurrences exceed the 32,000-character budget and
can never be packed; this must remain visible rather than be truncated or
silently excluded.

All 465 query vectors hit the retained exact-solo cache. None of the 167,918
unique rendered source-turn texts do. NF-005 therefore cannot honestly be
described as a zero-call replay. Any registered test needs a post-lock vector
capture phase with the pinned embedder, exact solo calls, a call-shape
sentinel, and a sealed content-addressed cache before measurement.

## Surrogate audit

Counting any span from an answer episode would let a non-evidence assistant
turn certify delivery of an omitted evidence-bearing user turn. NF-005 must
instead score the exact turn-level `has_answer` identities. A positive result
would support information dilution as a moderator, but cannot isolate raw
character count from semantic localization. Availability also cannot certify
reader correctness.
