# Amendment 001 — Executable Offline Protocol

**Survey:** Retrieval Bakeoff
**Registration anchor:** `b60b7084741eb5d30298261076b4bca78abe713a`
**Registered holdout anchor:** `23b9bb99`
**Status:** BINDING BEFORE IMPLEMENTATION OR REGISTERED RETRIEVAL
**Scope:** T0 through T5 only

## 1. Trigger And Evidence

The locked pre-registration names method families, metrics, and advancement
thresholds, but several choices required for deterministic execution remain
unstated: the common comparison stores, exact serialization accounting, BM25
and RRF constants, span construction, graph propagation, the first T4B gate,
ANN settings, and progressive-search termination.

Those choices can materially change recall or latency. Leaving them to
implementation would create researcher degrees of freedom after the holdout was
visible. This amendment binds them before any harness code or registered result.

The preserved artifacts establish what can be carried rather than redesigned:

- Study 007 and Study 010 Arm L contain both raw episodes and distilled LTM.
- Study 009 Arm S and Study 010 Arm S contain raw episodes only.
- The historical Study 007 renderer and replay helpers can reproduce legacy
  blocks without changing the bakeoff serializer.
- Raw episode embeddings are stored as 1,024-dimensional float32 vectors.
- Raw sentence spans must be reconstructed from source text because
  `span_inventory` does not store embeddings.
- Study 010 has complete constructed prompts and per-turn N/K records, so E2
  co-retrieval edges are reconstructable without approximation.

## 2. Comparison Corpora

Candidate advancement uses two primary stores on which M1 and all raw-store
methods are available:

| Corpus ID | Read-only store | Eligible turns |
|---|---|---:|
| `c121_l` | `experiments/study_007/runs/study_007_full_001/condition_c/study.db` | 1–111 |
| `c1000_l` | `experiments/study_010/runs/study_010_full_001/arm_l/study.db` | 1–986 |

Two raw-only stores are robustness sidecars and cannot independently advance a
candidate because M1 is absent:

| Corpus ID | Read-only store | Eligible turns |
|---|---|---:|
| `c121_s` | `experiments/study_009/runs/study_009_full_001/arm_s/study.db` | 1–111 |
| `c1000_s` | `experiments/study_010/runs/study_010_full_001/arm_s/study.db` | 1–986 |

Study 005/006 stores may be used only for T0.3 fidelity and M5 provenance
checks. Every opened source tree is SHA-256 hashed before and after a run.

For advancement, per-query-class recall is computed separately on `c121_l` and
`c1000_l`, then averaged with equal corpus weight. A candidate advances when
the pooled values satisfy the locked Tier 2 threshold. Per-corpus values and
any direction reversal are always reported.

## 3. Representation, Serialization, And Budget

### 3.1 Text indexed

- Episode text is `user_message + "\n" + assistant_message`.
- Distilled ranking uses the stored distilled embedding. Under M1, records that
  resolve to the same source episode collapse to the highest-ranked record
  before packing, matching the carried architecture.
- Span text is every non-empty sentence span from the locked Study 006
  `span_segmenter`, with no salience or eligibility filter. This is a raw-store
  granularity comparison, not formation.
- All dense vectors are float32 and L2-normalized before similarity search.

### 3.2 Exact serialization

The bakeoff uses dedicated deterministic XML serializers:

- Episode elements include source episode ID, turn, stored topic ID/label,
  ground-truth-domain metadata when present, score, user text, and assistant
  text.
- Span elements include source episode ID, turn, role, character offsets,
  stored topic ID/label, score, and verbatim span text.
- XML text and attributes use the production escaping helpers.

`serialized_chars` is Python `len()` of the complete rendered retrieval block,
including the outer block tags, every element tag and attribute, indentation,
newlines, and escaped content. The 32,000-character budget is satisfied only
when `len(block) <= 32000`.

Candidates are greedily considered in deterministic rank order. A candidate
that does not fit is skipped and later smaller candidates may still enter.
Ties use stable candidate ID ascending. Duplicate rendered units are removed
before packing.

T0.3 alone uses the historical Study 007 serializer and selection accounting,
because its criterion is reproduction of the historical block to the
character. Legacy accounting never supplies a bakeoff metric.

## 4. Tier 2 Methods

All fixed methods use a 32,000-character budget and the same temporal cutoff.
No holdout parameter sweep is permitted.

### M1 — Current distilled baseline

- Dense cosine over all eligible distilled records.
- Collapse by source episode and render whole source episodes.
- Carry `k_min = 1` round-robin topic floor, then global similarity fill.
- Topic floor uses stored canonical topic ID and similarity ordering.

### M2 — Dense raw episodes

