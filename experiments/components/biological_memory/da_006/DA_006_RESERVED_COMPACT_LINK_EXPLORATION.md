# DA-006 Reserved Headroom and Compact Link Exploration

**Status:** `POST-OUTCOME EXPLORATION PROTOCOL`
**Date:** August 29, 2026
**Parent:** DA-005 stop commit `49b99d58`
**Standing:** descriptive representation diagnostic on spent NF-004 LoCoMo
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Can prospectively reserved headroom protect a direct core while compact
atomic-turn links recover evidence efficiently enough to repay the evidence
lost by shrinking the direct allocation?

DA-005 proved that the existing 16k direct pack leaves no room for a link.
DA-006 creates room before retrieval outcomes are known. It does not predict
harm or inspect evidence when allocating capacity.

This spent-corpus exploration cannot select a reserve, renderer, gate, reader,
production policy, or adoption decision.

## 2. Locked Population

Use DA-003's committed 26,100 first-emitter edge opportunities, DA-002's blind
direct ranks and scores, and the byte-locked LoCoMo conversation text. Use no
vector cache, embedder, or model.

Evaluate 1,098 primary questions after the blind artifact is sealed. One row is
one DA-003 edge opportunity. Every treatment remains within the same exact
16,000-character evidence budget.

## 3. Fixed Arms

For reserve `R` in `{256, 512, 1024, 2048}`:

1. exact-pack the unchanged direct pair order under `16,000 - R` characters;
2. render at most one linked payload into the reserved slice;
3. never remove or reorder an identity selected into the direct core;
4. reject the link when it exceeds `R` or its pair is already represented in
   the direct core.

Two fixed payload renderers produce eight arms:

- `PAIR_R{R}`: the complete linked user/assistant pair, with its carried
  candidate character cost;
- `TURN_R{R}`: one source dialogue turn from that pair. Choose the member with
  greatest candidate-corpus-IDF-weighted query-token coverage; break ties by
  earlier source order. Its cost is the exact `speaker: text` serialization.

The unused part of a reserve is not returned to direct packing. This isolates
prospective protection rather than opportunistically reallocating after seeing
whether a link fits.

`DIRECT_16K` is the unchanged NF-004 pair-rank control. It is not reconstructed
from treatment cores.

## 4. Blind Outputs

For every arm and edge record:

- direct-core pair identities and SHA-256;
- core characters, count, and removed-from-16k direct identities;
- link admitted, payload type, payload characters, pair identity, and selected
  dialogue identity or identities;
- total evidence characters and unused reserve;
- exact selected dialogue identities carried by core plus link.

No answer, evidence annotation, category, outcome, or reader field may enter
the blind process.

## 5. Fixed Analysis

After committing the blind rows and SHA-256, join dialogue-level exact evidence.
Require `DIRECT_16K` to reproduce 935/1,098 complete items.

For every arm report:

- complete items, gains, losses, and net versus `DIRECT_16K`;
- link admission count and rate;
- link-carried gains and reservation-caused losses;
- conversation-level gains, losses, and net;
- p10/p50/p90 core, link, total, and unused-reserve characters;
- retained DA-004 neighbor-carried and downstream-carried benefit items where
  the relevant evidence identity is representable by the arm.

For each reserve, compare `TURN` with `PAIR` by exact item discordances. Report
all eight arms. Do not interpolate, combine arms, return slack, change tie
breaking, add multiple links, tune a reserve, or select a winner.

An arm is `PROTECTED_CAPACITY_SIGNAL` descriptively only if it has positive net
versus direct, every loss is caused by the prospective core reservation, every
gain is link-carried, and all six conversations have nonnegative net. Otherwise
report `NO_PROTECTED_CAPACITY_SIGNAL`. This is not an adoption bar.

## 6. Preflight Part 1 - Exploration

**Behavioral identity.** A reserve shrinks direct packing before link content is
known, making its tail loss explicit. The link can consume only that fixed
headroom and cannot displace the retained core. `TURN` changes representation
from pair to one dialogue unit; it does not claim semantic extraction.

**Name-to-behavior.** Tests must establish exact core budgets, no slack return,
pair-fit rejection, already-core rejection, turn serialization, IDF coverage
choice, source-order ties, dialogue membership, core immutability, total budget,
and direct-control identity.

**Distribution.** Before labels report admissions, core removals, unused
reserve, pair/turn fit disagreement, empty query overlap, tie choices, and every
conversation. Cover singleton pairs, both turns over reserve, one turn over
reserve, and a linked pair already in core.

The primary surrogate risk is treating a query-overlapping turn as the evidence
turn. The second is hiding reservation losses by comparing only with the
smaller core. All outcomes remain relative to `DIRECT_16K`.

## 7. Preflight Part 2 - Checklist

- **PF1 Inputs:** verify DA-003 and DA-002 hashes, locked corpus bytes, 26,100
  edges, 1,104 questions, and six conversations.
- **PF2 Identity:** pass every name-to-behavior and degenerate test in Section 6.
- **PF3 Ordering:** commit this protocol before implementation and commit blind
  rows before importing evidence.
- **PF4 Reachability:** require nonzero link admissions and core removals for all
  arms, plus at least one pair-rejected/turn-admitted edge.
- **PF5 Keys:** preserve question, pair, seed, neighbor, and dialogue identities;
  reject duplicates, cross-pair turns, or missing joins.
- **PF6 Reproduction:** require direct selected pair digests to match DA-003 and
  direct dialogue-level complete to reproduce 935/1,098 after label join.
- **PF7 Absorbing state:** not applicable; require byte-identical blind replay.
- **PF8 Length:** enumerate all DA-003 edges and all primary edges; no fresh-
  corpus transfer is available.
- **PF9 Surrogate audit:** lexical turn choice is not evidence choice, protected
  core is not protected full direct delivery, and availability is not reader use.
- **PF10 Live boundary:** any reserve or renderer selection requires fresh data,
  a separately locked multi-edge policy, reader, and adoption criteria.

## 8. Stops and Outputs

Stop on hash mismatch, corpus drift, cache access, nondeterminism, budget
overflow, core mutation, dialogue-membership mismatch, direct-total mismatch,
or causal-accounting failure.

Commit blind rows, joined result, and report. Do not alter reserves, renderer,
turn choice, endpoint, or disposition after labels are opened.
