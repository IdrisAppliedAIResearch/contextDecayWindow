# TC-007 Implementation Document — efficient relevance beside protected spread

**Document type:** Prospective implementation design  
**Status:** `PREFLIGHT PASSED — NOT YET PRE-REGISTERED — NO RUN AUTHORIZED`  
**Date:** August 23, 2026  
**Arc:** Tier-cost follow-on; this document does not modify the locked TC-001 through TC-004 registrations  
**Predecessors:** HH-002, TC-001B, TC-003, TC-004, EC-002, IC-001, E005, NF-007, LV-001  
**Planned relevance input:** the single ordering frozen by TC-005

---

## 0. Decision in plain language

Test one fixed-budget context builder with two role-bound consumers:

1. **relevance retrieval** uses the single strategy frozen by TC-005 for direct,
   well-cued questions; and
2. **spread retrieval** uses a separately frozen set-level strategy for weakly
   cued, distributed, or outlier evidence.

Both routes draw from the same store, use the same renderer and exact character
accounting, and deduplicate before serialization. Each begins with a
solo-accounted allowance equal to half of the total budget: exactly 8,000 or
16,000 characters. If spread cannot spend its share on distinct admissions,
the unused capacity returns to relevance.

The study asks whether a relevance strategy shown by TC-005 to work efficiently
at 8,000 and 16,000 characters can retain direct-question evidence while the
other half of a **16,000- or 32,000-character total budget** is protected for
spread. Relative, token-based, and adaptive budgets are deferred to later
enterprise-scale work rather than mixed into the allocator test.

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
  ranked retrieval. It establishes the starting failure: with the existing
  cosine/K relevance path, limiting relevance to half cost 30 complete-evidence
  questions on LoCoMo's mostly direct-question workload.
- The internal breadth probe requires facts from weakly cued domains. Pure
  relevance ranking can concentrate the budget in the best-cued region even
  when evidence from several regions is required.
- The deployed stack gives coverage no reliable capacity: earlier tiers can
  consume the budget before coverage serializes anything useful.

TC-007 does not rerun that result under a new name. TC-003's result is the
reproduction anchor and the causal premise: the old relevance strategy was not
efficient enough under a half-budget. TC-005 tests whether relevance can improve
at that constrained operating point. TC-007 then asks whether the improved
relevance route plus a separately bound spread route beats giving the improved
relevance route the entire budget.

## 2. The single new component

The one new component is an **admission-resolved two-route allocator**. It
accepts:

- a relevance candidate stream already sorted in TC-005's frozen order;
- a spread candidate stream in the frozen spread selector's own order;
- one total serialized-character budget;
- a protected spread share fixed at 50%; and
- stable candidate content hashes for cross-stream deduplication.

It returns one rendered context and an attribution report naming, for every
delivered candidate, the proposing route, the admitting route, the paying
allowance, exact serialized cost, and whether it was admitted during initial
relevance fill, protected spread fill, or returned-capacity fill.

The allocator does not change candidate formation, embeddings, relevance scores,
spread scores, cluster assignments, rendering, or the drop policy. If any of
those must change, TC-007 stops because the test would contain a second new
component.

### 2.1 Allocation contract

TC-007 evaluates `B ∈ {16_000, 32_000}` exact serialized characters and sets
each route's initial solo allowance to `H = floor(B / 2)`, exactly 8,000 or
16,000. Each route is charged as if its initial admissions were alone in the
carried payload, matching TC-003's conservative accounting. Because both routes
ultimately share one rendered block, solo charging double-counts rather than
under-counts shared wrapper cost. After merge and dedup, every actual character
remaining under `B`—unused spread allowance plus wrapper savings—returns to
relevance. Preflight must prove these identities with the exact renderer before
any outcome is generated.

1. Produce the complete relevance order and complete spread order independently
   before packing. Evidence labels are unavailable to both.
2. Relevance traverses its frozen order and admits what fits its solo allowance
   `H`.
3. Spread traverses its own frozen order without rebuilding or pruning its
   candidate pool. It skips identities already **admitted** by relevance and
   admits distinct candidates that fit its own solo allowance `H`.
4. A candidate merely ranked or proposed by relevance but not admitted is still
   available to spread. Proposal-set overlap does not establish ownership.
