# Rank Fine, Pack Fine, Call Nothing

### A memory layer that spends no generative calls, measured against one that spends 1,646

**Idris Applied AI Research** — independent, non-profit
Repository: `contextDecayWindow` · Licence: CC BY 4.0
Preprint — PAPER-002 · supersedes PAPER-001

---

## Executive summary

**What this is.** A conversational memory layer that makes **no generative model
calls**. It stores every exchange verbatim, ranks candidates by embedding
similarity, and packs a fixed character budget. Nothing in it asks a model to
write text about what was stored.

**What happened against Mem0.** Mem0 2.0.18 was installed and run here — same
corpus, same local reader, same 16,000-character budget, contrast hashed before
the first generation call.

| | This component | Mem0 2.0.18 |
|---|---:|---:|
| Questions answered, of 300 | **0.563** | 0.487 |
| Prompt tokens to build the store | **0** | **5,988,818** |
| Generative calls to build it | **0** | **1,646** |
| Wall clock to build it | — | **284 min** |
| Time to assemble one context block | **10 ms** | 413 ms |
| Store size | **7.2 MB** | 42.8 MB |
| Answer reached the delivered context | **101 of 108** | 79 of 108 |

The accuracy gap is **7.7 points, 46 gains against 23, p = 0.0038**. A
deterministic containment endpoint — no model, cannot be talked into a verdict —
agrees at **+9.7 points, p = 2.85e-05**. With no memory at all the reader scored
**zero**, so none of this is a model reciting a public dataset.

**Why it matters.** The generative call in the write path is the expensive,
lossy, slow part, and on this corpus it bought nothing. Mem0 spent **six million prompt tokens** and a model
call on every message pair, and still finished behind. Of the answers written verbatim
in those conversations, up to a fifth never reached its store: 31% of pairs
produced no memory at all, and 16 extractions returned malformed JSON and were
dropped. A verbatim store cannot lose what it was given.

**How it works.** Four parts. An append-only store that keeps each exchange
unchanged; a recency window; cosine-threshold similarity retrieval; and a
set-level coverage objective that packs one character budget at exact serialized
cost. `context()` is a pure function of store state, query and budget, verified
byte-identical across two processes.

**What this does not establish.**

- **Fixed-width chunk retrieval scored 0.550 against 0.563.** Thirteen
  thousandths. Against Mem0 the margin is 7.7 points and the sign test carries
  it; against chunk-and-embed on this corpus it does not.
- **Mem0 is the cheaper arm per question** — 3,392 prompt tokens against 4,009.
  Ingest cost and read cost run in opposite directions, and which architecture
  wins depends on a read-to-write ratio neither paper states.
- **The corpus fits the reader's window.** The arm that took the whole
  conversation scored highest, at 222 times the cheapest arm's tokens. Here a
  memory layer buys cost, not capability.
- **Not a comparison to Mem0's published 66.88%**, which used a different model
  as extractor, answerer and judge. Zep, Letta, HippoRAG and Mem0's graph
  variant were not run at all.

**The rest of the paper.** §5 is the head-to-head in full. §6 is the programme's
confirmatory result — a granularity rule on a sealed external holdout, 843 → 935
of 1,098 at p = 6.19e-12 — and §7 through §11 are the ten studies and one bakeoff
that cut the design to four parts. §13 is the limitations, at length.

---
## Abstract

We report a deterministic memory layer for long conversations that makes no
generative model calls, and the pre-registered programme that reduced it to four
components: ten numbered studies plus one registered exploratory bakeoff. The surviving design is an append-only verbatim store, a recency
window, cosine-threshold similarity retrieval, and a set-level coverage objective,
packed against one character budget at exact serialized cost.

Against Mem0 2.0.18, installed and run here on the same corpus, the same local
reader and the same 16,000-character budget, the layer that makes no generative
calls answers 7.7 points more of 300 questions than the layer that spent 1,646 of
them across 284 minutes (46 gains against 23, one-sided exact p = 0.0038; a
model-free containment endpoint agrees at +9.7 points, p = 2.85e-05). It assembles
a context block in 10 milliseconds against 413, in a store of 7.2 MB against 42.8.
Of the answers stated verbatim in those conversations, up to 21% are absent from
Mem0's store, an upper bound because a preserved paraphrase counts as absent; 31% of message pairs produced no memory at all. Per query Mem0 is the
cheaper arm, at 3,392 prompt tokens against 4,009, so ingest cost and read cost run
in opposite directions and both are reported. The comparison is to Mem0 as run
here, never to its published score, and the corpus fits the reader's window, so it
measures cost rather than capacity.

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
preserved. The relation is not monotone in granularity: on the same corpus,
ranking at the episode rather than the session loses 37 items, so the episode is
worse than both its parent and its child. The rule is therefore stated
conditionally — rank at a unit small enough that its embedding is dominated by the
material answering the query, and pack at the finest affordable unit — and that first
clause has no operational test here. Splitting also changes character count and
semantic localization together, so length is not isolated.

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
11.0, 8.0, 8.0, 8.0 and 8.0 in that order, so the run-to-run band is 3.0 points and
three of the arc's four scored verdicts fall inside it and are labelled not
demonstrated. The divergent run was the first in a fresh server process. The offline
delivery results are counts and identities and are unaffected.

---

## 1. Introduction

A long conversation forces a trade. Keep the whole transcript and the model slows
down and loses the middle. Summarize it and the details are gone. A third option is
to store every exchange verbatim and rebuild a small, relevant context each turn,
which moves the problem from compression to selection.

This paper is about that third option, built and measured over eleven pre-registered
efforts — **ten numbered studies plus one registered exploratory bakeoff**, counted
that way throughout. Most of the mechanisms failed. What survived is smaller than what the
programme set out to build, and the reason it is worth reading is that the survivor
is now confirmed on a corpus this programme did not construct, and that the failures
are specific enough to name.

The one-sentence result: **the unit you score a candidate by is a bigger lever than
the rule you score it with, and neither requires a language model** — with §7.3 the
counterexample that stops "smaller is better" from being the reading.

### 1.1 What kind of paper this is

A single-programme experience report with one external confirmation. One internal
corpus, one rubric locked since the second study, one local model at one
quantization, one machine, one seed. Every *scored* comparison is a single run, and
§13.1 gives the measured variance that bounds them.

That scope applies to the scored results. It does not apply to the deterministic
ones, and the distinction decides most of what this paper is permitted to say. The
delivery counts in §6 and §7 are produced with zero model calls, reproduce
byte-identically on replay, and are verified against committed hashes. They are
counts and identities rather than judgements. Where a result is one of those, this
paper states it plainly; where it is a score, it carries its band.

### 1.2 Contributions

1. **A granularity rule with a sealed external confirmation** (§6, §7). Ranking at
   the finest informative unit, confirmed prospectively on six withheld LoCoMo
   conversations and reproduced on two further corpora with the size mechanism
   measured rather than asserted.
2. **A decomposition of where retrieval failure lives** (§8): a candidate pool, a
   selection objective, and a similarity floor. They are not independent — they bind
   in a forced order, and applying the second fix without the first makes the shipped
   configuration worse than the baseline it replaces.
3. **The measurement that makes the decomposition possible**: a per-fact known
   optimum computed on the same store under exact serialized-cost accounting (§8.1).
   It costs an answer key and exact cost accounting, which is why it is unusual
   rather than difficult.
4. **A subtraction result** (§11): twelve mechanisms removed, each by its own gate,
   and the argument that the properties making the survivor deployable followed from
   the removals.
5. **A correction record** (§12) including the instrument's own measured noise band,
   and one case where a diagnostic written to catch a specific failure class nearly
   committed that exact failure.

### 1.3 What this paper does not claim

No scored difference below about three points in this arc is claimed as real; §13.1
gives the measurement. Mem0 was run here and §5 reports it; no comparison against
HippoRAG, Zep or Letta was run,
and §2 says exactly what is and is not being compared. No general claim that
similarity retrieval fails — §8.4 measures the opposite on eight of nine internal
probes and §9 measures it on 470 external ones. No novelty for maximal marginal
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
advancement gate (§11).

**Deployed memory systems.** Letta, Mem0 and Zep ship in this space. Full citation
detail, published numbers and verification status are in
`paper/notes/COMPETITIVE_LANDSCAPE.md`.

### 2.1 What is and is not being compared

**Of the systems named above, only Mem0 was run here** — §5. Every number attributed
to any of the others is cited from
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
| Generative calls per stored turn | **0** | Mem0's ingestion is one extraction call per message pair **plus one update call per extracted fact**, so `1 + n`; Graphiti runs entity extraction, entity resolution, fact extraction, temporal extraction and edge invalidation per episode |
| Delivered text | Stored episodes verbatim | Model-written summaries or extracted facts |
| Replayability | `context()` byte-identical across processes; 132 payloads reproduce by SHA-256 | Bounded by generation determinism |
| Failure mode | An episode is not delivered | An episode is not delivered, or is delivered as a wrong paraphrase |
| What is measured | Evidence availability | Judged answer accuracy |

**Only the first row is arithmetic on published descriptions.** It is the one
comparison this paper can make without running anything, and the axis on which the
difference is largest. The remaining rows are not of that kind and should not inherit
its licence: rows two and three describe *this* component and are measured here, with
the competitor column stating what follows from a generative pipeline in principle
rather than anything observed. Row four's "delivered as a wrong paraphrase" is a
failure mode those architectures admit, not one seen in a run. Row five is a
definition.

