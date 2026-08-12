# HYPOTHETICAL-001 — A Mechanical Implementation of the Biological Memory Model

**Type:** Speculative architecture design. **Clean slate.**
**Status:** THOUGHT EXPERIMENT — not authorized, not scoped, not a proposal
**Grounding:** `NEUROSCIENCE_LANDSCAPE.md`
**Constraint:** Derived from the biological literature alone. **Prior program results are deliberately excluded from the derivation** — they appear only in §8, after the design is complete, so the design is not quietly reverse-engineered from what already failed.

---

## 0. Rules of the exercise

1. **Only mechanisms with primary-source grounding.** Every design element traces to §1's numbered principles.
2. **No appeal to prior study results.** Not as justification, not as constraint. §8 is where they enter.
3. **Mechanical means mechanical.** Data structures, update rules, and where the compute goes. Not metaphor.
4. **Biological plausibility is not evidence.** This document produces a hypothesis with a falsification plan (§9), nothing more.

**What this is for:** the literature describes a system that solves several problems differently than any deployed memory architecture does. Writing it out mechanically shows which of those differences are implementable and which dissolve on contact with engineering.

---

## 1. Design principles, from the literature

| # | Principle | Source |
|---|---|---|
| **P1** | Tags mark recent activity, not importance. A tag is set by any encoding event and decays on a fixed window | Frey & Morris (1997/98) synaptic tagging and capture |
| **P2** | Consolidation resources are produced by *independent* salient events and captured by whichever tags are live. Capture is **symmetric in time** — resources can be captured before or after the tag is set | Frey & Morris; Moncada, Ballarini & Viola (2015) behavioral tagging |
| **P3** | Selection is **retroactive**. Awake ripples at reward select which experiences consolidate later | *Science* (2024) doi:10.1126/science.adk8261 |
| **P4** | Replay is **sequential and recombinant** — it merges new material with pre-existing information rather than compressing single episodes | Buzsáki (2015); Wilson & McNaughton (1994) |
| **P5** | **Storage and retrieval are separate substrates.** Connectivity carries storage; synaptic strength carries retrievability. A trace can be fully present and unreachable by natural cues | Ryan et al. (2015); Roy et al. (2017) silent engrams |
| **P6** | Retrieval is **competitive**. Retrieving one item suppresses competitors sharing a cue, and suppression occurs even when retrieval fails | Anderson, Bjork & Bjork (1994, 2000) |
| **P7** | Retrieval **destabilizes** the trace, which must be restabilized | Nader, Schafe & LeDoux (2000) |
| **P8** | Consolidation **transforms**: gist strengthens, contextual detail weakens, and remote traces gain illusory content | Yassa & Reagh (2013); Moscovitch et al. (2007) |
| **P9** | Retrieval may create a **new trace** rather than reactivating the old one | Nadel & Moscovitch (1997) multiple trace theory |
| **P10** | Fast and slow systems exist to prevent catastrophic interference | McClelland, McNaughton & O'Reilly (1995) |
| **P11** | The actively attended workspace is small and chunk-based; it is not a byte-addressed copy of long-term storage | Cowan et al. (2005), doi:10.1016/j.cogpsych.2004.12.001 |
| **P12** | A partial element of a bound event can reinstate other event elements through hippocampal pattern completion and cortical reinstatement | Horner et al. (2015), doi:10.1038/ncomms8462; Grande et al. (2019), doi:10.1523/JNEUROSCI.0722-19.2019 |
| **P13** | Recall changes the retrieval context. The recovered context then cues temporally and semantically associated memories, so memory search can be iterative without an external reasoner constructing each step | Kahana (1996), doi:10.3758/BF03197276; Polyn, Norman & Kahana (2009), doi:10.1037/a0014420 |
| **P14** | Retrieval is under top-down control: goal- and category-specific cortical states can precede recall and bias which stored representation is recovered | Tomita et al. (1999), doi:10.1038/44372; Polyn et al. (2005), doi:10.1126/science.1117645; Rajasethupathy et al. (2015), doi:10.1038/nature15389 |
| **P15** | Temporarily unattended working-memory content can remain recoverable in a latent or transformed state and can be reactivated by an internal cue or perturbation | Wolff et al. (2017), doi:10.1038/nn.4546 |
| **P16** | Continuous experience is segmented into events. Event boundaries shape hippocampal encoding and temporal context, and event patterns can be reinstated during later recall | Baldassano et al. (2017), doi:10.1016/j.neuron.2017.06.041; Ben-Yakov & Henson (2018), doi:10.1523/JNEUROSCI.0524-18.2018; Lohnas et al. (2023), doi:10.1037/xge0001354 |
| **P17** | Controlled retrieval and post-retrieval selection are dissociable operations rather than one undifferentiated relevance computation | Badre et al. (2005), doi:10.1016/j.neuron.2005.07.023 |
| **P18** | Direct and generative autobiographical retrieval are both observed, but behavioral evidence does not establish that they are fundamentally different cognitive processes | Harris & Berntsen (2019), doi:10.1016/j.concog.2019.102793 |

