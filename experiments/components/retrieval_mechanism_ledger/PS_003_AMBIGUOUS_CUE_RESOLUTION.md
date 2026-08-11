# PS-003 - Ambiguous Natural-Language Cue Resolution

**Type:** Pre-registered offline component study
**Date:** August 11, 2026
**Branch:** `study/ps-003-ambiguous-cue-resolution`
**Status:** PRE-REGISTERED - IMPLEMENTATION AND OUTCOME ACCESS PROHIBITED UNTIL AUTHORIZATION
**Predecessor:** PS-002 natural-language cue binding
**Outcome ceiling:** `CHARACTERIZED`

## 1. Motivation

PS-002's strongest label-blind cell converted 24 sealed natural-language query
vectors into 190 stored-code terminals across 192 rounds. One mixed cue entered
a two-cycle and one converged to a spurious fixed point. Because the registered
property required eight safe identities for every query, PS-002 stopped before
relevance measurement.

PS-003 adds exactly one component: a deterministic ambiguity resolver. It keeps
one attractor equal to one memory. For each proposed output, the resolver forms
a family of local probes around the unchanged PS-002 mixed cue and accepts an
episode only when every probe converges to the same exact stored PS-001 code.
Unsafe or disagreeing probe families are rejected, never replaced by a cosine
result, and the carried PS-002 inhibition rule advances to another attempt.

The study asks:

> Can deterministic local basin consensus reject PS-002's ambiguous mixed cues
> and still return eight independently certified stored memories per sealed
> natural-language query?

## 2. Integrity anchors and immutable inputs

The following byte hashes are authoritative. A mismatch stops execution.

| Input | Bytes | SHA-256 |
|---|---:|---|
| PS-001 component source, `src/retrieval_mechanism_ledger/ps001.py` | 21,048 | `BC29DC0F0D3A443D640572C88C3E10DF08C6277DDF2326C689D9BD0B9ECEF172` |
| PS-002 component source, `src/retrieval_mechanism_ledger/ps002.py` | 9,233 | `866429BF10096756340B536F2B952DD5D95F6979F4D145120FE42B256D7D5489` |
| PS-001 report | 11,138 | `FD7DF65335B1CE60822CA5114C1A5B832960D6F10659A6E9776564728DE29412` |
| PS-002 report | 8,854 | `FF2D22C3CEF426332E0BE0784F02B2D245C901F789B047A7CEA67ABD63906B35` |
| PS-001 first-process exploration | 935,053 | `A78922CA25F0CA5027F695B2A12E8059EE83597366F1B87ECF7B7EF6C5FFDC1D` |
| PS-002 first-process exploration | 13,858 | `C7B12A4E3250366D7FC37765A73E783FB688991900B4ABB47BD50A3DEF4A3825` |
| PS-002 two-process comparison | 488 | `128242740C0AEA40E03759667BFB17F0507228E8505F374ABDD34A5C3DD9142C` |
| 119-episode database | 1,978,368 | `5DA47EA3FC2C8E3DCC50FA380FF65202D82557905D9976117E9E5D82E55C1C41` |
| Sealed 121-turn query manifest | 4,231 | `AE950FDA20DCE9F519F31EE2670A815A5599648CAB618D42309DB7E3F23D36F4` |
| Sealed query-vector cache | 249,856 | `D9741EDB0545D8CFE050663340599A31813D6025C38F0467E0EC7671573A1E6A` |
| Query-vector capture manifest | 17,131 | `2C24EA75D7551BEB6658D8B9208225B985E25A9111CFD3766EC4F7980A7F18E4` |
| Measurement-only answer key | 9,832 | `2D43A31D3C04F4AD690FF2910ABDE71F508A3F6CE776545A9F2B16F90FAE5320` |

The population is the same 119 normalized source-turn 1-119 episodes and 24
`c121_l` queries used by PS-002, in their committed order. PS-003 makes zero new
embedding requests and zero model-generation calls.

## 3. Carried mechanisms

PS-003 must import and execute PS-001 and PS-002 without changing either source
file. It carries:

```text
D_CODE = 4096
K_ACTIVE = 41
PROJECTION_SEED = 0448cb7290b285bf85aa856004bd6ccbe8124aa8e3f83eaaa0225519dd626362
SUPPORT_WIDTH = 4
TEMPERATURE = 0.025
TARGET_OUTPUTS = 8
```

