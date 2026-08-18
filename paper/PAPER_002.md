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

## 5. The confirmatory results

Five results in this arc were obtained under a sealed holdout with bars locked
before the number existed. This section reports all five. Three returned nothing,
and they are here at the same resolution as the two that did, because a programme
that reports only its sealed successes has not earned the standing its sealed
successes carry.

### 5.1 NF-004 — ranking granularity, confirmed on withheld LoCoMo conversations

**Standing: CONFIRMATORY.** Pre-registration `95f0d25c`. Ten LoCoMo conversations
were split whole-conversation — so no question could share dialogue across the split
— by a seeded hash committed before any question, answer, category or evidence list
was opened. Four went to development. **Six were sealed and not touched until the
bars, the endpoint and the budget were locked.**

The question is what a candidate should be scored *by*. The baseline gives every
adjacent-turn pair the maximum query cosine attained by any pair in its session — a
session-level score inherited downward, which is what a system does when it ranks
sessions and then packs their contents. The treatment gives each pair **its own**
cosine. Both pack identical candidates under an identical 16,000-character
skip-on-overflow rule. Nothing else differs.

On 1,098 fully resolvable question-answer records, with **zero model calls and zero
embedding calls during measurement**:

| Arm | Complete evidence delivered | Any evidence |
|---|---:|---:|
| Source order (no ranking at all) | 258 / 1,098 | 352 / 1,098 |
| `S_SESSION_RANK` — inherited session score | 843 / 1,098 | 950 / 1,098 |
| **`P_PAIR_RANK` — own cosine** | **935 / 1,098** | **1,027 / 1,098** |

140 gains, 48 losses, 910 ties. Net +92. Gain/loss ratio **2.92** against a
registered bar of 2.0. One-sided exact binomial **p = 6.19e-12**. Median packed
characters 15,986 against 15,988, so the treatment is not simply spending more.
Median best-evidence rank moves **9 to 2**; p90 moves **80 to 34**, and those rank
statistics were opened only after the disposition was committed.

**Every one of the six sealed conversations is net positive**: +7, +6, +13, +30, +15,
+21. So are all five source categories. At the 32,000-character secondary the
direction holds, 961 to 1,024.

Gates G0 through G7 all pass, including a vector seal reading 2,749 of 2,749 cached
vectors with zero misses, and a G7 replay whose SHA-256 equals the committed G6
hash. Figure 1.

**Scope cap, and it is binding.** This is availability: whether the text carrying an
answer was present in the delivered context. It is not accuracy, and the
registration authorizes no reader, live, promotion or adoption claim. §12.3 is where
that distinction has teeth.

**What the source-order control buys.** 258 against 843 is the reason the treatment
effect cannot be read as a budget artifact. If the budget were slack enough that
ordering barely mattered, the unranked control would sit near the ranked arms. It
sits 585 items below. A development-side sweep across budgets from 4,000 to 96,000
characters makes the same point at every truncated point, and ties only at 96,000,
where everything fits and ordering is irrelevant by construction.

### 5.2 DMR-004 — no mechanical sufficiency signal *(negative)*

**Standing: CONFIRMATORY.** The strongest confirmatory construction in the
repository, and it returned nothing.

The question: can a model-free precedence parser over query text alone identify when
a query's evidence obligations are *finite* — when a retriever can know it has
enough and stop? A positive result would have given the deterministic stack an
adaptive controller. Sealed 180-query holdout, two blind raters, and PF3 verifying
the entire commit ordering from git history: protocol, then labels, then
registration, then compiler, then holdout labels, then gates, with the registration
commit carrying exactly one file.

| Registered criterion | Bar | Result |
|---|---|---|
| Youden's J | ≥ 0.50 | **0.320 — FAIL** |
| False-finite rate | ≤ 0.15 | **0.188 — FAIL** |
| `LOOKUP` recall | ≥ 0.60 | 0.800 — PASS |
| Well-formed span share | — | 1.000 — PASS |

