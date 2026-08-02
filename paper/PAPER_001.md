# Selection, Not Capacity

### A measured decomposition of retrieval failure in conversational memory, and what survived eleven negative results

**Idris Applied AI Research** — independent, non-profit
Repository: `contextDecayWindow` · Licence: CC BY 4.0
Draft — PAPER-001, seven-pass loop complete

---

## Abstract

This is a single-program experience report, not a general-claims paper. One
corpus, one probe set, one model, one quantization, one machine, one seed; there
is no error bar anywhere in the work it describes, and none of it was calibrated
against an external benchmark. We say so first because it decides how everything
below should be read.

Across ten pre-registered studies and one registered retrieval bakeoff, this
program tried to make a language model hold a long conversation by rebuilding a
small context each turn. Write-time selection failed in five studies. Moving
selection to query time failed in the bakeoff, which surfaced 8 of 17 target
facts where write-time formation had reached 11. Graph construction, query-type
routing, approximate search, query segmentation, and attention-derived term
selection each failed their own registered gates. What explains the set is
measurable: on this corpus the four highest-cosine episodes carry none of the
enumeration probe's target facts, and the last still-needed item does not appear
until rank 87 of 119. The same ordering is near-optimal on the eight targeted
probes, placing every needed item inside rank 2. The program has one
enumeration probe and eight lookup probes, so this is one instance behaving
unlike eight, not an established property of query types.

Separating that failure gives three constraints that bind in a forced order. The
candidate pool binds first, on domain coverage: with the selector frozen,
widening it from 34 to 119 episodes moves 5 of 17 items across 2 domains to 12
across 4, and the deployed pool contains no episode of one domain at any
setting. The objective binds second, and only after the pool is widened — on the
deployed pool, the set-level objective this program ships scores 5 of 17 against
the 6 of 17 baseline it replaces, while the best of 146 configurations on that
same pool reaches 13. Greedy search runs at 0.954–0.9996 of a data-dependent
bound, so the objective and not the search is the limit. A similarity floor
binds last: the final missing episode needs a query cosine of 0.225 and has
0.056, a shortfall no reweighting closes.

Capacity was never the constraint. An exact optimum computed on the same store
makes 14 of 17 items available in 5,058 of 32,000 characters; deployed selection
made 6 available while spending 31,946. These are availability counts, measured
offline against a planted answer key; no live run of the resulting configuration
exists. Eleven mechanisms were removed — distillation, promotion filters, a
topic layer, an associative graph, routing, approximate search among them — and
what remains is an append-only store, a recency window, similarity retrieval,
and a coverage objective, with no generative model calls in the memory path.
That design is reproducible and free of generated intermediate text because the
removed components were the ones that produced it.

---

## 1. Introduction

A long conversation forces a trade. Keep the transcript and the model slows down
and loses the middle. Summarize it and the details are gone. This program spent
eleven pre-registered efforts on a third option: store every exchange verbatim
and rebuild a small, relevant context each turn.

Most of those efforts failed. This paper is about what the failures had in
common, which turned out to be measurable, and about what was left after the
failed parts were removed, which turned out to be small.

### 1.1 The category, declared

This is a case study of one program. It is not a general-claims paper, and the
distinction is not modesty — it decides which sentences are permitted.

The program has never been externally calibrated. Study 003 retired external
baselines in favour of self-comparison and nothing restored them. LoCoMo and
LongMemEval were adopted in principle and never run. Every number here comes
from one corpus with facts planted at known turns, one rubric locked since
Study 002, one local model at one quantization, one machine, and one seed. Every
comparison is a single run. There is no variance estimate anywhere in the
program, and therefore no significance test that would mean anything.

Declaring this is what makes the report legitimate rather than defective. A case
study reporting what happened across eleven efforts on one program is a readable
form. The same content claiming general findings would deserve rejection. So the
findings below are stated as *on this corpus*, and where a result would be worth
testing elsewhere we name the experiment instead of implying the outcome.

### 1.2 Contributions

1. **A decomposition of where retrieval failure lives** (§5): a candidate pool,
   a selection objective, and a similarity floor, each separately bounded. They
   are not independent. They bind in a forced order, and applying the second fix
   without the first makes the shipped configuration worse than the baseline it
   replaces (§5.7).
2. **The measurement that makes the decomposition possible**: a per-fact known
   optimum computed on the same store under exact serialized-cost accounting
   (§5.1). It requires an answer key and exact cost accounting, which is why it
   is unusual rather than difficult.
3. **A subtraction result** (§6): what eleven efforts removed, and why the
   properties that make what remains deployable are consequences of the negative
   results rather than independent design choices.
4. **A correction record** (§7), including one instance where a diagnostic
   written to catch a specific failure class nearly committed that exact
   failure.

### 1.3 What this paper does not claim

No comparison against HippoRAG, Mem0, Zep, or Letta; none were run. No general
claim that similarity retrieval fails — §5.5 measures the opposite on eight of
nine probes. No novelty for maximal marginal relevance, facility location, or
submodular selection, which are established methods; what is offered is the
decomposition and the measurement, not the selector. And no claim that the 12
of 17 result is good: it sits below the program's own registered bar of 14 and
below the 15 that a known optimum reaches on the same store for a sixth of the
cost.

---

## 2. Related work

Studies 001–010 were designed and run before this program's first literature
scan, and are committed with SHAs that show it. We state that once because it
explains why the early designs rediscovered known ideas, and we do not press it
further: arriving independently at a worse version of a published method is not
a contribution.

**Entity-centric indexing.** HippoRAG builds a knowledge graph over extracted
entities and retrieves by traversal. The authors' own follow-up work identifies
entity-centricity as a limitation. This program's hardest repeated failure is
consistent with that: six target facts sit in spans where the entity extractor
finds zero entities, so an entity-gated index has no path to them. That is why
entity extraction was ruled out as a primary index here, and why HippoRAG was
treated as a comparison target rather than a component to adopt — though the
comparison was never run.

**Structure over retrieved units.** GraphRAG, SGMem, and CodaRAG each impose
explicit structure on retrieved material. This program built the corresponding
mechanism — an associative graph over observed co-activation — and no
configuration cleared its advancement gate (§4.3).

**Deployed conversational memory.** Letta, Mem0, and Zep ship systems in this
space. This program's surviving design (§6) is smaller than all of them, and the
comparison that would establish whether that matters was not run.

**Benchmarks.** LoCoMo and LongMemEval are the calibration this program lacks.
They are named here as the gap, not as work this paper competes with.

The placement is narrow. Every system above consumes a candidate set produced
upstream by similarity ranking. This paper measures that set rather than
proposing another structure over it.

---

## 3. Method

Four properties make the rest of the paper checkable.

