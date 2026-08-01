# CC-002 — Library Extraction

**Type:** Engineering specification. Not a study, not an analysis.
**Repository:** `contextDecayWindow` — new top-level package, working name `episodic/`
**Branch:** `cc/002-extraction`
**Status:** DRAFT — ready for agent handoff on commit
**Depends on:** DR-001 renderer (`202b1883`) · E005 PROMOTION_ELIGIBLE · DX-001 F.6 close
**Companions:** `CC_001_component_contract.md` · `RETRIEVAL_MECHANISM_LEDGER.md` · `DX_001_turn90_diagnostic_and_fix.md`

---

## 0. Objective

Extract the deployable memory component from the experiment harness into an
installable Python package, such that:

1. The package imports and runs with **zero** experiment machinery — no plants, no
   probes, no rubric artifacts, no scoring hooks, no replay harness.
2. The experiment harness imports **the package** and reproduces committed results
   through it — the harness becomes a consumer, not a sibling.
3. Every measured claim in the README traces to a committed artifact SHA.

**The direction of dependency is the whole point.** If extraction bends the code,
the harness bends to match the library, never the reverse. The library is the
product; the harness is its largest test.

## 0.1 What this PR is not

- Not budget *enforcement* (CC-003). Exact-cost accounting ships here because it
  exists (DR-001); the hard ceiling and truncation signal do not exist yet and are
  not smuggled in.
- Not eviction, not restart hardening, not a new selector, not E006.
- Not a rename or re-architecture of anything the studies validated. Extraction
  moves code; it does not improve it. **Any behavior change is a defect in this PR.**

---

## 1. Public API

The entire installable surface. Everything else is private.

```python
from episodic import EpisodeStore, ContextReport, EpisodicConfig

store = EpisodeStore(path, config=EpisodicConfig())   # opens or creates
store.append(role, content)                           # verbatim, append-only
block, report = store.context(query, budget)          # pure function of (store state, query, budget)
store.close()
```

**`store.context()` is a pure function** of store state, query, and budget: no
mutation, no inference calls, no network. Same inputs, same output, byte-identical.
That property is what made eleven studies replayable and it is the library's core
guarantee. A test asserts it directly (§5, T7).

### 1.1 `ContextReport`

The observability object no comparable library ships. Every call returns one.

| Field | Meaning |
|---|---|
| `chars_delivered` | exact serialized length of `block` |
| `chars_wanted` | what selection would have taken unconstrained |
| `episodes_delivered`, `episodes_dropped` | counts |
| `truncated` | bool — selection wanted more than budget allowed |
| `stm_count`, `k_count`, `coverage_count` | episodes per source path |
| `latency_ms` | wall-clock for this call |
| `pool_size` | candidates evaluated |

`truncated` is honest reporting of a condition the caller should know about;
*acting* on it (hard ceiling semantics) is CC-003.

### 1.2 `EpisodicConfig`

Every constant the studies swept or pinned, in one frozen dataclass — nothing
buried in module globals:

recency window N · K threshold (0.48) · candidate policy (**full store** — deployed
default per DR-002; the N∪K pool is retained as a named non-default option with its
limitation documented) · selector (`A3`, λ=0.1, r=0.0, k=16) · budget accounting
(exact serialized, DR-002 renderer) · **embedder identity: model hash AND call
shape** (§3) · seed.

The config serializes to JSON and is stored alongside the store on first open.
Reopening with a mismatched config raises unless explicitly overridden — a store's
numbers are only meaningful under the config that produced them.

---

## 2. What moves, what stays, what dies

### 2.1 Moves into `episodic/`

| Component | Source | Note |
|---|---|---|
| Append-only episode store | Study 005+ permissive store | Verbatim, offset-preserving |
| STM recency window | carried since 001 | |
| K-threshold similarity retrieval | carried since 001 | The 60/60 path |
| A3 coverage selector | E005 | Primary config as default; A1/A2 **not** extracted — O(n²) similarity matrix, disqualified at scale by DR-002 |
| N-first packing at exact cost | DR-001 | |
| Compact episode renderer | DR-001 | The serialization contract |
| Embedding wrapper | carried embedder | With call-shape pinning (§3) |
| Checkpoint write/read | Study 010 incident path | Moved as-is; **hardening is CC-004**, and its once-only provenance is documented in the README |

### 2.2 Stays in the harness (imports the library)

Plant/probe machinery · rubric and scoring artifacts · replay gates · determinism
spot-checks · leakage audits · the probe-order validator · all study runners and
sweep drivers.

### 2.3 Dies (not extracted, not deleted — remains in harness history)

Dreaming/distillation · promotion filters · TopicManager · rule detection · graph
construction · ANN experiments · routing · segmentation (E002) · attention capture
(E001). Each is in the ledger graveyard with the number that killed it. The library
README links there rather than re-litigating.

---

## 3. The two hazards shipped as contract requirements

Both found by gates in the last two weeks. Both would be silent in a deployed
library. Both become **pinned configuration + startup assertion**, not documentation
footnotes.

