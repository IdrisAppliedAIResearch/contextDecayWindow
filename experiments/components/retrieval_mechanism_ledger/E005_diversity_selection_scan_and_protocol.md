# E005 — Diversity-Aware Selection: Literature Scan and Implementation Protocol

**Type:** Literature scan (Part B) + ledger entry and implementation protocol (Part A). One document, for agent handoff.
**Repository:** `contextDecayWindow` · `experiments/components/retrieval_mechanism_ledger/`
**Addresses:** F1 (breadth / enumeration)
**Status:** PROPOSED — scan complete, protocol requires design-anchor commit before implementation
**Companions:** `RETRIEVAL_MECHANISM_LEDGER.md` · `AR_001_report.md` · `E002_POSTHOC_INTERPRETATION.md` · `LITERATURE_LANDSCAPE.md`

---

# PART B — LITERATURE SCAN

Scan performed July 30, 2026. This closes the "diversity-aware / coverage selection"
item that has blocked ledger promotion since revision 2. Sources were read, not
recalled. Every claim below is attributed.

## B.1 Why this scan was owed

AR-001 established that **14/17 Q11 facts fit in 5,058 exactly-serialized characters
against a 32,000 budget**, and that greedy set-cover reaches **15/17 at 5,455
characters**. Deployed selection delivers 6/17 while spending the full budget.

The gap is not capacity, formation, or cue quality. It is **selection**. The oracle
that closed it — greedy coverage maximization — is a named, forty-year-old
optimization problem with published approximation guarantees. Building an
approximation of it without reading that literature is exactly the failure this
program's landscape file exists to prevent.

## B.2 MMR — Carbonell & Goldstein (1998)

*The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing
Summaries.* SIGIR '98, pp. 335–336.

<cite index="10-1">MMR aims to reduce redundancy while maintaining query relevance, both when reranking retrieved documents and when selecting passages for summarization.</cite>

**Formulation.** <cite index="16-1">Candidates are scored as λ · Sim(Dᵢ, Q) − (1 − λ) · max_{Dⱼ∈S} Sim(Dᵢ, Dⱼ), where Sim is cosine similarity between embeddings, Q is the query, and S is built by adding each argmax candidate one at a time until the desired size is reached.</cite>

**Mechanics that matter for implementation.** <cite index="15-1">The first pick is simply the most relevant item, because the similarity penalty is zero when nothing has been selected. Each subsequent pick scores relevance minus a penalty for similarity to the most similar already-selected item. MMR is a post-scoring reranker: the pointwise relevance model runs first, then MMR adjusts ordering to reduce redundancy — a clean separation of concerns requiring no retraining.</cite>

That separation is why MMR is cheap here: it slots behind the existing cosine
retrieval without touching the embedder, the store, or the packing accountant.

**Reported strength.** <cite index="14-1">Carbonell and Goldstein report the clearest advantage in constructing non-redundant multi-document summaries, with preliminary benefits for MMR diversity ranking in document retrieval and single-document summarization.</cite> <cite index="12-1">In their user study, participants were not told which ordering method was used, and a majority preferred the method they felt gave the broadest and most interesting topics — MMR.</cite>

**Common configuration.** <cite index="10-1">A recent RAG evaluation uses MMR at λ = 0.5 against greedy top-k budget-fill and BM25, with all methods operating on the same top-100 cosine-pre-filtered candidate pool.</cite> That is a directly reusable experimental shape.

## B.3 The submodular family — Lin & Bilmes (2010, 2011)

*Multi-Document Summarization via Budgeted Maximization of Submodular Functions.*
NAACL-HLT 2010, pp. 912–920.
*A Class of Submodular Functions for Document Summarization.* ACL-HLT 2011, pp. 510–520.

**This is the family AR-001's oracle belongs to, and it is a better match to this problem than MMR.**

**The problem statement is literally ours.** <cite index="24-1">Selecting an optimal subset under a budget is framed as argmax_{S⊆𝒮} f(S) subject to Σ_{s∈S} c_s ≤ B, where c_s is the cost of element s, B is the budget, and f is a set function scoring the quality of the whole selection.</cite> Substitute *episode* for *sentence* and *exactly-serialized characters* for *word count* and it is the E005 problem unchanged.

**Why a set function and not a per-item score.** This is the conceptual break from
current behavior. Cosine ranking scores each episode independently; f(S) scores the
*selection as a whole*, so the value of adding an episode depends on what is already
in it. That is the property AR-001's oracle exploited.

**The algorithm.** <cite index="24-1">The task is NP-hard, but near-optimal performance is guaranteed by a modified greedy algorithm that iteratively selects the element maximizing the ratio of quality gain to scaled cost — (f(S ∪ s) − f(S)) / c_s^r — where r ≥ 0 is a scaling factor.</cite>