**One collision is worth naming explicitly, because it is where a reader is most
likely to construct a sentence this paper refuses.** Both this programme and Mem0
report a number "on LoCoMo". §6.1 ran six sealed conversations with zero model calls
during measurement and counts whether evidence text was delivered. Mem0's LoCoMo
figure has a model answering and a model judging. The corpus name is shared; the
denominators count different events. The sentence to refuse has the shape *"on LoCoMo,
system X reports [their accuracy] and this component reaches [our delivery count]"* —
both halves true, the juxtaposition meaningless, and it is not written out here with
real numerals precisely because it would then be quotable.

A second caution about the published numbers themselves. Several competitor scores
most often quoted for this space appear in **Mem0's own comparison table** and are
Mem0's reproductions rather than author-reported results; Zep's paper, for instance,
reports DMR and LongMemEval and never LoCoMo. `COMPETITIVE_LANDSCAPE.md` records
which numbers are author-reported and which are third-party, because the distinction
survives into any comparison built on them.

This programme committed, before it had any external result, to a framing in which
losing was still a finding: the question was how much of the layer survives without
the generative call, not whether the deterministic version wins. **§5 reports the
comparison, run here against Mem0 2.0.18 on a matched budget and a single reader.**
That framing is left standing rather than quietly retired, because it is what the
study was designed under and because it still governs every system in this section
that was not run — which is all of them except Mem0.

One boundary is load-bearing and appears again in §13.5. The LongMemEval authors'
LLM-assisted indexing and time-aware query expansion were available to this
programme and were deliberately not adopted, because they add generative calls to
the memory path and would change the component under test. Some of the gap between
this component's external numbers and published ones is that choice, and this paper
does not get to claim the choice was free.

**The placement is narrow.** Most systems above consume a candidate set produced
upstream by similarity ranking, and this paper measures that set. The claim is not
universal even across the short list: HippoRAG retrieves by graph traversal, as §2
says two paragraphs earlier, so the measurement here bears on it only where a
similarity-ranked candidate set feeds the traversal.

---

## 3. The architecture

Stated first, because it is the result. What follows in §6 through §11 is the
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
up to 68% (§12.1).

### 3.2 The property that matters

**There are no generative model calls anywhere in the memory path.** Nothing in it
asks a model to write text about the store.

This is not the absence of model calls, and the distinction is one this paper's
predecessor got wrong and had to correct. `context()` embeds the query on every
call and `append()` embeds every episode, so an embedding model must be resident.
What follows from the architecture is narrower and checkable: the memory path emits
no generated text, and its output is reproducible **given a pinned embedder** —
which is why the library asserts a sentinel vector hash on every store open rather
than assuming one (§12.3).

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
same size is 0.205. §12.4 gives the measurements. Nothing in this programme
establishes what a correctly implemented window would score, in either direction.

---

## 4. How results are graded

This section is what licenses the confident voice everywhere else. The programme's
own operating manual is explicit that its recurring failure is a surrogate that can
pass without the property it certifies, so results here are graded by how they were
obtained, before anyone looks at what they say.

### 4.1 The standing taxonomy

Five levels, separated by **when the claim was committed relative to the number**,
not by how the number was computed. Determinism is cheap; commitment order is what a
result cannot buy back afterwards.

| Standing | Requirement | How this paper states it |
|---|---|---|
| **CONFIRMATORY** | Pre-registered; sealed holdout; bars, endpoint and budget locked before the number existed; registration commit carries no implementation file | As an established result, with its scope cap |
| **REGISTERED-OFFLINE** | Pre-registered with bars locked first, zero generative calls, and reproducible on replay — byte-exactly where the embedding cache was retained, otherwise under recomputed embeddings, which the row says — but run on a corpus already observed, so it cannot confirm | As measured and registered, capped as characterization |
| **REGISTERED-LIVE** | Pre-registered with contrast, endpoint, budget and sample size hashed before the first generation call, but run on a corpus already observed, and **not replayable**: generation is stochastic, so replicates measure that spread instead of eliminating it | As measured and registered, capped as characterization; never as confirmation |
| **DESCRIPTIVE** | Deterministic and reproducible, but the reading was chosen after the number existed, or the quantity is a bound computed with the answer key | As measured, with what it cannot support said in the same breath |
| **NOT DEMONSTRATED** | A scored live comparison whose gap falls inside the measured 3.0-point band | With the number *and* the label. Not refuted either |
| **WITHDRAWN** | Corrected in `ERRATA.md` | Not at all. The list is `paper/notes/DO_NOT_WRITE.md` |

The second and third levels were one level in an earlier draft, and collapsing them
was a real defect: it let a byte-identical 500-store replay, a posthoc reading of an
exhausted corpus, and a bound computed with the answer key all inherit the same
phrase. They reproduce identically and they do not license the same sentence.

**The assignment, in full, so this table is checkable without leaving the paper.**

| Result | Standing | The binding limit |
|---|---|---|
| HH-001 — head-to-head against Mem0, +7.7 points (§5) | REGISTERED-LIVE | This reader, this corpus, this budget, this pair of configurations. Never confirmation |
| NF-004 — LoCoMo pair ranking, 843→935 (§6.1) | CONFIRMATORY | Availability only; no reader, universal-rule or adoption claim |
| DMR-004 — no sufficiency signal (§6.2) | CONFIRMATORY | Negative; closes deterministic stopping in this arc |
| DMR-001 — degenerate formation (§6.3) | CONFIRMATORY | Negative; its post-stop gates are not results |
| DMR-001C — transfer confirmed, boundary refuted (§6.3) | CONFIRMATORY | Split verdict; the statistic was ill-chosen and is not re-scored |
| SAL-001 — no surprisal signal (§6.4) | CONFIRMATORY | Negative; effect ran opposite to the registration |
| NF-005 — turn ranking, 361→461 (§7.2) | REGISTERED-OFFLINE | Corpus already observed; capped as characterization. Does not isolate length from localization |
| NF-006 — statement ranking, 12→14 of 17 (§7.4) | REGISTERED-OFFLINE | One probe; art falls 2/4 → 1/4; turn 90's carrier unresolved |
| EC-002 — packing priority, 109→261 (§9.1) | REGISTERED-OFFLINE | Reproduction under recomputed embeddings, **not** a byte-exact replay |
| IC-001 — zero K episodes at 8/8 probes (§9.2) | REGISTERED-OFFLINE | Internal store; frozen candidate identities |
| NF-003 — three-arm, 375/388/351 (§7.3) | DESCRIPTIVE | Posthoc on an exhausted corpus. Not a registered law |
| AR-001 — the 5,058-character optimum (§8.1) | DESCRIPTIVE | Computed **with the answer key**. A bound, not a method |
| DR-002 — the pool binds structurally (§8.2) | DESCRIPTIVE | A fact about the shortlist's contents, not a measured comparison |
| DX-001 — the 0.0560 floor (§8.4) | DESCRIPTIVE | One frozen configuration |
| NF-007 — coverage floor inert (§12.6) | DESCRIPTIVE | An **instrument** stop: the test could not distinguish the arms |
| Study 009 memory tier, +3.0 (§13.1) | NOT DEMONSTRATED | Inside the band; process state uncontrolled |
| LV-001 targeted regression, −2.0 (§13.3) | NOT DEMONSTRATED | Inside the band. The kill bar firing is separate and stands |
| Study 011 tier isolation, −1.0 (§9.3) | NOT DEMONSTRATED | Inside the band; the correction stays rejected |

Five results in the entire arc reach CONFIRMATORY, and **three of those five are
negative**. That ratio is the paper's most compact structural fact: the surviving
design is four components because the well-built experiments mostly returned nothing.

`paper/notes/EVIDENCE_SPINE.md` carries the same assignment with each number's
artifact path and hash, for a reader who wants to check a figure against its source.
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
failure, not a mechanism result. §6.4 and §12.5 each report one.

**Leakage control.** Mechanism code — retrieval, formation, ranking, gating — may not
read the answer key; measurement may. The boundary is enforced by grep, import-graph
checks, and a planted test violation that must be caught.

**Sealed scoring.** Three blind passes with registered adjudication triggers. Every
arm's scores are committed before anyone opens a mechanism log, and git order is the
evidence. **The raters were three models from one family and the adjudicators were
subagents — none human** (§13.8), and one live study ran a single rater against a
registered three (§13.3).

**None of this was uniformly achieved, and §12.6 is the list of where it was not.**
Four integrity gates in this programme were inert for their whole lives: three
through a line-ending mismatch, and one — on the sealed holdout itself — through a
constant that never matched the file it named. A targeted no-regression gate was
unsatisfiable by construction for any selector. One stop was reached only because its
evaluator searched for labels that did not exist. The machinery above is the standard
this programme holds itself to; §12.6 is the measured shortfall against it, and the
gap is the reason §12 exists rather than an embarrassment tucked into it.

### 4.3 What a stop means

A stop closes a design, not a question, and this paper distinguishes two kinds
throughout. A **mechanism stop** means the thing was tested and did not work. An
**instrument stop** means the test could not have detected the thing. Reporting the
first when it was the second is how a programme accumulates false confidence, so
each stop below says which it was.

