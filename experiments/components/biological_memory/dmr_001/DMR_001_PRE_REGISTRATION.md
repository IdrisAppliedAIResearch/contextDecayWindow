# DMR-001 - Online Event-Context Formation

**Type:** Pre-registered write-path component study
**Date:** August 12, 2026
**Branch:** `study/dmr-001-event-context-formation`
**Status:** PRE-REGISTERED - NO IMPLEMENTATION IN THIS COMMIT
**Authorization:** Program author approved
`DMR_001_EVENT_CONTEXT_FORMATION_IMPLEMENTATION_SPEC.md` and directed
end-to-end implementation on August 12, 2026
**Governing design:**
`experiments/components/biological_memory/deterministic_retrieval/DMR_001_EVENT_CONTEXT_FORMATION_IMPLEMENTATION_SPEC.md`
**Part 1 record:** `exploration/DMR_001_PART1_EXPLORATION.json`
**Corpus lock:** `artifacts/dmr001_corpus/corpus_lock.json`
**Outcome ceiling:** `CHARACTERIZED`. No retrieval, no reader, no ablation, no
live run, no adoption.

## 1. Decision this study owns

DMR-002 through DMR-006 all assume that a conversation can be partitioned into
event records that are stable, nondegenerate, and worth binding memories to.
Nothing in the program has tested that assumption. DMR-001 asks only:

> Can a label-blind, causal, deterministic encoder over pinned episode
> embeddings partition committed conversations into nondegenerate events, beat
> structural controls on sealed boundary evidence, and store an encoding
> context that separates within-event pairs from across-boundary pairs?

This study retrieves nothing, ranks nothing, packs nothing, and answers
nothing. It implements one component on the write path and measures it.

## 2. Revisions to the implementation spec

Part 1 forced three changes. Each is recorded here rather than by editing the
governing design.

### 2.1 Episode identity carries stream position

The spec's schema declares `event_members.episode_hash TEXT NOT NULL UNIQUE`,
which presumes that episode text identifies a stored row. It does not. In the
1,000-turn endurance stream, 844 of 1,000 episodes repeat an earlier episode's
exact user and assistant text; across the whole corpus 1,995 of 3,724 episodes
are content duplicates and one prompt repeats 11 times.

Registered identity:

```text
episode_hash = sha256(
    "dmr-episode-v1\0" + session_hash + "\0" + stream_index + "\0" +
    sha256(canonical JSON of [["user", u], ["assistant", a]])
)
```

This stays content-addressed - no path, timestamp, UUID, or row id - and is
unique per append, so the `UNIQUE` constraint holds as written.

### 2.2 The session token is minted by the corpus lock

The spec requires that `event_id` not depend on a future member. It does not.
But a session token must exist before the session's first episode is observed,
and first episodes are not unique across this corpus: 14 distinct 121-turn
realizations share only 4 distinct opening episodes, and both 1,000-turn
realizations share one.

Registered token:

```text
session_hash = sha256("dmr-session-v1\0" + sha256(ordered pair hashes of the session))
```

The corpus lock computes it once from the frozen stream and hands it to the
former as an opaque equality token, exactly as a live deployment would hand
over a session id minted when the session opens. The former never computes it
and uses it only for equality and for `event_id`.

**Residual, stated in the report:** in this offline replay the token is derived
from the session's complete content, so `event_id` inherits a whole-session
content dependency. It does not depend on future members *of the event*, it is
constant for the session, and event identity is still assignable when the event
opens and never mutates. DMR-001 does not demonstrate a live session-token
mint.

### 2.3 Boundary annotations are corpus provenance, not human annotators

The spec asks for independent human annotators, and separately forbids a
language-model boundary judge. No annotators are available to this program and
the model judge is excluded, so the registered annotation is the
`ground_truth_domain` column already committed in every selected run database.
It was written by the corpus scripts before DMR-001 existed, is blind to this
mechanism and its settings, is blind to retrieval outputs, and is never read by
the former.

**Residual, stated in the report:** this certifies agreement with a *scripted
topic schedule*, not with a human-perceived event boundary. G4 cannot be read
as psychological validity.

## 3. Corpus, splits, and sealing

The corpus lock is committed at
`artifacts/dmr001_corpus/corpus_lock.json`, corpus digest
`be939cbebc0e9e9f33906ffc92047e114372852bbc578bb4376efd0e061d3bf9`.

Selection is mechanical and was fixed before any agreement number existed:

