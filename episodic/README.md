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
| Selection latency, small pools | 35–43 µs per candidate over 20–**119** candidates; empirical exponent 0.96 | DR-002 timing sweep, 25 runs per point, embedding excluded | `scaling_timings.json` `08479d445add1519…` |
| Retrieval latency, full store | 190 ms at 1,000 candidates; empirical exponent 1.25 over 50–1,000; clustering is 81% of it | CC-005, 7 runs per point, embedding excluded | `growth_measurement.json` |
| Context bound at 1,000 turns | ~27k estimated tokens peak (27,154 = chars//4, verified across all 2,000 serialized prompts) | Study 010 corrected context peak audit | `context_peak_audit.json` `61e833965397c3f8…` |
| Selector scaling | A3 needs a cluster assignment vector, not the O(n²) similarity matrix A1/A2 require | DR-002 | `dr_002_results.json` `8be66a2f457a169d…` |
| Extraction equivalence | 132/132 committed A3 payload SHAs and 3/3 committed rendered blocks byte-identical through this package | CC-002 T3/T4 | `t3_e005_replay.json` `d8e08f94952e468d…`, `t4_render_replay.json` `43c938898a71fa06…` |
| Budget ceiling | `chars_delivered ≤ budget` at every one of 1,000 replayed turns and across a 1k–64k sweep; 0 breaches | CC-003 E1 + G-E0 | `ge0_growth_gate.json` |
| Delivered block does not grow with store size | p95 moves +18 chars over the last five 100-turn buckets of a 1,000-turn replay; −0.02% window over window | CC-003 G-E0 | `ge0_growth_gate.json` |
| Restart persistence | Turns acknowledged by `append()` survive `SIGKILL`; `context()` returns a byte-identical block across restart; 100 restart cycles with no drift | CC-004 P1–P6 | `CC_004_report.md` |

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
| Store growth | Unbounded retention by policy; see "Growth, and what it costs" below | CC-005 |
| Restart guarantees are tested against process kills, not power loss | P1/P3 kill a live process with no cleanup. Surviving a power cut or a lost storage connection rests on `synchronous=FULL` and SQLite's implementation, not on anything measured here | CC-004 |
| `chars_wanted` is not an upper bound | It is the cost of what the three paths proposed, not of an unconstrained selection: the coverage selector is a budgeted greedy with no unconstrained mode. It tells a caller how much budget the current proposal needed, not what a larger budget would retrieve | CC-003 |
| The ceiling covers the returned block only | Whatever a caller wraps around it — preamble, tool schemas, its own scratchpad — is outside this accounting, and that is exactly where Study 010's growth happened | DX-002 (`ge0_growth_gate.json`) |

## Growth, and what it costs

**The policy is unbounded retention. This version evicts nothing.** That is
a decision, not an omission, and these are the numbers behind it.

Three things could grow as a conversation gets longer. They are not the
same problem and only one of them binds.

| Path | Grows with | Measured | Status |
|---|---|---|---|
| Delivered context | turn count | p95 moves +18 chars across a 1,000-turn replay; −0.02% window over window | **Bounded.** The budget is a hard ceiling and the block does not grow with the store |
| Disk | turn count | 4,743 bytes per turn marginal; 4.8 MB at 1,000 turns | **Cheap.** ~48 MB at 10,000 turns, 86% of it embeddings |
| Retrieval latency | store size | 190 ms at 1,000 candidates; exponent 1.25 | **The binding constraint** |

Latency is what ends continuous operation. Clustering is 81% of it at 1,000
candidates and its share is still rising. Beyond the measured range these
are **projections from the fitted exponent, not measurements**: roughly
430 ms at 2,000 candidates, 1.3 s at 5,000, and 3.2 s at 10,000.

**The stated horizon: this configuration is comfortable to a few thousand
episodes and unusable in an interactive loop somewhere before 10,000.** If
your deployment expects more turns than that, the retrieval path needs work
that this version does not contain.

Two earlier numbers are corrected here rather than quietly restated. DR-002
measured 20–119 candidates and found per-candidate cost flat at 35–43 µs
with exponent 0.96; that holds inside its range and does not extend past
it. A linear projection from 119 understates the cost at 1,000 candidates
by about five times. See `ERRATA.md`.

### Trimming the candidate pool is not the answer

The obvious fix — drop low-similarity episodes so the pool stays small — is
the one operation measured to break retrieval. Dropping the 19
lowest-cosine episodes from a 119-episode pool cost an entire domain and
all known-optimum overlap, **despite 4 of the 5 optimum episodes surviving
the cut**. The selector clusters over the pool, so removing the tail
reshuffles the objective rather than removing options (DR-002).

So the candidate policy defaults to the full store, the trimming option is
named `unsafe_cosine_top_n`, and any eviction policy has to be evaluated
against domain coverage rather than against a similarity threshold.

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