---

## 5. The head-to-head: Mem0, run here

Every claim in this section is a measurement taken in this repository. Mem0
2.0.18 was installed, configured onto this programme's reader and embedder, and
run over the same corpus as the component it is compared against. The contrast,
the endpoint, the budget, the sample size and the replicate count were written
to `commitments.json` and hashed at `c143620b83c3f300` **before the first
generation call**. Provenance for every number: `notes/HH001_EVIDENCE_SPINE.md`.

### 5.1 The result

Five memory layers, 300 questions drawn by seeded stratification from 850
answerable LoCoMo records, three replicates each, one reader, one judge, one
16,000-character budget measured on the exact string handed to the model.

| Arm | Memory layer | Judged | Containment |
|---|---|---:|---:|
| A1 | Whole conversation, unbudgeted | 0.613 | 0.320 |
| **A2** | **This component** | **0.563** | **0.313** |
| A4 | Fixed-width chunk retrieval | 0.550 | 0.287 |
| A3 | **Mem0 2.0.18** | 0.487 | 0.217 |
| A0 | No memory | 0.000 | 0.000 |

Figure 1 sets the two panels side by side. **The component answers 7.7 points
more of the same questions than Mem0 does.**
Paired over the 300 items: **46 gains, 23 losses**, two gains for every loss,
one-sided exact binomial **p = 0.0038**. The deterministic containment endpoint,
which involves no model and cannot be talked into a verdict, puts the same
contrast at **+9.7 points, 40 gains against 11, p = 2.85e-05**. Both endpoints
point the same way, which is the condition this study registered in advance for
making a directional claim at all.

**§13.1's 3.0-point band does not govern this contrast.** That band was measured on
a 13-point holistic rubric scored once per run. This is 300 items paired within
item, three replicates deep, read out as a discordant count — a different
instrument with its own noise reading, and this one reports it: per-item unanimity
across replicates runs 0.85 to 0.89 by arm.

The floor arm scored **zero**. With no memory block the reader answered none of
the 300 questions; all fifty items in the contamination probe returned `I don't
know`, none empty. Nothing in the table is the model reciting a public dataset.

### 5.2 What the win cost each side

Mem0 built its store with **1,646 generative calls over 284 minutes**, one call for
every message pair, and those calls carried **about 4,100 prompt tokens each** —
5,988,818 of them across the sampled window. The cost per pair climbs as the store
grows, because each extraction is shown what is already stored. This component
built its store with **none**. That zero is architectural rather than measured:
`append()` embeds and stores, and no code path asks a model to write text about
what was stored.

Figure 2 shows what that ingest cost looked like as the store filled.
Retrieval separates them again. Assembling one context block takes this
component **10 milliseconds** at the median and Mem0 **413** — **41 times
slower**, on the same machine, over the same conversations. The finished store
occupies **42.8 MB** against **7.2 MB**, six times larger, counting only
Mem0's vector store and excluding its 692,224-byte history log.

**The cost runs the other way at read, and the paper states it in the same
breath.** Mem0 is the cheapest memory arm per question — **3,392 prompt tokens
against this component's 4,009** — because model-extracted memories are shorter
than stored turns. A system written once and queried a million times amortises
its ingest away. Which architecture is cheaper is decided by the read-to-write
ratio, and neither this paper nor arXiv:2504.19413 states one. Both halves are
measured here; the report gives both.

### 5.3 What the generative write path lost

The comparison above is downstream of a mechanism, and the mechanism is
measurable without a model in the loop.

Of the 315 answers stated verbatim somewhere in the six source conversations,
**66 are absent from Mem0's finished store — 21%.** Per conversation, retention
runs 0.68 to 0.86. This is a containment test over the store's own memory text:
a preserved paraphrase counts as absent, so **21% is an upper bound on
extraction loss and cannot understate it**. That is the honest reading and it is
the one to quote.

Two further numbers come from the ingest itself. **509 of 1,646 message pairs —
31% — produced no memory at all**: the extractor received the turn, spent a
model call on it, and decided nothing in it was worth storing. And **16
extractions returned malformed JSON** and were discarded, 0.97% of the corpus,
logged by Mem0 and passed over in silence.

Downstream, the answer reaches the delivered block for **101 of 108** eligible
items under this component and **79 of 108** under Mem0. The verbatim path
carries a 0.935 survival rate against 0.732. It cannot do better than the
selector, and it cannot do worse than what it stored, because it stored the turn
unchanged.

### 5.4 What the other arms did better

Fixed-width chunk retrieval stores **2.8 MB against this component's 7.2** and reads
at **3,904 prompt tokens against 4,009**. It is smaller and cheaper on both counts,
and it scored 0.550 to this component's 0.563. Mem0 costs less per read than either.
This component also has the **lowest replicate agreement of any memory arm** — 0.853
against 0.870 and 0.891 — so its answers are the least stable of the three under
reseeding.

### 5.5 Where the answer lives

Splitting by how far back in the conversation the evidence sits — these are
369- to 680-turn transcripts — the component leads Mem0 by **11.9 points in the
oldest quarter** and **14.9 points in the newest**, and trails by 3.1 in the
second quarter. The advantage is not a recency effect and is not uniform.

### 5.6 What this section does not say

**Not a comparison to Mem0's published score.** Mem0 reports 66.88% on LoCoMo
with GPT-4o-mini as extractor, answerer and judge. Every arm here ran on one
local 27B model. The two numbers share a corpus name and measure different
events, and no sentence in this paper puts them in the same column.

**Not a claim about any other system.** Mem0-graph, Zep, A-MEM, HippoRAG and
LangMem were not run. Nothing here is evidence about them.

**Not a capacity result.** The longest holdout conversation is 90,713 characters
— roughly 22,700 tokens against a 200,000-token window. The whole corpus fits, and
the arm that took it all scored highest at **222 times the prompt tokens of the
cheapest arm**. On this corpus a memory layer is a cost mechanism, not a
capability one. A corpus that did not fit would test something this one cannot.

**Not a breadth result.** The arm carries NF-004's pair ranking and no
set-level coverage objective; the multi-domain machinery of §8 was not in the
test. `SCOPE_LIMITS.md` records that gap and what would close it.

**Not confirmatory.** LoCoMo is exhausted on both splits, so this is
`REGISTERED-LIVE` under §4.1's taxonomy — a level added for this study, because the
programme had no pre-registered live comparison before it. The run artifact records
its stage as `DEVELOPMENT`, the same boundary named from the other side and does not become `CONFIRMATORY` by being
re-described. Three replicates is below the five this programme established as
its own minimum, and near-ties are reported as near-ties.

---

## 6. The confirmatory results

Five results in this arc were obtained under a sealed holdout with bars locked
before the number existed. This section reports all five. Three returned nothing,
and they are here at the same resolution as the two that did, because a programme
that reports only its sealed successes has not earned the standing its sealed
successes carry.

### 6.1 NF-004 — ranking granularity, confirmed on withheld LoCoMo conversations

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
registered bar of 2.0. One-sided exact binomial **p = 6.19e-12** over the 188
discordant questions.

**That p assumes the questions are independent, and they are not** — they cluster
within six conversations. The registered statistic is not re-scored, but a
conservative alternative is reported beside it: treating each conversation as a
single observation, all six are net positive, one-sided sign test **p = 0.0156**.
Six observations is what the sealed design actually bought, and it still clears 0.05. Median packed
characters 15,986 against 15,988, so the treatment is not simply spending more.
Median best-evidence rank moves **9 to 2**; p90 moves **80 to 34**, and those rank
statistics were opened only after the disposition was committed.

**Every one of the six sealed conversations is net positive**: +7, +6, +13, +30, +15,
+21. So are all five source categories. At the 32,000-character secondary the
direction holds, 961 to 1,024.

Gates G0 through G7 all pass, including a vector seal reading 2,749 of 2,749 cached
vectors with zero misses, and a G7 replay whose SHA-256 equals the committed G6
hash. Figure 3.

**Scope cap, and it is binding.** This is availability: whether the text carrying an
answer was present in the delivered context. It is not accuracy, and the
registration authorizes **no reader, live, universal-rule, promotion or adoption
claim**. The `universal-rule` term is the one that governs §7 and §14: this
confirms one substitution on one corpus, not a law about granularity. §13.3 is where
the accuracy distinction has teeth, and §7.3 is where the universality one does.

**What the source-order control buys.** 258 against 843 is the reason the treatment
effect cannot be read as a budget artifact. If the budget were slack enough that
ordering barely mattered, the unranked control would sit near the ranked arms. It
sits 585 items below. A development-side sweep across budgets from 4,000 to 96,000
characters makes the same point at every truncated point, and ties only at 96,000,
where everything fits and ordering is irrelevant by construction.

### 6.2 DMR-004 — no mechanical sufficiency signal *(negative)*

**Standing: CONFIRMATORY.** The strongest confirmatory construction in the
repository, and it returned nothing.

