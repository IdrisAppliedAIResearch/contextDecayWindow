# SUP-001 - Explicit Supersession Lineage

**Type:** Pre-registered offline component study with conditional 35-turn ablation
**Date:** August 11, 2026
**Branch:** `study/sup-001-explicit-supersession-lineage`
**Status:** PRE-REGISTERED - IMPLEMENTATION PROHIBITED BEFORE THIS COMMIT
**Authorization:** Program author approved the biological-memory research arc end to end on August 11, 2026
**Grounding:** `HYPOTHETICAL_001_MECHANICAL_BIOLOGICAL_MEMORY_MODEL.md` P5, P9, and F6
**Outcome ceiling:** `CHARACTERIZED`; no production adoption or full live run

## 1. Question and scope

The carried `episodic` store is verbatim, append-only, and has no current-value
state. Exploration wrote “My preferred tea is Earl Grey,” then an explicit
update to Sencha. Its natural context returned both values, old before new.

SUP-001 adds exactly one component: an **explicit supersession lineage
sidecar**. It asks:

> With stored text, embeddings, cosine scores, candidate pool, top-8 count,
> and 32,000-character ceiling fixed, can accessibility gating make the
> current value naturally reachable, preserve unchanged retrieval, and keep
> every prior value recoverable through an explicit lineage query?

Explicit update metadata supplies `memory_key` and `supersedes`. Contradiction
detection is excluded. The study does not infer updates from text, rewrite or
delete episodes, add generated text, change embeddings, or modify `episodic`.

SAL-001 killed surprisal-driven P1-P4 capture. SUP-001 is independent: it tests
P5/P9 only and uses no surprisal, tags, temporal capture, or replay.

## 2. Component

The sidecar stores only stable content identities and lineage state:

```text
LineageRecord:
    episode_sha256 : str
    memory_key     : str
    version        : int
    supersedes     : episode_sha256 | None
    superseded_by  : episode_sha256 | None
    accessibility  : 0.0 | 1.0
```

`register_initial(key, episode_sha256)` creates version 1 at accessibility
1.0. `register_update(key, new_sha, supersedes_sha)` succeeds only when the old
record is the unique accessible leaf for that key. It atomically sets the old
leaf to 0.0, links both directions, and creates the new leaf at 1.0. Duplicate
content IDs, forks, cycles, unknown parents, cross-key links, and updates of a
non-leaf fail closed.

Natural retrieval receives the frozen `(episode_sha256, cosine)` population,
multiplies cosine by accessibility, excludes zero-accessibility rows, and
applies the original descending-cosine/content-hash tie break. It returns the
first eight rows under the same exact 32k packer. An unregistered episode has
accessibility 1.0. No query changes state.

`lineage(key)` bypasses accessibility deliberately and returns every version
oldest to newest with exact content hashes and links. This is the only path by
which a zero-accessibility episode may be returned.

`accessibility=0` means naturally unreachable, not deleted. Stored text,
embedding bytes, source order, and episode count must remain unchanged.

## 3. Fixed benchmark

The benchmark is generated mechanically from templates committed with the
implementation, using seed 5005 only for deterministic ordering; no randomness
is drawn.

- 64 updated keys: 16 each in preference, location, schedule, and quantity.
- Every updated key has exactly three natural-language versions: initial,
  update 1, update 2. The two update calls explicitly name the prior content
  hash in sidecar metadata; the visible text contains a natural update phrase
  but the component may not parse it.
- 32 unchanged keys: eight per domain, one version each.
- 32 unrelated distractor episodes.
- Total stored episodes: 256, all unique by canonical content SHA-256.
- 96 natural queries: one current-value query per updated or unchanged key.
- 64 deliberate lineage queries: one per updated key.

Values come from fixed ASCII lists in the implementation specification. A key
and all three of its values occur in text; no value is shared across keys.
Queries mention the subject but not any old or current value. Templates rotate
by key index, not outcome. The complete generated corpus and query manifest are
committed before embeddings or labels are measured, and a second process must
reproduce their canonical digest.

Use the carried Qwen3-Embedding-0.6B Q8_0 GGUF, SHA-256
`06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439`,
one text per call. Persist exact float32 vectors in a read-only cache bound by
model SHA and canonical text-to-vector SHA-256. No embedding parameter or
template is swept.

Each natural query ranks all 256 episodes by cosine. C0 ignores the sidecar.
T1 applies the registered accessibility gate, then the same ranking, top-8
count, renderer, skip-overflow policy, and 32,000-character ceiling. Both arms
must return eight episodes and fit the ceiling or the study stops. This ceiling
is expected to be slack and is retained to prevent a new accounting regime.

## 4. Arms and measurements

### C0 - append-only control

Use the frozen corpus, embeddings, query vectors, and cosine ranking without
lineage or accessibility. C0 must reproduce an independently committed
ranking/payload artifact before T1 outcomes open.

### T1 - explicit supersession lineage

Use the same population and cosine values. The only ranking change is
`cosine * accessibility`, with zero rows excluded and lower-ranked accessible
rows backfilling to eight. The same packer and renderer run unchanged.

