# DA-013 Cumulative Architecture Cross-Corpus Stress Test

**Status:** `REGISTERED SPENT-CORPUS STRESS TEST`
**Date:** August 30, 2026
**Parent:** DA-012 result commit `3f81bb00`
**Standing:** prospective transfer to previously studied LongMemEval; not fresh confirmation
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Does the cumulative NF-004 architecture transfer across corpus structure without
changing direct evidence: exact episode ranking, reversible role-pattern direct
rendering, and temporal links ordered by a model trained only on NF-004?

LongMemEval has already been used throughout NF-002 through NF-007 and related
work. This run is therefore a spent cross-corpus stress test. It can expose a
mechanical failure or a transfer signal, but cannot confirm adoption or reader
value.

## 2. Locked Population and Inputs

Use the exact 465 question IDs in committed NF-003 Part 1 and their committed
NF-005 exact `has_answer` turn identities. Exclude no additional item and add no
item. Lock the source dataset to SHA-256
`d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`.

Use the retained read-only EC-002 exact-solo vector cache. Every question and
episode text must hit exactly; any miss stops the study. No vector may be
generated or written.

The budget is 16,000 Python characters. Candidates are accepted by
skip-on-overflow. Direct ranking is descending cosine between the question and
each full user/assistant episode, with the existing NF-005 deterministic tie
rule. The selected direct episode identities are frozen before evidence access.

## 3. Fixed Architecture

### Direct renderer

`DIRECT_ORIGINAL` charges the carried `User: ...\nAssistant: ...` rendering.
`COMPACT_DIRECT` preserves the exact selected direct identities and order while
using DA-009's reversible speaker dictionary plus modal role pattern. Decoding
must reproduce every original episode byte-for-byte. Compact rendering may not
expand any question.

### Temporal edges

For the first 16 direct seeds, offer the immediately prior and next episode in
the same session. Deduplicate by first emitter; ties are direct seed rank, prior
before next, then neighbor identity. Never offer a direct identity as a link.

Each admitted link first attempts the complete neighbor episode under the
locked role-pattern context. If it does not fit, attempt the one source turn
with maximum IDF-weighted question coverage, with source order as the tie rule.
Continue after overflow. Direct context is immutable: links only consume compact
slack and cannot displace, reorder, or rewrite a direct episode.

### Transferred ordering model

Refit DA-004's exact fixed L2 logistic pipeline on all 25,941 labelled NF-004
primary edges: all 73 sealed features in committed order, median imputation,
standardization, penalty 1, no class weighting. No LongMemEval outcome enters
the fit, feature choice, ordering, threshold, or tie rule.

Apply the refit to LongMemEval whole-pack perturbation features computed with
the same formulas. Because direct context is protected, the hypothetical pack
is direct plus that edge's pair-then-turn action under current compact slack.
Unchanged/displacement fields remain mechanically defined, including zeros.

Run two link orders:

- `TEMPORAL_ORDER`: seed rank, prior before next, neighbor identity.
- `TRANSFER_BENEFIT`: descending transferred DA-004 probability, then the
  temporal tie rule.

No threshold, blend, carrier model, feature selection, coefficient inspection,
hyperparameter change, or target-corpus tuning is allowed.

## 4. Exact Endpoint and Analysis

An item is complete only when every committed target turn identity is present in
the delivered direct episodes or link payloads. A full episode carries both turn
identities; a fallback turn carries only its own identity.

Report complete items for `DIRECT_ORIGINAL`, `COMPACT_DIRECT`,
`TEMPORAL_ORDER`, and `TRANSFER_BENEFIT`; gains/losses against direct; paired
exact tests; question-type cells; direct counts/chars/savings/slack; edge and
admission counts; full-pair versus turn-fallback actions; carrier provenance;
and the one-hop reachable ceiling under the fixed seed set.

`COMPACT_DIRECT` must be evidence-identical to `DIRECT_ORIGINAL`. Every link gain
must be carried by an admitted target identity. Any direct loss or unexplained
gain stops the study.

Report `CROSS_CORPUS_CAPACITY_SIGNAL` descriptively only if
`TRANSFER_BENEFIT` has at least five gains and zero losses against direct, every
question-type cell is nonnegative, and exceeds `TEMPORAL_ORDER`. Otherwise
report `NO_CROSS_CORPUS_CAPACITY_SIGNAL`. This is not an adoption bar.

## 5. Preflight Part 1 - Exploration

**Behavioral identity.** Direct selection is frozen under the original 16k
episode pack. Compression changes charging only. Links use only newly exposed
slack, so direct evidence cannot move.

**Name-to-behavior.** Tests must establish exact population reconstruction,
read-only cache hits, deterministic direct ranking, skip-on-overflow, reversible
role rendering, immutable direct identities, same-session neighbor construction,
pair-then-turn fallback, DA-004 feature order and full-NF-004-only fitting.

**Distribution.** Before evidence access report population, episodes, sessions,
question types, cache hits, direct counts/chars, compact savings/slack, edge
reachability, fallback reachability, feature finiteness, score variation and
byte-identical replay. Evidence prevalence and outcome distributions remain
sealed until this artifact is committed.

Primary risks are accidental reuse of LongMemEval labels while ranking, changing
direct selection under compact charging, treating a spent corpus as independent,
and importing NF-004 feature semantics that are mechanically degenerate here.

## 6. Preflight Part 2 - Checklist

- **PF1 Inputs:** verify dataset, cache, NF-003 population, NF-005 target and
  DA-004 blind/label hashes; require 465 joined questions.
- **PF2 Identity:** pass tests for every behavior named in Section 5.
- **PF3 Ordering:** commit this protocol and then commit mechanical selection,
  features, scores and allocations before reading `has_answer` or target IDs.
- **PF4 Reachability:** require positive compact savings, temporal edges, pair
  admissions, turn fallbacks, overflow skips and nonconstant transfer scores.
- **PF5 Keys:** preserve question, session, episode, turn, seed, neighbor,
  direction, feature, score and action keys; reject duplicates or missing joins.
- **PF6 Reproduction:** reproduce 465 NF-005 IDs, 106,412 episodes, zero cache
  misses, exact direct identity replay and the committed DA-004 training result.
- **PF7 Absorbing state:** not applicable; require deterministic byte-identical
  preflight and result replay.
- **PF8 Length:** process all 465 questions and every eligible fixed edge.
- **PF9 Surrogate audit:** availability is not answer use; LongMemEval is spent;
  zero-loss follows immutable direct context and is not learned safety.
- **PF10 Live boundary:** no reader, adoption, latency, fresh-validation or
  production claim is authorized.

## 7. Stops and Outputs

Stop on any hash mismatch, cache miss/write, population drift, direct identity
change, renderer expansion, target leakage, DA-004 reproduction failure,
unreachable fallback, nondeterminism, direct loss, or causal-accounting failure.

Commit in order: protocol, evidence-blind Part 1 artifact and tests, then opened
outcomes, report, scratchpad and digest. Do not repair a failed gate post hoc.

