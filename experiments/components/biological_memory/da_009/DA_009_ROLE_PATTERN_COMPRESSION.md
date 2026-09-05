# DA-009 Reversible Role-Pattern Compression

**Status:** `POST-OUTCOME EXPLORATION PROTOCOL`
**Date:** August 30, 2026
**Parent:** DA-008 result commit `3227cf0c`
**Standing:** descriptive incremental architecture diagnostic on spent NF-004
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Can repeated pair-level speaker order be encoded once per context to create
additional protected capacity and recover more of DA-008's 51 reachable one-hop
gains, without changing direct evidence or DA-004's ranking?

DA-008 established reversible speaker dictionaries and 961 complete items. Its
benefit allocator leaves median 42 characters and 25 one-hop-rescuable items.
DA-009 changes only the reversible rendering; ranking and allocation are frozen.

## 2. Fixed Renderer

Start from each DA-008 compact direct context and exact direct identity sequence.
Choose the most frequent ordered tuple of speaker codes among selected direct
pairs as the default role pattern; break count ties lexicographically. Add one
header `@pair=<comma-separated codes>`.

For a pair matching the default pattern, render member text byte-exact in member
order with one newline between members and omit per-member `<code>:` prefixes.
For every nonmatching pair, retain DA-008's explicit `<code>:<text>` rendering.
The speaker dictionary is unchanged. Pair boundaries and member fields remain
structural, as in the existing independently charged candidate representation.

The decoder must reconstruct every original `<speaker>: <text>` pair
serialization byte-for-byte. No identity, text, speaker, order, or attribution
may be dropped or inferred without the declared pattern.

For appended links, use the direct context's frozen default pattern. Matching
pairs use implicit rendering; exceptions remain explicit. New speakers extend
the dictionary exactly as DA-008 and make the pair explicit. Charge every new
dictionary entry and payload exactly.

## 3. Fixed Allocation and Analysis

Reuse DA-008's committed DA-004 grouped out-of-conversation benefit scores,
feature order, ties, eligible edges, full-pair links, skip-on-overflow allocator,
and 16,000-character budget. Refit the fixed model only to reproduce the same
scores; do not add labels, features, thresholds, controls, or tuning.

Part A passes only if all 1,098 primary direct contexts preserve exact identity
digests, byte-exact decode, and 935 complete items; every row is non-expanding
relative to DA-008; and median incremental savings are at least 128 characters.

After Part A is sealed, report complete items, gains/losses versus direct and
DA-008, characters, admissions, gain depth, conversation cells, and retained
fraction of the 51-gain one-hop oracle. Every new gain must be link-carried.

Report `INCREMENTAL_COMPACT_SIGNAL` descriptively only if DA-009 exceeds 961
complete, has zero losses versus direct, and no conversation falls below its
DA-008 benefit-arm complete total. Otherwise report
`NO_INCREMENTAL_COMPACT_SIGNAL`. This is not an adoption bar.

## 4. Preflight Part 1 - Exploration

**Behavioral identity.** One declared role tuple replaces only repeated speaker
codes. Exact speaker and text reconstruction remains mandatory before evidence.

**Name-to-behavior.** Tests must establish modal-pattern choice and ties,
matching and exception encoding, exact Unicode/newline reconstruction, new
speaker handling, incremental link charging, duplicate rejection,
skip-on-overflow continuation, stable rank replay, and total budget.

**Distribution.** Before evidence report default patterns, matching/exception
pairs, incremental savings and slack by conversation, expansions, eligible
neighbors, admissions, and overflow skips.

The primary surrogate risk is that structural reversibility does not prove a
reader follows the role header. The ranking remains spent-corpus evidence.

## 5. Preflight Part 2 - Checklist

- **PF1 Inputs:** verify DA-008 blind/result, DA-004 blind/labels, 25,941 primary
  edges, 1,098 primary questions, six conversations, 935 direct and 961 DA-008.
- **PF2 Identity:** pass every renderer, decoder, charging, and allocator test.
- **PF3 Ordering:** commit protocol before implementation and blind role rows
  before evidence access.
- **PF4 Reachability:** require matching and exception pairs, positive savings,
  link admissions, overflow skips, and at least one allocation differing from
  DA-008.
- **PF5 Keys:** preserve all question, direct, pair, dialogue, speaker, seed, and
  neighbor keys; reject duplicates or missing mappings.
- **PF6 Reproduction:** exact decode and digests; 935 direct, DA-008 961, DA-004
  57/40/25,844 labels, and grouped AUC .823401708567509.
- **PF7 Absorbing state:** not applicable; require byte-identical blind replay
  and deterministic scores/allocations.
- **PF8 Length:** use every primary question and edge; no transfer claim.
- **PF9 Surrogate audit:** reversible structure is availability, not reader use;
  extra complete items do not validate the learned ordering independently.
- **PF10 Live boundary:** adoption requires fresh transfer, reader validation,
  locked prompt syntax, latency, and prospective criteria.

## 6. Stops and Outputs

Stop on hash mismatch, decode drift, identity drift, expansion, median savings
below 128, score/allocation drift, budget overflow, population mismatch, direct
or DA-008 reproduction failure, any direct loss, or causal-accounting failure.
Commit blind rows before evidence, then result, report, scratchpad, and digest.

