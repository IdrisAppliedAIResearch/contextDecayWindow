# Retrieval Mechanism Ledger

**Type:** Living working document. Not a pre-registration, not a spec, not a study.
**Repository:** `contextDecayWindow` (memory track). **Track 2 only.**
**Status:** OPEN - extended through TA-001 on August 11, 2026
**Purpose:** One place where candidate retrieval mechanisms are recorded, checked against the failure data, and either promoted to a cheap test or buried. Replaces ad-hoc specs. **Nothing here is authorized work until it has a passing decisive test.**

---

## 0. Cross-track rule - read before adding an entry

**This ledger is `contextDecayWindow` only.**

`RecursiveSelfHealingAgent` (Track 1) contains the attention-head analysis, the
logit lens probe, the Attention Gateway prior work, and the transformers
forward-hook tooling. **None of it exists in this repository.** Track 1's Study
002B is paused and its first run was invalidated.

Track 1 findings may be cited as **evidence that a mechanism is worth trying**.
They may **never** be counted as available infrastructure here. An entry whose
decisive test needs tooling from the other repository is a build, not a test, and
must say so in its cost line.

*(Violated on the first draft of E001, which described a "cheap offline test"
using a dual backend that exists only in Track 1. Corrected in revision 2.)*

---

## 1. Entry types

Two kinds of entry. **Do not confuse them, and do not let an oracle drift into a roadmap.**

**CANDIDATE** - a mechanism that could ship if it passes. Must be implementable on
the standing runtime, must survive the constraints in Section 4, must carry a
no-regression arm.

**ORACLE / BOUND** - a measurement of what an entire family of mechanisms is worth.
**Never deployed.** Its job is to tell you whether to build the cheap members of
the family at all, or to stop. Precedent: bakeoff Tier 3 measured oracle routing at
**6.09%** and killed routing before a line of it was written.

An oracle is only informative when there is something to compare it to.
**Run the cheap candidates first, then the oracle as the bound.**

---

## 2. The one result everything must beat

**Raw delivery - hand the model more text and let attention sort it out - outperformed every retrieval mechanism this program built.**

- 6/6 availability and 5/6 correct use on the six formation-blind plants.
- Those six defeated density, IDF, entity extraction, promotion filters, and dreaming.
- Widened STM scored 11.0/13 vs the full LTM architecture's 12.0/13, losing by exactly one binary item.

**The model's own attention is the best retriever on record**, and it is reached by
putting text in the window - not by any mechanism in this repository. Candidates
here are curation *for* it: deciding what it gets to see under a real budget.

---

## 3. The failure surface

| # | Failure | Evidence | Status |
|---|---|---|---|
| **F1** | **Breadth / enumeration** | E002 raised its exact 32k matched baseline from 6/17 to 10/17 but missed the locked hurdle. AR-001 proves the bar exists: exact 14/17 costs 5,058 chars and 17/17 costs 7,592. E005 set-level selection reaches 12/17 at 4/4 domains with no targeted regression, and 35 of 146 configurations pass every gate. DX-001 localizes the whole remaining gap to one in-pool episode the objective declines everywhere, so the residual is a relevance-term problem. Threshold 14/17, binary | **OPEN, MATERIALLY ADVANCED - E005 PROMOTION_ELIGIBLE offline at 12/17; still short of the 14/17 rubric threshold and of the 15/17 oracle, and unvalidated in inference** |
| **F2** | **Bad cue / identity** | Corrected Q4 cosine 0.12042197585105896 vs K = 0.48. E001 best found across 335 cues was 0.21031804382801056; 0/714 crossed K. Planted turn 55, probed turn 115; exact N-first reachability is 108,432 chars | **CLOSED - Family QR did not authorize an identity repair** |
| **F3** | **No absence detection** | E002's duplicate/zero-unique counts did not certify completeness. EC-001 then emitted 0 component abstention signals across all 500 LongMemEval-S questions, while the fixed reader answered 17/20 abstention items correctly under Codex-substituted scoring | **RETIRED AS A COMPONENT REQUIREMENT — the detector remains absent, but the tested reader compensated; do not build a component mechanism without reader-level failure evidence** |
| **F4** | **Rare technical vocabulary** | `photophores`, `mantle margin`, `lead white`, `ultramarine glaze`, `marine snow`, `dual mandate`. Zero spaCy entities in the target span. Density ranks them 89th-316th. The later IDF audit has three non-primary variants that disagree | **SOLVED by raw delivery** (6/6) - do not re-solve |
| **F5** | **Enforced budget behavior** | Study 010 LTM undercharged Q13/Q14 by 67.9%/68.2%. Widened STM and bakeoff Tier 1 charged complete payloads exactly; post-DR-001 LTM now does too | **ENGINEERING FIXED; historical LTM results remain noncompliant** |

**What works and needs no mechanism:** targeted recall. Study 010 logged 203 K
events across Q1-Q12; `<retrieved_stm>` supplied all 60 targeted facts. Both arms
tied 12/12. **K-collapse is query-type-specific, not a scale failure.**

**Every candidate carries a no-regression arm against targeted recall.** Breaking
the one thing that works to fix the one that doesn't is a bad trade and is
undetectable without measuring it.

---

## 4. Constraints any candidate inherits

