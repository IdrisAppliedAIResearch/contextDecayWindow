# E006 Part 2 — Retrieved-Context Chained Retrieval (Rev 2, superseding)

**Type:** Mechanism specification. Written under the mandatory Preflight rule.
**Repository:** `contextDecayWindow` · `experiments/components/retrieval_mechanism_ledger/`
**Branch:** `e006-p2-chained-retrieval`
**Supersedes:** E006 Part 2 Rev 1 (SHA-256 `BF52E50B…E38680`) — withdrawn for the defects in §0.4
**Status:** DRAFT — pending author authorization (§0.3). **This document is the design anchor and must be committed before implementation.**
**Ledger:** F1 (breadth / enumeration), unclaimed
**Companions:** `NEUROSCIENCE_LANDSCAPE.md` · `RETRIEVAL_MECHANISM_LEDGER.md` · `STANDING_RULE_preflight.md` · Study 011 `AMENDMENT_001` · `RD-001`

---

## 0. Status, sequence, and what changed

### 0.1 Binding sequence — resolves the Rev 1 contradiction

**Strictly ordered. Each stage gates the next. No stage begins before the prior stage's artifacts are committed.**

| # | Stage | Cost | Can kill the mechanism |
|---|---|---|---|
| **S1** | Prior-art scan | hours | **Yes** — a published negative on conversational memory ends it |
| **S2** | Preflight (§2) | hours–1 day, offline | **Yes** — cycles, X1≠X0, or unreachable seeds |
| **S3** | Parameter registration | minutes | No, but locks the sweep |
| **S4** | Offline arms (§6) | offline, no model calls | **Yes** — kill condition |
| **S5** | Live evaluation | **separately registered and separately authorized** (§7) | — |

**Rev 1 contradicted itself**: §0.3 argued Preflight could run first, §9 listed the scan first. **Resolved toward the scan.** The scan is cheaper than Preflight's implementation and can make it moot.

### 0.2 Blockers — restated against current program state

| Rev 1 blocker | Status now |
|---|---|
| Prior-art scan owed | **Still owed. S1.** |
| Noise band unmeasured | **CLEARED AS A BLOCKER — and replaced by a stronger constraint.** Study 011 Amendment 001 Phase 2 measured the band at **3.0 points** on a 13-point rubric. This is no longer something to wait for; it is a design input. See §0.5 |
| Author authorization | **Outstanding.** RD-001 records Part 2 as NOT AUTHORIZED and only the author can change that |

### 0.3 Authorization required

RD-001 and this document both require explicit authorization from the program author, with compute cost stated. **The planning partner cannot supply it.** Authorization applies to S1–S4 only; S5 requires its own.

**Stated cost:** S1–S4 are hours to roughly a day, entirely offline, **zero model calls, zero embedding calls** beyond the committed cache. S5 is not costed here and is not authorized here.

### 0.4 Why Rev 1 was withdrawn

Three defects, two of them substantive:

1. **Ordering contradiction** between §0.3 and §9 (resolved in §0.1).
2. **Stale blocker.** The noise-band clause was written before Phase 2 landed and understated what the measurement implies (§0.5).
3. Parameter ranges and a noise-aware live protocol were unregistered (§5, §7).

### 0.5 What the 3.0 band means for this spec

Phase 2 found the instrument **bimodal, not noisy**: five replicates of Arm D produced two exactly-reproducible trajectories, 11.0 and 8.0, diverging at character 79 of turn 1. Under the amendment's uniform application, **every scored gap below 3.0 in the program's record re-reads as NOT DEMONSTRATED** — including Study 009's 3.0 and LV-001's −2.0.

**Three consequences, binding on this spec:**

1. **§8 predicts this mechanism moves availability by 1–3 facts. A live scored difference of that size is not interpretable from single runs.** Any live evaluation must be replicated; §7 registers how.
2. **The offline outcome (§6) is availability, which is a count, not a score.** Counts and identities are untouched by the band — Amendment 001 §7 names exactly this class as unaffected. **S4 therefore produces a real, interpretable result.**
3. Because S4 is interpretable and S5 currently is not, **S4 is where this mechanism lives or dies.** Do not treat the offline stage as a preliminary.

