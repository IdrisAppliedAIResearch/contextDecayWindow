# episodic-chat

Append-only conversational memory for ongoing chat. Every completed
user/assistant exchange is stored verbatim. Each `context()` call always adds
the latest 32 exchanges for continuity, then independently fills a
32,000-character long-term block with CC80—a fixed 80% dense-cosine, 20% BM25
ranking. Static ASPECT can protect half of the long-term budget for structured
spread, but is installed separately and disabled by default.

Install the `episodic-chat` distribution and import its stable `episodic`
namespace:

```python
from episodic import (
    EmbeddingCache, EpisodeStore, ContextReport, EpisodicConfig
)

store = EpisodeStore(path, config=EpisodicConfig())
store.append(role, content)
block, report = store.context(query)  # default: additive last 32 + 32k CC80
store.close()
```

The optional integer argument overrides only long-term capacity:
`store.context(query, 16_000)`. Recent continuity is additive and therefore
the total returned block may exceed that number. The exact retrieval ceiling
is `report.retrieval_chars_delivered <= report.retrieval_budget_chars`.

Enable the registered static spread route explicitly:

```bash
pip install "episodic-chat[aspect]"
```

```python
config = EpisodicConfig(aspect_enabled=True)
```

ASPECT uses the tested 50/50 protected allocator: CC80 fills one solo half,
ASPECT fills the other without duplicating recent or semantic identities, the
phases merge once, and all unused capacity returns to unchanged CC80 order.

Runs that must be replayable at vector granularity wrap their embedder in a
persistent cache, record both digests, and reopen it read-only:

```python
with EmbeddingCache(cache_path, mode="populate", embedder=embedder) as vectors:
    store = EpisodeStore(store_path, config=config, embedder=vectors)
    # append and context calls populate exact float32 vector bytes

with EmbeddingCache(
    cache_path,
    mode="reuse",
    expected_file_sha256=recorded_file_sha256,
    expected_content_sha256=recorded_content_sha256,
    expected_model_sha256=recorded_model_sha256,
) as vectors:
    store = EpisodeStore(store_path, config=config, embedder=vectors)
    # every cache miss is fatal; no model call is possible
```

The content digest binds each complete UTF-8 text to its exact vector bytes;
the file digest binds the retained SQLite artifact. This guarantee applies
only to runs that retained such a cache. It cannot reconstruct historical
vectors that were never preserved.

The pre-contract EC-002 cache can be opened with `legacy_v0=True` only after
its already-recorded file SHA and a newly recorded canonical content SHA are
both supplied. This adopts retained bytes; it does not recreate a missing
historical cache.

`store.context()` is a pure function of store state, query, retrieval budget,
and config:
no mutation, no inference calls, no network. Same inputs, same output,
byte-identical. That property is what made the studies reproducible and
it is the library's core guarantee (acceptance test T7 asserts it across
two processes).

## Measured behavior

Every number below was measured in the source repository and traces to a
committed artifact. CC-007 independently checked the package port against
4,355 frozen order/selection/payload groups before activating it.

| Claim | Number | Source | Artifact SHA-256 |
|---|---|---|---|
| CC80 complete evidence | 771/819 at 16k/32k over 868 eligible LoCoMo questions | TC-011 full-CC80 control | `tc011/result/result.json` |
| Static ASPECT complete evidence | 749/810 at 16k/32k; ASPECT is therefore off by default | TC-011 | `tc011/result/result.json` |
| Static ASPECT composition | At 32k: 80–126 selected (median 100), 37–54 spread (median 46) | TC-011 Preflight | `tc011/preflight/preflight.json` |
| Port equivalence | 4,355/4,355 CC80 order/payload and static-ASPECT payload groups exact; 0 mismatches | CC-007 PF6 | `episodic_chat/artifacts/cc007/preflight.json` |
| Retrieval budget ceiling | Long-term serialized characters never exceed their explicit allowance; recent continuity is additive | CC-007 contract tests | `tests/test_cc007_mechanisms.py` |
| Extraction equivalence of carried primitives | 132/132 historical A3 payload SHAs and 3/3 renderer blocks byte-identical | CC-002 T3/T4 | `t3_e005_replay.json` `d8e08f94952e468d…`, `t4_render_replay.json` `43c938898a71fa06…` |
| Restart persistence | Turns acknowledged by `append()` survive `SIGKILL`; `context()` returns a byte-identical block across restart; 100 restart cycles with no drift | CC-004 P1–P6 | `CC_004_report.md` |

Artifacts live in the source repository under
`experiments/components/tier_cost/artifacts/`,
`experiments/components/episodic_chat/artifacts/`, and
`experiments/components/library_extraction/artifacts/cc002/`.

## Known limitations

