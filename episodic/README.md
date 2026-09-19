# episodic-chat

Append-only conversational memory with chronological retrieval. Store each
completed user/assistant exchange verbatim. At each query, retrieve every
exchange with raw cosine similarity >=0.48, add the latest 32 completed
exchanges for continuity, deduplicate, and present the union in source order.
There is no relevance item limit or character packing cap, and no generative
call inside retrieval. Query and source embeddings use an encoder.

## Use

Install this repository's package with `pip install ./episodic`. For the bundled
local GGUF embedding adapter, install `./episodic[llama]` and configure its model
path, or supply your own compatible `embedder`. Import the stable `episodic`
namespace:

```python
from episodic import EpisodeStore, EpisodicConfig

with EpisodeStore("memory.db", config=EpisodicConfig()) as store:
    store.append("user", "The delivery location is now the workshop.")
    store.append("assistant", "Understood.")
    block, report = store.context("Where is the delivery location?")
```

Continuity is on by default and can be switched off:

```python
config = EpisodicConfig(recency_window_n=0)
```

With continuity disabled, only qualifying relevant exchanges and any explicitly
protected anchor are delivered. Relevance does not certify that all necessary
evidence was found. The reader is supplied by your application.

## Explicit source boundaries

```python
block, report = store.context(
    "What had been recorded by the review?",
    through_turn=85,  # inclusive source-turn horizon, including continuity
    anchor_turn=85,   # protect this stored exchange even below the threshold
)
```

Both arguments are optional. The library never guesses an anchor from names or
natural-language dates. A horizon is when evidence was recorded, not the date of
an event described in it. Later retrospective testimony or clarification may be
necessary; omit the horizon when that material should remain eligible. An anchor
must name a stored complete exchange and cannot fall after the horizon.

## Reports and capacity

`report.selected_ids` lists the chronological union. `recency_count` counts the
continuity window; `semantic_count` counts relevant additions outside it. A
protected anchor can add another record. `eligible_count`, `through_turn`,
`anchor_turn`, `read_policy` and `relevance_threshold` describe the selection.
`chars_delivered` is the exact serialized output size.

The timeline's `budget_chars`, `retrieval_budget_chars` and `chars_available` are
`None`. Nothing is silently packed or dropped for size. `truncated=False` does
not mean the final reader prompt fits. The application must check its reader's
capacity; relevant evidence and stored history can grow without a bound. Source
order is append order, not an inferred ordering of real-world events.

The block preserves the existing XML envelope, with an empty `<recent_context/>`
and the complete chronological union in `<retrieved_stm>`. Continuity records
are interleaved by source turn instead of being duplicated in a separate tier.

## Existing stores and legacy behavior

The configuration is stored with the database. A different configuration fails
on open unless explicitly migrated with `override_config=True`. The migration
preserves source rows and embeddings and retains the embedding identity checks.
To retain version 0.2 behavior:

```python
config = EpisodicConfig(read_policy="legacy_cc80")
with EpisodeStore("old-memory.db", config=config) as store:
    block, report = store.context("Where is the delivery location?", 32_000)
```

Preserve any customized original fields too. Loading old serialized settings
through `EpisodicConfig.from_json()` selects the legacy policy automatically;
opening under the new default does not silently migrate an old store.

Legacy CC80 uses normalized 80% cosine + 20% BM25 with a character allowance;
continuity remains additive. Optional `aspect_enabled=True` requires the
`aspect` installation extra and the legacy policy. Timeline calls reject a
positional budget or enabled ASPECT. See [release and migration notes](CHANGELOG.md).

## Determinism and persistence

Selection is deterministic given identical source records, vector bytes,
configuration and explicit boundary. `context()` does not mutate the store or
call a generative model. It does embed the query, so encoder runtime and call
shape still matter. `EmbeddingCache` can retain exact float32 vectors:

```python
from episodic import EmbeddingCache

with EmbeddingCache(cache_path, mode="populate", embedder=embedder) as vectors:
    with EpisodeStore(store_path, config=config, embedder=vectors) as store:
        pass  # Append and context calls populate exact vector bytes.

with EmbeddingCache(
    cache_path, mode="reuse",
    expected_file_sha256=recorded_file_sha256,
    expected_content_sha256=recorded_content_sha256,
    expected_model_sha256=recorded_model_sha256,
) as vectors:
    with EpisodeStore(store_path, config=config, embedder=vectors) as store:
        pass  # A cache miss fails; no encoder call is possible.
```