**Pre-registration and binding gates.** Each study's design was committed before
implementation, and that commit's SHA is the integrity anchor. Pre-registration
commits contain no implementation files. Offline gates run before inference and
bind: Study 008 stopped at its pre-run gates when replay proved that no
registered fill cap between 1 and 50 could pass the breadth and targeted gates
jointly, which prevented four invalid 121-turn runs.

**Amendments, recorded not absorbed.** Locked registrations are never edited.
Changes go in standalone amendment files carrying the trigger, the change, the
rationale, and the authorization. Whether an amendment preceded the result it
affects is recorded per amendment rather than asserted globally; the bakeoff
carries twelve, each with that column filled in.

**Exact serialized cost.** Every character budget charges the complete
serialized block — per-episode tags, metadata, and separators included, not just
the source text. This was not true before DR-001 (§7.2), and correcting it moved
published numbers by up to 68%. Every figure in this paper uses the corrected
accounting.

**Determinism and leakage control.** Fixed seed, one slot, speculative decoding
disabled, and a required byte-identical seeded-prefix rerun. Mechanism code —
retrieval, formation, ranking, gating — may not read the answer key; measurement
may. The boundary is enforced by grep, by import-graph checks, and by a planted
test violation that must be caught.

**Controls versus baselines.** A control runs from checked-out prior code in a
separate worktree. Disabling a feature in the current runner does not produce a
control, and results from flag-disabled arms were rejected.

---

## 4. The arc

Ten numbered studies and one registered bakeoff. The table is the record; the
turning points are the argument.

| # | Added | Outcome | Terminal diagnosis |
|---|---|---|---|
| 001 | Recency plus similarity retrieval | PARTIAL (2/3 bars) | Similarity fired once in 32 turns. Thirty topics for 32 episodes compressed nothing |
| 002 | Consolidation, rule pinning, 120 turns | PARTIAL (3/4) | Similarity recovered buried facts; consolidation produced 52 topics |
| 003 | Long-term write path, four promotion filters | PARTIAL (2/3) | The weighted route was arithmetically unreachable; every promotion used the bypass, making it a novelty-spike detector |
| 004 | Long-term read path and arbitration | PARTIAL (1/3) | Retrieval ran on all 90 eligible turns with zero displacement; the store lacked the later-domain facts |
| 005 | Permissive capture, extractive distillation | PARTIAL | Absolute entity and number counts selected long responses. The salience metric was a verbosity detector; 2 of 4 domains formed |
| 006 | Length-normalized span selection | PARTIAL (1/3) | Formation reached 4 of 4 domains; records shrank ~28×, and count-based retrieval budgets silently broke |
| 007 | Character-budgeted retrieval | PARTIAL (2/3) | Best score of the series. The model used all 10 delivered facts and invented none; 7 required facts were absent from the store |
| 008 | Rendering-by-floor factorial | STOPPED AT PRE-RUN GATES | No fill cap from 1 to 50 passed breadth and targeted gates jointly |
| 009 | Pure-STM null test | PARTIAL, null decisive | Same seed: 9.0 without the memory tier, 12.0 with it |
| 010 | 1,000-turn endurance | STOPPED AT G2 | Post-stop arms were budget-noncompliant by 67.9% and 68.2%; scores unaudited; one bar not evaluable |
| — | Retrieval bakeoff | MIXED | Query-time selection did not recover what formation missed |

Scores are post-audit corrected values (§7.1). They are not a controlled series
— runtime and response budgets changed across it — and Figure 4 carries that
warning where the numbers appear.

### 4.1 Write-time selection cannot anticipate a query

Studies 003 through 007 are five attempts to decide, at write time, what deserves
to be remembered. Every one returned PARTIAL, and the reasons converge on one
shape: each policy optimized a proxy that could be satisfied without the property
it was supposed to certify.

Study 003's promotion route could not fire, because novelty and association were
complementary values derived from a single centroid and their weighted sum was
capped below the threshold. Every promotion therefore came through the bypass,
and a mechanism registered as salience judgment behaved as spike detection.
Study 005 replaced it with absolute entity and number counts, which selected the
longest responses. Study 006 normalized by length, which fixed formation — 4 of
4 domains, faithful and junk-free — and broke delivery, because records shrank by
about 28× while the retrieval budget was still counted in records rather than
characters.

The terminal diagnosis is specific. Density, the best of the write-time salience
signals, ranks the six hardest planted facts between 89th and 316th. Word-level
inverse document frequency ranks them worse. These are facts like *photophores*,
*mantle margin*, and *ultramarine glaze*: rare technical phrases whose component
words are common.

### 4.2 Moving selection to query time did not recover it

If write-time selection cannot anticipate a query, the obvious repair is to
select at query time over a permissive raw store. The bakeoff registered that as
its central premise and refuted it. The best registered 32,000-character
retrieval block surfaced **8 of 17** target facts — below the 11 of 17 that the
formation era could reach. All 17 facts were present in the raw store. Retrieval
did not find them.

### 4.3 The mechanisms the field favors did not clear their own gates

The bakeoff tested three more pillars of the proposed pivot and advanced none.
Graph retrieval over observed co-activation: no configuration of eight edge
types at three traversal depths cleared the advancement gate, so the
extraction-based follow-up never ran. Query-type routing: an oracle upper bound
of **6.09%**, against a registered 10% build threshold — an oracle, meaning the
number assumes perfect routing decisions and is still too small to justify
building the router. Approximate nearest-neighbour search: recall degraded at
synthetic scale.

### 4.4 The first clean positive was volume, with no mechanism at all

Widened raw short-term memory delivered all six formation-blind facts and the
model used five of them correctly in targeted answers. No selection filter was
involved. This remains the program's most specific positive result, and it is
the reason §6 treats raw verbatim storage as load-bearing rather than as a
default.

One caution the bakeoff records and this paper repeats: the widened arm also
produced 13 of 17 correctly attributed facts in a live answer, and that figure
does not overturn the 8 of 17 above. They measure different objects — offline
content in a single retrieval block against end-to-end content in a generated
answer, over different denominators — and a live answer can contain facts
repeated from earlier probe responses that the final block never carried.

### 4.5 Query representation was not the problem either

Two further attempts moved the failure to the query side. Exhaustive mechanical
segmentation (E002) improved its exact-budget baseline from 6 of 17 to 10 of 17,
using 21,761 characters where the baseline spent 31,946 — and still failed its
locked 14 of 17 bar, so it was killed. Attention-derived term selection (E001),
run as an oracle over 714 candidate cue rows, moved the relevant cosine from
0.120 to a best-found 0.210 against a retrieval threshold of 0.48. No row
reached the threshold. The oracle was not a ceiling — 266 of 384 selected
attention heads were not sparse — but the program closed the line anyway.