**The guarantee requires structure.** <cite index="24-1">For the performance guarantees to hold, f must be submodular and monotone non-decreasing.</cite> Submodular means diminishing returns: an episode adds less when much is already selected. Monotone means adding never hurts.

**Guarantee values, and a correction in the literature worth knowing.**
<cite index="27-1">Wolsey (1982) first showed the Greedy+Singleton algorithm — return the better of the greedy solution and the best single item — guarantees 0.35. Khuller et al. (1999) suggested it for a special case and Lin & Bilmes (2010) adapted it to submodular functions.</cite> <cite index="18-1">A 2021 analysis raises the factor to 0.405, improves on Wolsey's 0.357 and the (1−1/e)/2 ≈ 0.316 of Khuller et al., and closes a gap in Khuller et al.'s proof of the widely cited (1−1/√e) ≈ 0.393 — clarifying a long-standing misconception. It also derives a data-dependent upper bound on the optimum, typically giving a ratio much higher than 0.405 in practice.</cite>

**The data-dependent bound is directly useful here.** It means a greedy run can
report how close it is to the unknown optimum on *this* corpus, rather than only
citing a worst-case constant.

**Cost-scaling caveat.** <cite index="24-1">The scaling factor r ensures quality gain and item cost are comparable.</cite> In practice it is corpus-dependent: <cite index="28-1">Shang et al. found λ mostly non-zero — a diversity regularizer is necessary — but r sometimes zero, meaning costs did not enter the greedy decision at all, contradicting Lin's (2012) conclusion that r = 0 cannot give best results.</cite> **Sweep r; do not assume it matters.**

**A concrete objective function to copy.** <cite index="28-1">Shang et al. use f(S) = Σ_{sᵢ∈S} n_{sᵢ} w_{sᵢ} + λ Σ_{j=1..k} 1[∃ sᵢ ∈ S | sᵢ ∈ clusterⱼ] — a weighted informativeness term plus a diversity term counting how many distinct embedding-space clusters the selection touches.</cite> The second term is a coverage count over clusters. It is monotone, submodular, and requires no knowledge of which facts exist.

**Facility location.** The other standard submodular objective is
f(S) = Σ_{i∈V} max_{j∈S} sim(i, j) — every episode in the store should have a good
representative in the selection. It is monotone submodular and, unlike MMR's
pairwise penalty, it measures **coverage of the corpus** rather than dissimilarity
among the picks. <cite index="10-1">MMR and Determinantal Point Processes are described as the classical instances of diversity-aware selection</cite>; facility location sits alongside them with stronger guarantees under the submodular framework.

## B.4 Analysis — what actually transfers, and what does not

Four conclusions, each with a consequence for the protocol.

**1. AR-001's oracle is submodular coverage maximization.** "Number of distinct Q11
facts covered" is a monotone submodular coverage function; greedy set-cover is the
standard algorithm for it. The oracle is not an ad-hoc script — it is the exact
optimization Lin & Bilmes formalize, run with ground truth. **E005 is therefore
correctly framed as approximating a known optimum, with 15/17 @ 5,455 as its
measured target.**

**2. The knapsack half of the literature does not transfer, because the budget is slack.**
Lin & Bilmes' central contribution is *budgeted* maximization — selection when cost
binds. Here 17/17 fits in 7,592 characters against 32,000. **The budget is not
binding at roughly 4× headroom.** Cost-normalized greedy is built for a constraint
this problem does not have. Consequence: expect r ≈ 0 to be competitive, keep the
sweep small, and put the effort into the objective function f instead. *This is the
kind of mismatch the scan exists to catch — importing the knapsack machinery would
have been solving someone else's constraint.*

**3. MMR and facility location optimize different things, and the difference is the
whole experiment.** MMR penalizes similarity *to what is already picked*. Facility
location rewards *representation of the entire store*. On a four-domain breadth
query these come apart: MMR can assemble four mutually dissimilar episodes that
collectively represent one corner of the store, while facility location is pushed
toward spanning it. **Both must be tested; neither is the obvious winner.**

**4. Verification owed before the write-up.** MMR's objective is widely described as
lacking the submodularity that buys the greedy guarantees, which would make it a
heuristic where Lin & Bilmes' formulations are approximation algorithms. **This was
not confirmed from a primary source in this scan.** Confirm against Lin & Bilmes
(2011) §2 before stating it anywhere. Do not cite it as established on the strength
of this document.

## B.5 Novelty position

MMR (1998), facility location, and submodular summarization (2010–2011) are
**established methods**. Nothing in E005 claims to invent a selection algorithm.

What is not established, and what E005 measures: **how these selectors behave on
conversational episodic memory under an enforced exact-character budget, evaluated
against a per-fact oracle measured on the same store.** The published work evaluates
on ROUGE against reference summaries. AR-001 supplies something ROUGE cannot — a
committed, exact, per-fact optimum with its exact character cost. Reporting a
deployable approximation against a measured optimum, on this corpus, is the
contribution. **Grounding, never derivation.**