The question: can a model-free precedence parser over query text alone identify when
a query's evidence obligations are *finite* — when a retriever can know it has
enough and stop? A positive result would have given the deterministic stack an
adaptive controller. Sealed 180-query holdout, two blind raters — neither human, see §13.8 — and PF3 verifying
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
over answering "I cannot tell" to everything is not a controller. The two raters
— the implementing agent and the carried local model — reached J of about 0.76
against the compiler's 0.320, with Cohen's kappa of 0.770, so the task is doable and
the mechanism did not do it. The registration records the boundary before any label
existed: rater A is not independent of the mechanism, and **neither rater is human**
(§13.8).

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

### 6.3 DMR-001 and DMR-001C — event formation *(negative, then split)*

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

### 6.4 SAL-001 — no independent surprisal signal *(negative)*

**Standing: CONFIRMATORY.** Does a surprisal-proximity signal identify what deserves
capture, independent of what is already retrievable? Deterministic 60-history
LongMemEval holdout, label-blind scoring sealed, 92 session-level AUC replications.

Adjusted neighbour AUC **0.41599** against a bar of 0.60. One-sided permutation
**p = 0.99134** against a bar of 0.01. Bootstrap 95% interval [0.35132, 0.48388].
**Five of six strata fall below chance.** The registered effect is not weak; it is in
the opposite direction. That kills the surprisal-based capture line the programme's
design document had proposed.

### 6.5 What five sealed experiments bought

One positive result, on the unit of ranking, that reproduces at the turn and pair
unit on all three corpora and on every conversation inside the sealed one, with §7.3
marking where the direction reverses at a coarser unit. Three well-built negatives that each
closed a line the programme wanted: adaptive stopping, event segmentation, and
surprisal-based capture. One split verdict where the transfer property confirmed and
the claim built on top of it did not.

The shipped component contains none of the three killed mechanisms. That is the
subtraction §11 completes, and this section is where most of it was paid for.

---

## 7. Granularity: rank at the finest informative unit

§6.1 confirmed one substitution on withheld data. This section locates the mechanism
using corpora already observed — reported as measured rather than confirmed — and
§7.3 reports the case where the same lever, applied at a coarser unit, **reverses
sign**. The reversal is on the same corpus as the largest gain, which makes it the
more informative half of this section.

### 7.1 The size of a candidate

**Standing: REGISTERED-OFFLINE for NF-005 and NF-006; DESCRIPTIVE for NF-003's
three-arm reading in §7.3.** Zero model calls throughout.

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

### 7.2 NF-005 — splitting episodes into their source turns

465 turn-labelled LongMemEval questions, 32,000-character budget, packing unit held
fixed at the turn so that only the *ranking* unit varies.

| Ranking unit | Packing unit | Any exact evidence | All exact evidence |
|---|---|---:|---:|
| Source order | Turn | 64 / 465 | 7 / 465 |
| Episode | Episode | 351 / 465 | 201 / 465 |
| Episode | Turn | 361 / 465 | 208 / 465 |
| **Turn (own cosine)** | Turn | **461 / 465** | **454 / 465** |

**100 gains, 0 losses, 365 ties. One-sided exact binomial p = 7.89e-31.** Median best
evidence rank moves 5 to 1; p90 moves 131 to 7. Figure 4 places this beside the other
two corpora and the candidate-size measurement that explains all three. The budget delivers 109 turns where
it delivered 46 episodes.

Gates G0 through G8 pass. The vector seal reads 167,918 cached vectors with zero
misses. The final outcome hash and its replay hash are identical.

**Scope cap.** Splitting an episode changes its character count *and* its semantic
localization at the same time. This result supports candidate information dilution
as the moderator; **it does not isolate raw character count**, and no experiment here
does.

### 7.3 NF-003 — where the rule reverses, and why it is stated conditionally

The same corpus, varying ranking and packing independently:

| Ranking unit | Packing unit | Exact answer-episode delivery |
|---|---|---:|
| Session | Session | 375 / 465 |
| **Session** | **Episode** | **388 / 465** |
| Episode | Episode | 351 / 465 |

Finer *packing* gains 13 items. Finer *ranking* — at this unit, on this corpus —
**loses 37**, with 26 gains against 63 losses. That is the opposite sign to §7.2, on
the same corpus, and the reconciliation is the size table in §7.1: an episode is
already small enough that its embedding stays informative, and dropping to it
discards the broader context that was doing the scoring work. A source turn is small
enough that its embedding is *sharp*. The 63 items rescued by coarse ranking have
median own-episode cosine rank 46; the 26 gained by fine ranking have median rank 10.

**State the shape before stating any rule, because the shape is not monotone.** On
one corpus, at a fixed packing unit, the episode loses in both directions: the turn
beats it 461 to 361, and the session beats it 388 to 351. A candidate unit that is
worse than both its parent and its child cannot be produced by any rule of the form
*finer is better* or *coarser is better*. Whatever governs this is not a monotone
function of granularity, and this programme has not identified it.

What can be said conditionally is: **rank at a unit small enough that its embedding
is dominated by the material answering the query, and pack at the finest affordable
unit.** The first clause needs an operational test to be a rule rather than a
restatement, and **it does not have one here** — "dominated by" is measured after the
fact by whether delivery improved. Two proxies are available and neither was
registered: the 240-to-300-character band where every confirmed gain in this paper
sits, and the Spearman rho of 0.484 between parent length and worse own-cosine rank.
Both are descriptions of these corpora, not thresholds anyone should carry.

This is a posthoc characterization on an exhausted corpus, not a registered universal
law, and §7.5 refutes the scope condition that was proposed to predict where the sign
flips.

### 7.4 NF-006 — the same substitution on the internal store

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

### 7.5 Where a tempting generalization fails

A budget sweep across both external corpora refutes the obvious scope condition. The
proposal was that the effect depends on how oversubscribed the budget is — the ratio
of available candidate text to deliverable characters. **Seven overlapping cells have
opposite signs.** The sharpest pair: LoCoMo at a 4,000-character budget, median
binding ratio 19.85x, nets **+123**; LongMemEval at 24,000 characters, median ratio
19.39x, nets **−14**. Nearly identical pressure, opposite direction.

The binding-ratio scope condition is therefore rejected, and the registration that
followed was written corpus-specific rather than universal. The 16,000-character
operating point in §6.1 was chosen because its baseline sits off-ceiling at 80.9% of
deliverable items — **explicitly not because it showed the largest effect.**

---

## 8. The decomposition: three constraints in a forced order

The granularity result is about the unit. This section is about what happens after
the unit is fixed, and it is the part of the programme that generalizes least and
explains most. All of it is **DESCRIPTIVE** on the internal store: the optimum is
computed with the answer key, the pool claim is a fact about the shortlist's
contents rather than a comparison, and the floor is one frozen configuration.

### 8.1 Capacity was never the constraint

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
spent all of it and delivered a third as much. Figure 8.

**Both optima are computed with the answer key. They are bounds, not methods**, and
they are not achievable by any retriever. One further qualifier: four of the five
optimum episodes are *prior probe exchanges*, and this probe's earlier answers were
largely wrong. An item counts as available if its text appears, however wrong the
response surrounding it.

### 8.2 The candidate pool binds first, and structurally

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
the objective rather than simply removing options.

**This is the operational instruction with the widest reach: do not prune the
candidate pool to control cost.** The reason is structural rather than comparative,
and it is the paragraph above: a shortlist with no art episode cannot yield art at
any setting. This programme did not run a controlled comparison of pruning against
not pruning.

### 8.3 The objective binds second, and only after

Run on the *deployed* 34-episode pool, the shipped set-level objective scores **5 of
17 against the baseline's 6**. It is worse than what it replaces.

That single count — one run, one configuration — is what makes the order forced
rather than tidy. Improving the selection rule before widening the shortlist is not
merely less effective; on this store it was negative. A practitioner who reads §8.1
and reaches for a better objective first will reproduce that result.

### 8.4 A similarity floor binds last

After the pool is wide and the objective is set-level, one episode remains
unreachable. It carries four monetary items, sits at cosine rank 112 of 119 with a
query cosine of **0.0560**, and would need **0.225** to be selected. Only 20 of 119
episodes clear that bar. Across 146 swept configurations, **zero** selected it.

The tempting explanation — that it collided with a higher-scoring episode in the same
diversity cluster — was tested and **refuted**: its cluster is never entered at all,
so the diversity term was payable in full at every step. No reweighting closes a gap
of that size. The programme shipped the configuration with the miss characterized
rather than tuned away.

### 8.5 What the internal inversion does and does not mean

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

## 9. Packing priority is a causal delivery gate

**Standing: REGISTERED-OFFLINE.** The order in which a fixed candidate set is
packed into a fixed budget decides what arrives. This was measured twice, once
externally and once internally, holding everything else constant.

### 9.1 EC-002 — reversing the order on 500 external stores

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

**Plus 32.3 percentage points on the primary, with 152 gains and no losses.** Figure 6.
One qualifier travels with this: the deployed arm is a *reproduction under recomputed
embeddings*, not a byte-exact replay — the original run's embedding cache was not
retained, and that run is permanently unreplayable at bit granularity.
Restricted to the 401 questions whose evidence was already in the top four ranks,
recall goes from 96 to 248. The evidence was ranked correctly and then not delivered.

**The medians concealed all of it.** Block size stays at 31,920 characters; the median
composition stays 16 recency episodes, 0 non-recency similarity episodes, 1 coverage
episode. What moves is the aggregate: delivered similarity episodes rise from **26 to
476**. A summary statistic that looked stable across the change was hiding a
twentyfold difference in the tier the system exists to provide.

