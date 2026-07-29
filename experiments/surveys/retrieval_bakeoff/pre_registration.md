# Retrieval Bakeoff — Exploratory Survey Pre-Registration (LOCKED v1)
## contextDecayWindow
**Idris Applied AI Research**
**Date:** July 2026
**Status:** LOCKED before implementation. The registration anchor is the commit that first adds this file.
**Source draft:** SHA-256 `e1e00a4a703ad5e81265f0b649e237af2481e2cd4089f6a6263b81ce5742ea5f`.
**Type:** Exploratory survey. **NOT a study. NOT in the arc numbering.** Path: `experiments/surveys/retrieval_bakeoff/`.
**Output class:** hypotheses and a candidate ranking. **Nothing produced here may be cited as a confirmatory finding.**

---

## 1. What this is, and what it is not

The program has assembled a memory pipeline and established, across five studies, that **query-blind selection cannot pick what a later question will need.** Every proxy tried — novelty, absolute entity counts, density, word-level IDF — selected a correlate instead of the target. That is now treated as a documented negative result, not a bug awaiting a fix.

The architectural direction changes accordingly: **store everything; make retrieval good.** Storage is cheap, and exact recall is the property a machine should have that biology cannot. Selection does not disappear — a 50,000-character window still cannot hold 100,000 turns — but it **moves from write time to query time**, where the system knows what is being asked. That is a categorically easier problem, and it is unexplored here: this program has only ever tested one retrieval method, flat cosine similarity, in one configuration family.

This survey is a **dense battery of small, mostly offline tests** across retrieval methods, query classes, and storage structures, run against preserved raw stores with known ground truth. It exists to produce evidence before an architecture is chosen for the deployment direction (continuous operation — long-lived agents and robots), not to validate one.

**It is not a study.** No component is under test, no bar produces a VALIDATED verdict, and its results cannot close a research question. It ranks candidates and generates hypotheses that a subsequent pre-registered study confirms or refutes.

**It does not occupy an arc slot.** The Track 1 lesson is explicit: a feasibility probe must never sit in a pre-registered component slot.

---

## 2. Why now — the evidence that motivates each candidate

| Observation | Candidate it motivates |
|---|---|
| Six planted facts are unreachable by formation at any parameter — but they are present, verbatim, in the raw store | Retrieval over the **raw store** rather than a distilled subset |
| Those six are rare exact phrases (`photophores`, `mantle margin`, `lead white`, `ultramarine glaze`, `marine snow`, `dual mandate`) whose component words are common — dense embeddings smear exactly this, lexical search finds it instantly | **BM25 / lexical**, and **hybrid fusion**. This also subsumes the phrase-rarity hypothesis on the retrieval side |
| Enumeration queries embed near topic centroids, and centroids sit nearest overviews — eleven consecutive failures | **Graph traversal** (enumeration is a walk, not a search) and **query-type routing** |
| Study 007/009 delivered all four domains and 10/17 facts and still scored 0.0; Study 002's pure STM reached a fact the LTM arms missed | **Context-matched raw retrieval** — is the tier earning its place, or just delivering more? |
| K retrieval collapsed to **zero** at turn 120 in Study 009 with ~120 episodes, where Study 002 had K=5 | **Diagnostic**: something is broken at small scale; tiering a broken primitive distributes the failure |
| `sqlite-vec` is brute force; deployment implies unbounded growth | **ANN indexing** and **progressive/tiered search** |
| Dense cosine already computes an edge weight between every pair of episodes at query time — it *is* a graph walk, just implicit, all-pairs, and single-hop | The real axis is **implicit/dense/single-hop vs explicit/sparse/typed/multi-hop**, not graph vs no-graph |
| Chained queries need multiple hops; cosine gets exactly one | **Multi-hop traversal** |
| Biological association is built by co-activation, not by extraction — and extraction is precisely where a graph would inherit formation's blindness | **Associative edge construction** from observed adjacency and co-retrieval: no NER, no LLM, no fabrication surface |
| Study 010's topic layer collapsed twelve domains into two | Edge types that require **no clustering**; topic-derived edges are unreliable and must be tested separately |
| Traversal depth is itself a latency tier — one hop is cheap and near, three hops is slower and further | **Depth-as-tier**: bounded latency per depth with unbounded reach, from one mechanism rather than a partitioning scheme bolted on |

