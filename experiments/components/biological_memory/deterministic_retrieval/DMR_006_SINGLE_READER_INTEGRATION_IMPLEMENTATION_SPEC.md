# DMR-006 - Single-Reader Integration Validation Specification

**Document type:** Prospective implementation and validation specification
**Status:** `DESIGN ONLY - NOT PRE-REGISTERED - NO IMPLEMENTATION OR RUN AUTHORIZED`
**New memory components:** None; validation of the frozen passing DMR stack
**Depends on:** DMR-001, DMR-004, DMR-005, and at least one independently
passing alternate route from DMR-002 or DMR-003
**Reference:** `DMR_ARC_IMPLEMENTATION_ROADMAP.md`
**Date:** August 11, 2026

## Complete Arc Roadmap

This roadmap is repeated in every DMR specification so that no stage can be
read as an isolated optimization.

### Arc Thesis

The system should reconstruct useful context through deterministic memory
operations, then give that context to one downstream language-model reader.
The reader is the consumer of recall, not the controller of recall. Query
embeddings and stored embeddings are permitted retrieval primitives; generated
intermediate language is not.

### Non-Negotiable Invariants

1. Exactly one generative inference call is permitted per answered user turn,
   and it occurs only after retrieval terminates.
2. The memory path is extractive and provenance-preserving. Stored episode text
   is immutable; no generated summaries or rewritten search queries enter it.
3. Retrieval state contains vectors, typed edges, hashes, scores, bitsets, and
   deterministic query features only. It contains no model-authored reasoning.
4. A small active foreground and the serialized reader budget are separate
   limits. The existing 32,000-character ceiling remains a matched experimental
   control, not a claim about brain capacity.
5. The answer key and rubric may measure retrieval but cannot form, rank, route,
   stop, or pack it.
6. Each study adds one component. A downstream stage cannot rescue a failed
   upstream mechanism by changing it in the same study.
7. Existing known corpora are diagnostic development sets. Confirmatory claims
   require a newly locked holdout whose answers remain sealed through retrieval.
8. Offline availability is not an answer verdict. Any delivery-changing stack
   must pass the required 35-turn ablation before a longer or live run.

### Ordered Studies

| Stage | One new component | Mechanical question | Required output | Binding stop |
|---|---|---|---|---|
| **DMR-001** | Online event-context formation | Can a label-blind deterministic encoder partition a conversation into nondegenerate events and store stable encoding context? | Frozen episode-to-event map, typed event records, encoding-context vectors, and formation report | Stop if event identity is unstable, collapses to singletons/one giant event, or cannot beat structural controls on sealed boundary evidence |
| **DMR-002** | Typed event-bound pattern completion | Given an unchanged direct seed, do `MEMBER_OF_EVENT` edges recover other elements of that encoded event better than generic adjacency or recursive cosine? | Frozen completion operator and matched-opportunity offline report | Stop on no broad gain, any targeted loss, cross-event contamination, or identity-equivalence to a control |
| **DMR-003** | Retrieved-context recurrence | Does reinstating an encoding-time context state cue useful unvisited events that fixed-query similarity chaining does not reach? | Frozen recurrence operator, state traces, cycle proof, and matched-budget report | Stop on no differentiated cue, no broad gain, any targeted loss, or recurrent/absorbing behavior |
| **DMR-004** | Deterministic query-obligation compiler | Can explicit lookup, conjunction, enumeration, history, and open-query obligations be represented without a model or answer-key labels? | Frozen compiler, obligation manifests, coverage/ambiguity report, and unsupported-query contract | Stop if compiler output is unstable, key-dependent, fails registered class coverage, or falsely marks open requests complete |
| **DMR-005** | Deterministic route and stopping controller | Can frozen obligations and evidence novelty switch among direct, event, and context routes without a second model call? | Frozen state machine, route traces, false-stop report, and call-count proof | Stop if routing is equivalent to fixed depth, false stops exceed the locked bar, unsupported queries are claimed complete, or any extra generation occurs |
| **DMR-006** | No new memory component; integration validation | Does the frozen stack improve reader answers when retrieval is completed before one reader call? | Offline gates, 35-turn ablation, then only if eligible a separately authorized longer/live run | Stop on any targeted reader regression, failure of broad/domain gates, nondeterminism, budget violation, or pre-reader generation |

### Dependency and Branch Order