---

## 1. S1 — Prior-art scan

**Runs first. Blocks everything.**

Targets, at minimum:

- **Pseudo-relevance feedback** (Rocchio; RM3) — the classical IR form of cue update from retrieved results. **Query drift is its documented failure mode**; establish what is known about it, including known mitigations.
- **FLARE, IRCoT, Self-RAG** — iterative and active retrieval in LLM pipelines.
- **Retrieved-context models in IR** — whether Howard/Kahana-style context updating has been implemented outside cognitive modelling.
- **Conversational memory specifically** — whether chained or iterative retrieval has been reported on conversational/episodic memory, with what result.

**Kill condition for S1:** a published negative result for chained retrieval on conversational memory. **Record in the ledger and stop.**

**Novelty position, registered now:** chaining is not novel. If this mechanism has a contribution it is the setting and the absorbing-state discipline, not the algorithm. **Do not claim novelty for the update rule.**

---

## 2. S2 — Preflight

Per `STANDING_RULE_preflight.md`. **Exploration first, then checklist.** Artifacts committed.

### 2.1 Exploration

**E-1 — Characterize the current cue.** For every probe on the committed 121-turn store: query embedding, cosine to every episode, rank distribution of fact-bearing episodes. **This is the state the chain starts from.** DR-002 measured the four highest-cosine episodes carrying zero target facts on the enumeration probe; establish whether that holds across probes.

**E-2 — Behavioral identity of every component touched.** Mandatory after the N-tier finding. One falsifiable sentence each for the seeding path, K threshold, packer, renderer. **No component is used on the strength of its name.**

**E-3 — Feedback inventory.** Every place an output influences a later input: state variable, update rule, monotone or not. **A monotone state with no decay is an absorbing-state candidate by construction** — that is what locked Arm S for 111 turns.

**E-4 — Distribution shape** of one retrieval step's return. Not medians: EC-002's medians were identical while the aggregate moved 18×.

### 2.2 Checklist

| # | Check | Answered by |
|---|---|---|
| PF1 | Inputs exist | Committed store, vectors, and candidate identities from `logs/context_match.jsonl`, counted and hashed. **If no vector cache exists for this corpus, say so and substitute committed candidate identities** — IC-001's precedent, under an authorized amendment |
| PF2 | Mechanism identity | E-2 |
| PF3 | **Gate ordering enforced** | Every gate implemented and executed before what it gates; ordering asserted in git and in each run header. **Study 011's determinism check ran after scoring — this spec asserts order mechanically** |
| PF4 | Threshold achievability | §6.3, checked before the kill condition locks |
| PF5 | Stable comparison keys | Content hashes only. No `uuid4`, timestamps, or paths |
| PF6 | Reproduction anchor | X0 reproduces the committed single-shot result by episode identity and payload digest before any depth ≥1 output opens |
| PF7 | **Absorbing-state proof** | §3. Load-bearing |
| PF8 | Ablation adequacy | Chain behavior is depth-dependent, not turn-dependent; a 35-turn trace exercises the mechanism fully. **Stated explicitly rather than carried** |
| PF9 | Surrogate audit | §9 |
| PF10 | Live-evaluation requirement | §7 |

---

## 3. PF7 — Absorbing-state proof

**This mechanism has feedback by definition, and the program's one prior stateful retrieval path locked.**

Arm S: `retrieve()` refreshed delivery timestamps in one batched write, the key ranked freshest first, ties broke toward oldest turn. The block selected itself for **111 consecutive turns**; episodes 10–118 were delivered once each and never again. **Cause: a monotone state with no decay.**

Retrieved-context theory avoids this because context **blends rather than replaces** — provided the blend retains a nonzero share of both prior context and the original query.

**Required, offline, before any arm runs:**

1. Run the chain to depth `D` on every committed probe.
2. Record the retrieved set and context vector at each step.
3. **Assert no repeated retrieved set within a chain** and **no fixed point**.
4. **Assert per-step novelty > 0** — a chain returning the same set at every depth is degenerate even without exact repetition.
5. Sweep blend parameters; report the region where cycles or degeneracy appear. **Cycles anywhere in the registered operating range means those settings are not authorized.**

