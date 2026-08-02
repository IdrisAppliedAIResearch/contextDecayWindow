# CC-003/004/005 — Deployment Closeout: Growth, Enforcement, Persistence, Eviction

**Type:** Diagnostic (Part 0) + three engineering specifications (Parts 1–3).
**Repository:** `contextDecayWindow` · `episodic/`
**Branches:** `cc/003-enforcement` · `cc/004-persistence` · `cc/005-eviction`
**Status:** DRAFT — **Part 0 gates Part 3's design and may change it**
**Depends on:** CC-002 complete (PR #28) · DR-001 · DR-002 · Study 010
**Companions:** `CC_001_component_contract.md` · `CC_002_library_extraction.md`

---

## 0. Why these are one document

They are the four unresolved obligations from `CC_001` §1.1 (O1, O2, O4, O5), and
they interact. Enforcement determines whether context is bounded. Boundedness
determines what eviction is *for*. Persistence determines whether either survives a
restart. Scoping them separately produced three specs that each assumed the other
two were solved.

**Part 0 runs first and may change Part 3.** Do not scope eviction before the growth
question is answered.

---

# PART 0 — DX-002: THE CONTEXT GROWTH QUESTION

## 0.1 The observation

Study 010's context traces begin near ~10k tokens and reach **27,154 tokens (Arm L)
by turn 1,000**, with Arm S at 17,541. Read off the curve, that looks like
unbounded growth, which would disqualify the component for continuous operation.

**This has never been analyzed as a growth question.** 27,154 was reported as a peak
and verified as `characters // 4` across all 2,000 serialized prompts. Nobody asked
whether the curve was still climbing.

## 0.2 The competing explanations

**H-A — Asymptotic fill.** The greedy frame fills whatever budget it is given. E005's
primary spent **31,569 of 32,000** characters; DR-001's re-derivation has Study 010's
Q13/Q14 selecting 69 and 71 episodes at 31,993 and 31,796 characters at exact cost.
Early in a conversation the store cannot supply enough material to fill the budget,
so context rises until it saturates and then flattens. Under this explanation
**context is bounded by construction** and 27k against a 32k LTM budget is
approximately the ceiling, not a waypoint.

**H-B — Genuine unbounded growth.** Something outside the budgeted LTM block grows
with turn count. Candidates, all real: the STM recency window if episode size grows;
rule pinning, which reached **118 false rules** at 1,000 turns before persistence was
disabled; TopicManager, which collapsed 12 domains into two; any accumulating
preamble. Under this explanation the component fails at long horizons regardless of
selection quality.

**H-C — Both, at different scales.** LTM saturates while a smaller unbudgeted
component keeps climbing. This is the most likely outcome and the most dangerous,
because the LTM plateau makes the total look controlled while a slow leak continues.

## 0.3 The measurement

Offline. Committed Study 010 artifacts. No run.

1. **Plot context size against turn number, both arms, all 2,000 serialized prompts.**
   This has not been done. The peak is committed; the curve is not.
2. **Decompose each prompt into its parts** — system preamble, STM block, LTM block,
   pinned rules, topic digest, query — and plot each independently. **The
   decomposition is the whole diagnostic.** A flat LTM under a climbing total names
   the leak immediately.
3. **Fit the last 300 turns of each series.** Slope indistinguishable from zero →
   H-A. Slope materially positive → H-B or H-C, and the decomposition says which.
4. **Report LTM block size against the 32,000 budget over time**, in exactly-serialized
   characters under the post-DR-001 renderer, not the historical undercharged figures.
5. **Check the rule-pinning contribution specifically.** 118 false rules is a known
   growth path with a known cause.

## 0.4 Decision rule — commit before opening the curves

| Branch | Finding | Consequence |
|---|---|---|
| **A** | Terminal slope ≈ 0; LTM saturated; no unbudgeted component climbing | Context is bounded. **Eviction (Part 3) is a disk and latency policy, not a context policy.** Scope it accordingly |
| **B** | Terminal slope positive, cause is an unbudgeted component | Name it, and **bring it inside the budget or remove it** before anything ships. This blocks CC-003 |
| **C** | Terminal slope positive, LTM itself still climbing | Contradicts the budget accounting. **STOP and reconcile** against DR-001 before proceeding |
| **D** | Not determinable from committed artifacts | State the limit. Do not estimate. Escalate to a measured run under enforcement |

## 0.5 Prediction, committed

**H-A for the LTM block, H-C overall, ~60%.** The greedy frame fills the budget, so
LTM should saturate near 32,000 characters. I expect a small positive residual slope
from rule pinning or the STM window. **Most likely outcome: bounded once the leak is
named and budgeted.**

**Caveat on this whole section.** The 10k→27k reading is from a chart, and the
numbers above are from summary records rather than from the artifacts themselves.
Verifying the source figures is step zero. This document's author has been wrong
repeatedly in exactly this way — reasoning from a summary instead of the artifact —
and Part 0 exists because that pattern is worth one more check, not because the
conclusion is presumed.

## 0.6 Surrogate audit

| Check | Certifies | Can it pass falsely? | Mitigation |
|---|---|---|---|
| Terminal slope ≈ 0 | context is bounded | **Yes** — a plateau at 1,000 turns says nothing about 10,000 | State the horizon. Claim bounded *at the tested horizon only* |
| LTM ≤ budget | total is bounded | Yes — unbudgeted parts are invisible to it | The decomposition (0.3.2) is mandatory, not optional |
| Peak reported | growth characterized | **Yes — this is the current state of the record** | Curve, not peak |

---

# PART 1 — CC-003: BUDGET ENFORCEMENT AND TRUNCATION SEMANTICS

Closes `CC_001` O1 and O2. **The largest correctness gap in the library.**

## 1.1 The gap

Every study on record ran **67.9–68.2% over its stated budget** (DR-001). Exact-cost
accounting now exists; a hard ceiling does not. `ContextReport.truncated` reports a
condition the library does not act on. **No result in the program's history describes
behavior when the budget binds.**

## 1.2 Requirements

1. **Hard ceiling.** `store.context(query, budget)` never returns a block exceeding
   `budget` in exactly-serialized characters via the production renderer. No
   exceptions, no tolerance, no configuration to disable.
2. **Drop order is specified and deterministic.** When selection wants more than
   fits, what is dropped is a documented policy, not an artifact of iteration order.
   **Default: the selector's own marginal-gain order, dropping lowest gain first** —
   it is the objective's own ranking and requires no new heuristic.
3. **Truncation signal is actionable.** `truncated=True` plus `chars_wanted`,
   `episodes_dropped`, and the identity of what was dropped. A boolean alone lets a
   caller know something happened and not what.
4. **Degradation is graceful and tested at the boundary.** Budgets at, just below,
   and far below what selection wants. Including the pathological case: a budget
   smaller than a single episode.
5. **Report before block.** `chars_wanted` is computed from the unconstrained
   selection, so the caller can see the shortfall size, not just its existence.

## 1.3 Tests

| # | Test | Certifies |
|---|---|---|
| E1 | Sweep budgets 1k–64k on the Study 010 store; assert `chars_delivered ≤ budget` at every point | Ceiling holds |
| E2 | Every budget where selection wants more sets `truncated=True` | Signal fires |
| E3 | No budget where selection fits sets `truncated=True` | No false positives |
| E4 | Budget smaller than the smallest episode returns an empty block, `truncated=True`, no exception | Pathological case |
| E5 | Drop order deterministic across two processes, fixed seed | Reproducibility |
| E6 | At 32,000 the E005 primary vector still reproduces: 12/17 · 4/4 · 16/16 @ 31,569 chars | **Enforcement changed nothing at the operating point** |

**E6 is the replay gate.** The primary ran at 31,569 of 32,000, so enforcement should
be inert there. If the number moves, enforcement changed selection and the cause must
be found before merge.

## 1.4 Surrogate audit

| Check | Certifies | Can it pass falsely? | Mitigation |
|---|---|---|---|
| `chars_delivered ≤ budget` | budget respected | **Yes — by delivering nothing** | Always report with `episodes_delivered`; E6 pins the operating point |
| `truncated` set | caller can act | Yes — a flag with no content | Signal must carry wanted-vs-delivered and dropped identities |
| Boundary tests pass | graceful at all budgets | Yes — tested budgets are a sample | Sweep, not spot-check; include adversarial small values |

---

# PART 2 — CC-004: RESTART PERSISTENCE

Closes `CC_001` O4.

## 2.1 The gap

The checkpoint path exists and has run exactly once, in an incident: Study 010 Arm L
resumed from its turn-500 checkpoint after the process was reaped at turn 597. **A
path that worked once under lab conditions is not a guarantee.** A deployed agent
restarts constantly.

## 2.2 Requirements

1. **Durable append.** A turn acknowledged by `append()` survives process kill.
   Specify the durability point — after fsync, or after the write returns — and
   document it. Do not leave it implicit.
2. **Identical context after restart.** For the same query and budget, `context()`
   returns a **byte-identical** block before and after a restart. This is the real
   guarantee; everything else is mechanism.
3. **Embedding cache survives**, or is rebuilt deterministically. If rebuilt, the
   rebuild must reproduce vectors exactly — under the H1 pinned call shape from
   CC-002, since batch-versus-single embedding produces materially different vectors.
4. **Crash-consistency.** A kill mid-write leaves a store that opens without manual
   repair. Torn writes are detected, not silently accepted.
5. **Config check on open.** Reopening under a mismatched `EpisodicConfig` fails
   loudly. A store's measured properties hold only under the config that produced it.

## 2.3 Tests

| # | Test | Certifies |
|---|---|---|
| P1 | Append n turns, `SIGKILL`, reopen: all n present and verbatim | Durability |
| P2 | Same query and budget pre/post restart: byte-identical block | **The core guarantee** |
| P3 | `SIGKILL` mid-`append`: store opens, last turn either fully present or fully absent — never partial | Crash consistency |
| P4 | Embedding cache dropped and rebuilt: vectors bit-identical | Rebuild determinism |
| P5 | Reopen with altered config: raises | Config integrity |
| P6 | 100 restart cycles: no drift, no growth in open time | Repeated restart |

**P2 pairs with a content check.** Byte-identical blocks are also produced by two
empty stores; assert non-empty and fact-bearing.

---

# PART 3 — CC-005: EVICTION AND STORE GROWTH

Closes `CC_001` O5. **Design gated on Part 0.**

## 3.1 What is actually unbounded

Three growth paths, and they are not the same problem. Conflating them is why this
looked like one item.

| Path | Grows with | Current state | Real limit |
|---|---|---|---|
| **Context window** | turn count | Part 0 answers this | If H-A, bounded by budget; if H-B/C, a leak to name |
| **Disk / store size** | turn count, linearly | Unbounded, no policy | Cheap. 18,951 distilled characters at 1,000 turns; raw is larger but still small |
| **Retrieval latency** | store size, linearly | **Unbounded and the real constraint** | ~40 µs/candidate, exponent 0.96; DR-002 projects ~40 ms at 1,000 candidates and **~400 ms at 10,000** |

**Latency is the binding growth constraint, not disk and probably not context.**
At 10,000 turns a full-store candidate pool costs roughly 400 ms per query, of which
clustering is ~73%. That is the number that ends continuous operation, and it is the
one this program has never treated as an eviction driver.

## 3.2 The tension eviction must respect

DR-002 established that **pool trimming is unsafe**: dropping the 19 lowest-cosine
episodes from a 119-pool cost an entire domain and all oracle overlap, despite 4 of 5
oracle episodes surviving the cut. A3 clusters over the pool, so removing the tail
reshuffles the objective rather than removing options.

**Therefore eviction cannot be "drop low-similarity episodes."** That is exactly the
operation shown to destroy domain coverage. Any eviction policy must be evaluated
against domain coverage, not against a similarity threshold.

## 3.3 v0 policy — stated, not implemented

**Default: unbounded retention. No eviction.**

This is a policy, and stating it is the deliverable. The README documents:
- Disk growth per turn, measured.
- Latency at 1,000 and 10,000 candidates, measured and projected with the projection
  labelled as such.
- The horizon at which latency becomes unacceptable, with the threshold stated.
- **That trimming is unsafe and why**, with the DR-002 artifact reference.

## 3.4 What to build instead of eviction

Since latency is the constraint and trimming is unsafe, the two honest options are:

1. **Bounded-cost candidate generation that is not similarity-trimming.** Out of scope
   here; note it as the open question it is. ANN was already refuted at synthetic
   scale (bakeoff T5).
2. **Archival with explicit reload.** Episodes past a horizon move to cold storage
   and are excluded from the pool by an explicit, caller-visible policy — not
   silently. The caller knows the memory has a horizon.

**Recommendation: ship neither in v0.** Document the limit, measure it, and let real
use determine whether 400 ms at 10,000 turns is a problem worth solving. Building an
eviction policy before anyone has hit the wall is speculative work of exactly the
kind this program has spent a year learning to avoid.

## 3.5 Deliverables

- [ ] Measured disk growth per turn
- [ ] Latency curve to the largest store available, with projection labelled
- [ ] README growth section with the stated policy and the unsafe-trimming finding
- [ ] `unsafe_` prefix retained on any trimming API
- [ ] **No eviction implementation in v0**

---

## 4. Sequencing

1. **Part 0 (DX-002)** — offline, gates Part 3, may block Part 1 if branch B fires.
2. **Part 1 (CC-003)** — the correctness gap. Largest value.
3. **Part 2 (CC-004)** — restart.
4. **Part 3 (CC-005)** — documentation and measurement, no implementation.

Each is its own PR with its own gates. Part 0's result is committed before Part 3's
README section is written.

## 5. Definition of done for the library

After these three, `CC_001`'s obligations stand as: O1 enforced, O2 implemented, O3
measured, O4 guaranteed, O5 stated. **O6 — runtime independence — remains open and
unmeasured**, and the README must say so. Every number is from one model, one quant,
one machine.

---

*Drafted August 1, 2026. CC-002 complete at PR #28; suite green at 804. Shipping
configuration `A3_l0.1_r0.0_k16`: 12/17 · 4/4 · 16/16 @ 31,569 of 32,000 chars.*
