# DMR-001 - Event-Context Formation Implementation Specification

**Document type:** Prospective implementation specification
**Status:** `APPROVED - PRE-REGISTERED - IMPLEMENTATION AUTHORIZED`
**Approved:** August 12, 2026 by the program author, who directed end-to-end
implementation of this stage
**Pre-registration:** `../dmr_001/DMR_001_PRE_REGISTRATION.md`, which governs
wherever it and this file disagree, and which records three registered
revisions to sections 5.1, 6, and 8 that Part 1 forced
**One proposed component:** `OnlineEventContextFormer`
**Depends on:** Frozen append-only episode records and pinned episode embeddings
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

Pattern completion requires patterns to have been bound during encoding. The
prior autoassociation diagnostic showed that merely turning real episode
embeddings into sparse codes did not store the episodes as recoverable fixed
points. DMR-001 asks a more basic question: can continuous conversation be
partitioned online into event records that are stable, nondegenerate, and useful
enough to become a retrieval substrate later?

This stage does not retrieve answers. It creates and evaluates one write-path
component only.

## 2. Scientific Claim and Engineering Hypothesis

Naturalistic experience is segmented into events; high-order event boundaries
are associated with hippocampal activity and later reinstatement
([Baldassano et al., 2017](https://doi.org/10.1016/j.neuron.2017.06.041);
[Ben-Yakov & Henson, 2018](https://doi.org/10.1523/JNEUROSCI.0524-18.2018)).
Temporal-context representations differ across event boundaries and can be
reinstated at recall
([Lohnas et al., 2023](https://doi.org/10.1037/xge0001354)).

The engineering hypothesis is narrower and unproven: a causal change detector
over pinned episode embeddings can define useful conversational event records,
and an online leaky context state can preserve encoding context without a model
call. Neuroscience does not establish this detector or equation.

## 3. Scope

### Included

- Consume the existing user-plus-assistant episode unit without changing its
  text, embedding call shape, durability, or append order.
- Detect hard session boundaries and provisional within-session boundaries
  using only past and current episodes.
- Assign each episode exactly one stable event identity.
- Store an ordered membership edge and an encoding-context vector.
- Emit enough boundary evidence to replay every decision exactly.

### Excluded

- Retrieval, ranking, pattern completion, packing, answer generation, scoring,
  salience, consolidation, supersession, and retrieval-induced plasticity.
- Answer-key facts, domains, probe locations, future turns, generated labels,
  generated summaries, or a language-model boundary judge.
- Retroactive reassignment after a later answer reveals that an event grouping
  would have been convenient.

## 4. Intended Future Interface

The implementation target is a new prototype module, later and only after a
locked registration:

```text
src/biological_memory/event_context.py
```

Proposed public contract:

```python
class OnlineEventContextFormer:
    def observe(
        self,
        *,
        episode_hash: str,
        session_hash: str,
        turn_index: int,
        embedding: Float32Vector,
    ) -> FormationDecision: ...

    def snapshot(self) -> EventContextSnapshot: ...
```

`observe` is causal and deterministic. It accepts no text because the pinned
episode embedding and structural metadata are sufficient for this registered
hypothesis. A future text-feature variant would be a different component.

## 5. Mechanical Formation Rule

### 5.1 Identity

An event identity is available when its first member is observed:

```text
event_id = sha256(
    "dmr-event-v1\0" +
    design_sha256 + "\0" +
    session_hash + "\0" +
    first_episode_hash
)
```

The ID does not depend on a future member, runtime path, timestamp, UUID, or
filesystem location. Event membership is kept in a sidecar index; immutable
episode rows are not rewritten.

### 5.2 Online State

For normalized episode vector `x_t`, the open event maintains:

```text
n_t = number of members in the open event
p_t = normalized arithmetic mean of event-member vectors
c_t = normalize(rho * c_(t-1) + (1 - rho) * x_t)
d_t = 1 - cosine(x_t, p_(t-1))
```

At the first member of an event, `p_t = c_t = x_t`. Accumulation uses a fixed
float32 order and records vector SHA-256 values. `rho` is a free engineering
parameter; the future pre-registration must lock it after Part 1.

### 5.3 Boundary Decision

Before adding `x_t` to the open event, begin a new event when:

```text
hard_boundary = session_hash changed
drift_boundary = n_(t-1) >= min_event_size and d_t >= drift_threshold
forced_boundary = n_(t-1) >= max_event_size

new_event = hard_boundary or drift_boundary or forced_boundary
```

The forced boundary is a safety bound, not a scientific event claim. Every
decision records the three booleans, `d_t`, open-event size, threshold, and
design hash. The future registration must lock `min_event_size`,
`max_event_size`, `drift_threshold`, and tie behavior in one authoritative
configuration.

The algorithm is intentionally simple. Adding lexical markers, entity shifts,
learned HMM states, or outcome-aware tuning would add mechanisms and requires a
new study.

## 6. Persistence Schema

The future sidecar store must contain:

```text
event_records(
    event_id TEXT PRIMARY KEY,
    design_sha256 TEXT NOT NULL,
    session_hash TEXT NOT NULL,
    first_episode_hash TEXT NOT NULL,
    start_turn INTEGER NOT NULL,
    end_turn INTEGER NOT NULL,
    member_count INTEGER NOT NULL,
    prototype_f32 BLOB NOT NULL,
    prototype_sha256 TEXT NOT NULL,
    context_f32 BLOB NOT NULL,
    context_sha256 TEXT NOT NULL,
    close_reason TEXT NOT NULL
)

event_members(
    event_id TEXT NOT NULL,
    episode_hash TEXT NOT NULL UNIQUE,
    event_position INTEGER NOT NULL,
    boundary_score REAL NOT NULL,
    boundary_reason TEXT NOT NULL,
    PRIMARY KEY(event_id, event_position)
)
```

Writes for one observed episode are atomic. Replaying the same episode is either
an exact idempotent no-op or a loud mismatch; silent reassignment is forbidden.

## 7. Part 1 Exploration Before Pre-Registration

The future DMR-001 branch must characterize, not merely inspect:

1. The current episode unit and embedding call shape on a committed trace.
2. Drift-score distributions within sessions, at session boundaries, and at
   independently annotated event boundaries.
3. Event-size and duration distributions over a label-blind threshold grid.
4. Sensitivity to one duplicated episode, one near-duplicate embedding, one
   abrupt domain shift, and one long coherent event.
5. All singleton, all-one-event, forced-boundary-periodic, and oscillating
   threshold states.
6. Determinism across two fresh processes and two supported platforms or an
   explicit platform limitation.

Threshold selection may use the development split and independent boundary
annotations, but not answer facts or later retrieval scores. A separate holdout
supplies the binding outcome.

## 8. Prospective Arms and Measures

### Structural Controls

- `C_SESSION`: session boundaries only.
- `C_PAIR`: every episode is its own event.
- `C_ALL`: each session is one event.
- `T_EVENT`: the locked online drift rule.

`C_PAIR` and `C_ALL` are degenerate controls, not viable competitors.

### Measurement-Only Evidence

Independent annotators mark event boundaries without seeing queries, facts,
retrieval outputs, or mechanism settings. The annotation protocol and agreement
rule are committed before the treatment outcome opens. Annotation is not read by
the former.

### Required Reports

- Boundary precision, recall, and tolerance-aware agreement against sealed
  annotations.
- Full event-size distribution and fraction of singleton and forced events.
- Within-event versus across-boundary context similarity distributions.
- Membership stability under exact replay.
- Domain/fact co-membership only as post-formation measurement, never selection.
- Every individual boundary decision with causal input hashes.

## 9. Gates and Kill Conditions

Numeric bars are deliberately not invented in this prospective file. Part 1
must establish achievable values, then the pre-registration locks them before
implementation. It must include these binding gate meanings:

| Gate | Property certified | Binding failure |
|---|---|---|
| G1 Integrity | The treatment consumed only permitted causal inputs and reproduced byte-identically | Any leakage, future input, hash mismatch, or nondeterminism |
| G2 Partition | Every episode belongs to exactly one event in order | Missing, duplicate, reordered, or cross-session membership |
| G3 Nondegeneracy | Event formation is not equivalent to `C_PAIR`, `C_ALL`, or fixed periodic chopping | Registered degeneracy bar crossed |
| G4 Boundary evidence | Treatment improves sealed structural boundary agreement over `C_SESSION` | No registered improvement |
| G5 Context separation | Within-event context is distinguishable from across-boundary context on holdout | Registered interval/bar not met |

Passing G4 cannot certify retrieval usefulness. Passing G5 cannot certify
biological context. Both residuals must be stated in the report.

## 10. Stage Preflight

**State:** `RUN`. Part 1 is committed at
`../dmr_001/exploration/DMR_001_PART1_EXPLORATION.json` and PF1-PF10 are
executed into `../dmr_001/artifacts/dmr001_preflight/preflight.json`. The
binding evidence for both parts, and the numeric bars this file deliberately
declined to invent, live in `../dmr_001/DMR_001_PRE_REGISTRATION.md` sections
7 and 8.

### Part 1 Deliverables

- Falsifiable identity: for example, "At design SHA X, the former starts a new
  event iff one of the three recorded causal boundary predicates is true."
- Name checks for episode, session, event, prototype, context, drift, and forced
  boundary.
- Full distributions, not only means.
- Real-trace demonstrations of every degenerate state named above.

### PF1-PF10

| Check | DMR-001 required artifact |
|---|---|
| PF1 | Corpus, annotation, embedding-cache, config, and episode manifests with counts and hashes |
| PF2 | Behavioral identity trace for the current episode store, embedder, and proposed former |
| PF3 | Test proving leakage/preflight gates execute before annotation outcome access |
| PF4 | Reachability table for boundary, size, agreement, and context-separation bars |
| PF5 | Identity test using only content, session, and design hashes |
| PF6 | Byte-identical reproduction of the frozen source episode stream and vectors |
| PF7 | Intended-length proof for singleton, giant-event, and forced-periodic states |
| PF8 | Statement that no reader ablation occurs and formation-only limits are explicit |
| PF9 | Surrogate table for boundary agreement, context separation, and nondegeneracy |
| PF10 | Explicit statement that DMR-001 has no live verdict and cannot authorize one |

## 11. Verification Contract for Later Implementation

The eventual implementation must have unit, property, integration, leakage, and
two-process tests covering:

- stable IDs and canonical serialization;
- causal input rejection and out-of-order turns;
- event partition invariants;
- exact float32 update order and vector hashes;
- hard, drift, and forced boundary precedence;
- idempotent replay and loud conflicting replay;
- transactional failure midway through a boundary;
- no import path to keys, rubrics, reader clients, packers, or scorers;
- no completion/chat/response call in the process.

Test names and expected artifacts are locked in the future pre-registration;
this document creates none of them.

## 12. Decision

If DMR-001 passes, its complete event map and design are frozen for DMR-002.
DMR-002 may not retune boundaries to improve retrieval. If DMR-001 stops, the
arc records that deterministic embedding-change event formation was not a valid
substrate; the biological event literature remains intact, but this engineering
translation is rejected.

## Sources

- [Baldassano et al. (2017)](https://doi.org/10.1016/j.neuron.2017.06.041)
- [Ben-Yakov & Henson (2018)](https://doi.org/10.1523/JNEUROSCI.0524-18.2018)
- [Lohnas, Healey & Davachi (2023)](https://doi.org/10.1037/xge0001354)