Five studies of write-time selection, one bakeoff of query-time selection, and
two attempts at query representation. Each is an unremarkable negative result on
its own. §5 is what they have in common.

---

## 5. The decomposition

### 5.1 The target was reachable, in the sense of being present and affordable

**Two notes before the numbers.**

*Which corpus.* All of §5 is one 121-turn scripted conversation whose store
holds 119 episodes eligible for the turn-120 breadth probe. §6.4's growth and
latency results come from a different, 1,000-turn run and are labelled there.
The two are not interchangeable, and no §5 result is established at 1,000 turns.

*What the counts measure.* 6 of 17, 12 of 17, 14 of 17, 15 of 17 are
*availability*: whether an item's text was present in the block delivered to the
model. They are not answer correctness. A separate rubric scores answers, and no
arm of the selection work was ever scored end-to-end. Where this section says a
configuration "delivers" facts, it means the facts were in the window, nothing
more — and §8.6 records a specific way availability and correctness come apart
on this probe.

Before asking why selection failed, the program asked what success would have
cost. AR-001 computed, on the same store and under exact serialized accounting,
the cheapest set of episodes that makes the breadth items available.

All 17 items are present in the store; 76 of the 119 eligible episodes carry at
least one. The exact minimum for 14 of 17 items is **5,058 characters across
five episodes**, leaving 26,942 characters of the 32,000-character budget unused.
A greedy variant reaches 15 of 17 for 5,455 characters. Even 17 of 17 costs only
7,592. The most expensive single domain, art, needs 3,182 characters — under a
tenth of the budget.

Deployed selection made **6 of 17 available while spending 31,946 characters**.

Figure 2 is that comparison. The budget was never tight. Selection spent it on
episodes that carried nothing.

Three cautions attach to the optimum and hold everywhere it appears below.

*It is computed with the answer key*, so it is a bound and not a method. No
deployable retriever can be expected to find it.

*There are two sets, easily conflated.* The exact 14-fact optimum covers turns
{90, 112, 113, 115, 118}; the greedy 15-fact set covers turns {90, 112, 113,
**116**, 118}. Everything the program calls "the oracle" downstream, including
every overlap figure in this paper, is the greedy 15-fact set.

*Four of the five episodes are prior probe exchanges, not original plant
sources.* Only turn 90 is a plant source; turns 112, 113, 116 and 118 are turns
at which an earlier probe was asked and answered. So a substantial part of what
makes the target cheap is that the conversation had already restated those facts
in compact form. Achievability holds under the registered eligibility rule —
any episode before the probe turn counts — and not under a stricter rule
admitting only plant sources. A reader who prefers the stricter rule should
discount the 15 of 17 accordingly, and §8.6 returns to this.

### 5.2 Set-level selection recovers about half the gap

If the budget is not the constraint and the facts are present, the remaining
suspect is the rule that decides which episodes to take. The deployed rule ranks
each episode against the query independently and takes the best until the budget
fills. That rule cannot represent redundancy: an episode's value does not depend
on what has already been selected.

E005 replaced it with three set-level objectives — maximal marginal relevance,
facility location, and relevance plus cluster diversity — swept over 146
configurations per candidate pool at the enforced budget, with zero inference
calls and a byte-identical rerun.

The best configuration that passed every gate makes **12 of 17 items available
across 4 of 4 domains at 31,569 characters**, preserving all 16 targeted items
and recovering 4 of the 5 known-optimum episodes.

**That headline moves two variables at once, and the paper says so before using
it.** The deployed baseline is the deployed selector running on the deployed
34-episode pre-filter; the 12 of 17 is a set-level selector running on the full
119-episode store. Selector and pool both changed. The per-pool minima across
the same 146 configurations make the confound concrete:

| Pool | Worst of 146 | Best of 146 | Frozen shipped config | Deployed baseline |
|---|---:|---:|---:|---:|
| deployed pre-filter, 34 | **4/17** | 13/17 | **5/17** | 6/17 |
| cosine top-100 | 5/17 | 13/17 | 9/17 | not applicable |
| full eligible store, 119 | 7/17 | 13/17 | 12/17 | not applicable |

The baseline column has one entry because the baseline has no pool variable: it
is the deployed pipeline's own pre-filter and selector together, and it was
never run against a wider pool. The blank rows are not zero measurements.

Read the first row. On the pool the system actually used, set-level
configurations fall as low as 4 of 17, and **the configuration this program
ships scores 5 of 17 there — below the 6 of 17 baseline it replaces.** The
selector is not a free improvement. It is an improvement that requires the wider
pool, and without the pool it is a regression.

The honest within-pool statement is the third column against the fourth: on the
deployed 34-episode pool, holding the pool fixed, the best of 146 set-level
configurations makes 13 of 17 available against the baseline's 6. That is a
selector effect. The 6 → 12 headline is a selector-and-pool effect, and §5.3
separates the second half of it.

Three further results matter more than the headline.

**The highest-scoring selector was the worst one.** Facility location reached 13
of 17, the highest raw count in the sweep, and passed no gate at any setting,
because it delivered the monetary domain 0 of 4 every time. It improved the
total by abandoning a domain. Only the per-domain check caught it; a reader
looking at fact counts would have shipped it. Figure 5.

**A parameter registered as inert was not.** Cost scaling was predicted to make
no difference on a budget with slack. The budget is slack for the optimum and
not for a selector registered to fill it, and the prediction failed.

**The search is not the limit.** The bound here is data-dependent, not the
worst-case submodular constant: at the final greedy set, each unselected
candidate's marginal gain per unit cost is computed, the remaining budget is
filled fractionally in that order, and the result is added to the achieved
objective value to give an upper bound on the optimum. Across the 405
configurations where that bound is computable, the greedy solution sits between
**0.954 and 0.9996** of it; the shipped configuration is at 0.9927. A better
search over the same objective has almost nothing left to find, so what limits
the result is the objective.

The bound is computable only for the two arms with a set function. All 33
non-computable rows are the maximal-marginal-relevance arm, which has no set
function to bound — so this reading covers facility location and
relevance-plus-diversity, and says nothing about MMR's search quality.

### 5.3 The candidate pool binds on domain coverage

Selection runs over whatever the pre-filter admits. DR-002 froze the shipped
configuration and varied only pool membership — same store, same renderer, same
embedding.

| Pool | Candidates | Facts | Domains | Known-optimum overlap |
|---|---:|---:|---:|---:|
| deployed pre-filter | 34 | 5/17 | 2/4 | 1/5 |
| cosine top-100 | 100 | 9/17 | 3/4 | 0/5 |
| full eligible store | 119 | 12/17 | 4/4 | 4/5 |

Widening the pool moves the same configuration from 5 of 17 across 2 domains to
12 across 4. Figure 3.

