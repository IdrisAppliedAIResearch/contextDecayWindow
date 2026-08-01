# DX-001 — Turn-90 Selection Miss: Diagnostic and Conditional Fix Protocol

**Type:** Diagnostic specification (Part 1) + conditional fix protocol (Part 2).
**Repository:** `contextDecayWindow` · `experiments/components/retrieval_mechanism_ledger/`
**Branch:** `dx/001-turn90-miss`
**Status:** DRAFT — Part 1 authorized on commit; **Part 2 does not exist until Part 1 names a mechanism**
**Depends on:** E005 PROMOTION_ELIGIBLE · DR-002 pool read-out (PR #26) · AR-001
**Companions:** `RETRIEVAL_MECHANISM_LEDGER.md` · `E005_diversity_selection_scan_and_protocol.md` · `CC_001_component_contract.md`

---

## 0. Scope and framing

**This is not an architectural repair.** The E005 primary configuration
(`A3_l0.1_r0.0_k16`) delivers 12/17 Q11 facts across 4/4 domains with 16/16
targeted preserved at 31,569 characters, recovering 4 of the oracle's 5 episodes.

The entire remaining gap to the oracle is **one episode**: turn 90, monetary
domain, 4 facts, cosine rank **112 of 119**. It is also the reason monetary is the
weakest domain at 1/4. Recovering it would close both the 12→15 fact gap and the
domain imbalance.

**The episode was in the candidate pool. The selector saw it and passed.** This is
therefore a question about the objective, not about retrieval or the pool.

### 0.1 What this document does not assume

It does not assume the miss is fixable. It does not assume a fix would generalize.
It does not assume 12/17 is unshippable. Those are open, and Part 2 §F.6 records the
conditions under which the correct outcome is **no change**.

---

# PART 1 — DIAGNOSTIC

Offline. No inference, no new run, no code change. Reads committed E005 artifacts.

## D.1 The question

**Why did the A3 objective decline to select turn 90 at any step of the greedy run?**

Three candidate mechanisms, mutually distinguishable from committed artifacts:

| # | Mechanism | Signature |
|---|---|---|
| **M1** | **Cluster collision.** A3's diversity term counts distinct clusters touched. If turn 90 shares its k=16 cluster with an already-selected episode, the diversity term pays nothing for it, leaving only its near-bottom relevance | Turn 90's cluster already occupied at the step it would otherwise have been competitive |
| **M2** | **Cost discount.** r changed fact counts in 44/44 A3 cells, so cost is active. Monetary's domain cost is 2,913, second-highest of four | Turn 90's serialized cost high relative to selected episodes; its rank improves as r → 0 |
| **M3** | **Relevance floor.** At cosine rank 112 its relevance contribution may be too small for any λ to overcome regardless of diversity | Marginal gain below the step-winner at every step, across all λ |

These are not exclusive. Report the contribution of each rather than forcing a single verdict.

## D.2 Measurements

All from committed E005 sweep artifacts.

1. **Selection census — run first.** Did **any** of the 146 configurations select
   turn 90? This is the highest-value single query in the document.
   - **Yes** → the recovery condition already exists in the committed sweep. Diff
     that configuration against the primary on every parameter, and report its full
     result vector (Q11 total, per-domain, targeted, chars, oracle overlap). A
     configuration that recovers turn 90 while losing art or a targeted item is not
     a fix; record it as such.
   - **No** → the objective is structurally blind to it across the entire
     parameter space explored. That is a stronger finding than any single-cell
     explanation and changes Part 2's shape.
2. **Cluster assignment.** Turn 90's cluster ID at every k in the sweep. For each,
   which episode first occupied that cluster, at which greedy step, and that
   episode's fact count.
3. **Cost.** Turn 90's exact serialized cost under the post-DR-001 renderer, against
   the cost distribution of selected episodes. Also its cost per Q11 fact carried
   (4 facts) versus the same ratio for selected episodes.
4. **Greedy trace.** Turn 90's marginal objective gain at every step of the primary
   run, alongside the step winner's gain. Report the **gap**, not just the rank —
   a near-miss and a structural exclusion are different findings.
5. **λ and r sensitivity.** Turn 90's best achieved position across the λ and r
   sweeps, holding k at 16 and then across k.
6. **Headroom.** Characters remaining at the point the primary run terminated. The
   primary spent 31,569 of 32,000. **If it terminated on budget rather than on
   candidates, budget exhaustion is a fourth mechanism (M4)** and must be reported
   as such — turn 90's cost is then decisive independent of the objective.

## D.3 Deliverable

A mechanism attribution: M1, M2, M3, M4, or a named combination, with the artifact
supporting each. **If the evidence does not distinguish them, say so and stop.**
"Unresolved" is a permitted outcome and is preferable to a fix built on a guess.

## D.4 Surrogate audit

| Check | Certifies | Can it pass falsely? | Mitigation |
|---|---|---|---|
| Turn 90's rank improves under a parameter | that parameter is the cause | **Yes** — rank can move for reasons unrelated to selection | Report the marginal-gain gap at the deciding step, not rank alone |
| A configuration selected turn 90 | that configuration is better | **Yes** — it may have lost art, a targeted item, or total facts | Full result vector mandatory for any such configuration |
| Cluster collision observed | M1 is the cause | Yes — collision may be incidental if relevance was already fatal | Test M1 and M3 jointly: would turn 90 win with the diversity term paid in full? |
| Mechanism identified | the miss is fixable | **Yes** — a cause is not a remedy | Part 2 is conditional and may correctly conclude no change |

---

# PART 2 — CONDITIONAL FIX PROTOCOL

> **This part is a stub until Part 1 returns.** The fix's shape depends entirely on
> the mechanism. Do not pre-select a branch. Do not implement anything in Part 2
> before Part 1's attribution is committed.

## F.1 The governing hazard, stated before any result

**n = 1 episode, n = 1 probe, and the desired answer is known in advance.**

Any parameter adjusted until turn 90 appears is overfitting to a single test case.
This program has a documented history of catching itself building against a
surrogate; this is the most direct opportunity it has had to do so.

**Binding rule — commit before touching any parameter:**

> A fix must be justified by the mechanism Part 1 identified, stated as a reason
> that would have applied without knowing turn 90 exists. If the justification is
> "this value recovers turn 90," it is not a fix and must not be promoted.

Worked example of an illegitimate fix: *"k=24 recovers turn 90"* with no account of
why 24 is the right cluster granularity. Worked example of a legitimate one:
*"k=16 produces clusters coarser than the domain structure, so within-domain
diversity is unrewarded; k should be set to the observed sub-domain count, which is
24 — and this predicts recovery of turn 90 as a consequence."* The second makes a
prediction; the first reports one.

## F.2 Branch A — M1, cluster collision

Change: k, or the cluster-assignment method.

**Justification required:** an independent account of correct cluster granularity —
observed sub-domain count, silhouette or elbow analysis over the store, or the
distribution of facts per cluster. k is currently a swept value with no derivation.
**A principled derivation of k is a legitimate contribution regardless of whether it
recovers turn 90.**

**Watch:** k interacts with everything. Changing it re-partitions the pool and
therefore re-runs the whole objective. Every arm must be re-evaluated, not just the
primary cell.

## F.3 Branch B — M2, cost discount

Change: r, or the cost-normalization form.

**Justification required:** DR-002 established that the budget is slack for the
optimum (5,455 of 32,000) but binding for the selector, because the greedy frame
fills the budget. If cost is discounting a high-value episode under a
non-binding-at-the-optimum budget, **the correct fix may be to stop filling the
budget** — a termination-rule change rather than a cost-weight change.

That is a more interesting outcome than tuning r, and it is a direct CC-001 input:
a selector that stops when marginal gain falls below a threshold, rather than when
characters run out, is a different and arguably better component contract.

## F.4 Branch C — M3, relevance floor

Change: the objective's relevance term, or its weighting.

**Justification required:** this is the hardest branch and the most likely to be
correctly abandoned. DR-002 established that **the four highest-cosine episodes
contribute zero Q11 facts** — cosine relevance is inverted at the top of the
ordering. If turn 90 is excluded by a relevance floor, the floor itself is suspect,
and repairing it is not a parameter change but a new objective.

**If Branch C is reached, escalate. Do not implement.** A new objective is a new
ledger entry (E006) with its own scan, kill condition, and full arm set — not a
patch to E005.

## F.5 Branch D — M4, budget exhaustion

Change: the termination rule.

If the primary run terminated on budget with turn 90 unselected but affordable
earlier, this is not an objective failure at all. See F.3 — the same
marginal-gain termination rule applies, and this branch converges with Branch B.

## F.6 No-change outcomes — explicitly legitimate

**The correct result may be no change.** Record and stop if:

- Part 1 cannot distinguish mechanisms.
- The only recovering configurations lose art, a targeted item, or total facts.
- The required justification cannot be stated without reference to turn 90.
- Branch C is reached (escalate to E006 instead).

In any of these, **12/17 at 4/4 domains is promoted as the shipping configuration
with rank 112 recorded as a known, characterized limitation.** A documented
limitation with an identified cause is a shippable state; an unjustified parameter
tuned to a single test case is not.

## F.7 Acceptance bars for any fix — registered now

Committed before Part 2 begins, unchanged by Part 1's result.

| Bar | Requirement |
|---|---|
| **B1 Targeted** | 16/16 preserved. No exceptions |
| **B2 Domains** | 4/4 maintained. Trading art for monetary is not a fix |
| **B3 Total** | Q11 total ≥ 12/17. A fix that adds monetary while dropping elsewhere fails |
| **B4 Budget** | ≤ 32,000 exactly-serialized characters, enforced |
| **B5 Justification** | Mechanism-based, statable without reference to turn 90 (F.1) |
| **B6 Latency** | Within the DR-002 envelope: ~40 µs/candidate, linear. Report if the fix changes the scaling exponent |
| **B7 No re-run of a locked artifact** | E005's committed results are not re-scored |

**A fix reaching 13/17 or 14/17 while clearing B1–B7 is a success.** 15/17 is the
oracle and is not the target — DR-002 bounded how much a better selector alone can
recover, and the bound is small.

## F.8 Prediction, committed before Part 1 runs

Recorded so it can be wrong on the record.

- **Most likely mechanism: M1 cluster collision, with M3 contributing.** k=16 over a
  4-domain store gives ~4 clusters per domain; turn 90 plausibly shares one with a
  higher-relevance monetary episode already selected.
- **Selection census: no configuration selected turn 90.** ~65% confidence. If one
  did, it likely sits at high k.
- **Outcome: 13/17.** Recovering 1–2 facts, not all 4, because turn 90's 4 facts may
  not all survive containment dedup and rendering.
- **Non-trivial probability (~30%) that F.6 fires and the correct answer is no change.**

---

## Deliverables

**Part 1**
- [ ] Selection census across all 146 configurations — run first
- [ ] Cluster assignment table, all k
- [ ] Cost and cost-per-fact comparison
- [ ] Greedy trace with marginal-gain gaps
- [ ] λ / r / k sensitivity for turn 90
- [ ] Termination-cause determination (M4 check)
- [ ] Mechanism attribution, committed

**Part 2 — only if Part 1 names a mechanism**
- [ ] Branch selected, with F.1 justification stated first and committed before implementation
- [ ] Full arm re-evaluation if k changes
- [ ] B1–B7 evaluated and reported
- [ ] Ledger updated; `README.md`, `AGENTS.md` digest, `ERRATA.md` if any committed number changes
- [ ] If F.6 fires: 12/17 promoted as shipping configuration, rank 112 recorded as characterized limitation

---

*Drafted August 1, 2026. E005 primary `A3_l0.1_r0.0_k16`: 12/17, 4/4 domains, 16/16
targeted, 31,569 chars, 4/5 oracle overlap. Oracle: 15/17 @ 5,455 chars. Miss: turn
90, monetary, 4 facts, cosine rank 112/119. DR-002 PR #26; suite green at 778.*