---

## 2. Data model

The load-bearing decision is P5: **two independent quantities per episode.** Every deployed memory system conflates them into one relevance score.

```
Episode:
    id              : uuid
    content         : str            # verbatim, immutable
    t               : int            # sequence position
    embedding       : vec

    # --- storage substrate (P5) ---
    edges           : [(episode_id, weight: float)]

    # --- retrieval substrate (P5) ---
    accessibility   : float          # gates natural-cue activation. NOT similarity.

    # --- tag state (P1) ---
    tag_set_at      : int | None
    tag_expires_at  : int | None
    captured        : float          # cumulative resource captured

    # --- trace lineage (P9) ---
    supersedes      : episode_id | None
    superseded_by   : episode_id | None
```

```
SalienceEvent:
    t               : int
    magnitude       : float          # resource pool size
    reach           : int            # ± turns of temporal window (P2)
```

```
SemanticNode:                        # the slow store (P10)
    id              : uuid
    content         : str            # extractive only — spans copied verbatim
    support         : [episode_id]   # provenance, always
    strength        : float          # grows with each replay (P8)
```

```
RetrievalState:                      # transient; never written as generated text
    goal_features   : sparse_vec     # deterministic lexical/entity/query features
    active_ids      : [episode_id]   # small foreground, not the whole payload
    context_vec     : vec            # reinstated encoding context (P13)
    route           : enum           # DIRECT, EPISODIC, CONTEXT, STOP
    unresolved      : bitset         # mechanically testable query obligations
    visited         : set[episode_id]
    step            : int
```

```
EventRecord:                         # encoding-time binding substrate
    id              : sha256
    member_ids      : ordered[episode_id]
    prototype       : vec            # event-content state
    encoding_context: vec            # context stored before any query exists
    boundary_evidence: record         # causal, replayable, label-blind
```

**Invariants**
- `content` is never rewritten. Transformation acts on `accessibility` and `edges`, never on stored text.
- `accessibility == 0` with `edges` intact is a **silent engram**: stored, connected, unreachable by cue. A legal and expected state, not a bug.
- `SemanticNode.content` contains only spans copied from `support` episodes. **No generated text anywhere in the memory path.**
- `RetrievalState` is computed from the user turn and stored metadata. It cannot contain a generated search query, chain-of-thought, summary, or model-authored routing decision.
- The active foreground has a small item/count ceiling independent of the larger serialization ceiling used to deliver provenance to the final reader.
- Event membership and encoding context are fixed on the write path. Retrieval outcomes cannot retroactively move episodes between events.

---

## 3. Write path — tagging (P1, P2)

```
on_turn(content, t):
    ep = Episode(content, t, embed(content))
    ep.accessibility  = A_INIT          # uniform. no content-based scoring.
    ep.tag_set_at     = t
    ep.tag_expires_at = t + TAG_WINDOW
    ep.edges          = [(prev.id, W_ADJ)]      # temporal adjacency only
    store.append(ep)

    s = salience(t)
    if s > S_THRESHOLD:
        emit SalienceEvent(t, magnitude=s, reach=REACH)
```