Two things keep this honest. It is a **frozen-configuration** readout, not a
sweep: the best of the 146 configurations reaches 13 of 17 on all three pools,
so the pool's binding effect is properly read in domain coverage rather than in
that maximum. And on the deployed 34-episode pool, **no configuration covers
four domains at all**, because the art domain has no representative anywhere in
the top 34. That is a statement about what the pre-filter makes possible, not
about how well any selector searches.

The middle row deserves a second look. Dropping only the 19 lowest-cosine
episodes to form the 100-pool costs three facts, the whole art domain, and *all*
overlap with the known optimum — even though four of the five optimum episodes
survive the cut. The selector clusters over the pool, so removing the tail
reshuffles the objective rather than merely removing options. Pool size does not
predict what removal costs.

### 5.4 The ordering is anti-correlated at the top, for one query type

DR-002 registered its rule before computing any rank: *any fact-bearing
selection at cosine rank 80 or worse means cosine ordering is the wrong prior
for breadth.*

It fired. The worst fact-bearing selection sits at rank 86 and carries two of
the four art items. Around it:

- **The four highest-cosine episodes in the store carry zero target facts.**
- The first fact-bearing episode is at rank 5; the last still-needed item does
  not appear until rank 87 of 119.
- Both art contributors sit at ranks 50 and 86, which is why the deployed
  34-episode pool cannot reach four domains.
- The five known-optimum episodes sit at ranks 14, 20, 22, 86, and 112. The
  shipped configuration recovers four of them, including the one at rank 86, and
  misses only the deepest.

Figure 1. The failure is not that the ordering is noisy. At the top it is
anti-correlated: the most query-similar episodes are the least informative for
this probe, and one of the two domains that decides the gate is unreachable
before rank 50.

That a set-level objective reaches rank 86 at all is worth stating, because it
bounds the claim. The objective partially compensates for a bad ordering. It
does not compensate fully.

### 5.5 What the inversion does not explain

The result in §5.4 invites a larger claim — that every mechanism in this
program, and much of the published architecture in this space, ran downstream of
a broken candidate ordering. DR-002 tested that reading and **measured it
false**.

On the eight targeted probes, cosine ordering places every needed item **inside
rank 2**. The top four candidates carry a target item on every one of them. That
is not adequate performance, it is near-optimal, and it is why targeted recall
runs at 60 of 60 and why 137 of the 146 configurations preserve 16 of 16
targeted items without effort. Q11 — the enumeration probe — is the only probe
where the ordering fails, and it is the only enumeration probe the program has.

The inversion also fails to explain most of §4. It does not explain the
formation-side failures, which ran at write time upstream of any retrieval
filter. It does not explain Study 003's promotion route, which was
arithmetically unreachable. It does not explain Study 007, where the model used
all 10 delivered facts and seven required facts were simply absent from the
store. It is contradicted by the bakeoff's routing oracle, which assumed perfect
selection and still ceilinged at 6.09%. And it is contradicted by widened raw
short-term memory, which delivered 6 of 6 formation-blind facts with no
selection filter at all.

One more limit, and it is the one that decides how much weight §5.4 can carry.
The comparison is **eight probes against one**. The program has exactly one
enumeration question, so the entire enumeration side of the split — the top four
carrying zero, the rank-87 reading, the registered rule firing at rank 86 — is a
single instance. One instance cannot establish a query *type*.

So the claim is stated as what was measured: **on this corpus, one enumeration
probe behaves completely unlike the eight lookup probes, and the mechanisms this
program built for breadth all ran downstream of the ordering that probe
exposes.** It unifies the breadth failures. It does not unify the program, and
it does not yet describe a category of query. Whether "enumeration queries need
a different candidate ordering" is true in general is the open question §9
names, not a finding this paper reports.

### 5.6 The residual is a floor, not an interaction

After the pool is widened and the objective replaced, one known-optimum episode
remains unselected: turn 90, carrying four monetary items — the reason monetary
is the shipped configuration's weakest domain at 1 of 4.

DX-001 asked why, and ran a replay gate first that reproduced 146 of 146
committed payload hashes byte-for-byte before reporting anything. The gate
earned its place; §7.4 records what it caught.

No configuration in the registered space selects turn 90 — 0 of 146. That count
is weaker evidence than it looks, and we do not lean on it: the 146
configurations are a grid over three parameters, not 146 independent draws, so
sweeping the diversity weight eleven times is closer to one chance repeated than
to eleven chances. The arithmetic below is the actual argument.

The registered prediction was cluster collision: the episode shares a cluster
with a selected one, so the diversity term goes unpaid. That prediction is
**wrong**, and refuted twice over. The episode's cluster is never entered by any
selection, so the diversity term was payable in full at all 15 steps; a
counterfactual that pays it in full wins at no step.

What remains is arithmetic. To win at its best step the episode needed a query
relevance of **0.225**. It has **0.056**. Only 20 of the 119 episodes clear that
bar, so it would have to be a different episode by cosine, not a
better-weighted one. Across 132 walks of the parameter space its best rank
anywhere is 4, and never 1.

This is a floor. No reweighting of an objective built on that similarity reaches
it, which is why the program's registered no-change branch fired and 12 of 17
ships with the miss characterized rather than tuned away.

### 5.7 The three constraints, separated

| Constraint | Binds on | Bound, on this corpus |
|---|---|---|
| **Candidate pool** | domain coverage, and part of the fact gap | With the selector frozen, 34 → 119 candidates moves 5/17 across 2 domains to 12/17 across 4. On the 34-pool no configuration reaches four domains, because one domain is absent from it entirely |
| **Selection objective** | the remaining recoverable facts | Holding the deployed pool fixed, the best set-level configuration reaches 13/17 against the baseline's 6/17. Greedy runs at 0.954–0.9996 of a data-dependent bound, so the objective and not the search is the limit |
| **Similarity floor** | the irreducible residual | 0.056 measured against the 0.225 required, a shortfall of 0.169; only 20 of 119 episodes clear the bar; unreachable by any reweighting of this objective |

The three respond to different fixes, and the order is not arbitrary — it is
forced, and §5.2's first table is the evidence. A better objective over the
deployed pool cannot reach four domains, because that pool does not contain
them; and the specific objective this program ships, run on that pool, scores
5 of 17 against a 6 of 17 baseline. **The pool has to be widened first. Doing
the objective work alone makes the shipped configuration worse than what it
replaces.**

That is the operational content of the decomposition, and it is the sentence a
practitioner should take from §5.

