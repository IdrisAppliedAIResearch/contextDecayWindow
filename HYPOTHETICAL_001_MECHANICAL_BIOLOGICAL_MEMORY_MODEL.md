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

**Invariants**
- `content` is never rewritten. Transformation acts on `accessibility` and `edges`, never on stored text.
- `accessibility == 0` with `edges` intact is a **silent engram**: stored, connected, unreachable by cue. A legal and expected state, not a bug.
- `SemanticNode.content` contains only spans copied from `support` episodes. **No generated text anywhere in the memory path.**

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

## 6. Read path — spreading activation with competition (P5, P6)

```
retrieve(query, budget):
    q = embed(query)

    # 1. seeding — the ONLY place similarity is used
    seeds = {ep: sim(q, ep.embedding) * ep.accessibility
             for ep in store if sim(q, ep.embedding) > K}

    # 2. spread over the storage substrate, P5
    act = seeds
    for depth in 1..D:
        for ep, a in act.items():
            for (tgt, w) in ep.edges:
                act[tgt] += a * w * DECAY**depth

    # 3. competition, P6
    for group in cue_groups(act):
        winner = argmax(group)
        for loser in group - {winner}:
            act[loser] *= SUPPRESS          # < 1

    # 4. pack under budget
    selected = pack(sorted(act, desc), budget)

    # 5. retrieval-induced plasticity, P6 — the read path WRITES
    for ep in selected:
        ep.accessibility += RETRIEVE_GAIN
    for ep in suppressed_this_query:
        ep.accessibility *= RIF_PENALTY     # < 1

    return selected
```

**Similarity appears exactly once, at seeding.** Everything after is graph traversal weighted by accessibility. That is P5 taken seriously: the storage substrate is connectivity, and similarity is only a way in.

**Step 5 makes the read path stateful**, which breaks the pure-function property most memory components have. Retrieval changes the store. That is P6, and it means:

- Frequently retrieved material becomes progressively easier to reach.
- Competitors of frequently retrieved material become progressively harder to reach, and can be driven to silence.
- **Two identical queries in sequence do not return identical results.**

The last is a serious engineering cost — no replay, no deterministic reproduction, no cache. It is also exactly what the literature describes.

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
| **Similarity used once, at seeding** | Similarity is usually the entire ranking function |

**The supersession mechanism (§7) is the element most likely to be independently valuable**, because it addresses a concrete failure mode — a memory that confidently returns a stale value — without either deleting history or calling a model.

---

## 9. Falsification plan

The design makes testable predictions. Ordered by cost.

**F1 — Do accessibility and similarity dissociate?**
Instrument both on any existing corpus. If accessibility (however initialized) never changes the ranking similarity would have produced, P5 buys nothing and the two-substrate model collapses to one.

**F2 — Is temporal proximity to a surprisal spike a useful relevance prior in text?**
Correlate distance-to-surprisal-spike against whether an episode is needed by a later query. **If null, §4 is dead and the architecture loses its formation mechanism.** Cheapest decisive test in the document; run it first.

**F3 — Does retrieval-induced suppression help or hurt?**
Ablate step 5's penalty. RIF is adaptive under cue overload in humans; whether an artificial store has that problem is unknown. **Suppressing material a later query needs is the obvious catastrophic failure.**

**F4 — Does sequential replay beat co-occurrence edges?**
P4 specifies sequential replay. Compare against edges built from plain co-occurrence.

**F5 — Does extractive gist survive contact with a budget?**
SemanticNodes plus full episodes cost more than episodes alone. If gist never displaces episodes under a real ceiling, §5 step 3 is dead weight.

**F6 — Does supersession-by-decay actually surface current values?**
Directly testable against any knowledge-update benchmark.

---

## 10. Honest accounting

**Free parameters:** `A_INIT`, `TAG_WINDOW`, `REACH`, `S_THRESHOLD`, `CAPTURE_GAIN`, kernel shape, `C_THRESHOLD`, `REPLAY_GAIN`, `DETAIL_DECAY`, `K`, `D`, `DECAY`, `SUPPRESS`, `RETRIEVE_GAIN`, `RIF_PENALTY`, `SUPERSEDE_DECAY`, `W_ADJ`, `W_LINEAGE`. **Eighteen.** No principled way to set most of them, and several interact multiplicatively. This is the design's most serious practical objection: it has more knobs than any experiment could tune, and a system with eighteen free parameters can be made to produce almost any result.

**Compute:** spreading activation over a growing edge set per query, with edge density rising as replay adds connections. Cost grows superlinearly in stored episodes unless traversal is bounded — and bounding it is the thing depth `D` already does, which caps reach.

**Loss of reproducibility:** §6 step 5 makes the store a function of its own query history. Two deployments given identical inputs in different order diverge permanently. Debugging, replay, and cache invalidation all become harder.

**Unresolved:**
- Salience without reward (§3.1).
- When consolidation runs (§5.1).
- Contradiction detection without a model call (§7).
- Whether RIF is adaptive here at all (F3).

**What survives even if the whole design fails:** the two-substrate model (§2) and supersession-by-decay (§7). Both are small, both are independently implementable, and both address failure modes that single-score relevance systems cannot express.

---

*Drafted August 7, 2026. Speculative. No mechanism herein is authorized; each would require a ledger entry, a decisive test, a kill condition, and live evaluation. Biological plausibility has no standing as evidence.*