## B.6 Reference list

- Carbonell, J. & Goldstein, J. (1998). *The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries.* SIGIR '98, 335–336.
- Lin, H. & Bilmes, J. (2010). *Multi-Document Summarization via Budgeted Maximization of Submodular Functions.* NAACL-HLT, 912–920.
- Lin, H. & Bilmes, J. (2011). *A Class of Submodular Functions for Document Summarization.* ACL-HLT, 510–520.
- Nemhauser, G., Wolsey, L. & Fisher, M. (1978). *An Analysis of Approximations for Maximizing Submodular Set Functions — I.* Mathematical Programming 14, 265–294.
- Khuller, S., Moss, A. & Naor, J. (1999). *The Budgeted Maximum Coverage Problem.*
- Feng, Wang et al. (2021). *Revisiting Modified Greedy Algorithm for Monotone Submodular Maximization with a Knapsack Constraint.* ACM POMACS. — 0.405 factor; closes the Khuller et al. proof gap; data-dependent upper bound.
- Shang, G. et al. (2018). *Unsupervised Abstractive Meeting Summarization with Multi-Sentence Compression and Budgeted Submodular Maximization.* ACL 2018. arXiv:1805.05271. — concrete objective function; λ and r tuning evidence.
- Kulesza, A. & Taskar, B. (2012). *Determinantal Point Processes for Machine Learning.* — not scanned; the third classical diversity family.

**Not scanned, recorded as owed:** DPPs; diversity in conversational-memory
retrieval specifically; Lin & Bilmes (2011) primary text for the MMR-submodularity
question in B.4(4).

---

# PART A — E005 LEDGER ENTRY AND PROTOCOL

### E005 — Diversity-aware / coverage-based selection

**Type:** CANDIDATE (deployable). **Addresses:** F1. **Status:** PROPOSED.

**Claim.** Cosine top-k scores each episode independently and therefore fills the
budget with mutually redundant episodes. Replacing it with a set-level objective —
one where an episode's value depends on what is already selected — recovers a
material fraction of the coverage gap AR-001 measured.

**Why this is the right next candidate.**
- AR-001 proved the gap is selection: 6/17 delivered against 15/17 available at 17% of budget.
- The oracle that reached 15/17 is submodular coverage maximization (B.4.1). E005 is its deployable approximation.
- It is a **post-scoring reranker** (B.2): no new model, no storage multiplier, no forward pass, no quant conflict, no second resident model. It satisfies every §4 ledger constraint.
- It keeps the `store.context(query, budget)` pure-function contract.

## A.1 Arms

Fixed candidate pool for every arm: the existing N-cap retrieval output, cosine
pre-filtered. <cite index="10-1">All methods operate on the same pre-filtered candidate pool</cite> — matching published practice and making the arms comparable.

| Arm | Selector | Purpose |
|---|---|---|
| **A0** | Current cosine top-k + N-first packing | Committed baseline. **6/17.** |
| **A1** | MMR, λ sweep | The classical reranker (B.2) |
| **A2** | Facility location, cost-scaled greedy | Corpus coverage (B.3) |
| **A3** | Coverage + cluster-diversity, Shang-form f(S) | Explicit diversity regularizer (B.3) |
| **A4** | Greedy set-cover with ground-truth facts | **ORACLE.** AR-001: **15/17 @ 5,455 chars.** Never deployable |

A4 is not re-derived; it is AR-001's committed result carried in as the ceiling.

## A.2 Parameters

- **λ** (A1, A3): sweep [0, 1] step 0.1. <cite index="10-1">λ = 0.5 is the common published default for MMR</cite> and should be reported explicitly. <cite index="28-1">Shang et al. found λ mostly non-zero</cite>.
- **r**, cost scaling (A2, A3): sweep {0, 0.5, 1.0} only. **Deliberately small — B.4.2 argues the budget is slack at ~4× headroom, so r is expected to be inert.** If r matters materially, that contradicts the slack-budget analysis and is itself a finding to escalate.
- **Budget:** enforced 32,000 characters, exact serialized cost, post-DR-001 renderer. No arm may exceed it.
- **Similarity:** the carried, hash-verified embedding model. No new embedder.

## A.3 Kill condition

**E005 is KILLED if no arm exceeds A0's 6/17 at the enforced budget.**

Registered secondary reference points, reported but **not** kill thresholds:
- E002's best: **10/17** (killed on its own registered hurdle).
- Rubric threshold: **14/17**.
- Oracle: **15/17 @ 5,455 characters**.

