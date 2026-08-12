# DMR Arc - Deterministic Multi-Route Retrieval Implementation Roadmap

**Document type:** Prospective implementation specification
**Status:** `BLOCKED AT DMR-001`. DMR-001 was approved, pre-registered,
implemented, and run on August 12, 2026. It stopped at G3 with disposition
`DEGENERATE_FORMATION`, so the arc has no validated event substrate and
DMR-002 through DMR-006 are blocked by this roadmap's own dependency rule 4.
Stages 2 through 6 remain `DESIGN ONLY - NOT PRE-REGISTERED - NO
IMPLEMENTATION AUTHORIZED`. See
`../dmr_001/DMR_001_REPORT.md`.
**Reference architecture:** `HYPOTHETICAL_001_MECHANICAL_BIOLOGICAL_MEMORY_MODEL.md`
**Thesis constraint:** Retrieval completes before exactly one final reader
generation call. No generative model writes a query, summary, route, stopping
decision, memory, or score inside the retrieval path.
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

## 1. Problem Statement

Repeated cosine retrieval is one operator applied multiple times. It can expand
within a semantic neighborhood, but it has no representation of which details
were encoded as one event, no encoding-time context to reinstate, and no
mechanical account of when a search is complete. Increasing the delivery budget
cannot create those missing structures.

The DMR hypothesis is that recall needs three separable operations:

1. **Direct access:** fast similarity-based access when the original cue is
   already diagnostic.
2. **Event completion:** recovery of other elements bound into the same encoded
   event as a retrieved seed.
3. **Context search:** reinstatement of the seed's encoding context, which
   changes the next cue while preserving the user's original goal.

A fourth operation, deterministic control, decides which route to attempt and
when to stop. It is deliberately not a language model.

## 2. Scientific Grounding

### Evidence Classes

- **Empirical:** a reported behavioral or neural observation.
- **Computational:** a formal model that explains observations but is not itself
  a direct measurement.
- **Engineering translation:** an implementable hypothesis introduced here. It
  must be tested and is not licensed merely by biological plausibility.

| Source | Evidence class | Supported observation | DMR translation | What it does not support |
|---|---|---|---|---|
| Cowan et al. (2005) | Empirical | Attentional working-memory capacity is limited and chunk-sensitive | Separate `active_foreground_cap` from reader serialization budget | A fixed token, character, or universal four-item parameter |
| Baldassano et al. (2017) | Empirical/model-based analysis | Continuous narratives exhibit stable event patterns and boundaries associated with later reinstatement | Store explicit event identities and event-state vectors | That embedding drift is the biological boundary detector |
| Ben-Yakov & Henson (2018) | Empirical | Hippocampal activity is sensitive to independently identified naturalistic event boundaries | Treat event formation as a first-class write-path problem | That every turn boundary or topic shift is an event boundary |
| Lohnas, Healey & Davachi (2023) | Empirical plus CMR comparison | Temporal context is disrupted by event boundaries and reinstated during recall | Preserve event-conditioned encoding context for later retrieval | The exact recurrence equation or parameter values used here |
| Horner et al. (2015) | Empirical | A cue to one element can be associated with reinstatement of other elements from a learned event | Traverse typed same-event bindings from a seed | Arbitrary nearest-neighbor or temporal expansion |
| Grande et al. (2019) | Empirical | Human CA3 activity is associated with holistic multi-element recollection | Test event-level completion as distinct from similarity ranking | That a software event node is CA3 |
| Kahana (1996) | Behavioral | Recall transitions show temporal associative organization | Evaluate sequential transitions, not only one-shot rank | Unbounded search until a person consciously remembers |
| Polyn, Norman & Kahana (2009) | Computational | Recalled items can reinstate context that cues subsequent recall | Update a deterministic context state after retrieval | That mean-pooling retrieved text embeddings is context reinstatement |
| Manning et al. (2011) | Empirical | Neural context reinstatement correlates with successive recall of neighboring study items | Require stored encoding context to influence later cue state | A guarantee that context recurrence helps text retrieval |
| Polyn et al. (2005) | Empirical | Category-specific cortical activity can precede recall | Derive goal/category features before memory search | Generated query planning or hidden chain-of-thought |
| Tomita et al. (1999) | Empirical | Top-down prefrontal signals influence memory retrieval | Maintain an unchanged goal anchor during route changes | A direct mapping from prefrontal cortex to a software controller |
| Rajasethupathy et al. (2015) | Empirical in mice | Neocortical projections can mediate top-down control of recall | Keep control state separate from stored episodic content | Human consciousness as a scientifically localized software module |
| Badre et al. (2005) | Empirical | Controlled retrieval and post-retrieval selection can dissociate | Separate candidate access, competition, and delivery | That deterministic query obligations are neurally established |
| Wolff et al. (2017) | Empirical | Temporarily unattended working-memory content can remain in a recoverable hidden state | Permit latent retrieved evidence outside the active foreground | Unlimited latent capacity or persistence without interference |
| Harris & Berntsen (2019) | Behavioral | Direct and generative autobiographical retrieval are both observed; direct retrieval is common | Retain a cheap direct route before controlled search | Two anatomically discrete systems or a second artificial reasoner |

