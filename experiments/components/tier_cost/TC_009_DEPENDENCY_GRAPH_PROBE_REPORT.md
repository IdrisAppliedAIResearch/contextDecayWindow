# TC-009 dependency-graph subject probe — report

**Status:** `NO_POSITIVE_SIGNAL`; descriptive feasibility diagnostic  
**Design commit:** `d6af16e4`  
**Amendment commit:** `84b9267c`  
**Implementation and Preflight commit:** `a48d7d5e`  
**Date:** 2026-08-23

## Result

Dependency parsing can mechanically expose grammatical subjects, but neither
subject matching nor graph centrality is a useful replacement for dense
semantic ranking here. Every frozen treatment regresses the accepted 32k dense
baseline on combined, targeted, and breadth evidence delivery, and in all four
conversations.

| Arm | Combined complete | Gains/losses | Targeted complete | Gains/losses | Breadth complete | Breadth identity net |
|---|---:|---:|---:|---:|---:|---:|
| Dense | 810 | — | 680 | — | 27 | — |
| IDF lexical overlap | 727 | 21 / 104 | 632 | 15 / 63 | 15 | -19 |
| Dependency PageRank | 677 | 16 / 149 | 598 | 11 / 93 | 10 | -41 |
| Subject overlap | 316 | 12 / 506 | 284 | 9 / 405 | 3 | -73 |
| Subject-personalized PageRank | 344 | 8 / 474 | 320 | 6 / 366 | 3 | -65 |

No arm passes any clause of the frozen positive-feedback rule.

## What happened

Plain exact-word overlap retains substantial signal, but still loses 83
complete questions to dense. Adding dependency PageRank makes that lexical
signal worse: it loses another 50 complete questions versus the lexical
control. Required evidence has median rank 4 under both dense and lexical, but
rank 20 under dependency PageRank. Centrality downweights query words when they
are peripheral in a section even when those words carry the answer.

Grammatical subjects are far too sparse to rank a whole conversation. The
median question has 295 zero-scoring candidates under direct subject overlap
and 261 under subject-personalized PageRank. Required evidence falls to median
ranks 136 and 115. A section's answer-bearing entity is often an object,
attribute, location, number, or subject expressed with a pronoun; “grammatical
subject” is not the same property as “what this section is about.”

The graph route is also not operationally lightweight at this granularity.
Preflight needed 204,409 personalized PageRank solutions because personalization
changes for each query–pair overlap. This is deterministic and model-free in
the program's sense, but it spends more computation to deliver less evidence.

## Integrity and boundary

The initial Preflight stopped because label-blind exploration had overstated
questions with any exact subject overlap as 871/871; the implemented count is
870/871. Amendment `TC009-DEPGRAPH-001` corrected only that expected blind
count before outcome, retained the zero-score case, and changed no route,
fallback, parameter, population, or success clause.

Corrected Preflight parsed 1,365 pair and 871 question documents, reproduced
all 871 accepted dense selected-id and payload digests using one-dimensional
dummy vectors, and converged 1,365 standard plus 204,409 personalized PageRank
runs with maximum 175 iterations. It used zero embedding vectors, zero
embedding calls, and zero LLM/generative calls. The outcome loaded sealed
selections with zero parser or model calls.

Availability only on used LoCoMo development data. This does not test a trained
subject classifier, entity linking, semantic-role labeling, propositions, or a
hybrid with dense ranking. It provides no positive feedback for TC-010,
deployment, or reader answers.

The final repository suite is 2,238 passed.