**Rationale for setting the bar at A0 and not at 14/17.** E002 was killed against a
13/17 hurdle set under superseded accounting, and the post-hoc interpretation
records that it improved its exact-budget baseline by 66.7% while remaining KILL.
The lesson is that a bar must be checked for achievability against the regime the
arm actually runs in. A0 at 6/17 is the committed same-regime baseline. **State the
achievability check in the design commit** — AR-001 has already established 14/17 is
reachable at this budget, so 14/17 is achievable in principle; it is simply not the
threshold for "this mechanism does something."

## A.4 Mandatory diagnostics

Reported for every arm and configuration, not only the winner.

1. **Per-domain fact counts.** AR-001 domain costs: civil 826, art 3,182, monetary
   2,913, marine 824. E002's best reached 3/4 domains. **A selector that improves
   the total while still dropping a domain has not solved breadth.**
2. **Characters spent vs facts delivered.** The oracle's ratio is 15 facts / 5,455
   characters. Efficiency, not just count, is the finding.
3. **Prior-answer fraction.** AR-001 noted four optimal-set episodes are prior probe
   answers. Log, per arm, what fraction of selections are prior answers vs raw
   turns. **Study 004's error-cascade dynamic is the hazard:** preferring prior
   answers propagates prior errors, and Q11's prior answers were largely wrong.
4. **Data-dependent optimality ratio** where computable (B.3), reported alongside
   the worst-case constant.
5. **Selection overlap with the oracle set.** Which of the oracle's episodes each
   arm found, and which it missed. This distinguishes "close to the oracle" from
   "coincidentally similar score."

## A.5 No-regression arm — binding

Targeted recall currently runs at 60/60 with 203 K events. **Every arm must be run
against the targeted probes and must not degrade from the committed result.**

A diversity penalty is actively dangerous here: on a targeted query the correct
answer may be several near-identical episodes about the same fact, and MMR's penalty
suppresses exactly that. **If any arm improves breadth while degrading targeted
recall, it is not a win — report both and do not promote.**

## A.6 Surrogate audit

> *Can each check pass while the property it certifies is false?*

| Check | Certifies | Can it pass falsely? | Mitigation |
|---|---|---|---|
| Diversity score improved | more facts covered | **Yes — the central risk.** Dissimilarity is a surrogate for informational novelty. Chit-chat is maximally dissimilar from a technical turn and factually empty. Precedent: density was a surrogate for factual content and ranked the six hard plants 89th–316th | Score on **fact count**, never on the diversity objective. The objective is the mechanism; facts are the measurement |
| Total facts increased | breadth solved | Yes — by concentrating in cheap domains | Per-domain counts mandatory (A.4.1) |
| Arm beats A0 | selector is better | Yes — if it spent more characters | Report facts-per-character; both arms enforced at the same budget |
| Beats the oracle's fact count | approximation is excellent | Yes — impossible by construction, so a value above 15/17 means the fact-detection code is wrong | Treat >15/17 as a bug signal, not a result |
| Targeted unchanged in aggregate | no regression | Yes — aggregates hide per-probe swings | Per-probe reporting on the no-regression arm |

**Accepted residual:** all arms are evaluated on one probe (Q11) against one store.
Q11 is the program's only breadth probe. **No arm may claim general breadth
capability from it.** State this wherever a result is cited.

## A.7 Integrity requirements

Standard, carried unchanged:
- Design anchor committed **before** implementation; SHA recorded.
- Kill condition and diagnostics committed **before** any result is opened.
- Leakage: the ground-truth fact key is measurement, never mechanism. **A4 is the
  only arm permitted to read it, and A4 is not deployable.** Grep + import-graph
  audit with a planted violation, as standing protocol.
- Mechanism seal, source integrity, determinism spot-check, raw rerun determinism.
- Full suite green (currently 760).
- One PR; `README.md`, `AGENTS.md` digest, and ledger updated in the same PR.
- `ERRATA.md` if any committed number changes.

## A.8 Deliverables

- [ ] Design anchor commit, before implementation
- [ ] Achievability statement for the kill condition (A.3)
- [ ] A1–A3 implemented behind the existing selection interface; A0 unchanged; A4 carried from AR-001
- [ ] λ and r sweeps, all arms
- [ ] Per-arm fact counts, per-domain counts, chars spent, facts-per-character
- [ ] Prior-answer fraction per arm
- [ ] Oracle-overlap table
- [ ] No-regression targeted results, per probe
- [ ] Verification of B.4(4) against Lin & Bilmes (2011) primary text
- [ ] Ledger entry closed with verdict; graveyard updated if killed

---

*Drafted July 30, 2026. Scan performed against primary sources, not recall.
AR-001: 14/17 @ 5,058 chars, 17/17 @ 7,592, greedy 15/17 @ 5,455; domain costs
civil 826 / art 3,182 / monetary 2,913 / marine 824. E002 KILLED at 10/17 vs
exact-budget baseline 6/17. E001 KILLED, F2 closed. PR #25.*