Raw accuracy was 0.706. An always-`OPEN` degenerate control scores **0.650**, which
is precisely why J and not accuracy was the registered statistic: a 5.6-point margin
over answering "I cannot tell" to everything is not a controller. The two human
raters reached J of about 0.76 against the compiler's 0.320, with Cohen's kappa of
0.770 — so the task is doable and the mechanism did not do it.

The failure structure is specific. Of 31 misses, 12 are questions of the form *which
happened first* — a family flagged in writing before the compiler existed and
deliberately not patched, because patching a known family after seeing its cost is
the rescue `AGENTS.md` §9.4 forbids. Adding the registered markers `first` and `last`
moved development J from 0.363 to **0.220**: implementing the lock faithfully made it
worse.

**Disposition:** a model-free adaptive controller is not authorized on this
evidence, and the registration forbids replacing the compiler with a second
language-model call inside this arc. That closes the deterministic stopping line,
which is why the shipped component has no adaptive controller in it.

### 5.3 DMR-001 and DMR-001C — event formation *(negative, then split)*

**DMR-001. Standing: CONFIRMATORY.** Does an absolute embedding-drift threshold form
a usable event substrate? 2,000-episode sealed holdout. **52 of 74 events close
because the size cap binds — forced fraction 0.703 against a bar of 0.35.** The size
cap became the partitioner. Drift precision was perfect on the boundaries it did
find, 20 of 20, and irrelevant, because 0 of 52 forced boundaries matched anything.
The locked threshold sits above the holdout's 95th percentile while firing on 18.5%
of development episodes against 1.2% of holdout — an absolute drift threshold is not
a transferable quantity.

Two cautions travel with this. The second gate check was **unreachable by
construction**, a preflight defect recorded rather than repaired; the disposition
does not depend on it. And the two descriptive gates were computed after the stop —
they are not cited as results anywhere in this paper.

**DMR-001C. Standing: CONFIRMATORY, and it splits.** A relative percentile rule was
frozen at its predecessor's anchor, and 50 unread LongMemEval haystacks — 11,453
episodes, 2,128 real session seams — were fetched *after* the freeze.

- **Transfer confirmed.** Per-stream fire rate holds between 3.41% and 7.35%, p05 to
  p95 ratio **1.67x**, against the fixed rule's 9x to unbounded. The operating point
  moves across corpora; the relative rule survives the move.
- **Boundary claim refuted.** Macro F1 of **0.387** against a control that chops
  every four episodes regardless of content, at **0.606**. The detector loses to a
  fixed chop by 0.219.

The report then audits its own statistic: macro F1 against a corpus with seams every
5.4 episodes rewards frequent firing, so it was a poorly chosen bar. **It is not
re-scored.** Choosing a better statistic after seeing the number is the same rescue
the previous section refused.

### 5.4 SAL-001 — no independent surprisal signal *(negative)*

**Standing: CONFIRMATORY.** Does a surprisal-proximity signal identify what deserves
capture, independent of what is already retrievable? Deterministic 60-history
LongMemEval holdout, label-blind scoring sealed, 92 session-level AUC replications.

Adjusted neighbour AUC **0.41599** against a bar of 0.60. One-sided permutation
**p = 0.99134** against a bar of 0.01. Bootstrap 95% interval [0.35132, 0.48388].
**Five of six strata fall below chance.** The registered effect is not weak; it is in
the opposite direction. That kills the surprisal-based capture line the programme's
design document had proposed.

### 5.5 What five sealed experiments bought

One positive result, on the unit of ranking, that reproduces on every corpus tried
and every conversation inside the sealed one. Three well-built negatives that each
closed a line the programme wanted: adaptive stopping, event segmentation, and
surprisal-based capture. One split verdict where the transfer property confirmed and
the claim built on top of it did not.

The shipped component contains none of the three killed mechanisms. That is the
subtraction §10 completes, and this section is where most of it was paid for.

---

## 6. Granularity: rank at the finest informative unit

§5.1 confirmed the direction on withheld data. This section locates the mechanism,
using corpora that were already observed and are therefore reported as measured
rather than confirmed.

### 6.1 The size of a candidate

**Standing: DETERMINISTIC-OFFLINE.** Zero model calls.

