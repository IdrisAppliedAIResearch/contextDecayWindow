# TC-007 Implementation Document — protected coverage beside ranked retrieval

**Document type:** Prospective implementation design  
**Status:** `DESIGN ONLY — NOT PRE-REGISTERED — NO IMPLEMENTATION OR RUN AUTHORIZED`  
**Date:** August 23, 2026  
**Arc:** Tier-cost follow-on; this document does not modify the locked TC-001 through TC-004 registrations  
**Predecessors:** HH-002, TC-001B, TC-003, TC-004, EC-002, IC-001, E005, NF-007, LV-001  
**Planned ranked input:** the single ordering frozen by TC-005

---

## 0. Decision in plain language

Test one fixed-budget context builder with two parallel consumers:

1. **ranked relevance retrieval** takes candidates in the single order frozen
   by TC-005; and
2. **coverage retrieval** has protected character capacity that ranked retrieval
   cannot consume.

Both arms draw from the same store, use the same renderer and exact character
accounting, and deduplicate before serialization. Coverage owns half of each
budget. If it cannot spend that capacity, the unused characters return to ranked
retrieval.

The study asks whether protected spread is measurably better than unprotected
ranked retrieval at the tier-cost arc's historical **16,000- and
32,000-character budgets**. Relative, token-based, and adaptive budgets are
deferred to later enterprise-scale work rather than mixed into the allocator
test.

## 1. Why TC-007 exists

HH-002's 79.09% arm was not the deployed tiered read path. It ranked every
adjacent-turn pair by cosine and packed a 16,000-character context. Against the
published RAG arm, it also returned many more and much smaller retrieval units
than one 500-token chunk. That result supports localized, broad semantic
retrieval on targeted questions; it does not establish a coverage mechanism.

The later tier-cost studies isolate the problem:

- TC-001B found that relevance-ranking the K tier recovered almost the entire
  flat-arm result: 748 complete-evidence questions versus 749 for flat.
- TC-003's equal-share dual floors scored 718 versus 748 for unrestricted
  ranked retrieval. On LoCoMo's mostly targeted questions, reservation cost more
  complete-evidence deliveries than it gained.
- The internal breadth probe requires facts from weakly cued domains. Pure
  relevance ranking can concentrate the budget in the best-cued region even
  when evidence from several regions is required.
- The deployed stack gives coverage no reliable capacity: earlier tiers can
  consume the budget before coverage serializes anything useful.

These findings do not imply that spread is unnecessary. They imply that the
relevant comparison is **ranked relevance retrieval alone versus the same ranked
retrieval with a protected, auditable coverage allowance**, measured separately
on targeted and breadth workloads.

## 2. The single new component

The one new component is a **two-consumer fixed-budget allocator**. It accepts:

- a relevance candidate stream already sorted in TC-005's frozen order;
- a coverage candidate stream in the frozen coverage selector's own order;
- one total serialized-character budget;
- a protected coverage share fixed at 50%; and
- stable candidate content hashes for cross-stream deduplication.

It returns one rendered context and an attribution report naming, for every
delivered candidate, the proposing route, the paying allowance, exact serialized
cost, and whether it was admitted during protected or returned-capacity fill.

The allocator does not change candidate formation, embeddings, relevance scores,
coverage scores, cluster assignments, rendering, or the drop policy. If any of
those must change, TC-007 stops because the test would contain a second new
component.

### 2.1 Allocation contract

TC-007 evaluates `B ∈ {16_000, 32_000}` exact serialized characters. At every
budget the protected coverage allowance is `C = floor(B / 2)` and ranked
retrieval begins with the other half. Preflight must lock how the shared wrapper
cost is charged before candidate outcomes are generated.

1. Produce both candidate streams before packing.
2. Deduplicate by stable content identity, not generated episode id. A candidate
   proposed by both routes exists once in the serialized output.
3. Coverage may spend up to `C` exact serialized characters on coverage-owned
   candidates.
4. Ranked retrieval may spend the remaining `B - coverage_spend` characters,
   in TC-005's frozen order.
