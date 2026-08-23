# TC-005 Implementation Document — relevance efficiency under a half-budget

**Document type:** Prospective implementation design  
**Status:** `DESIGN ONLY — NOT PRE-REGISTERED — NO IMPLEMENTATION OR RUN AUTHORIZED`  
**Date:** August 23, 2026  
**Arc:** Tier-cost follow-on; repurposes the unregistered clustering-cost placeholder  
**Predecessors:** Retrieval bakeoff M2/M3/M4, NF-004, HH-002, TC-001 through TC-004  

---

## 0. Decision in plain language

TC-005 will determine which already-carried global relevance strategy should
feed TC-007's protected-spread allocator:

1. dense embedding cosine;
2. sparse lexical BM25; or
3. dense-plus-sparse reciprocal-rank fusion (RRF).

Every arm receives the same LoCoMo adjacent-turn-pair candidates and uses the
same exact renderer and skip-on-overflow packer. The primary operating points
are **8,000 and 16,000 characters**: the relevance route's actual half-shares
inside TC-007's 16,000- and 32,000-character total contexts. Full-budget
16,000- and 32,000-character runs are secondary continuity anchors. Only the
order offered to the packer changes.

This is a comparison of retrieval ranking strategies, not merely alternative
"semantic similarities." BM25 is lexical. With normalized vectors, cosine,
dot-product rank, and Euclidean-distance rank are mathematically equivalent in
exact arithmetic, so testing those three names would not create three objective
arms. Preflight found that changing the numerical implementation can still move
near-ties: float64 dot/Euclidean agreed on 871/871 real queries, while the
carried float32 matrix multiply agreed with them on 868/871. That is a
precision/tie-break change, not a fourth retrieval objective, and is out of
scope.

The former TC-005 clustering-latency proposal was design-only and is retired
before registration. Large-store latency, adaptive budgets, and enterprise
scaling move to a later design after the retrieval architecture earns a place.

## 1. Question

> Holding candidates, candidate granularity, query, renderer, packer, budget,
> evidence measurement, and dense vectors fixed, does carried BM25 or carried
> dense-plus-sparse RRF preserve more direct-question evidence than the current
> dense-cosine order when relevance is limited to TC-007's half-budget?

TC-005 does not test coverage, protected allocation, recency, chunking,
reranking by an LLM or cross-encoder, query expansion, or a new embedder.

## 2. Carried ranking strategies

| Arm | Ordering | Source |
|---|---|---|
| `A_DENSE` | Adjacent-turn pairs by descending query/candidate cosine; conversation order breaks ties | TC-001 standing flat arm |
| `A_BM25` | Global BM25 rank using Unicode casefold tokenization, `k1=1.2`, `b=0.75` | Retrieval bakeoff M3 |
| `A_HYBRID` | One-based RRF of `A_DENSE` and `A_BM25`, constant 60 | Retrieval bakeoff M4 |

The BM25 tokenizer and score formula, and the RRF constant and score formula,
are imported or reproduced by exact identity from the committed bakeoff
implementation. TC-005 does not tune them on LoCoMo. The bakeoff's final
candidate-id tie-break is not silently assumed suitable for a new corpus: a
common stable conversation-order tie-break for all three LoCoMo arms must be
verified in exploration and locked before outcomes are generated. The exact
prior implementation still runs unmodified for the reproduction anchor.

All arms rank the full candidate store. There is no threshold, top-k pool cut,
topic floor, recency insertion, coverage reservation, or post-ranking reorder.

## 3. Corpus, unit, and budgets

- **Corpus:** the same four LoCoMo development conversations and resolved
  question records used by TC-001 through TC-004.
- **Unit:** the same 1,365 adjacent-turn pairs, with the same content identities
  and evidence mapping.
- **Primary budgets:** 8,000 and 16,000 characters, corresponding to the
  relevance route's 50% operating points in TC-007.
- **Secondary anchors:** 16,000 and 32,000 characters with relevance allowed to
  consume the full TC-007 total budget.
- **Cost:** exact serialized characters including wrappers and separators,
  using the carried skip-on-overflow packer.

The half-budgets test the mechanism the successor actually needs: whether a
better ordering can make relevance more character-efficient under protection.
The full-budget anchors preserve direct continuity with the tier-cost arc. None
claims to be an optimal production budget. Token-relative and adaptive
budgeting remain separate enterprise-scale questions.

## 4. Endpoints and eventual selection rule

The primary endpoint is question-level **complete required-evidence delivery on
the targeted population at 8,000 and 16,000 characters**. This directly tests
whether relevance can do more with its protected half. Any-evidence delivery,
the combined eligible population, the breadth population, and the 16,000- and
32,000-character full-budget anchors are secondary. Every comparison is paired
by stable question identity and reports gains, losses, ties, exact delivered
characters, candidate count, and the best and worst rank of every required
evidence unit.

Results are also reported separately for the two TC-007 populations:

- targeted questions whose evidence is confined to one adjacent-turn pair in
  one session; and
