# TC Arc — What the tiered architecture earns, and what it costs

**Document type:** Prospective arc roadmap
**Status:** `DESIGN ONLY — NOT PRE-REGISTERED — NO IMPLEMENTATION AUTHORIZED`,
except TC-001, registered separately on August 22, 2026 in
`TC_001_PRE_REGISTRATION.md`. That document, not this one, governs TC-001;
where the two disagree the registration wins and the disagreement is a defect
in this file. TC-002 through TC-006 remain design only.
**Date:** August 21, 2026
**Predecessors:** HH-002 (`experiments/comparisons/hh_002/`), EC-002 and IC-001
(`PAPER_002.md` §9), DR-002 (§8.2), NF-005 (§7.2), §10's cost envelope
**Branch:** `study/tc-arc-tier-cost`, rebased onto `main` after PR #63 merged.

---

## 0. Why this arc exists

HH-002 scored **79.09%** on the harness that produced arXiv:2504.19413's Table 2,
above every row of it. The arm that did it was **`CdwArm`: rank adjacent-turn
pairs by cosine, pack a 16,000-character budget, stop.** No recency tier, no
K-threshold, no candidate pool filter, no coverage selector, no clustering.

The deployed library is none of those things. It is four tiers filled in a fixed
order, and every measured pathology in this programme lives in that machinery:

| Finding | Where | What it costs |
|---|---|---|
| Recency-first fill starves everything after it | §9.1, EC-002 | **32.3 points of evidence availability**; 152 gains, 0 losses on reversal (live test rejected it, see TC-002) |
| The similarity path delivered **zero** episodes at 8 of 8 probes | §9.2, IC-001 | Every internal number published for that configuration |
| Pool pruning removes a whole domain | §8.2, DR-002 | 19 of 119 episodes dropped ⇒ art domain gone, **all** optimum overlap gone |
| Clustering is 81% of latency and its share is **rising** from 37% | §10 | The horizon: unusable somewhere before 10,000 episodes |
| The deployed LTM tier is inert | Study 011 | D ≡ A on all 13 questions |

**The arc's question is therefore not "how do we optimize the tiers."** It is:
*does the tiered stack beat the flat arm at all, and if it does, which of its
parts is carrying that?*

That ordering matters. Optimizing a component before establishing it earns its
place is how a programme spends a year on machinery it should have deleted.

## 0.1 The one thing this arc cannot produce

**No study here can be `CONFIRMATORY`.** LongMemEval is exhausted; LoCoMo is now
spent three times over (NF-004, HH-001, HH-002). No sealed external corpus
remains to this programme.

The consequence is not fatal, because **every study below is zero-inference and
deterministic.** That puts `REGISTERED-OFFLINE` within reach for all five — bars
locked first, replayable under a pinned embedder, capped as characterization.
A study that needed a reader would be capped lower, at `REGISTERED-LIVE`, and
would also inherit the 3.0-point instrument band. None of them need one.

Acquiring a new sealed corpus would raise the ceiling. That is a separate
decision and is **not** a dependency of any study here.

---

## 1. The anti-stall design

This programme has stalled an arc once, and the post-mortem is in the
repository: `DMR_ARC_BLOCKING_REVIEW.md`. Its finding, in its own words:

> **I carried DMR-001's blanket blocking claim forward after the evidence under
> it had changed.** … This is the second time in this arc I have over-applied a
> blocking claim.

The mechanism of that failure was a **blanket dependency rule repeated in every
spec** — *"if DMR-001 stops, DMR-002 through DMR-006 are blocked"* — which was
still being applied after DMR-001B and DMR-001C had supplied exactly what it
demanded. One stage was declared blocked despite its own header saying it was
independent.

Four rules follow, and they are structural rather than advisory.

**Rule 1 — No arc-level dependency clause exists.** There is no sentence
anywhere in this arc of the form "if TC-00n stops, the rest are blocked." Each
study carries its own dependency line and nothing inherits.

**Rule 2 — A dependency names evidence, never a stage.** "Requires TC-001 to
pass" is forbidden. "Requires a measured cluster-assignment baseline on a pool
of ≥100 candidates" is the permitted form, because it can be satisfied from any
source and can be checked without re-reading another study's verdict.

**Rule 3 — Every dependency carries an expiry condition.** The line states what
evidence would release it. A dependency with no stated release is a defect and
the study may not be registered with one.

**Rule 4 — Dependency re-read is scheduled, not remembered.** When any study
reports, every other study's dependency line is re-read against the new
evidence *before* the next study is registered, and the re-read is logged in
`TC_ARC_DEPENDENCY_LOG.md` with an explicit verdict per study. DMR's blocking
review was a correction written after the damage; this is the same act, moved
in front of it and made mandatory.