5. If coverage cannot spend all of `C`, its slack is immediately available to
   ranked retrieval.
6. The combined payload must never exceed `B` after wrappers and separators.
7. Reversing internal service order must not change the delivered identities,
   ownership, serialized payload, or accounting report.

Step 5 makes the protection a floor for available qualifying coverage, not a
permanent empty reservation. Step 7 prevents the old fixed-fill-order pathology
from reappearing behind a new name.

### 2.2 Ownership of shared candidates

TC-003 showed that floors remove service-order dependence but introduce
ownership-order dependence: a shared candidate can charge either allowance.
TC-007 must not silently inherit that ambiguity.

Before pre-registration, exploration must enumerate shared candidates and test
the locked ownership rule on real traces: **ranked retrieval owns every shared
candidate and its cost is charged to ranked retrieval**. Coverage can spend its
half only on candidates not already owned by ranked retrieval. This aligns
accounting with slack return: coverage is protected when it contributes
distinct spread, while unused coverage characters return to ranked retrieval.
Exploration must still
demonstrate that the rule cannot manufacture a gain merely by relabelling hits.

## 3. Arms

| Arm | Description | Purpose |
|---|---|---|
| `A_RANKED` | Every candidate in TC-005's frozen order; exact matched-budget packing | Frozen control |
| `A_PROTECTED_A3` | Frozen ranked retrieval plus 50% protected capacity for the carried A3 relevance-plus-cluster-diversity selector | Treatment 1 |
| `A_PROTECTED_FACILITY` | Frozen ranked retrieval plus 50% protected capacity for the committed E005 facility-location selector | Treatment 2 |
| `A_SHAM` | Same accounting boundary and wrapper cost as treatment, but no coverage-selected admissions | Cost/control check |

All arms receive identical candidates, vectors, query, renderer, character
accounting, total budget, and exact-cost packer. `A_SHAM` prevents
wrapper or accounting overhead from being credited to coverage. A3 and facility
location are both carried mechanisms, not newly tuned selectors; the allocator
is TC-007's single new component.

No recency arm is included. Adding recency would change a second architectural
lever and would make the protected coverage contrast uninterpretable.

## 4. Workloads and endpoints

TC-007 requires two labelled workloads because aggregate accuracy can hide a
trade between different retrieval obligations.

### 4.1 Targeted workload — selected definition

Use the committed LoCoMo question population whose complete evidence is confined
to one adjacent-turn pair within one session. These are the cleanest cases where
the query supplies a localized semantic target. Exact eligibility rules, counts,
and content hashes are produced in exploration and locked before outcomes are
opened.

Primary measurements:

- any required evidence delivered;
- complete required evidence delivered;
- gains, losses, and ties against `A_RANKED`; and
- exact characters and candidate counts by route.

### 4.2 Breadth workload — selected definition

Use committed LoCoMo questions whose required evidence spans at least three
distinct sessions. Session membership comes from corpus structure and required
evidence identities come from the existing labels; neither is exposed to the
retrieval mechanism. This operationalizes breadth as multi-location obligation
without asking a rater to infer whether a question “sounds broad.”

Primary measurements:

- number of required facts delivered;
- number of required domains represented;
- complete breadth-set delivery;
- gains, losses, and ties against `A_RANKED`; and
- concentration of delivered characters by session and cluster.

The internal Q11 17-fact/four-domain probe is retained as a positive control and
descriptive mechanism trace, not as the inferential population. If exploration
finds too few eligible three-session LoCoMo questions for a reachable bar,
TC-007 stops or is registered as characterization-only; the definition is not
relaxed after counts are known.

### 4.3 Joint decision

The architecture succeeds only if at least one protected treatment is
**measurably better than `A_RANKED`**, not merely more diverse. The binding
endpoint is complete required-evidence delivery over the combined eligible
population, paired by question at each of the two character budgets. Breadth
and targeted results are also reported separately so an aggregate gain cannot
hide which workload paid for it.