The `(4, 0.025)` support cell is fixed prospectively from PS-002's strongest
mechanical cell; it is not reselected in PS-003. Before every PS-003 cell, the
runner must reproduce:

- PS-001 mechanism digest
  `0D45DDD45980DBF3989A543136BAD52D4F743F650F3C0AF76E370F049B6C80CC`;
- PS-001 code-sequence SHA-256
  `A8D1364A58DE6D6C70DB2DD771BA96E59FCF931D36CFB28EA69C780B55E3A3B8`;
- `119/119` stored PS-001 fixed points;
- PS-002 mechanism digest
  `CFCA813A79EE96EE2949E9F567F9C5360ACB30D410E37AFD847EF65D5666E15C`;
- PS-002 deterministic artifact-sequence digest
  `DF47BBBC1E6B7A21BB8EC48BF81D7661B494FD693EA0905A544874CA142D9194`;
- the exact strongest-cell cycle cue
  `BB2CCCA6BAAFA7920E0E112CC4A34ADED69C3B1D7E5370F52E77C33BFCADA256`;
- the exact strongest-cell spurious cue
  `DAF89FD2E81596C34E742709E811B34D860E3C862A5337F224729F33DA5AD662`.

Any failure stops PS-003. Repair or recalibration of either carried component is
out of scope.

## 4. The one new component

### 4.1 Behavioral identity

In one falsifiable sentence:

> Given one sealed normalized query vector, the ambiguity resolver repeatedly
> forms the carried PS-002 four-support cue, recalls a deterministic local probe
> family through unchanged PS-001 recurrence, and emits an identity only when
> every probe reaches the same exact new stored code.

### 4.2 Base mixed cue

For each attempt, compute semantic support and uninhibited candidates exactly as
PS-002 Section 4.3 with `M=4` and `TAU=0.025`. Let `g` be that carried float64
field and `pi` be all 4,096 field indices ordered by descending field value with
unit index resolving exact ties. The base cue is the first 41 units in `pi`.

No source turns, domains, fact IDs, required terms, rubrics, scores, or answer
keys enter this operation.

### 4.3 Deterministic local probe family

One registered cell supplies probe count `P` and swap count `S`. Probe zero is
the base cue. For each probe `p` from 1 through `P-1`, copy the base cue and, for
each `j` from 0 through `S-1`, perform:

```text
deactivate pi[40 - ((p - 1) * S + j)]
activate   pi[41 + ((p - 1) * S + j)]
```

The registered grid never makes either index cross its side of the 41-unit
boundary. Every probe therefore has exactly 41 active units. Run unchanged
PS-001 synchronous recurrence independently from every probe.

### 4.4 Consensus, rejection, and inhibition

An attempt is accepted only if all `P` recalls:

1. terminate without a cycle or runtime guard;
2. terminate at an exact stored PS-001 code;
3. terminate at the same code identity;
4. identify an episode not previously emitted for this query.

On acceptance, emit that one identity and inhibit its episode index. If any
condition fails, emit nothing and inhibit only the highest-support candidate in
the attempt, exactly as PS-002 does after a failed round. A rejected family can
never contribute an identity, even if some probes reached stored codes.

Continue until eight identities have been accepted or exactly 16 attempts have
executed. Exhaustion returns fewer than eight identities and fails cell
eligibility. There is no cosine fallback, singleton-code fallback, majority
vote, label-dependent retry, or relaxation after a rejection.

## 5. Registered Part 1 grid and selection

Part 1 runs exactly four cells in row-major order:

```text
P in {3, 5}
S in {1, 4}
```

Each cell runs all 24 sealed queries for at most 16 attempts per query. The
answer key may not be imported, opened, parsed, or used in selection. The input
verifier may hash it without parsing it.

A cell is eligible only if:

- all 24 queries emit exactly eight unique identities within 16 attempts;
- every emitted identity came from a unanimous accepted family;
- no probe hits a runtime guard;
- every cue and terminal state has exactly 41 active units;
- all numeric values are finite;
- the two carried `h121_l02` unsafe base cues are encountered with their exact
  identities, rejected, and emit no identity;
- no rejected family contributes an output.

Among eligible cells, select mechanically by:

1. greatest `S`;
2. greatest `P`;
3. fewest total attempts;
4. row-major order.