| Unit | Median characters |
|---|---:|
| LongMemEval evidence *episode* | **2,550** |
| The exact source *turn* carrying the answer | **298** |
| LoCoMo adjacent-turn pair | **241** |

An embedding of a 2,550-character episode is an average over everything that episode
discusses. If one sentence in it answers the query, the query's match against the
whole is diluted by the rest. This is measurable rather than rhetorical: across the
corpus, **longer parents have worse normalized own-cosine evidence rank at Spearman
rho 0.484**. Separately, 831 of 881 evidence flags fall on user turns rather than
assistant turns, so the dilution is asymmetric in a way that matters for what a
system should index.

### 6.2 NF-005 — splitting episodes into their source turns

465 turn-labelled LongMemEval questions, 32,000-character budget, packing unit held
fixed at the turn so that only the *ranking* unit varies.

| Ranking unit | Packing unit | Any exact evidence | All exact evidence |
|---|---|---:|---:|
| Source order | Turn | 64 / 465 | 7 / 465 |
| Episode | Episode | 351 / 465 | 201 / 465 |
| Episode | Turn | 361 / 465 | 208 / 465 |
| **Turn (own cosine)** | Turn | **461 / 465** | **454 / 465** |

**100 gains, 0 losses, 365 ties. One-sided exact binomial p = 7.89e-31.** Median best
evidence rank moves 5 to 1; p90 moves 131 to 7. The budget delivers 109 turns where
it delivered 46 episodes.

Gates G0 through G8 pass. The vector seal reads 167,918 cached vectors with zero
misses. The final outcome hash and its replay hash are identical.

**Scope cap.** Splitting an episode changes its character count *and* its semantic
localization at the same time. This result supports candidate information dilution
as the moderator; **it does not isolate raw character count**, and no experiment here
does.

### 6.3 NF-003 — where the rule reverses, and why it is stated conditionally

The same corpus, varying ranking and packing independently:

| Ranking unit | Packing unit | Strict answer-episode delivery |
|---|---|---:|
| Session | Session | 375 / 465 |
| **Session** | **Episode** | **388 / 465** |
| Episode | Episode | 351 / 465 |

Finer *packing* gains 13 items. Finer *ranking* — at this unit, on this corpus —
**loses 37**, with 26 gains against 63 losses. That is the opposite sign to §6.2, on
the same corpus, and the reconciliation is the size table in §6.1: an episode is
already small enough that its embedding stays informative, and dropping to it
discards the broader context that was doing the scoring work. A source turn is small
enough that its embedding is *sharp*. The 63 items rescued by coarse ranking have
median own-episode cosine rank 46; the 26 gained by fine ranking have median rank 10.

So the rule is conditional, and stated that way: **rank at the finest unit whose
embedding remains informative, and pack at the finest affordable unit.** This is a
posthoc characterization on an exhausted corpus, not a registered universal law, and
§6.5 gives a second place where a tempting generalization does not hold.

### 6.4 NF-006 — the same substitution on the internal store

The internal 121-turn store, 119 eligible episodes, one enumeration probe worth 17
items, 32,000 serialized characters. Selections were sealed outcome-blind before
measurement.

| Arm | Total | Civil | Art | Monetary | Marine | Units | Chars |
|---|---:|---:|---:|---:|---:|---:|---:|
| Episode rank, episode pack | 12/17 | 5/5 | 2/4 | 1/4 | 4/4 | 15 | 31,569 |
| *Inherited* score, statement pack | 7/17 | 3/5 | 2/4 | 1/4 | 1/4 | 51 | 31,931 |
| **Own-statement cosine, statement pack** | **14/17** | 5/5 | 1/4 | **4/4** | 4/4 | 80 | 31,991 |

The middle row is the control that makes this a ranking result rather than a packing
result: split the candidates but let each inherit its parent's score and delivery
*falls* to 7 of 17. The unit only helps when it is scored on its own terms.

Targeted probes hold at 21 of 21 against 21 of 21 — zero losses. Gates G0 through G9
pass.