Residual, stated because it bounds the fix: 209 of 470 still recall no evidence
session under the better order.

### 9.2 IC-001 — the same gate on the internal store

Both orders replayed over frozen candidate identities; zero inference, zero
embedding, no vector re-derived.

**Under the deployed order, the similarity path delivered zero episodes and zero
characters at 8 of 8 probes.** Every internal number this programme published for
that configuration sits behind a starved fill order. Reversing it delivers 9 episodes
and 14,796 characters. The enumeration probe moves 6 to 7 of 17; targeted probes move
14 to 18 of 21, with four gains and zero losses. At the enumeration probe the
reversed order delivers 12 episodes in 31,863 characters against 8 in 31,946 — four
more episodes in 83 fewer characters.

### 9.3 What was done about it, and why that is not a contradiction

The correction was tested live and **rejected**. A registered comparison scored the
similarity-first arm at 7.0 against the deployed arm's 8.0, and the registration's
own bar fired. The correction is not adopted.

Those two facts sit together honestly. The suppression is confirmed — it is an
offline count that reproduces on replay — under recomputed embeddings for the
external arm, per §9.1 — and §13.1's noise band does not touch it.
The live comparison that would have justified adopting the fix went the other way,
and its −1.0 margin is *inside* the band and therefore **not demonstrated in either
direction**. The programme's registration forbids citing the band to revive the
rejected correction, and this paper does not. What is established is that packing
order is a delivery gate. What is not established is that reversing it improves
answers.

---

## 10. Cost and the operating envelope

**Standing: DESCRIPTIVE.** These come from a 1,000-turn endurance run, not
the 121-turn corpus §8 uses. Nothing here establishes a §8 result at 1,000 turns, and
nothing in §8 establishes these at 121.

Three things could grow as a conversation lengthens. Only one binds.

**Delivered context is bounded, because it is enforced.** Replaying 1,000 committed
episodes through the library at a 32,000-character budget, the delivered block
breaches the budget on **0 of 1,000 turns**, and its 95th percentile moves **+18
characters** across the final five 100-turn buckets. The same block also **truncates
on 895 of those turns**, dropping up to 70 episodes and wanting up to 65,864
characters. It is bounded because a ceiling binds during selection, not because
demand is small. Both readings belong together; the first alone would be the kind of
surrogate this programme keeps catching.

**Disk is cheap.** 4,743 bytes per turn at the margin, 86% of it embeddings. About
48 MB at 10,000 turns. Nothing there ends continuous operation.

**Latency binds.** **190 ms at 1,000 candidates**, with clustering taking 81% of it
and that share rising from 37%. The measured exponent is 1.25 over 50 to 1,000
candidates. The stated horizon is comfortable to a few thousand episodes and
unusable in an interactive loop somewhere before 10,000. Figure 9.

That last number corrects a published projection of this programme's own, and the
correction is instructive: the withdrawn estimate of about 40 ms at 1,000 candidates
came from extending a curve **84 times beyond its last measured point**. Measuring
instead gave roughly five times the projection.

**These milliseconds are one machine's.** The runtime is llama.cpp with a 27B
generation model at UD-Q6_K_XL, one slot, fixed seed, speculative decoding disabled,
and Qwen3-Embedding-0.6B over SQLite with `sqlite-vec`. Selection timings exclude
embedding entirely, because query and episode vectors are already resident. Only the
exponent and the clustering share plausibly transfer.

**The obvious optimization is the one thing not to do.** Keeping the pool small by
dropping low-similarity episodes is what §8.2 shows removes a domain from the
shortlist outright. So retention is unbounded by policy, the trimming knob carries an
`unsafe_` prefix with the finding in its docstring, and the horizon is stated rather
than engineered around.

**Growth belonged to the harness, not the design.** In the original study runner the
retrieved block rose 23,238 characters in one arm and 28,701 in the other, still
setting records in the final bucket. Replayed through the extracted library at the
same budget it moves +18. The leak was the runner's.

---

## 11. What was removed

Each mechanism below was built, measured, and closed by the result beside it. They do
not correspond one-to-one with the studies: several fell to the same study, and some
outlived the study that first weakened them. Figure 5 places each against the bar it
had to clear.

| Removed | Killed by |
|---|---|
| Distillation and "dreaming" | Five studies; query-blind selection cannot anticipate a later query |
| Promotion filters | The weighted route was arithmetically unreachable; every promotion came via bypass |
| Topic layer and consolidation | 52 topics for one 120-turn conversation; 12 domains collapsed to 2 at 1,000 turns |
| Associative graph from co-activation | No configuration cleared its advancement gate at any of eight registered edge sets across three depths |
| Query-type routing | Oracle ceiling 6.09% against a registered 10% build threshold |
| Approximate nearest-neighbour search | Recall degraded at synthetic scale |
| Query segmentation | Improved its matched-budget baseline from 6/17 to 10/17 and still failed its locked 14/17 bar |
| Attention-derived term selection | Run as an oracle over 714 candidate cue rows: 0 reached the retrieval threshold |
| Entity extraction as primary index | Zero entities in the target span |
| Density for formation | Ranks the six hardest planted facts between 89th and 316th |
| Rule detection and persistence | 118 false rules by turn 200; failed at 1,000-turn scale |
| Surprisal-based capture | SAL-001, sealed holdout: AUC 0.416 against a 0.60 bar, five of six strata below chance |
| Deterministic adaptive stopping | DMR-004, sealed holdout: Youden's J 0.320 against a 0.50 bar |
| Absolute-threshold event segmentation | DMR-001, sealed holdout: forced fraction 0.703 against a 0.35 bar |

**Two results from the numbered arc carry the argument.**

*Write-time selection cannot anticipate a query.* Studies 003 through 007 are five
attempts to decide, at write time, what deserves remembering. Each optimized a proxy
satisfiable without the property it certified: record count for information, novelty
for importance, density for factual value. The terminal diagnosis is specific —
density, the best write-time salience signal available, ranks the six hardest planted
facts between 89th and 316th. These are rare technical phrases whose component words
are common.

*Moving selection to query time did not recover it.* A registered bakeoff made that
repair its central premise and refuted it. The best registered 32,000-character
retrieval block surfaced **8 of 17** target facts, below the 11 of 17 the formation
era reached. All 17 were present in the raw store. Retrieval did not find them.

**What remains** is §3.1's four components. It contains none of the mechanisms above.

**One item is retired rather than solved.** The component emits no absence signal on
any of 500 external questions, while the fixed reader correctly abstained on 17 of 20
registered abstention items. That does not give the component an absence detector, and
it does not establish reader reliability across models and prompts. It shows that
component-level detection is not necessary for end-to-end abstention *under this
tested reader*, which is why the requirement is retired at the component level rather
than marked solved.

---

## 12. Self-audit and corrections

Everything internal in this paper rests on this programme's own measurements, scored
by its own raters, against its own rubric. The reason to extend it credit is that it
audited itself and published what it found. `ERRATA.md` holds 19 corrections; all
were caught by gates the programme wrote. This section gives the ones that change how
a reader should read the rest.

### 12.1 The scoring audit removed the programme's only success

A blind re-scoring of 222 committed items across nine studies changed 19. One study's
headline arm fell from 13.0 to 8.5, because a truncated reasoning block had been
credited as a complete response. Study 001 lost the programme's only VALIDATED
verdict and became PARTIAL.

The residual estimate is extrapolated, and its precision is reported with it: 3
disagreements in a 26-item control sample projected across 143 unreviewed items gives
16.5 expected errors, but the 95% Clopper-Pearson interval on 3 of 26 runs from
**about 3 to about 43**. An earlier version of this paper reported "about 20" without
the interval. That is the defect, not the estimate.

### 12.2 Every study on record ran over its stated budget

Character budgets were charged against source text rather than the complete
serialized block — tags, metadata and separators excluded. Correcting it moved
published numbers by up to 68%: two blocks reported at 31,991 and 31,847 characters
against a 32,000 budget were actually **53,726 and 53,839**. The budget was violated,
not saturated, and the scaling conclusion derived from the undercharged values is
withdrawn. Every figure in this paper uses the corrected accounting.

### 12.3 The same query text returns different vectors

Reproducing a retrieval result requires reproducing the *embedding call shape*, not
only the query text. The same embedder, given the same text solo rather than in a
batch of nine, returns a vector agreeing to cosine **0.999837** — with a largest
component difference of 0.217, and that difference **flips 6 of 146 committed
payloads**.

This is why §13.4 does not treat embedder sensitivity as unmeasured. A perturbation
far smaller than a model change already moves 4% of results. The library now asserts
a sentinel vector hash on every store open, so a mismatched embedder fails loudly
instead of silently returning different answers.

### 12.4 The tier called a recency window was not one

Three different rules have carried that name in this programme, and only the one in
the extracted library is a window.

The rule every live study through the endurance run actually ran sorts the whole
store by delivery history, and `retrieve()` refreshes what it just delivered — so the
block re-selects itself. Tie-breaking on ascending turn number means it settles on
the oldest episodes and cannot leave. **From turn 11 onward it delivered source turns
1 through 9 plus the immediately previous turn, for 111 consecutive turns.** Mean
overlap with a true window of the same size is **0.205**; 111 of 120 episodes were
delivered exactly once.

