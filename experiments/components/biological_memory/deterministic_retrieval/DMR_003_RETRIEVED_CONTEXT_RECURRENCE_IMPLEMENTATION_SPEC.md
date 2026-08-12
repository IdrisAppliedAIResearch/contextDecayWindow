# DMR-003 - Retrieved-Context Recurrence Implementation Specification

**Document type:** Prospective implementation specification
**Status:** `DESIGN ONLY - NOT PRE-REGISTERED - NO IMPLEMENTATION AUTHORIZED`
**One proposed component:** `RetrievedContextRecursor`
**Depends on:** A passing, frozen DMR-001 event/context snapshot; DMR-002 is
carried only if it independently passed
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

E006 already implemented a mathematically corrected recursive cue: it blended
the original query with a running mean-derived state from retrieved episode
embeddings. It improved broad availability but never reached art and did not
have targeted traces. DMR-003 does not repeat that experiment. It asks whether
retrieving an event can reinstate a context vector stored when that event was
encoded, and whether that encoding context produces a differentiated next cue.

The distinction is mechanical:

- E006 state was constructed from **what retrieval had just returned**.
- DMR-003 state comes from **what surrounded the event at encoding**, frozen
  before any query exists.

## 2. Scientific Claim and Engineering Hypothesis

Free-recall transitions show temporal organization
([Kahana, 1996](https://doi.org/10.3758/BF03197276)). The CMR model formalizes a
process in which a recalled item reinstates context, and that context cues later
recall ([Polyn, Norman & Kahana, 2009](https://doi.org/10.1037/a0014420)). Neural
context reinstatement has been associated with successive recall of neighboring
study items ([Manning et al., 2011](https://doi.org/10.1073/pnas.1015174108)),
and event boundaries structure the temporal context reinstated during recall
([Lohnas et al., 2023](https://doi.org/10.1037/xge0001354)).

The engineering hypothesis is that frozen DMR-001 `encoding_context` vectors
contain useful information not reducible to direct query similarity or the mean
of retrieved content. The exact vector interpolation below is not supplied by
the empirical studies.

## 3. Scope

### Included

- Start from byte-identical frozen direct seeds in every arm.
- Select event representatives under one locked rule.
- Reinstate each selected event's pre-query encoding-context vector.
- Blend that context with an immutable original-query anchor.
- Retrieve only unvisited event representatives at a bounded depth.
- If DMR-002 passed, apply its frozen completion after an event is selected in
  both control and treatment where applicable; do not change it.

### Excluded

- Query text generation, language-model routing, query obligations, adaptive
  stopping, event reformation, answer-key routing, consolidation, plasticity,
  and reader inference.
- Treating the newest hit mean as encoding context.

## 4. Intended Future Interface

```text
src/biological_memory/retrieved_context.py
```

```python
class RetrievedContextRecursor:
    def search(
        self,
        *,
        query_hash: str,
        query_vector: Float32Vector,
        direct_seeds: Sequence[RankedEpisode],
        event_snapshot: EventContextSnapshot,
        event_index: EventPrototypeIndex,
        max_depth: int,
        per_depth: int,
    ) -> ContextSearchTrace: ...
```

It receives no query text, key, rubric, model client, reader, or stopping
callback. It always executes the registered fixed depth unless candidates are
exhausted or a mechanical fault stops it. Adaptive control belongs to DMR-005.

## 5. Mechanical Recurrence

### 5.1 Canonical Event Representative

For each event `E` and query `q`, its delivery representative is the member with
the best frozen **original-query** direct rank; ties use event position then
content hash. This reuses the carried direct score and does not introduce a
new learned selector.

The event search index ranks event prototype vectors, not every episode. An
event is visited at most once.

### 5.2 State Update

Let `q_hat` be the normalized original query vector, `r_d` the normalized
retrieval context, and `c(E)` the frozen normalized encoding context of selected
event `E`.

```text
r_0 = q_hat

cue_d = normalize(goal_weight * q_hat + context_weight * r_d)
hits_d = top_unvisited_events(cue_d, per_depth)

selected_context_d = normalize(
    sum(rank_weight(i) * c(E_i) for E_i in hits_d)
)

r_(d+1) = normalize(
    persistence * r_d + update_weight * selected_context_d
)
```

All vectors and operations use a locked dtype and accumulation order. The
original query weight must remain strictly positive at every depth. Parameters,
rank weighting, tie rules, and handling of a zero-norm context are locked after
Part 1 and before implementation.

### 5.3 Stopping and Fault States

DMR-003 is not yet a sufficiency controller. It stops only on:

- registered `max_depth` reached;
- no unvisited event remains above the locked retrieval floor;
- no valid context vector can be formed;
- exact event-set repetition or cue-hash repetition, which is a registered
  recurrence fault rather than successful completion.

The visited set makes event selection finite, but that alone does not prove the
state is useful. Every early stop and fault is reported.

## 6. Matched Arms

All arms share direct seeds, candidate opportunity, packing, character budget,
and any independently passing DMR-002 completion.

| Arm | Recurrent state | Next cue |
|---|---|---|
| `C_DIRECT` | None | No recurrence |
| `C_E006` | Corrected running state derived from retrieved hit embeddings | Original query plus hit-derived state |
| `C_SHUFFLED` | Encoding contexts reassigned among events within session before queries | Original query plus mismatched encoding context |
| `T_CONTEXT` | Correct event's frozen encoding context | Original query plus reinstated encoding context |

`C_SHUFFLED` tests whether any added vector diversity helps. The permutation is
seeded and locked before outcomes. If shuffled and true context perform alike,
the encoding relation has not earned causal credit.

## 7. Part 1 Exploration Before Pre-Registration

The future branch must characterize:

1. Norms, pairwise similarities, and effective rank of DMR-001 event contexts.
2. Correlation between event prototype and encoding context; if they are nearly
   identical, the proposed mechanism may add no information.
3. Cue-to-query cosine, cue-to-prior-cue cosine, ranking changes, visited-event
   counts, and newly admitted candidates at each proposed depth.
4. Parameter regions producing no cue change, query loss, oscillation,
   one-session attraction, or immediate candidate exhaustion.
5. Differences among true, shuffled, and hit-mean context on real traces.
6. Fixed-depth achievability for broad and targeted gates.

If `encoding_context` is algebraically or behaviorally equivalent to event
prototype or hit mean, stop before pre-registration; renaming the vector does
not create a mechanism.

## 8. Prospective Measures and Gates

### Required Measures

- Per-depth cue hashes and cosine drift from `q_hat`.
- Full event and episode ranking at each depth.
- New event, new episode, required-fact, and domain admissions per depth.
- Candidate and packed availability by query and domain.
- True-versus-shuffled context differences.
- Revisit, cycle, zero-norm, exhausted, and max-depth rates.
- Exact characters after the frozen packer.

### Binding Gate Meanings

Numeric thresholds are calibrated in Part 1 and locked before implementation:

| Gate | Required meaning |
|---|---|
| G1 Reproduction | Direct, E006, optional DMR-002, and packer controls reproduce by identity and digest |
| G2 Differentiated cue | True encoding context changes rankings and admitted identities beyond E006 and shuffled controls |
| G3 Broad availability | `T_CONTEXT` improves the registered packed broad evidence measure |
| G4 Target safety | Zero per-query targeted losses against the strongest frozen carried control |
| G5 Domain safety | No domain regression and the preregistered disconnected-domain recovery requirement is met |
| G6 Recurrence safety | Zero registered cycles, absorbing routes, nonfinite states, or unreported early stops |

No targeted trace means G4 is not evaluable and the study cannot promote, even
if broad availability improves.

## 9. Surrogate Audit

| Metric | False-pass mode | Protection |
|---|---|---|
| Cue drift | A wildly changed cue can be worse | Require required-evidence gains and target safety |
| New candidates | New identities can all be irrelevant | Fact/domain measures after sealed lookup |
| True beats E006 | Added context may only exploit a different scale | Include shuffled-context control and exact normalization |
| No cycles | Finite visited set can terminate a useless search | Separate safety from usefulness gates |
| Broad gain | One query/domain can carry the aggregate | Per-query loss and domain gates |
| Packed gain | More characters can drive it | Exact matched budget and opportunity |

## 10. Stage Preflight

**State:** `NOT RUN`.

### Part 1 Deliverables

- Falsifiable identity describing exactly how a selected event's frozen context
  alters the next event ranking.
- Name checks for encoding context, reinstatement, recurrence, event
  representative, cue, visit, and depth.
- Full per-depth distributions.
- Real-trace demonstrations of no-change, query-loss, cycle, exhaustion, and
  max-depth states.

### PF1-PF10

| Check | DMR-003 required artifact |
|---|---|
| PF1 | Hash manifest for event contexts, query vectors, Gram/index data, controls, keys, and packer |
| PF2 | Identity traces proving encoding context predates queries and differs from hit-mean state |
| PF3 | Test proving control reproduction and recurrence safety gates execute before held-out outcomes |
| PF4 | Achievability matrix over all locked weights, depths, opportunities, domains, and bars |
| PF5 | Stable event/content hash and cue digest proof |
| PF6 | Exact E006 and carried-control reproduction before treatment output opens |
| PF7 | Intended-length cycle, revisit, zero-norm, and absorbing-state report on real traces |
| PF8 | State what fixed-depth offline testing cannot say about adaptive routing or long conversations |
| PF9 | Completed surrogate table with observed true-versus-shuffled residuals |
| PF10 | State that availability is not a verdict and no reader/live run is authorized |

## 11. Verification Contract for Later Implementation

Tests must cover equation-level agreement with an independent vector route,
locked dtype/order, query-anchor positivity, event representative ties, visited
filtering, shuffled assignment, zero norm, nonfinite input, cue repetition,
depth zero, candidate exhaustion, exact traces in two processes, leakage, and
zero generation calls. A full-rank comparison, not top-k agreement alone, is
required for recurrence math preflight.

## 12. Decision

If DMR-003 passes, freeze its recurrence and traces for DMR-004 and DMR-005. If it stops,
the result means stored encoding context did not improve this text retrieval
problem under the registered translation. It does not mean human context
reinstatement is absent. Do not add an LLM-written intermediate query as a
repair; that is outside the arc thesis.

## Sources

- [Kahana (1996)](https://doi.org/10.3758/BF03197276)
- [Polyn, Norman & Kahana (2009)](https://doi.org/10.1037/a0014420)
- [Manning et al. (2011)](https://doi.org/10.1073/pnas.1015174108)
- [Lohnas, Healey & Davachi (2023)](https://doi.org/10.1037/xge0001354)