- Dense cosine over every eligible raw episode.
- Global similarity rank; no topic floor.

### M3 — BM25 raw episodes

- Unicode casefold followed by tokens matching
  `[^\W_]+(?:[-'][^\W_]+)*`.
- Robertson/Sparck Jones BM25 with `k1 = 1.2`, `b = 0.75`, and
  `idf = log(1 + (N - df + 0.5) / (df + 0.5))`.
- Global BM25 rank; no topic floor.

### M4 — Hybrid dense and sparse

- M2 dense rank plus M3 BM25 rank over the same raw episodes.
- Reciprocal-rank fusion score
  `1 / (60 + dense_rank) + 1 / (60 + bm25_rank)`, ranks one-based.
- Global fused rank; no topic floor.

### M5 — Granularity

- `M5_episode` is M2 and is not counted as a separate candidate.
- `M5_span` embeds every raw sentence span and ranks by dense cosine.
- Span embeddings are cached by embedding-model SHA-256 plus UTF-8 text
  SHA-256. Cache creation is mechanism-only and may not read a key.
- Each selected span renders independently with exact provenance.

### M6 — Enumeration multi-vector

- Non-enumeration queries use the unmodified M2 rank and are reported as such.
- Enumeration queries use the original query plus one expansion per canonical
  domain name present in the corpus's script metadata:
  `"<domain>: <original query>"`.
- Every expansion is embedded independently; full episode ranks are fused by
  one-based RRF with constant 60.
- Domain names come only from query-visible script/episode metadata, never from
  an answer key or required-fact list.

## 5. Metrics And Advancement

The evaluator, and only the evaluator, reads the measurement key.

- `fact_recall_at_budget`: unique required facts matched divided by required
  facts for the query.
- `domain_coverage`: required domains with at least one matched fact divided by
  required domains.
- `precision_proxy`: exact serialized characters belonging to elements that
  contain at least one required fact, divided by total serialized block
  characters. Wrapper characters are non-key-bearing.
- `delivered_characters`: exact complete block length.
- `index_build_ms`: one cold build per method/corpus.
- `query_encode_ms`: one uncached encode per dense query vector.
- `rank_pack_ms`: median of nine single-threaded repetitions using the encoded
  query, after one warm-up.
- `latency_ms`: `query_encode_ms + rank_pack_ms`.

Fact matching is case-insensitive and requires all terms for a fact within one
serialized element. Source provenance is checked independently; a term match
outside an eligible source episode is a test failure, not credit.

Class recall is the macro mean across queries, then the equal-weight mean across
the two primary corpora. “Beats” means a strict numerical increase. “Not more
than 10% below” means candidate recall is at least `0.90 * M1 recall`; when the
M1 value is zero, the non-regression condition is automatically satisfied and
does not itself constitute a win.

T1.2 uses the fixed raw-store configurations M2–M6 on the 121-turn Q11 query
against turns 1–111. No post-result configuration is added.

## 6. Tier 3 Rules

The oracle router chooses the highest-recall fixed Tier 2 method separately for
each true class, with ties broken by precision proxy, latency, then method ID.
The single-method comparator uses the same tie-breaks on overall macro recall.
Oracle gain is `(oracle_recall - single_recall) / single_recall`; if the
denominator is zero, gain is reported as undefined rather than infinite.

The feasible classifier is deterministic and reads query text only:

1. `enumeration` when the text contains `across`, `all`, or `list` and refers
   to at least three canonical domain names or an explicit number of subject
   areas;
2. otherwise `chained` when it contains `pair`, `connect`, `both`, or at least
   two canonical domain names;
3. otherwise `lookup`.

Query IDs and labels are forbidden classifier inputs. Accuracy and the complete
confusion matrix are reported.

## 7. Tier 4 Protocol

### 7.1 Associative edges

- E1: undirected edges between consecutive eligible turns, weight 1.
- E2: undirected co-retrieval edges between distinct raw source episodes that
  co-occur in one historical constructed memory context, weighted by the
  number of turns in which they co-occur. Only exact parsed episode/source IDs
  count.
- E3: undirected top-8 cosine-neighbor edges from exact raw embedding search;
  edge weight is `max(cosine, 0)`. Union asymmetric neighbor selections by
  retaining the larger weight.
- E4: undirected shared-stored-topic edges, reported alone and never merged
  into the viable E1–E3 core.

Registered combinations are E1, E2, E3, E1+E2, E1+E3, E2+E3,
E1+E2+E3, and E4.

Within each edge type, outgoing weights are row-normalized. Combined
transition matrices are the equal-weight mean of their component transitions.
The seed distribution is the normalized non-negative cosine score of the top
eight raw episodes; if all eight scores are non-positive, it is uniform.
Traversal uses truncated personalized PageRank:

`a_0 = seed`

`a_d = 0.15 * seed + 0.85 * P^T * a_(d-1)` for depths 1, 2, and 3.

Nodes rank by activation descending, then raw cosine descending, then episode
ID ascending. Packing uses the same exact raw-episode serializer and budget as
M2.

Per-episode update cost is measured single-threaded at both real corpus sizes
and at the Tier 5 synthetic scales. The empirical log-log slope of median
update time must be at most 1.10 to satisfy “not superlinear.” E2 context
updates and E3 neighbor updates are reported separately.

An old fact is one whose earliest source turn is in the oldest quartile of the
eligible corpus. Old-but-required miss rate is the fraction of such required
facts not delivered.

### 7.2 Extraction gate

If T4A fails its locked advancement rule, T4B is not run.

Otherwise, the T4B sample contains exactly 50 source-verbatim spans, covers
every corpus domain, and includes all six known-unreachable facts. The sample,
labels, and SHA-256 are committed before any extractor runs.

T4B.1 passes only when an extractor:

- detects all six known-unreachable facts,
- reaches node F1 at least 0.80, and
- reaches relation F1 at least 0.70.

Only passing extractors may enter traversal. The LLM extractor additionally
stops when more than 5% of extracted edges lack source-text support, exactly as
registered. Unsupported fraction uses all audited LLM edges as denominator.

## 8. Tier 5 Protocol

### 8.1 Fixed policy and budgets

T5 uses the advanced Tier 2/T4A method with highest pooled holdout macro recall;
ties use precision proxy, latency, then method ID. If no method advances, T5
uses the highest-recall method descriptively and labels it `non_advancing`.

T5.0 budgets are exactly 32,000, 64,000, 160,000, and 320,000 characters.

### 8.2 ANN

T5.1 uses HNSW (`hnswlib` 0.8.x), cosine space, dimension 1,024,
`M = 16`, `ef_construction = 200`, `ef_search = 64`, seed 5005, and one
thread. Primary recall is recall@10 against exact cosine; recall@50 is
secondary.

Scales are exactly 120, 1,000, 10,000, and 100,000 vectors. When padding is
required, vectors are sampled with replacement from normalized real vectors,
receive deterministic Gaussian noise with standard deviation 0.01, and are
renormalized. Every padded row and result is labelled synthetic. Index bytes on
disk, build time, and median of 25 query times after five warm-ups are reported.

### 8.3 Recency-partitioned search

Newest-first tiers contain 10%, the next 30%, and the oldest 60% of eligible
episodes, with deterministic boundary rounding that assigns any remainder to
the cold tier. Search proceeds hot, warm, cold. It terminates after a tier only
when the currently packed block uses at least 95% of budget and the best
searched cosine is at least 0.50. Otherwise the next tier is searched.

The topic axis is valid only when every ground-truth domain has a dominant
stored topic and macro domain-to-topic purity is at least 0.80. The pinned-rule
axis is valid only when at least one persisted rule resolves verbatim to a
source instruction. Invalid axes are reported `NOT_EVALUABLE` and are not
silently approximated.

T5.4 compares this partitioned policy with T4A depth 1–3 on the same query
rows, exact budgets, latency definition, and old-but-required metric.

## 9. Leakage And Determinism

Mechanism modules may read only query manifests, source databases/logs, and
mechanism configuration. They may not read files containing `answer_key`,
`overlap_matrix`, `rubric`, or `q_facts_key`.

The audit includes:

- static path/import scanning,
- an import-graph walk from every mechanism entry point,
- runtime file-open tracing during one query per method, and
- a planted module and file-access violation that must both be rejected.

All ordering is stable, all random operations use seed 5005, all benchmarks are
single-threaded unless a library cannot disable an internal thread (which is
then recorded), and all text I/O is explicit UTF-8.

## 10. Exclusions

- No registered threshold is weakened.
- No new retrieval candidate, policy level, or budget is added.
- Holdout artifacts remain unchanged.
- Historical run artifacts remain read-only.
- T6 live-run widening, launcher, scoring, and rater settings are not changed
  here. They require the separately registered settings artifact already
  mandated by the pre-registration.

## 11. Rationale

This amendment removes implementation discretion while preserving every
registered comparison and threshold. Carried behavior is used where the survey
calls for the current architecture; new constants are standard fixed defaults
or explicit deterministic choices applied equally across corpora. The stronger
serialization rule prevents a budget from passing while the actual rendered
context exceeds it.

## 12. Author Authorization

The repository owner authorized end-to-end execution and amendments in the
2026-07-28 instruction: “Follow it end to end. Amendments are allowed if
needed.”
