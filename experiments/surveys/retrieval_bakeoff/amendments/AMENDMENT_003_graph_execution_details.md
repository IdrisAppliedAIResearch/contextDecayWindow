# Amendment 003 - Graph Execution Details

**Survey:** Retrieval Bakeoff
**Registration anchor:** `b60b7084741eb5d30298261076b4bca78abe713a`
**Executable protocol anchor:** `d6d80fbb`
**Corrected T1-T3 evidence anchor:** `f3e9735b`
**Status:** BINDING BEFORE TIER 4 IMPLEMENTATION
**Scope:** T4A execution details only

## 1. Trigger

The locked protocol fixes graph edge semantics, propagation, depths, metrics,
and advancement, but it does not fix four implementation details that can
change results or the update-cost slope:

- which historical constructed contexts may create E2 edges;
- how shared-topic E4 edges are expanded;
- how one incremental update is benchmarked at synthetic scales;
- how the oldest quartile and graph advancement baseline are operationalized.

These choices are fixed here before graph code or graph retrieval runs.

## 2. Nodes And Historical Contexts

One graph node is one temporally eligible raw source episode. Node order is
`turn_number` ascending, then episode ID ascending.

E2 parses only committed constructed prompts whose own turn is within the
corpus cutoff: turns 1-111 for `c121_l` and 1-986 for `c1000_l`. Later prompts
are excluded because their retrieval contexts depend on terminal probes.

Within each eligible prompt, exact XML elements under `recent_context`,
`retrieved_stm`, and `retrieved_ltm` are parsed. Episode `turn` and span
`source_turn` attributes resolve to raw source episode IDs through the database.
Malformed, missing, or ambiguous turn references fail the build. Duplicate
references collapse within one prompt. Every unordered pair in the resulting
set receives one co-retrieval count for that prompt. No absent context is
inferred from neighboring logs.

E4 is the complete undirected unit-weight graph within each non-empty stored
canonical `topic_id`. Empty-topic nodes remain isolated. E4 is never combined
with E1-E3 and remains unreliable/descriptive as registered.

## 3. Retrieval And Timing

T4A runs the eight registered edge configurations at depths 1, 2, and 3 on
`c121_l` and `c1000_l`, all 24 holdout queries, with the same exact 32,000
character serializer and nine measured rank-plus-pack repetitions after one
warm-up. Query encoding is one uncached, single-threaded carried-model call per
configuration/depth/query.

The flat advancement baseline is M1 from the corrected Tier 2 table. Only
E1-E3 configurations can advance; E4 is reported but cannot open T4B. Exact
fraction arithmetic from Amendment 002 governs recall comparisons.

## 4. Incremental Update Benchmark

Scales are 120, 1,000, 10,000, and 100,000 nodes. Synthetic vectors use the
registered Tier 5 padding rule: seed 5005, sampling normalized real vectors
with replacement, Gaussian noise standard deviation 0.01, then
renormalization. Topic IDs are sampled with replacement from real non-empty
topic IDs. Synthetic labels are explicit.

At each scale, run five warm-ups followed by 25 measured single-threaded
updates and report the median:

- E1: add the one adjacency edge from the new node to the previous node.
- E2: add one ten-node context consisting of the new node and nine
  seed-selected existing nodes; increment all 45 unordered pair counters.
- E3: score the new vector against all existing vectors by exact cosine,
  select its top eight neighbors, and test/update the new similarity against
  each existing node's retained eighth-neighbor threshold.
- E4: connect the new node to every existing node with its sampled topic ID.

Vector generation, allocation of the base store, and garbage collection are
outside measured regions. Update data structures are preallocated where the
library permits. Timing uses `perf_counter_ns`.

The empirical slope is ordinary least squares over
`log10(scale), log10(median_ns)`. A component satisfies the update-cost
criterion at slope at most 1.10. A combination inherits the maximum slope of
its components. E1 timing is reported even when timer resolution dominates.

Real-corpus incremental costs are also reported by replaying each component's
actual eligible node/context sequence once and taking the median per-update
time. Synthetic slopes, not two-point real-corpus slopes, govern the
superlinearity criterion.

## 5. Old-But-Required

Sort eligible source turns. The oldest quartile is the first
`ceil(node_count / 4)` turns. A required fact is old when its earliest locked
source turn is at or before that boundary. Miss rate is unmatched old required
facts divided by old required facts, macro-averaged over queries with at least
one old required fact. Queries with no old required fact are reported
`NOT_APPLICABLE` and excluded from that macro mean.

## 6. Exclusions

- No graph edge, depth, propagation constant, budget, query, or threshold
  changes.
- No answer key enters graph construction, routing, seeding, ranking, or
  packing.
- No terminal prompt contributes structure.
- No approximate search is introduced in T4A.
- The original and corrected T1-T3 artifacts remain unchanged.

## 7. Authorization

The repository owner authorized end-to-end execution and amendments in the
2026-07-28 instruction: "Follow it end to end. Amendments are allowed if
needed."
