# CC-007 — episodic-chat CC80 + static ASPECT read-path adoption

**Type:** engineering specification and benchmark-component adoption  
**Status:** pre-registered; implementation not yet present  
**Date:** 2026-08-24  
**Authorization:** user explicitly authorized the deployed architecture and
required an independent 1:1 port verification  
**Part 1:** `CC_007_PART1_EXPLORATION.md` at commit `ad650881`

## 1. Objective and claim boundary

Replace the deployable store's N-first cosine-threshold/A3 read path with one
composed context pipeline:

1. always render the latest 32 completed user/assistant episodes for chat
   continuity;
2. independently retrieve long-term episodes with frozen CC80 under a default
   32,000-character long-term budget;
3. exclude recent identities from long-term admission so no episode renders
   twice; and
4. provide frozen static ASPECT as an optional protected-spread mode, disabled
   by default.

The adoption makes no new accuracy, reader-use, transfer, concurrency,
throughput, or optimality claim. CC80 and ASPECT were measured only for offline
evidence availability on reused LoCoMo development conversations. The user is
selecting a product architecture with ASPECT explicitly experimental/off by
default, not reinterpreting TC-011's `NO_CANDIDATE` disposition.

The read path is the single component changed by this engineering adoption.
The distribution rename is release metadata; storage, embedding, rendering,
append durability, checkpointing, retention and vector-cache behavior are
carried unchanged.

## 2. Frozen package and public API

- Distribution name: `episodic-chat`.
- Python import namespace: `episodic`, retained for source/store compatibility.
- Version: `0.2.0`.
- `EpisodeStore.context(query, budget=None)` remains pure and byte-deterministic.
  `budget` is now the long-term retrieval budget. `None` uses 32,000.
- `EpisodicConfig` defaults:
  - `recency_window_n=32`
  - `retrieval_budget_chars=32_000`
  - `semantic_dense_weight=0.8`
  - `aspect_enabled=False`
  - `aspect_share=0.5`
  - `aspect_model="en_core_web_sm"`
  - BM25 `k1=1.2`, `b=0.75`
- Existing explicit integer budgets remain valid overrides, including zero.
- Existing pre-CC-007 configuration fields remain only for the frozen private
  `build_context` replay path until historical harness consumers migrate. They
  do not alter the new `EpisodeStore.context` pipeline.

The spaCy runtime and exact `en_core_web_sm` 3.8.0 model are optional install
dependencies because ASPECT defaults off. Enabling ASPECT without them fails
loudly with an actionable package-extra message; it never silently falls back.

## 3. Frozen CC80

For every stored episode, searchable text is exactly
`user_message + "\n" + assistant_message`. Query embedding and stored episode
embeddings use the carried solo-call float32 contract.

Compute dense cosine and BM25 over the complete store. Independently min-max
normalize each score family per query and calculate

`score_i = 0.8 * dense_normalized_i + 0.2 * bm25_normalized_i`.

Rank descending by score, then ascending `turn_number`, then stable episode id.
Recent episodes participate in score normalization so the complete-store CC80
order remains the studied mechanism, but their identities are skipped during
long-term admission. The walk continues after every recent or oversized item.

If a component range is exactly zero, its normalized contribution is the
all-zero vector. This production-only total-function rule is outside the
nondegenerate parity population. Empty stores return the empty two-block
payload without error.

## 4. Additive recency and exact accounting

Let `R` be the final `min(32,N)` episodes in conversation order and `B` the
long-term retrieval budget. Long-term candidates are packed and measured as
`render_stm_payload([], L)`, whose exact length must not exceed `B`. The final
returned block is `render_stm_payload(R, L)`. Consequently:

- every episode in `R` is rendered even when the final block exceeds `B`;
- `R` is not truncated, charged, or counted against `B`;
- `R` and `L` are identity-disjoint and the final block has no duplicate id;
- `ContextReport.chars_delivered` is total returned characters;
- `retrieval_chars_delivered <= retrieval_budget_chars` is the hard retrieval
  ceiling; and
- `chars_available` is computed against retrieval characters, not total output.

`budget=0` therefore returns the complete recent block and no long-term
episodes. A store of at most 32 episodes likewise returns all episodes as recent
and no long-term duplicate.

## 5. Frozen optional static ASPECT

When disabled, CC80 receives all `B` characters. When enabled:

1. CC80 admits complete nonrecent episodes under solo allowance `H=B/2`.
2. Parse complete candidate text once per construction using
   `en_core_web_sm` 3.8.0 and TC-011's exact six facet families: entity/date,
   number, noun chunk, verb event, and registered dependency relation.
3. Compute conversation-store facet IDF as
   `log((N+1)/(df+1))+1` and initialize coverage from the CC80 seed.