Two consequences. The programme's cleanest architectural contrast did not compare a
memory tier against a recency baseline — it compared it against nine frozen episodes
and one recent one. And **nothing in this programme establishes what a correctly
implemented window would score, in either direction.** No arm ever ran one.

### 12.5 A diagnostic written to catch surrogate failures nearly committed one

The clearest methodological lesson here. A granularity study reported 49 gains and
zero losses on evidence delivery. Its own preflight surrogate audit — the check that
asks *can this pass while the property it certifies is false?* — then found that 94
treatment hits contained no answer-bearing episode at all. The measure was
**session-touch**: it credited delivering *any* part of a session containing the
answer.

Under the strict measure the result does not shrink. **It reverses**: 388 to 351,
with 26 gains and 63 losses. The claim was withdrawn.

Two smaller failures sit inside the same study, and both are unit errors in a study
whose entire subject is units. A first pass compared evidence *episodes* against
evidence *sessions* and reported a 45-item regression that did not exist. A
denominator counted five never-ranked items as misses.

**Session-touch is not used anywhere in this paper.** On LoCoMo development it
reports 40 gains and zero losses where the strict measure reports 44 gains and **9
losses** — it hides every strict loss.

### 12.6 What the gates missed

A gate is only trustworthy if its tested population could have existed. Three cases
here where one could not:

- A targeted no-regression gate keyed on `(turn, item)` while its requirement keyed
  on `(question, turn, item)`. The condition was **unsatisfiable by construction, for
  any selector**. Correcting it turned a recorded failure into a pass.
- A cluster-floor study stopped as inert — and the first execution reached that
  branch only because its evaluator searched for domain labels that did not exist.
  The invalid artifact is preserved and corrected by a standalone amendment.
- Fourteen repository integrity gates failed unconditionally for months because
  constants were recorded under one line-ending convention and checked under another.
  The cost was fourteen gates that could not have detected real drift, and one real
  drift was sitting behind them.
- A fifteenth was found while this paper was being written, on the sealed holdout
  itself. The constant binding NF-004's LoCoMo corpus-lock record had never matched
  the file it names: that file has one revision and one hash, and the expected value
  matched nothing in the repository. Its two sibling constants verify clean, and the
  corpus lock's content is independently checkable and intact, so **no NF-004 number
  moves**. What moved is the gate's status — for its whole life it could not have
  detected a real change to the record it guards. It was recorded here while still
  unfixed, then corrected separately once the decision belonged to someone entitled to
  make it; `ERRATA.md` carries both halves in order. The correction makes the gate
  bind from now on. It does not retroactively validate the period it was inert, and
  NF-004's result never rested on it: that rests on a replay hash equalling its
  committed value and a vector seal reading 2,749 of 2,749 with zero misses.

---

## 13. Limitations

Each item names what would settle it. This is the complete list rather than a
restatement of scope caps already given at the claims they bound.

### 13.1 The instrument's band is 3.0, and most scored comparisons here are below it

Every *scored* comparison in this paper is a single run at a fixed seed. That was
recorded as a missing variance estimate until the estimate was made.

Five replicates of the deployed configuration — identical corpus, settings, seed and
standing runtime, run back to back in one server process — scored **11.0, 8.0, 8.0,
8.0 and 8.0**, in that order. Max minus min is **3.0**, against a decision rule
committed before the replicates ran.

It is not a spread but a switch, and the run order is the finding. Replicates two
through five are byte-identical across all 121 turns. **The one that diverges is
replicate one — the first run in a fresh server process**, the only one to meet an
empty slot. It diverges at turn 1 from a byte-identical 757-byte prompt and never
re-converges.

Stated that way it is sharper than "one of five was odd", and it reaches further:
every scored run in this arc that began on a cold server sits on the divergent side
of that switch, and no study in the arc pinned process state (§13.2). Rater disagreement was
measured separately and is near zero, 64 of 65 items unanimous, so this is
run-to-run variation and not scoring noise.

Figure 7 draws the band across every scored verdict in the arc. Applied uniformly and
in both directions, **three of this arc's four scored verdicts fall inside the band
and are not demonstrated**: the memory-tier contrast at 3.0, the
live-validation targeted regression at −2.0, and the tier-isolation result at −1.0.
*Not demonstrated is not refuted.* These may be real, and a single run per arm cannot
say. One asymmetry is worth stating: the memory-tier contrast has **less** protection
than the others, not more — its two arms ran hours apart and neither manifest records
a server process id, so the process state of the arc's cleanest architectural
comparison is unknowable from the committed artifacts.

**What the band does not touch** is everything offline and deterministic: gate
outcomes, delivery counts, character accounting, packing measurements, §6's sealed
holdout, §7's granularity results, §9's 152 gains and zero losses. Those are counts
and identities, not scores. *Settled by:* repeated runs at multiple seeds with
process state pinned, which no study in this arc pinned.

### 13.2 The runtime is not bit-reproducible

The programme's standing rule requires a byte-identical seeded-prefix rerun. On this
runtime that rule is satisfiable **between runs that share server process state** and
**not** between a cold-start run and a warm-start one — and no study in the arc pinned
process state. An identical 757-byte prompt at seed 5005, with one slot and
speculative decoding disabled, produced responses diverging at character 79.

This bounds every scored claim and none of the offline ones. *Settled by:* pinning
process state as a run gate.

### 13.3 Availability is not correctness

Every selection count here measures whether a fact was *present in the delivered
window*, not whether the model answered correctly. This was the largest structural
weakness of this paper's predecessor. **It has now been measured, and the weakness is
real.**

A pre-registered live run compared the shipping configuration against the deployed
baseline at one seed, fixing both reporting outcomes before any number existed:

| Registered bar | Result |
|---|---|
| Does the offline advantage convert? | **WEAK.** A six-item offline gap became +1 correctly attributed item |
| No targeted regression, tolerance 0.5 | **FAIL.** 1.5 of 8 against the baseline's 3.5 — a 2.0 shortfall, four times the tolerance |

The second was registered as a kill. The configuration's status is **not promoted**.

The mechanism is legible. Asked for two formatting rules planted in the first two
turns, the shipping configuration reported that it could not see the start of the
conversation: the coverage objective had spent its budget on domain spread and
stopped carrying the opening, which per-item cosine ranking had retained. Offline,
that same configuration preserved 16 of 16 targeted items. **Preserving an item's
availability and preserving the answer that depends on it are not the same property,
and this programme had measured only the first.**

**The finding that survives the band is not the score.** Both arms fabricated
confidently on the domain neither retrieved, one attributing a painting to the wrong
artist while still producing both correct pigment terms — which a presence-only
scorer credits as a hit. That is an identity, not a rating, so §13.1 does not touch
it, and it is the more durable result of the two: a measure that counts an item as
available when its text appears will score a confident fabrication as a success. The
−2.0 magnitude is as unreplicated as the +1 and neither is demonstrated; the kill bar
fired on a threshold registered before either number existed, and that stands
independently. *Settled by:* the frozen-context reader study described in §14.

### 13.4 One runtime, one embedder, and positive evidence of fragility

One model, one quantization, one machine, one embedder. Whether §8's results survive a
*different* embedder is unmeasured — but this is not a blank absence of evidence, and
it would be convenient to call it one. §12.3 shows the *same* embedder under a
different call shape flipping 6 of 146 committed payloads. A perturbation far smaller
than a model change already moves 4% of results, so the reasonable prior is that §8's
specific numbers are embedder-dependent. *Settled by:* rerunning the sweep under a
second embedder.

### 13.5 External scoring is substituted, not official

The external calibration run's end-to-end scores — 20.0% on an equal-quota subset and
12.22% post-stratified — are **Codex-substituted integrity scores**, because the
benchmark's pinned evaluator was unavailable and was replaced by a panel of hosted
models with AI adjudication. A binding amendment forbids placing either number against
published LongMemEval results, and this paper does not.

Two further boundaries. The corpus is a cleaned variant rather than the original
histories. And the benchmark authors' LLM-assisted indexing and time-aware query
expansion were available and **deliberately not adopted**, because they add generative
calls to the memory path. Some of the gap between this component and published systems
is that choice, and this paper does not claim the choice was free. *Settled by:* the
official evaluator on the registered answers.

### 13.6 The internal corpus is constructed, and one probe carries the breadth claims

Every internal breadth number — 6, 12, 14 and 15 of 17, and the rank-87 reading —
comes from **one enumeration question** at one turn. The corpus is constructed, and
its planted vocabulary is a specific reason to suspect the ranking inversion is a
property of the plant rather than of retrieval. §8.5 gives the external test, which
narrows the claim sharply, and §12.5 gives the rarity diagnostic that failed to
identify the mechanism. *Settled by:* multiple literal enumeration probes across
external domains.

### 13.7 The endurance corpus is 84% repeats

The 1,000-turn run holds only **156 distinct user-assistant pairs**; 844 of 1,000
episodes are exact content duplicates. Any saturation reading from that run has a
mechanical reason to saturate independent of the mechanism, and §10's growth and
latency findings are the parts unaffected. That run's scores were outside the scoring
audit and one of its arms was budget-noncompliant; they are not used in this paper.