**The detector runs on a real trace.** Arguing from the update rule that cycles cannot occur is the reasoning that failed for Arm S.

---

## 4. Mechanism

### 4.1 Grounding

<cite index="16-1">Recall of an item leads to retrieval of its context, and this retrieved context is incorporated into the context used to cue the next recall, promoting recall of items sharing the just-recalled item's temporal context.</cite> <cite index="17-1">Contextual drift gives rise to recency effects; contextual retrieval gives rise to contiguity effects.</cite> <cite index="14-1">Retrieved context is an asymmetric cue, which is why forward transitions are favoured.</cite>

**Grounding, never derivation.** This supplies the update rule's shape. It supplies no evidence the mechanism helps here.

### 4.2 The rule

```
retrieve_chained(query, budget, D):
    q0 = embed(query)
    c  = q0
    seen = {}

    for step in 0..D:
        cue = normalize(W_Q * q0 + W_C * c)
        hits = top_m(cue, exclude=seen)
        seen |= hits
        c_reinstated = mean(embedding(h) for h in hits)
        c = normalize(RHO * c + BETA * c_reinstated)

    return pack(rank(seen, cue_final), budget)
```

**Three asserted properties, not tuning choices:**

- **`W_Q > 0` at every step** — the original query never leaves the cue. Primary defence against query drift.
- **`RHO > 0`** — context never fully replaced. Defence against absorbing states; the property Arm S lacked.
- **`exclude=seen`** — one retrieval per episode per chain; prevents the trivial fixed point.

---

## 5. S3 — Parameter registration

**Committed before any arm runs. Narrow by design** — six free parameters is itself an objection, and a mechanism with enough knobs can be made to produce most results.

| Parameter | Registered range | Rationale |
|---|---|---|
| `D` depth | {1, 2, 3} | §8 predicts drift dominates past 2 |
| `m` per-step | {3, 5} | Small; the budget is not binding (§6.3) |
| `W_Q` | {0.3, 0.5, 0.7} | Must exceed 0; drift defence |
| `W_C` | `1 − W_Q` | Not free. Removes one parameter |
| `RHO` | {0.5, 0.7} | Must exceed 0; absorbing-state defence |
| `BETA` | `1 − RHO` | Not free. Removes one parameter |

**Two parameters are eliminated by construction.** Grid: 3 × 2 × 3 × 2 = **36 cells.** Registered in full before S4; **no cell is added after results are seen.**

---

## 6. S4 — Offline arms

### 6.1 Arms

| Arm | Configuration | Purpose |
|---|---|---|
| **X0** | Single-shot, deployed retrieval | **Reproduction anchor (PF6).** Identity and payload digest |
| **X1** | Chain, `BETA = 0` | **Degeneracy control.** With reinstatement disabled the chain must equal X0 across all probes, by digest. If not, the harness is wrong and S4 stops |
| **X2–X4** | Chain, `D` = 1, 2, 3 | The mechanism |

### 6.2 Outcome

**Facts available on the enumeration probe**, at the enforced 32,000-character budget under exact serialized cost. A count, not a score — therefore interpretable despite the 3.0 band (§0.5).

Reported jointly, never alone: facts, characters, episodes, per depth.

### 6.3 Kill condition and achievability

**Kill: no chained arm exceeds X0's committed availability at any registered cell.**

**Achievability (PF4):** AR-001 established 14/17 fits in 5,058 of 32,000 characters — **the budget does not bind.** The question is reachability. **Before locking, state the maximum reachable at depth `D` from the committed seeds.** If the seeds cannot reach fact-bearing episodes at any depth, the mechanism is dead and S4 need not run.

Reference points, reported and **not** thresholds: E002 reached 10/17 against a 6/17 baseline and was killed on its own bar; E005 reached 12/17; the AR-001 oracle is 15/17 at 5,455 characters.

### 6.4 No-regression arm, binding

**The eight targeted probes must not fall.** Targeted retrieval is the one capability that works; every mechanism proposed for breadth is a candidate for breaking it. Per-probe, 21-item grain.

