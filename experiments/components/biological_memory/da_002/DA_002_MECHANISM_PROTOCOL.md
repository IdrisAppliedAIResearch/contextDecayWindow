# DA-002 Linked-Context Mechanism Decomposition Protocol

**Status:** `POST-OUTCOME REANALYSIS PROTOCOL`
**Date:** August 29, 2026
**Parent:** DA-001 at blind-selection commit `1181e24d`
**Standing:** descriptive mechanism audit on spent NF-004 LoCoMo
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

What caused DA-001's temporal-link gains and losses, why did shallow temporal
expansion help while full-event expansion regressed, and why did `conv-44`
reverse the aggregate direction?

This audit explains already-open outcomes. It cannot confirm a moderator,
select a seed depth, tune a link gate, authorize a new arm, or make a reader or
adoption claim.

## 2. Provenance Reconstruction

Before evidence fields are opened by the analysis process, reconstruct every
DA-001 order from the locked corpus and retained cache. For every candidate and
arm record:

- own-cosine direct rank and score;
- selected status and selected position;
- whether it first entered directly or through a link;
- the first seed that emitted it, seed direct rank and score;
- signed pair offset within the session and absolute graph distance;
- candidate and seed character costs;
- whether it displaced or was displaced relative to `DIRECT`.

The provenance stage must reproduce all 12,144 DA-001 question-arm selected
identity digests exactly before writing its sealed artifact. It must not import
NF-004 measurement code, G6 outcomes, answers, categories, or evidence fields.

## 3. Fixed Decompositions

### 3.1 Cue transfer

For each gain, report every direct-missing evidence carrier's direct rank,
linked selected position, seed rank, signed offset, graph distance, evidence
score, seed score, score gap, and character cost. Summarize p10/p50/p90 and full
counts for previous versus next links.

The cue-transfer description is supported only descriptively when the linked
evidence median direct rank is worse than the median direct selected count and
its seed median rank is inside the arm's fixed seed count. This is a mechanism
identity check, not a success bar.

### 3.2 Budget displacement

For each loss, report every direct-delivered evidence carrier removed by the
treatment: direct selected position and percentile, direct rank, score, chars,
linked chars admitted, and total direct candidates/chars displaced. Separate
losses caused by one versus multiple evidence carriers.

### 3.3 Incremental trajectory

Across `m={1,2,4,8,16}`, classify each primary item separately for `TEMPORAL`
and `EVENT` as always tied, persistent gain, persistent loss, late gain, late
loss, gain-then-loss, loss-then-gain, or multiple reversal. Report every class
and the exact first transition depth. Do not collapse nonmonotonic trajectories.

### 3.4 Local versus deep context

At each shared seed depth, partition EVENT gains into also gained by TEMPORAL
and EVENT-only; partition EVENT losses the same way. For EVENT-only gains,
report evidence graph distance. This identifies what deeper event traversal
adds beyond immediate neighbors and what it costs.

### 3.5 Conversation reversal

For every conversation and temporal depth, report:

- gain/loss and linked-carrier counts;
- linked characters per gain;
- displaced candidates per loss;
- gain-carrier seed rank, evidence rank, score gap, and direction;
- loss-carrier direct selected percentile and character cost.

Compare `conv-44` with the pooled other five using only medians and exact
counts. No hypothesis test, threshold, classifier, or post-hoc subgroup may be
added.

## 4. Preflight Part 1 - Exploration

**Behavioral identity.** DA-001 interleaves linked candidates ahead of their
own cosine position, then exact-packs the reordered list; a gain occurs only
when linked promotion moves missing evidence into the pack, and a loss occurs
only when linked cost displaces directly delivered evidence.

**Name-to-behavior.** Tests must establish first-emitter provenance under
deduplication, signed previous/next offset, graph distance, seed-rank identity,
selected position, and exact displaced identity. Multiple seeds may point to a
node, but only the first emitter receives causal admission credit because it
sets the node's order position.

**Distribution.** Report complete p10/p50/p90 plus counts, never only pooled
means. Preserve conversation and seed-depth cells even when empty.

**Degenerate states.** Cover singleton sessions, edge nodes, a node linked by
two seeds, a seed already emitted as a prior neighbor, a linked node skipped on
overflow, multiple evidence candidates, no gain/loss, and nonmonotonic item
trajectories. There is no feedback or absorbing state.

The primary surrogate risk is attributing a gain to a nearby seed merely
because both were selected. Causal credit requires that the evidence node first
entered through that seed and was absent from `DIRECT`.

## 5. Preflight Part 2 - Checklist

- **PF1 Inputs:** verify hashes for corpus, cache, DA-001 blind selections,
  preflight, result, and NF-004 G6; require 1,104 questions and 11 arms.
- **PF2 Identity:** run every name-to-behavior and degenerate test in Section 4.
- **PF3 Ordering:** commit this protocol before implementation; commit
  provenance before the analysis process opens evidence.
- **PF4 Reachability:** DA-001 has gains and losses in both traversal families;
  empty trajectory or direction cells remain reportable.
- **PF5 Keys:** carry NF-004 comparison/candidate identities and reject every
  duplicate or missing join.
- **PF6 Reproduction:** require 12,144/12,144 selected digests, DA-001's full
  11-arm complete/gain/loss matrix, and NF-004's 935 direct total.
- **PF7 Absorbing state:** not applicable to stateless question replay; require
  byte-identical provenance replay.
- **PF8 Length:** all 1,098 primary items and all DA-001 transitions; cannot
  establish new-corpus transfer or reader effects.
- **PF9 Surrogate audit:** seed adjacency is not semantic dependence, exact
  evidence availability is not answer use, and median rank can hide
  conversation reversal. Preserve those residuals.
- **PF10 Live boundary:** any answer or adoption claim requires a new corpus and
  prospective live registration.

## 6. Stops and Outputs

Stop on any digest mismatch, cache miss, early evidence access, provenance
ambiguity, session crossing, incomplete order, nondeterminism, matrix mismatch,
or population drift.

Commit a blind provenance artifact, joined mechanism artifact, and report. Do
not add a feature, arm, seed depth, statistic, threshold, or interpretation
after evidence opens.
