# DMR-005 - Deterministic Route and Stopping Controller Implementation Specification

**Document type:** Prospective implementation specification
**Status:** `DESIGN ONLY - NOT PRE-REGISTERED - NO IMPLEMENTATION AUTHORIZED`
**One proposed component:** `DeterministicRetrievalController`
**Depends on:** Passing frozen DMR-004 plans and whichever of DMR-002/DMR-003
independently passed; DMR-001 is required for either biological route
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

DMR-002 and DMR-003 use fixed opportunities/depth so their causal mechanisms
can be isolated. DMR-005 asks whether a deterministic state machine can avoid
unnecessary expansion on easy queries, continue on unresolved hard queries, and
stop without another language model deciding whether enough was remembered.

The controller consumes a frozen DMR-004 query plan. It cannot invent new goals
or reinterpret an unsupported query.

## 2. Scientific Claim and Engineering Hypothesis

Top-down goal states can precede and bias retrieval
([Polyn et al., 2005](https://doi.org/10.1126/science.1117645);
[Tomita et al., 1999](https://doi.org/10.1038/44372)), neocortical projections
can mediate retrieval control
([Rajasethupathy et al., 2015](https://doi.org/10.1038/nature15389)), and
controlled retrieval and selection have dissociable signatures
([Badre et al., 2005](https://doi.org/10.1016/j.neuron.2005.07.023)).
Direct and effortful/generative autobiographical retrieval are both observed,
although they should not be assumed to be wholly separate cognitive systems
([Harris & Berntsen, 2019](https://doi.org/10.1016/j.concog.2019.102793)).

The engineering hypothesis is that a finite deterministic state machine can
operationalize a cheap direct route followed by event/context search only when
mechanical evidence remains unresolved. The cited work does not establish this
state machine, its route order, or its stopping predicates.

## 3. Scope

### Included

- Direct route first on every query.
- Optional event route only if DMR-002 passed and an active seed has unexpanded
  event members.
- Optional context route only if DMR-003 passed and unvisited events remain.
- Deterministic obligation-evidence matching for explicit lookup/conjunction
  plans.
- Novelty-bounded search for enumeration and open plans, without a completeness
  declaration.
- Separate active foreground, resolved-evidence archive, and delivery packing.
- Exact route, support, replacement, and stop traces.

### Excluded

- Generated cues or summaries, model reranking, model sufficiency checks,
  learned routing, hidden answer-key facts, route retuning, reader inference,
  accessibility writes, and consolidation.
- Claiming an unbounded or open query has been completely answered.
- Repairing a stopped upstream component inside this controller.

## 4. Intended Future Interface

```text
src/biological_memory/retrieval_controller.py
```

```python
class DeterministicRetrievalController:
    def retrieve(
        self,
        *,
        plan: QueryPlan,
        query_vector: Float32Vector,
        frozen_routes: FrozenRouteSet,
        delivery_budget_chars: int,
    ) -> ControlledRetrievalResult: ...
```

The controller receives only route interfaces whose design hashes are pinned in
its configuration. Missing or mismatched required routes fail at construction;
the controller does not silently fall back to current code.

## 5. Evidence-Matching Predicate

This predicate is a control signal, not answer scoring.

For each explicit lookup/conjunct obligation, embed its exact source substring
under the pinned query-embedding call shape. A candidate evidence record can
support the obligation only if:

1. its cosine to the obligation-span embedding reaches the locked support
   floor;
2. every explicit hard anchor in the span that also occurs in the full query is
   present in the candidate's immutable text under locked normalization; and
3. the candidate has not been assigned to an incompatible obligation.

Hard anchors are syntax-defined quoted strings, numeric/date/unit tokens, and
unambiguous capitalized spans. They are not extracted from answer keys.

The controller builds the bipartite obligation/evidence graph and selects a
deterministic maximum-cardinality assignment, maximizing total support score
with content-hash tie breaks. A query is `FINITE_MATCHED` only when every
finite `ONE_EVIDENCE` obligation has an assignment.

### Limits

- Semantic support can exist without lexical anchors and be missed.
- High cosine plus anchors can still be topically related rather than
  answer-bearing.
- A finite enumeration states how many answers are requested but not how to
  prove distinct answer content without extraction. Therefore enumeration can
  reach `ENUMERATION_TARGET_EVIDENCE`, never `FINITE_MATCHED`.
- An open plan can reach `OPEN_NOVELTY_EXHAUSTED`, never `FINITE_MATCHED`.

These distinctions are serialized in the stop reason; user-facing code may not
collapse them to one `complete=True` flag.

## 6. State Machine

```text
START
  -> run DIRECT
  -> update foreground, evidence archive, and support assignment

if finite lookup/conjunct obligations all matched:
  -> STOP(FINITE_MATCHED_DIRECT)
else if EVENT route is registered and an unexpanded seed event exists:
  -> run EVENT once
  -> update state
  -> if finite obligations all matched: STOP(FINITE_MATCHED_EVENT)
else:
  -> CONTEXT or STOP(NO_ADMISSIBLE_ROUTE)

while CONTEXT is registered and step < max_context_steps:
  -> run one frozen CONTEXT step
  -> optionally run frozen EVENT completion on newly selected events
  -> update state
  -> if finite obligations all matched: STOP(FINITE_MATCHED_CONTEXT)
  -> if enumeration evidence target reached: STOP(ENUMERATION_TARGET_EVIDENCE)
  -> if no registered novelty: STOP(NO_NOVEL_EVIDENCE)

if plan is OPEN and no novelty or max depth fires:
  -> STOP(OPEN_NOVELTY_EXHAUSTED | OPEN_MAX_DEPTH)
else:
  -> STOP(MAX_DEPTH | NO_ADMISSIBLE_ROUTE)
```

Direct, event, and context route calls return candidates but cannot mutate the
controller. The controller alone owns `visited`, active foreground, evidence
archive, obligation assignment, and stop reason.

## 7. Foreground and Novelty

`active_foreground_cap` limits representations that can drive the next route.
`resolved_evidence_cap` retains provenance already matched to an obligation.
Neither is the 32,000-character delivery budget.

Candidate priority is a lexicographic key locked in the registration:

```text
(
    adds_new_finite_obligation desc,
    adds_new_hard_anchor desc,
    route_precedence,
    route_rank,
    source_turn,
    content_hash
)
```

Novelty means at least one of:

- a newly matched finite obligation;
- a new hard anchor for an unresolved obligation;
- a new event identity for enumeration/open search;
- a new explicit lineage node for a history plan.

Raw candidate identity alone is insufficient novelty. This prevents a route
from continuing merely because it can enumerate endless irrelevant episodes.

## 8. History Plans and SUP-001

A history obligation may use SUP-001 only when the store exposes an explicit
lineage key that the query plan names deterministically. The controller walks
the frozen lineage route and records ordered versions. Natural contradiction or
entity-key inference remains unsolved and is not introduced here. Without a
matching explicit key, the plan is `HISTORY_UNREPRESENTABLE`, not complete.

## 9. Call Boundary

Before retrieval, the process installs counters around every available
completion/chat/response-generation client and every tool capable of invoking
one. Permitted pre-reader calls are only the registered embedding operations.
The controlled retrieval result contains:

```text
generation_calls_before_reader = 0
embedding_calls = exact registered count
reader_calls = 0
```

Any nonzero pre-reader generation count aborts before packing and is a binding
failure. DMR-006 later permits exactly one reader generation after the frozen
retrieval result is committed.

## 10. Matched Arms

- `C_DIRECT`: frozen direct retrieval and packer.
- `C_FIXED`: execute every passing route to maximum registered depth, with the
  same opportunity and budget.
- `T_CONTROLLED`: state machine above.
- `M_ORACLE_STOP`: measurement-only posthoc upper bound using sealed evidence;
  never imported by mechanism code and never a deployable arm.

The primary controller claim requires both efficiency on easy queries and
recovery on unresolved queries. Merely matching `C_FIXED` while emitting a
different stop label is identity-equivalent and stops the study.

## 11. Part 1 Exploration Before Pre-Registration

Characterize:

1. Support-score and hard-anchor distributions for correct, topical-but-wrong,
   and unrelated evidence on development data.
2. Bipartite assignment ambiguity, shared evidence, and unsupported finite
   obligations.
3. Route eligibility, transition, foreground occupancy, evidence archive size,
   and stop-reason distributions.
4. False stops versus `M_ORACLE_STOP` on development only.
5. Easy-query saved route calls and hard-query added evidence.
6. No-novelty, repeated event, max-depth, all-open, all-finite, no-route, and
   exact-threshold traces at intended length.
7. Every combination of independently passing upstream routes. The final
   registration locks one stack; it does not branch based on held-out results.

## 12. Prospective Measures and Gates

Numeric bars are set after Part 1 and before implementation:

| Gate | Required meaning |
|---|---|
| G1 Stack identity | Every carried route, plan, vector, seed, and packer reproduces its frozen identities and digests |
| G2 Call purity | Zero generative calls before reader; exact registered embedding-call shape |
| G3 Route differentiation | `T_CONTROLLED` differs from both direct and fixed-depth controls on registered traces for the stated reason |
| G4 Stop safety | False-stop and false-finite rates meet strict per-class bars; open/enumeration plans are never labeled complete |
| G5 Retrieval utility | Packed broad evidence improves over direct and targeted queries have zero losses |
| G6 Domain safety | No registered domain regresses; disconnected-domain recovery meets its bar |
| G7 Efficiency | Easy finite queries avoid a registered amount of needless route work without sacrificing evidence |
| G8 State safety | No cycle, absorbing route, unbounded foreground/archive, unstable tie, or unreported stop |

An efficiency gain cannot compensate for a false stop. Aggregate utility cannot
compensate for a targeted or domain loss.

## 13. Surrogate Audit

| Metric | False-pass mode | Protection |
|---|---|---|
| Obligation matched | Topical evidence can satisfy cosine/anchor rules without an answer | Sealed false-stop audit and DMR-006 reader test |
| New hard anchor | Anchor can appear in irrelevant text | Must combine with support score; still reported as heuristic |
| N evidence units | Multiple episodes can repeat one answer | Never call enumeration complete |
| Saved calls | Stopping immediately is maximally efficient | Utility and false-stop gates bind first |
| Broad gain | Hard queries can improve while lookups fall | Zero targeted-loss gate |
| No second LLM | A model service can hide behind a reranker name | Network/client/tool call sentinels and import graph |
| Small foreground | Resolved archive can secretly grow without bound | Separate caps and full occupancy distributions |

## 14. Stage Preflight

**State:** `NOT RUN`.

### Part 1 Deliverables

- One falsifiable sentence describing every route transition and stop predicate.
- Name checks for direct, event, context, foreground, archive, obligation,
  support, novelty, complete, and stop reason.
- Full per-query/per-step distributions.
- Real intended-length traces for every feedback and degenerate state.

### PF1-PF10

| Check | DMR-005 required artifact |
|---|---|
| PF1 | Hash manifest for all route modules/configs, plans, vectors, controls, keys, packer, and call sentinel |
| PF2 | Executed behavioral identity for every route and state variable |
| PF3 | Proof that reproduction, leakage, call, and safety gates precede held-out evidence access |
| PF4 | Joint achievability matrix for support floors, caps, steps, classes, domains, and all bars |
| PF5 | Stable query/obligation/event/content/design hash proof |
| PF6 | Reproduce every carried component and control by ordered identity and payload digest |
| PF7 | Intended-length cycle/absorbing/bound proof for controller feedback on real traces |
| PF8 | State that offline controller tests cannot detect reader interpretation or long-run plasticity |
| PF9 | Completed surrogate table including direct, fixed, open-only, and immediate-stop baselines |
| PF10 | State that controller availability is not a verdict and DMR-006 is required |

## 15. Verification Contract for Later Implementation

Tests must cover every state/transition/stop reason, deterministic bipartite
assignment, hard-anchor rules, unsupported enumeration/open/history behavior,
route absence, route hash mismatch, foreground/archive bounds, novelty, ties,
cycles, max depth, exact budget packing, two-process replay, import/leakage
sentinels, and model-call interception. A planted fake generation client must
fail before its result can affect retrieval.

## 16. Decision

If DMR-005 passes, freeze the entire retrieval result boundary for DMR-006. If
it stops, retain independently successful lower-level routes as fixed-depth
components only. Do not add a second language-model controller as an amendment;
that would be a different architecture and a different thesis.

## Sources

- [Polyn et al. (2005)](https://doi.org/10.1126/science.1117645)
- [Tomita et al. (1999)](https://doi.org/10.1038/44372)
- [Rajasethupathy et al. (2015)](https://doi.org/10.1038/nature15389)
- [Badre et al. (2005)](https://doi.org/10.1016/j.neuron.2005.07.023)
- [Harris & Berntsen (2019)](https://doi.org/10.1016/j.concog.2019.102793)