4. Excluding both recent and seed identities, greedily admit feasible episodes
   maximizing TC-011's CC80-weighted facet marginal per exact additive
   character cost. Ties and stopping behavior are byte-for-byte ports of the
   source implementation.
5. Pack the ASPECT order under solo allowance `H`, merge CC80 then ASPECT once,
   and resume unchanged CC80 order into actual remaining capacity.

Thus 50/50 means two protected maximum solo allowances. Wrapper savings and
unused ASPECT space return only to CC80; final composition need not be 50/50.
No dynamic prompt, residual cue, A3, facility, chain, coefficient sweep, facet
weight, threshold, truncation, or alternate parser is permitted.

If no semantic seed fits, ASPECT is inactive and the full-budget CC80 route is
used. This makes tiny budgets total without inventing an untested spread seed.

## 6. Context report contract

Retain existing fields for compatibility and add explicit attribution:
`retrieval_chars_delivered`, `retrieval_budget_chars`, `recency_count`,
`semantic_count`, `aspect_count`, `returned_semantic_count`, `aspect_enabled`,
and `recent_ids`. Historical `stm_count`, `k_count`, and `coverage_count` map to
recency, all semantic admissions, and ASPECT admissions on the new path.

Dropped identities report nonrecent long-term candidates that were not
admitted. Recent identities are never reported dropped. `truncated` describes
long-term shortfall only.

## 7. Preflight — binding before activation

- **PF1 Inputs:** hash and count the Part 1 file, TC-009 CC80 frozen selection,
  TC-011 frozen selection, dataset, blind vector cache, renderer, packer and
  source mechanisms. Require 871 question traces, 1,365 stable candidate
  identities and zero missing vectors.
- **PF2 Identity:** through package-only mechanism calls, reproduce the Part 1
  identity, score equations, facet families, stopping states and reported
  distributions. Explicitly prove default ASPECT is off and recency means the
  final 32 completed episodes.
- **PF3 Ordering:** the parity gate and package-separation tests run and their
  artifact is committed before `EpisodeStore.context` is switched. Activation
  refuses a missing or failed gate artifact in its acceptance test.
- **PF4 Reachability:** execute synthetic empty, singleton, constant-score,
  too-small-budget, no-positive-marginal, no-fit, full recent overlap and
  nonempty ASPECT cases. Both enabled and disabled branches must fire.
- **PF5 Keys:** compare and deduplicate only by stable episode/content identity;
  reject duplicate ids and prove generated timestamps and paths do not enter
  ordering.
- **PF6 Reproduction:** independently reproduce all 871 CC80 full-store orders
  and both 16k/32k selected identity sequences and payload SHA-256 values from
  TC-009, then reproduce both TC-011 static-ASPECT selected identity sequences
  and payload SHA-256 values. Exact expected total: 4,355 order/selection/payload
  trace groups, with zero mismatches. The verification code may import source
  adapters to read frozen inputs but the mechanism under test must import only
  the installable package.
- **PF7 Absorbing state:** on all ASPECT parity traces prove no repeated
  admission, admission-only state updates, monotone facet maxima, nonincreasing
  capacity and terminal no-fit/no-positive states. The pipeline has no
  cross-call feedback.
- **PF8 Length:** 871 queries over four conversations detect port drift across
  the full studied trace but cannot detect new-corpus transfer, live reader use,
  high-concurrency safety, or latency beyond the measured store sizes.
- **PF9 Surrogates:** byte parity can pass while the selected architecture is
  ineffective; dedup can pass while useful long-term capacity is wasted;
  character compliance can pass while total prompt is too large; availability
  can pass while a reader ignores evidence. These residuals are accepted and
  must remain documented.
- **PF10 Live requirement:** no live answer run is authorized or implied.
  Reader validation on an untouched external benchmark remains necessary for
  an effectiveness claim.

Preflight uses retained embeddings read-only. Under program convention those
are not counted as model calls. Cache misses, new embedding calls and LLM calls
must all be zero.

## 8. Acceptance and activation sequence

1. Implement package-private CC80, ASPECT and long-term allocation modules
   without changing `EpisodeStore.context`.
2. Add unit/adversarial tests and the independent parity verifier.
3. Run Preflight, commit its JSON artifact and exact mismatch counts.
4. Only after the passing artifact exists, activate the new store path, report
   contract, default configuration, metadata rename and documentation.
5. Run focused tests, clean-install import/metadata tests, full suite, leakage
   and import-graph checks, plus a two-process byte-determinism test.
6. Verify the worktree contains no generated cache/database residue, update the
   root deployed architecture and closeout records, then commit.

Any parity mismatch blocks activation. The source mechanism is authoritative;
the package port is repaired rather than the frozen artifact.