**Two boundaries travel with this number.** The winning trace selects **no statement
whose source turn is 90**, so the specific episode a prior diagnostic identified as
the hardest miss remains unresolved; all four monetary items arrive by another route.
And art falls from 2 of 4 to 1 of 4. This is a breadth composition trade, not
universal dominance.

### 6.5 Where a tempting generalization fails

A budget sweep across both external corpora refutes the obvious scope condition. The
proposal was that the effect depends on how oversubscribed the budget is — the ratio
of available candidate text to deliverable characters. **Seven overlapping cells have
opposite signs.** The sharpest pair: LoCoMo at a 4,000-character budget, median
binding ratio 19.85x, nets **+123**; LongMemEval at 24,000 characters, median ratio
19.39x, nets **−14**. Nearly identical pressure, opposite direction.

The binding-ratio scope condition is therefore rejected, and the registration that
followed was written corpus-specific rather than universal. The 16,000-character
operating point in §5.1 was chosen because its baseline sits off-ceiling at 80.9% of
deliverable items — **explicitly not because it showed the largest effect.**

---

## 7. The decomposition: three constraints in a forced order

The granularity result is about the unit. This section is about what happens after
the unit is fixed, and it is the part of the programme that generalizes least and
explains most. All of it is DETERMINISTIC-OFFLINE on the internal store.

### 7.1 Capacity was never the constraint

The measurement that makes the rest possible: compute, with the answer key, the
cheapest set of stored episodes that satisfies the enumeration probe, charged at the
same exact serialized cost as the deployed path.

| Configuration | Items available | Characters spent |
|---|---:|---:|
| Deployed baseline | 6 / 17 | 31,946 |
| Shipped set-level configuration | 12 / 17 | 31,569 |
| **Exact known optimum** | **14 / 17** | **5,058** |
| Greedy variant | 15 / 17 | 5,455 |

A perfect picker reaches the target using a sixth of the budget. Deployed selection
spent all of it and delivered a third as much. Figure 4.

**Both optima are computed with the answer key. They are bounds, not methods**, and
they are not achievable by any retriever. One further qualifier: four of the five
optimum episodes are *prior probe exchanges*, and this probe's earlier answers were
largely wrong. An item counts as available if its text appears, however wrong the
response surrounding it.

### 7.2 The candidate pool binds first, and structurally

The deployed path pre-filters the store to a 34-episode shortlist before any selector
runs. **Neither art-domain contributor is in it** — they sit at cosine ranks 50 and
86 of 119.

That is not a measured comparison; it is a fact about the shortlist's contents. **No
selection rule of any kind can reach the art domain from a shortlist that contains no
art episode.** The constraint binds before any objective is evaluated, which is why
it is first.

With the selector held fixed and only the pool widened, the same configuration moves
from 5 of 17 across 2 domains to **12 of 17 across 4**. Dropping only the 19
lowest-cosine episodes of 119 costs three facts, the entire art domain, and all
overlap with the known optimum — even though four of the five optimum episodes
survive the cut. The selector clusters over its pool, so removing the tail reshuffles
the objective rather than simply removing options. Figure 3.

**This is the operational instruction with the widest reach: do not prune the
candidate pool to control cost.** It is the one operation this programme measured to
break retrieval.

### 7.3 The objective binds second, and only after

Run on the *deployed* 34-episode pool, the shipped set-level objective scores **5 of
17 against the baseline's 6**. It is worse than what it replaces.

That single count — one run, one configuration — is what makes the order forced
rather than tidy. Improving the selection rule before widening the shortlist is not
merely less effective; on this store it was negative. A practitioner who reads §7.1
and reaches for a better objective first will reproduce that result.

### 7.4 A similarity floor binds last

After the pool is wide and the objective is set-level, one episode remains
unreachable. It carries four monetary items, sits at cosine rank 112 of 119 with a
query cosine of **0.0560**, and would need **0.225** to be selected. Only 20 of 119
episodes clear that bar. Across 146 swept configurations, **zero** selected it.

The tempting explanation — that it collided with a higher-scoring episode in the same
diversity cluster — was tested and **refuted**: its cluster is never entered at all,
so the diversity term was payable in full at every step. No reweighting closes a gap
of that size. The programme shipped the configuration with the miss characterized
rather than tuned away.

