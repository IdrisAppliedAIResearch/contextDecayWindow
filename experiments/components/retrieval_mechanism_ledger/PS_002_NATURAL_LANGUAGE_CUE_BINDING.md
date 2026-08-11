# PS-002 - Natural-Language Cue Binding to Sparse Engrams

**Type:** Pre-registered offline component study
**Date:** August 11, 2026
**Branch:** `study/ps-002-natural-language-cue-binding`
**Status:** PRE-REGISTERED - IMPLEMENTATION AND OUTCOME ACCESS PROHIBITED UNTIL AUTHORIZATION
**Predecessor:** PS-001 pattern-separated engram formation
**Outcome ceiling:** `CHARACTERIZED`

## 1. Motivation

PS-001 formed 119 unique 41-of-4,096 sparse episode codes, stored all 119 as
fixed points, and recovered all 119 under the registered source-centered swap
corruptions. It did not show that a natural-language question could activate a
relevant stored code. Its cues were generated from the source code itself.

PS-002 adds exactly one component: a deterministic semantic-to-engram cue
binder. The binder converts a sealed natural-language query embedding into a
sparse cue field, lets the unchanged PS-001 recurrence resolve that cue, and
returns at most eight stored episode identities. It does not answer questions.

The study asks:

> Can a natural-language query, without fact labels or a source identity, drive
> the fixed PS-001 memory into engrams containing the query's required evidence?

## 2. Integrity anchors and immutable inputs

The following byte hashes are authoritative. A mismatch stops execution.

| Input | Bytes | SHA-256 |
|---|---:|---|
| PS-001 component source, `src/retrieval_mechanism_ledger/ps001.py` | 21,048 | `BC29DC0F0D3A443D640572C88C3E10DF08C6277DDF2326C689D9BD0B9ECEF172` |
| PS-001 report | 11,138 | `FD7DF65335B1CE60822CA5114C1A5B832960D6F10659A6E9776564728DE29412` |
| 119-episode database | 1,978,368 | `5DA47EA3FC2C8E3DCC50FA380FF65202D82557905D9976117E9E5D82E55C1C41` |
| Sealed 121-turn query manifest | 4,231 | `AE950FDA20DCE9F519F31EE2670A815A5599648CAB618D42309DB7E3F23D36F4` |
| Sealed query-vector cache | 249,856 | `D9741EDB0545D8CFE050663340599A31813D6025C38F0467E0EC7671573A1E6A` |
| Query-vector capture manifest | 17,131 | `2C24EA75D7551BEB6658D8B9208225B985E25A9111CFD3766EC4F7980A7F18E4` |
| Measurement-only answer key | 9,832 | `2D43A31D3C04F4AD690FF2910ABDE71F508A3F6CE776545A9F2B16F90FAE5320` |
| Holdout artifact lock | 1,348 | `CDB3B2D7EBFEC8D24F566A43FC3B2A46722DAEF8B95C3AA831E4D88BE1FA9388` |

The artifact lock also records normalized-LF content hashes. The implementation
must verify both the raw-byte hashes above and the lock's normalized-LF hashes
for the query manifest and answer key.

The eligible memory population is exactly source turns 1-119 from the database,
ordered by `(turn_number, id)`. The exact normalized episode matrix identity is
the PS-001 digest
`2ED0CC29B0DE9B54BF80BBD800123938ECAAC2353B3E01ECE37E397B6844E27B`.

The query population is the 24 `c121_l` queries in manifest order:

- 12 `lookup` queries, one required fact each;
- 8 `chained` queries, two required facts each;
- 4 `enumeration` queries, four required facts each.

The 24 query vectors already exist in the sealed cache. PS-002 makes zero new
embedding requests and zero generation calls.

## 3. Carried PS-001 mechanism

PS-002 must construct PS-001 without modifying its source or behavior:

```text
D_CODE = 4096
K_ACTIVE = 41
PROJECTION_SEED = 0448cb7290b285bf85aa856004bd6ccbe8124aa8e3f83eaaa0225519dd626362
MAX_SWEEPS = 4096
```

The carried mechanism must reproduce:

- 119 unique code hashes in the PS-001 committed sequence;
- 119/119 fixed points;
- the PS-001 canonical mechanism digest
  `0D45DDD45980DBF3989A543136BAD52D4F743F650F3C0AF76E370F049B6C80CC`.

Any carried-identity failure stops PS-002. Repairing or recalibrating PS-001 is
out of scope and requires a prospective amendment.

## 4. The one new component

### 4.1 Behavioral identity

In one falsifiable sentence:

> Given one normalized natural-language query vector, the cue binder computes
> semantic support over all 119 label-blind episode vectors, converts a bounded
> support mixture into a 41-active cue, runs unchanged PS-001 recurrence, and
> emits only exact stored-code identities, without reading fact labels.

### 4.2 Semantic support

Let `X` be the fixed 119 by 1,024 normalized episode matrix, `q` one normalized
query vector, `C` the 119 by 4,096 binary code matrix, and
`eta = C - 41/4096` the carried centered code matrix.

For each query:

```text
s_i = fixed_order_dot(X_i, q)
```

Ties are resolved by population index, which is bound to content-hash order.
No timestamps, generated IDs, file paths, domains, source turns, fact IDs, or
rubric fields enter the mechanism.

### 4.3 One retrieval round

For one registered support width `M` and temperature `TAU`:

1. Exclude episode indices already emitted for this query.
2. Select the highest-support `M` remaining indices, using population index for
   exact ties.
3. Let `s_max` be their maximum support and compute float64 weights:

```text
w_i = exp((s_i - s_max) / TAU)
w_i = w_i / fixed_order_sum(w)
```

4. Form the cue field in selected-index order:

```text
g = fixed_order_sum_i(w_i * eta_i)
```

5. Convert `g` to exactly 41 active units using PS-001 `top_k_binary`, including
   its index tie rule.
6. Run unchanged PS-001 synchronous recall from that cue.
7. Emit the terminal identity only if it exactly equals one of the 119 stored
   code hashes and has not already been emitted.
8. If the terminal is spurious, cyclic, guarded, or duplicate, emit no identity
   for that round and inhibit the highest-support candidate from step 2.
9. If an exact new identity is emitted, inhibit that emitted episode.

Execute exactly eight rounds per query. The ordered emitted identities are the
binder output. A failed round is retained in its original position in the trace
and does not increase the output count.

### 4.4 Registered Part 1 grid

Part 1 explores exactly nine cells, in row-major order:

```text
M in {4, 8, 16}
TAU in {0.025, 0.050, 0.100}
```

Every cell runs all 24 queries for eight rounds, but Part 1 is label-blind. The
answer key may not be imported, opened, parsed, hashed by mechanism code, or
used in cell selection. The input verifier may hash the answer-key file without
parsing it.

### 4.5 Mechanical cell selection

A cell is eligible only if:

- all 192 rounds terminate without a runtime guard;
- no round terminates in a cycle;
- every query emits eight unique stored identities;
- all cue and terminal states have exactly 41 active units;
- all numerical values are finite.

Among eligible cells, select mechanically by this ordered tuple:

1. greatest number of initial cues changed by recurrence and completed to a
   stored identity;
2. greatest minimum positive terminal competition margin;
3. greatest median initial-to-terminal Hamming distance;
4. smallest `M`;
5. smallest `TAU`.

If no cell is eligible, disposition is `NATURAL_CUES_NOT_BOUND`; stop before
Part 2 and before opening measurement labels.

This selection rule deliberately does not optimize relevance. It selects a
well-defined cue-to-attractor mechanism before asking whether its attractors are
the right memories.

## 5. Part 1 exploration requirements

Part 1 must commit, unopened by measurement code until its commit exists:

- one row per cell and query;
- all 1,728 round traces (9 cells x 24 queries x 8 rounds);
- semantic-support distribution, including all 119 ranks per query;
- initial and terminal code identities and active counts;
- initial-to-terminal Hamming distance distribution;
- fixed, spurious, cycle, duplicate, and runtime-guard counts;
- margin distributions and every tie-sensitive trace;
- emitted-identity frequency and unused-memory counts;
- selected-cell identity under Section 4.5;
- wall time, peak RSS, estimated live-array bytes, environment, command, PID,
  Python, NumPy, and source hashes;
- zero embedding requests, zero generation calls, and a forbidden-import audit;
- an artifact manifest binding every output by bytes and SHA-256.

The entire Part 1 process must be repeated in a fresh process. Deterministic
artifacts, excluding explicit process metadata and wall/RSS fields, must match
byte-for-byte by canonical digest.

## 6. Final design lock

After Part 1 is committed, a standalone final design revision must record only:

- the mechanically selected `(M, TAU)` cell;
- the committed Part 1 artifact and digest;
- the unchanged Part 2 gates in Section 8;
- whether Part 2 is authorized to proceed.

The revision may not inspect or report answer-key facts, source turns, domains,
lookup correctness, chained coverage, enumeration coverage, or any relevance
outcome. It must be separately authorized and committed before Part 2 code.