- **No inference calls in the memory path.** Study 005 principle.
- **No entity extraction as the primary index.** F4 is the reason; also why HippoRAG is a baseline, not an import.
- **No fabrication surface.** Select from the store; do not generate text about it.
- **Exact serialized cost**, via the post-DR-001 production renderer.
- **Must degrade gracefully under an enforced budget.** Untested for everything on record.
- **Must not require a second resident model** or a quant that conflicts with the standing runtime. *(Constraint added July 30, 2026 - see E001.)*
- **Surrogate audit before promotion.** Can the test pass while the property it certifies is false?
- **A scored gain below 3.0 points is not a result on this instrument.** Amendment
  001 Phase 2 ran the deployed configuration five times under identical corpus,
  settings, seed and runtime: four scored 8.0 and one 11.0, so the measured
  run-to-run band is **3.0 on the 13-point rubric**. Any candidate promoted on a
  one- or two-point live gain would be promoted on noise. Offline counts —
  delivery, availability, characters, identity — are unaffected and remain the
  ledger's currency, which is what they always were. *(Constraint added August 9,
  2026 - see `experiments/study_011/noise_band/NOISE_BAND_REPORT.md`. It cuts
  against promotion only; it may not be cited to revive anything this program
  killed, and Amendment 001 §1.2 makes that binding for K-first packing.)*
- **Every number in this ledger was measured behind recency-first packing.** IC-001
  replayed the corrected 121-turn run under both orders and found the K path
  delivered **zero episodes and zero characters at 8 of 8 probes** under the
  deployed order. Q11 rises 6/17 to 7/17 and the eight targeted probes 14/21 to
  18/21, both with zero losses, on frozen candidate identities. A candidate's
  measured value is therefore a joint readout of the mechanism and the fill
  order; a candidate that looks weak may have been starved rather than wrong.
  *(Constraint added August 6, 2026 - see `IC_001_REPORT.md`. This does not
  authorize re-running anything: IC-001 section 9 lists the five conditions.)*

  **Amended August 7, 2026 by Study 011, which tested that constraint live and
  found its natural reading wrong.** Starving the similarity path is real: the
  deployed arm scored identically to the recency-only arm on all thirteen
  questions, so the tier this ledger measures contributed nothing at all in
  deployment. But unstarving it did not help. The K-first arm delivered
  thirteen K-path episodes against the deployed arm's one, raised Q11
  availability to 10/17 and targeted to 10/21, and **scored a point lower**,
  7.0 against 8.0. The registered kill fired and the correction was not
  adopted. So a candidate that looks weak may indeed have been starved rather
  than wrong - and feeding it may still cost answers. No entry in this ledger
  is revived by Study 011, and a delivery gain remains not a result.
  *(See `experiments/study_011/study_011_report.md`. One seed, one run per arm,
  no variance estimate.)*

- **The tier every number here was measured against is not a recency window.**
  `logical_n_key` sorts the whole store by (has ever been delivered, turn last
  delivered, source turn, id) ascending: a least-recently-delivered coverage
  rotation. Replay reproduces the live ranking on 120 of 120 testable turns per
  arm. The delivered set overlaps a true window of the same size by 0.29, 36% of
  deliveries are older than the cap of 32 turns, and the rotation reaches all
  120 reachable episodes. **A candidate proposing to add breadth is therefore
  competing with a baseline that already touches everything**, which is the most
  plausible reading of why 79% of Study 011's K-first arm's similarity
  candidates were material the rotation had already nominated. Three different
  rules carry this name in the repository — the carried engines' rule at cap 10
  (every live run through Study 010), `logical_n_key` at cap 32 (corrected Tier
  6 and Study 011), and the extracted library's genuine last-N window at cap 32
  (EC-002, CC-003, CC-005) — so an entry must name the path it was measured
  against, not the tier. **The first two fail in opposite directions and no
  baseline intuition transfers between them:** the rotation reaches every
  episode and duplicates the similarity tier, while the carried rule locks onto
  the conversation's first nine turns and holds them for the rest of the run,
  reaching almost nothing. A breadth candidate benchmarked against the carried
  rule was competing with a baseline that delivered 111 of 120 episodes exactly
  once. *(Constraint added August 8, 2026 - see
  `experiments/study_011/amendments/AMENDMENT_002_n_tier_is_not_a_recency_window.md`.
  This does not establish what a real recency window would score.)*

### 4.1 What actually exists in this repository

Verify against the tree; this is from the record, not from inspection.

**Available:** the carried hash-verified embedding model; cosine similarity; the N
candidate cap; the K threshold; N-first packing against a character budget; the
compact episode renderer (DR-001); the append-only raw episode store; the STM
least-recently-delivered rotation, called the recency window everywhere in this
record and measured as a rotation in §4; the extracted library's separate
genuine last-N window; the replay harness; the probe-order validator; the
scoring protocol; llama.cpp generation runtime. ANN indexing and graph-construction code
exist from bakeoff Tiers 4-5 and are refuted, not absent.

**Not available:** any attention extraction, forward hooks, head analysis,
interpretability tooling, late-interaction/multi-vector retrieval, or reranking
machinery.

**Retired / failed, present but disabled:** dreaming and distillation, promotion
filters, TopicManager, rule detection.

---

## 5. Family QR - Query Representation

> **Shared hypothesis:** collapsing the query into one averaged vector is a common
> cause of F1 and F2. One vector points in one direction: on a breadth query it
> starves whichever domains the average does not point at (F1); on a targeted query
> it dilutes the one discriminative term across a sentence of filler (F2).

Three mechanisms, same hypothesis, **ranked by cost**:

| Entry | Mechanism | Type | Status | Cost | Deployable |
|---|---|---|---|---|---|
| **E002** | Mechanical query segmentation | CANDIDATE | **KILLED** | existing machinery | Yes |
| **E003** | Late interaction / token-level MaxSim | CANDIDATE | **NOT AUTHORIZED** | build, no second model | Yes, at a storage cost |
| **E001** | Attention-derived term selection | **EXPLORATORY DIAGNOSTIC** | **KILLED** | build + Q4 model in VRAM | **No** |

**Run order completed:** E002, then E001 as a narrow F2 diagnostic. E003 was
not run because no valid breadth bound authorized it.

E001 asks whether generator attention can improve the specific Q4 identity cue.
It does not measure perfect selection and cannot bound breadth.

---