If no cell is eligible, disposition is `AMBIGUOUS_CUES_UNRESOLVED`; stop before
Part 2 and before opening measurement labels.

## 6. Part 1 exploration requirements

Part 1 must retain and commit:

- every semantic support and candidate order;
- every attempt, field identity, base cue, perturbation identity, and probe;
- complete recurrence traces for all probes;
- accepted, disagreement, spurious, cycle, duplicate, and exhausted counts;
- attempts and probe recalls per accepted output;
- emitted-identity frequencies and unused-memory counts;
- exact treatment of the two carried unsafe cues;
- all distributions, including degenerate and absorbing states;
- selected-cell identity under Section 5;
- source hashes, command, environment, PID, Python, NumPy, wall time, estimated
  arrays, and RSS;
- zero embedding requests, zero generation calls, leakage audit, and planted
  forbidden-path failure;
- a byte-hashed artifact manifest.

Repeat the complete exploration in a fresh process. Canonical outputs excluding
explicit process metadata and wall/RSS fields must match byte-for-byte.

## 7. Final design lock

After a passing Part 1 is committed, a standalone final-design revision records
only the mechanically selected `(P, S)` cell, its committed artifact and digest,
the unchanged gates below, and whether Part 2 is authorized. It may not inspect
or report labels, source turns, domains, fact IDs, or relevance. It must be
separately authorized and committed before Part 2 code.

## 8. Preflight

### 8.1 Part 1 - empirical characterization

Sections 5 and 6 are the mandatory Part 1 exploration. It must test the
behavioral identity on all 24 real queries, verify that `consensus`, `rejection`,
`inhibition`, `probe`, and `attempt` match their executed behavior, report full
distributions, and retain all unsafe, disagreeing, duplicate, and exhausted
traces. A label-blind selected cell is required to continue.

### 8.2 Part 2 - PF1-PF10

| Check | Required executed evidence |
|---|---|
| PF1 inputs | Hash, byte count, schema, row count, vector shape, and content count for every Section 2 input |
| PF2 identity | Reproduce both carried digests and execute the selected resolver on all 24 committed queries |
| PF3 ordering | A planted sentinel proves labels cannot be parsed before selected-artifact verification and all gates execute before relevance output |
| PF4 reachability | Verify all 24 required fact sets exist in eligible earlier turns; lookup ceiling 12/12, per-domain ceiling 3/3, output capacity eight |
| PF5 stable keys | Query-text, episode-content, code, cue, and terminal SHA-256 plus fact IDs only; no generated IDs, paths, or timestamps compare conditions |
| PF6 reproduction | Reproduce the committed PS-001, PS-002, selected-cell, and two-process digests exactly |
| PF7 feedback | Independently replay every selected-cell probe through full recurrence and retain cycle/spurious absorbing witnesses |
| PF8 adequacy | State that 24 queries cover lookup, two-memory, and four-memory cues on this one store, but not other language, stores, seeds, or drift |
| PF9 surrogate | Compare direct cosine, PS-002 base cue, accepted consensus, and final output; safe stored identity is not relevant binding |
| PF10 live requirement | State that offline evidence availability is not an answer verdict; PS-003 authorizes no generation or live score |

Every item must name an executed test and committed artifact. Prose-only or
assumed checks fail.

## 9. Relevance evaluation and ordered gates

Only after Part 1, final-design lock, authorization, and PF1-PF10 pass may a
separate measurement module parse `answer_key_121.json`.

Use PS-002's exact same-serialized-episode, case-insensitive required-term and
source-turn matching rule. Report every required fact, matching episode, rank,
direct-cosine top-eight control, carried PS-002 base result, and resolver result.

Execute gates in order and stop at the first failure:

| Gate | Binding bar | Failure disposition |
|---|---|---|
| G1 carried identity | PS-001 and PS-002 digests exact; 119/119 fixed points | `CARRIED_MECHANISM_IDENTITY_FAILED` |
| G2 safe resolution | Selected cell meets every Section 5 rule and PF7 replay | `AMBIGUOUS_CUES_UNRESOLVED` |
| G3 lookup binding | At least 9/12 lookup facts available and at least 2/3 in each of four domains | `LOOKUP_BINDING_INSUFFICIENT` |
| G4 baseline differentiation | Lookup count at least direct-cosine top-eight +2, with no domain below cosine | `NO_BINDING_GAIN` |
| G5 bounded output | Every query emits exactly eight unique identities with no label-dependent retry | `OUTPUT_BOUND_FAILED` |