The primary sources support the separation of event binding, completion,
context reinstatement, selection, and control. They do not specify embeddings,
hashes, bitsets, thresholds, or graph schemas. Those are engineering hypotheses
and are exposed as such below.

## 3. Shared Mechanical Contract

### 3.1 Intended Future Data Structures

```text
EpisodeRecord:
    content_hash        : sha256
    content             : immutable utf8
    turn_index          : int
    session_hash        : sha256
    embedding_ref       : vector_cache_key
    accessibility       : float
    event_id            : sha256 | None
    event_position      : int | None

EventRecord:
    event_id            : sha256(canonical member hashes + design hash)
    member_hashes       : ordered[sha256]
    start_turn          : int
    end_turn            : int
    boundary_evidence   : deterministic fields
    prototype_vector    : float32 vector
    encoding_context    : float32 vector

QueryObligation:
    obligation_id       : stable hash
    kind                : LOOKUP | ENUMERATION | CONJUNCT | HISTORY | OPEN
    lexical_features    : immutable normalized tokens
    entity_keys         : ordered[stable key]
    requested_count     : int | UNKNOWN
    status              : UNRESOLVED | SUPPORTED | UNREPRESENTABLE

RetrievalState:
    query_hash          : sha256
    query_vector        : float32 vector
    goal_features       : deterministic sparse vector
    obligations         : ordered[QueryObligation]
    active_event_ids    : ordered[event_id]
    active_episode_ids  : ordered[content_hash]
    resolved_evidence   : ordered[content_hash]
    context_vector      : float32 vector
    visited             : set[stable hash]
    route               : DIRECT | EVENT | CONTEXT | STOP
    stop_reason         : enum | None
    step                : int
```

No generated identifier may be used as an equality key. UUIDs, timestamps, and
filesystem paths are metadata only.

### 3.2 Intended Future Module Boundaries

These paths describe later implementation ownership. This document does not
create them.

| Future module | Sole responsibility | Forbidden responsibility |
|---|---|---|
| `src/biological_memory/event_context.py` | Online event partition and encoding-context state | Query scoring, answer keys, packing, model calls |
| `src/biological_memory/pattern_completion.py` | Typed event-member expansion from frozen seeds | Generic vector chaining, routing, reader calls |
| `src/biological_memory/retrieved_context.py` | Context reinstatement and fixed recurrence | Generated query rewriting, stopping policy |
| `src/biological_memory/query_obligations.py` | Deterministic query obligations and explicit unsupported states | Retrieval execution, answer generation, content rewriting |
| `src/biological_memory/retrieval_controller.py` | Route transitions and stop reasons over frozen obligations | Obligation invention, answer generation, content rewriting |
| `src/biological_memory/reader_boundary.py` | Enforce retrieval-before-reader call count | Retrieval ranking or scoring outcomes |

### 3.3 Model-Call Boundary

The process contract is:

```text
user turn
  -> deterministic query features
  -> query embedding lookup or one embedding request
  -> direct retrieval
  -> optional typed event completion
  -> optional retrieved-context recurrence
  -> deterministic stopping
  -> exact evidence packing
  -> one final reader generation call
  -> answer
```

An embedding request is not a generative reasoning call, but it must be counted,
recorded, and fixed across arms. A completion, chat, response-generation, tool
reasoner, reranker LLM, or model-written query before the reader is a hard
failure.

## 4. Capacity Model