**Every episode is written and tagged identically.** No novelty score, no salience weighting at write time, no promotion decision. Importance is not a property of the episode at encoding — it is conferred later by neighbours (P2).

### 3.1 The salience signal — the design's weakest joint

Biology uses reward and its dopaminergic prediction error. A text agent has no reward.

The most principled available proxy is **the model's own token-level surprisal on the incoming turn**: dopamine encodes reward prediction error, and surprisal is prediction error in the only currency available. If generation exposes logprobs it costs nothing extra.

Weaker alternatives, all content-based and therefore closer to the importance-filter design P1 rejects: explicit user correction, affect markers, task boundaries, question density.

**Recorded as the design's largest unvalidated assumption.** If surprisal is a poor salience proxy, P2's capture mechanism distributes resources at random, and the architecture degenerates to uniform retention.

---

## 4. Capture — retroactive, symmetric (P2, P3)

Runs after each salience event. No model call.

```
on_salience(E):
    live = [ep for ep in store if ep.tag_expires_at > E.t - E.reach
                              and abs(ep.t - E.t) <= E.reach]
    pool = E.magnitude
    for ep in live:
        share = pool * kernel(abs(ep.t - E.t))     # symmetric decay in |Δt|
        ep.captured      += share
        ep.accessibility += CAPTURE_GAIN * share
```

**Three properties that distinguish this from every write-time filter:**

1. **Retroactive.** An episode's fate is decided after it is written, possibly much later.
2. **Symmetric.** Episodes *before* and *after* the salient event capture equally (P2). A mundane turn preceding a surprising one is consolidated by adjacency.
3. **Content-blind.** Capture never inspects the episode. A trivial turn beside a salient one outranks a substantive turn in a quiet stretch.

**That last property is the design's most falsifiable claim**, and the one most likely to be wrong in a text domain. In an organism, temporal proximity to a salient event is a good prior for relevance. In a conversation it may not be.

---

## 5. Consolidation — sequential replay (P3, P4, P8, P10)

Runs offline, between sessions.

```
consolidate():
    candidates = [ep for ep in store if ep.captured > C_THRESHOLD]
    for seq in contiguous_runs(candidates):          # sequential, P4
        # 1. strengthen co-replay connectivity
        for a, b in pairs(seq):
            edge(a, b).weight += REPLAY_GAIN / distance(a, b)

        # 2. recombine with existing semantic structure, P4
        for node in semantic_neighbours(seq):
            edge(node, seq).weight += REPLAY_GAIN
            node.strength += 1
            node.support += [ep.id for ep in seq]

        # 3. extractive gist, P8 — no generation
        invariant_spans = spans_recurring_across(seq, semantic_neighbours(seq))
        if invariant_spans:
            upsert SemanticNode(content=invariant_spans, support=seq)

        # 4. transformation: detail fades, gist persists, P8
        for ep in seq:
            ep.accessibility *= DETAIL_DECAY        # < 1
```

**Step 4 is the counter-intuitive one.** Consolidating an episode *lowers* its individual accessibility while raising the strength of the semantic node it supports. Gist becomes reachable; the specific episode recedes toward silence. The content is never deleted — provenance survives at full fidelity, and `support` links back.

That is P8 implemented literally: consolidation trades contextual detail for semantic strength.

**Step 3 is where fabrication would enter and is therefore extractive-only.** Recurring spans are copied. Nothing is written that was not said.

### 5.1 When does an agent sleep?

Biology consolidates offline. A deployed agent may never idle.

Options, none satisfying: after N turns of inactivity; on session boundary; on a background thread against a snapshot; or **awake ripples** — P3's actual finding is that selection happens during *awake* quiescence at reward, so consolidating immediately after each salience event is arguably the more faithful reading.

**Unresolved. The design does not depend on which is chosen, but the parameters do.**

---

## 6. Read path - controlled multi-route retrieval (P5, P6, P11-P15)

The load-bearing addition is a distinction between **retrieval capacity** and
**delivery capacity**. Biology does not appear to make a transcript-sized block
simultaneously active. A small foreground is repeatedly updated while much
larger distributed representations remain latent. Therefore a large engineering
context ceiling cannot stand in for a retrieval mechanism.