1. Every committed `experiments/**/study.db` whose `episodes` table has at
   least 30 rows, turn numbers contiguous from 1, a non-empty
   `ground_truth_domain` on every row, both message texts, and a
   1024-dimensional float32 embedding on every row.
2. Group by user-script identity; drop any script that is a strict prefix of
   another. This removes the 100-900 turn checkpoints and rehearsals that are
   prefixes of the 1,000-turn stream, and the 35-turn ablation script that is a
   prefix of the 121-turn script.
3. Within a surviving script keep one session per distinct realization of the
   ordered user-plus-assistant content, choosing the smallest source path.
4. The single longest script is the **holdout**. Everything else is
   **development**.

| Split | Sessions | Episodes | Annotated boundaries |
|---|---|---|---|
| Development | 15 | 1,724 | 60 internal plus 15 session starts |
| Holdout | 2 | 2,000 | 36 internal plus 2 session starts |

No holdout agreement, size distribution, or context statistic was computed
before this file was committed. The Part 1 record contains holdout counts and
identity digests only. Any holdout number that appears before this commit in
git order invalidates the study.

## 4. Locked mechanism

Module: `src/biological_memory/event_context.py`, class
`OnlineEventContextFormer`. Public contract exactly as the governing design
states: `observe(*, episode_hash, session_hash, turn_index, embedding)` and
`snapshot()`. `observe` accepts no text.

### 4.1 Numeric contract

Vectors are float32. Every reduction - norm, dot, cosine - is computed with
`math.fsum` over float64 products, which is exactly rounded and independent of
summation order. No BLAS call participates, so thread count, CPU dispatch, and
machine cannot change a bit. Vector SHA-256 is taken over little-endian float32
bytes.

```text
x_t = normalize(pinned episode vector)          # pinned vectors are NOT unit norm
n_t = members in the open event
S_t = S_(t-1) + x_t                             # float32, element-wise, append order
p_t = normalize(S_t / float32(n_t))
c_t = normalize(float32(rho) * c_(t-1) + float32(1 - rho) * x_t)
d_t = 1 - dot(x_t, p_(t-1))
```

At the first member of an event, `S_t = x_t`, `p_t = normalize(x_t)`, and
`c_t = x_t`.

### 4.2 Locked parameters

| Parameter | Value | Basis |
|---|---|---|
| `rho` | `0.5` | Highest development context AUC (.8233) over the grid 0, .25, .5, .75, .9; rho does not enter the boundary rule |
| `drift_threshold` | `0.70` | Highest development boundary F1 at tolerance 1 over the 171-cell grid |
| `min_event_size` | `5` | Same grid cell |
| `max_event_size` | `32` | Same grid cell; smallest max at the peak F1, forced fraction .0052 |
| `boundary_tolerance` | `1` | Primary; 0 and 2 reported |
| `context_lag_max` | `8` | Pair lag for the context-separation statistic |

These are the only tunable values and they live nowhere else. The
implementation must read them from `DMR_001_FINAL_DESIGN.json` and refuse to
run against a mismatched design hash.

### 4.3 Boundary decision and tie behavior

```text
hard_boundary   = a session token was already open and the new token differs
drift_boundary  = n_(t-1) >= min_event_size and d_t >= drift_threshold
forced_boundary = n_(t-1) >= max_event_size
new_event       = hard_boundary or drift_boundary or forced_boundary
```

Comparisons are `>=`, so a drift exactly equal to the threshold opens a new
event. All three booleans, `d_t`, `n_(t-1)`, the threshold, and the design hash
are recorded for every episode. When more than one predicate is true the
recorded `boundary_reason` uses the precedence `hard` > `drift` > `forced`;
precedence affects the recorded label only, never the partition. The first
episode of the whole stream records `stream_start`.

### 4.4 Identity and persistence

```text
event_id = sha256("dmr-event-v1\0" + design_sha256 + "\0" + session_hash + "\0"
                  + first_episode_hash)
```

`design_sha256` is the SHA-256 of this file's committed bytes with line endings
normalized to LF. Storage is the spec's schema unchanged. Writes for one
observed episode are one transaction. Replaying an episode that is already
stored with identical values is a no-op; any differing value raises. Silent
reassignment is prohibited.

## 5. Arms

| Arm | Rule |
|---|---|
| `C_SESSION` | Boundaries at session changes only |
| `C_PAIR` | Every episode is its own event |
| `C_ALL` | Each session is exactly one event |
| `C_PERIODIC_k` | Session starts plus every k-th episode, `k` in 2, 4, 8, 16, 32, 64 |
| `T_EVENT` | The locked rule in section 4 |