The program's 32,000-character limit constrains serialized evidence, not memory
search. DMR uses three independent ceilings:

| Ceiling | Limits | May affect later search? |
|---|---|---|
| `active_foreground_cap` | Event or episode representations participating in the current transition | Yes |
| `resolved_evidence_cap` | Provenance-linked evidence retained after leaving foreground | Only through obligation status; content does not become a new cue |
| `delivery_budget_chars` | Final serialized evidence sent to the reader | No; packing runs after search terminates |

The active cap will not be set to a human chunk estimate. Cowan et al. motivates
the separation, not a software parameter. Candidate values must be characterized
in Part 1, locked once, and tested for reachability and interaction before any
outcome is opened.

## 5. Shared Evaluation Design

### 5.1 Corpora

1. The existing 119-episode internal corpus and 24-query manifest are a
   diagnostic development set because their outcomes are already known.
2. Existing LongMemEval artifacts may test scale and session structure when
   their exact inputs and caches are hash-available.
3. A new holdout must be locked before confirmatory evaluation. Its event
   annotations are created independently of retrieval labels; its answer key is
   measurement-only and sealed from mechanism imports.
4. Synthetic fixtures prove identities, edge traversal, recurrence, cycles, and
   stop states. They cannot satisfy evidence-quality gates.

### 5.2 Controls

- `C_DIRECT`: frozen single-shot direct retrieval from a prior worktree.
- `C_ADJ`: radius-matched temporal adjacency when event completion is tested.
- `C_CHAIN`: the corrected E006 fixed-query similarity recurrence.
- `C_FIXED_DEPTH`: all DMR routes attempted for a fixed number of steps when the
  controller is tested.

Controls are checked out independently; treatment code is never disabled to
manufacture a control.

### 5.3 Common Metrics

- Exact candidate and packed identity by content hash.
- Required-evidence availability at broad, domain, and targeted probes.
- Per-query gains and losses, not total score alone.
- Event-boundary agreement and event-size distribution for DMR-001.
- Cross-event contamination for DMR-002.
- Cue differentiation, route transitions, cycles, and revisits for DMR-003.
- Obligation coverage, ambiguity, and false-complete declarations for DMR-004.
- False stops, needless retries, and unsupported completion declarations for
  DMR-005.
- Reader correctness, attribution, abstention, and targeted regression for
  DMR-006.
- Exact characters and model-call counts for every arm.

### 5.4 Quantitative Answer Contract

Future scoring must accept equivalent integer and finite-decimal forms when
numeric value, sign, unit or currency marker, and surrounding factual content
agree. This rule is locked before answers. It does not imply unit conversion,
date/time normalization, percentage inference, or semantic paraphrase.

## 6. Arc-Level Preflight

**State:** `NOT RUN`. This roadmap is not run authorization. Each study must
materialize and commit its own answers before implementation.

### Part 1 - Exploration Deliverables

- A one-sentence falsifiable behavioral identity for every imported component.
- Name-to-behavior checks for every block, tier, state variable, edge type, and
  route on real committed traces.
- Full distributions of event sizes, candidate ranks, route lengths, foreground
  occupancy, delivered characters, and stop reasons.
- Real-trace demonstrations of singleton, giant-event, repeated-cue, cycle,
  no-novelty, and max-depth states.
- A design revision or explicit no-change decision committed after exploration
  and before pre-registration lock.

### Part 2 - PF1-PF10 Required Evidence

| Check | Required committed answer before implementation |
|---|---|
| PF1 | Input manifest with path, byte count, record count, SHA-256, encoding, and vector-cache identity |
| PF2 | Behavioral identity report proving every imported mechanism matches its name on committed traces |
| PF3 | Gate-order test and git anchors proving preflight and offline gates execute before sealed outcomes or inference |
| PF4 | Reachability report for every threshold, budget, class count, and kill condition |
| PF5 | Stable-key report proving comparisons use content/design hashes only |
| PF6 | Replay reproducing a known control by ordered identities, payload bytes, and digest |
| PF7 | Intended-length absorbing-state and cycle report for every feedback path |
| PF8 | Ablation-length statement naming failures detectable and undetectable at 35 turns |
| PF9 | Surrogate table for every gate, including how it could pass while event binding, recall, sufficiency, or reader correctness is false |
| PF10 | Exact offline, 35-turn, longer-run, and live decision sequence with availability explicitly nonverdictive |

