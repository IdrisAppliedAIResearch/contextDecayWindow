# Rank Fine, Pack Fine, Call Nothing

### A deterministic memory path for long conversations, and the eleven experiments that cut it down to size

**Idris Applied AI Research** — independent, non-profit
Repository: `contextDecayWindow` · Licence: CC BY 4.0
Preprint — PAPER-002 · supersedes PAPER-001

---

## Executive summary

**The claim.** A conversational memory layer needs no generative model calls. This
one stores every exchange verbatim, ranks candidates by embedding similarity at the
finest unit that stays informative, and packs a fixed character budget with a
set-level coverage objective. Nothing in the path asks a model to write text about
the store. On a sealed external holdout it beats its own strongest control by a
margin that is not close.

**The headline result.** On six LoCoMo conversations sealed until the bars were
locked — 1,098 question-answer records, a 16,000-character budget, **zero model
calls and zero embedding calls during measurement** — ranking adjacent-turn pairs by
their own cosine raises complete evidence delivery from **843 to 935 of 1,098**
against session-score inheritance, and from **258** against source order. 140 gains,
48 losses, gain/loss ratio 2.92 against a registered bar of 2.0, one-sided exact
binomial **p = 6.19e-12**. All six conversations are net positive. The replay hash
equals the committed hash.

**Why the unit is the lever.** The same change reproduces on two more corpora and
the mechanism is legible. LongMemEval evidence episodes have median **2,550
characters**; the exact source turns carrying their answers have median **298**.
Ranking the 2,550-character parent dilutes the match. Split it, rank each turn by
its own cosine, and exact evidence delivery goes from **361 to 461 of 465** — 100
gains, zero losses, p = 7.89e-31. On the internal store the same move takes an
enumeration probe from 12 to 14 of 17 with zero targeted losses.

**Why no model calls matters, stated as measured properties rather than preference.**
`context()` is a pure function of store state, query and budget, verified
byte-identical across two processes; 132 committed selection payloads and 3 rendered
blocks reproduce their SHA-256 through the installed library. Every delivered
character is a stored episode verbatim, so there is no generated text about the
store that can be wrong. The systems that ship in this space spend a language-model
call on exactly this layer. **The question this paper answers is not whether the
deterministic version wins. It is how much of the layer survives without the call.**

**What it costs.** Disk is trivial — 4,743 bytes per turn, about 48 MB at ten
thousand turns. Retrieval time binds first: **190 ms at 1,000 candidates**, 81% of
it in clustering and that share still rising. On this hardware the design is
comfortable to a few thousand episodes and unusable in an interactive loop somewhere
before ten thousand. The obvious fix — prune low-similarity candidates to control
cost — is the one operation measured here to break retrieval, so retention is
unbounded by policy and the trimming knob carries an `unsafe_` prefix.

**What this does not establish, in four lines.**

- **The instrument's run-to-run band is 3.0 points on a 13-point rubric, measured
  rather than assumed.** No *scored* comparison in this arc below about three points
  is demonstrated — including the memory-tier contrast this programme would most
  like to keep. The offline delivery counts above are unaffected: they are counts and
  identities, not scores.
- **Availability is not correctness, and one live run showed them moving in opposite
  directions.** The configuration that made six more facts available scored *lower*
  on targeted probes and failed its own pre-registered bar. It is **not promoted**.
- **No competing system was run here.** Mem0, Zep, Letta and HippoRAG are cited from
  their published results and compared on axes that are commensurable, never on a
  head-to-head number that does not exist.
- **The internal breadth findings rest on a single enumeration probe.** The external
  confirmations do not.

**Read next.** §5 for the confirmatory results, §6 for the granularity mechanism,
§12 for the complete limits. Figure 1 is the sealed holdout; Figure 5 draws the
instrument band across every scored verdict in the arc.

---

## Abstract

We report a deterministic memory layer for long conversations that makes no
generative model calls, and the eleven pre-registered experiments that reduced it to
four components. The surviving design is an append-only verbatim store, a recency
window, cosine-threshold similarity retrieval, and a set-level coverage objective,
packed against one character budget at exact serialized cost.

The programme's central positive result is a granularity rule confirmed on a sealed
external holdout. On six LoCoMo conversations withheld until bars, endpoint and
budget were locked, ranking adjacent-turn pairs by their own cosine raises complete
exact-evidence delivery from 843 to 935 of 1,098 over assigning each pair its
session's maximum score, with 140 gains against 48 losses (ratio 2.92, one-sided
exact p = 6.19e-12) and every conversation net positive; source order reaches 258.
The result is bounded to evidence availability and authorizes no reader claim.