**A consequence worth stating plainly:** the five studies below are designed to
be runnable **in any order, including all at once.** If that is true, no
ordering can stall. Section 8 tests that claim rather than asserting it.

## 1.1 Standing arms

Added August 22, 2026, after TC-001B, on the author's instruction that the dual
arm travel with this arc.

TC-001 compared two arms and found the flat one ahead by 435 questions. TC-001B
added two and found that the 435 decomposed into **158** questions of
recency-tier cost and **276** questions of K-tier ordering cost. Neither number
was visible from TC-001's two arms, and both were measurable only because the
later study kept the earlier one's reference arm alongside its own.

**Every study from TC-002 onward carries three arms regardless of its own
question:**

| Arm | What it is | First measured |
|---|---|---|
| `A_FLAT` | rank by cosine, pack to budget | TC-001 |
| `A_DUAL` | `build_context` with `recency_window_n=0` | TC-001B |
| `A_DUAL_RANKED` | `A_DUAL` with the K tier offered best-first | TC-001B |

A study adds its own arms on top; it does not drop these, and it does not
redefine them. `src/analysis/tc_standing_arms.py` is the registry and
`tests/test_dual_arm_standing.py` holds each arm's behavioural identity, so an
inherited arm that drifts fails a test rather than quietly changing what a
prior study's number meant.

**The shipped configuration is deliberately not standing.** It is the thing
under test when a study tests it, and carrying it unconditionally would make
every stage of this arc read as a referendum on it.

**This costs multiplicity, and that is registered rather than absorbed.** Two
extra arms mean extra contrasts, and every contrast a study registers enters its
Bonferroni family. A standing arm that is not worth a divisor is not worth
carrying — so a study may report a standing arm descriptively, without a
contrast, if its question does not need one.

---

---

## 2. TC-001 — Does the tiered stack beat the flat arm?

**The root question, and it is not a tuning question.**

Two configurations over one store, one query set, one budget:

- **Flat**: `CdwArm`'s path — rank candidates by cosine, pack to budget.
- **Tiered**: the library's `build_context` — recency, then K-threshold, then
  coverage over the pool, packed N-first.

**Endpoint.** Evidence availability: whether text carrying an answer is present
in the delivered block. Zero inference, no judge, no reader. This is NF-004's
endpoint and the arc uses it deliberately — it is deterministic, it is the one
this programme has the longest baseline for, and it does not spend a corpus.

**Secondary.** Delivered composition by tier, and delivered character count.
IC-001's failure was visible in composition and invisible in the aggregate;
§9.1 records that "the medians concealed all of it."

**Bars, locked before the run.** A directional bar on paired availability
(one-sided exact binomial), plus a pre-declared **null band**: a difference
inside the band is reported as *no difference established*, not as a win for
the simpler arm. Simplicity is not entitled to a free pass either.

**Dependency line.** Requires a store with per-item evidence labels and both
paths runnable over identical candidate identities. Satisfied today by the
internal 121-turn store and by LoCoMo development.
**Expiry:** none — the dependency is already satisfied.

**What this blocks:** nothing.
**What it does not block:** TC-002 through TC-005, all of which measure
properties of the tiered path that remain worth knowing whichever way this
lands. If the flat arm wins, the tiered path's defects become the explanation
rather than the target, and the other four studies supply that explanation.

## 3. TC-002 — Does the fill-order result hold off its original corpus?

**Read §9.3 before this section.** EC-002 reversed the packing order on 500
external stores and moved any-evidence-session recall from **109 to 261 of
470**, with **152 gains and zero losses**. That is an *availability* result and
it is confirmed offline. The library still packs N-first.

**The fix was then tested live and rejected.** A registered comparison scored
the similarity-first arm at **7.0 against the deployed arm's 8.0**, the
registration's bar fired, and the correction was not adopted. The −1.0 margin
sits **inside** the 3.0-point instrument band, so it is *not demonstrated in
either direction* — and this programme's registration forbids citing the band
to revive the rejected correction.

So the honest statement of the situation is: **a large, confirmed gain in
whether the evidence arrives, and no demonstrated gain in whether the reader
answers.** Shipping the reversal is not free money and this arc does not treat
it as such.

**The question here is therefore narrow and offline:** does the *availability*
gain hold off its original corpus? That bounds EC-002 without touching the
adoption question, which TC-006 owns.

**Endpoint.** Same availability endpoint, on a store that is not the 500-store
calibration set.

**Bars.** Direction and a minimum effect size fixed first. A null result here
does not retract EC-002; it bounds it to its corpus, which is a result.
**A positive result does not authorize shipping**, because §9.3 already showed
that availability and adoption are different questions.

**Dependency line.** Requires a second store with evidence labels where both
orders can be replayed over frozen candidate identities.
**Expiry:** satisfied by the internal store or LoCoMo development today.