### 13.8 AI raters, AI adjudicators

Scoring used three blind passes with registered adjudication triggers, but the
adjudicators were subagents rather than humans, and the three raters were three
models from one family — a departure disclosed in advance. Shared-family bias inflates
apparent agreement, and inflated agreement *understates* a band. The control sample
disagreed at 11.54%. *Settled by:* human adjudication of the same items.

### 13.9 Amendments exist after results

Twelve in the bakeoff alone. The programme records per amendment whether it preceded
the result it affects, and applies a legitimacy test permitting corrections to
measurement units and protocol contradictions while forbidding making a criterion
easier once results are known. The record is published so a reader can disagree with
individual calls.

### 13.10 LongMemEval is exhausted

Every item in that corpus has now been used by this programme. **No confirmatory claim
is available from it again**, and any registration written today inherits that
ceiling. The LoCoMo holdout in §6.1 is now the only sealed external evidence this
programme holds for the granularity result, and **LoCoMo is now spent too**: NF-004
read the six holdout conversations and HH-001 read them again. §5 is `REGISTERED-LIVE`
for that reason and cannot become confirmatory.

---

## 14. Conclusion

Eleven pre-registered efforts produced one architecture worth keeping, one
externally confirmed rule about how to use it, and a measurable account of why the
rest did not work.

**For a practitioner**, three things transfer.

*Score a candidate by its own text, not by its parent's.* This is the substitution
with sealed external confirmation — 843 to 935 of 1,098 on withheld conversations,
reproduced at 361 to 461 of 465 on a second corpus and 12 to 14 of 17 internally. The
mechanism is candidate size: a 2,550-character episode averages away the
298-character turn that answers the question.

*And do not read that as "finer is always better", because this paper's own data
refutes it.* On the same LongMemEval corpus, moving the ranking unit from the session
to the episode **loses 37 items**, 26 gains against 63 losses (§7.3). Turn ranking
beats episode ranking; session ranking also beats episode ranking. The episode loses
from both sides, which no monotone rule about fineness can produce. The confirmed
result is the specific substitution above, on units of roughly 240 to 300 characters.
Where the useful unit sits for a different corpus is not something this programme
measured, and §7.5 refutes the scope condition proposed to predict it.

*Do not prune the candidate pool to control cost.* On this store the deployed
shortlist contains no representative of one of four domains, so no selection rule
reaches it from there. That is a fact about the shortlist's contents rather than a
measured comparison, and it is the sharper reason to leave retention alone.

*Check whether your memory layer needs generative calls at all.* Every component this
programme removed was one that required them, and what is left is replayable and
provenance-preserving as a consequence. Mem0, Zep, Letta and Graphiti each spend at
least one generative call on this layer by their own published descriptions. One of
them was run here. On 300 questions, one reader and a matched budget, the layer that
spends nothing answered more of them than the layer that spent 1,646 calls and 284
minutes — and reached its store 41 times faster, in a sixth of the space, having
dropped none of what it was given.

**Three of the five sealed results were negative, and they are why the list above is
short.** A deterministic stopping controller reached Youden's J of 0.320 against a
registered 0.50. An absolute-threshold event segmenter closed 52 of 74 events on its
size cap against a 0.35 bar, and its relative successor then lost to chopping every
four episodes regardless of content. A surprisal-proximity capture signal scored AUC
0.416 against a 0.60 bar, below chance in five of six strata. Each was pre-registered
against a sealed holdout, and each closed a line this programme wanted to keep.

**For a researcher**, the useful part is the decomposition and the order inside it.
Retrieval failure here was not one thing. The candidate pool decided what could be
seen, the objective decided what was worth taking, and a similarity floor decided
what was unreachable at any weighting. The order is forced and structurally so: one
domain has no representative anywhere in the deployed shortlist, so no objective can
recover it from there. Widening the pool is not the first fix because it measured
better — it is first because the alternative is impossible. Separating the three
required a per-fact known optimum on the same store, a measurement costing an answer
key and exact cost accounting, and buying a sharper question than an end-to-end score.

**What this programme has not shown** is that any of it makes a reader answer better.
Availability and correctness were measured moving in opposite directions once, and
that result stands unrescued. The next decision-relevant experiment is therefore not
another retrieval study. It is a reader study over two already-frozen contexts —
whether the 14-of-17 context causes a reader to use more correct facts than the
12-of-17 context, under an identical prompt and runtime, scored as a 17-bit
fact-use vector rather than on the 13-point rubric whose 3.0-point band cannot
resolve a two-item contrast. That design is prepared and unregistered. The internal
corpus is exhausted, so its maximum evidential status is characterization, and the
value is causal interpretation rather than fresh-corpus confirmation.

The programme's summary of ten studies and one bakeoff is that, at the one probe
where it was measured item by item, the model used all ten available facts and
invented none. That is a statement about one probe and it does not generalize: §13.3
records the counterexample, where both live arms fabricated confidently on the domain
neither of them retrieved — one of them producing the correct pigment terms attached
to the wrong painter, which a presence-only scorer credits.

So the failures measured here were delivery failures, and delivery turned out to be a
selection problem sitting on top of a candidate set already narrowed by the wrong
rule and scored at the wrong unit. What happens when delivery succeeds and the reader
still gets it wrong is the part this programme has not measured.

---

## Figures

Seven, generated by `scripts/generate_paper_002_figures.py` from committed artifacts.
No value in any figure is typed by hand. Each caption carries the first 16 hex digits
of the SHA-256 of the artifacts it draws from, hashed over git blob content so the
values are stable across platforms; `paper/figures/figure_manifest_002.json` records
all 33 inputs alongside the commit they were read at. Vector SVG alongside PNG. Two
consecutive runs produce byte-identical SVGs and manifest.

The script reads and hashes the *same* bytes — `git show HEAD:<path>` is hashed and
then parsed — so a recorded hash always corresponds to the values plotted. Five
registered bars exist only in prose rather than in JSON, and are extracted by a
strict pattern that fails the build rather than plotting a stale value if the
wording changes.

**Figure 1 — The head-to-head.** `f1_head_to_head.svg`
*What each memory layer answered, beside what it spent to build the store.*
Judged and containment accuracy over 300 questions at three replicates, one
local reader, one 16,000-character budget: whole conversation 0.613, this
component 0.563, fixed-width chunk retrieval 0.550, Mem0 2.0.18 0.487, no
memory 0.000. The right panel is **prompt tokens spent building the store — 5,988,818 for Mem0
against zero for every other arm**, across 1,646 calls and 284 minutes. Tokens
rather than calls, because a call count understates a generative write path: the
prompt grows as the store does. The figure is measured over 88% of the ingest, so
the true total is higher. The two panels are not one
trade curve: accuracy and build cost are different quantities and a single
axis would imply a relationship the data does not describe. Sources:
`result.json` `7fa4119c29f06b1c`, `cost/mem0_ingest.json` `a9653199d0d8317f`,
`cost/storage.json` `adcc2ea410046e22`.

**Figure 2 — What the store costs to build, as it grows.** `f2_mem0_ingest_latency.svg`
*Mem0's per-pair ingest latency against the number of memories already stored.*
Derived from Mem0's own history table: each `add()` emits a burst of writes
milliseconds apart, and the gap between bursts is the wall clock that call
spent. 1,137 measured bursts, store reaching 1,825 memories, p50 11.9 s and
p95 34.8 s. First decile mean 14.5 s against last decile 16.5 s — a 1.13×
drift, not a runaway. The flat line at zero is this component's generative
cost, which is architectural rather than measured. **The latency points cover
only the 69% of pairs that wrote something**; a pair Mem0 declined to store
leaves no burst and is invisible here, and is likely the faster case. Source:
`cost/mem0_ingest_latency.json` `0ad65363b635b6e7`.

**Figure 3 — The sealed holdout.** `f3_sealed_holdout.svg`
*Six LoCoMo conversations withheld until the bars were locked, and the ranking unit
is the whole difference.* Complete exact-evidence delivery over 1,098 records at a
16,000-character budget: source order 258, session-score inheritance 843, own-cosine
pair ranking 935. The gain/loss panel shows 140 against 48 with 910 ties, against the
registered bar of gains at least twice losses — ratio 2.92, one-sided exact binomial
p = 6.19e-12. Every one of the six withheld conversations is net positive: +7, +6,
+13, +30, +15, +21. Median packed characters differ by 2, so the treatment is not
spending more. **The result is bounded to availability and authorizes no reader
claim.** Sources: `g6_holdout_outcomes.json` `7be2668d21163c93`,
`g7_result_integrity.json` `890b4831d530e9a7`, `NF_004_PRE_REGISTRATION.md`
`de2d5e05646b769c`.

**Figure 4 — Granularity across three corpora.** `f4_granularity_three_corpora.svg`
*The same substitution, three corpora, and the candidate size that explains it.*
Left: exact-evidence delivery before and after ranking each candidate by its own
cosine — LongMemEval 361 to 461 of 465, LoCoMo 843 to 935 of 1,098, the internal
store 12 to 14 of 17. Right: median candidate length with p10–p90 whiskers —
LongMemEval evidence episodes 2,550 characters, their exact source turns 298, LoCoMo
adjacent pairs 241. An embedding of the 2,550-character parent averages away the
298-character turn that answers the question. LongMemEval's gain/loss ratio is
undefined rather than large — 100 gains and zero losses — and is drawn off-scale
with its raw counts. §7.3 marks where the direction reverses at a coarser unit.
Sources: `g8_integrity.json` `17cbdbad274c1863`, `exploration.json`
`00d78ad3bd113abb`, `g6_holdout_outcomes.json` `7be2668d21163c93`,
`g8_g9_measurement.json` `d20dffd563e5777e`.