---

## 3. Evidentiary rules (the discipline that keeps this honest)

Exploratory work finds something if you look long enough. Two tiers of evidence, with different status, both logged:

**Registered battery.** The tests in §6, their metrics, and their advancement thresholds are fixed in this document before any test runs. Only registered-battery results on **holdout** queries may advance a candidate.

**Open exploration.** Free experimentation is expected and encouraged — new methods, parameter sweeps, hunches. It is logged in `exploration_log.md` with what was tried and what was seen. **It cannot advance a candidate on its own.** An exploratory result that looks promising must be re-expressed as a registered test with a threshold and re-run on holdout before it counts. This is the mechanism by which a hunch becomes evidence rather than a story.

**Every result carries its class** (`registered` / `exploratory`) and its query set (`development` / `holdout`) in the results table. No exception.

---

## 4. Ground truth, development set, and holdout

**Corpora (read-only, hash-verified before and after):**
- **Study 010 stores — the primary test bed.** Both 1,000-turn arms provide a 986-episode pre-terminal-probe corpus, 290 distilled records, 12 domains, 36 plants, and 23 registered probes with locked answer keys. This is a far stronger corpus than the 120-turn stores and every tier should use it where the test permits. Study 010 is closed (STOPPED_AT_G2 with an exploratory continuation); its artifacts are read-only inputs here.
- Study 007 preserved raw and distilled stores (`study_007_full_001`) — retained for continuity with prior analyses and for the Tier 0 fidelity check.
- Study 009 Arm S and Arm L stores.
- Study 005 and 006 stores where a granularity comparison needs them.

**Two corpus scales are therefore available**, and results are reported per corpus. Where a finding holds at 120 turns and fails at 1,000 (or vice versa), that divergence is itself a result — Study 010 established that "settled at 120 turns" predicted nothing about behaviour at the new horizon.

**Temporal eligibility (binding):** registered holdout and development bakeoff queries may read only episodes from turns 1–111 on the 121-turn lineage and turns 1–986 on the 1,000-turn lineage. No method may index a terminal probe, its answer, the query itself, or any later episode. T0.3 is the sole exception: historical fidelity replay reconstructs each Q11/Q14 prompt from the exact episodes available immediately before that original turn. The harness must assert the cutoff before every retrieval and include eligible-turn bounds in each result row.

**Development set (burned).** On the 121-turn lineage, Q11, Q14, the existing targeted fixture, and the 17 rubric-critical facts have been used for diagnosis and parameter selection across four studies. On the 1,000-turn lineage, all 23 registered probes and their locked facts are burned. These are **development evidence only.** Results on them are reported and may not advance a candidate.

**Holdout sets (authored and locked before any test runs).** Because the 121-turn and 1,000-turn scripts contain different facts, each corpus receives a corpus-matched set of exactly 24 queries:
- **12 lookup queries** (single source-supported fact, one domain)
- **8 chained queries** (require two or more facts, ideally across turns or domains — e.g. relating a researcher to a finding to a value)
- **4 enumeration queries** (breadth across domains, phrased differently from all registered probes)
- Each with a locked answer key of required facts and source episode/turn provenance.

The two sets have the same class counts and evaluation schema but are not translations of one another. A query is run only against the corpus whose source facts it targets. This pre-lock correction is required to make the registered two-scale comparison meaningful; running a 121-turn fact query against the unrelated 1,000-turn script would certify corpus mismatch rather than retrieval quality.

**Disjointness requirement:** each holdout key must draw on source-supported content outside its corpus's burned development facts wherever the preserved corpus supports it. Where fact disjointness is impossible, the overlap is quantified and reported per query, and any candidate advancing on an overlapping query is flagged. Query wording is always new. A committed overlap matrix is part of the holdout lock.