### E002 - Segmented query retrieval with per-segment budget

**Type:** CANDIDATE. **Addresses:** F1 primarily, F2 possibly. **Status:** **KILLED July 30, 2026.**

**Disposition:** An exhaustive 992-cell sweep reached at most 10/17 Q11 items
across 3/4 domains and preserved every required targeted item. *(Originally
published as 14/16; corrected to 16/16 on August 1, 2026 - see
`amendments/AMENDMENT_004_targeted_item_identity.md`. The KILL is unaffected.)*
It did not beat
the historical 13/17 hurdle, which came from a 60,285-character Q11 payload.
The unchanged same-budget baseline was 6/17 at 31,946 characters, so E002
improved matched-budget availability by 66.7%. The KILL remains binding; F1
remains open. Mechanism seal, leakage audit, source integrity, and raw rerun
determinism all passed. See `artifacts/e002/E002_report.md` and
`E002_POSTHOC_INTERPRETATION.md`.

**Bar achievability:** AR-001 was registered after E002 and before its own
implementation or output. Exact dynamic programming over the committed
turn-log store found a 14/17 minimum of 5,058 serialized characters and a
17/17 frontier point of 7,592. Standalone complete-domain minima were civil
826, art 3,182, monetary 2,913, and marine 824 characters. E002's missing art
domain is therefore not explained by payload capacity. This is an answer-key
oracle over availability, not a deployable selection policy. Four of the five
threshold episodes are prior probe answers allowed by the locked
`source_turn < 120` rule, so AR-001 does not establish a plant-source-only
bound. See
`AR_001_Q11_ACHIEVABILITY_PROTOCOL.md` and
`artifacts/ar_001/AR_001_report.md`.

**Claim:** Segmenting the query and allocating a small fixed retrieval budget per
segment converts one averaged cue into several specific ones.

**Mechanism:** Split the query into M segments. Embed each separately. Retrieve
top-1 or top-2 per segment. Dedup by containment. Pack under the character budget.

**Why it is the strong candidate:**
1. **Keeps the contract.** `store.context(query, budget)` stays a pure function.
   No decode loop, no KV manipulation, still evaluable without a model.
2. **Retrieval volume becomes deterministic in query length.** M x b is bounded
   before retrieval runs - what an enforced budget (F5) needs.
3. **Mechanical.** No LLM decomposition, so no inference call and no fabrication surface.
4. **Converts F1 into N instances of the thing that already works** at 60/60.

**Prior art:** query decomposition and sub-query generation (typically LLM-driven -
the distinction here is that segmentation is mechanical); diversity-aware selection
(MMR, submodular/facility-location) is the established answer to coverage. The
blocking scan is complete; see `LITERATURE_SCAN.md`.

**Cost:** test with existing machinery. Embeddings and cosine only. No forward
pass, no generation, no new run.

**Decisive test - offline, embeddings only:**
1. Q11 probe against the committed bakeoff Tier 6 corrected store.
2. Baseline: current selection makes **13/17** facts available.
3. Sweep segment size S and per-segment budget b in {1, 2}.
4. Retrieve, dedup, pack at the enforced 32,000-character budget under exact cost.
5. Recount facts available.

**Kill condition:** does not exceed **13/17** at any (S, b). 14/17 is the rubric
threshold, so 14+ is the number that makes this interesting rather than merely better.

**No-regression arm:** targeted probes must not degrade from their committed result.
**Prediction to test, not assume:** a targeted query is homogeneous, so its segments
should retrieve near-identical episodes and dedup should collapse them back to
current behavior.

**Risks from our own record:**
- **Fixed-size segments are a surrogate for information needs.** A four-domain query
  might be 40 tokens; segmenting at 16 aligns with domains only by luck.
- **Boundaries through multi-word terms.** `marine snow`, `mantle margin`, `lead
  white`. A boundary splitting one destroys the discriminative term. Sweep boundary
  offsets, or segment on whitespace/punctuation rather than raw token counts.
- **Budget overflow on long queries.** M x b can exceed the character budget. The
  overflow rule is undefined and interacts with F5. Define before testing.

**Surrogate audit:** "retrieved b per segment" certifies "each need served" only if
segments align with needs. **Report, per segment, which episode was retrieved and
which domain it belongs to.** A configuration retrieving four episodes from one
domain has satisfied the mechanism and failed the purpose.

---

### E001 - Attention-derived term selection *(EXPLORATORY DIAGNOSTIC)*

*(Revision 4 - narrowed from an invalid family oracle. Not deployable; see Deployment.)*

**Type:** EXPLORATORY DIAGNOSTIC. **Addresses:** F2 only. **Status:** **KILLED July 30, 2026.**

**Disposition:** The deterministic NF4 capture calibrated 266 retrieval heads
from 32 cases and produced 714 complete cue-sweep rows across 335 unique cues.
No cue reached K=0.48. The corrected baseline was cosine 0.120421976 at
descriptive similarity rank 24/114; the best all-head cue reached 0.210318044
at rank 20/114. This is the best found across 335 cues, not a ceiling. Selecting
266/384 full-attention heads (69.3%) was non-discriminating relative to Wu et
al.'s reported under-5% retrieval-head sparsity, consistent with the all-head
arm winning. Source seal, leakage audit, source integrity, model revision, and
deterministic reruns passed. See
`artifacts/e001/analysis_001/E001_report.md`.

**Validity correction:** attention is not perfect term selection, and the
Q4-only test cannot bound F1 breadth. E001 cannot authorize E003 regardless of
its narrow F2 result. See `E001_attention_term_selection_protocol.md`.

**What it measures:** whether attention-derived query-term selection improves
the corrected Q4 cue enough to cross K. It is not a shippable mechanism or a
family ceiling.

