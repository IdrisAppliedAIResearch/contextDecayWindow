# DA-003 Evidence-Blind Edge Utility Exploration

**Status:** `POST-OUTCOME EXPLORATION PROTOCOL`
**Date:** August 29, 2026
**Parent:** DA-002 at result commit `fc055a8b`
**Standing:** descriptive signal search on spent NF-004 LoCoMo
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Can information available before evidence labels distinguish a locally useful
temporal edge from an edge whose byte cost only displaces direct retrieval?

This exploration characterizes a new information family omitted from NF-004's
58-feature audit: candidate-text complementarity at the individual seed-edge
decision. It cannot select a gate, threshold, depth, production policy, reader,
or adoption decision.

## 2. Population and Unit

Use the locked six-conversation NF-004 LoCoMo population, its retained vector
cache, DA-001's fixed 16k direct order, and no new calls. For each of 1,098
primary questions, enumerate the immediate previous and next pair of each of
the top 16 direct-ranked seeds, preserving first-emitter deduplication and
session boundaries.

One row is one unique `(question, seed, neighbor)` opportunity. The blind stage
also exact-packs `DIRECT` plus that one neighbor interleaved immediately after
its seed. It records the resulting identities but cannot read evidence fields.

## 3. Fixed Blind Features

Tokenization is lowercase ASCII alphanumeric tokens. Corpus IDF is fixed from
all candidate pairs in the six locked conversations and does not use questions
or evidence annotations.

### 3.1 Query-facing complementarity

- IDF-weighted query coverage by seed, neighbor, and their union;
- neighbor-only and seed-only IDF-weighted query coverage;
- counts of query tokens matched by seed, neighbor, and neighbor only;
- numeric-token and four-digit-year matches by seed and neighbor;
- seed and neighbor own query cosine, their difference, and maximum;
- cosine between seed and neighbor from retained candidate vectors;
- residual semantic score `neighbor_query_cosine - seed_neighbor_cosine *
  seed_query_cosine`.

### 3.2 Exact admission cost

- neighbor and seed characters;
- direct slack and counterfactual packed characters;
- displaced candidate count and characters;
- displaced own-score sum, maximum, minimum, and mean;
- neighbor score minus displaced maximum and mean;
- whether the neighbor already fits in `DIRECT`;
- seed rank, neighbor direct rank, signed direction, and rank gap.

### 3.3 Fixed summaries

Report every feature's p10/p50/p90 for positive, negative, and neutral edges.
For benefit and harm separately, report pooled and per-conversation univariate
AUC in the direction chosen from the feature definition, not from outcomes.

Evaluate one multivariable L2 logistic model for each endpoint with
leave-one-conversation-out prediction. Median imputation and standardization
are fit on training conversations only. Fix `C=1`; do not tune it. Report pooled
ROC AUC, average precision, Brier score, and every evaluable held-out
conversation AUC. No permutation test, feature selection, interaction,
nonlinear model, or threshold is permitted.

## 4. Labels Opened After Seal

After the blind edge rows and their file SHA-256 are committed, join NF-004
evidence identities.

- `BENEFIT`: the one-edge counterfactual changes an incomplete `DIRECT` item to
  complete because the admitted neighbor carries missing evidence.
- `HARM`: the one-edge counterfactual changes a complete `DIRECT` item to
  incomplete because exact packing displaces evidence.
- `NEUTRAL`: neither transition occurs.

An edge cannot be both `BENEFIT` and `HARM` at the complete-item endpoint.
Benefit and harm models use all rows, with their named class positive. Repeated
edges from one question remain grouped within its conversation; uncertainty is
descriptive because only six groups exist.

## 5. Preflight Part 1 - Exploration

**Behavioral identity.** An edge is a one-neighbor insertion immediately after
its direct-ranked seed followed by the unchanged exact 16k packer. It adds no
budget and can help only by admitting missing evidence or harm only by
displacing directly delivered evidence.

**Name-to-behavior.** Tests must establish previous/next direction, session
boundary rejection, first-emitter deduplication, top-16 seed identity, one-edge
interleaving, exact skip-on-overflow packing, displaced identity, token/IDF
identity, retained-vector identity, and residual-score arithmetic.

**Distribution.** Preserve every conversation and direction. Report duplicate
neighbor nominations before deduplication, already-direct neighbors, no-cost
admissions, overflow skips, zero-overlap texts, empty displaced sets, and
single-class held-out folds.

The primary surrogate risk is lexical overlap that repeats the question while
omitting its answer. A second is treating low displaced cosine mass as proof
that no evidence was lost. These features are decision-time proxies only.

## 6. Preflight Part 2 - Checklist

- **PF1 Inputs:** verify locked corpus, cache, DA-001 blind selections, DA-002
  provenance, 1,104 questions, 1,098 primary items, six conversations, and zero
  cache misses.
- **PF2 Identity:** pass every name-to-behavior and degenerate test in Section 5.
- **PF3 Ordering:** commit this protocol before implementation and commit blind
  edge rows before importing evidence annotations.
- **PF4 Reachability:** require at least one one-edge benefit, harm, and neutral
  after label join; otherwise stop with the observed degeneracy.
- **PF5 Keys:** carry comparison, candidate, seed, neighbor, and counterfactual
  payload identities; reject duplicate or missing joins.
- **PF6 Reproduction:** direct exact delivery must reproduce 935/1,098 and every
  one-edge transition must have the causal admission/displacement identity.
- **PF7 Absorbing state:** not applicable; require byte-identical blind replay.
- **PF8 Length:** enumerate all unique immediate edges from the first 16 direct
  seeds for every primary question; this cannot establish new-corpus transfer.
- **PF9 Surrogate audit:** text complementarity is not answer complementarity,
  cosine is not utility, and availability is not reader use.
- **PF10 Live boundary:** a gate test requires a fresh corpus, a separately
  locked rule, and prospective reader and adoption criteria.

## 7. Stops and Outputs

Stop on any hash mismatch, cache miss, evidence access before seal, ambiguous
first emitter, cross-session edge, nondeterminism, direct-total mismatch, or
causal-accounting failure.

Commit a blind edge artifact, joined result artifact, and report. Do not add or
remove a feature, endpoint, model, subgroup, depth, threshold, or interpretation
after labels are opened.
