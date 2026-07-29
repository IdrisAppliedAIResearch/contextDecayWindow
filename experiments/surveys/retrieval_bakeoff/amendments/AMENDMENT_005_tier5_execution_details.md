# Amendment 005: Tier 5 Execution Details

**Date:** 2026-07-28  
**Status:** Binding before Tier 5 implementation or registered execution  
**Applies to:** T5.0 through T5.4

## Trigger And Evidence

The locked protocol fixes Tier 5's budgets, HNSW parameters, scale ceiling,
recency fractions, and early-stop threshold, but leaves several choices that
materially affect recall or latency: the ANN query schedule and base corpus,
ranking and packing across progressive tiers, how an orthogonal topic tier is
selected, and how T5.4 operationalizes "matches or beats."

The registered topic validity check also has a surrogate defect. On the
Study 010 primary corpus, macro domain-to-topic purity is
`12835/13284` (about 0.966) even though all twelve registered domains have the
same dominant topic. The stated purity threshold can therefore pass while the
certified property, an age-independent domain axis, is false. This is the
recurring failure class identified in `AGENTS.md`, and it contradicts the
pre-registration's requirement to validate the known-collapsed topic layer.

The corrected Tier 2 table and committed Tier 4 result fix the policy choice:
M3 is advancing and has the highest eligible pooled macro recall, `67/96`.
No Tier 4 graph advances.

## T5.0 Fixed Policy

T5.0 and T5.2-T5.3 use M3, the registered raw-episode BM25 policy, without
retuning. T5.0 runs all 24 holdout queries on `c121_l` and `c1000_l` at exactly
32,000, 64,000, 160,000, and 320,000 serialized characters. Each query-budget
cell uses one warm-up and nine measured rank-plus-pack repetitions. The index is
built once per corpus. Packing is the already-locked exact serializer.

T5.1 remains the independent exact-cosine versus HNSW test required by the
protocol; selecting M3 for the retrieval-policy tests does not replace it.

## T5.1 ANN Corpus And Queries

The base vector store is `c1000_l`, ordered by turn and episode ID. Scale 120
uses its first 120 real vectors. Scale 1,000 uses all 986 real vectors plus 14
synthetic vectors. Scales 10,000 and 100,000 use all real vectors and synthetic
padding. Each scale starts an independent NumPy generator at seed 5005.
Synthetic vectors sample a real row with replacement, add float32 Gaussian
noise with standard deviation 0.01, and are renormalized. A row-provenance
artifact records scale, row index, real/synthetic status, and sampled source
index for every row.

The 24 `c1000_l` holdout queries are embedded once with the carried embedding
model before index-query timing. Recall@10 and recall@50 are macro-averaged over
all 24 queries against deterministic exact-cosine neighbors; exact ties resolve
by row index.

Both exact and HNSW query timing use the same locked schedule. The five warm-ups
are query indices 0-4. The 25 measured calls are indices 5-23 followed by 0-5.
Timing covers neighbor search only, uses `perf_counter_ns`, and reports the
median. HNSW uses `hnswlib==0.8.0`, the already-registered index parameters,
one thread, and row index as label. Build timing includes index initialization
and `add_items`, not vector generation. Saved index bytes, vector bytes, and
build time are reported.

## T5.2 Progressive Search

For `n` eligible episodes, `hot = floor(0.10n)`,
`warm = floor(0.30n)`, and cold receives all remaining episodes. Tiers are
newest hot, then next-newest warm, then cold. M3 ranks candidates within each
tier. Ranked tier lists are appended in search order and repacked from the
accumulated list with exact identity deduplication.

Each method/query gets one uncached carried-model query embedding for the
registered cosine stop condition. The best searched cosine is the maximum exact
cosine over every candidate searched so far. The base sequence is hot, warm,
cold. After hot and after warm, search stops only when the packed block is at
least 95% of 32,000 characters and best searched cosine is at least 0.50.

One complete progressive search is warmed up, followed by nine measured
repetitions. Query encoding plus median full rank-and-pack time is the reported
latency, matching the Tier 4 definition. Median incremental time and cumulative
characters after each tier are also reported. T5.2-T5.4 use only the
32,000-character budget.

## T5.3 Orthogonal Axes

The registered domains used for topic validation are:

- `c121_l`: `civil_engineering`, `renaissance_art`, `monetary_policy`,
  `marine_biology`.
- `c1000_l`: `structural`, `epidemiology`, `archives`, `battery`, `monetary`,
  `astronomy`, `ecology`, `cryptography`, `geophysics`, `linguistics`,
  `robotics`, `conservation`.

The Study 010 `probe` label is not a registered corpus domain and is reported
separately rather than entering validity.

The topic axis is valid only when all locked requirements hold and:

1. every registered domain has at least one non-empty stored topic;
2. macro domain-to-topic purity is at least 0.80; and
3. the dominant topic IDs are distinct across registered domains.

Count ties resolve by topic ID. The distinctness requirement repairs the
collapsed-topic surrogate and makes the gate stricter, never easier.
Topic-to-domain purity is reported as an additional diagnostic but is not a
substituted threshold.

For a valid topic axis, select one query topic by exact cosine between the query
embedding and stored topic centroids, with topic-ID tie-breaking. The
age-independent topic tier contains every raw episode assigned to that topic
and is ranked by M3.

The pinned-rule axis is valid only when at least one `rule_store` row references
an eligible raw source episode and its `rule_summary` occurs verbatim in that
episode's user message. Its tier contains the resolving source episodes,
ranked by M3.

The registered mitigation arms are base recency, recency plus topic, recency
plus pinned rules, and recency plus both valid axes. Invalid-axis arms are
reported `NOT_EVALUABLE`. For mitigation arms, search hot first, then pinned
rules when present, then topic when present; candidates already searched are
excluded. The first early-stop check occurs only after hot and all arm-required
orthogonal tiers have run, ensuring the mitigation cannot be bypassed by a
hot-tier stop. Warm and cold then follow the T5.2 rule.

## T5.4 Comparison

The fixed viable-core graph comparators, selected from the committed Tier 4
rows by exact pooled macro recall, then precision, latency, and method ID, are:

- depth 1: `G_E1_E3_d1`;
- depth 2: `G_E3_d2`;
- depth 3: `G_E3_d3`.

T5.4 compares each with every evaluable partition arm over the same 48 holdout
queries. It macro-averages query fact recall, latency under the common
definition, and old-but-required miss rate over applicable queries. A scheme
matches or beats another only when recall is no lower, latency is no higher,
and old-fact miss rate is no higher. Otherwise the result is a reported
tradeoff, not a discretionary winner.

## Exclusions

This amendment does not change a holdout, answer key, budget, HNSW parameter,
recency fraction, stop threshold, advancement result, or scale ceiling. It does
not rehabilitate T4B or permit an invalid topic/rule axis to be approximated.
Mechanism code remains barred from measurement artifacts.

## Authorization

The repository owner authorized end-to-end execution and amendments on
2026-07-28. This amendment fixes execution details before Tier 5 code or
registered results and tightens a gate that otherwise certifies a known-false
property.
