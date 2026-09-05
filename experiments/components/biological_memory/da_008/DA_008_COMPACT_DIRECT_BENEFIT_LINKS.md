# DA-008 Reversible Compact Direct Rendering and Benefit-Ranked Links

**Status:** `POST-OUTCOME EXPLORATION PROTOCOL`
**Date:** August 30, 2026
**Parent:** DA-007 result commit `423ff082`
**Standing:** descriptive architecture diagnostic on spent NF-004 LoCoMo
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Can a reversible compact rendering create capacity without removing any direct
identity or dialogue content, and can DA-004's evidence-blind benefit ranking
use that capacity to improve exact evidence delivery?

DA-007 showed that reserving capacity by dropping the direct suffix loses more
evidence than temporal links restore. DA-008 instead freezes the actual 16k
direct selection, compacts only repeated speaker attribution, and validates
that representation independently before any linked evidence is scored.

This spent-corpus exploration cannot select a production renderer, threshold,
reader, live policy, or adoption decision.

## 2. Part A: Reversible Direct Renderer

Use the exact NF-004 `DIRECT_16K` selected pair sequence. Do not rerank, repack,
drop, truncate, summarize, or alter dialogue text.

For each question, assign speaker codes `0..n-1` by first occurrence in the
selected sequence. Render one dictionary entry per speaker as
`@<code>=<speaker>`. Render each pair member as `<code>:<text>`. Charge the
dictionary once and each selected pair independently; do not charge a separator
between pairs because the locked direct packer sums independent candidate
payload lengths. Speaker names and dialogue text remain byte-exact UTF-8.

The decoder must reconstruct every selected pair's original
`<speaker>: <text>` serialization byte-for-byte and in order. The compact cost
must not exceed the original direct cost. `SLACK = 16,000 - compact_cost`; the
unspent tail already present under the original pack is included because no
direct content is removed.

Part A passes `COMPACT_DIRECT_VALIDATED` only if all 1,098 primary questions
decode exactly, selected identity digests are unchanged, treatment remains at
935 complete items, every row is non-expanding, and median savings over the
original direct rendering are at least 256 characters. Otherwise stop before
Part B.

## 3. Part B: Frozen Link Allocation

Use DA-004's committed blind perturbation rows, fixed 58 features, and committed
edge labels. For each target conversation, fit DA-004's fixed L2 logistic
benefit model on the other five conversations only. Median imputation,
standardization, penalty 1, and feature order remain exactly DA-004. The target
conversation's labels never enter its scores.

Evaluate three locked orderings over primary edges whose neighbor pair is not
already direct-selected:

- `BENEFIT_MODEL`: descending grouped out-of-conversation predicted benefit;
- `QUERY_COVERAGE`: descending DA-004 `added_query_coverage`;
- `TEMPORAL_ORDER`: ascending seed direct rank, then prior before next.

All ties use seed direct rank, prior before next, neighbor identity. For each
question, traverse its ordered edges, skip a neighbor already direct or already
linked, and greedily append the full neighbor pair only when its incremental
dictionary-coded cost fits remaining slack. Skip-on-overflow continues to later
edges. Direct identities and rendering never change. No score threshold,
reserve, turn extraction, eviction, downstream repacking, or slack interpolation
is allowed.

## 4. Fixed Analysis

Report original and compact character distributions, savings, slack, exact
decode totals, direct evidence reproduction, links admitted, link characters,
unused slack, and complete evidence for every arm. Every gain must have missing
direct evidence in an admitted linked pair; any loss or non-link-carried gain is
a stop.

Compare `BENEFIT_MODEL` with both controls by exact item discordance overall and
per conversation. Report gain depth, score/rank distributions, distinct linked
pairs, and capacity-use distributions. Do not tune or select an arm.

Report `RANKED_COMPACT_SIGNAL` descriptively only if Part A passes, the benefit
arm has at least one gain and zero losses versus direct, all six conversations
are nonnegative, and it has more complete items than both controls. Otherwise
report `NO_RANKED_COMPACT_SIGNAL`. This is not an adoption bar.

## 5. Preflight Part 1 - Exploration

**Behavioral identity.** Compression changes only repeated speaker labels. It
is exactly reversible and cannot change direct selection or evidence identity.
Links consume measured slack after direct protection; they cannot displace it.

**Name-to-behavior.** Tests must establish deterministic first-occurrence codes,
multi-speaker and repeated-speaker decoding, exact punctuation/Unicode text,
independent pair charging, incremental dictionary cost, duplicate-neighbor
rejection, skip-on-overflow continuation, stable ties, and total budget.

**Distribution.** Before evidence analysis report savings/slack by conversation,
zero/negative savings, candidate edge counts, duplicate neighbors, fit skips,
admissions, and all conversation coverage for each ordering.

The primary surrogate risk is that byte-reversible availability does not prove
a reader interprets numeric speaker codes. A second is that DA-004's model is
cross-conversation evaluated but was developed on this spent corpus.

## 6. Preflight Part 2 - Checklist

- **PF1 Inputs:** verify DA-004 blind/label seals, DA-002 provenance, 26,100
  blind edges, 25,941 primary edges, 1,098 primary questions, six conversations,
  and direct 935 complete.
- **PF2 Identity:** pass every renderer, decoder, allocator, and degenerate test
  in Section 5.
- **PF3 Ordering:** commit protocol before implementation; commit blind compact
  rows before evidence access; Part B cannot run unless Part A passes.
- **PF4 Reachability:** require positive median savings, positive slack, eligible
  non-direct neighbors, admissions, overflow skips, and differing arm orders.
- **PF5 Keys:** preserve question, seed, neighbor, pair, dialogue, and selected
  direct keys; reject duplicates or missing mappings.
- **PF6 Reproduction:** require exact direct digests, byte decode, 935 complete,
  and DA-004's 57 benefits, 40 harms, and 25,844 neutral edges.
- **PF7 Absorbing state:** not applicable; require byte-identical blind replay
  and deterministic grouped scores.
- **PF8 Length:** use every primary question and edge; no fresh transfer claim.
- **PF9 Surrogate audit:** reversible text availability is not reader use;
  grouped reuse on spent data is not independent ranking validation.
- **PF10 Live boundary:** adoption requires a fresh corpus, reader validation,
  locked renderer syntax, latency measurement, and prospective criteria.

## 7. Stops and Outputs

Stop on hash mismatch, decode drift, expansion, direct identity drift, budget
overflow, Part A failure, nondeterminism, population mismatch, direct-total
mismatch, any loss, or causal-accounting failure. Commit blind compact rows
before importing evidence. Commit result and report only after all gates pass.

