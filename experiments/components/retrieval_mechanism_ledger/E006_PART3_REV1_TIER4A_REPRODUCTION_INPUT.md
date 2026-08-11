# E006 Part 3 Rev 1 - Tier 4A Reproduction Input Repair

**Type:** Protocol revision for a structural Preflight blocker
**Date:** August 10, 2026
**Supersedes:** The call boundary and Tier 4A PF6 input assumptions in protocol
anchor `12f5a3f2`; every other registered choice remains unchanged
**Status:** PRE-REGISTERED - AUTHORIZATION MUST FOLLOW THIS REVISION ANCHOR
**Outcome access:** PROHIBITED until the repaired reproduction gate passes

## Trigger and evidence

Authorized Part 1 inspection found that Tier 4A did not persist its holdout
query vectors. The retained `c121_l` and `c1000_l` embedding caches contain
`0/24` exact locked holdout query texts each. Across every committed Tier 4A
retrieval row, selected-item diagnostics recover only `23-32/111` raw query
cosines per `c121_l` query and `106-165/986` per `c1000_l` query. No query has a
complete cosine vector.

Tier 4A E3 cannot therefore be mechanically re-executed from committed inputs
under the protocol's zero-embedding-call rule. Hashing or restating the prior
output would not reproduce the mechanism and cannot satisfy PF6. Weakening PF6
to artifact self-consistency is prohibited.

## Sole repair

Before any Q11 fact or domain measurement is opened, capture exactly the 48
locked Tier 4A holdout query embeddings: 24 for `c121_l` and 24 for `c1000_l`.
Use the carried Qwen3 embedding artifact with SHA-256
`06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439`,
`llama-cpp-python==0.3.25`, CPU execution, one thread, no speculative decoding,
and one solo embedding request per query in ascending `(corpus_id, query_id)`
order. Normalize each result and persist its exact float32 bytes.

The capture artifact must bind every vector to:

- corpus ID and query ID;
- SHA-256 of the exact UTF-8 query text;
- embedding-model SHA-256;
- vector dimension and byte SHA-256;
- source query-manifest path and SHA-256;
- launch command, Python and provider versions, PID, and thread settings.

The capture must reject a dirty worktree except for the unrelated pre-existing
`tmp/pr43_body.md`, reject an unexpected model hash or query count, and refuse
to overwrite an existing retained cache. After capture, all reproduction and
evidence code opens the cache read-only and fails on a miss. No span, episode,
Q11, targeted-probe, or newly authored query embedding is permitted.

## Repaired gate order

1. Commit this revision with no implementation files.
2. Record standalone author authorization against its commit and file SHA-256.
3. Implement and test the 48-vector capture plus read-only loader.
4. Run and commit the sealed vector cache and manifest.
5. Execute Tier 4A E3 from the original graph implementation and compare every
   one of its 144 E3 rows by selected identity sequence and rendered payload
   SHA-256 before any A2 output is opened.
6. Continue the original Part 1 exploration only if all 144 rows reproduce.

The 144 rows are 2 primary corpora by 24 queries by 3 registered depths. A
single identity or payload mismatch is a binding stop. The original Tier 4A
source, database episodes, graph construction, serializer, budget, and ranking
rules remain unchanged.

## Scope and exclusions

This revision authorizes exactly 48 embedding requests solely to reconstruct a
missing historical reproduction input. It changes no graph, arm, parameter,
threshold, prediction, comparison, interpretation ceiling, or Q11 mechanism.
It does not authorize model generation, live inference, targeted reconstruction,
fact measurement, tuning, adoption, promotion, or production changes.

The repaired cache removes the zero-embedding-call claim for the capture stage.
All subsequent E006-P3 stages must report zero additional embedding calls. This
repair makes PF6 executable; it does not make PF6 easier.