The controller below is mechanical. It does not ask a language model whether to
continue, does not generate a new query, and does not call the final reader until
retrieval has terminated.

```
retrieve(query, delivery_budget):
    q = embed(query)
    state = RetrievalState(
        goal_features = parse_features(query),
        context_vec   = q,
        unresolved    = obligations(query),
        route         = DIRECT,
        visited       = set(),
        step          = 0,
    )

    # Route 1: fast direct access to current semantic and episodic traces.
    direct = top_k_accessible(q, K_DIRECT)
    foreground = compete(direct, ACTIVE_CAP)
    state.active_ids = ids(foreground)
    state.visited |= state.active_ids
    state.unresolved -= mechanically_supported(foreground, state.goal_features)

    while state.unresolved and state.step < MAX_RETRIEVAL_STEPS:
        state.step += 1

        # Route 2: episodic pattern completion. A seed reinstates the
        # event-bound elements and encoding context, not arbitrary neighbours.
        if state.route == DIRECT:
            episode = strongest_event_seed(foreground, state.visited)
            completed = event_edges(episode, EDGE_EVENT, MAX_EVENT_ITEMS)
            state.context_vec = reinstate_context(episode)
            candidates = completed
            state.route = EPISODIC

        # Route 3: retrieved-context search. Recovered context, plus the
        # unchanged goal, cues the next item. No generated intermediate query.
        else:
            cue = normalize(GOAL_WEIGHT * q
                            + CONTEXT_WEIGHT * state.context_vec
                            + NEED_WEIGHT * vectorize(state.unresolved))
            candidates = top_k_unvisited(cue, K_CONTEXT, state.visited)
            state.route = CONTEXT

        winners = compete(candidates, ACTIVE_CAP)
        if no_novel_support(winners, state.unresolved):
            state.route = STOP
            break

        foreground = replace_foreground(foreground, winners, ACTIVE_CAP)
        state.active_ids = ids(foreground)
        state.unresolved -= mechanically_supported(foreground,
                                                    state.goal_features)
        state.context_vec = update_context(state.context_vec, winners)
        state.visited |= ids(winners)

    # Serialize only resolved evidence plus minimum provenance. Delivery is
    # downstream of retrieval and cannot decide what was reachable.
    selected = pack_evidence(foreground, delivery_budget)

    # Retrieval-induced plasticity, P6 - the read path WRITES.
    for ep in selected:
        ep.accessibility += RETRIEVE_GAIN
    for ep in suppressed_during_search:
        ep.accessibility *= RIF_PENALTY     # < 1

    return selected, state.route, state.unresolved
```

### 6.1 What the three routes mean

1. **Direct route.** Similarity/familiarity provides fast access when the natural
   cue is already diagnostic. This is the cheap path and may terminate retrieval.
   P18 supports retaining direct and generative modes as observed retrieval
   forms, but not treating them as proven independent biological systems.
2. **Episodic route.** A selected event seed activates only edges recorded as
   belonging to the same encoded event. This is pattern completion, not generic
   nearest-neighbour expansion.
3. **Retrieved-context route.** The recovered event context changes the cue for
   the next attempt while the original goal remains anchored. This supplies the
   chain, but the chain is over reinstated context rather than a mean of retrieved
   text embeddings.

The controller is **multi-route but not multi-model**. Its compute consists of
feature extraction, vector arithmetic, indexed lookup, typed edge traversal,
competition, bitset updates, and exact packing. The final language model sees the
result once. Adding a model call to decide the route or write the next cue would
replace the memory hypothesis with an agentic query-rewriting architecture.

### 6.2 Stopping without a second model call

The difficult engineering joint is `obligations(query)`. P14 and P17 support
goal-sensitive control and a retrieval/selection distinction; they do not
supply a natural-language obligation parser. It may use only
deterministic features available before inference: interrogative type, named
entities, explicit dates/units, requested list cardinality, conjunctions, and
stored schema keys. The controller stops when one of three conditions fires:

- all mechanically identifiable obligations have evidence;
- a step produces no new evidence for an unresolved obligation; or
- `MAX_RETRIEVAL_STEPS` is reached.

This is intentionally weaker than asking a model, "Do you have enough context?"
Open-ended prompts may expose no reliable obligations and terminate too early.
That limitation is falsifiable and preferable to hiding a second reasoner inside
the retriever.

### 6.3 Capacity is not a character count

`ACTIVE_CAP` limits foreground representations; `delivery_budget` limits the
serialized evidence shown to the final reader. They are independent. A compact
event node can stand for many bound details, so neither quantity maps cleanly to
human chunks. The biological claim is only that active access is selective and
small relative to latent storage, not that humans possess a particular token
window.

**Retrieval-induced plasticity makes the read path stateful**, which breaks the
pure-function property most memory components have. Frequently retrieved material
becomes easier to reach, while suppressed competitors can become harder to reach.
Two identical queries can therefore diverge after different retrieval histories.
That engineering cost is retained from P6 and must be tested independently of the
route controller.

---

## 7. Update path — supersession without deletion (P7, P9)

P7 says retrieval destabilizes. P9 says retrieval may create a new trace rather than modifying the old one. **Implementing P9 rather than P7 avoids a fabrication surface entirely.**

```
on_contradiction(retrieved_ep, new_content, t):
    new_ep = Episode(new_content, t, embed(new_content))
    new_ep.supersedes           = retrieved_ep.id
    retrieved_ep.superseded_by  = new_ep.id

    retrieved_ep.accessibility *= SUPERSEDE_DECAY    # → toward silence
    # edges untouched: storage intact, retrievability reduced

    edge(new_ep, retrieved_ep).weight = W_LINEAGE
```

**The superseded fact becomes a silent engram** — present, connected, provenance intact, unreachable by ordinary cue. A deliberate query can still walk the lineage edge and recover it.

This gives, without deletion and without rewriting:
- Current values reachable by default.
- Prior values recoverable on demand.
- Full audit trail of what changed and when.

Detecting contradiction without a model call is unsolved here. Embedding-space proximity plus a mismatch heuristic is the cheap approximation and is probably inadequate.

---

## 8. Where this differs from what has been built — read only after §§1–7

Deliberately withheld from the derivation.

| Design element | How deployed memory systems typically differ |
|---|---|
| **Accessibility separate from similarity** | Almost all systems collapse retrievability into one relevance score computed at query time. P5 says these are different substrates |
| **Retroactive, content-blind capture** | Every promotion or importance filter scores content at write time. P2 confers importance by temporal neighbours, afterwards |
| **Consolidation *lowers* episode accessibility** | Summarization systems raise the summary's prominence and keep or drop the source. Here the source is retained at full fidelity and quietly recedes |
| **Read path writes** | Retrieval is universally a pure function. P6 makes it a plasticity event |
| **Supersession by accessibility decay** | Append-only stores return both old and new values with no signal about which is current; overwriting stores destroy provenance. P9 gives a third option |
| **Similarity is one route, not the controller** | Similarity is usually the entire ranking function or is recursively applied by an LLM-generated query |
| **Small foreground, separate delivery ceiling** | Context-window systems usually equate what can be serialized with what has been retrieved |
| **Direct, episodic, and context routes** | Chained RAG usually applies one similarity operator repeatedly over a homogeneous store |
| **Mechanical retrieval controller** | Agentic retrieval commonly delegates query rewriting and stopping to another model call |

**The supersession mechanism (§7) is the element most likely to be independently valuable**, because it addresses a concrete failure mode — a memory that confidently returns a stale value — without either deleting history or calling a model.

### 8.1 The program's fixed 32,000-character ceiling

The program's 32,000-character retrieval allowance is an experimental control,
not a biological parameter. It was calibrated in Study 007 against one corpus,
renderer, model context, breadth gate, and targeted fixture. Later exact
achievability analysis found that at least 14/17 benchmark facts fit in 5,058
serialized characters and all 17 fit in 7,592. Therefore the benchmark's
remaining misses cannot generally be attributed to the raw 32,000-character
capacity. They are failures to reach and select evidence that would fit.