5. Merge and deduplicate the two initial selections, render once, and compute
   exact remaining capacity as `B - serialized_chars`.
6. Relevance resumes its frozen order, skips every identity already serialized,
   and fills that remaining capacity.
7. Deduplicate by stable content identity. Every candidate serializes at most
   once and is charged to the phase that admitted it.
8. The combined payload must never exceed `B` after wrappers and separators.

This is intentionally role-ordered rather than service-order invariant:
relevance receives first claim only on what fits its solo-accounted half, spread
then receives protected room for distinct admissions, and relevance receives
the actual merged-payload remainder. Reversing those roles would define a
different architecture, not an implementation permutation.

### 2.2 Admission-resolved ownership

TC-003 showed that floors remove service-order dependence but introduce
ownership-order dependence: a shared candidate can charge either allowance.
TC-007 must not silently inherit that ambiguity.

TC-007 resolves ownership from admissions, not proposals. Relevance owns and
pays for identities admitted during its initial half. Spread owns and pays for
later distinct admissions even though relevance also ranked those identities
somewhere in its complete order. Relevance owns returned-capacity admissions.

Exploration must enumerate proposal overlap, initial relevance admissions,
spread duplicate skips, distinct spread admissions, and returned relevance
admissions on every real trace. If every spread candidate is incorrectly marked
shared merely because relevance ranks the full store, the spread route becomes
inert and TC-007 stops before registration.

## 3. Arms

| Arm | Description | Purpose |
|---|---|---|
| `A_TC003_FLOORS_REPLAY` | Unmodified TC-003 `A_FLOORS_DUAL` replay | Descriptive reproduction anchor; no new contrast |
| `A_TC003_RANKED_REPLAY` | Unmodified TC-003 `A_DUAL_RANKED` replay | Descriptive reproduction anchor; no new contrast |
| `A_RELEVANCE_FULL` | TC-005's frozen relevance order receives the full 16k/32k total budget | Binding control |
| `A_SPLIT_A3` | The same relevance order receives its 50% initial share; carried A3 receives the protected spread share | Treatment 1 |
| `A_SPLIT_FACILITY` | The same relevance order receives its 50% initial share; carried facility location receives the protected spread share | Treatment 2 |
| `A_SHAM` | Same phased accounting and wrapper cost as treatment, but no spread admissions | Cost/control check |

The binding control and treatments receive identical candidates, vectors,
query, relevance order, renderer, character accounting, total budget, and
exact-cost packer. `A_SHAM` prevents phased accounting or wrapper overhead from
being credited to spread. A3 and facility location are separately bound carried
spread strategies, not newly tuned selectors; the admission-resolved allocator
is TC-007's single new component.

No recency arm is included. Adding recency would change a second architectural
lever and would make the protected spread contrast uninterpretable.

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
- gains, losses, and ties against `A_RELEVANCE_FULL`; and
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
- gains, losses, and ties against `A_RELEVANCE_FULL`; and
- concentration of delivered characters by session and cluster.

The internal Q11 17-fact/four-domain probe is retained as a positive control and
descriptive mechanism trace, not as the inferential population. If exploration
finds too few eligible three-session LoCoMo questions for a reachable bar,
TC-007 stops or is registered as characterization-only; the definition is not
relaxed after counts are known.

### 4.3 Joint decision

The architecture succeeds only if at least one split treatment does all three:

1. beats `A_RELEVANCE_FULL` on complete required-evidence delivery over the
   combined eligible population;
2. improves the registered breadth endpoint, demonstrating that the protected
   route did the job it exists to do; and
3. stays inside a pre-registered targeted-loss tolerance, demonstrating that
   the more efficient relevance route preserved direct questions while limited
   to its half.

The exact paired bars, breadth endpoint, targeted tolerance, multiplicity, and
their reachability are locked only after Preflight Part 1 and before treatment
outcomes. Diversity, cluster count, or spread without required evidence cannot
pass. A combined gain without breadth improvement cannot pass; a breadth gain
that pays for itself with excessive targeted losses cannot pass.

## 5. Required attribution and diagnostics

Every question-level record must include:

- stable question and candidate content hashes;
- complete ordered candidate identities from both routes;
- proposal-set intersection;
- initial relevance admissions and spend;
- spread identities skipped because relevance already admitted them;
- distinct spread admissions and spend;
- returned-capacity relevance admissions and spend;
- admission-resolved ownership of every serialized candidate;
- exact wrapper, separator, candidate, and total costs;
- exact character limit, protected allowance, spread spend, slack returned,
  and relevance spend;
- delivered and dropped identities with reasons;
- evidence identities and domains delivered by each route; and
- byte digest of the final payload.

Aggregate counts without these records are insufficient. A result must reveal
whether spread added distinct evidence, merely relabelled relevance admissions,
or displaced direct-question evidence relevance would have delivered with the
full budget.

## 6. Preflight Part 1 — exploration before registration

Exploration is committed separately and may change this design before any bars
or parameters are locked.

1. **TC-003 reproduction.** Reproduce the unmodified 16,000-character C5 result
   `718 vs 748` and its committed payload digest, plus the registered
   32,000-character descriptive result `806 vs 811`, before constructing a
   TC-007 treatment.
2. **TC-005 reproduction.** Reproduce the frozen relevance order and its
   8,000-, 16,000-, and 32,000-character payload anchors by identity and digest.
3. **Behavioral identity.** Run relevance and each spread selector independently
   on every intended question. State in one falsifiable sentence what each
   orders and what each allocator phase admits.
4. **Name-to-behavior.** Demonstrate that relevance is limited to its initial
   half, spread admits candidates not already admitted by relevance, proposal
   overlap alone does not suppress spread, slack returns, and dedup serializes
   each identity once.
5. **Full distributions.** Report proposal overlap, initial relevance spend,
   spread duplicate skips, distinct spread spend, binding rate, returned slack,
   domain/cluster concentration, delivered evidence, and payload cost per
   question—not only means or medians.
6. **Degenerate states.** Exhibit no spread candidates, all spread proposals
   inside the initial relevance admissions, all spread proposals outside those
   admissions, oversized candidates, no returned slack, complete returned
   slack, relevance exhaustion, and a budget smaller than wrapper cost.
7. **Ownership sensitivity.** Compare admission-resolved ownership against
   TC-003's proposal/tier ownership on real traces. If the new rule is inert or
   manufactures a gain merely by relabelling the same delivered set,
   registration stops or names that residual.
8. **Positive controls.** Include at least one constructed case where protected
   spread adds unique breadth evidence and one where it displaces the only
   targeted evidence. Both outcomes must be reachable before bars are set.
9. **Budget characterization.** Characterize the locked 16,000- and
   32,000-character totals, their exact 8,000- and 16,000-character solo
   allowances, wrapper savings after merge, and returned capacity. Prove that
   both routes can bind and measure saturation at each budget.

## 7. Preflight Part 2 — mandatory checklist

| Check | Required evidence before registration/run |
|---|---|
| **PF1 Inputs exist** | Hash and count every store, vector cache, question, evidence label, session label, renderer, character counter, and packer consumed |
| **PF2 Mechanism identity** | Committed real-trace exploration proving frozen relevance order, independently frozen spread order, admission-resolved ownership, protection, returned slack, and dedup behavior |
| **PF3 Gate ordering** | A run entry point that executes G0 and exits before opening treatment outcomes; git and run-header assertions |
| **PF4 Thresholds achievable** | Mechanical reachability of the combined gain, breadth gain, and targeted-loss tolerance after multiplicity correction in all four treatment-budget cells |
| **PF5 Stable keys** | Content hashes for questions and candidates; no UUID, timestamp, or path identity |
| **PF6 Reproduction anchor** | Unmodified TC-003 C5 and TC-005's frozen relevance rankings/payloads reproduce by identity and digest before treatment output is generated |
| **PF7 Absorbing state** | No feedback is planned; prove allocator output is a pure function of frozen inputs. If feedback appears, run an intended-length real trace |
| **PF8 Ablation length** | Full-population offline replay where labels permit; otherwise state what the sampled breadth set cannot detect. No live 120-turn run without a passing 35-turn ablation |
| **PF9 Surrogate audit** | Record that domain/cluster spread can rise without breadth evidence, a full-budget ranker can hide half-budget inefficiency, evidence can arrive without being used, and ownership can relabel rather than add value |
| **PF10 Live requirement** | State that availability is not an answer verdict; TC-006 or a separately registered live reader study is required before adoption |