`C_PAIR` and `C_ALL` are degenerate references. `C_PERIODIC_k` exists so that
G3 and G4 cannot be passed by fixed chopping. On this corpus `C_SESSION` and
`C_ALL` produce the same boundary set; both are reported.

## 6. Measures

- **Boundary agreement.** Tolerance-aware precision, recall, and F1 against the
  registered annotation. A predicted boundary matches an annotated boundary
  within `tolerance` stream positions; each annotation matches at most once;
  matching walks stream order so one prediction cannot cover several
  annotations.
- **Event size.** Full distribution, singleton fraction, forced fraction, and
  the largest event as a fraction of its session.
- **Context separation.** For every ordered within-session pair at lag 1 to 8,
  `within` when no annotated boundary falls between the two episodes and
  `across` otherwise; predictor is the cosine of the two stored context
  vectors; AUC per session, macro-averaged. The same statistic on the raw
  normalized episode vectors is the control.
- **Replay stability.** Byte-identical decision digest, event records, and
  vector hashes across two fresh processes.
- **Every boundary decision** with its causal input hashes.

Domain and fact co-membership may be reported after formation. Neither may
select anything.

## 7. Binding gates

Stop at the first failed gate. G1-G3 are evaluated on both splits. G4 and G5
are binding on the holdout; development values are reported for contrast only.

| Gate | Binding bar | Failure disposition |
|---|---|---|
| **G1 Integrity** | Two fresh processes give identical decision digests, event rows, and vector hashes; the frozen corpus replays to the committed corpus digest; the former rejects out-of-order turns, wrong-dimension vectors, malformed hashes, and a reopened session; no import path from the mechanism to keys, rubrics, reader clients, packers, or scorers; no completion, chat, or response call in the process | `INTEGRITY_STOP` |
| **G2 Partition** | Every episode appears in exactly one event at exactly one position; positions are contiguous from 0; no event spans two sessions; event order is append order | `PARTITION_VIOLATION` |
| **G3 Nondegeneracy** | Singleton fraction <= 0.20; forced fraction <= 0.35; no event holds more than 25% of its session; the boundary set is not identical to `C_PAIR`, `C_ALL`, `C_SESSION`, or any `C_PERIODIC_k` | `DEGENERATE_FORMATION` |
| **G4 Boundary evidence** | On the holdout at tolerance 1: `T_EVENT` F1 >= `C_SESSION` F1 + 0.05, `T_EVENT` F1 >= best `C_PERIODIC_k` F1 + 0.05, `T_EVENT` recall >= 0.50, and `T_EVENT` precision >= 0.20 | `NO_BOUNDARY_EVIDENCE` |
| **G5 Context separation** | On the holdout: macro context AUC >= 0.70, context AUC >= raw-vector AUC, and every holdout session's context AUC >= 0.60 | `NO_CONTEXT_SEPARATION` |

If G1-G5 pass, the disposition is `EVENT_SUBSTRATE_SUPPORTED_OFFLINE`. That
freezes the event map and this design for DMR-002 and authorizes nothing else.
If G4 or G5 fails, the arc records that deterministic embedding-change event
formation is not a valid substrate on this evidence, and DMR-002 through
DMR-006 are blocked. Do not retune a threshold, widen the tolerance, change the
aggregator, or swap the corpus after seeing a holdout number.

### 7.1 Reachability

Every bar is reachable, demonstrated on development before locking:

| Bar | Development value | Reachable |
|---|---|---|
| F1 margin over `C_SESSION` >= 0.05 | +0.0861 (.4195 vs .3333) | yes |
| F1 margin over best periodic >= 0.05 | +0.1126 (.4195 vs .3069) | yes |
| Recall >= 0.50 | 0.747 | yes |
| Precision >= 0.20 | 0.292 | yes |
| Singleton fraction <= 0.20 | 0.000 | yes |
| Forced fraction <= 0.35 | 0.0052 | yes |
| Context AUC >= 0.70 | 0.8233 | yes |
| Context minus raw >= 0 | +0.0510 | yes |
| Per-session context AUC >= 0.60 | min 0.7802 | yes |

Failure is reachable too: `C_PAIR` scores F1 .0834 and `C_ALL` scores .3333 on
the same development split, so the bars discriminate.

## 8. Preflight

### Part 1 - completed, committed at `exploration/DMR_001_PART1_EXPLORATION.json`

Findings that bind this registration:

- Pinned vectors are not unit norm; median 113.37, range 83.02 to 148.57.
  Normalization is part of the mechanism.