E006's chained retrieval repeatedly expanded a similarity-derived candidate
pool. The mechanism is not equivalent to P12-P14: it lacked typed event binding,
did not reinstate an encoding-context state, did not maintain unresolved query
obligations, and had no controller that could switch retrieval routes. The new
design does not explain away that result; it identifies a mechanically different
hypothesis.

---

## 9. Falsification plan

The design makes testable predictions. Ordered by cost.

**F1 — Do accessibility and similarity dissociate?**
Instrument both on any existing corpus. If accessibility (however initialized) never changes the ranking similarity would have produced, P5 buys nothing and the two-substrate model collapses to one.

**F2 — Is temporal proximity to a surprisal spike a useful relevance prior in text?**
Correlate distance-to-surprisal-spike against whether an episode is needed by a later query. **If null, §4 is dead and the architecture loses its formation mechanism.** Cheapest decisive test in the document; run it first.

**F3 — Does retrieval-induced suppression help or hurt?**
Ablate the read-path penalty. RIF is adaptive under cue overload in humans; whether an artificial store has that problem is unknown. **Suppressing material a later query needs is the obvious catastrophic failure.**

**F4 — Does sequential replay beat co-occurrence edges?**
P4 specifies sequential replay. Compare against edges built from plain co-occurrence.

**F5 — Does extractive gist survive contact with a budget?**
SemanticNodes plus full episodes cost more than episodes alone. If gist never displaces episodes under a real ceiling, §5 step 3 is dead weight.

**F6 — Does supersession-by-decay actually surface current values?**
Directly testable against any knowledge-update benchmark.

**F7 - Does event-bound completion beat generic similarity chaining?**
Hold first-hop seeds, candidate opportunity, delivery budget, and reader fixed.
Compare typed event-edge completion against repeated embedding expansion. If
the same identities are recovered in the same order, P12 adds no mechanism.

**F8 - Does a deterministic route controller improve retrieval?**
Compare direct-only retrieval with DIRECT -> EPISODIC -> CONTEXT switching. The
controller must improve required-evidence availability with zero targeted-query
losses and without any generated cue or additional inference call.

**F9 - Can mechanical sufficiency stop at the right time?**
Measure false-stop and needless-retry rates separately on explicit, enumerative,
and open-ended queries. If `obligations(query)` cannot distinguish missing
evidence from an inherently open request, the controller is not a general
retrieval solution.

---

## 10. Honest accounting

**Free parameters:** `A_INIT`, `TAG_WINDOW`, `REACH`, `S_THRESHOLD`, `CAPTURE_GAIN`, kernel shape, `C_THRESHOLD`, `REPLAY_GAIN`, `DETAIL_DECAY`, event-boundary rule, event minimum and maximum size, context persistence, `K_DIRECT`, `K_CONTEXT`, `ACTIVE_CAP`, `MAX_EVENT_ITEMS`, `MAX_RETRIEVAL_STEPS`, `GOAL_WEIGHT`, `CONTEXT_WEIGHT`, `NEED_WEIGHT`, support and novelty floors, `SUPPRESS`, `RETRIEVE_GAIN`, `RIF_PENALTY`, `SUPERSEDE_DECAY`, `W_ADJ`, `W_LINEAGE`. **At least twenty-nine.** No principled way to set most of them, and several interact multiplicatively. This is the design's most serious practical objection: it has more knobs than any experiment could tune, and a system with this many free parameters can be made to produce almost any result.

**Compute:** indexed direct search plus bounded typed-edge traversal and context retries. Cost is bounded by `MAX_RETRIEVAL_STEPS`, `K_CONTEXT`, and `MAX_EVENT_ITEMS`, but those same bounds can stop immediately before the needed trace.

**Loss of reproducibility:** retrieval-induced plasticity makes the store a function of its own query history. Two deployments given identical inputs in different order diverge permanently. Debugging, replay, and cache invalidation all become harder. The route controller itself remains deterministic given the same store state.