For each natural query report current version present, every stale version
present, current-only success, selected identities/ranks, exact characters,
and payload hash. For unchanged queries report target presence and rank. For
each deliberate history query report the exact three-version ordered lineage,
links, accessibility values, and content-hash round trips.

## 5. Part 1 exploration and Preflight

The companion exploration record must reproduce before outcome work. Its
falsifiable identities are:

- `episodic.context()` is append-only and returns old and new update text with
  no lineage or current marker on the demonstrated trace.
- LongMemEval's `knowledge-update` class cannot supply lineage ground truth:
  it mixes replacement and accumulation and annotates evidence sessions, not
  old-to-new edges.
- The sidecar is stateful only on explicit registration. Natural and lineage
  reads are pure and cannot create an absorbing query-history state.

After implementation, Part 1 runs every state transition and failure mode on
real generated traces, records accessibility/edge distributions after each
update, demonstrates no forks/cycles, and repeats the complete 256-episode
construction in a fresh process.

PF1-PF10 then execute before labels or current/stale values open:

| Check | Required evidence |
|---|---|
| PF1 | Hash and count the reference, carried package/source, model, corpus, manifests, vectors, and scripts |
| PF2 | Execute register, update, natural gate, lineage bypass, immutability, and pure reads against their names |
| PF3 | Git ancestry and sentinels prove design, implementation, corpus lock, C0 reproduction, Part 1, and PF1-PF10 precede measurement |
| PF4 | Synthetic fixtures reach every gate/disposition; all 96 targets exist and all 64 lineages have three versions before lock |
| PF5 | Content SHA-256 and memory key compare records; no generated IDs, paths, or timestamps |
| PF6 | C0 reproduces every frozen top-8 identity, cosine, payload, character count, and digest before T1 opens |
| PF7 | Repeated natural/history reads are identity-equal and leave the ledger/store hashes unchanged; explicit updates terminate in one leaf |
| PF8 | The 96-query offline test detects selection/provenance behavior; a 35-turn ablation tests integration but not long-run or inferred contradictions |
| PF9 | Audit current-only availability, unchanged recall, lineage recovery, no deletion, and payload fit against false certification |
| PF10 | Availability is not answer correctness; passing offline gates permits only the registered 35-turn ablation |

Every check cites a committed executed artifact. Prose assertions fail.

## 6. Binding gates

Stop at the first failed gate.

| Gate | Bar | Failure disposition |
|---|---|---|
| G1 integrity | Part 1 and PF1-PF10 pass; C0 exact; store, vectors, ranks, count, budget, and source identities match | `INTEGRITY_STOP` |
| G2 current-value retrieval | T1 is current-only on all 64 updated queries, and improves current-only count over C0 by at least 16/64 | `CURRENT_VALUE_NOT_SURFACED` |
| G3 unchanged safety | T1 loses zero target facts across 32 unchanged queries relative to C0 | `UNCHANGED_FACT_REGRESSION` |
| G4 history recovery | All 64 deliberate lineage queries return exactly three immutable versions oldest-to-newest; natural queries return zero stale versions | `LINEAGE_OR_SILENCE_FAILURE` |
| G5 provenance | Store count remains 256; all text/vector hashes are unchanged; links are reciprocal, acyclic, same-key, and have exactly one accessible leaf | `PROVENANCE_OR_INVARIANT_FAILURE` |

If G1-G5 pass, disposition is `SUPERSESSION_OFFLINE_ELIGIBLE`. This authorizes
only Section 7. It is not production or live evidence.

## 7. Conditional 35-turn ablation

Only after G1-G5 pass, commit a run lock and execute separate clean control and
treatment worktrees. The scripted conversation contains four explicit keys,
two updates per key, four unchanged facts, natural current queries, and one
deliberate history query, all planted before probes. Use the fixed Qwen reader,
seed 5005, `--parallel 1`, no speculative decoding, exact 32k ceiling, source
SHA assertion after decoding, and a byte-identical prefix rerun.

The ablation passes only if T1 answers every current and unchanged query from
delivered evidence without stale attribution, returns ordered history on the
deliberate query, preserves all store/lineage invariants, stays in budget, and
has zero targeted regression versus C0. A pass is
`READY_FOR_SEPARATE_LIVE_DECISION`; it does not authorize a 120-turn run.

## 8. Surrogate audit and exclusions

Current-only payload can pass while a reader answers stale from priors; the
conditional ablation owns that gap. Explicit keys can pass while contradiction
detection fails; inference is deliberately excluded. Exact lineage recovery
can pass while natural retrieval misses the current value; G2 is separate.
Zero deletion can pass while old values leak naturally; G4 checks silence.
Aggregate safety can hide one damaged fact; G3 requires zero losses.

No salience, temporal capture, accessibility learning, retrieval-induced
suppression, consolidation, semantic gist, contradiction detector, overwrite,
deletion, generation during offline gates, production change, or full live run
is authorized.