**Mechanism:** Forward pass over the query. Extract attention over query tokens.
Select top-k. Embed *only those tokens* with the carried embedding model. Retrieve
on that vector. Attention supplies **token selection**; the embedder still supplies
the vector, so no cross-model vector transfer is required.

**Prior art (scanned July 29, 2026):**
- *Retrieval Head Mechanistically Explains Long-Context Factuality* (Wu et al.,
  arXiv:2404.15574). <5% of heads perform the copy-paste retrieval operation;
  universal, sparse, present from short-context pretraining. Detection code:
  `nightdessert/Retrieval_Head`.
- *ICR* (ICLR 2025) and *ReAttn* (arXiv:2602.19969) - score candidates by attention
  received from query tokens. **Requires candidates already in context: reranking.**
- *PECAN* (arXiv:2410.04790); *attention sorting* (Peysakhovich & Lerer 2023) - also in-context.
- ColBERT late interaction - see E003.
- Encoder-based term weighting (DeepCT, DeepImpact) - trained encoder, not the
  generator's inference-time attention.

**Not found:** using the generator's own attention to construct a **first-stage**
retrieval cue over a corpus not in context.

**Cost: BUILD, completed for the diagnostic.** The implementation uses the
Transformers path, model-specific retrieval-head calibration on Qwen3.6 27B,
and eager full-attention capture. **The model fits only at Q4 in available VRAM.**

**Compute is not the constraint the test is limited by.** The forward pass is over
the *query* - tens of tokens, not the 50k context - so attention is trivially
cheap at that length. The Q4 constraint is about fitting the model in VRAM under
eager attention, not about sequence length.

**Deployment status: NOT DEPLOYABLE on the standing runtime.**
A generator forward pass per retrieval, a second model resident in VRAM, and
transformers alongside llama.cpp, for the life of a long-lived agent. This is why
it remains diagnostic. **If it passes, it does not become the roadmap.**

**Validity caveat:** Q4 diverges from the standing UD-Q6_K_XL runtime, against the
standing rule that hardware must not cap study intelligence. The measurement is
*which query tokens attention selects*, which is plausibly more quant-robust than
generation quality - but that is an assumption, not a finding. **Exploratory only;
never enters the confirmatory record. State the quant wherever the number is cited.**

**Decisive test:** Q4 probe at turn 115 from the committed Study 009 Arm L
artifact. Forward pass; extract attention over probe tokens (all-heads averaged vs
retrieval-heads-only); select top-k with a sweep; embed selected tokens with the
carried embedder; recompute cosine against the turn-55 identity bundle. Baseline:
the corrected committed **0.12042197585105896** (`0.16612689197063446` is
superseded). Sweep probe position - see risks.

**Interpretation:** The narrow F2 signal is present only if a cue reaches
K=0.48. Similarity rank is descriptive because the historical rank 27 is a
different, logical N ordering. E003 remains unauthorized under either outcome
because this Q4-only diagnostic has no breadth arm.

**Risks - all from Track 1, advisory only:**
- **Attention ceiling 0.05-0.17** (Track 1, Study 002). If attention over probe
  tokens is that flat there is no signal to select on. Most likely killer.
- **Logit lens** (Track 1): at the generation position the model encodes *what it
  is about to do*, not what it read. Probe position is a free parameter; sweep it.
- **Attention bias** toward punctuation and meaningless tokens (ReAttn); ICR
  calibrates with an "N/A" query. Expect to need the same.

**Surrogate audit:** "cosine improved" certifies "the right episode is retrieved"
only if the **ranking** changes. Report the turn-55 bundle's rank under each arm,
not only its cosine. A cue that raises all cosines uniformly has done nothing.

---

## 5A. Family CS - Coverage Selection

> **Shared hypothesis:** cosine top-k scores each episode independently and
> therefore fills the budget with mutually redundant episodes. A set-level
> objective, where an episode's value depends on what is already selected,
> recovers a material fraction of the coverage gap AR-001 measured.

### E005 - Diversity-aware / coverage-based selection

**Type:** CANDIDATE (deployable). **Addresses:** F1. **Status:** **PROMOTION_ELIGIBLE August 1, 2026.**

**Disposition:** All 146 swept configurations beat A0's committed 6/17 at the
enforced 32,000-character budget; 137 preserved targeted recall completely, 40
covered all four domains, and 35 passed all three gates. The primary
configuration `A3_l0.1_r0.0_k16` delivered **12/17 items across 4/4 domains at
31,569 characters with 16/16 targeted items preserved**, recovering 4 of the
oracle's 5 episodes. A2 facility location produced the highest raw count, 13/17,
but delivered monetary 0/4 at every `r` and passed no gate - the registered
per-domain surrogate check firing as designed. Data-dependent optimality ratios
of 0.955-0.9996 place greedy near its own bound, so the remaining gap to the
oracle is in the objective, not in the search. Mechanism seal, leakage audit,
source integrity, and byte-identical rerun all passed. Promotion eligibility is
an offline result; **no live run is authorized.** See
`artifacts/e005/E005_report.md` and `E005_POSTHOC_INTERPRETATION.md`.

**Two escalations recorded, neither changing the outcome:**
1. **`r` is not inert.** It changes the fact count in 44/44 A3 cells. The budget
   is slack for the *optimum* (15/17 costs 5,455 of 32,000) but not for the
   *selector*, because the registered greedy frame fills the budget. The
   knapsack constraint is active after all.
2. **The candidate pool is load-bearing.** On the deployed N-cap union K pool,
   **zero** configurations cover four domains, so nothing could have passed the
   surrogate gate. The registered unrestricted pool is what made the experiment
   measurable.

**Post-promotion diagnostics, neither reopening the entry:**
- **DR-002 (pool prior).** Cosine ordering is the wrong prior for this probe:
  the four highest-cosine episodes carry zero Q11 items and both art
  contributors sit at ranks 50 and 86. Widening 34 to 119 moves the frozen
  configuration from 5/17 at 2/4 domains to 12/17 at 4/4. The failure is
  query-type-specific - every targeted probe places all needed items inside
  rank 2. See `E005_DR_002_pool_prior_diagnostic.md`.