- breadth questions whose evidence spans at least three sessions.

Preflight resolved **704 targeted**, **44 breadth**, **120 other eligible**, and
**3 ineligible** unique questions. The pre-registration must lock a reachable,
multiplicity-corrected rule for
which single ordering TC-007 inherits. Selection must be driven by targeted
complete-evidence delivery at the two half-budgets; a full-budget win alone
cannot select a strategy that is inefficient at its actual TC-007 operating
point. The rule must also include a combined/full-budget regression guardrail
and a fallback if neither treatment clears dense. No winner, guardrail value, or
fallback is selected in this design document.

## 5. Required diagnostics

For every question and arm, record:

- the ordered candidate content identities and ranking digest;
- dense cosine, BM25 score, dense rank, sparse rank, and fused rank;
- exact serialized candidate and payload cost;
- delivered and skipped identities with skip reason;
- required-evidence ranks and delivered evidence identities; and
- pairwise rank disagreement among the three arms.

Report full distributions rather than only pooled means. In particular,
separate exact-identifier/number questions where lexical rank may help from
paraphrased questions where dense rank may help, using question-visible rules
locked before treatment outcomes are opened.

## 6. Preflight Part 1 — exploration before registration

Exploration is committed separately and may change this design before any bar
or disposition is locked.

1. **Behavioral identity:** run all three carried rankers on real LoCoMo traces
   and state in one falsifiable sentence what each orders.
2. **Name-to-behavior:** prove dense is descending cosine, BM25 is the carried
   sparse formula, and hybrid is the carried RRF rather than score averaging.
3. **Distribution:** report score and rank distributions, pairwise rank
   correlations, evidence ranks, delivered characters, and budget binding for
   every question at the three unique budgets, separating the 8k/16k
   half-budget operating roles from the 16k/32k full-budget anchor roles.
4. **Degenerate states:** exhibit all-zero BM25 queries, dense ties, RRF ties,
   complete agreement, maximum disagreement, oversized candidates, and
   everything-fits cases on real traces where they exist; construct positive
   controls for states absent from the corpus.
5. **Identity tests:** demonstrate the exact-arithmetic dot/Euclidean identity,
   quantify carried-float32 near-tie order drift, and keep numerical precision
   variants from entering as fake objective arms.
6. **Prior-transfer check:** reproduce the committed retrieval-bakeoff M2/M3/M4
   rankings with the unmodified prior implementation and the TC-001 dense
   payload before producing LoCoMo treatment output; separately enumerate every
   LoCoMo order position changed by the common tie-break.
7. **Reachability:** establish that both a sparse/hybrid gain and a dense win are
   mechanically possible at each half-budget, that the eventual selection bar
   and regression guardrail can fire, and that the full-budget anchors are not
   being used to select a half-budget loser.

## 7. Preflight Part 2 — mandatory checklist

| Check | Required evidence before registration/run |
|---|---|
| **PF1 Inputs exist** | Hash and count the LoCoMo store, questions, evidence mapping, vector cache, renderer, packer, and carried BM25/RRF source |
| **PF2 Mechanism identity** | Real-trace evidence for dense, sparse, and RRF ordering, including exact-arithmetic metric identity and measured float-implementation residuals |
| **PF3 Gate ordering** | G0 must finish and commit before treatment outcomes can be generated or opened |
| **PF4 Thresholds achievable** | Every selection branch, half-budget directional bar, and full-budget regression guardrail shown reachable and failable before locking |
| **PF5 Stable keys** | Question and candidate content hashes only; no generated ids, timestamps, or paths |
| **PF6 Reproduction anchor** | Exact TC-001 dense payload plus committed bakeoff M2/M3/M4 ranking identities and digests |
| **PF7 Absorbing state** | No feedback; prove every ranker is a pure function of frozen inputs and is nonconstant on the intended population |
| **PF8 Ablation length** | Full offline population; state that it cannot establish reader use, unseen-corpus transfer, or behavior beyond these store sizes |
| **PF9 Surrogate audit** | Higher lexical overlap, cosine, fused score, candidate count, or any-evidence delivery cannot substitute for complete labelled evidence |
| **PF10 Live requirement** | Availability chooses a retrieval input for TC-007; it does not authorize production or claim a reader benefit |

## 8. Scope and relationship to TC-007

TC-005 is model-free under this programme's terminology: embedding calls are
allowed, LLM/generative calls are not. Retained read-only dense caches are
preferred, and every cache miss and call shape must be reported.

TC-005 freezes one relevance order specifically for operation at 8,000 and
16,000 characters. TC-007 then compares that same order with the full 16,000 or
32,000 characters against the same order receiving its 50% share beside a
separately bound spread strategy. This sequencing keeps relevance quality and
budget allocation from becoming two simultaneous changes.

TC-005 cannot establish reader accuracy, an optimal budget, adaptive stopping,
large-store latency, or enterprise-scale cost. Those claims require separate
registered work.