One clarification the title invites. "Selection, not capacity" contrasts with
the *character budget*, which was never binding: the target cost 5,058 of 32,000
characters and deployed selection spent 31,946 to deliver a third of it. The
candidate pool is a capacity limit of a different kind — on how many episodes
the selector may consider — and §5.3 says it binds first. Both statements hold.
What the program spent four studies believing, and what is false, is that the
character budget was the constraint.

We have not found this decomposition reported elsewhere in this space. The
reason is likely mechanical rather than intellectual: computing it requires a
per-fact known optimum measured on the same store, which requires both an answer
key and exact-cost accounting. Evaluations that report end-to-end scores against
a benchmark do not usually carry either.

---

## 6. What survives

**Before anything in this section: none of it was run live.** The 12 of 17
result is offline availability. Its registered outcome is PROMOTION_ELIGIBLE,
which in this program means it may be promoted to a live study and has not been.
No inference run of the shipped configuration exists, so nothing here reports
what a model scored with it. The component-level guarantees below — budget
enforcement, restart, byte-identical reproduction — are tested; the retrieval
result they carry is not.

### 6.1 What was removed

Eleven mechanisms, each with the result that closed it. The count is a
coincidence: "eleven efforts" elsewhere in this paper means ten studies plus the
bakeoff, and these are not in one-to-one correspondence with those.

| Removed | Killed by |
|---|---|
| Distillation and "dreaming" | Five studies; query-blind selection cannot anticipate a later query |
| Promotion filters | The weighted route was arithmetically unreachable; every promotion came via bypass |
| Topic layer and consolidation | 52 topics for one 120-turn conversation; 12 domains collapsed to 2 at 1,000 turns |
| Associative graph from co-activation | No configuration cleared its advancement gate |
| Query-type routing | Oracle ceiling 6.09% against a 10% threshold |
| Approximate nearest-neighbour search | Recall degraded at synthetic scale |
| Query segmentation | Failed its locked 14/17 bar at matched budget |
| Attention-derived term selection | 0 of 714 rows reached the retrieval threshold |
| Entity extraction as primary index | Zero entities in the target span |
| Density and inverse document frequency for formation | Rank the six hardest facts 89th–316th, and worse |
| Rule detection and persistence | Failed at 1,000-turn scale |

### 6.2 What remains

An append-only verbatim store. A recency window. Cosine-threshold similarity
retrieval for targeted queries. A set-level coverage objective for selection.
Everything packed at exact serialized cost against one budget.

**There are no generative model calls anywhere in the memory path.** Nothing in
it asks a model to write text about the store. That is the property Study 005
established and the one all eleven removals in §6.1 preserve.

It is not the absence of model calls. `context()` embeds the query on every
call, and `append()` embeds every episode, so an embedding model must be
resident. The distinction matters for §6.3: what follows from the architecture
is that the memory path emits no generated text, and that its output is
reproducible **given a pinned embedder** — which is why the library asserts a
sentinel vector hash on every store open rather than assuming one (§7.4).

That is the whole architecture, and it is smaller than what this program started
building. It contains none of the eleven mechanisms in §6.1 — no entity
extraction, no graph, no router, no distillation step, no topic layer. We make
no claim about how it compares to Letta, Mem0, or Zep, whose systems were never
run here and whose designs are not measured by anything in this paper.

### 6.3 Why a practitioner should care

*This subsection is interpretation, not measurement. The properties are
measured; the causal story about why they hold is a reading of this program's
history.*

The surviving design is reproducible and provenance-preserving. Both properties
track a negative result rather than a design goal.

It is reproducible because distillation was removed, and distillation was the
component whose output could vary run to run: `context()` is a pure function of
store state, query, and budget, verified byte-identical across two processes.
That reproducibility is conditional on a pinned embedder, not unconditional
(§6.2). It preserves provenance because every delivered character is a stored
episode verbatim — there is no generated text about the store to be wrong, which
follows from removing the mechanisms that generated such text.

Stated plainly, and as a reading rather than a result: **the properties that
make this component deployable were bought by the failures, not by the design.**
A program that had succeeded at distillation would have shipped something harder
to test and harder to audit. That counterfactual is not measured; the absence of
generative calls, and what follows from it, is.

The extraction is certified rather than assumed. All 132 committed selection
records and all three committed rendered blocks reproduce their SHA-256
byte-for-byte through the library, and the full suite runs at 1,007 tests with
the study harness consuming it.

### 6.4 What it costs

These results come from the program's 1,000-turn endurance run, not from the
121-turn corpus §5 uses. Nothing here establishes a §5 result at 1,000 turns,
and nothing in §5 establishes these at 121.

Three things could grow as a conversation lengthens. Only one binds.

**Delivered context is bounded, because it is enforced.** Replaying the 1,000
committed episodes of that run through the library at a 32,000-character budget,
the delivered block breaches the budget on 0 of 1,000 turns and its 95th
percentile moves +18 characters across the final five 100-turn buckets. The same
block also **truncates on 895 of those 1,000 turns**, dropping up to 70 episodes
and wanting up to 65,864 characters. It is bounded because a ceiling binds during selection,
not because demand is small. Both readings belong together; the first alone
would be the kind of surrogate this program keeps catching.

**Disk is cheap.** 4,743 bytes per turn at the margin, 86% of it embeddings.
About 48 MB at 10,000 turns. Nothing there ends continuous operation.

**Latency binds.** 190 ms at 1,000 candidates, with clustering at 81% of it and
rising. The stated horizon is comfortable to a few thousand episodes and
unusable in an interactive loop somewhere before 10,000. Figure 6, right panel.

Those milliseconds are one machine's. The runtime throughout this program is
llama.cpp with a 27B generation model at UD-Q6_K_XL, one slot, fixed seed,
speculative decoding disabled, and Qwen3-Embedding-0.6B for embeddings over
SQLite with `sqlite-vec`. Selection timings exclude embedding entirely — query
and episode vectors are already resident — and are medians over repeated runs on
a single machine. Only the exponent and the clustering share plausibly transfer;
the absolute numbers do not.

The obvious fix — keep the pool small by dropping low-similarity episodes — is
the one operation this program measured to break retrieval (§5.3). So retention
is unbounded by policy, the trimming knob carries an `unsafe_` prefix and the
finding in its docstring, and the horizon is stated rather than engineered
around.

---

## 7. Self-audit and corrections

Everything in §5 rests on this program's own measurements, scored by its own
raters, against its own rubric. The reason to extend it any credit is that the
program audited itself and published what it found. All six items below were
caught by gates the program wrote, and all six are in the repository's `ERRATA`.

### 7.1 The scoring audit removed the program's only success

A blind re-scoring of 222 committed items across Studies 001–009 changed 19.
Study 002's iterative arm fell from 13.0 to 8.5, because a truncated reasoning
block had been credited as a complete response; its full-context arm fell from
8.0 to 5.5. Study 001 lost the program's **only VALIDATED verdict**. Figure 4.