- **DX-001 (turn-90 miss).** The entire remaining gap to the oracle is one
  episode: turn 90, monetary, 4 items, cosine rank 112. **It is in the pool and
  the objective declines it in all 146 configurations.** Attribution M2+M3+M4;
  M1 cluster collision is refuted - its k=16 cluster is never entered, so the
  diversity term was payable in full at all 15 steps and it still lost by
  0.169. To win it needed cosine 0.225 against its actual 0.056. Outcome:
  **NO CHANGE**, 12/17 ships with rank 112 as a characterized limitation, and
  the objective question escalates to a proposed, unauthorized E006. See
  `DX_001_PART2_DISPOSITION.md`.
- **RD-001 / E006 Part 1 (rarity diagnostic).** The complete 119-rank ordering
  replayed under E005's committed embedding call, but the registered
  correlation stopped before computation. The prior rarity artifact scores
  only 6 of 76 fact-bearing episodes and exposes three variants without a
  registered primary or episode aggregation. No registered branch covers that
  state. The vocabulary alternative remains unresolved. E006 Part 2 Rev 2 was
  separately authorized for offline stages S1-S4 on August 10, 2026; it does
  not alter RD-001's result or authorize live evaluation. S1 found no published
  negative on conversational memory, so its registered kill did not fire.
  RF-Mem is close positive prior art for iterative embedding-space memory/query
  mixing, while MemR3, EviMem, and MGRetrieval are positive inference-driven
  neighbors. **S2 FAILS and stops before S3:** no committed raw query vectors
  exist for the eight probes, and X1 cannot equal X0 because `exclude=seen`
  accumulates `m` new episodes on each inclusive `0..D` iteration even when
  `BETA=0`. See `RD_001_report.md`, `E006_PART2_AUTHORIZATION.md`,
  `E006_PART2_S1_PRIOR_ART_SCAN.md`, and `E006_PART2_S2_PREFLIGHT.md`. Rev 3 was
  separately authorized as a Q11-only zero-call repair and **STOPPED AT PF11**:
  its registered mean-hit equations omit the mechanism's recursive `RHO`
  context. Full rankings agree in 0/12 cells, score differences span
  0.040-0.212, and 3/12 next `top_m` sets change. A corrected recurrence matches
  the reconstructed-vector route to `9.5e-15` but is not registered and cannot
  pass the gate. See `E006_PART2_REV3_PF11.md`. Rev 4 prospectively registered
  that recursive structure and was separately authorized, but **STOPPED AT PF11
  again**: its context norm uses `BETA^2` where the mean hit vector requires
  `BETA^2 * ||mu||^2`. The observed squared norms are 0.843 and 0.533. Score
  tolerance and full rankings pass in 0/12 cells, although all 12 immediate next
  sets agree. PF1-PF10 and S3-S4 were not entered. See
  `E006_PART2_REV4_PF11.md`. Rev 5 prospectively registered the complete norm
  expansion and **COMPLETED offline, CHARACTERIZED**. PF11 passes 12/12 at
  `9.5e-15`; PF1-PF10 and all 48 PF7 cells pass. Chaining reaches 9/17 at D2/D3
  versus X0's 6/17 and single-shot `top_m` at 3/17, so its kill does not fire.
  The best cells use 15-20 candidates, select 12 episodes, and still deliver
  0/4 art facts; they trail E005's 12/17. No targeted traces exist, so there is
  no promotion, adoption, or live run. See `E006_PART2_REV5_REPORT.md`.

**Measurement correction applied before the outcome was accepted:** the
no-regression numerator was keyed on `(turn, item)` while its denominator
counted rows, and Q7/Q10 share two turn-118 items, capping preservation at 14/16
for any selector. Corrected to question-scoped identity. This also corrects
E002's published 14/16 to 16/16 without disturbing its KILL. See
`amendments/AMENDMENT_004_targeted_item_identity.md` and `ERRATA.md`.

**Claim:** Replacing per-item cosine ranking with a set-level selection
objective recovers a material fraction of the AR-001 coverage gap.

**Why it is the right next candidate:**
- AR-001 proved the gap is selection: 6/17 delivered against 15/17 available at
  17% of budget.
- The oracle that reached 15/17 is submodular coverage maximization. E005 is its
  deployable approximation.
- It is a **post-scoring reranker**: no new model, no storage multiplier, no
  forward pass, no quant conflict, no second resident model. It satisfies every
  Section 4 constraint.
- It keeps the `store.context(query, budget)` pure-function contract.

**Arms:** A0 committed cosine/N-first baseline at 6/17; A1 MMR; A2 facility
location, cost-scaled greedy; A3 relevance plus cluster diversity in the Shang
form; A4 AR-001's greedy set cover carried in at 15/17 / 5,455 chars as the
reference point, never deployable.

**Kill condition:** KILLED if no arm exceeds A0's committed 6/17 at the enforced
32,000-character budget. The bar sits at the same-regime baseline, not at the
14/17 rubric threshold, because E002 was killed against a hurdle imported from a
superseded accounting regime.

**Registered candidate-pool decision:** the primary pool is the complete
eligible store with no similarity pre-filter. The deployed N-cap union K pool
contains two of AR-001's five optimum episodes and a cosine top-100 pre-filter
contains four; either restriction would set the ceiling by pool construction
rather than by the selector. Both restricted pools are reported as secondaries.

**Cost:** test with existing machinery. Embeddings and cosine only. No forward
pass, no generation, no new run.