| Limitation | Number | Source |
|---|---|---|
| Effectiveness evidence is development-only | CC80/ASPECT were selected and measured on the same four LoCoMo development conversations; no reader or enterprise transfer claim | TC-009–TC-012 |
| ASPECT loses to full CC80 | 810 vs 819 complete evidence at 32k; 749 vs 771 at 16k | TC-011 |
| Additive total size | The 32 latest exchanges are outside the retrieval budget, so `chars_delivered` can exceed 32,000 | CC-007 contract |
| Store growth | Unbounded retention by policy; see "Growth, and what it costs" below | CC-005 |
| Restart guarantees are tested against process kills, not power loss | P1/P3 kill a live process with no cleanup. Surviving a power cut or a lost storage connection rests on `synchronous=FULL` and SQLite's implementation, not on anything measured here | CC-004 |
| Parser dependency | ASPECT requires spaCy and exactly `en_core_web_sm` 3.8.0; missing dependencies fail rather than fall back | CC-007 |
| The ceiling is not a prompt ceiling | Recent context, preambles, tool schemas and caller content are outside long-term accounting | CC-007; DX-002 |

### Two numbers this table used to get wrong

These are historical pre-0.2 corrections for the removed A3 path. Both were
caught by the program's own gates and remain here because they explain why this
README does not project old scale or ceiling measurements onto CC80.

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

## Growth, and what it costs

**The policy is unbounded retention. This version evicts nothing.** That is
a decision, not an omission, and these are the numbers behind it.

Three things can grow as a conversation gets longer. The old A3 path was timed;
the new CC80/ASPECT path has not yet been re-benchmarked, so its latency is not
silently inferred from the old selector.

| Path | Grows with | Measured | Status |
|---|---|---|---|
| Long-term context | turn count | exact configured retrieval ceiling, default 32,000 chars | **Bounded.** Independent of store length |
| Recent continuity | content of latest 32 episodes | additive, no character ceiling | **Fixed count, variable size.** Total output can exceed 32k |
| Disk | turn count | 4,743 bytes per turn marginal; 4.8 MB at 1,000 turns | **Cheap.** ~48 MB at 10,000 turns, 86% of it embeddings |
| Retrieval latency | store size | CC80/ASPECT deployment path not re-benchmarked | **Unknown.** CC80 scans the full store; ASPECT additionally parses and scans facets |

The historical 190 ms at 1,000 candidates and its fitted projections belong to
the removed cluster-A3 read path. They do not certify this version. Deployments
with large stores should measure their own CC80 latency; enabling ASPECT is the
more expensive branch and is intentionally opt-in.
Those old horizon values were **projections from the fitted exponent, not measurements**.

Two earlier numbers are corrected here rather than quietly restated. DR-002
measured 20–119 candidates and found per-candidate cost flat at 35–43 µs
with exponent 0.96; that holds inside its range and does not extend past
it. A linear projection from 119 understates the cost at 1,000 candidates
by about five times. See `ERRATA.md`.

### Trimming the candidate pool is not the answer

The obvious fix—drop low-similarity episodes so the pool stays small—is one
operation already measured to break the former selector. Dropping the 19
lowest-cosine episodes from a 119-episode pool cost an entire domain and
all known-optimum overlap, **despite 4 of the 5 optimum episodes surviving
the cut**. The selector clusters over the pool, so removing the tail
reshuffles the objective rather than removing options (DR-002).

CC80 therefore ranks the complete store. The retained
`unsafe_cosine_top_n` field is historical compatibility for the private old
builder and does not trim the deployed CC80 path. Any future index or eviction
policy has to be evaluated as a new component.

If you need a horizon, prefer archival with an explicit, caller-visible
cutoff — the caller should know the memory has a horizon — over silent
trimming.

## What was removed and why

Each mechanism below was measured and closed in the source repository's
ledger; the numbers live there, not here.

- Dreaming/distillation — salience selected verbosity, not value (Study 005).
- Promotion filters — behaved as a novelty-spike detector (Study 003).
- TopicManager — 52 topics for one conversation; failed again at scale (Studies 002, 010).
- Rule detection/persistence — failed at scale (Study 010).
- Graph construction and routing — did not advance the bakeoff; oracle routing added 6.09%.
- ANN experiments — bakeoff, no advance over exact search at this scale.
- Segmentation (E002) — killed under its locked criterion at matched budget.
- Attention capture (E001) — 0/714 rows reached the retrieval threshold; closed as a program disposition.
- MMR (A1) and facility location (A2) — A2 scored highest on raw count while delivering monetary 0/4 and passed no gate; both need O(n²) similarity.
- Cosine threshold plus cluster-A3 routing — replaced by CC80; it remains only in the private historical builder.

See `RETRIEVAL_MECHANISM_LEDGER.md` in the source repository.

## Hazards, shipped as contract requirements

**H1 — Embedder call-shape dependence.** The carried model returns
materially different vectors for the same text embedded alone versus in a
batch: cosine agreement 0.999837, largest component difference 0.217,
enough to flip 6 of 146 committed selection payloads (DX-001).
`EpisodicConfig` pins the model hash and the call shape jointly; on every
store open, a fixed sentinel string is embedded under the pinned shape and
its vector hash is asserted against the one stored on first open. Drift is
a hard failure (`CallShapeError`), not a warning.

**H2 — Pool-trimming brittleness.** Dropping the 19 lowest-cosine episodes
from a 119-episode pool cost an entire domain and all known-optimum
overlap, despite 4 of 5 optimum episodes surviving the cut (DR-002). Deployed
CC80 ranks the complete store; no trimming field affects the new path.