## 7. Preflight

Preflight occurs in two ordered parts and must pass before relevance evaluation.

### 7.1 Part 1 - empirical characterization

Section 5 is the required empirical characterization. It must establish the
behavioral identity in Section 4.1, verify every named component against actual
traces, report distributions rather than summaries, and retain degenerate
outcomes including spurious, duplicate, cyclic, guarded, and tie-sensitive
states. A label-blind selected cell is required to continue.

### 7.2 Part 2 - PF1-PF10

| Check | Required executed evidence |
|---|---|
| PF1 inputs | Hash, byte count, schema, row count, vector shape, and content count for every Section 2 input |
| PF2 identity | Reproduce PS-001 digest and execute the selected binder on all 24 committed natural-language queries |
| PF3 ordering | A planted sentinel proves answer-key parsing is impossible before selected-cell artifact verification and all gates run before relevance output |
| PF4 reachability | Verify all 24 required fact sets exist in eligible turns; the lookup ceiling is 12/12, per-domain ceiling 3/3, and output capacity is eight identities |
| PF5 stable keys | Query text SHA-256, episode content SHA-256, code SHA-256, and fact IDs only; no generated IDs, paths, or timestamps compare conditions |
| PF6 reproduction | Reproduce the committed PS-001 mechanism digest and selected Part 1 deterministic digest exactly |
| PF7 feedback | Verify all selected-cell traces terminate as registered and independently replay at least one changed cue per query through full recurrence |
| PF8 adequacy | State that 24 queries cover lookup, two-memory, and four-memory cues on this 119-episode store, but cannot estimate other language, stores, seeds, or long-run drift |
| PF9 surrogate | Report direct-cosine, initial-cue, recurrence, and final-output controls; a stored terminal alone is not relevant binding |
| PF10 live requirement | State that offline evidence availability is not an answer verdict; PS-002 authorizes no generation or live score |

Every item must name an executed test and committed artifact. A checked box,
assumption, or prose-only assertion is a failure.

## 8. Relevance evaluation and ordered gates

Only after Part 1, the final design lock, authorization, and PF1-PF10 pass may a
measurement-only module parse `answer_key_121.json`.

### 8.1 Matching

A fact is available if at least one emitted episode has a source turn listed for
that fact in the sealed answer key and contains all required terms under the
answer key's case-insensitive, same-serialized-episode rule. Mechanism code sees
none of these fields.

Report per query:

- ordered emitted source turns and content hashes;
- required fact IDs and matched episode hashes;
- facts available / facts required;
- reciprocal rank of the first matching emitted episode;
- direct-cosine top-eight control under the same matching rule;
- initial-cue nearest-code and final terminal identity for every round.

### 8.2 Gates

Gates execute in this order and stop at the first failure:

| Gate | Binding bar | Failure disposition |
|---|---|---|
| G1 carried memory | PS-001 digest exact; 119/119 fixed points | `CARRIED_MEMORY_IDENTITY_FAILED` |
| G2 cue mechanics | Selected cell meets every Section 4.5 eligibility rule in committed Part 1 and PF7 replay | `NATURAL_CUES_NOT_BOUND` |
| G3 lookup binding | At least 9/12 lookup facts available and at least 2/3 in each of structural, art, monetary, and marine | `LOOKUP_BINDING_INSUFFICIENT` |
| G4 baseline differentiation | Binder lookup count is at least direct-cosine top-eight count + 2, with no domain below its cosine count | `NO_BINDING_GAIN` |
| G5 bounded output | Every query emits exactly eight unique episode identities; no label-dependent retries | `OUTPUT_BOUND_FAILED` |

The registered G3 bar is above the pre-lock direct-cosine feasibility result of
7/12 top-eight lookup coverage. G4 requires a gain that cannot be obtained by
renaming cosine retrieval as engram binding. The theoretical source-existence
ceiling is 12/12 and 3/3 per domain, so the bars are reachable.

### 8.3 Stress tests

If G1-G5 pass, chained and enumeration results are reported but do not alter
the disposition:

- 8 chained queries, 16 required facts total;
- 4 enumeration queries, 16 required facts total;
- exact query completion counts and per-domain fact counts;
- direct-cosine top-eight control and paired gains/losses;
- output-rank distribution for every matched fact.

These are stress tests because one eight-item attractor output is not registered
as a solution to exhaustive multi-memory retrieval. They cannot rescue G3 or G4.

## 9. Dispositions

Apply the first matching disposition:

1. Any input, anchor, leakage, ordering, determinism, or PF failure:
   `INTEGRITY_STOP`.
