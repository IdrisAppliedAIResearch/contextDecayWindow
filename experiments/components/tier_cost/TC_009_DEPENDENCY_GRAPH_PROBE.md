# TC-009 dependency-graph subject probe

**Type:** descriptive feasibility diagnostic; not TC-010  
**Status:** design lock before implementation  
**Date:** 2026-08-23  
**Parent:** TC-009 and its syntactic-span probe

## 1. Question and claim boundary

Test whether dependency syntax and graph centrality can identify the subject of
a complete adjacent-turn pair well enough to rank evidence at 32,000 characters
without using an embedding model.

This is a label-blind lexical/syntactic probe, not a semantic-retrieval system.
A positive result would justify a registered successor; it would not select,
ship, or live-test a route. A negative result closes only the definitions below
on used LoCoMo development data. The accepted dense arm is replayed from frozen
identities and payloads; no embedding vectors are read or produced.

## 2. Label-blind exploration

Executed before this lock on the committed TC-009 blind manifest with spaCy
3.8.14 and installed `en_core_web_sm`, with NER and text classification
disabled. A content token is a non-space, non-punctuation, non-stop token whose
POS is `NOUN`, `PROPN`, `VERB`, `ADJ`, or `NUM`; its key is the case-folded
lemma.

- 1,365 complete adjacent-turn pairs and 871 questions;
- pair content graphs have median 16 and maximum 46 unique lemma nodes;
- grammatical-subject sets have median 1 and maximum 7 nodes;
- 402 pairs have no grammatical-subject node;
- every question has at least one candidate with exact content-lemma overlap;
- every question has at least one candidate with exact subject-lemma overlap;
- no query has an empty content-token set.

Thus the intended signals, ties, and subject-empty state all exist. The parser
is a trained, non-generative component and its document calls are reported
separately from LLM calls.

## 3. Frozen representation and algorithms

Global IDF is computed label-blind across the 1,365 pair documents as
`log((N + 1) / (df + 1)) + 1`.

For each pair, create an undirected weighted dependency graph:

1. nodes are its unique content-lemma keys;
2. for each dependency token-head relation whose endpoints are distinct content
   keys, increment that undirected edge's weight by one;
3. include isolated content nodes; ignore self-loops and excluded tokens; and
4. grammatical-subject nodes are content keys occurring with dependency label
   `nsubj`, `nsubjpass`, or `csubj`.

PageRank uses damping 0.85, L1 tolerance `1e-12`, at most 200 iterations, and a
deterministic sorted-node update. Standard PageRank uses uniform teleportation;
dangling mass follows the teleportation distribution. Personalized PageRank
uses query-shared graph nodes as teleport seeds, proportional to their IDF. If
there is no shared seed or no subject node, its candidate score is zero.

## 4. Frozen arms

Every arm ranks the same complete pair candidates and packs the original pair
elements with TC-009's full-budget dense packer at exactly 32,000 characters.
Ties use `(session_order, pair_order, candidate_identity)`.

- `A_DENSE`: accepted TC-009 whole-pair cosine order, replayed by identity only.
- `A_LEXICAL`: sum of IDF over query/pair content-lemma intersection.
- `A_SUBJECT_OVERLAP`: sum of IDF over query/pair grammatical-subject-lemma
  intersection.
- `A_DEP_PAGERANK`: sum, over query-shared graph nodes, of `IDF * PageRank`.
- `A_SUBJECT_PPR`: total personalized-PageRank mass on grammatical-subject
  nodes.

There is no embedding use, coefficient fitting, threshold, parser alternative,
edge-direction alternative, arm fusion, span packing, fallback, or parameter
sweep. `A_LEXICAL` is the control for whether graph structure adds anything to
exact lexical matching.

## 5. Population and endpoints

Run all 871 unique LoCoMo development questions. Formal descriptive reads use
the 868 eligible questions and the frozen `targeted` (704) and `breadth` (44)
populations. For every treatment versus dense, report paired:

- combined, targeted, and breadth complete-evidence gains/losses;
- breadth required-identity gains/losses and net identities;
- all four conversation-level combined complete nets;
- evidence-candidate dense and treatment ranks;
- score-zero, graph-size, PageRank-iteration, subject-empty selected, and
  subject-mass distributions; and
- each graph treatment against `A_LEXICAL` as a descriptive decomposition.

## 6. Frozen positive-feedback rule

A treatment is `DESCRIPTIVE_POSITIVE_SIGNAL` only if all hold:

1. combined complete-evidence gains exceed losses;
2. targeted complete-evidence gains are at least losses;
3. breadth required-identity net is positive;
4. breadth complete-evidence gains are at least losses; and
5. every conversation's combined complete net is nonnegative, with at least
   two conversations positive.

If no arm passes, disposition is `NO_POSITIVE_SIGNAL`. If one or more pass,
name them under `DESCRIPTIVE_POSITIVE_SIGNAL`. No p-value, optimization,
architecture selection, TC-010, or reader authorization follows.

## 7. Preflight — before label join

Part 1 must re-run and record §2's distributions, parser/model identities,
graph-content hash, subject-empty examples, and PageRank convergence before any
evidence import.

- **PF1:** hash/count corpus, blind manifest, accepted TC-009 selections,
  parser package/model, sealed graph and selection artifacts, and labels.
- **PF2:** planted traces prove content nodes, dependency edges, grammatical
  subjects, direct overlaps, and complete-pair packing match their names.
- **PF3:** graph construction and selection bytes close before the evidence
  module or per-question labels can import; planted early access fails.
- **PF4:** synthetic paired rows demonstrate every rule clause and both
  dispositions reachable.
- **PF5:** question content hashes and pair content identities only.
- **PF6:** `A_DENSE` reproduces all 871 accepted TC-009 32k selected-id and
  payload digests with dummy, non-retrieval vectors.
- **PF7:** standard and personalized PageRank converge on every real graph;
  a hand-solvable graph matches an independent matrix solution.
- **PF8:** four conversations can expose reversal but not new-corpus transfer.
- **PF9:** exact words, parser labels, and graph centrality can pass while
  subject meaning or reader value is false; report zero scores, subject-empty
  selections, graph size, and degree/length association.
- **PF10:** availability only; reader work requires separate registration.

The selection phase may call the dependency parser but may not import evidence
labels, read embedding vectors, or call an embedding model. The outcome phase
loads sealed selections with zero parser, embedding, cache, LLM, or generative
calls. Use one process, explicit UTF-8, and deterministic serialization.

## 8. Execution order

1. Commit this design alone.
2. Implement graph construction, custom PageRank, selection, measurement, and
   tests.
3. Commit passing PF1-PF10 and sealed graph/selection artifacts before labels.
4. Run the frozen outcome, report, update memory/README/AGENTS only if material,
   and open a stacked diagnostic PR. Do not create TC-010 or reader answers.