## 8. Gates and execution order

1. Close TC-005 with one frozen relevance strategy and committed 8k/16k
   half-budget plus 16k/32k full-budget anchors.
2. Commit TC-007 exploration artifacts, including both reproduction anchors.
3. Author resolves any remaining open decisions in §11.
4. Commit `TC_007_PRE_REGISTRATION.md` alone and record its SHA-256.
5. Implement the admission-resolved allocator and tests without modifying
   carried rankers, selectors, renderer, or packer.
6. **G0:** input hashes, leakage boundary, both reproduction anchors, phased
   ownership, exact 50/50 accounting, dedup, positive controls, and reachable
   bars all pass.
7. Run the offline targeted and breadth populations.
8. Commit question-level outputs before opening aggregate mechanism analysis.
9. Report availability only. Do not infer reader benefit or adoption.

No LLM calls are required for the offline study. Embedding calls are permitted
under this programme's terminology, but retained read-only caches are preferred;
cache misses and embedding call shape must be reported.

## 9. What TC-007 can and cannot establish

**Can establish:** whether improving relevance efficiency at its 8k/16k
half-budget operating points changes TC-003's negative 50/50 result, and whether
binding that relevance strategy beside A3 or facility-location spread improves
breadth without surrendering direct-question performance relative to giving the
same relevance strategy the full 16k/32k budget.

**Cannot establish:**

- that a reader notices or correctly uses delivered evidence;
- that cluster or domain spread is itself useful without evidence labels;
- the best spread share outside the locked 50/50 design;
- transfer to an unseen corpus;
- production latency or budget selection at enterprise store sizes; or
- superiority of the current clustering algorithm over other spread mechanisms.

## 10. Re-evaluation of TC-005 and TC-006

### TC-005 — repurposed as the ranked-retrieval comparison

TC-005 now compares the carried dense-cosine, BM25, and dense-plus-sparse RRF
orders over identical LoCoMo candidates. Its primary operating points are 8,000
and 16,000 characters—the relevance halves TC-007 will actually provide—with
16,000 and 32,000 as full-budget continuity anchors. It freezes one relevance
stream before TC-007 changes allocation, preventing ranker quality and protected
spread from becoming simultaneous interventions.

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

The resulting implementation order is **TC-005 Preflight → TC-005 registration
→ TC-005 implementation/run/close → TC-007 Preflight → TC-007 registration →
TC-007 implementation/run/close → TC-006 reader validation**. Each requires its
own committed Preflight and standalone pre-registration.

## 11. Author decisions recorded August 23, 2026

1. **Budgets:** 16,000 characters primary and 32,000 characters secondary;
   relative/token budgeting is deferred to later enterprise-scale work.
2. **Route binding:** TC-005 freezes one relevance strategy at its 8,000- and
   16,000-character operating points. TC-007 separately binds spread to carried
   A3 or carried E005 facility location.
3. **Allocation:** relevance receives the initial 50%; spread receives 50% for
   identities relevance did not already admit; unused spread capacity returns
   to relevance.
4. **Shared ownership:** ownership follows admission phase, not proposal-set
   membership. Ranking the full store does not give relevance ownership of the
   full store.
5. **Breadth population:** existing labelled questions requiring evidence from
   at least three sessions; internal Q11 remains a descriptive positive control.
6. **Targeted population:** existing labelled questions whose evidence is
   confined to one adjacent-turn pair in one session.
7. **Success:** a split treatment must beat the same relevance strategy with the
   full budget on combined complete-evidence delivery, improve the registered
   breadth endpoint, and stay within a registered targeted-loss tolerance. Exact
   reachable bars are locked after exploration and before treatment outcomes.
8. **Reader validation:** TC-006 will use frozen TC-007 contexts, subject to its
   own standalone pre-registration.

TC-005 has reported and froze dense as the relevance route. TC-007 Preflight
then reproduced TC-003 and TC-005, inventoried the populations, verified
admission-resolved dedup and exact 50/50 behavior, bound shipped A3 and pure
facility location without tuning, and proved all three success conditions
reachable. The next step is the standalone TC-007 pre-registration; no outcome
run is authorized before that file is committed alone.
