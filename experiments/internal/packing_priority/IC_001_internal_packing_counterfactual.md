# IC-001 — Internal Packing-Priority Counterfactual

**Type:** Offline counterfactual replay. Single variable. **Not a recalibration of the arc.**
**Repository:** `contextDecayWindow` · `experiments/internal/packing_priority/`
**Branch:** `ic/001-packing-priority`
**Status:** DRAFT — ready for handoff on commit
**Depends on:** EC-002 (PR #40) · CC-006 vector cache contract · AR-001 · E005 · DR-002
**Companions:** `PAPER_001.md` · `RETRIEVAL_MECHANISM_LEDGER.md` · `EC_002_REPORT.md`

---

## 0. Purpose, and what this is not

EC-002 established on external data that packing priority is a causal delivery gate:
flipping recency-first to K-first raised any-evidence-session recall from 109/470 to
261/470, with **152 gains and zero losses**, and raised delivered K episodes from
**26 to 476** across 500 questions. The similarity path was computing correct
candidates and being denied window space.

**Every study in this program's record ran recency-first.** Whether that starved the
internal corpus the same way is unmeasured.

**This document tests one question on one probe.** It is explicitly *not* a rerun of
the arc. §5 records why most of the graveyard cannot be rescued by packing order, and
§6 sets the conditions under which any broader recalibration would be authorized.

**Scope discipline is the point.** The temptation after EC-002 is to rerun everything.
That is months of compute against a hypothesis that has not been tested once
internally.

---

## 1. The question

> **On the internal corpus, does packing K before recency change what reaches the window?**

**The prior is that the effect should be smaller here.** EC-001's histories are 30–40
discontinuous sessions, where the recency window holds the most recent session and the
answer often lives twenty sessions back. The internal corpus is one continuous
121-turn conversation, where recent turns and relevant turns overlap far more.
Recency-first looked defensible for eleven studies because on that corpus it largely
was.

**Smaller is not zero, and "should be" is a hypothesis.** AR-001 is the sharpest
available test of it.

## 2. Why AR-001 is the right probe

| Fact | Value | Source |
|---|---|---|
| Q11 optimum, 14/17 facts | 5,058 exactly-serialized characters | AR-001 |
| Q11 optimum, 17/17 facts | 7,592 characters | AR-001 |
| Greedy oracle | 15/17 at 5,455 characters | AR-001 |
| Deployed selection | 6/17 while spending ~31,946 characters | PAPER-001 §5 |
| Budget | 32,000 characters | Study 007 |

**Deployed selection spent roughly six times the optimum's cost to deliver less than
half its facts.** If most of that spend was the recency window, then a share of what
PAPER-001 §5 attributes to *selection* is attributable to *packing priority*, and the
decomposition needs revising before the paper goes anywhere.

That is a direct, cheap, offline test against a committed artifact.

## 3. Method

Offline replay. **No inference, no new embedding calls, no mechanism change.**

**Arms.** Identical in every respect except fill order:

| Arm | Packing order |
|---|---|
| **B0** | recency → K → coverage *(the deployed order, carried since Study 001)* |
| **B1** | K → recency → coverage *(EC-002's A1 order)* |

**Held fixed:** store, vectors, K threshold (0.48), N recency cap, selector and its
parameters, 32,000-character budget under exact serialized cost via the post-DR-001
renderer, measurement code, seed 5005.

**Vector cache.** Read-only against the CC-006-protected cache, with the file and
canonical content hashes asserted before and after. **Zero new model calls, zero
misses.** EC-002's pattern exactly; a recomputation here would reintroduce the
EC-001 problem where nominally identical embedding moved a rank and a block boundary.

**B0 gate, binding.** B0 must reproduce the committed deployed result — 6/17 with
per-domain breakdown — before B1 output is opened. **A failed B0 gate stops IC-001.**
The delta is uninterpretable without it, per the DR-001/G-R1 discipline.

**Reported, per arm:**
1. Q11 facts available, and per-domain counts.
2. Characters delivered, split by path: recency, K, coverage.
3. Episodes delivered by path.
4. Oracle-set overlap: which of the five optimum episodes each arm delivered.
5. Paired per-question gains and losses, not aggregate difference.
6. **The targeted probes Q1–Q8, both arms.**

**Item 6 is not optional.** LV-001 killed the shipped configuration on a targeted
regression that offline availability had scored 16/16. K-first reorders what recency
delivers; the opening turns that LV-001 found missing are exactly the material a
recency-first order protects. **If K-first improves breadth by displacing early
recency episodes, IC-001 has reproduced the LV-001 failure and must say so.**

## 4. Decision rule — commits before B1 output is opened

Git-verifiable, per standing protocol.

| Branch | Condition | Verdict | Consequence |
|---|---|---|---|
| **A** | Q11 availability rises materially **and** Q1–Q8 availability does not fall | **PACKING IS A GATE INTERNALLY TOO** | PAPER-001 §5's decomposition must be revised — some selection attribution is packing attribution. §6's recalibration conditions become live |
| **B** | Q11 unchanged or trivially changed | **RECENCY–RELEVANCE OVERLAP ABSORBED IT** | The internal corpus did not have the external failure. §5 stands. **No recalibration.** A publishable boundary condition on EC-002's finding |
| **C** | Q11 rises **and** Q1–Q8 falls | **TRADE, NOT A GAIN** | The LV-001 pattern reproduced offline. Report both. No promotion, no recalibration on availability alone |
| **D** | Q11 falls | **RECENCY WAS LOAD-BEARING HERE** | Strengthens §5's selection attribution. Record and stop |

**No materiality threshold is registered**, matching EC-002's treatment. Report exact
paired counts. **Do not convert a paired count into a significance claim** — the
program has no variance estimates anywhere.

## 5. Why the graveyard mostly stays closed

Recorded now so a Branch A result does not become a general licence.

**Cannot be rescued by packing order** — these failed upstream of delivery:

| Entry | Failure locus |
|---|---|
| Dreaming / distillation | Write-time formation. Never produced the records to deliver |
| Promotion filters | Weighted route structurally unreachable |
| Density, IDF | Ranked the target spans 89th–316th at formation |
| Topic layer | Structural collapse — 12 domains into 2 at 1,000 turns |
| Query routing | Oracle ceiling 6.09% with perfect information |
| Graph edges | Failed the advancement gate before delivery |
| ANN | Recall degraded at synthetic scale |

**Could be availability-mediated, and are therefore candidates *only* under §6:**
Studies 003–007's LTM read path, Study 009's 9.0-vs-12.0 contrast, Study 010's
breadth-only finding, E005's selector arms.

**The distinction that matters:** a mechanism that never formed the right record
cannot be helped by delivering records differently.

## 6. Conditions for any broader recalibration

**Branch A is necessary and not sufficient.** All of the following must hold before a
second internal replay is scoped:

1. Branch A, with Q1–Q8 not falling.
2. The candidate list is drawn **only** from §5's availability-mediated set.
3. **Each candidate is a separate registered replay**, one at a time, not a survey.
   The retrieval bakeoff's nine tiers took months; this must not become that.
4. **Availability is not a verdict.** LV-001 measured 16/16 offline against 1.5/8 live.
   A recalibration reporting only availability establishes that a mechanism *could*
   have delivered, never that it *would* have worked. Any verdict change requires a
   live run, separately registered.
5. Muzaffer authorizes explicitly, with the compute cost stated.

**Say plainly in the report:** re-running seven studies live is a different order of
budget than one offline replay, and arrives after a decision to move toward a product.

## 7. Surrogate audit

| Check | Certifies | Can it pass falsely? | Mitigation |
|---|---|---|---|
| Q11 availability rises | the mechanism is better | **Yes — LV-001 is the proof** | Branch A is availability only; §6.4 forbids a verdict without a live run |
| Aggregate delta | per-question improvement | **Yes — EC-002's medians were identical while aggregates moved 18×** | Paired gains and losses, never aggregate difference alone |
| Q1–Q8 unchanged in total | no targeted regression | Yes — aggregates hide per-probe swings | Per-probe reporting on all eight |
| B0 reproduces 6/17 | the replay is faithful | Yes — the count could match with different episodes | Assert delivered episode identities, not just the fact count |
| Path character split | recency was the consumer | Yes — a path can be large and irrelevant | Report path split *and* oracle-set overlap together |

**Accepted residual:** one probe, one store, one run, no variance. IC-001 can show
that packing priority moved availability on Q11. It cannot show that Q11 is
representative — the program has exactly one breadth probe, and PAPER-001 §8.2 already
concedes a single probe cannot support a claim about enumeration in general.

## 8. Deliverables

- [ ] Decision rule committed before B1 output is opened — SHA recorded
- [ ] B0 gate: committed deployed result reproduced, episode identities asserted
- [ ] Cache hashes asserted before and after; zero new model calls, zero misses
- [ ] Per-arm Q11 facts and per-domain counts
- [ ] Character and episode split by path, both arms
- [ ] Oracle-set overlap, both arms
- [ ] Q1–Q8 per-probe, both arms
- [ ] Paired gains and losses
- [ ] Branch verdict
- [ ] `PAPER_001.md` §5 updated **in either direction**, per the both-outcomes rule
- [ ] Ledger entry; `README.md` and `AGENTS.md` digest in the same PR
- [ ] `ERRATA.md` if any committed number moves

---

*Drafted August 3, 2026. EC-002: any-session recall 109/470 → 261/470, 152 gains 0
losses, delivered K episodes 26 → 476, PR #40, suite 1,093. AR-001: 14/17 at 5,058 of
32,000 characters. Deployed: 6/17 at ~31,946 characters.*
