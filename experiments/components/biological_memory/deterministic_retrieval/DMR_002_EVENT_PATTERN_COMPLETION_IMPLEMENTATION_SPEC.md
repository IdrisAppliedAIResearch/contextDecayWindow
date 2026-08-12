# DMR-002 - Event-Bound Pattern Completion Implementation Specification

**Document type:** Prospective implementation specification
**Status:** `DESIGN ONLY - NOT PRE-REGISTERED - NO IMPLEMENTATION AUTHORIZED`
**One proposed component:** `TypedEventPatternCompleter`
**Depends on:** A passing, frozen DMR-001 event map
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

DMR-002 asks whether a partial cue can recover other elements that were
explicitly bound into the same event. This is not radius-one adjacency and is
not another nearest-neighbor hop. The only new operation is traversal of frozen
`MEMBER_OF_EVENT` relationships produced before queries exist.

## 2. Scientific Claim and Engineering Hypothesis

Multi-element event paradigms support holistic recollection: cueing one event
element is associated with retrieval of other event elements
([Horner et al., 2015](https://doi.org/10.1038/ncomms8462)). Human CA3 activity
has been associated with this form of pattern completion
([Grande et al., 2019](https://doi.org/10.1523/JNEUROSCI.0722-19.2019)).

The engineering hypothesis is that deterministic traversal of a frozen event
membership relation will recover useful evidence missed by direct similarity,
without the irrelevant expansions observed under unconditional temporal
adjacency. Typed graph traversal is an implementation hypothesis, not a claim
that the graph is a hippocampus.

## 3. Scope

### Included

- Freeze direct-retrieval seed identities and scores before treatment runs.
- For each seed, retrieve unvisited members of that seed's DMR-001 event.
- Rank completed members with a fixed, content-blind event rule.
- Merge seeds and completed members under matched candidate and delivery
  opportunities.
- Report every edge traversal and exclusion.

### Excluded

- Recomputing first-hop ranks, changing DMR-001 events, generic adjacency,
  semantic-neighbor traversal, query rewriting, context recurrence, controller
  logic, reader calls, accessibility plasticity, and consolidation.
- Answer-key-guided event selection or member order.

## 4. Intended Future Interface

```text
src/biological_memory/pattern_completion.py
```

```python
class TypedEventPatternCompleter:
    def complete(
        self,
        *,
        seeds: Sequence[RankedEpisode],
        event_snapshot: EventContextSnapshot,
        visited: Collection[str],
        opportunity_cap: int,
    ) -> CompletionTrace: ...
```

The method receives no answer key, query text, query vector, or model client. It
cannot create new event edges. Its output identities are a deterministic
function of seed order, the frozen event map, visited identities, and locked
configuration.

## 5. Mechanical Completion Rule

For seed `s_i` at direct rank `i`, let `E(s_i)` be its frozen event and
`pos(e)` its within-event position. Candidate `e` receives:

```text
event_distance(s_i, e) = abs(pos(s_i) - pos(e))
completion_key(e) = (
    best_seed_rank_linking_e,
    event_distance(best_seed, e),
    event_position(e),
    episode_hash(e)
)
```

Candidates are emitted in ascending `completion_key`; an episode linked from
multiple seeds appears once under its best key. No member embedding or query
similarity appears in this ranking. This makes the added information source
exactly event binding.

The opportunity cap is charged on unique emitted candidates. The same number of
extra opportunities is provided to each control:

- `C_ADJ`: nearest unvisited temporal neighbors by radius then source order.
- `C_CHAIN`: fixed-query recursive-cosine candidates using the corrected E006
  recurrence.
- `T_EVENT`: typed event members under the rule above.

All arms begin with byte-identical direct seeds and are packed by the same frozen
packer to the same exact character budget. If an arm cannot fill its cap, the
shortfall is recorded; the system does not add a fallback mechanism.

## 6. Candidate Versus Delivery Accounting

Pattern completion is measured at two boundaries:

1. **Candidate recovery:** whether event traversal made required evidence
   reachable before packing.
2. **Packed recovery:** whether the frozen packer delivered that evidence.

Candidate count, active foreground count, packed episode count, and exact
characters are all separate fields. A candidate gain that the matched packer
always discards does not pass the stage. Conversely, a packing-order gain cannot
be attributed to pattern completion unless candidate identities differ first.

## 7. Part 1 Exploration Before Pre-Registration

The future branch must empirically characterize:

1. Frozen DMR-001 event-size, within-event distance, and seed-event coverage
   distributions on the real intended corpus.
2. How often direct seeds share one event, yielding duplicate completion paths.
3. Candidate counts available to `C_ADJ`, `C_CHAIN`, and `T_EVENT` at every
   proposed cap.
4. Whether `T_EVENT` is identity-equivalent to either control on any probe.
5. Cross-event contamination and required-evidence co-membership measured only
   after the event snapshot is frozen.
6. Empty event, singleton event, all-seeds-same-event, and opportunity-exhausted
   traces.

If DMR-001 events contain no useful multi-element structure, DMR-002 should stop
in exploration rather than invent a retrieval gate that can pass.

## 8. Prospective Evaluation

### Probe Classes

- Broad multi-domain enumeration.
- Targeted single-fact lookup.
- Multi-element within-event probes.
- Cross-event probes for which event completion should not claim sufficiency.
- The known art bundle as diagnostic only, not as the sole gate.

### Required Measures

- Candidate and packed required facts overall and by domain.
- Per-query gains and losses relative to `C_DIRECT` and each matched control.
- Seed event coverage and completed-member precision.
- Cross-event contamination rate.
- Candidate opportunity and exact delivered characters.
- Identity overlap/Jaccard and ordered-prefix equality among arms.

### Binding Gate Meanings

Part 1 must calibrate achievable numeric bars before the registration locks:

| Gate | Required meaning |
|---|---|
| G1 Reproduction | Direct seeds and control payloads reproduce their frozen identities and digests |
| G2 Differentiation | `T_EVENT` emits identities not obtainable in the same order from both controls |
| G3 Broad availability | Event completion improves the registered broad required-evidence measure |
| G4 Target safety | Zero per-query targeted losses relative to frozen direct retrieval |
| G5 Domain safety | No registered domain regresses; art recovery is required if art is structurally co-event-bound in the holdout |
| G6 Contamination | Cross-event additions remain below the locked achievable bar |

Candidate-only improvement cannot satisfy G3. Aggregate improvement cannot hide
a G4 or G5 loss.

## 9. Surrogate Audit

| Metric | How it could pass falsely | Required residual control |
|---|---|---|
| Event-member precision | Members can be same-event but irrelevant to the query | Measure required evidence and reader later; do not call precision usefulness |
| Broad fact count | Gains can evict targeted facts | Zero per-query targeted loss gate |
| Art recovery | A special case can improve while other domains fall | Domain table and all-query losses |
| Candidate gain | Packer can discard every gain | Packed gate required |
| Difference from adjacency | Different order can contain identical evidence | Identity sets, ordered identities, and required-evidence outcomes |
| Biological grounding | A typed edge can work for nonbiological reasons | Claim only engineering performance |

## 10. Stage Preflight

**State:** `NOT RUN`.

### Part 1 Deliverables

- Falsifiable identity: "Given frozen seeds and event map X, the completer emits
  exactly the unique unvisited same-event members ordered by key Y."
- Name checks for seed, event member, completion, opportunity, candidate,
  packing, and contamination.
- Per-probe distributions for every arm.
- Real traces for every empty, duplicate, and exhausted state.

### PF1-PF10

| Check | DMR-002 required artifact |
|---|---|
| PF1 | Hash manifest for DMR-001 snapshot, direct seeds, query set, plant key, packer, and controls |
| PF2 | Behavioral identity traces for all three expansion operators and the packer |
| PF3 | Test proving reproduction and leakage gates precede treatment outcomes |
| PF4 | Achievability matrix over candidate caps, budgets, domains, and required gains |
| PF5 | Content-hash equality and deterministic duplicate-resolution proof |
| PF6 | Frozen direct and E006/adjacency control reproduction by identities and payload digest |
| PF7 | No feedback is introduced; nevertheless prove duplicate expansion terminates at the opportunity cap |
| PF8 | Explicitly formation/retrieval offline only; no ablation or live verdict |
| PF9 | Completed surrogate table with observed residual magnitudes |
| PF10 | State that a passing offline stage only authorizes DMR-003 design, not reader/live promotion |

## 11. Verification Contract for Later Implementation

Tests must cover stable ordering, duplicate paths, visited filtering, singleton
events, cap zero, cap exhaustion, cross-session rejection, malformed snapshots,
design-hash mismatch, exact control matching, leakage imports, and zero model
calls. A property test must prove every emitted episode is a member of at least
one seed event and every eligible member before the cap is emitted exactly once.

## 12. Decision

If `T_EVENT` passes, freeze its module, configuration, output schema, and event
snapshot by hash. If it stops, do not blend event completion with recurrence or
routing to rescue it. DMR-003 may still test context recurrence from DMR-001,
but the final controller cannot claim a validated event-completion route.

## Sources

- [Horner et al. (2015)](https://doi.org/10.1038/ncomms8462)
- [Grande et al. (2019)](https://doi.org/10.1523/JNEUROSCI.0722-19.2019)
- [Badre et al. (2005)](https://doi.org/10.1016/j.neuron.2005.07.023)