The model-artifact/call-shape sentinel is checked when a store opens. A changed
sentinel is a hard failure. Cache identity requires both file and canonical
text-to-vector digests; it cannot recreate missing historical vectors.
Old EC-002 caches require explicit `legacy_v0=True` and their recorded hashes.

Appending an assistant reply commits the completed exchange with SQLite
`synchronous=FULL` and rollback journaling. Historical process-kill tests verify
acknowledged-turn persistence; they are not physical power-loss tests. Records
are never evicted automatically. Preserving source text prevents rewriting loss;
it does not guarantee that the source itself is true or that the reader answers
correctly.

## Evidence and limits

The repository's [adoption report](../experiments/components/episodic_chat/TIMELINE_REPORT.md)
links every artifact. The selector reproduces **2,306** historical selections and
payload checks with continuity disabled: 192 synthetic timelines, 128 explicit
prefixes and 1,986 LoCoMo selections with their retained source-adapter blocks.
This tests port identity, not benchmark accuracy of the installed package.

- A 12-question synthetic before-event probe improved **5/12 to 8/12** under
  chronological presentation without recency. It is small and exploratory.
- Uncapped relevance plus known anchors reached **106/128** before-event answers;
  restricting to the anchor prefix reached **126/128** across two diagnostic
  batches, with 22 gains and 2 losses. This is not a chronology-only effect.
- Natural LoCoMo timeline30 scored **13/20** broad and **5/10** additional temporal
  answers. Its automatic anchor grammar matched no questions; it does not
  establish general anchor resolution or a causal chronology gain.
- The later contextual/traversal experiment shared chronology across both arms.
  It remains experimental; its scores do not measure this library release.

Default last-32 continuity is retained by user direction. That composition has
not received a new live-reader evaluation. Historical 0.2 CC80/ASPECT benchmark
scores and latency do not transfer to this default. The .48 threshold is a
carried operating point tied to the encoder, not a universal relevance scale.
Full-store scanning and output size grow with history; no new latency, capacity,
or generalization claim is made here.

## Retention and historical measurement limits

The policy is **unbounded retention**; this version evicts nothing. The original
store measurement was 4,743 bytes per turn (4.8 MB at 1,000 turns). A 10,000-turn
estimate is an extrapolation, not a newly measured capacity horizon. The current
timeline output is also uncapped and has no established latency horizon.
Historical retrieval latency horizons were projections from the fitted exponent, not measurements;
they described the old cluster-A3 selector, not the timeline or legacy CC80.

DR-002 found that removing 19 low-cosine episodes from a 119-episode pool cost a
whole domain even though 4 of the 5 oracle episodes remained. The historical
`unsafe_cosine_top_n` field applies only to that private cluster builder. The
current timeline scans the full eligible store before applying its threshold;
it performs no approximate pool trimming or clustering.

### Two numbers this table used to get wrong

These are historical pre-0.2 corrections for the removed A3 path. Both were
caught by the program's own gates and remain here because they explain why these historical measurements cannot certify the current timeline.

**A confidence interval was read as evidence of boundedness.** DX-002 asked
whether Study 010's context was still growing at turn 1,000. Its first
decision rule asked only whether the terminal slope's 95% interval
contained zero. It does — for every part of the prompt, in both arms — and
the diagnostic returned "bounded". The interval was measuring statistical
power, not flatness: these series are sawtooths, and the smallest slope the
data could resolve was about 17 characters per turn, or 17,000 per 1,000
turns. Underneath that threshold sat a block whose 95th percentile had
risen 23,238 characters and which was still setting records in the final
bucket of the run.

The verdict now rests on two readings that assume nothing about noise —
whether the last bucket still holds the maximum, and how the terminal
window compares against the one before it — with the fit kept only as
corroboration. That old delivered-block claim does not include CC-007's
additive recency composition.

**A scaling range was quoted eight times wider than it was measured.** This
README cited DR-002 for "35–43 µs per candidate over 20–3,000 candidates".
DR-002's committed sweep is six rows covering 20–119; the 3,000 was a
cumulative *character* count from a different table in the same report.
Per-candidate cost is flat across the range DR-002 actually measured and
rises steadily above it, so projecting from 119 understates the cost at
1,000 candidates by about fivefold — 190 ms measured against ~40 ms
projected. See `ERRATA.md`.

The general form of the second one is worth stating plainly, because it is
the more likely of the two to bite a reader of this file: **before relying
on any scaling number here, check the range it was measured over.**
Anything beyond that range is a projection, and this document labels it as
one.

## Licence

Dual licensed: AGPL-3.0-or-later (see [LICENSE](LICENSE)) or a commercial licence
from Idris Applied AI Research. See the repository's `LICENSING.md`.