**What this blocks:** nothing. It does **not** gate shipping the order change,
because §9.3's live rejection is the binding evidence there and this study does
not address it. The adoption question is TC-006's.
**What it does not block:** TC-003, which asks a different question — whether
*any* fixed order is the right shape.

## 4. TC-003 — Reserved floors against sequential fill

**Reversing the order does not fix the defect; it moves it.** Greedy sequential
fill lets whichever tier goes first take everything, and §9.1's median
composition shows exactly that: 16 recency episodes, **0** non-recency
similarity episodes, 1 coverage episode.

The proposal: give each tier a guaranteed minimum share of the budget and let
them compete only for the remainder, so allocation stops depending on order.

**Endpoint.** Availability, plus delivered composition, plus the property that
motivates it: **order-invariance.** A floors-based allocator should produce the
same delivered set under permuted tier order. That is a deterministic property
and is checked directly, not inferred.

**Bars.** Availability against both fixed orders, and an exact order-invariance
check that either passes or does not.

**Dependency line.** Requires the tier boundaries to be identifiable in the
delivered block. Satisfied by `ContextReport`.
**Expiry:** none.

**What this blocks:** nothing.
**What it does not block:** anything. If TC-001 finds the flat arm wins, this
study still answers whether allocation was the reason — which is the difference
between deleting the tiers and fixing them.

## 5. TC-004 — An operational test for "small enough"

§7 states this programme's granularity rule conditionally, and admits the gap:

> rank at a unit small enough that its embedding is dominated by the material
> answering the query … **and that first clause has no operational test here.**

NF-005 got as far as a correlate: evidence turns have a median of **298
characters against 2,550 for their parent episodes**, and parent length
correlates with worse normalized own-cosine rank at **Spearman ρ = 0.484**.
HH-002 added a matched-budget replication from a different direction: four
500-token chunks beat two 1000-token chunks by **14.68 points** at 2,030 tokens
against 2,012.

**The question:** is there a computable, model-free predictor — over a candidate
and a query, before any ranking — of whether that candidate should be split?

**Endpoint.** Predictive: does the proposed statistic identify the units whose
splitting improves availability, at a rate better than length alone? Length is
the baseline to beat, because ρ = 0.484 is already available for free.

**Bars.** A minimum improvement over the length baseline, fixed first, and a
pre-declared statement that beating length is the bar — not beating chance.

**Dependency line.** Requires a corpus with span-level evidence labels so that
"the material answering the query" is identifiable within a unit. LongMemEval's
turn labels and LoCoMo's evidence dialogue ids both qualify.
**Expiry:** none.

**What this blocks:** nothing.
**What it does not block:** anything. This is the arc's one genuinely open
research question and it stands whether or not the tiers survive TC-001 —
`CdwArm` ranks units too.

## 6. TC-005 — Clustering cost at a pool size that must not shrink

**The latency problem and the breadth finding are the same problem.** This is
the arc's central technical claim and it is assembled from two existing results
that have never been read together:

- §10: clustering is **81% of selection latency and rising from 37%**, at a
  measured exponent of **1.25** over 50 to 1,000 candidates.
- §8.2: clustering runs over the **pool**, and the pool must not be pruned —
  dropping 19 of 119 episodes cost an entire domain *and* all overlap with the
  known optimum, **even though four of the five optimum episodes survived the
  cut**, because "the selector clusters over its pool, so removing the tail
  reshuffles the objective rather than simply removing options."

So the pool cannot shrink, and the pool is what drives the cost. **The only
safe lever is the clustering algorithm itself.**

This rules out the obvious design. A hierarchical index that finds the *k* most
relevant folders and searches only inside them is pool pruning wearing a new
name, and §8.2 is the measured verdict on it. It also rules out approximate
nearest-neighbour retrieval used to *build* the pool, unless recall against the
exact pool is demonstrated to be 1.0 — an ANN index with recall below 1.0 is
stochastic pruning, which is strictly worse than the deterministic kind because
it cannot be audited.

**The question:** can cluster assignments be produced more cheaply at fixed pool
size, either identically or within a bounded and measured distance?

**Endpoint.** Wall-clock at matched pool sizes, and **exact-match rate of
cluster assignments against the current implementation.** Any candidate
acceleration that changes assignments must show its availability effect
separately; speed is not permitted to be traded against delivery silently.

**Bars.** A latency reduction target at 1,000 candidates, and an assignment
agreement floor. Both fixed first.

**Dependency line.** Requires a pool-size-versus-latency series over the current
implementation. §10's 50-to-1,000 series supplies it.
**Expiry:** none.

**What this blocks:** nothing.
**What it does not block:** anything. Latency is worth reducing whichever
architecture survives, and it is the constraint that decides whether the
document-corpus benchmarks in §8 below are reachable at all.

---