2. G1 failure: `CARRIED_MEMORY_IDENTITY_FAILED`.
3. G2 failure: `NATURAL_CUES_NOT_BOUND`.
4. G3 failure: `LOOKUP_BINDING_INSUFFICIENT`.
5. G4 failure: `NO_BINDING_GAIN`.
6. G5 failure: `OUTPUT_BOUND_FAILED`.
7. All gates pass: `NATURAL_LANGUAGE_CUE_BINDING_CANDIDATE_CHARACTERIZED`.

Every non-integrity outcome is capped at `CHARACTERIZED`. A passing disposition
permits proposing a separately pre-registered live answer study. It does not
authorize that study, promotion, adoption, or production use.

## 10. Surrogate audit

| Observed pass | Property that can remain false | Required control or residual |
|---|---|---|
| Query reaches any stored code | The stored code is irrelevant | Sealed source-turn and required-term match |
| Eight outputs are unique | Required evidence is absent | Per-fact availability and 119-item source ceiling |
| Recurrence changes the cue | The change harms relevance | Initial-cue versus terminal paired identity report |
| Binder beats one-nearest episode | It is only a wider cosine list | Same-budget cosine top-eight control and G4 +2 bar |
| Lookup gate passes | Multi-memory questions work | Chained/enumeration stress distributions, no promotion claim |
| Offline facts are available | A model uses them correctly | PF10 and a separate live answer study |
| Same-store determinism passes | Other stores or wording generalize | Explicit single-store, single-model, single-seed limit |

## 11. Leakage boundary

The cue binder and Part 1 modules may import only general utilities, PS-001, the
episode database loader, the query manifest, and read-only query-vector cache.
They may not import or inspect:

- any `q_facts_key.md`;
- `answer_key_121.json` contents;
- rubric readers, criteria evaluators, atomic-item or targeted-item modules;
- evaluation outputs, scores, fact matrices, or prior selected source turns.

Measurement code is separate and may read the answer key only after a verified
preflight artifact. Enforce this with source grep, AST import traversal, runtime
path sentinels, and a planted forbidden-import test that must fail loudly.

## 12. Runtime, resources, and artifacts

Use fixed seed material inherited from PS-001, one process, and these environment
variables set to `1`: `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`,
`MKL_NUM_THREADS`, and `NUMEXPR_NUM_THREADS`.

Resource ceilings:

- 512 MiB estimated live NumPy arrays;
- 512 MiB observed process RSS above launch baseline;
- 10 minutes per grid cell;
- 60 minutes for complete Part 1;
- 10 minutes for Part 2 and relevance evaluation.

All retained outputs use UTF-8 with LF newlines, canonical sorted JSON, explicit
float serialization, overwrite refusal, and a manifest containing file bytes and
SHA-256. Run commands, source hashes, Python, NumPy, platform, PID, thread
settings, elapsed time, and memory are mandatory.

## 13. Tests and closeout

Before any output:

- unit-test fixed-order support, softmax, tie rules, inhibition, eight-round
  bounds, exact-code mapping, duplicate/spurious/cycle handling, and resource
  guards;
- prove PS-001 source is unchanged and its complete existing test suite passes;
- prove mechanism modules cannot parse a planted answer key;
- prove measurement refuses a missing or failing preflight artifact;
- prove artifact overwrite refusal and two-process deterministic comparison.

Closeout requires the pre-registration SHA in the report, all artifacts and
manifests committed, root README status and table updates, an AGENTS.md digest
of at most 400 characters, retrieval-ledger report and memory updates, ERRATA
review, the full test suite, a clean worktree, branch push, and a dedicated PR.

## 14. Explicit exclusions

PS-002 does not authorize:

- embedding requests or model generation;
- answer generation, scoring, a 35-turn ablation, or a 120-turn live run;
- changing PS-001 codes, recurrence, seed, dimensions, or normalization;
- using source turns, domains, facts, or rubrics inside the binder;
- tuning `(M, TAU)` on relevance labels;
- claiming biological replication of dentate gyrus, CA3, or hippocampus;
- promotion, adoption, deployment, or a production configuration change.

The only advancement path after a pass is a new pre-registration whose live
instrument includes the standing 35-turn ablation, deterministic prefix rerun,
three-pass blind scoring, and the measured 3.0-point instrument band.

---

*Registered prospectively on August 11, 2026. The author requested a separate
pre-registered natural-language cue-binding study after merging PS-001. The
implementation agent is authorized to execute only after a standalone
authorization binds this file's committed identity.*