“Measurably better” means a positive paired net exceeding a pre-registered,
mechanically reachable instrument band with multiplicity handled across two
treatments and two budgets. Preflight Part 1 supplies the discordant-pair
counts needed to set a reachable band; it may not choose the winning budget or
selector after opening treatment outcomes. A breadth gain accompanied by a
larger targeted loss is not a pass because it cannot beat `A_RANKED` on the
combined binding endpoint.

## 5. Required attribution and diagnostics

Every question-level record must include:

- stable question and candidate content hashes;
- ordered candidate identities from both routes;
- intersection of the two proposed sets;
- locked ownership of every shared candidate;
- exact wrapper, separator, candidate, and total costs;
- exact character limit, protected allowance, coverage spend, slack returned,
  and ranked-retrieval spend;
- delivered and dropped identities with reasons;
- evidence identities and domains delivered by each route; and
- byte digest of the final payload.

Aggregate counts without these records are insufficient. A result must reveal
whether coverage added distinct evidence or merely claimed evidence ranked
retrieval would already have delivered.

## 6. Preflight Part 1 — exploration before registration

Exploration is committed separately and may change this design before any bars
or parameters are locked.

1. **Behavioral identity.** Run the frozen ranked path and coverage
   selector on every intended question. State in one falsifiable sentence what
   each proposes and what the allocator admits.
2. **Name-to-behavior.** Demonstrate that the ranked path exactly reproduces
   TC-005's frozen order, coverage increases a defined spread property,
   protection actually binds, slack actually returns, and dedup emits shared
   content once.
3. **Full distributions.** Report candidate overlap, protected spend, binding
   rate, slack, domain/cluster concentration, delivered evidence, and payload
   cost per question—not only means or medians.
4. **Degenerate states.** Exhibit questions with no coverage candidates, all
   candidates shared, coverage candidates too large for the allowance, ranked
   exhaustion, and a budget smaller than the wrapper cost.
5. **Ownership sensitivity.** Permute route ownership for shared candidates and
   measure every changed delivery. If the proposed policy makes the result depend
   materially on arbitrary ownership, registration stops or names that residual.
6. **Positive controls.** Include at least one constructed case where protected
   coverage adds unique breadth evidence and one where protection displaces the
   only targeted evidence. Both outcomes must be reachable before bars are set.
7. **Budget characterization.** Characterize the locked 16,000- and
   32,000-character budgets and the locked 50/50 initial split. Prove that both
   consumers can bind and measure saturation at each budget.

## 7. Preflight Part 2 — mandatory checklist

| Check | Required evidence before registration/run |
|---|---|
| **PF1 Inputs exist** | Hash and count every store, vector cache, question, evidence label, session label, renderer, character counter, and packer consumed |
| **PF2 Mechanism identity** | Committed real-trace exploration proving ranked order, coverage spread, protection, returned slack, and dedup behavior |
| **PF3 Gate ordering** | A run entry point that executes G0 and exits before opening treatment outcomes; git and run-header assertions |
| **PF4 Thresholds achievable** | Mechanical reachability of a positive paired net over `A_RANKED` after multiplicity correction, including both positive controls and all four treatment-budget cells |
| **PF5 Stable keys** | Content hashes for questions and candidates; no UUID, timestamp, or path identity |
| **PF6 Reproduction anchor** | `A_RANKED` reproduces TC-005's committed frozen payload digest and count before treatment output is generated |
| **PF7 Absorbing state** | No feedback is planned; prove allocator output is a pure function of frozen inputs. If feedback appears, run an intended-length real trace |
| **PF8 Ablation length** | Full-population offline replay where labels permit; otherwise state what the sampled breadth set cannot detect. No live 120-turn run without a passing 35-turn ablation |
| **PF9 Surrogate audit** | Record that domain/cluster spread can rise without required evidence, evidence can arrive without being used, and ownership can relabel rather than add value |
| **PF10 Live requirement** | State that availability is not an answer verdict; TC-006 or a separately registered live reader study is required before adoption |

## 8. Gates and execution order