**H1 — Embedder call-shape dependence (DX-001 replay gate).** The carried embedder
returns materially different vectors for a query embedded alone versus in a batch —
cosine agreement 0.999837 yet a component difference of 0.217, flipping 6 of 146
committed payloads. Production embeds queries one at a time; every committed number
came from batch embedding.
**Requirement:** `EpisodicConfig` pins the call shape. On store open, the library
embeds a fixed sentinel string under the pinned shape and asserts the vector hash
against the stored one. Drift → hard failure with a message naming this hazard.

**H2 — Pool-trimming brittleness (DR-002).** Dropping the 19 lowest-cosine episodes
from the 119 pool cost an entire domain and all oracle overlap, despite 4 of 5
oracle episodes surviving the cut — A3 clusters over the pool, so tail removal
reshuffles the objective rather than removing options.
**Requirement:** candidate policy defaults to full store. Any trimming option is
named `unsafe_` and its docstring states the finding with the artifact reference.

---

## 4. README — measured claims only

The README is a measurement report. Layout:

1. **What it is** — three sentences, the API block.
2. **Measured behavior** — the table below, every row carrying its artifact SHA.
3. **Known limitations** — same table discipline. The rank-112 class (an episode
   whose cosine to the relevant query is below what any reweighting can recover:
   0.056 vs the 0.225 needed) named as a *class*, with DX-001 linked. Breadth 12/17.
   One runtime, one conversation shape, one probe set.
4. **What was removed and why** — one line per graveyard entry, ledger link.
5. **Hazards** — H1, H2 as above.

| Claim | Number | Source |
|---|---|---|
| Targeted recall, 121 turns | 16/16 | E005 |
| Targeted recall, 1,000 turns | 60/60, 203 K events | Study 010 |
| Breadth, best measured | 12/17, 4/4 domains | E005 primary |
| Selection latency | ~40 µs/candidate, empirical exponent 0.96 | DR-002 |
| Context bound at 1,000 turns | ~27k tokens (chars//4, verified across all 2,000 serialized prompts) | Study 010 corrected |
| Selector scaling | A3 avoids the O(n²) similarity matrix | DR-002 |

**Rule: no claim without a SHA. No adjective without a number.** "Fast,"
"robust," and "production-ready" do not appear.

---

## 5. Acceptance tests — the definition of done

| # | Test | Certifies |
|---|---|---|
| T1 | `pip install -e . && python -c "import episodic"` in a clean venv with **no harness on the path** | Zero experiment dependencies |
| T2 | Grep gate: no reference to plants, probes, rubric, scoring, replay in `episodic/` — enforced in CI, mirroring the leakage audit | Separation is structural, not incidental |
| T3 | Harness reproduces the E005 primary result vector (12/17, 4/4, 16/16, 31,569 chars) **through the library import** | Extraction changed nothing |
| T4 | Harness reproduces the Study 010 replay blocks to the character through the library renderer | Serialization contract intact |
| T5 | H1 sentinel assertion fails loudly under a deliberately wrong call shape | Hazard gate works |
| T6 | Full existing suite green (778) with the harness consuming the library | No regression anywhere |
| T7 | `store.context()` byte-identical across two processes, same inputs, fixed seed | Purity guarantee holds outside the harness |

**T3 is the extraction's replay gate.** If the number moves, the extraction changed
behavior, and the PR does not merge until the cause is found — the DR-001/G-R1
discipline applied to a refactor.

### Surrogate audit on the tests

| Test | Can it pass falsely? | Mitigation |
|---|---|---|
| T1 imports | Yes — import ≠ works | T3/T4 exercise the full path |
| T2 grep | Yes — renamed references evade grep | Import-graph audit alongside, per standing leakage protocol |
| T3 result vector | Yes — if the harness shim reimplements rather than imports | Assert call goes through `episodic` symbols (import-graph, not just result equality) |
| T6 suite green | Yes — tests could be weakened during the move | Test files are moved verbatim; any test modification is listed and justified in the PR description |

## 6. Sequencing within the PR

1. Skeleton package: API, config, empty implementations. T1 passes trivially.
2. Move store + renderer. T4.
3. Move retrieval + selector + packing. T3.
4. H1/H2 gates. T5.
5. Rewire harness imports. T6, T7.
6. README with the claims table.

One PR, reviewable in stages by commit. If it grows past reviewability, split at
step 4 — the library core and the harness rewiring are separable merges.

## 7. Out of scope, queued behind this

- **CC-003:** budget enforcement + truncation semantics (the ceiling, the signal contract)
- **CC-004:** restart persistence as a tested guarantee
- **CC-005:** eviction policy (v0: stated unbounded)
- LongMemEval identity slice + instrument audit (unblocked by nothing, still owed)
- E006 (proposed, unauthorized)

---

*Drafted August 1, 2026. Shipping configuration: `A3_l0.1_r0.0_k16` over the full
store, 12/17 · 4/4 · 16/16 @ 31,569 chars, certified DX-001 F.6. Suite 778. PRs
#25, #26 merged context.*
