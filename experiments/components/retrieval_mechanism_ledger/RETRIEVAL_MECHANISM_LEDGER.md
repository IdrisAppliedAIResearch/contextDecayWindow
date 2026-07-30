# Retrieval Mechanism Ledger

**Type:** Living working document. Not a pre-registration, not a spec, not a study.
**Repository:** `contextDecayWindow` (memory track). **Track 2 only.**
**Status:** OPEN - current Family QR queue disposition recorded July 30, 2026
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
| **F1** | **Breadth / enumeration** | Q11 never answered correctly by any arm. Raw store 8/17. Widened STM 13/17. Threshold 14/17, binary. Similarity ranking is anti-correlated with informativeness on breadth queries (Study 007) | **CLAIMED - Family QR** |
| **F2** | **Bad cue / identity** | Q4 bundle: corrected cosine 0.12042197585105896 vs K = 0.48 (0.16612689197063446 superseded). Planted turn 55, probed turn 115. Rank 27 of 32. First reachable at 108,432 chars vs 32,000 budget | **CLAIMED - Family QR** |
| **F3** | **No absence detection** | Q11 returned 8/17 and signalled nothing. No mechanism exists by which the system can know it is missing something | **UNCLAIMED** |
| **F4** | **Rare technical vocabulary** | `photophores`, `mantle margin`, `lead white`, `ultramarine glaze`, `marine snow`, `dual mandate`. Zero spaCy entities in the target span. Density ranks them 89th-316th; IDF worse | **SOLVED by raw delivery** (6/6) - do not re-solve |
| **F5** | **Enforced budget behavior** | No study in the record ran under an enforced ceiling; all were 68% over | Engineering - see `CC_001` |

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

### 4.1 What actually exists in this repository

Verify against the tree; this is from the record, not from inspection.

**Available:** the carried hash-verified embedding model; cosine similarity; the N
candidate cap; the K threshold; N-first packing against a character budget; the
compact episode renderer (DR-001); the append-only raw episode store; the STM
recency window; the replay harness; the probe-order validator; the scoring
protocol; llama.cpp generation runtime. ANN indexing and graph-construction code
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

| Entry | Mechanism | Type | Cost | Deployable |
|---|---|---|---|---|
| **E002** | Mechanical query segmentation | CANDIDATE | existing machinery | Yes |
| **E003** | Late interaction / token-level MaxSim | CANDIDATE | build, no second model | Yes, at a storage cost |
| **E001** | Attention-derived term selection | **EXPLORATORY DIAGNOSTIC** | build + Q4 model in VRAM | **No** |

**Run order:** E002, then E001 as a narrow F2 diagnostic. E003 remains
unauthorized until a separate breadth bound exists.

E001 asks whether generator attention can improve the specific Q4 identity cue.
It does not measure perfect selection and cannot bound breadth.

---

### E002 - Segmented query retrieval with per-segment budget

**Type:** CANDIDATE. **Addresses:** F1 primarily, F2 possibly. **Status:** **KILLED July 30, 2026.**

**Disposition:** An exhaustive 992-cell sweep reached at most 10/17 Q11 items
across 3/4 domains and preserved 14/16 required targeted items. It did not beat
the historical 13/17 hurdle. The unchanged same-budget baseline was 6/17 at
31,946 characters. Mechanism seal, leakage audit, source integrity, and raw
rerun determinism all passed. See `artifacts/e002/E002_report.md`.

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
(MMR, submodular/facility-location) is the established answer to coverage and
**has not been scanned. Scan blocks promotion.**

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

**Type:** EXPLORATORY DIAGNOSTIC. **Addresses:** F2 only. **Status:** PROTOCOL LOCKED - run after E002.

**Validity correction:** attention is not perfect term selection, and the
Q4-only test cannot bound F1 breadth. E001 cannot authorize E003 regardless of
its narrow F2 result. See `E001_attention_term_selection_protocol.md`.

**What it measures:** whether attention-derived query-term selection improves
the corrected Q4 cue enough to cross K or enter a compact similarity-ranked
candidate set. It is not a shippable mechanism or a family ceiling.

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

**Cost: BUILD.** No attention extraction exists here. Requires the transformers
path stood up in this repository, retrieval-head detection on Qwen3.6 27B, and
attention-bias calibration. **The model fits only at Q4 in available VRAM.**

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
K=0.48 or moves turn 55 to rank 9 or better. E003 remains unauthorized under
either outcome because this Q4-only diagnostic has no breadth arm.

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
| IDF / rarity for **episode ranking** | Ranks them *worse* than density (breadth regression audit). **Note: refuted as an episode-ranking signal, not as a query-term weighting signal - that role is untested** |
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

## 7. Open slots

- **F3 (absence detection):** nothing proposed. Arguably prior to F1 - a system that
  knew it had 8 of 17 could act on it. Candidate signals discussed, not entered:
  retrieval-score distribution shape; per-segment miss counts under E002 (**cheap,
  and it comes free with the E002 test**); generation-time confidence (FLARE-style,
  unscanned, breaks the one-shot contract).

## 8. Scan disposition

- Diversity-aware / coverage selection: **COMPLETE.**
- Query decomposition and multi-vector conversational retrieval: **COMPLETE.**
- Active / mid-generation retrieval: **COMPLETE.**
- Details and sources: `LITERATURE_SCAN.md`.
- `LITERATURE_LANDSCAPE.md` Section 7: **UNRESOLVED SOURCE REFERENCE**; no
  such file exists in the repository or beside the supplied ledger.

---

*Opened July 29, 2026. Revision 4, July 30, 2026 - E002 killed by exhaustive
offline test; owed scans completed; F2 cosine corrected; E001 narrowed from an
invalid family oracle to an F2 diagnostic; E003 left unauthorized because no
breadth bound exists. Revision 3, July 30, 2026 - entry types introduced;
Family QR framing added; E001 recategorized as ORACLE/BOUND with deployment status
stated; E003 entered; second-resident-model constraint added to Section 4; mid-generation
retrieval moved to the graveyard on contract grounds; IDF graveyard entry narrowed
to episode ranking. Bakeoff `145d576c` / PR #22. DR-001 `202b1883` / PR #23.*