Two further corpora locate the mechanism. On 465 turn-labelled LongMemEval
questions, own-turn ranking raises any-exact-evidence delivery from 361 to 461 with
100 gains and no losses; evidence turns have median 298 characters against 2,550 for
their parent episodes, and parent length correlates with worse normalized own-cosine
rank at Spearman rho 0.484. On the internal 121-turn store the same substitution
takes an enumeration probe from 12 to 14 of 17 with 21 of 21 targeted items
preserved. Because splitting changes character count and semantic localization
together, the rule is stated conditionally: rank at the finest unit whose embedding
remains informative, and pack at the finest affordable unit.

Underneath sits a decomposition of retrieval failure into three constraints that
bind in a forced order. The candidate pool binds first and structurally — one of
four domains has no representative anywhere in the deployed shortlist, so no
selection rule reaches it from there. The objective binds second and only after: run
on the deployed pool, the shipped objective scores below the baseline it replaces.
A similarity floor binds last, at a query cosine no reweighting closes. Capacity was
never the constraint: an exact optimum computed with the answer key makes 14 of 17
items available in 5,058 of 32,000 characters while deployed selection made 6
available and spent 31,946.

We report the negative results at the same resolution. Write-time selection failed
in five studies because it cannot anticipate a later query; moving selection to
query time failed in a registered bakeoff; graph construction, query routing,
approximate search, query segmentation and attention-derived term selection each
failed their own gates. Three sealed-holdout experiments returned no signal at all.
We also report the instrument: five replicates under identical conditions scored
8.0, 8.0, 8.0, 8.0 and 11.0, so the run-to-run band is 3.0 points and three of the
arc's scored verdicts fall inside it and are labelled not demonstrated. The offline
delivery results are counts and identities and are unaffected.

---

## 1. Introduction

A long conversation forces a trade. Keep the whole transcript and the model slows
down and loses the middle. Summarize it and the details are gone. A third option is
to store every exchange verbatim and rebuild a small, relevant context each turn,
which moves the problem from compression to selection.

This paper is about that third option, built and measured over eleven pre-registered
experiments. Most of the mechanisms failed. What survived is smaller than what the
programme set out to build, and the reason it is worth reading is that the survivor
is now confirmed on a corpus this programme did not construct, and that the failures
are specific enough to name.

The one-sentence result: **the unit you rank is a bigger lever than the rule you
rank with, and neither requires a language model.**

### 1.1 What kind of paper this is

A single-programme experience report with one external confirmation. One internal
corpus, one rubric locked since the second study, one local model at one
quantization, one machine, one seed. Every *scored* comparison is a single run, and
§12.1 gives the measured variance that bounds them.

That scope applies to the scored results. It does not apply to the deterministic
ones, and the distinction decides most of what this paper is permitted to say. The
delivery counts in §5 and §6 are produced with zero model calls, reproduce
byte-identically on replay, and are verified against committed hashes. They are
counts and identities rather than judgements. Where a result is one of those, this
paper states it plainly; where it is a score, it carries its band.

### 1.2 Contributions

1. **A granularity rule with a sealed external confirmation** (§5, §6). Ranking at
   the finest informative unit, confirmed prospectively on six withheld LoCoMo
   conversations and reproduced on two further corpora with the size mechanism
   measured rather than asserted.
2. **A decomposition of where retrieval failure lives** (§7): a candidate pool, a
   selection objective, and a similarity floor. They are not independent — they bind
   in a forced order, and applying the second fix without the first makes the shipped
   configuration worse than the baseline it replaces.
3. **The measurement that makes the decomposition possible**: a per-fact known
   optimum computed on the same store under exact serialized-cost accounting (§7.1).
   It costs an answer key and exact cost accounting, which is why it is unusual
   rather than difficult.
4. **A subtraction result** (§10): twelve mechanisms removed, each by its own gate,
   and the argument that the properties making the survivor deployable followed from
   the removals.
5. **A correction record** (§11) including the instrument's own measured noise band,
   and one case where a diagnostic written to catch a specific failure class nearly
   committed that exact failure.

### 1.3 What this paper does not claim