**Prior art:** MMR (Carbonell and Goldstein 1998); budgeted submodular
maximization (Lin and Bilmes 2010, 2011); facility location; Shang et al. (2018)
objective form; Feng/Wang et al. (2021) data-dependent bound. Scan complete; see
`E005_diversity_selection_scan_and_protocol.md`.

**Surrogate audit:** "diversity score improved" certifies "more facts covered"
only if dissimilarity tracks informational novelty, which it does not - chit-chat
is maximally dissimilar and factually empty. Score on fact count, never on the
diversity objective. Per-domain counts are mandatory.

See `E005_diversity_selection_protocol.md` for the committed design anchor and
`E005_diversity_selection_scan_and_protocol.md` for the literature scan.

---

### E003 - Late interaction / token-level MaxSim

**Type:** CANDIDATE. **Addresses:** F1, F2. **Status:** **NOT AUTHORIZED.**

**Claim:** Query-vector dilution is solved structurally by never forming a single
query vector: embed query tokens individually and score each stored episode by the
maximum similarity across query tokens.

**Mechanism:** ColBERT-style late interaction using the carried embedding model.
Per-token query vectors, MaxSim against per-token or per-span episode vectors.

**Why it sits between E002 and E001:** no generator forward pass, no second model,
no quant conflict - so unlike E001 it is deployable. But it requires per-token
vector storage, which is a real and unmeasured cost against F5 and against store
growth at 1,000+ turns.

**Cost:** BUILD. No multi-vector machinery exists here.

**Gated on:** a valid breadth bound. The supplied Q4-only E001 test cannot
provide one, so no E003 implementation or storage-cost experiment is authorized
by this ledger pass.

**Open question before any test:** what is the storage multiplier for per-token
vectors over the Study 010 store, and does it survive the enforced-budget and
eviction work in `CC_001`?

---

## 6. Graveyard - refuted, do not re-propose

| Mechanism | Killed by |
|---|---|
| Density / span salience for formation | Ranks the six hard plants 89th-316th (Study 006, Q11 audit) |
| IDF / rarity for **episode ranking** | **NOT REFUTED.** Mean IDF ranks 5/5 eligible hard-plant spans worse than density, but max IDF improves 2/5 and sum/word improves 1/5; no primary was registered. See `RD_001_RARITY_PROVENANCE_AUDIT.md` and `ERRATA.md` |
| Entity extraction as index | Zero spaCy entities in the target span (F4) |
| Promotion filters (novelty/repetition/association/emotional) | Weighted route structurally unreachable; every promotion via bypass (Study 003) |
| Query-blind distillation for breadth | Five studies; bakeoff T1 8/17 |
| Topic layer / consolidation | 52 topics at 120 turns; 12 domains -> 2 at 1,000 turns |
| Associative graph (co-activation edges) | No configuration cleared the advancement gate (Bakeoff T4A); 4B never ran |
| Query-type routing | Oracle ceiling 6.09% (Bakeoff T3) |
| ANN at synthetic scale | Recall degraded (Bakeoff T5) |
| Mid-generation / active retrieval | **Not refuted - rejected on contract grounds.** Breaks the one-shot pure-function contract, requires KV manipulation, makes the component un-testable without a model. Revisit only if the deployable target becomes an agent rather than a library |
| Pinned identity tier | **Not refuted - unauthorized.** AS-001 withdrew the primacy conclusion; rank 27 needs 108,432 chars, a packing/budget limit |

---

## 7. Retired slot

- **F3 (absence detection): retired as a component requirement.**
  EC-001 records 0 component abstention signals on 500 cleaned LongMemEval-S
  questions, confirming the architectural absence. The fixed reader nonetheless
  scores 17/20 abstention items under Codex-substituted integrity, so component
  absence detection and end-to-end refusal are different properties. This is
  one reader, prompt, seed, and 20-item abstention subset, so F3 is not
  component-solved or universally unnecessary. It is retired because the
  external result removes the evidence that a new component mechanism is owed.
  Reopen only on a prospective reader-level regression. E002's 18
  slots yielded 10 unique episodes and eight duplicates; two of nine segments
  added no unique episode, but that signal did not certify completeness because
  the result still missed 7/17 facts and one domain.

## 8. Scan disposition

- Temporal-adjacency bridge: **G5 FAIL; TARGETED_REGRESSION,
  CHARACTERIZED.** TA-001 interleaves each direct-query seed with its eligible
  radius-1 source-turn neighbors under matched 15-candidate and 32,000-character
  limits. Q11 candidate facts rise 9/17->10/17, packed facts 7/17->9/17, and
  art 0/4->4/4. But 24 targeted queries yield 2 gains, 6 losses, and 16 ties;
  enumeration falls 0.3125->0.125. G5 blocks the 35-turn ablation, live run,
  promotion, and adoption. See `TA_001_REPORT.md`.
- Ambiguous natural-language cue resolution: **G3 FAIL;
  LOOKUP_BINDING_INSUFFICIENT, CHARACTERIZED.** PS-003's selected five-probe,
  four-swap consensus cell emits eight unanimous stored identities for all 24
  queries and rejects three cyclic, one spurious, and one disagreeing family.
  G1/G2 and PF1-PF10 pass. Lookup remains 7/12, identical to direct cosine and
  PS-002, with monetary 1/3 against the 2/3 domain bar. G4/G5, stress tests,
  answers, live evaluation, promotion, and adoption are not reached. See
  `PS_003_REPORT.md`.
- Natural-language cue binding: **STOP AT PREFLIGHT PART 1;
  NATURAL_CUES_NOT_BOUND, CHARACTERIZED.** PS-002 applies nine label-blind
  semantic-to-engram cells to 24 sealed query vectors for eight rounds each.
  No cell meets the registered all-query mechanical bar. Best `(M=4,
  TAU=0.025)` reaches stored codes in 190/192 rounds but one cue enters a cycle
  and one reaches a spurious fixed point; one query emits six rather than eight
  identities. Wider or softer mixtures produce more cue changes and more unsafe
  terminals. The answer key remains unopened by PS-002 measurement; final
  design, PF1-PF10, relevance, answers, live evaluation, promotion, and adoption
  are not entered. See `PS_002_REPORT.md`.
