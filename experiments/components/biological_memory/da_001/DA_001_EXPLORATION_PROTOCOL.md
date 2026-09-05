# DA-001 Light Linked-Context Exploration Protocol

**Status:** `EXPLORATION PROTOCOL - OUTCOMES ALREADY OPEN`
**Date:** August 29, 2026
**Parent:** NF-004 item anatomy
**Standing:** post-outcome architecture characterization on spent LoCoMo
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question and boundary

Does an explicit link from a directly retrieved adjacent-turn pair to nearby or
session-level derivative context recover exact NF-004 evidence that direct pair
ranking misses, and what direct evidence does that expansion displace under the
same 16,000-character budget?

This is a light feasibility exploration, not a study or selector search. It
uses NF-004's opened holdout and may report only descriptive availability. It
does not test atomic fact extraction: the current adjacent-turn pair is a fact
proxy, and the source session is an event/context proxy.

## 2. Fixed substrate

- NF-004's six holdout conversations, 1,104 canonical questions and 1,098
  primary exact-evidence items.
- NF-004 adjacent-turn candidates, retained Qwen3 vectors, own-pair cosine
  order, skip-on-overflow packer, and 16,000 candidate-text-character budget.
- Stable candidate and question identities carried unchanged.
- Zero new embeddings, generations, readers, or judges.

The evidence-blind stage may read question text, candidate text, vectors,
session membership, and pair order. It may not read answers, categories,
evidence identities, evidence counts, or NF-004 outcome rows.

## 3. Linked representation

Each pair candidate is one node. Within each source session, nodes form a
bidirectional temporal chain in source order.

- `DIRECT`: NF-004 pair-cosine order with no traversal.
- `TEMPORAL_m`: for each of the first `m` direct seeds, emit the seed and its
  immediate previous and next nodes in the same session; deduplicate; then emit
  every remaining node in direct order.
- `EVENT_m`: for each of the first `m` direct seeds, emit the seed and then all
  other nodes in its session by increasing chain distance, breaking equal
  distance toward earlier source order; deduplicate; then emit every remaining
  node in direct order.

The fixed seed counts are `m in {1, 2, 4, 8, 16}`. The full 11-arm matrix is
reported. No seed count or traversal may be selected, promoted, or called best.
Every order is packed by NF-004's unchanged 16k skip-on-overflow rule.

`linked_admission` means a selected candidate entered through an expansion
position before its ordinary direct-order position. A candidate merely sharing
a session with a seed does not count if direct order already emitted it first.

## 4. Measures

For every question-arm before labels are opened, record:

- complete selected identity sequence and digest;
- packed characters, selected count, sessions touched;
- linked admissions and linked characters;
- direct-control candidates and characters displaced;
- order displacement from `DIRECT` for every candidate.

After the blind artifact is committed, join exact evidence candidate identities
and report for every arm:

- complete and any exact-evidence delivery over 1,098 primary items;
- gains, losses, and ties versus `DIRECT`;
- gain/loss counts on NF-004's 188 original discordances;
- gains whose missing evidence entered through a link;
- losses whose formerly delivered evidence was displaced;
- linked admission, character, and displacement distributions by conversation.

No p-values, winner, aggregate utility score, reader inference, or architecture
adoption decision are authorized.

## 5. Preflight Part 1 - Exploration

**Behavioral identity.** On a real NF-004 trace, `TEMPORAL_m` promotes at most
two chain neighbors per direct seed, while `EVENT_m` promotes the seed's whole
session by graph distance; both spend the same budget by displacing later
direct-ranked candidates.

**Name-to-behavior.** Before label access, tests must show: predecessor and
successor never cross a session boundary; event expansion includes exactly one
source session; graph-distance order is exact; deduplication emits every node
once; the direct suffix preserves own-cosine order; and `m=0` reproduces
`DIRECT` byte-for-byte as a planted control.

**Distribution.** The blind report records all 11 arms over all 1,104 questions,
including p10/p50/p90/max linked admissions, linked characters, displaced
candidates, packed characters, and sessions touched. A median alone is not a
mechanism characterization.

**Degenerate states.** Test singleton sessions, edge nodes with one neighbor,
multiple seeds in one session, linked nodes already emitted directly, sessions
larger than the budget, and full-store-fit convergence. There is no feedback
across questions or turns, so no absorbing state exists.

The known surrogate is session touch: it can pass while the required pair is
absent. Only exact candidate identity joined after selection may count as
evidence delivery.

## 6. Preflight Part 2 - Checklist

- **PF1 Inputs:** hash corpus, vector manifest/cache, NF-004 mechanism, and G6
  labels; require six conversations, 1,104 blind rows, 1,098 primary rows, and
  zero cache misses.
- **PF2 Identity:** execute the name-to-behavior and degenerate tests in Section
  5 on synthetic cases plus all real traces.
- **PF3 Ordering:** commit protocol before implementation; commit blind
  selections before the label-join process may open G6.
- **PF4 Reachability:** report the blind count of questions on which every
  treatment differs from `DIRECT`; an inert arm remains a valid finding.
- **PF5 Keys:** use NF-004 canonical comparison and candidate identities; reject
  duplicates or missing joins.
- **PF6 Reproduction:** `DIRECT` must reproduce NF-004 pair selected metrics and,
  after label join, 935 complete deliveries and 140/48 against session ranking.
  Historical selected identities were not retained; DA-001 inherits the item-
  anatomy Amendment 001 limitation.
- **PF7 Absorbing state:** not applicable because each question is a stateless
  replay; demonstrate identical output on repeated calls.
- **PF8 Length:** all 1,098 primary items and all 188 original discordances;
  cannot detect reader behavior or fresh-corpus transfer.
- **PF9 Surrogate audit:** exact evidence delivery can still pass while a reader
  fails; linked delivery can also be credited while direct evidence is
  displaced. Report both gains and losses separately.
- **PF10 Live boundary:** any reader or adoption claim requires a new corpus and
  prospective live registration with exact rendering cost and no-regression
  bars.

## 7. Stops and outputs

Stop on input drift, cache miss, early label access, duplicate key, direct replay
failure, nondeterminism, link crossing a session, incomplete order, budget
breach, or primary count mismatch.

Commit a blind preflight artifact, a joined matrix artifact, and a concise
report. Preserve the whole matrix and negative results. Do not add a traversal,
seed count, endpoint, subgroup, or statistic after labels open.