The holdout set, its key, and its SHA are committed **before** the first test executes. Git order is the proof.

---

## 5. Leakage boundary (binding)

Answer keys are **measurement, never mechanism.**

No retrieval method, index builder, scorer, router, or graph constructor may read, import, or transitively depend on any answer key or rubric artifact. Enforced by the standing grep + import-graph audit with a planted violation, run at every tier.

**The graph constructor is the highest-risk component here** — it is the one candidate whose *build step* could trivially be tuned against the key. Its extraction must be domain-general and its inputs auditable.

---

## 6. The battery

Every test states its metric and its advancement threshold. Tests are small by design; the battery is dense.

### Tier 0 — Harness and ground truth
- **T0.1** Build the offline retrieval harness: load a preserved store at the registered temporal cutoff, embed a query, run a method, return a ranked candidate list, charge **exact serialized cost**, and evaluate against a key. Read-only against all source artifacts.
- **T0.2** Author and lock both corpus-matched holdout sets and their overlap matrix (§4).
- **T0.3** **Fidelity check:** the harness configured as Study 007's retrieval must reproduce that study's actual Q11/Q14 blocks **to the character.** *Gate: if it does not, no result from this survey is trustworthy — stop and fix.*

### Tier 1 — Reachability and the K-collapse diagnostic
- **T1.1 Presence.** On each preserved 121-turn raw store, are all 17 rubric-critical facts present verbatim? Report per fact, per store. *Expected yes; a no would relocate the problem to capture.* Report the analogous locked-fact presence inventory for Study 010 separately; its unrelated corpus is not scored against the 17-fact key.
- **T1.2 Reachability ceiling.** Across all methods in Tier 2 on the 121-turn lineage, does **any** configuration surface ≥14/17 facts (the Q11 threshold) within a 32,000-character budget from the raw store? *This is the single most consequential number in the survey: it determines whether breadth is impossible or merely unsolved.* Study 010 receives a descriptive corpus-matched ceiling with no substituted threshold.
- **T1.3 K-collapse diagnostic.** Deterministically re-embed Study 009 Arm S's stored episodes and the turn-120 query; dump the full similarity distribution; count candidates clearing 0.50 and those in [0.45, 0.50). Compare against Study 002 Condition C at the same turn. Report the most likely mechanism and the evidence that would confirm it. *Requires embedding calls; no generation. Explicitly authorized as bounded inference-adjacent work.*

### Tier 2 — Method bakeoff (offline, no inference)
Each method is run over the same stores and the same corpus-matched query sets.
- **M1** Dense cosine over **distilled LTM** — the current architecture, as baseline.
- **M2** Dense cosine over the **raw store**.
- **M3** **BM25 / lexical (FTS)** over the raw store.
- **M4** **Hybrid dense + sparse** with reciprocal-rank fusion. *Note the in-house precedent: SCOUT Phase 6.3 is hybrid FTS + pgvector with RRF.*
- **M5** Granularity comparison: episode-level vs span-level embeddings, holding method constant.
- **M6** Query expansion / multi-vector query (one broad query fanned into per-topic sub-queries), for enumeration.

**Metrics per method × query class:** fact recall@budget (primary), domain coverage, precision proxy (fraction of delivered characters that are key-bearing), delivered characters, latency, index build cost.

**Advancement threshold:** a method advances if, on **holdout**, it beats M1 on fact recall@budget for at least one query class **without** falling more than 10% below M1 on any other class.

### Tier 3 — Query-class behaviour and routing
- **T3.1** Per-class winner table: which method wins on lookup, on chained, on enumeration.
- **T3.2** **Routing value:** does an oracle router (best method per class, chosen with hindsight) beat the single best method overall? *This bounds what routing could ever buy. If the oracle gain is under 10%, routing is not worth building and that is a finding.*
- **T3.3** Feasibility of a **query-class classifier** built without the answer key — features from the query alone (length, interrogative form, domain-term count, embedding spread against topic centroids). Report accuracy on the holdout classes.