The residual estimate is extrapolated, and this paper reports its precision as
well as its value. Three disagreements in a 26-item control sample is 11.54%,
which projected across 143 unreviewed items gives a point estimate of 16.5
remaining errors — the figure the repository reports informally as "about 20".
The 95% Clopper-Pearson interval on 3 of 26 runs from 2.4% to 30.2%, so the
same projection admits **anywhere from about 3 to about 43 remaining errors**.

The point estimate is not usefully precise, and a paper whose §7.6 is about an
interval being misread should not quietly present one number where the data
supports a range that wide.

### 7.2 Every study on record ran over its stated budget

Study 010 reported two retrieval blocks at 31,991 and 31,847 characters and
described them as near-saturation of a 32,000-character budget. DR-001 replayed
both blocks character-for-character. Their actual serialized lengths were 53,726
and 53,839 — **67.9% and 68.2% over budget**, not saturated.

The old accounting counted source text and omitted per-episode tags, metadata,
and separators. The scores did not change, because the model received the blocks
that were recorded, but they describe a budget-noncompliant arm, and the
compact-store scaling conclusion built on the undercharged figures was
withdrawn.

### 7.3 A validator invalidated a published curve

A probe-order validator checks mechanically that every rubric-required fact is
planted in a scripted turn strictly before the probe that asks for it. It found
degradation probes requesting facts that had not yet been planted, which
invalidated a published curve. The check now blocks artifact lock: any
unavailable fact stops the run before inference.

### 7.4 The same query text returns different vectors

DX-001's replay gate failed on its first attempt. The cause was not the query
text but the shape of the embedding call: E005 embedded nine probe queries in
one batch, and the replay embedded one query alone. The two vectors agree to a
cosine of **0.999837**, with a largest single-component difference of **0.217**,
and that difference flips **6 of 146** committed selection payloads.

A 0.999837 agreement reads as identical and is not. Reproducing a retrieval
result requires reproducing the call shape, not only the text. The shipped
library now embeds a fixed sentinel under the pinned call shape on every store
open and asserts its hash against the one recorded at first open; drift raises
rather than warns.

This is also evidence about something else, and §8.8 collects the consequence:
if a change this small moves 4% of committed payloads, the pipeline's
sensitivity to the embedder is not merely unmeasured.

It has one direct consequence for a reader reproducing this work. The 12-of-17
result was produced with the breadth query embedded in a nine-query batch; the
shipped `context()` embeds a single query alone. Those are the two call shapes
that differ. The primary configuration `A3_l0.1_r0.0_k16` is **not** among the
six payloads the difference flips, so the headline reproduces under either — but
that is a checked fact rather than a safe assumption, and six other
configurations do not have it.

### 7.5 A projection extended 84× past its data

The pre-registration for the deployment work quoted a measured cost of about
40 microseconds per candidate at an empirical exponent of 0.96, and projected
40 ms at 1,000 candidates and 400 ms at 10,000.

The source sweep covered **20 to 119 candidates**. Inside that range every
figure it reported is correct. The projection extended it 84× beyond its last
measured point, and per-candidate cost stops being flat shortly after the data
ends: measured at 1,000 candidates, the cost is **190 ms, about five times the
projection**, at an exponent of 1.25. A published README figure separately
described the sweep as covering "20–3,000 candidates"; the 3,000 was a character
count from an unrelated table in the same report.

The correction is not to the original measurement, which stands. It is to the
range attributed to it and the extrapolation built on top. Figure 6, right
panel.

### 7.6 A diagnostic written to catch surrogate failures nearly committed one

This is the most instructive of the six.

The recurring failure class this program tracks is a check that can pass while
the property it certifies is false. DX-002 was written to determine whether a
1,000-turn run's context was still growing. Its decision rule was a three-clause
conjunction; its implementation checked one clause — whether the terminal slope's
95% confidence interval contained zero.

It did, for every component of the prompt, in both arms. The diagnostic returned
"bounded".

The third clause was *no unbudgeted component climbing*, and one was. A block
whose 95th percentile rose from 25,253 to **48,491 characters** across the final
five buckets, and which was still setting records in the last bucket of the run,
was reported as flat. The interval was wide because the series are sawtooths with
autocorrelated residuals; it was measuring statistical power, and it was read as
evidence of boundedness. The smallest slope the data could distinguish from zero
was about 17 characters per turn — 17,203 characters of drift over 1,000 turns
that the fit would not have caught.

The rule was replaced with two readings that assume nothing about noise: whether
the final bucket still holds the maximum, and how the terminal window compares
against the one before it. The verdict flipped, and the near miss was written
into the decision record rather than quietly repaired.

The finding that followed is in Figure 6: the leak belonged to the study runner,
which carried the recency window and the retrieval tier on separate budgets, not
to the extracted component, which routes both through one.

### 7.7 What the gates missed

Every error above was caught by a gate this program wrote, which invites the
obvious question, and it deserves the honest answer rather than the flattering
one.

Somewhere between about 3 and about 43 scoring errors are estimated to remain
unreviewed in the corpus, with a point estimate of 16.5 (§7.1). Runtime
independence was never measured: every number in this paper comes from one model
at one quantization on one machine, and §7.4 gives positive reason to expect
that a different embedder would move the §5 results. Study 010 was outside the scoring audit
entirely, so its exploratory scores are not comparable to the corrected series.
The mechanism seal for one tier was computed over mixed line-ending
representations and referenced a database file that was never committed. And the
program refuted one of its own literature claims: an internal note described
maximal marginal relevance as lacking submodularity, which is wrong — it is
non-monotone submodular, and the conclusion drawn from it happened to survive
for a different reason than the one given.

---

## 8. Limitations

This section is load-bearing. Each item names what would settle it.

**8.1 One corpus, one seed, no variance.** Every comparison in this program is a
single run at a fixed seed. There is no error bar anywhere, and no significance
test would be meaningful. Where this paper reports a difference — 6 of 17 against
12 of 17, 5 of 17 against 12 of 17 — the difference is one measurement against
another, not an estimate with an interval. *Settled by:* repeated runs at
multiple seeds, which the program never did.

**8.2 No external calibration.** Study 003 retired external baselines and nothing
restored them. LoCoMo and LongMemEval were adopted in principle and never run.
Nothing here establishes where this program sits relative to published systems.
*Settled by:* running one of them.

**8.3 Breadth rests on a single probe.** The program has exactly one enumeration
question. Every breadth number in this paper — 6 of 17, 12 of 17, 14 of 17, the
rank-87 reading, the whole of §5.4 — comes from it. A single probe cannot
support a claim about enumeration in general, and this paper does not make one.
*Settled by:* more enumeration probes across more domains.