No scored difference below about three points in this arc is claimed as real; §12.1
gives the measurement. No comparison against HippoRAG, Mem0, Zep or Letta was run,
and §2 says exactly what is and is not being compared. No general claim that
similarity retrieval fails — §7.4 measures the opposite on eight of nine internal
probes and §8 measures it on 470 external ones. No novelty for maximal marginal
relevance, facility location or submodular selection, which are established methods;
what is offered is the decomposition and the measurement, not the selector. And no
claim that the internal 12 of 17 is good: it sits below the programme's registered
bar of 14, and below the 15 a known optimum reaches on the same store for a sixth of
the cost.

---

## 2. Related work and positioning

Studies 001–010 were designed and run before this programme's first literature scan,
and are committed with SHAs that show it. We state that once, because it explains why
early designs rediscovered known ideas, and press it no further: arriving
independently at a worse version of a published method is not a contribution.

**Entity-centric indexing.** HippoRAG builds a knowledge graph over extracted
entities and retrieves by traversal; the authors' own follow-up identifies
entity-centricity as a limitation. This programme's hardest repeated failure is
consistent with that. Six target facts sit in spans where the entity extractor finds
zero entities, so an entity-gated index has no path to them, which is why entity
extraction was ruled out as a primary index here.

**Structure over retrieved units.** GraphRAG, SGMem and CodaRAG impose explicit
structure on retrieved material. This programme built the corresponding mechanism —
an associative graph over observed co-activation — and no configuration cleared its
advancement gate (§10).

**Deployed memory systems.** Letta, Mem0 and Zep ship in this space. Full citation
detail, published numbers and verification status are in
`paper/notes/COMPETITIVE_LANDSCAPE.md`.

### 2.1 What is and is not being compared

**No system named above was run here.** Every number attributed to one is cited from
its publication and labelled as such.

More importantly, the measures differ. Mem0 and its neighbours report LLM-judged
question-answering accuracy on LoCoMo. This paper reports deterministic evidence
availability at a fixed character budget: whether the text carrying an answer was
present in the delivered context, established without a model in the loop. Placing
those two in one column would be exactly the substitution this programme's own
operating manual names as its recurring failure — *a surrogate that can pass without
the property it claims to certify*. We do not place them in one column.

What is comparable is architectural, and the axes are countable from either system's
own description:

| Axis | This component | Systems that spend a call on this layer |
|---|---|---|
| Generative calls per stored turn | **0** | At least one extraction call per turn |
| Delivered text | Stored episodes verbatim | Model-written summaries or extracted facts |
| Replayability | `context()` byte-identical across processes; 132 payloads reproduce by SHA-256 | Bounded by generation determinism |
| Failure mode | An episode is not delivered | An episode is not delivered, or is delivered as a wrong paraphrase |
| What is measured | Evidence availability | Judged answer accuracy |

The honest framing, which this programme committed to before it had the external
result: **the question is rarely whether the deterministic version wins. It is how
much of the layer survives without the call.** A mechanism that recovers most of it
and still loses a head-to-head is a finding, and one this paper is not in a position
to report either way.

One boundary is load-bearing and appears again in §12.5. The LongMemEval authors'
LLM-assisted indexing and time-aware query expansion were available to this
programme and were deliberately not adopted, because they add generative calls to
the memory path and would change the component under test. Some of the gap between
this component's external numbers and published ones is that choice, and this paper
does not get to claim the choice was free.

**The placement is narrow.** Every system above consumes a candidate set produced
upstream by similarity ranking. This paper measures that set.

---

## 3. The architecture

Stated first, because it is the result. What follows in §5 through §10 is the
evidence for why it is this small.

### 3.1 What it is

Four components, and one budget.

| Component | What it does |
|---|---|
| **Append-only verbatim store** | Every user message and its assistant reply, kept as stored. Nothing is rewritten, summarized, or distilled |
| **Recency window** | The last *N* episodes, unconditionally |
| **Similarity retrieval** | Cosine over embeddings against the query, admitted above a threshold |
| **Set-level coverage objective** | Chooses a delivered set by what each candidate *adds* to those already chosen, rather than scoring each independently |

Everything is packed against one hard character budget, charged at exact serialized
cost — per-episode tags, metadata and separators included, not just source text.
That accounting was not always right, and correcting it moved published numbers by
up to 68% (§11.1).

### 3.2 The property that matters

**There are no generative model calls anywhere in the memory path.** Nothing in it
asks a model to write text about the store.

This is not the absence of model calls, and the distinction is one this paper's
predecessor got wrong and had to correct. `context()` embeds the query on every
call and `append()` embeds every episode, so an embedding model must be resident.
What follows from the architecture is narrower and checkable: the memory path emits
no generated text, and its output is reproducible **given a pinned embedder** —
which is why the library asserts a sentinel vector hash on every store open rather
than assuming one (§11.3).

