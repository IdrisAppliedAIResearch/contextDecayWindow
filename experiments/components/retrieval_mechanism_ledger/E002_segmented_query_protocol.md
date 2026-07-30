# E002 Segmented Query Retrieval Protocol

**Status:** COMPLETE - KILL (best 10/17; targeted 14/16)
**Type:** Offline component test, not a study or pre-registration
**Parent:** `RETRIEVAL_MECHANISM_LEDGER.md`, E002
**Inference calls:** 0

## Purpose

Test whether mechanical query segmentation can improve breadth-fact availability
without degrading the targeted retrieval behavior already observed in the
corrected Tier 6 artifact. Passing this test authorizes a promotion decision in
the living ledger; it does not authorize a live run or a new study.

## Preflight Disclosure

The supplied ledger calls 13/17 the baseline while also imposing a 32,000
character budget. The 13/17 figure comes from the corrected Tier 6 run at its
locked 60,595-character payload budget. During protocol preparation, before this
file was committed, a manual compact-renderer replay indicated that the current
selector is materially lower at 32,000 characters. That observation is
contaminated preflight information and is not an E002 result.

The executable analysis must report both:

1. the committed historical hurdle, 13/17 at 60,595 characters; and
2. a reproduced same-budget baseline using the unchanged selector and compact
   production renderer at 32,000 characters.

The E002 kill threshold remains the ledger's stricter historical hurdle: a
candidate must reach at least 14/17.

## Locked Inputs

- Corrected Tier 6 run:
  `experiments/surveys/retrieval_bakeoff/tier6/runs/tier6_live_121_corrected_001/context_matched_stm`
- Primary breadth probe: turn 120, Q11.
- Targeted no-regression probes: turns 112, 113, 115, 116, 117, 118, and 119.
- Store eligibility: raw episodes with `source_turn < probe_turn`.
- Candidate text: the stored raw episode embedding already present in the
  corrected run database.
- Query embeddings: the carried Qwen3-Embedding-0.6B Q8_0 artifact, SHA-256
  `06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439`.
- Similarity: carried cosine implementation.
- Rendering: post-DR-001 `render_episode_element`.
- Retrieval payload budget: exactly 32,000 Python characters after complete
  serialization.

The input database and all source logs are read-only and hashed before and after
execution. The run's mechanism seal must pass before analysis.

## Mechanical Segmentation Sweep

Tokenization is Unicode-aware whitespace tokenization: every maximal
non-whitespace run is one unit. Punctuation remains attached to its adjacent
unit; no linguistic model, entity recognizer, fact key, or rubric is consulted.

For the Q11 query with `L` units, sweep:

- segment width `S` over every integer in `[1, L]`;
- boundary offset `o` over every integer in `[0, S - 1]`;
- per-segment retrieval budget `b` over `{1, 2}`.

For a given `(S, o)`, retain every query unit exactly once. If `o > 0`, the first
segment contains the first `o` units. Remaining segments contain successive
groups of at most `S` units. Empty segments are never emitted. The same locked
`(S, o, b)` configuration is applied unchanged to every targeted probe; offsets
larger than a shorter query simply produce one segment containing the query.

This exhaustive finite sweep avoids selecting a favored segment width before the
test while exercising every boundary placement for every width.

## Retrieval And Packing

1. Embed each non-empty segment independently.
2. Rank every eligible raw episode by descending cosine. Break exact ties by
   ascending source turn, then episode ID.
3. Retain the top `b` rows per segment.
4. Merge in rank-round-robin order: every segment's rank-1 candidate in query
   order, then every segment's rank-2 candidate in query order.
5. Drop duplicate episode IDs on later occurrence. For whole raw episodes,
   containment identity is the source episode ID; no semantic or fact-aware
   deduplication is permitted.
6. Serialize candidates into the production `<retrieved_stm>` payload in merge
   order. If a candidate would exceed 32,000 characters, skip it and continue.
   Never truncate an episode and never stop merely because one candidate does
   not fit.

Round-robin order preserves the fixed per-segment allocation under overflow.
Skip-and-continue is the carried greedy packer's graceful-degradation behavior.

## Measurement Boundary

Mechanism code may read only the query text, eligible episode identities,
episode content, stored embeddings, budget, and configuration. It must reject
paths or imports containing `q_facts_key`, `rubric`, `ATOMIC_ITEMS`, or
`TARGETED_ITEMS`.

A separate analysis layer may read the committed measurement artifacts:

- `analysis_corrected_121/breadth_fact_delivery.csv`
- `analysis_corrected_121/targeted_fact_delivery.csv`

The mechanism must write selected IDs, source turns, domains, segment text,
local rank, cosine, dedup outcome, fit outcome, and exact serialized cost before
the analysis layer counts any fact.

## Baselines And Gates

**Historical hurdle:** 13/17 Q11 atomic items in the committed corrected run at
60,595 characters.

**Same-budget baseline:** unchanged corrected-run candidate ordering, repacked
with the compact renderer at 32,000 characters. Report only; it does not lower
the historical hurdle.

**Primary pass:** at least one E002 configuration makes at least 14/17 Q11
atomic items available at 32,000 characters.

**No-regression pass:** the same configuration preserves every targeted item
whose committed corrected-T6 availability is `True`. Previously unavailable
items may improve and do not count against the gate.

**Surrogate pass:** the primary configuration must cover all four domains and
the report must expose every segment-to-episode mapping. Because the domain
sizes are 5/4/4/4, 14/17 mathematically implies four-domain coverage; the
explicit check guards the implementation.

**E002 outcome:**

- `KILL` if no configuration reaches 14/17.
- `REJECT_NO_REGRESSION` if one reaches 14/17 but none also passes the targeted
  no-regression gate.
- `PROMOTION_ELIGIBLE` if one configuration passes all three gates.

Promotion remains blocked until the ledger's diversity-aware selection scan is
complete.

## Selection And Tie-Breaks

Among configurations passing all gates, choose the primary configuration by:

1. highest Q11 atomic availability;
2. highest number of committed targeted items preserved;
3. highest Q4 identity-item availability;
4. fewest serialized characters;
5. fewest selected episodes;
6. lower `b`;
7. larger `S`;
8. lower `o`.

If no configuration passes, apply the same ordering without the failed gate
fields to identify the descriptive best row. This tie-break is fixed before
segmented output.

## Required Artifacts

- input and output hash manifest;
- same-budget baseline report;
- full configuration sweep CSV;
- per-segment selection CSV;
- primary configuration payload and identity list;
- Q11 item and domain matrix;
- targeted no-regression matrix;
- deterministic rerun hashes;
- leakage audit with a planted forbidden-path failure;
- final E002 report and ledger disposition.

All artifacts are availability measurements. They make no answer-correctness
claim and authorize no inference run.