## 7. Free Parameters and Lock Discipline

The proposed stack exposes at least: event-boundary rule, event minimum and
maximum size, context persistence, event-edge weight, completion cap, direct
candidate count, recurrence interpolation, recurrence depth, active foreground
cap, evidence cap, similarity floors, novelty floor, obligation parser rules,
route order, and stop thresholds. Neuroscience supplies none of their software
values.

Part 1 may measure these interactions on diagnostic data. A study must then lock
one configuration and one control before opening its held-out outcome. Tuning a
downstream stage may not alter a frozen upstream parameter. If interactions make
the registered threshold unreachable, the study stops; it does not expand a
grid after seeing results.

## 8. Source List

- Badre, D. et al. (2005). Dissociable controlled retrieval and generalized
  selection mechanisms in ventrolateral prefrontal cortex. *Neuron*, 47,
  907-918. https://doi.org/10.1016/j.neuron.2005.07.023
- Baldassano, C. et al. (2017). Discovering event structure in continuous
  narrative perception and memory. *Neuron*, 95, 709-721.e5.
  https://doi.org/10.1016/j.neuron.2017.06.041
- Ben-Yakov, A. & Henson, R. N. (2018). The hippocampal film editor:
  sensitivity and specificity to event boundaries in continuous experience.
  *Journal of Neuroscience*, 38, 10057-10068.
  https://doi.org/10.1523/JNEUROSCI.0524-18.2018
- Cowan, N. et al. (2005). On the capacity of attention. *Cognitive
  Psychology*, 51, 42-100. https://doi.org/10.1016/j.cogpsych.2004.12.001
- Grande, X. et al. (2019). Holistic recollection via pattern completion
  involves hippocampal subfield CA3. *Journal of Neuroscience*, 39, 8100-8111.
  https://doi.org/10.1523/JNEUROSCI.0722-19.2019
- Harris, C. B. & Berntsen, D. (2019). Direct and generative autobiographical
  memory retrieval: How different are they? *Consciousness and Cognition*, 74,
  102793. https://doi.org/10.1016/j.concog.2019.102793
- Horner, A. J. et al. (2015). Evidence for holistic episodic recollection via
  hippocampal pattern completion. *Nature Communications*, 6, 7462.
  https://doi.org/10.1038/ncomms8462
- Kahana, M. J. (1996). Associative retrieval processes in free recall.
  *Memory & Cognition*, 24, 103-109. https://doi.org/10.3758/BF03197276
- Lohnas, L. J., Healey, M. K. & Davachi, L. (2023). Neural temporal context
  reinstatement of event structure during memory recall. *Journal of
  Experimental Psychology: General*, 152, 1840-1872.
  https://doi.org/10.1037/xge0001354
- Manning, J. R. et al. (2011). Oscillatory patterns in temporal lobe reveal
  context reinstatement during memory search. *PNAS*, 108, 12893-12897.
  https://doi.org/10.1073/pnas.1015174108
- Polyn, S. M. et al. (2005). Category-specific cortical activity precedes
  retrieval during memory search. *Science*, 310, 1963-1966.
  https://doi.org/10.1126/science.1117645
- Polyn, S. M., Norman, K. A. & Kahana, M. J. (2009). A context maintenance and
  retrieval model of organizational processes in free recall. *Psychological
  Review*, 116, 129-156. https://doi.org/10.1037/a0014420
- Rajasethupathy, P. et al. (2015). Projections from neocortex mediate top-down
  control of memory retrieval. *Nature*, 526, 653-659.
  https://doi.org/10.1038/nature15389
- Tomita, H. et al. (1999). Top-down signal from prefrontal cortex in executive
  control of memory retrieval. *Nature*, 401, 699-703.
  https://doi.org/10.1038/44372
- Wolff, M. J. et al. (2017). Dynamic hidden states underlying working-memory-
  guided behavior. *Nature Neuroscience*, 20, 864-871.
  https://doi.org/10.1038/nn.4546

## 9. Authorization Boundary

These are implementation specifications, not locked pre-registrations and not
permission to create modules, tests, artifacts, caches, or runs. The next legal
action for DMR-001 is a clean branch plus Part 1 exploration specification and
pre-registration commit. No code may precede that commit.