- Pattern-separated sparse engram formation: **COMPLETE;
  SPARSE_ENGRAM_CANDIDATE_CHARACTERIZED.** PS-001 reproduces Rev 4 exactly,
  then characterizes nine deterministic sparse cells on the same 119 episodes.
  Only `(D_CODE=4096, K_ACTIVE=41)` passes G3-G5: 119/119 fixed points and
  119/119 exact recovery at one swap, 10%, 30%, and 50%. Eight cells fail G3.
  The selected cell's registered corruptions have no cycles, spurious terminals,
  or tie-sensitive sweeps, but 1,351/4,096 units are unused, the conceptual
  recurrent matrix is 99.976% nonzero, and the union-biased degenerate cue
  enters a zero-margin two-cycle. This is same-store code-space completion, not
  natural-language cue binding, retrieval, a live result, biological
  replication, promotion, or adoption. See `PS_001_REPORT.md`.
- Autoassociative construct repair: **STOP AT PREFLIGHT PART 1;
  PATTERNS_NOT_STORED, CHARACTERIZED.** Rev 4 leaves the completed associative
  frontier result immutable and tests the intended attractor property directly.
  A symmetric zero-diagonal Hebbian recurrence passes the synthetic storage and
  one-bit recovery fixture but stores `0/119` real population-centered episode
  codes as fixed points. All 119 traces converge with non-increasing energy into
  six spurious attractors. Balanced coordinate marginals did not provide pattern
  separation. G4, PF1-PF10, Q11, live evaluation, promotion, and adoption are not
  entered. See `E006_PART3_REV4_REPORT.md`.
- Query-anchored associative-frontier retrieval: **COMPLETE;
  NO_DIFFERENTIATED_CUE, CHARACTERIZED.** This local strongest-edge frontier
  differs mechanically from Tier 4A's global PPR, but it does not reopen Tier
  4A's negative result. At primary `D=2, m=5`, A0/A1/A2 each admit 15
  candidates; A2 carries and packs 5/17 facts in civil only, versus A0's 9
  candidate/7 packed and A1's 9/9. Best A2 is 6/17 and every A2 cell has art
  0/4. Equal candidate quotas do not equalize volume or evidence opportunity;
  the local frontier reinforces a single-domain neighborhood. No targeted
  claim, live run, promotion, or adoption. See `E006_PART3_REPORT.md`.
- Retrieved-context chained retrieval: **REV 5 COMPLETE; CHARACTERIZED.**
  Classical PRF establishes both the operation and query drift. Four recent
  conversational-memory preprints report positive iterative-retrieval results;
  RF-Mem is close mechanical prior art. No published negative in the registered
  setting was located. Chaining and the conversational-memory setting are not
  novel; E006's remaining distinction is the committed corpus, deterministic
  zero-model-call path, and absorbing-state discipline. Preflight reproduces X0
  exactly but finds 0/8 cached probe-query vectors and proves X1 differs from X0
  for all six registered `(D,m)` cells on the committed Q11 rank trace. Rev 3
  repaired those defects and narrowed scope to Q11, but PF11 found its Section 2
  derivation was not the unchanged recursive mechanism. Rev 4 then registered
  recursion but omitted the hit mean's squared norm and stopped at PF11. Rev 5
  registers the complete norm: PF11 passes 12/12, remaining Preflight passes,
  and the fixed offline grid reaches 9/17 at D2/D3 versus X0's 6/17. The best
  cells still miss art 0/4 and return more material; without targeted traces the
  ceiling is CHARACTERIZED. See
  `E006_PART2_S1_PRIOR_ART_SCAN.md`, `E006_PART2_S2_PREFLIGHT.md`, and
  `E006_PART2_REV3_PF11.md`, `E006_PART2_REV4_PF11.md`, and
  `E006_PART2_REV5_REPORT.md`.
- Diversity-aware / coverage selection: **COMPLETE, and its one owed
  verification is discharged.** The scan's unconfirmed claim that MMR lacks
  submodularity is **refuted** by Lin and Bilmes (2011) Section 3, Theorem 2:
  `F_MMR` is **non-monotone submodular**. The greedy guarantee fails for MMR
  because the objective is not monotone, not because it is not submodular. The
  scan's conclusion stands; its reason does not. **No text in this repository
  may describe MMR as non-submodular.**
- Determinantal Point Processes: **still not scanned, still owed.**
- Query decomposition and multi-vector conversational retrieval: **COMPLETE.**
- Active / mid-generation retrieval: **COMPLETE.**
- Candidate-mechanism details and sources: `LITERATURE_SCAN.md`.
- Program positioning, benchmark adoption, HippoRAG disposition, and carried
  Section 7 decisions: `LITERATURE_LANDSCAPE.md`.

---