**8.4 AI raters, AI adjudicators.** Scoring used three blind passes with
registered adjudication triggers, but the adjudicators were subagents, not
humans. The control sample disagreed at 11.54%. *Settled by:* human adjudication
of the same items.

**8.5 Planted facts may not represent natural conversation, and there is a
specific reason to suspect they do not.** The corpus is constructed: facts are
planted at known turns in a scripted conversation. The program's own description
of its hardest facts is that they are rare technical phrases whose component
words are common — *photophores*, *mantle margin*, *ultramarine glaze*. That is
a lexical property, and it predicts the observed effect directly: an embedding
will place such a span far from a query phrased in ordinary words. If that is
the mechanism, §5.4 is a finding about this corpus's planted vocabulary and
generalizes only to corpora whose target facts are similarly distinctive.

*Settled by:* correlating each fact-bearing episode's cosine rank against the
lexical rarity of its key phrases, on the committed store. This is cheaper than
it sounds — the ranks and the phrases are both already committed, and the
program has rarity scores from the breadth regression audit — and it
discriminates between the two explanations without collecting a new corpus. If
rank tracks rarity, the inversion is vocabulary. If it does not, the corpus
objection weakens considerably. This program did not run it, and it is the
single measurement that would most change how much weight §5.4 deserves.

**8.6 The known optimum is mostly the conversation's own earlier answers.** Four
of its five episodes are prior probe exchanges; only turn 90 is an original
plant source (§5.1). So "the target was reachable in 5,058 characters" partly
means the facts had already been restated compactly in earlier answers, and
retrieving those restatements is cheap. Achievability holds under the registered
eligibility rule and not under a stricter plant-source-only rule.

There is a further hazard the program recorded and this paper repeats, and it is
the sharpest limit on how much §5's counts mean. A selector that prefers prior
answers propagates prior errors, **and this probe's earlier answers were largely
wrong.** Availability is scored on an item's presence in the delivered text, so
an earlier answer that names the right entity inside an otherwise incorrect
response makes that item "available".

A part of the 15-of-17 known optimum, and of any configuration that scores well
by recovering those four episodes, therefore consists of delivering the
conversation's own earlier mistakes with the correct nouns in them. The
decomposition in §5 survives this — it is about which episodes get selected, not
about whether they are true — but "makes 15 of 17 available" and "would help the
model answer correctly" are further apart than an availability count suggests,
and nothing in this program measured the distance.

**8.7 Amendments exist after results.** Twelve in the bakeoff alone. The program
does not claim these were unnecessary; it records, per amendment, whether it
preceded the result it affects, and applies a legitimacy test that permits
correcting measurement units and repairing protocol contradictions while
forbidding making a criterion easier once results are known. The record is
published so a reader can disagree with individual calls.

**8.8 One runtime, and positive evidence of fragility.** One model, one
quantization, one machine, one embedder. The absolute latencies in §6.4 are not
portable; only the exponent and the clustering share plausibly are.

Whether the §5 results survive a *different* embedder is unmeasured. But this is
not a blank absence of evidence, and it would be convenient to describe it as
one. §7.4 shows that the *same* embedder, given the same text under a different
call shape, returns a vector agreeing to cosine 0.999837 that nonetheless flips
6 of 146 committed selection payloads. A perturbation far smaller than a model
change already moves 4% of the results. The reasonable prior is therefore that
§5's specific numbers are embedder-dependent, and the burden sits with anyone
who wants to assume otherwise. *Settled by:* rerunning the E005 sweep under a
second embedder.

**8.9 The horizon is 1,000 turns.** Every boundedness claim in §6.4 is a
statement about the tested horizon. A plateau at 1,000 turns says nothing about
10,000.

**8.10 Figure 1 is drawn at the resolution the artifacts support.** Per-episode
cosine ranks were committed for 16 of the 119 candidates. The remaining ranks
were never committed, and recomputing them requires the carried embedder under
the batched call shape of §7.4, which is not in the repository. The structural
readings the figure annotates — the top four carrying zero facts, first hit at
rank 5, last needed item at rank 87 — are committed values, but the full curve
is not drawn because it cannot be drawn honestly.

---

## 9. Conclusion

Eleven pre-registered efforts on one program produced one architecture worth
keeping and a great deal of evidence about why the rest did not work.

For a practitioner, the useful part is the subtraction. Eleven mechanisms were
built and none of them cleared its own gate; what is left is an append-only
verbatim store, a recency window, similarity retrieval, and a set-level coverage
objective, with no generative model calls in the memory path. That component is
reproducible given a pinned embedder and auditable line by line, and §6.3 argues
both properties followed from the removals rather than from foresight. If a memory component in your
system makes model calls, this program's experience is that the calls bought
less than they cost — on one corpus, with no live comparison run.

For a researcher, the useful part is the decomposition, and the order inside it.
Retrieval failure here was not one thing. The candidate pool decided what could
be seen, the objective decided what was worth taking, and a similarity floor
decided what was unreachable at any weighting. The order is forced rather than
tidy: on the deployed pool, the objective this program ships scores 5 of 17
against the 6 of 17 baseline it replaces, and only becomes an improvement once
the pool is widened. Separating the three required a per-fact known optimum on
the same store — a measurement that costs an answer key and exact cost
accounting, and buys a sharper question than an end-to-end score.

The observation most worth testing elsewhere is the narrow one, and it is a
single instance. On this corpus, for the one enumeration probe this program has,
the four highest-cosine episodes carried none of the target facts and the last
needed item sat at rank 87 of 119 — while the same ordering placed every needed
item inside rank 2 on all eight lookup probes. One probe cannot establish that
enumeration queries are a category with different retrieval needs. It is enough
to make the question worth asking on a corpus this program did not build, and
§8.5 names the cheaper measurement that would first tell us whether the effect
is about retrieval or about the vocabulary these facts were planted in.

If it turns out to be vocabulary, the finding is about this corpus. Saying so
was the point of §1.1.

The program's own summary of eleven efforts is that the model used what it
received. At the hardest probe it used all ten available facts and invented
none. The failures were delivery failures, and delivery turned out to be a
selection problem sitting on top of a candidate set that had already been
narrowed by the wrong rule.

---

## Figures

Six. All generated by `scripts/generate_paper_001_figures.py` from committed
artifacts. Each caption carries the first 16 hex digits of the SHA-256 of every
artifact it draws from, over git blob content so the values are stable across
platforms; `paper/figures/figure_manifest.json` records the full set alongside
the commit they were read at. Vector SVG alongside PNG.

