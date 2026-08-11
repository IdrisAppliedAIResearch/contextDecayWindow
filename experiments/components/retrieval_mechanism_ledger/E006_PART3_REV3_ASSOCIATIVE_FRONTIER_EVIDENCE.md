# E006 Part 3 Rev 3 - Associative-Frontier Evidence Design

**Type:** Final offline evidence specification after mandatory exploration
**Date:** August 10, 2026
**Exploration commit:** `09631a0f`
**Exploration SHA-256:** `90E1054CB9AB2408317D8D4C2CC2742183C144DC190D2AD8BBAFE88B1F076EA3`
**Mechanism SHA-256:** `8BB02F16DD6D07CDA0D050289DAB6AB939E9CF7048D14564B8E71DFBD3347030`
**Status:** FINAL DESIGN - STANDALONE EVIDENCE AUTHORIZATION REQUIRED
**Outcome ceiling:** `CHARACTERIZED`

## 1. Exploration disposition

Preflight Part 1 passed without opening Q11 fact or domain labels. The graph has
119 nodes, 676 retained undirected edges, one connected component, and zero
isolates. Of 952 directed top-8 selections, 552 are reciprocal. Every registered
arm cell admits exactly `m * (D + 1)` unique candidates.

The blocking identity condition does not fire. On the same committed Tier 4A
`c121_l` graph and query, A2 differs from E3 PPR in recurrence, ranking digest,
candidate volume, and exact payload digest. A2 also differs from A1 on the real
Q11 trace. Tier 4A reproduces `144/144` rows and A1 reproduces `8/8` carried
cells before A2 exploration.

The required degenerate traces all execute. Empty, zero, and all-negative
adjacency reduce association to zero and preserve volume through Q. Seen
exclusion prevents repeated identities through a graph cycle. Constant scores
resolve by registered Q and content-hash ties. An exhausted unseen pool fails
before selection.

Candidate equality does not establish delivered-volume equality. At the primary
cell A0, A1, and A2 each admit 15 candidates, but select 11, 12, and 15 episodes
and deliver 31,957, 28,562, and 29,987 characters respectively. These are
label-blind packing facts, not availability outcomes.

## 2. Final mechanism and grid

No author-selected choice changes after exploration. The original protocol's
Section 3.2 remains authoritative:

- `K_GRAPH = 8`.
- Graph topology is the non-negative undirected union of directed top-8 exact
  cosine selections; duplicate union edges retain the larger weight.
- A2 association is the maximum retained edge from the immediately previous
  frontier.
- A2 score is `0.3 * Q + 0.7 * association`, with no additional normalization.
- A1 remains E006 Rev 5 with `W_Q = 0.3`, `RHO = 0.5`.
- No-edge association is zero, leaving every unseen node rankable through Q.
- Ties are descending arm score, descending Q, ascending content SHA-256.
- `D in {0,1,2,3}` and `m in {3,5}` produce exactly 24 arm cells.
- The primary cell is `D=2, m=5`.
- Native final arm score ranks each cumulative candidate set before the unchanged
  authoritative compact-XML packer applies the 32,000-character ceiling.

At `D=0`, all arms must remain identical by candidate, selected sequence, and
payload digest. Every later hop must add exactly `m` unseen identities. The
evidence implementation must reproduce every exploration candidate, selected,
and payload digest before measurement is imported.

## 3. Outcomes and disposition

Only after immutable identity reproduction passes may measurement read the
committed Q11 inventory. Every cell reports candidate and packed fact counts,
all four per-domain counts, exact candidate/selected/skipped characters and
episodes, three fact-efficiency diagnostics, candidate/selected/payload digests,
per-hop hashes/scores/source turns/predecessors, and pairwise arm overlap.

The primary thresholds remain unchanged:

**`CUE_DIFFERENTIATED`:** A2 has at least one more candidate-set fact than A0
and A1 and is no lower than either control in every domain.

**`DELIVERY_DIFFERENTIATED`:** A2 has at least one more packed fact than A0 and
A1, is no lower than either control in every domain, and delivers no more exact
characters than either control.

Disposition is ordered and mechanical:

| Primary result | Disposition |
|---|---|
| Candidate threshold fails | `NO_DIFFERENTIATED_CUE` |
| Candidate passes; packed gain absent | `REACH_ONLY_NOT_DELIVERED` |
| Packed facts improve but A2 delivers more characters than either control | `VOLUME_CONSISTENT_PACKED_GAIN` |
| Both thresholds pass | `DIFFERENTIATED_OFFLINE_DELIVERY` |

Secondary cells never rescue the primary disposition. Predictions 1-8 in the
exploration protocol remain registered and unchanged.

## 4. Remaining gate order

1. Commit this final design.
2. Record standalone author authorization against its commit and SHA-256.
3. Implement evidence reproduction, PF1-PF10, leakage checks, and measurement
   separation without opening outcomes.
4. Execute and commit the complete PF1-PF10 artifact. Any failure stops.
5. Commit a parameter lock that binds this design, authorization, mechanism,
   evidence source, exploration, reproduction, and passing Preflight hashes.
6. Run the complete 24-cell measurement once, commit all outputs, and report the
   primary disposition before inspecting secondary predictions.

## 5. Scope and interpretation

This remains one offline Q11 probe with no targeted cosine traces, live answer
generation, inference variance, deployment test, adoption, or promotion. Fact
availability is not answer correctness. E005's historical `12/17` is descriptive
and not an equal-volume control. Every possible result remains `CHARACTERIZED`.

Tier 4A already refuted advancement for global PPR traversal over observed
co-activation edges and an exact-cosine top-8 graph. This diagnostic does not
reopen that result. It tests a different propagation operator over the same
broad cosine-graph family, with a matched-volume fixed-query control and the
E006 exact packing path. Any result remains `CHARACTERIZED`.