*Opened July 29, 2026. Revision 22, August 11, 2026 - TA-001 recovers Q11 art
0/4->4/4 and packed facts 7/17->9/17 under matched opportunity, but targeted
queries produce 2 gains, 6 losses, and 16 ties. G5 blocks ablation and live
evaluation. Revision 21, August 11, 2026 - PS-003 passes safe
ambiguity resolution but fails G3 with 7/12 lookup facts and monetary 1/3.
Direct cosine and PS-002 are also 7/12; G4/G5, stress, answers, and live use are
not reached. Revision 20, August 11, 2026 - PS-002 stops at Preflight
Part 1, NATURAL_CUES_NOT_BOUND, CHARACTERIZED. Best `(M=4,TAU=.025)` reaches
stored codes in 190/192 natural-language cue rounds but retains one cycle and
one spurious fixed point, so no cell emits eight clean identities/query. Labels,
PF1-PF10, answers, and live use are not entered. Revision 19, August 11, 2026 - PS-001 completes
CHARACTERIZED. One of nine sparse cells, `(4096,41)`, stores and recovers
119/119 codes through the registered 50% swaps. Degenerate cues retain a
zero-margin two-cycle; natural cue binding, retrieval, live use, promotion, and
adoption remain untested and unauthorized. Revision 18, August 10, 2026 - E006 Part 3 Rev 4 stops
at Preflight Part 1, PATTERNS_NOT_STORED, CHARACTERIZED. The Hebbian recurrence
stores 0/119 real episode codes and converges into six spurious attractors; G4,
PF1-PF10, and Q11 are not entered. Original P3 remains unchanged. Revision 17,
August 10, 2026 - E006 Part 3 closes
NO_DIFFERENTIATED_CUE, CHARACTERIZED. The query-anchored local frontier packs
5/17 facts in civil only at primary D2,m5 versus A0 7/17 and A1 9/17, peaks at
6/17, and retrieves art 0/4 throughout. Tier 4A's global-PPR boundary remains
closed; no targeted/live claim, promotion, or adoption. Revision 16, August 10,
2026 - E006 Part 2 Rev 5
completes offline, CHARACTERIZED. PF11 passes 12/12 at `9.5e-15`; PF1-PF10 and
PF7 48/48 pass. Chaining reaches 9/17 at D2/D3 versus X0 6/17 but uses 15-20
candidates, selects 12, and misses art 0/4. No targeted traces; no promotion or
live run. Revision 15, August 10, 2026 - E006 Part 2 Rev 4 is
authorized, then stops at PF11. Its context norm treats the mean of hit vectors
as unit length, but the observed squared norms are 0.843 and 0.533. Score
tolerance and full-ranking identity pass in 0/12 cells; all 12 immediate next
sets agree. PF1-PF10 and S3-S4 were not entered. Revision 14, August 10, 2026 - E006 Part 2 Rev 3 is
authorized, then stops at its first gate, PF11. Its registered mean-hit equations
omit the recursive context and `RHO`; 0/12 full rankings agree with the unchanged
mechanism, score gaps are 0.040-0.212, and 3/12 next sets change. A corrected
recurrence agrees to `9.5e-15` but is unregistered. Revision 13, August 10, 2026 - E006 Part 2 S2 fails and
stops before S3. X0 reproduces by content identity and payload digest, but no
committed cache contains the eight raw probe-query vectors required for the
chain, and the registered disabled-chain X1 is structurally unequal to X0
because exclusion accumulates new episodes at every inclusive `0..D` step.
Revision 12, August 10, 2026 - E006 Part 2 Rev 2 is
authorized for offline S1-S4. S1 finds no published negative for chained
retrieval on conversational memory, so the registered kill does not fire; four
positive conversational-memory preprints, especially RF-Mem's iterative
embedding-space alpha-mix, narrow the novelty position. Revision 11, August 3,
2026 - the IDF graveyard claim is
withdrawn after provenance review: no primary variant was registered, and only
mean IDF ranks all five eligible hard-plant spans worse than density. Revision
10, August 3, 2026 - RD-001 recovers the full
119-episode cosine ordering but stops before correlation because unchanged
rarity scores exist for only 6 of 76 fact-bearing episodes across three
unregistered variants. No coefficient is computed, no registered branch
applies, and chained retrieval remains unauthorized. Revision 9, August 1,
2026 - post-promotion diagnostics
recorded against E005 without reopening it. DR-002 finds cosine ordering is the
wrong prior for the enumeration probe and the candidate pool binds on both facts
and domains. DX-001 localizes the entire remaining oracle gap to one in-pool
episode at cosine rank 112 that the objective declines in all 146
configurations, refutes cluster collision as its cause, and closes NO CHANGE:
12/17 ships with the miss characterized, and the objective question escalates to
a proposed, unauthorized E006. One published DR-002 rank is corrected in
`ERRATA.md`. Revision 8, August 1, 2026 - Family CS opened and E005
diversity-aware selection returns PROMOTION_ELIGIBLE offline: 12/17 at 4/4
domains with 16/16 targeted preservation, against A0's 6/17. Facility location
scored highest and failed the per-domain gate. Two escalations recorded: cost
scaling `r` is material because the greedy frame fills the budget, and the
deployed candidate pool cannot express a four-domain answer at all. The
no-regression unit mismatch is corrected, which also lifts E002's published
14/16 to 16/16 without disturbing its KILL. The scan's MMR-submodularity claim
is refuted against primary text. Revision 7, July 31, 2026 - AR-001 establishes exact
bar achievability: 14/17 at 5,058 chars and 17/17 at 7,592; F1 remains an open
selection/ranking problem, not a 32k capacity impossibility. Revision 6, July
31, 2026 - outcomes unchanged; E002
cross-budget interpretation corrected; F1 left open and F2 closed; E002 segment
diagnostics recorded; literature landscape recovered and reconciled. Revision
5, July 30, 2026 - ledger closed: E001 and E002
killed by their registered diagnostics; E003 not authorized because no breadth
bound exists. Revision 4, July 30, 2026 - E002 killed by exhaustive
offline test; owed scans completed; F2 cosine corrected; E001 narrowed from an
invalid family oracle to an F2 diagnostic; E003 left unauthorized because no
breadth bound exists. Revision 3, July 30, 2026 - entry types introduced;
Family QR framing added; E001 recategorized as ORACLE/BOUND with deployment status
stated; E003 entered; second-resident-model constraint added to Section 4; mid-generation
retrieval moved to the graveyard on contract grounds; IDF graveyard entry narrowed
to episode ranking. Bakeoff `145d576c` / PR #22. DR-001 `202b1883` / PR #23.*