- Adjacent-episode drift is median .724 within a block, .828 at an annotated
  boundary, .552 at a session start; annotated-versus-within AUC .755. Running
  prototype drift gives .576 / .683 / .669 and AUC .718.
- The minimum drift at an abrupt annotated shift (.7485) is .175 *below* the
  maximum drift inside the longest coherent annotated block (.9234). No
  threshold separates them cleanly, and no bar in section 7 assumes one does.
- An exact duplicate episode gives drift 4.99e-9; a one-coordinate 1e-3
  perturbation gives 5.00e-7. Duplicates never open an event.
- All four degenerate states are demonstrated on the real development stream:
  all-singleton at threshold 0 (1,724 events), all-one-event at an unreachable
  threshold (15 events, one per session), forced-periodic at
  `max_event_size` 8 (228 events, maximum size exactly 8), and oscillation,
  which requires `min_event_size` 1 and even then reaches only .29 alternation
  with 76% singletons. `min_event_size` 5 forbids it structurally.
- Two fresh processes produce identical decision digests at two configurations
  on both splits.

### Part 2 - PF1-PF10

Executed by `scripts/run_dmr001_preflight.py` into
`artifacts/dmr001_preflight/preflight.json`. Every check names an executed test
or an artifact hash; a prose assertion fails.

| Check | Required executed evidence |
|---|---|
| PF1 | Recompute every source database SHA-256, episode count, stream digest, and vector digest in the corpus lock; counts must match section 3 exactly |
| PF2 | The locked component and the Part 1 exploratory implementation, written independently, must produce identical decisions, prototypes, and context hashes on a real stream |
| PF3 | Git ancestry proves corpus lock, Part 1, and this registration precede the mechanism commit; a runtime sentinel proves the preflight artifact exists before any gate is evaluated |
| PF4 | Reproduce the section 7.1 reachability table by execution, and drive synthetic fixtures through every gate disposition including each failure |
| PF5 | Identity is a pure function of content, session token, stream position, and design hash; a fixture proves paths, timestamps, and row ids change nothing |
| PF6 | Replay the frozen corpus and reproduce the committed corpus digest and the Part 1 decision digests exactly |
| PF7 | Absorbing-state proof at the intended length: run the 1,000-turn holdout stream and show singleton, giant-event, and forced-periodic states are entered only at their registered settings and not at the locked one |
| PF8 | State that no reader ablation occurs, that formation-only limits are explicit, and what the 3,724-episode corpus cannot detect |
| PF9 | Execute the section 9 surrogate table and record every residual |
| PF10 | State that DMR-001 has no live verdict and cannot authorize one |

## 9. Surrogate audit

| Observed pass | Property that can remain false | Control or residual |
|---|---|---|
| Boundary F1 beats controls | The detector found event structure | It may be tracking the lexical template that opens each scripted block; periodic and raw-vector controls bound this, external replication does not exist |
| Annotation agreement | Boundaries are psychologically real | The annotation is a scripted topic schedule, not human judgment; see 2.3 |
| Context AUC is high | The context state adds information | Context resets at formed boundaries that correlate with annotated ones, which is partly tautological; the raw-vector control is required to be beaten, not merely matched |
| Nondegeneracy passes | The partition is useful for retrieval | DMR-001 measures no retrieval at all; usefulness is DMR-002's question and is not implied |
| Byte-identical replay | The mechanism is correct | Determinism certifies reproducibility, not validity |
| Two 1,000-turn sessions pass | The rule generalizes | The holdout is one script in two realizations sharing all user text; sessions are not independent conversations |
| The corpus is 3,724 episodes | The corpus is naturalistic | Both scripts are synthetic study corpora; 1,995 episodes are exact content duplicates and the endurance script is 84% repeated filler |

## 10. Runtime, artifacts, exclusions

Set `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`,
`NUMEXPR_NUM_THREADS=1`. Record command, process id, source commit, script
SHA-256 after decoding, platform, Python and NumPy versions, and explicit
UTF-8. Artifacts are canonical UTF-8/LF JSON, sorted keys, refuse overwrite,
and carry no generated timestamp inside any comparison digest.

Required artifacts: corpus lock, Part 1 record, this registration,
`DMR_001_FINAL_DESIGN.json`, preflight report, per-arm formation stores and
decision logs, measurement report, gate report, and study report.

No generation occurs. No answer is scored. No retrieval, ranking, packing,
32,000-character block, reader call, ablation, or live inference is run. A
failed gate is a completed negative result, not an invitation to amend the
mechanism.