If G1-G5 pass, report but do not gate the 8 chained queries (16 facts) and 4
enumeration queries (16 facts), including exact completion counts, domain
counts, output ranks, paired gains, and losses. These stress tests cannot rescue
a failed lookup gate.

## 10. Dispositions

Apply the first matching disposition:

1. Input, anchor, leakage, ordering, determinism, or PF failure:
   `INTEGRITY_STOP`.
2. G1 failure: `CARRIED_MECHANISM_IDENTITY_FAILED`.
3. G2 failure: `AMBIGUOUS_CUES_UNRESOLVED`.
4. G3 failure: `LOOKUP_BINDING_INSUFFICIENT`.
5. G4 failure: `NO_BINDING_GAIN`.
6. G5 failure: `OUTPUT_BOUND_FAILED`.
7. All gates pass: `AMBIGUOUS_CUE_RESOLUTION_CANDIDATE_CHARACTERIZED`.

Every non-integrity outcome is capped at `CHARACTERIZED`. A pass permits
proposing a separate live answer study; it does not authorize one.

## 11. Surrogate audit

| Observed pass | Property that can remain false | Required control or residual |
|---|---|---|
| All probes reach one stored code | The code is irrelevant | Sealed fact availability after label lock |
| A family is unanimous | Its probes are too similar to test a basin | Registered 1- and 4-swap distributions; no generalization claim |
| Unsafe cues are rejected | Eight safe outputs cannot be completed | Binding 16-attempt output gate |
| Eight outputs are unique | Required evidence is absent | Per-fact and per-domain availability |
| Resolver beats PS-002 mechanics | It only extends the cosine-ranked search | Same-budget cosine top-eight and binding +2 G4 |
| Offline facts are available | A model uses them correctly | PF10; separate live answer study |
| Same-store determinism passes | Other wording or stores generalize | Explicit single-store, model, and seed limit |

## 12. Leakage, runtime, and resources

Mechanism and Part 1 code may import only general utilities, PS-001, PS-002,
the episode loader, query manifest, and read-only query cache. They may not
import or inspect any answer key, `q_facts_key.md`, rubric, criteria evaluator,
atomic-item module, targeted-item module, prior relevance output, or score.
Enforce this by source grep, AST import traversal, runtime path sentinels, and a
planted forbidden import that fails loudly.

Use one process and inherited fixed seed material. Set `OMP_NUM_THREADS`,
`OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`, and `NUMEXPR_NUM_THREADS` to `1`.
Resource ceilings are 512 MiB estimated live NumPy arrays, 512 MiB RSS growth,
10 minutes per cell, 60 minutes for Part 1, and 10 minutes for Part 2.

Artifacts use explicit UTF-8, LF, canonical sorted JSON, finite float values,
overwrite refusal, and byte/SHA-256 manifests. Runtime metadata must include
command, source hashes, Python, NumPy, platform, PID, thread settings, elapsed
time, and memory.

## 13. Tests and closeout

Before retained output, test probe construction, tie rules, exact active count,
unanimous acceptance, every rejection path, inhibition, attempt/output bounds,
carried identities, leakage, resource guards, overwrite refusal, and two-process
determinism. Prove PS-001 and PS-002 sources remain byte-identical and their
focused tests pass.

Closeout requires the pre-registration SHA in the report, artifacts committed,
root README status and table updates, an AGENTS digest of at most 400 characters,
retrieval-ledger and memory updates, ERRATA review, full-suite verification,
clean worktree, branch push, and a dedicated chained pull request.

## 14. Explicit exclusions

PS-003 does not authorize embedding requests, generation, scoring, a 35-turn
ablation, a 120-turn live run, changes to PS-001 or PS-002, majority-vote or
cosine fallback, label-dependent retries, relevance tuning, biological
replication claims, promotion, adoption, or production changes.

---

*Registered prospectively on August 11, 2026. The author selected the
one-attractor/one-memory design and authorized deterministic multi-probe
consensus as the PS-003 architecture. Implementation remains prohibited until a
standalone authorization binds this file's committed identity.*