### 7.5 What the internal inversion does and does not mean

On this corpus's one enumeration probe, the four highest-cosine episodes carry none
of its target facts, and the last needed item does not appear until rank 87 of 119.
That is a striking number, and it has been tested externally, where it **narrows
sharply**.

On 470 answerable LongMemEval questions, only **69 (14.7%)** place every piece of
evidence below the top four. Median evidence-session rank is **2**; the 95th
percentile is 23. The internal inversion is real and it is **not the dominant
external pattern**.

Two further constraints on how far it travels. The same internal ordering places
every needed item inside rank 2 on all eight targeted probes — so this is *one probe
behaving unlike eight*, not an established property of query types. And a diagnostic
built to test whether the planted vocabulary caused the inversion could not be
completed: the prior rarity artifact scores only 6 of 76 fact-bearing episodes across
three variants with no registered primary. That is a measurement-unit failure rather
than a null, and the categorical claim it was meant to support has been withdrawn.

---

## 8. Packing priority is a causal delivery gate

**Standing: DETERMINISTIC-OFFLINE.** The order in which a fixed candidate set is
packed into a fixed budget decides what arrives. This was measured twice, once
externally and once internally, holding everything else constant.

### 8.1 EC-002 — reversing the order on 500 external stores

The 500 stores from the external calibration run, replayed with **only the packing
order changed**. The deployed order fills recency first, then similarity, then
coverage. The counterfactual fills similarity first. No reader inference, no
embedding call.

| Outcome | Deployed order | Similarity-first | Gains | Losses |
|---|---:|---:|---:|---:|
| Any evidence session | 109 / 470 (23.2%) | **261 / 470 (55.5%)** | 152 | **0** |
| All evidence sessions | 34 / 470 | 137 / 470 | 103 | 0 |
| Any exact answer turn | 79 / 470 (16.8%) | 196 / 470 (41.7%) | 119 | 2 |
| All exact answer turns | 20 / 470 | 106 / 470 | 86 | 0 |

**Plus 32.3 percentage points on the primary, with 152 gains and no losses.**
Restricted to the 401 questions whose evidence was already in the top four ranks,
recall goes from 96 to 248. The evidence was ranked correctly and then not delivered.

**The medians concealed all of it.** Block size stays at 31,920 characters; the median
composition stays 16 recency episodes, 0 non-recency similarity episodes, 1 coverage
episode. What moves is the aggregate: delivered similarity episodes rise from **26 to
476**. A summary statistic that looked stable across the change was hiding a
twentyfold difference in the tier the system exists to provide.

Residual, stated because it bounds the fix: 209 of 470 still recall no evidence
session under the better order.

### 8.2 IC-001 — the same gate on the internal store

Both orders replayed over frozen candidate identities; zero inference, zero
embedding, no vector re-derived.

**Under the deployed order, the similarity path delivered zero episodes and zero
characters at 8 of 8 probes.** Every internal number this programme published for
that configuration sits behind a starved fill order. Reversing it delivers 9 episodes
and 14,796 characters. The enumeration probe moves 6 to 7 of 17; targeted probes move
14 to 18 of 21, with four gains and zero losses. At the enumeration probe the
reversed order delivers 12 episodes in 31,863 characters against 8 in 31,946 — four
more episodes in 83 fewer characters.

### 8.3 What was done about it, and why that is not a contradiction

The correction was tested live and **rejected**. A registered comparison scored the
similarity-first arm at 7.0 against the deployed arm's 8.0, and the registration's
own bar fired. The correction is not adopted.

Those two facts sit together honestly. The suppression is confirmed — it is an
offline count, byte-identically replayable, and §12.1's noise band does not touch it.
The live comparison that would have justified adopting the fix went the other way,
and its −1.0 margin is *inside* the band and therefore **not demonstrated in either
direction**. The programme's registration forbids citing the band to revive the
rejected correction, and this paper does not. What is established is that packing
order is a delivery gate. What is not established is that reversing it improves
answers.

---