**Figure 1 — Cosine rank against fact content.**
`paper/figures/f1_cosine_rank_vs_fact_content.svg`
*On this corpus, the enumeration probe's target facts sit outside the top of the
cosine ranking, and the deployed pool cut removes an entire domain.* Horizontal
axis: cosine rank against the turn-120 breadth query over the 119 eligible
episodes. Vertical axis: target facts carried. The four highest-ranked episodes
carry zero; the first fact-bearing episode is at rank 5 and the last
still-needed item does not appear until rank 87. The five episodes of the
15-fact known optimum are marked at ranks 14, 20, 22, 86 and 112. Both art
contributors lie at ranks 50 and 86, so the deployed 34-episode pool contains no
art episode and cannot reach four domains at any setting; the 100-episode pool
excludes the rank-112 episode carrying four monetary items. Only the 16 episodes
whose ranks are committed are plotted — the 15 selected plus the rank-112 miss;
ranks for the other 103 candidates were never committed and recomputing them
needs the carried embedder under the batched call of §7.4. The rank-4, rank-5
and rank-87 readings are committed structural values drawn as annotations, not
inferred from the plotted points. Sources: `selection_ranks.csv` `6fdff4022997ab83`,
`cost_comparison.csv` `1ca40da99315c719`, `generality_batched.json`
`7e1fa13ef71a8077`; rank 20 supersedes the published 21 per `ERRATA.md`,
2026-08-01.

**Figure 2 — The budget efficiency gap.**
`paper/figures/f2_budget_efficiency_gap.svg`
*The constraint is not capacity: the tallest result is also the narrowest.* Each
horizontal stem runs from zero to the characters spent, at a height equal to the
facts delivered, over the same store at the same enforced 32,000-character
budget. The deployed baseline delivers 6 of 17 for 31,946 characters; the
shipped set-level configuration 12 of 17 for 31,569; the exact known optimum 14
of 17 for 5,058, leaving 26,942 characters unused; its greedy variant 15 of 17
for 5,455. The shipped configuration spends 26,114 more characters than the
greedy optimum and delivers three fewer facts. Both optima are computed with the
answer key and are bounds, not methods. Sources: `a0_baseline.json`
`7645e4746715a965`, `e005_results.json` `07b714389697c6e5`,
`achievability.json` `770792d09e07978d`.

**Figure 3 — Pool ablation.**
`paper/figures/f3_pool_ablation.svg`
*Widening the candidate pool from 34 to 119 episodes, with the selector frozen,
moves the same configuration from 5 of 17 across 2 domains to 12 of 17 across
4.* Facts, domains, and known-optimum overlap at three pool sizes, everything
except pool membership held fixed. Dropping only the 19 lowest-cosine episodes
to form the 100-pool costs three facts, the whole art domain, and all optimum
overlap, though four of the five optimum episodes survive the cut — the selector
clusters over the pool, so tail removal reshuffles the objective rather than
removing options. The orange rule marks the best of 146 configurations on each
pool: 13 of 17 on all three, which is why the pool's binding effect must be read
in domain coverage. Sources: `configuration_sweep.csv` `1ad625d10fb988f9`,
`pool_secondaries.csv` `5987d05846c64f97`; narrative in `DR_002_report.md`
`df1a5e93c9647a65` §1.

**Figure 4 — The corrected arc.**
`paper/figures/f4_corrected_arc.svg`
*19 of 222 re-scored items changed, and the program's only VALIDATED verdict
disappeared.* Paired points, original against corrected, for Studies 002C
through 009L. The largest fall is Study 002's iterative arm at −4.5, where a
truncated reasoning block had been credited as complete. These points are **not
a controlled series** — runtime and response budgets changed across it — and the
only clean architectural comparison in the program is Study 009's same-seed
pair, 9.0 without the memory tier against 12.0 with it. Study 010 was outside the
audit and Study 001 scored on a different rubric; neither is plotted. Source:
`arm_totals.json` `443282df34a3a4ba`.

**Figure 5 — Selector comparison.**
`paper/figures/f5_selector_comparison.svg`
*The selector with the highest raw fact count delivered nothing from one domain
and passed no gate.* Best configuration per arm on the 119-candidate pool at the
enforced budget, with the monetary domain broken out. Facility location leads on
count at 13 of 17 and delivers monetary 0 of 4 at every setting; the shipped
relevance-plus-diversity configuration reaches 12 of 17 across all four domains.
All 146 configurations beat the deployed 6 of 17, and 137 preserve 16 of 16
targeted items — targeted recall does not separate the arms, which is itself the
finding. Sources: `configuration_sweep.csv` `1ad625d10fb988f9`,
`a0_baseline.json` `7645e4746715a965`, `e005_results.json` `07b714389697c6e5`,
`achievability.json` `770792d09e07978d`.

**Figure 6 — Growth and cost.**
`paper/figures/f6_growth_and_cost.svg`
*Growth belonged to the harness; cost was five times the projection.* Left: the
95th percentile of the retrieved block per 100-turn bucket over the final 500
turns. In the study runner the block rises 23,238 characters in one arm and
28,701 in the other and is still setting records in the last bucket; replayed
through the extracted library at the same budget it moves +18 characters and
breaches the budget on 0 of 1,000 turns — while truncating on 895 of them, so it
is bounded because enforced, not because demand is small. Right: measured median
selection latency against candidate count with the withdrawn linear projection
overlaid; 190 ms measured at 1,000 candidates against about 40 ms projected,
exponent 1.25 over 50–1,000 where the earlier sweep found 0.96 over 20–119, and
clustering's share rising from 37% to 81%. Values above 1,000 candidates are
projections, drawn dashed. Sources: `dx002_results.json` `f8ab79ab041cb3e3`,
`ge0_growth_gate.json` `350fe20bbc3beed9`, `latency_curve.csv`
`0d2b8075ff5a971f`, `growth_measurement.json` `20d65a018e28b03f`.

---

## Appendices

- **A. Claim-to-artifact table** — `paper/CLAIM_TO_ARTIFACT.md`. Every claim with
  its committed artifact and hash; two claims cut or demoted for lack of one.
- **B. Study table** — §4 above, with full reports under
  `experiments/study_NNN/`.
- **C. Amendment record** — per-study `amendments/` directories, each with the
  before/after-result status.
- **D. Corrections index** — `ERRATA.md`, cross-referenced from §7.
- **E. Reproduction** — `paper/REPRODUCTION.md` and `paper/reproduce_headline.py`.
  Rebuilds the 5,058-character exact optimum from the committed turn log through
  the installed library and checks its length and SHA-256 against AR-001's
  committed values. Verified in a clean virtual environment containing only
  `episodic`. The selection results cannot be reproduced this way, because the
  store's vectors were never committed; the appendix says so.
- **F. Spec reconciliation** — `paper/notes/EVIDENCE_INDEX.md` §1, recording six
  places where the authoring specification and the committed artifacts disagreed
  and the artifact won.