### Tier 4 — Graph structure and traversal depth

**Conceptual frame.** Dense cosine retrieval already computes an edge weight between every pair of episodes at query time. It is a graph walk — implicit, all-pairs, single-hop, untyped. The question this tier asks is not *graph or no graph*, but whether an **explicit, sparse, typed, multi-hop** structure beats the implicit one on query classes where a single hop is structurally insufficient: enumeration (a walk over topic-level nodes) and chaining (multi-hop by definition).

The tier splits by construction method, because construction is where the risk lives and the two methods carry entirely different risk profiles.

*(Grounding: this converges with spreading-activation models in cognitive science — Collins & Loftus, 1975. Convergence and grounding, arrived at independently from this program's failure data; not derivation.)*

#### Tier 4A — Associative construction (cheap, ungated, runs early)

Edges built from **observed co-activation**, not from inferred semantics. Nothing is extracted, so nothing can be fabricated, and there is no quality gate to fail — only a usefulness question.

- **E1 Adjacency edges.** Episodes contiguous in the conversation. Free; already in the store.
- **E2 Co-retrieval edges.** Episodes that appeared in the same constructed context on any turn, weighted by co-occurrence count. **Recoverable directly from the preserved retrieval logs** — this is history the program has been writing since Study 004 and has never used as structure.
- **E3 Similarity edges, thresholded and sparsified.** The implicit graph made explicit and pruned to top-k neighbours per node — the control that isolates whether sparsity and typing help, or whether cosine already had everything.
- **E4 Topic-derived edges.** Shared canonical topic. **Reported separately and treated as unreliable**: Study 010's topic layer collapsed twelve domains into two, so any E4 result on that corpus reflects a known-broken partition. E1–E3 require no clustering and are the viable core.

**T4A.1** Build each edge type and their combinations over both corpora. Report node/edge counts, density, build time, and **per-episode incremental update cost** — the number that determines maintainability in continuous operation.
**T4A.2** Traversal on all three query classes at depths 1, 2, 3. Same metrics as Tier 2. Enumeration and chained queries are the tests that matter; lookup is the sanity check.
**T4A.3 Depth-as-tier.** Measure recall and latency at each traversal depth. **This is the direct test of progressive search as a single mechanism** rather than a recency partition bolted on: does depth 1 give hot-tier latency, and does depth 3 reach material that flat retrieval misses? Report the recall/latency curve per depth.
**T4A.4 Old-but-required.** The failure mode any tiering scheme creates: measure whether depth-limited traversal misses facts that are old but required. Compare against the recency-partitioned scheme in Tier 5.

**Advancement threshold:** as Tier 2 (beat the flat baseline on ≥1 query class on holdout without falling >10% below on another), plus an update cost that does not grow superlinearly with store size.

#### Tier 4B — Extraction-based construction (gated, expensive, runs last)

Semantic nodes and typed relations. Retained because it is the version that could serve genuinely novel query types — but it is the version that inherits formation's blindness, and it runs last because it is most likely to be closed by its own gate.

**T4B.1 Extraction quality.** spaCy vs rule/pattern vs LLM extractor, measured against a hand-labelled ~50-span sample covering all domains and **all six known-unreachable facts**. *Known prior: spaCy returned zero entities for the* Vampyroteuthis infernalis *span. An extractor that cannot see those six cannot build a graph that reaches them.*
**T4B.2 Fabrication audit (LLM extractor only).** Fraction of nodes and edges unsupported by source text. **Gate: >5% unsupported edges does not proceed.** A wrong edge corrupts traversal for every future query, which makes structural fabrication strictly worse than a fabricated retrieved span.
**T4B.3 Traversal and cost.** Only for extractors clearing both gates. Same protocol as T4A.2–4.
**T4B.4 Comparison.** Does extraction-based traversal beat associative traversal by enough to justify its construction cost and fabrication risk?

*If all extractors fail their gates, record the extraction-based graph direction as **closed with a negative result** and stop. Tier 4A stands on its own.*

### Tier 5 — Scale, budget, and progressive search
- **T5.0 Budget multiples.** One fixed retrieval policy at **1×, 2×, 5×, and 10×** the 32,000-character budget, on both corpora. *Motivation: at 1,000 turns the LTM block already consumed 31,991 of 32,000 characters at Q13 and 31,847 at Q14 — the budget was saturated, because episode rendering expands each record far beyond its span. At the next order of magnitude the store does not deliver more, it competes harder for the same window.* This measures how much of the breadth result was budget headroom rather than method.
- **T5.1** ANN index (HNSW and/or IVF-PQ) vs brute force: recall@k against exact search, query latency, build time, memory, at **120 / 1,000 / 10,000 / 100,000** episodes. Synthetic episodes may pad the corpus; label every synthetic-padded result.
- **T5.2 Recency-partitioned progressive search.** Hot/warm/cold tiers with early termination. Latency per tier and — critically — **miss rate for old-but-required facts**, the failure mode time-tiering creates.
- **T5.3 Orthogonal-axis mitigation.** Re-run T5.2 with topic-indexed and pinned-rule tiers alongside time tiers. Does an age-independent axis recover the old-but-required misses? *Caveat: the topic axis is known-broken on the Study 010 corpus; the pinned-rule store also persisted zero rules in both arms. Both must be validated before they can serve as tiers, and that validation is part of this test.*
- **T5.4 Tiering-scheme comparison.** Recency partitioning (T5.2/5.3) vs **traversal depth (T4A.3)** as the mechanism for progressive search. Same latency and miss-rate axes, so the two schemes are directly comparable. *If depth-as-tier matches or beats partitioning, the deployment architecture needs one mechanism instead of two.*

### Tier 6 — The one live test
- **T6.1 Context-matched raw retrieval.** Pure STM over the raw store, widened (N, K, and budget) to match Study 009 Arm L's delivered context, same seed, same script, scored on the locked rubric under `PROTOCOL_scoring_integrity.md`.
  *This is the only test requiring generation, and it decides the architecture's premise:* if it reaches ~12.0, **LTM's advantage was bulk delivery, not selection**, and the store-everything/retrieve-better direction is validated in a single run. If it stalls near 9.0, the LTM tier is doing real work and that is worth knowing before it is dismantled.
  Run under full study protocol — seeded, guarded launcher, blinded scoring, scores before mechanism logs — because unlike the rest of the battery it produces a score that will be compared to committed scores.

---

## 7. Decision rules

**What the survey outputs:** a ranked candidate list with, for each candidate, its evidence class, its query-set provenance, and its cost profile — plus a written recommendation for the next pre-registered study.

**A candidate is recommended for a confirmatory study only if:**
1. It clears its Tier 2 advancement threshold **on holdout**, and
2. Its cost profile is viable at the projected deployment scale (Tier 5), and
3. It requires no answer-key access (leakage clean), and
4. Its result is registered-class, not exploratory-only.

**Pre-registered interpretation of the pivotal outcomes:**
- **T1.2 ≥ 14/17 reachable** → breadth is an engineering problem; the next study is a retrieval-method study, and **Q11 becomes usable as a bar again**.
- **T1.2 < 14/17 by any method** → breadth is not retrievable from this store at this budget; the constraint is capture or budget, not method, and the next study must address one of those. **Q11 stays retired as a bar.**
- **T6.1 ≈ 12.0** → the LTM tier's benefit was volume; recommend collapsing to one store with better retrieval.
- **T6.1 ≈ 9.0** → the LTM tier does real work; the store-everything direction needs revision before it is adopted.
- **T3.2 oracle gain < 10%** → do not build routing.
- **T4A beats flat retrieval on enumeration or chaining** → an explicit sparse graph earns a confirmatory study, built on *observed* edges with no extraction step and no fabrication surface.
- **T4A does not beat flat retrieval** → the implicit all-pairs graph already had everything; explicit structure is not the lever, and Tier 4B should not be attempted.
- **T4A.3 depth curve matches or beats T5.2 partitioning** → recommend depth-as-tier as the single progressive-search mechanism, retiring the separate partitioning scheme.
- **T4B.1/T4B.2 fail for all extractors** → the extraction-based graph direction closes with a negative result. Tier 4A stands independently.
- **T5.0 shows breadth collapsing above 2× budget** → the Study 010 breadth success was budget headroom, not method, and the deployment architecture must solve selection-at-saturation before scale.

---

## 8. What would falsify the whole direction

Stated in advance so the survey can return a null:

If no method — dense, lexical, hybrid, associative-graph, or extraction-graph — materially beats flat cosine over the raw store on holdout, then **retrieval method is not the lever**, and the program's constraint lies in capture, budget, or the query itself. Given T5.0's saturation motivation, budget is the leading alternative and the survey should say so. That outcome is a legitimate and valuable result, and it would redirect the deployment architecture toward budget and context-window strategy rather than retrieval sophistication.

---

## 9. Limitations

- One script, one domain structure, four topics. Findings characterize this corpus, not retrieval in general.
- Synthetic padding at Tier 5 tests index behaviour, not real conversational structure at scale.
- The holdout set is authored by the same people who know the failure modes; disjointness from the development set is enforced where possible and reported where not.
- T6.1 is a single seeded run per arm — the same n=1 limitation every study in this program carries.
- Chained-query evaluation depends on the holdout's chain design; a poorly chained query set would understate graph traversal's advantage.
- Latency numbers come from this hardware and this store; they rank options, they do not predict production.

---

## 10. Locked Decisions

1. **Holdout size and disjointness.** Lock exactly 12 lookup, 8 chained, and 4 enumeration queries per corpus: 24 for the 121-turn lineage and 24 for the 1,000-turn lineage. T0.2 locks the keys, source provenance, SHA-256 hashes, and per-query overlap matrix before the first registered test.
2. **Edge types for Tier 4A.** Retain E1 adjacency, E2 co-retrieval, and E3 sparsified similarity; report E4 topic-derived separately as unreliable. E2 is available: the preserved runs contain per-turn N and K episode IDs, LTM selection logs where applicable, and complete constructed prompts for all 121 and 1,000 turns. Reconstruction must use those exact records and may not infer missing co-occurrences.
3. **LLM extractor for T4B.1.** Test the carried `Qwen3.6-27B-UD-Q6_K_XL.gguf` from Hugging Face snapshot `5cb35eb3dcbf52dbce5f87dbc64df6aaffadcace`, with seed 5005, one slot, and speculative decoding disabled. Hash the model file and record the server build before extraction. Its use is acceptable only behind T4B.2's >5% unsupported-edge stop gate; a pass permits a later study, not adoption.
4. **Scale ceiling for Tier 5.** Lock 100,000 episodes as the maximum synthetic-padded scale. No higher scale is part of the registered battery.
5. **T6.1 widening rule.** Match Study 009 Arm L on exact serialized delivered retrieval characters, after deduplication, not on N/K counts. Lock the calibrated widening settings in a standalone settings artifact committed before the guarded live run; calibration may use development turns and may not use live answers.
6. **Survey execution budget.** Run the full registered battery. The priority order in the source draft is contingency guidance only and does not authorize omission.

---

## Appendix

- Preserved stores: `experiments/study_005..010/runs/`
- Development facts: per-study `q_facts_key.md` (17 rubric-critical)
- Unreachable six: `art_pigment`, `art_patron_role`, `monetary_taylor`, `monetary_fed`, `marine_photophores`, `marine_feeding`
- Rubric (development only here): `experiments/study_002/rubric_filled.md`
- Standing rules: `PROTOCOL_scoring_integrity.md`, `AGENTS.md`
- Survey path: `experiments/surveys/retrieval_bakeoff/`