1. Execute only one stage per `study/dmr-NNN-short-name` branch and pull request.
2. Complete mandatory Part 1 exploration before locking that stage's
   pre-registration. Commit the pre-registration before implementation.
3. Freeze every upstream artifact by content hash. A later study imports the
   frozen artifact and proves byte-identical reproduction before adding its one
   component.
4. If DMR-001 stops, DMR-002 through DMR-006 are blocked because there is no
   validated event substrate. If DMR-002 stops, DMR-003 may test context
   recurrence from DMR-001, but DMR-005 cannot claim an event-completion route.
5. DMR-006 begins only after all included routes pass their own offline gates.
   Its 35-turn ablation precedes any 120-turn or live run.

### Arc Success Claim

The strongest claim this arc can earn is narrow: on preregistered held-out
conversations, a deterministic multi-route memory path supplies better evidence
and reader answers than the frozen direct-retrieval control, without targeted
losses, domain losses, extra generation calls, or budget violations. It cannot
establish that the implementation is how a brain works.

## 1. Stage Question

Earlier program results repeatedly showed that evidence availability does not
guarantee a better answer. DMR-006 therefore adds no retrieval mechanism. It
tests whether the frozen deterministic stack improves the final reader under
the same model, prompt contract, seed, renderer, and 32,000-character ceiling.

The architectural boundary is explicit: all recall finishes first; the reader
is invoked once. This operationalizes the user's distinction between a
subconscious-like retrieval process and a downstream consumer, but it is an
engineering analogy, not a neuroscientific claim about consciousness.

## 2. Scientific Context

