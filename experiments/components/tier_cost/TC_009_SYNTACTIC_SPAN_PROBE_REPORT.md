# TC-009 syntactic-span retrieval probe — report

**Status:** `NO_POSITIVE_SIGNAL`; descriptive feasibility diagnostic  
**Design commit:** `3d472faf`  
**Implementation commit:** `ef249a4c`  
**Implementation repair:** `676f741d`  
**Preflight commit:** `1b62934c`  
**Bias-diagnostic commit:** `89a9dee3`  
**Date:** 2026-08-23

## Result

Syntactic spans can be extracted and embedded, but neither frozen span score is
a useful retrieval signal. Ranking complete adjacent-turn pairs by their most
query-similar noun phrase or subject-bearing sentence severely regresses the
accepted 32k whole-pair cosine baseline.

| Arm | Combined complete | Gains/losses | Targeted complete | Gains/losses | Breadth complete | Breadth identity net |
|---|---:|---:|---:|---:|---:|---:|
| Dense | 810 | — | 680 | — | 27 | — |
| Noun-phrase max | 443 | 16 / 383 | 391 | 13 / 302 | 10 | -57 |
| Subject-sentence max | 659 | 14 / 165 | 580 | 11 / 111 | 13 | -26 |

All four conversations regress under both arms. Neither treatment passes any
clause of the frozen positive-feedback rule.

## What happened

The max-over-spans operation modestly rewards candidates with more spans:
median within-question score/count correlation is `.255` for nouns and `.184`
for subject sentences. Selected noun candidates have median 15 spans versus 14
in the store; subject counts are 4 versus 4. This is not merely a verbosity
failure.

The more important failure is rank displacement. Required evidence lost by
noun ranking has median dense rank **5**; for subject-sentence ranking it is
**14**. The few recovered identities enter at median treatment ranks 38.5 and
65. A short noun phrase or subject sentence can resemble the query while the
surrounding pair lacks the answer, and a required pair can express its useful
fact outside the locally best-scoring span.

The result distinguishes feasibility from value: nouns and grammatical
subjects are mechanically recoverable from raw text with a parser, but their
maximum embedding cosine is not a safe ranking criterion.

## Integrity and boundary

Label-blind exploration parsed 1,365 pair documents into 4,935 unique noun
phrases and 5,385 unique subject-bearing sentences. Capture embedded 10,320
unique span texts in 162 fixed batches using the carried embedding model;
there were zero LLM/generative calls. Preflight then used the sealed vectors,
reproduced all 871 accepted dense selections and payloads, exercised noun and
subject fallback states, and committed selection bytes before labels. The
outcome phase made zero parser, embedding or LLM calls and zero cache misses.

Availability only on used LoCoMo development data. This does not test packing
the spans themselves, a trained syntactic probe, propositions, or a new corpus.
It provides no positive feedback for committing noun/subject max-cosine
reranking. No TC-010, selector or reader work is authorized. The final
repository suite is 2,233 passed.