## 7. TC-006 - Why a confirmed delivery gain did not become an answer gain

**This is the arc's one study that needs a reader, and the only one whose
standing is capped at `REGISTERED-LIVE`.** It is listed last because of that
cost, not because anything waits on it.

Sections 9.1 and 9.3 of the paper together state a gap this programme has never
closed. Reversing the packing order moved evidence availability by **32.3 points
with zero losses**. The live comparison that followed scored the reversed arm
**7.0 against 8.0** and the registration's bar fired. Evidence arriving and a
reader using it are not the same event, and this arc's other five studies all
measure the first one.

Section 14 already names this as the next decision-relevant experiment and
records that its design is *prepared and unregistered*: a reader study over
**two already-frozen contexts**, scored as a **17-bit fact-use vector** rather
than on the 13-point rubric whose 3.0-point band cannot resolve a two-item
contrast.

**Why the instrument has to change.** The observed margin was -1.0 and the band
is 3.0. Running the same rubric again cannot resolve it in either direction, no
matter how many replicates are added - the band is a property of the instrument,
not of the sample size. A study that reuses that rubric here is unreachable by
construction, which is exactly the `PF4` defect DMR-001 committed.

**Endpoint.** Fact use over frozen contexts: of the facts present in a delivered
block, how many appear correctly in the answer. Per-fact, paired, deterministic
to score once generated.

**Bars.** Fixed first, on the fact-use vector, with reachability demonstrated
against the new instrument's own measured spread - not against the 13-point
band, which does not apply to it.

**Dependency line.** Requires two frozen delivered contexts over the same query
set that differ in evidence availability by a known margin, and an instrument
whose resolution is finer than the margin being tested.
**Expiry:** the first clause is satisfied by EC-002's replay artifacts today.
The second is **not yet satisfied** - the fact-use instrument's spread has never
been measured - and that measurement is the study's own first task, not a
precondition supplied by another study.

**What this blocks:** any claim that fixing delivery improves answers, which is
the claim the tiered architecture ultimately rests on.
**What it does not block:** TC-001 through TC-005, none of which make that
claim.

---

## 8. The dependency matrix, stated once so it can be checked

| Study | Needs | From | Blocks | Blocked by |
|---|---|---|---|---|
| TC-001 | Evidence-labelled store, both paths over identical candidates | Internal 121-turn store; LoCoMo dev | — | nothing |
| TC-002 | A second evidence-labelled store | Internal store; LoCoMo dev | Shipping the order change | nothing |
| TC-003 | Tier boundaries visible in the delivered block | `ContextReport` | — | nothing |
| TC-004 | Span-level evidence labels | LongMemEval turns; LoCoMo evidence ids | — | nothing |
| TC-005 | Pool-size-versus-latency series | Paper §10 | — | nothing |
| TC-006 | Two frozen contexts of known margin; an instrument finer than it | EC-002 replay artifacts; instrument spread **measured as its own first task** | Any delivery-implies-answer claim | nothing |

**Every cell in the "blocked by" column reads `nothing`, and that is the design,
not a coincidence.** Each study was scoped until it depended on an artifact
rather than on a verdict. If a study cannot be scoped that way it does not enter
the arc.

The one real ordering preference is a *reading* preference, not a dependency:
TC-001 first makes the other four easier to interpret. It does not make them
runnable, and none of them waits for it.

---

## 9. What this arc does not cover

- **Document-corpus generalization.** LegalBench-RAG and EnterpriseRAG-Bench
  are a separate question and a separate arc. TC-005's outcome decides whether
  they are reachable; it is not a dependency in the other direction.
- **The reader.** Nothing here measures answer quality. §5's endpoint costs a
  corpus and this arc is deliberately built not to spend one.
- **The recency window's real behaviour.** §3.4 records that no live study ran
  a true last-*N* window; the studies ran a rotation and, before that, a locked
  prefix. TC-003 measures allocation among tiers as they are, not as they are
  documented. Fixing the window is its own work.

## 10. Open decisions, in the order they block registration

1. **Corpus per study.** The internal 121-turn store is exhausted and
   `DESCRIPTIVE` by default; LoCoMo development is spent. Both are acceptable
   for `REGISTERED-OFFLINE` given zero inference, but the choice must be made
   and written down per study before bars are set.
2. **Whether to acquire a new sealed corpus.** It is the only route to
   `CONFIRMATORY` for anything in §0.1. Cost and choice unknown.
3. **TC-001's null band.** Must be derived from a measured quantity, not chosen
   round. `PF4` requires every bar to be shown reachable *and* failable before
   the run — the DMR-001 lesson, where a bar was locked that was unreachable by
   construction.
4. **Whether TC-002's result, if positive, ships immediately** or waits for
   TC-003. Deciding now avoids a live argument later with a number on the table.
