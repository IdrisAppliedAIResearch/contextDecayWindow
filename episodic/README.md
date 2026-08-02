# episodic

Append-only conversational memory with budgeted context construction.
Every exchange is stored verbatim; each call to `context()` rebuilds a
small context from three paths — a recency window, a cosine-threshold
similarity match, and a set-level coverage selector — packed at exact
serialized cost. The design was reached across eleven pre-registered
studies in the `contextDecayWindow` repository, and every behavioral
claim below carries the committed artifact that measured it.

```python
from episodic import EpisodeStore, ContextReport, EpisodicConfig

store = EpisodeStore(path, config=EpisodicConfig())   # opens or creates
store.append(role, content)                           # verbatim, append-only
block, report = store.context(query, budget)          # pure function of (store state, query, budget)
store.close()
```

`store.context()` is a pure function of store state, query, and budget:
no mutation, no inference calls, no network. Same inputs, same output,
byte-identical. That property is what made the studies reproducible and
it is the library's core guarantee (acceptance test T7 asserts it across
two processes).

## Measured behavior

Every number below was measured in the source repository and traces to a
committed artifact. Extraction is certified behavior-preserving by T3/T4:
all 132 committed A3 selection records and all three committed serialized
blocks reproduce their SHA-256 byte-for-byte through this package.

| Claim | Number | Source | Artifact SHA-256 |
|---|---|---|---|
| Targeted recall, 121 turns | 16/16 items preserved | E005 primary configuration | `e005_results.json` `07b714389697c6e5…` |
| Targeted recall, 1,000 turns | 60/60 required facts delivered; 203 K-threshold retrieval events | Study 010, arm S terminal targeted turns | `study_010_report.md` `f013ac7fd446420c…` |
| Breadth, best measured | 12/17 items across 4/4 domains at 31,569 chars | E005 primary configuration | `e005_results.json` `07b714389697c6e5…` |
| Selection latency | 35–43 µs per candidate over 20–3,000 candidates; empirical scaling exponent 0.96 | DR-002 timing sweep, 25 runs per point, embedding excluded | `scaling_timings.json` `08479d445add1519…` |
| Context bound at 1,000 turns | ~27k estimated tokens peak (27,154 = chars//4, verified across all 2,000 serialized prompts) | Study 010 corrected context peak audit | `context_peak_audit.json` `61e833965397c3f8…` |
| Selector scaling | A3 needs a cluster assignment vector, not the O(n²) similarity matrix A1/A2 require | DR-002 | `dr_002_results.json` `8be66a2f457a169d…` |
| Extraction equivalence | 132/132 committed A3 payload SHAs and 3/3 committed rendered blocks byte-identical through this package | CC-002 T3/T4 | `t3_e005_replay.json` `d8e08f94952e468d…`, `t4_render_replay.json` `43c938898a71fa06…` |

Artifacts live in the source repository under
`experiments/components/retrieval_mechanism_ledger/artifacts/e005/`,
`experiments/study_010/`,
`experiments/components/rendering_expansion/artifacts/`, and
`experiments/components/library_extraction/artifacts/cc002/`.

## Known limitations

| Limitation | Number | Source |
|---|---|---|
| Breadth is below the source repository's own bar | 12/17 against a 14/17 threshold and a 15/17 known optimum | E005 (`e005_results.json`, above) |
| The rank-112 class | An episode whose cosine to the relevant query is below what any reweighting can recover (0.056 measured against the 0.225 needed) is invisible to the selector at every registered setting: 0 of 146 configurations selected it | DX-001, `dx001_results.json` `2f07a462e09bdf79…` |
| Evidence breadth | One runtime (llama.cpp CPU embedding), one conversation shape (a scripted 121-turn run and one 1,000-turn run), one measurement set | all of the above |
| Store growth | Unbounded by design in this version; eviction is deliberately out of scope (CC-005) | — |
| Checkpointing | The checkpoint module moved as-is from code that has survived exactly one 1,000-turn run; it is not yet a tested guarantee (CC-004) | Study 010 incident path |
| `truncated` is a report, not a ceiling | The signal is honest; enforcement semantics are out of scope (CC-003) | — |

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
overlap, despite 4 of 5 optimum episodes surviving the cut — the selector
clusters over the pool, so tail removal reshuffles the objective rather
than removing options (DR-002). The candidate policy defaults to the full
store; the trimming option is named `unsafe_cosine_top_n` and its
docstring carries the finding.