Limited active access and recoverable latent states motivate separating a small
retrieval foreground from what is eventually serialized
([Cowan et al., 2005](https://doi.org/10.1016/j.cogpsych.2004.12.001);
[Wolff et al., 2017](https://doi.org/10.1038/nn.4546)). Direct and
effortful/generative autobiographical retrieval can both precede report
([Harris & Berntsen, 2019](https://doi.org/10.1016/j.concog.2019.102793)). None
of these sources establishes an LLM context budget or says that a language model
should be called once. The one-reader boundary is the engineering thesis under
test.

## 3. Frozen Stack Contract

Before DMR-006 is locked, its manifest names exact SHAs for:

- episode store and source corpus;
- event former and event snapshot;
- every included alternate route;
- query-obligation compiler;
- deterministic controller;
- embedder model, call shape, cache, and sentinel vector;
- exact packer and renderer;
- reader prompt template, model artifact, runtime build, seed, and server flags;
- query set, fact key, scoring protocol, and numeric comparator specification.

DMR-006 cannot alter these components. A needed change sends work back to a new
upstream study rather than entering as an integration fix.

## 4. Runtime Boundary

The per-probe process is:

```text
1. Accept immutable user query.
2. Compile frozen QueryPlan.
3. Obtain query/obligation embeddings under the registered call shape.
4. Run frozen deterministic controller to a recorded stop reason.
5. Commit retrieval trace, selected identities, payload bytes, and digests.
6. Assert pre-reader generation call count equals zero.
7. Invoke the frozen reader exactly once with the serialized payload.
8. Commit raw answer before opening mechanism traces or score keys.
```

The reader cannot request tools, search, or additional memory. A retry caused by
transport failure invalidates the probe unless a pre-registered whole-arm rerun
rule applies. No response from the first call means `NO_ANSWER`; it is not
silently retried into a score.

## 5. Arms

### C0 - Frozen Direct Control

Checked out from the last accepted direct-retrieval control in a separate
worktree. It uses the same embedder, reader, prompt, renderer, exact character
budget, and scoring protocol. It contains no imports from DMR treatment modules.

### T1 - Frozen DMR Stack

Uses the exact passing DMR stack. Route labels, obligation status, controller
scores, and stop reasons are not shown to the reader; the reader sees only the
same evidence rendering and provenance fields available in C0. This prevents a
prompt-format explanation from masquerading as retrieval improvement.

### Optional Diagnostic Arms

No diagnostic arm enters live inference unless separately preregistered. Offline
identity ablations may compare fixed-depth and individual passing routes, but
DMR-006's reader comparison remains C0 versus one locked T1.

## 6. Budgets and Capacity

- `delivery_budget_chars = 32,000` is charged against exact serialized UTF-8
  character length in both arms.
- Complete block wrappers, provenance, separators, and metadata count.
- Oversize individual records follow one locked policy; silent truncation is
  forbidden.
- The treatment's active foreground and resolved-evidence caps remain frozen
  internal state limits. C0 need not mimic them because they are the treatment
  mechanism.
- Candidate work, vector operations, route calls, active occupancy, and wall
  time are reported separately from final characters.

The 32k limit is a comparability control. Passing under it does not imply a
human-like capacity, and failing to retrieve evidence that would fit is not a
capacity failure.

## 7. Evaluation Sequence

### Phase 0 - Corpus and Rubric Lock

Before any reader call, mechanically prove every scored fact is planted in a
user turn strictly before its probe. Lock query classes and score rules,
including numeric value equivalence.

### Phase 1 - Offline Gates

Run C0 and T1 retrieval only. Required strata include:

- easy direct lookup;
- within-event multi-element recall;
- context-bridge recall not solved by direct similarity;
- disconnected-domain routing, including the existing art diagnostic;
- targeted single-fact safety probes;
- explicit conjunction;
- finite enumeration without a false completeness claim;
- open query with an honest noncomplete stop;
- explicit history only if SUP-001 lineage is in the frozen stack.

T1 must improve broad packed evidence, recover the registered disconnected
domain, have zero targeted losses, have no domain regression, remain within the
exact budget, and make zero generative calls. Failing any binding offline gate
stops before reader inference.

### Phase 2 - Required 35-Turn Ablation

Build a new 35-turn minimum fixture whose plants and probes exercise every route
that T1 claims. The exact turn script, probe count, placements, and score bars
are locked after Part 1 but before inference. At minimum, the final fixture must
include direct-only success, event-route need, context-route need when included,
targeted controls, a disconnected-domain probe, and one unsupported/open query.

Run C0 and T1 from separate worktrees with `--parallel 1`, no speculative
decoding, fixed seed, one server slot, recorded build/model hashes, and explicit
UTF-8. Require the registered byte-identical seeded-prefix rerun before scoring.

If the reader/runtime does not reproduce, stop and characterize the instrument.
The prior 3.0-point band on a different 13-item instrument is not transferred as
a universal tolerance.

### Phase 3 - Longer or Live Run

No longer or live run is automatic. A passing ablation produces
`ELIGIBLE_FOR_SEPARATE_LIVE_DECISION`. A new run lock must name the intended
natural conversation population, duration, scoring, cost, privacy treatment,
and stop conditions. A 120-turn run still precedes any production adoption when
the program requires it.

## 8. Reader and Scoring Contract

### Answer Scoring

- Only content outside reasoning blocks is scoreable.
- Missing final answer is `NO_ANSWER` and scores zero.
- Every item has a rationale; conflicts block the commit.
- AI raters, if used, follow the repository scoring-integrity protocol with
  planted calibration and blind passes.
- All arm scores commit before mechanism logs open.

### Quantitative Values

The pre-registered comparator accepts exact text and equivalent integer/finite
decimal forms when value, sign, unit or currency marker, and surrounding factual
content agree. For example, a redundant decimal zero does not change a currency
value. The comparator does not silently perform unit conversion, percentage,
date/time, range, or paraphrase inference.

### Primary Reader Outcome

Use paired item outcomes, not total score alone:

- T1 gains over C0;
- T1 losses against C0;
- current/unchanged/history correctness where applicable;
- broad and per-domain correctness;
- unsupported-query attribution and abstention;
- fabricated facts and stale attributions.

Zero targeted losses is binding. A total gain cannot average away a regression.

## 9. Gates and Dispositions

Numeric gain bars are calibrated for reachability during Part 1 and locked in
the pre-registration:

| Gate | Executes before | Binding requirement |
|---|---|---|
| G0 Input lock | Any retrieval | Every stack, corpus, cache, prompt, runtime, key, and scorer hash matches |
| G1 Leakage/call purity | Treatment output access | No mechanism path to keys/rubrics and zero pre-reader generation calls |
| G2 Offline evidence | Any reader call | Broad gain, disconnected-domain recovery, zero targeted losses, no domain loss |
| G3 Budget/invariants | Any reader call | Exact payload <=32k; stable identities; no route/state violation |
| G4 Runtime determinism | Scoring | Registered seeded-prefix reproduction and call-count identity |
| G5 Reader utility | Longer/live decision | Registered paired gains, zero targeted losses, no domain loss, no fabrication/stale regression |
| G6 Procedural integrity | Report interpretation | Scores committed before mechanism logs; every artifact traceable to design anchor |

Dispositions:

- Any G0-G4 failure: `STOP_BEFORE_READER_VERDICT`.
- G5 failure: `RETRIEVAL_AVAILABLE_READER_NOT_SUPPORTED`.
- G0-G6 pass: `ELIGIBLE_FOR_SEPARATE_LIVE_DECISION`.
- No DMR-006 outcome directly authorizes adoption.

## 10. Surrogate Audit

| Metric | False-pass mode | Protection |
|---|---|---|
| Offline fact availability | Reader may ignore or misuse evidence | Binding 35-turn reader phase |
| Reader total | Gains can hide targeted losses or noise | Paired per-item loss gate and determinism check |
| Art recovery | One diagnostic bundle can be overfit | New disconnected-domain holdout and all-domain table |
| 32k compliance | A large compliant payload can still be badly selected | Required evidence and reader outcomes |
| One generation call | One reader can still internally reason poorly | Answer scoring; call count supports architecture only |
| Stop reason | `FINITE_MATCHED` can be a false support match | Sealed evidence and reader false-stop analysis |
| Numeric exactness | Serialization can disagree while value is correct | Pre-locked value comparator |

## 11. Stage Preflight

**State:** `NOT RUN`.

### Part 1 Deliverables

- Falsifiable identity for C0, T1, every route, renderer, prompt block, call
  counter, reader, and scorer.
- Name-to-behavior proof that C0 is the claimed prior mechanism and no current
  treatment code escapes into its worktree.
- Full distributions for candidates, active state, characters, stop reasons,
  evidence, answer outcomes, and latency.
- Intended-length traces for route loops, foreground saturation, no-novelty,
  unsupported queries, and reader nonresponse.

### PF1-PF10

| Check | DMR-006 required artifact |
|---|---|
| PF1 | Complete input/runtime/cache/key/scorer manifest with paths, hashes, counts, and encodings |
| PF2 | Executed behavioral identity report for every named stack component and prompt block |
| PF3 | Gate-order tests plus git anchors proving G0-G4 precede scoring and G5 precedes mechanism-log opening |
| PF4 | Reachability report for every stratum, evidence bar, paired-gain bar, budget, and stop condition |
| PF5 | Content/query/design hashes only; no UUID/timestamp/path comparison keys |
| PF6 | C0 and every T1 upstream artifact reproduce by identity, payload bytes, and digest |
| PF7 | 35-turn real-trace proof for every feedback/absorbing state in the frozen controller |
| PF8 | Explicit list of failures the 35-turn ablation can detect and long-run failures it cannot |
| PF9 | Completed surrogate table with planted false-pass fixtures for availability, totals, call counts, and numeric format |
| PF10 | Exact statement that availability is nonverdictive and a separate live decision follows only after pass |

## 12. Commit and Artifact Order

The future DMR-006 branch preserves this order:

1. Part 1 exploration and design decision.
2. Pre-registration with no implementation files.
3. Implementation/integration harness and tests.
4. Passing preflight artifacts.
5. Calibrated settings and exact 35-turn run lock.
6. C0 raw answers and scores.
7. T1 raw answers and scores.
8. Mechanism traces unsealed and analyzed.
9. Report, root README, AGENTS digest, ERRATA if needed, and memory update.
10. Pull request with no automatic live/adoption claim.

## 13. Verification Contract for Later Integration

Tests must enforce separate control worktree/import roots, dirty-tree rejection,
module SHA assertions, exact prompt serialization, exact 32k charging, planted
key leakage failure, call interception, one-reader maximum, no retry, seeded
prefix replay, raw-before-score ordering, score-before-log ordering, quantitative
value equivalence, `NO_ANSWER`, every stop reason, and full artifact hashes.

## 14. Decision

DMR-006 is the first point at which the arc can answer whether deterministic
context reconstruction helped the model answer. A pass supports a separately
authorized naturalistic live study. A failure identifies whether the break was
formation, route reach, controller stopping, packing, or reader use because each
boundary is independently committed. It must not be repaired by adding a second
language-model retrieval call under the same thesis.

## Sources

- [Cowan et al. (2005)](https://doi.org/10.1016/j.cogpsych.2004.12.001)
- [Wolff et al. (2017)](https://doi.org/10.1038/nn.4546)
- [Harris & Berntsen (2019)](https://doi.org/10.1016/j.concog.2019.102793)