**Figure 5 — Every mechanism against its own bar.** `f5_mechanisms_against_bars.svg`
*Twelve mechanisms fell short of the bar each had to clear; the three that cleared
are all the same family.* Each numeric row is rescaled so 1.0 is that row's own
registered bar, which is the only way results measured in incompatible units belong
on one axis. Fifteen rows have a committed numeric bar; eleven more have none and are
drawn categorically with the reason parsed from the ledger rather than assigned a
number. The three rows above 1.0 are NF-004, NF-005 and NF-006 — the granularity
family. **This is the figure that answers why the survivor survived: not because it
was designed better, but because it is the only thing that cleared its gate.**
Sources: `RETRIEVAL_MECHANISM_LEDGER.md` `6c3875cc4f63046d`,
`retrieval_bakeoff_report.md` `681208a78d12f591`, `tier3_results.json`
`8c229f7b70de9a70`, `e001_results.json` `a996ecd881ae52aa`, `gate_report.json`
`1a43d8a5345188af`, `gates_holdout.json` `13dd30919acd91bf`.

**Figure 6 — Packing priority is a delivery gate.** `f6_packing_priority_gate.svg`
*The evidence was ranked correctly and then not delivered.* Left: reversing only the
fill order on 500 external stores moves any-evidence-session recall from 109 to 261
of 470, with 152 gains and zero losses, while the median delivered block stays at
31,920 characters and the median path composition stays 16 recency, 0 non-recency
similarity, 1 coverage. The aggregate that moves is delivered similarity episodes, 26
to 476 — the medians concealed a twentyfold change in the tier the system exists to
provide. Right: on the internal store the deployed order delivered zero similarity
episodes and zero characters at 8 of 8 probes. §9.3 records that the live correction
built on this was tested and rejected. Sources: `paired_comparison.json`
`6f18b46f7316f8dc`, `paired_comparison.json` `5dad3eabfac3df39`, `path_split.csv`
`d26440d1476e8923`.

**Figure 7 — The standing ladder and the instrument band.**
`f7_standing_ladder.svg`
*What the programme measured, sorted by what would make it believable.* Fifteen
results in three tiers — confirmatory under a sealed holdout, deterministic and
offline, and scored-live. The shaded region is the measured run-to-run band of 3.0
points, from five replicates of one configuration under identical corpus, settings,
seed and runtime that scored 8.0, 8.0, 8.0, 8.0 and 11.0. It swallows three of the
arc's scored verdicts: the memory-tier contrast at +3.0, the live-validation
regression at −2.0, and the tier-isolation result at −1.0. The corrected treatment
series at +3.5 sits outside it, and exceeding a band is not the same as being
demonstrated. **Nothing in the top two tiers is touched by the band** — those are
counts and identities rather than scores. Sources: `band_verdict.json`
`cb241ac01cbcde5f`, `verdict.json` `83bd4bbbc4209a48`, `LV_001_report.md`
`cd3dc4cdaa450002`, `SAL_001_FINAL_DESIGN.json` `783cc8ad7f5796ac`.

**Figure 8 — The budget efficiency gap.** `f8_budget_efficiency_gap.svg`
*The constraint was never capacity: the tallest result is also the narrowest.* Each
horizontal stem runs from zero to the characters spent, at a height equal to the
items made available, over the same store at the same enforced 32,000-character
budget. The deployed baseline reaches 6 of 17 for 31,946 characters; the shipped
set-level configuration 12 of 17 for 31,569; the exact known optimum 14 of 17 for
5,058, leaving 26,942 unused; its greedy variant 15 of 17 for 5,455. **The top two
bars change two things against the baseline, not one** — the selector and the
candidate pool; §8.3 separates them, and on the deployed pool the same configuration
scores 5 of 17 against the baseline's 6. **Both optima are computed with the answer
key and are bounds, not methods.** Sources: `a0_baseline.json` `7645e4746715a965`,
`e005_results.json` `07b714389697c6e5`, `achievability.json` `770792d09e07978d`.

**Figure 9 — Growth and cost.** `f9_growth_and_cost.svg`
*The growth belonged to the harness; the cost was five times its projection.* Left:
the 95th percentile of the retrieved block per 100-turn bucket over the final 500
turns of the 1,000-turn run. In the study runner the block rises 23,238 characters in
one arm and 28,701 in the other, still setting records in the last bucket; replayed
through the extracted library at the same budget it moves +18 characters and breaches
the budget on 0 of 1,000 turns — while truncating on 895 of them, so it is bounded
because enforced, not because demand is small. Right: measured median selection
latency against candidate count, with the withdrawn projection drawn as the range it
actually published rather than a single point. 190 ms measured at 1,000 candidates,
exponent 1.25 over 50–1,000, and clustering's share rising from 37% to 81%. Values
above 1,000 candidates are projections, drawn dashed. Sources: `dx002_results.json`
`f8ab79ab041cb3e3`, `ge0_growth_gate.json` `350fe20bbc3beed9`, `latency_curve.csv`
`0d2b8075ff5a971f`, `growth_measurement.json` `20d65a018e28b03f`,
`latency_components.csv` `82bbbe38e9423d00`.

---

## Appendices

**A. Evidence spine** — `paper/notes/EVIDENCE_SPINE.md`. Every number in this paper
with its artifact, its SHA prefix where one exists, and its standing under §4.1's
taxonomy. Built before the prose, so the draft was assembled from it rather than
checked against it afterwards.

**B. Withdrawn claims** — `paper/notes/DO_NOT_WRITE.md`. Thirty-five sentences this
programme has published and then corrected, each with its replacement, drawn from
`ERRATA.md` and two adversarial review cycles. A rewrite is when withdrawn claims
come back, because they are usually the cleaner sentence.

**C. Claim gates** — `scripts/check_paper_002_claims.py`. Two automated checks:
every numeric literal in this paper must appear in the evidence spine, and no value
on the machine-checkable superseded list may appear at all. Both pass at the
committed revision. Neither proves a claim is right; they catch the two failure
modes this repository has actually committed.

**D. Corrections index** — `ERRATA.md`, 20 entries, cross-referenced from §12. It
includes one entry that was wrong when first written and is superseded in place by
its own reversal, with the original text kept so the mistake stays visible.

**E. Study reports** — `experiments/`. Each carries its pre-registration commit SHA,
its preflight record, its gate outcomes, and its own boundary section. Where a
report and a summary disagree, the report is authoritative; this paper was written
from the reports.

**F. Amendment record** — per-study `amendments/` directories, each a standalone file
recording whether it preceded the result it affects.

**G. Reproduction** — `paper/REPRODUCTION.md` and `paper/reproduce_headline.py`. The
script rebuilds the 5,058-character exact optimum from the committed turn log through
the installed library and checks its length and SHA-256 against the committed values,
verified in a clean virtual environment containing only `episodic`.

Stated plainly, because it is a limitation and not a feature: **the selection results
cannot be reproduced this way.** They need per-episode embedding vectors, which live
in a store that is gitignored and was never committed, and regenerating them needs
the pinned embedder, which is not in the repository either. One number in this paper
is reproducible from committed data alone, and it is that one.

**H. Review record** — `paper/reviews/`. Two adversarial cycles against this paper's
predecessor (sixteen objections and ten, all accepted) and a slop audit. The
constraints they established carry forward into this document and are listed in
appendix B §4.

**I. Pipeline log** — `paper/notes/PIPELINE_LOG.md`. The academic-research-skills
stages this rewrite ran, and the verdict returned at each checkpoint.

**J. Competitive landscape** — `paper/notes/COMPETITIVE_LANDSCAPE.md`. Published
results for the systems named in §2, with citation verification status and the
boundary. §4.1 of that file records what HH-001 changed: Mem0 was run, so a
comparison to **Mem0 as run here** is measured; every other system in the file is
still published-only, and a comparison to Mem0's published score is still
forbidden.

---

## Provenance of this document

**The paper is generated, not authored.** This Markdown file is the only place a
claim may be edited. `paper/figures/` is a build output of
`scripts/generate_paper_002_figures.py`, which reads every plotted value from a
committed artifact and records the SHA-256 of each input in
`paper/figures/figure_manifest_002.json`. The PDF is a build output of
`scripts/build_paper_pdf.py`. Hand-editing a figure, the manifest, or the PDF is a
defect rather than a shortcut.

If this file and a figure disagree, this file is right and the build script is
broken. If this file and a study's pre-registration disagree, **the pre-registration
governs** — that conflict is a defect to be flagged, not reconciled silently.

**Supersedes PAPER-001.** The predecessor's structure led with the negative
results and reached its sealed-holdout confirmation in passing. Two numbers changed in
this rewrite; the ordering and the standing labels did. Six stale cross-references
in the predecessor were found during the rewrite audit and are listed in appendix B
§6.
