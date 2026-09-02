# DA-010 Evidence-Blind Linked Payload Granularity

**Status:** `POST-OUTCOME EXPLORATION PROTOCOL`
**Date:** August 30, 2026
**Parent:** DA-009 result commit `7eca012a`
**Standing:** descriptive payload diagnostic on spent NF-004 LoCoMo
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Does full-pair link cost now limit protected evidence delivery, and can
evidence-blind atomic turns recover more of DA-009's 20 remaining one-hop gains?

DA-009 fixes direct rendering at 966 complete with DA-004 ordering. DA-010 holds
that direct renderer, edge scores, ordering, budget, and skip-on-overflow policy
fixed. Only linked payload granularity changes.

## 2. Blind Turn Order

Use DA-006's frozen lowercase ASCII-alphanumeric tokenization, candidate-corpus
IDF, and weighted query coverage. For each linked pair, order its members by
descending IDF-weighted query coverage of `<speaker>: <text>`, then source member
index. This order uses no answer, evidence identity, category, outcome, reader,
conversation feature, embedding, or model.

Render a single linked member explicitly as `<speaker-code>:<text>` under the
frozen DA-009 speaker dictionary. A new speaker extends the dictionary exactly
once. Singletons never use the two-member default role pattern. Every admitted
dialogue ID and character cost must remain exact.

## 3. Fixed Arms

Traverse the identical DA-004 grouped benefit edge order and reject direct or
previously linked identities as before:

- `FULL_PAIR`: exact DA-009 full-pair allocator; must reproduce 966.
- `BEST_TURN`: attempt only the first blind member of each neighbor pair.
- `ATOMIC_TURNS`: attempt both members independently in blind member order;
  skip an overflowing member and continue to the other member and later edges.
- `PAIR_THEN_TURN`: attempt the full pair; only when it overflows, attempt the
  first blind member; then continue to later edges.

An admitted full pair marks both dialogue IDs linked. An admitted singleton
marks only its own dialogue ID. Duplicate pair or dialogue admissions are
forbidden. No threshold, reserve, evidence-aware member choice, reranking,
backtracking, replacement, slack interpolation, or direct change is allowed.

## 4. Fixed Analysis

Commit blind member choices and payload costs before evidence access. Then
reproduce 935 direct, DA-009 966, the 25,941 DA-004 edge population and grouped
AUC .823401708567509.

For every arm report complete items, direct gains/losses, exact discordance with
`FULL_PAIR`, conversation cells, pair/member admissions, characters, overflow
actions, unused slack, gain depth, and whether each gain requires one or both
dialogue members. Every gain must be carried by admitted linked dialogue IDs;
any direct loss is a stop.

Report `COMPACT_PAYLOAD_SIGNAL` descriptively for an arm only if it exceeds 966,
has zero direct losses, and no conversation falls below `FULL_PAIR` complete.
Otherwise report `NO_COMPACT_PAYLOAD_SIGNAL`. Report all arms; do not select or
tune a production policy.

## 5. Preflight Part 1 - Exploration

**Behavioral identity.** Direct context is immutable. Payload arms differ only
in which exact linked dialogue members are appended and their measured cost.

**Name-to-behavior.** Tests must establish IDF member order and source ties,
explicit singleton charging, new-speaker extension, pair and dialogue duplicate
rejection, atomic second-member continuation, pair-overflow fallback only,
later-edge continuation, stable DA-004 ties, and total budget.

**Distribution.** Before evidence report selected member indices, pair/turn cost
ratios, turn coverage ties, new-speaker cases, eligible pairs/dialogues, blind
admissions and overflow actions by arm and conversation, and allocation
differences from full pair.

Primary surrogate risks are lexical overlap selecting the wrong evidence member
and atomic fragmentation admitting more text snippets without complete evidence.
Availability remains distinct from reader use.

## 6. Preflight Part 2 - Checklist

- **PF1 Inputs:** verify DA-009 blind/result, DA-004 blind/labels, DA-002
  provenance, 25,941 primary edges, 1,098 questions and six conversations.
- **PF2 Identity:** pass every member-order, renderer, allocator and degenerate
  test in Section 5.
- **PF3 Ordering:** commit protocol before implementation and blind payload rows
  before evidence access.
- **PF4 Reachability:** require both selected member indices, coverage ties,
  pair/turn cost differences, singleton admissions, pair fallback, atomic second
  admissions, overflow continuation, and arm allocation differences.
- **PF5 Keys:** preserve every question, seed, neighbor, pair, member, dialogue,
  speaker, direct and rank key; reject duplicates and missing mappings.
- **PF6 Reproduction:** exact direct decode/digests, 935 direct, 966 full pair,
  DA-004 labels 57/40/25,844 and grouped AUC .823401708567509.
- **PF7 Absorbing state:** not applicable; require byte-identical blind replay
  and deterministic scores/allocations.
- **PF8 Length:** use every primary question and edge; no fresh transfer.
- **PF9 Surrogate audit:** lexical member choice is not evidence localization;
  more admitted turns are not reader benefit.
- **PF10 Live boundary:** adoption requires fresh transfer, reader validation,
  locked syntax, latency, and prospective criteria.

## 7. Stops and Outputs

Stop on hash mismatch, direct drift, payload/dialogue drift, budget overflow,
nondeterminism, population mismatch, reproduction failure, any direct loss, or
causal-accounting failure. Commit blind rows, then result, report, scratchpad and
digest. No model, embedder, or cache access is authorized.