---

## 7. S5 — Live evaluation, separately gated

**Not authorized by this document.**

Availability has twice failed to predict answers in this program: LV-001 measured 16/16 offline against 1.5/8 live, and Study 011's best-availability arm scored lowest.

**And the band now constrains the design.** With a measured 3.0 band and a predicted 1–3 fact effect, **a single-run live comparison cannot resolve this mechanism.** Any S5 registration must therefore carry:

1. **Replication, not single runs.** Minimum five replicates per arm, matching Amendment 001 Phase 2.
2. **Process-state control.** Phase 2 found the switch appears at cold versus warm slot state. Replicates must record and control it — Study 009's manifests record no server PID at all, and that is the failure to avoid repeating.
3. **A stated resolvable difference.** What effect size the design can detect. If it cannot detect the predicted effect, say so before running.
4. Its own pre-registration, its own bar, its own authorization.

**Any S4 report states plainly: the offline result is a characterization of delivery, not a finding about answers.**

---

## 8. Registered predictions

Committed so they can be wrong. Prior: twelve predictions, most wrong on mechanism.

1. **Preflight passes without cycles** at `RHO ≥ 0.5`, `W_Q ≥ 0.3`. ~70%.
2. **Depth 1 helps, depth 3 hurts.** Drift dominates past two hops. ~60%.
3. **Best chained arm reaches 8–11/17**, below E005's 12/17. Chaining expands reach; it does not repair a seed set whose top ranks carry no facts.
4. **Targeted probes hold.** Chains seed from high-similarity material, which is where targeted facts sit. ~75%.
5. **Final cue drifts measurably** — cosine below 0.7 to the original query by depth 2.

**The uncomfortable one:** prediction 3 says this loses to a mechanism already in the ledger. If so, the value of the work is PF7's absorbing-state discipline and the drift measurement, not the mechanism.

---

## 9. Surrogate audit

| Check | Certifies | Can it pass falsely? | Mitigation |
|---|---|---|---|
| No cycle detected | mechanism stable | **Yes** — near-identical sets without exact repetition | Assert per-step novelty, not just non-identity |
| Availability rises | mechanism works | **Yes, twice demonstrated** | §7. No verdict from offline alone |
| X1 = X0 | harness correct | Yes — could match on one probe by chance | All probes, by payload digest |
| Targeted holds | no regression | Yes — aggregates hide per-probe swings | Per-probe, 21-item grain |
| `W_Q > 0` prevents drift | cue stays on topic | **Yes** — small `W_Q` against large `W_C` drifts anyway | Measure and report final-cue cosine to `q0` per depth |
| Depth helps | chaining helps | Yes — could be more material at any cost | Facts, characters, episodes reported jointly |

**Accepted residual:** one corpus, one breadth probe, no variance. The program has exactly one enumeration probe and cannot support a general claim about enumeration.

---

## 10. Deliverables

- [ ] **This spec committed as the design anchor before implementation** — SHA recorded
- [ ] Author authorization recorded for S1–S4
- [ ] S1 prior-art scan; ledger entry; **stop if a published negative is found**
- [ ] S2 Preflight: exploration E-1–E-4 and PF1–PF10, artifacts committed
- [ ] S3 PF7 cycle detector on a real trace; sweep region reported
- [ ] X1 = X0 asserted across all probes by payload digest
- [ ] Parameter grid registered before S4; **36 cells, no additions after results**
- [ ] Kill-condition achievability stated (§6.3)
- [ ] S4 offline: facts, characters, episodes per arm and depth
- [ ] Final-cue drift per depth
- [ ] Targeted probes per probe, all arms
- [ ] Ledger verdict; graveyard entry if killed
- [ ] **Explicit statement that no offline result is a verdict** (§7)

---

*Rev 2, August 9, 2026. Supersedes Rev 1 (`BF52E50B…E38680`). Corrections: S1-before-S2 ordering; noise-band blocker replaced by the measured 3.0 band as a design input; parameter grid registered; live evaluation given replication requirements. Reference failure for PF7: Arm S locked at turn 11 for 111 turns under a monotone no-decay state.*