1. Commit exploration artifacts.
2. Author resolves the open decisions in §11.
3. Commit `TC_007_PRE_REGISTRATION.md` alone and record its SHA-256.
4. Implement allocator and tests without modifying carried subsystems.
5. **G0:** input hashes, leakage boundary, reproduction anchor, service-order
   invariance, ownership policy, exact budget, dedup, positive controls, and
   reachable bars all pass.
6. Run the offline targeted and breadth populations.
7. Commit question-level outputs before opening aggregate mechanism analysis.
8. Report availability only. Do not infer reader benefit or adoption.

No LLM calls are required for the offline study. Embedding calls are permitted
under this programme's terminology, but retained read-only caches are preferred;
cache misses and embedding call shape must be reported.

## 9. What TC-007 can and cannot establish

**Can establish:** whether either of two protected coverage mechanisms improves
labelled evidence delivery relative to the same frozen ranked retriever at
16,000 and 32,000 characters, and whether the change differs between
targeted and breadth questions.

**Cannot establish:**

- that a reader notices or correctly uses delivered evidence;
- that cluster or domain coverage is itself useful without evidence labels;
- the best coverage share outside the locked 50/50 design;
- transfer to an unseen corpus;
- production latency or budget selection at enterprise store sizes; or
- superiority of the current clustering algorithm over other spread mechanisms.

## 10. Re-evaluation of TC-005 and TC-006

### TC-005 — repurposed as the ranked-retrieval comparison

TC-005 now compares the carried dense-cosine, BM25, and dense-plus-sparse RRF
orders over identical LoCoMo candidates and historical character budgets. It
freezes one ranked stream before TC-007 changes allocation, preventing ranker
quality and protected spread from becoming simultaneous interventions.

The former clustering-cost proposal was not registered and is retired. Its
enterprise-scale latency question remains open but no longer occupies TC-005.

### TC-006 — retain; its necessity increases

TC-006 asks whether a reader uses evidence that offline retrieval delivers.
TC-007 intentionally stops at availability, and breadth is especially vulnerable
to the surrogate failure “more domains present” while the answer remains no
better.

Disposition:

- **Continue TC-006.** It is required before any TC-007 adoption claim.
- Use **frozen TC-007 contexts** as TC-006's intended contrast, but authorize that
  change only through TC-006's own future pre-registration; do not silently alter
  its roadmap design.

The resulting preferred order is **TC-005 → TC-007 → TC-006**. TC-005 freezes
ranking, TC-007 tests allocation, and TC-006 tests reader use. Each still
requires its own Preflight and standalone pre-registration.

## 11. Author decisions recorded August 23, 2026

1. **Budgets:** 16,000 characters primary and 32,000 characters secondary;
   relative/token budgeting is deferred to later enterprise-scale work.
2. **Ranked route and allocation:** TC-005 freezes the ranked retrieval order;
   TC-007 gives it 50% beside 50% protected coverage, with unused coverage
   returned to ranked retrieval.
3. **Coverage mechanisms:** test both carried set-level selectors: A3
   relevance-plus-cluster-diversity and E005 facility location.
4. **Shared ownership:** ranked retrieval owns and pays for candidates proposed
   by both.
5. **Breadth population:** existing labelled questions requiring evidence from
   at least three sessions; internal Q11 remains a descriptive positive control.
6. **Targeted population:** existing labelled questions whose evidence is
   confined to one adjacent-turn pair in one session.
7. **Success:** a protected treatment must be measurably better than
   unprotected ranked retrieval on combined complete-evidence delivery; the
   exact reachable band is locked after exploration and before treatment
   outcomes.
8. **Reader validation:** TC-006 will use frozen TC-007 contexts, subject to its
   own standalone pre-registration.

The next work is TC-005's empirical Preflight Part 1 and standalone
pre-registration. TC-007 then inventories its two selected populations,
reproduces TC-005's frozen order, verifies character-budget behavior, measures
overlap and ownership effects, and proves its eventual statistical bar is
reachable. Neither study is runnable before its own committed Preflight and
standalone pre-registration.