**Unresolved:**
- Salience without reward (§3.1).
- When consolidation runs (§5.1).
- Contradiction detection without a model call (§7).
- Whether RIF is adaptive here at all (F3).
- Deterministic extraction of retrieval obligations for open-ended language (§6.2).
- How event-bound edges are formed without smuggling task labels into storage.

**What survives even if the whole design fails:** the two-substrate model (§2) and supersession-by-decay (§7). Both are small, both are independently implementable, and both address failure modes that single-score relevance systems cannot express.

---

## 11. Added retrieval sources

- Cowan, N. et al. (2005). *On the capacity of attention: Its estimation and its
  role in working memory and cognitive aptitudes.* Cognitive Psychology 51,
  42-100. https://doi.org/10.1016/j.cogpsych.2004.12.001
- Baldassano, C. et al. (2017). *Discovering event structure in continuous
  narrative perception and memory.* Neuron 95, 709-721.e5.
  https://doi.org/10.1016/j.neuron.2017.06.041
- Ben-Yakov, A. & Henson, R. N. (2018). *The hippocampal film editor:
  sensitivity and specificity to event boundaries in continuous experience.*
  Journal of Neuroscience 38, 10057-10068.
  https://doi.org/10.1523/JNEUROSCI.0524-18.2018
- Badre, D. et al. (2005). *Dissociable controlled retrieval and generalized
  selection mechanisms in ventrolateral prefrontal cortex.* Neuron 47,
  907-918. https://doi.org/10.1016/j.neuron.2005.07.023
- Grande, X. et al. (2019). *Holistic recollection via pattern completion
  involves hippocampal subfield CA3.* Journal of Neuroscience 39, 8100-8111.
  https://doi.org/10.1523/JNEUROSCI.0722-19.2019
- Harris, C. B. & Berntsen, D. (2019). *Direct and generative autobiographical
  memory retrieval: How different are they?* Consciousness and Cognition 74,
  102793. https://doi.org/10.1016/j.concog.2019.102793
- Horner, A. J. et al. (2015). *Evidence for holistic episodic recollection via
  hippocampal pattern completion.* Nature Communications 6, 7462.
  https://doi.org/10.1038/ncomms8462
- Kahana, M. J. (1996). *Associative retrieval processes in free recall.* Memory
  & Cognition 24, 103-109. https://doi.org/10.3758/BF03197276
- Lohnas, L. J., Healey, M. K. & Davachi, L. (2023). *Neural temporal context
  reinstatement of event structure during memory recall.* Journal of
  Experimental Psychology: General 152, 1840-1872.
  https://doi.org/10.1037/xge0001354
- Manning, J. R. et al. (2011). *Oscillatory patterns in temporal lobe reveal
  context reinstatement during memory search.* PNAS 108, 12893-12897.
  https://doi.org/10.1073/pnas.1015174108
- Polyn, S. M., Norman, K. A. & Kahana, M. J. (2009). *A context maintenance and
  retrieval model of organizational processes in free recall.* Psychological
  Review 116, 129-156. https://doi.org/10.1037/a0014420
- Tomita, H. et al. (1999). *Top-down signal from prefrontal cortex in executive
  control of memory retrieval.* Nature 401, 699-703.
  https://doi.org/10.1038/44372
- Polyn, S. M. et al. (2005). *Category-specific cortical activity precedes
  retrieval during memory search.* Science 310, 1963-1966.
  https://doi.org/10.1126/science.1117645
- Rajasethupathy, P. et al. (2015). *Projections from neocortex mediate top-down
  control of memory retrieval.* Nature 526, 653-659.
  https://doi.org/10.1038/nature15389
- Wolff, M. J. et al. (2017). *Dynamic hidden states underlying working-memory-
  guided behavior.* Nature Neuroscience 20, 864-871.
  https://doi.org/10.1038/nn.4546

---

*Drafted August 7, 2026; retrieval architecture revised August 11, 2026. Speculative. No mechanism herein is authorized; each would require a ledger entry, a decisive test, a kill condition, and live evaluation. Biological plausibility has no standing as evidence.*