Two consequences are measured rather than argued:

- **Replayability.** `context()` is a pure function of store state, query and
  budget, verified byte-identical across two processes. All 132 committed selection
  payloads and all 3 committed rendered blocks reproduce their SHA-256 byte-for-byte
  through the installed library, with the full suite at 1,007 tests.
- **Provenance.** Every delivered character is a stored episode verbatim. There is
  no generated text about the store that can be wrong, because nothing generates
  any.

### 3.3 Why those properties were bought, not designed

*Interpretation, not measurement. The properties are measured; the causal story is a
reading of this programme's history.*

The component is reproducible because distillation was removed, and distillation was
the component whose output could vary run to run. It preserves provenance because
every mechanism that generated text about the store failed its own gate and was
taken out. Stated plainly: **the properties that make this component deployable were
bought by the failures, not by the design.** A programme that had succeeded at
distillation would have shipped something harder to test and harder to audit.

### 3.4 One correction that travels with the description

The list in §3.1 describes the component as it now exists in the installable
library, where the recency window is a genuine last-*N* window. **No live study
behind the results in this paper ran one.** The studies ran two different rules under
that name: a least-recently-delivered rotation over the whole store in the most
recent work, and before it a block that locked onto the conversation's first nine
turns and held them for 111 consecutive turns. Mean overlap with a true window of the
same size is 0.205. §11.4 gives the measurements. Nothing in this programme
establishes what a correctly implemented window would score, in either direction.

---

## 4. How results are graded

This section is what licenses the confident voice everywhere else. The programme's
own operating manual is explicit that its recurring failure is a surrogate that can
pass without the property it certifies, so results here are graded by how they were
obtained, before anyone looks at what they say.

### 4.1 The standing taxonomy

Four levels. Applied once, here, so the prose does not hedge sentence by sentence.
The full assignment for every number in this paper is in
`paper/notes/EVIDENCE_SPINE.md`.

| Standing | Requirement | How this paper states it |
|---|---|---|
| **CONFIRMATORY** | Pre-registered; sealed holdout; bars, endpoint and budget locked before the number existed; registration commit carries no implementation file | As an established result, with its scope cap |
| **DETERMINISTIC-OFFLINE** | Zero generative calls; counts and identities, not scores; byte-identical on replay | As measured, with the corpus named. Not a benchmark score |
| **NOT DEMONSTRATED** | A scored live comparison whose gap falls inside the measured 3.0-point band | With the number *and* the label |
| **WITHDRAWN** | Corrected in `ERRATA.md` | Not at all. The list is `paper/notes/DO_NOT_WRITE.md` |

Five results in the entire arc reach CONFIRMATORY. Three of those five are negative.

### 4.2 The machinery behind those grades

**Pre-registration.** Each study's design was committed before implementation, and
that commit's SHA is the integrity anchor. Registration commits contain no
implementation files, which is checkable and was checked. Amendments never edit a
locked registration; they are standalone files recording whether they preceded the
result they affect.

**Preflight, in two parts, before any run.** Part 1 characterizes the mechanism
empirically — *not by reading the code, not by trusting its name, not by citing a
prior study*. Part 2 is a ten-item checklist where "assumed" is not an answer and
"verified at `<SHA>`" is. Two items earn their place repeatedly: PF4 asks whether the
registered thresholds are achievable at all, and PF9 asks the surrogate question —
*can this pass while the property it certifies is false?*

**Gates that bind and run before inference.** Study 008 stopped at its pre-run gates
when replay proved no registered fill cap between 1 and 50 could pass the breadth and
targeted gates jointly, preventing four invalid 121-turn runs. A gate is trusted to
stop only after showing that its tested population and its non-stopping alternative
were capable of existing; an empty join or an inert treatment is an instrument
failure, not a mechanism result. §5.4 and §11.5 each report one.

**Leakage control.** Mechanism code — retrieval, formation, ranking, gating — may not
read the answer key; measurement may. The boundary is enforced by grep, import-graph
checks, and a planted test violation that must be caught.

**Sealed scoring.** Three blind passes with registered adjudication triggers. Every
arm's scores are committed before anyone opens a mechanism log, and git order is the
evidence.

### 4.3 What a stop means

A stop closes a design, not a question, and this paper distinguishes two kinds
throughout. A **mechanism stop** means the thing was tested and did not work. An
**instrument stop** means the test could not have detected the thing. Reporting the
first when it was the second is how a programme accumulates false confidence, so
each stop below says which it was.

---
