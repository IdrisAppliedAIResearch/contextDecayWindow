# LV-001 — Live Validation of the Shipping Selection Configuration

**Status:** PRE-REGISTERED, NOT RUN. Awaiting authorization.
**Family:** LV (live validation) — new prefix, registered in `AGENTS.md` §8.
**Prior result under test:** E005 `A3_l0.1_r0.0_k16`, PROMOTION_ELIGIBLE offline.
**This document contains no implementation files.** Its commit SHA is the
integrity anchor for anything LV-001 later produces.

---

## 0. Why this exists

PAPER-001 hedges in the same place at least six times: every selection number in
it is *availability* — whether a fact's text reached the window — and not answer
correctness. §6 opens by stating that no live run of the shipping configuration
exists. The hedging is honest and it is also the paper's largest structural
weakness, because the central artifact is an offline count that has never been
shown to matter to a model's output.

One 121-turn inference run converts that count into a measured result, or shows
that it does not convert. Either outcome is worth more than the hedge.

**E005's disposition says "no live run is authorized."** This pre-registration
is the authorized design that requirement asks for. It does not itself
constitute authorization; §7 records what authorization means here.

---

## 1. Question

Does the shipping configuration's offline availability advantage — 12 of 17
breadth items against the deployed baseline's 6 — produce a better *scored
answer* in a live conversation at the same budget, same seed, same model?

The program's most durable positive result is that the model used what it
received: at the hardest probe it used all 10 available facts and invented none.
LV-001 tests whether that relationship survives roughly doubling what is
delivered, which is not guaranteed. More material in the window can also dilute
attention or invite fabrication, and nothing on record rules that out.

---

## 2. Arms

Two arms, one seed, one corpus, one model.

| Arm | Selection | Provenance |
|---|---|---|
| **L-A0** | Deployed baseline: N-cap union K pre-filter, per-item cosine ranking | Control, run from checked-out prior code in a separate worktree (`AGENTS.md` §4) |
| **L-A3** | `A3_l0.1_r0.0_k16` over the full eligible store, via `episodic` | Treatment |

Both arms use the 121-turn scripted corpus, the rubric locked since Study 002,
budget 32,000 characters at exact serialized cost, seed 5005, `--parallel 1`,
speculative decoding disabled, Qwen3-Embedding-0.6B, and the generation model
and quantization recorded in the run header.

**L-A0 must not be produced by disabling features in the current runner.** That
is a flag-disabled arm and `AGENTS.md` §7 forbids it.

---

## 3. Bars, registered before any run

### B1 — Primary: does availability convert to correct answers?

**Measure.** Q11 correctly-attributed target facts in the model's turn-120
answer, scored against `q_facts_key.md` under the locked rubric, three blind
passes.

**Registered prediction.** L-A3 > L-A0.

**Outcome rule, fixed now.**

| Result | Verdict |
|---|---|
| L-A3 exceeds L-A0 by ≥ 3 items | **CONVERTS.** The offline count predicts live answer content |
| L-A3 exceeds L-A0 by 1–2 items | **WEAK.** Directionally right, inside the noise of a single unreplicated run; the paper's hedging stays |
| L-A3 equals L-A0 | **DOES NOT CONVERT** |
| L-A3 below L-A0 | **INVERTS.** Delivering more hurt. This is a publishable negative result and the paper must say so in §5.1 |

The 3-item threshold is set at half the offline gap (6 items) before any live
number exists, and is not to be revised afterwards.

### B2 — No regression on what already works

**Measure.** Targeted probes Q1–Q10, scored total.

**Rule.** L-A3 must not fall more than 0.5 below L-A0. Offline, both preserve
16 of 16 targeted items, so a live targeted regression means the coverage
objective costs accuracy that per-item ranking did not — which would outweigh
any B1 gain. **A B2 failure kills the promotion regardless of B1.**

### B3 — Fabrication

**Measure.** Count of asserted facts in each arm's turn-120 answer with no
support in the delivered context.

**Rule.** Descriptive, no threshold. Registered because roughly doubling
delivered material is exactly the condition under which fabrication would be
expected to rise, and the program has never measured it under that condition.
Recording it without a bar is honest; inventing a bar now would be a surrogate.

---

## 4. Gates, all binding, all before inference

| Gate | Certifies | Blocks on failure |
|---|---|---|
| **G1** | Probe-order validator passes: every rubric-required fact is planted in a scripted turn strictly before its probe | Artifact lock |
| **G2** | Byte-identical seeded-prefix rerun for both arms | Inference |
| **G3** | **Call-shape re-verification.** `store.context()` embeds the query alone; E005's committed result embedded nine queries in one batch. The primary configuration is not among the 6 of 146 payloads that difference flips, but that must be re-checked under the live path rather than assumed (PAPER-001 §7.2) | Inference |
| **G4** | Leakage audit: retrieval, formation, ranking and gating code reads no rubric artifact. Grep, import-graph, planted violation | Inference |
| **G5** | Control provenance: L-A0's worktree is at the prior commit, tree clean, script hashes match | Inference |
| **G6** | 35-turn ablation completes for both arms with no budget breach and no `truncated=True` on a turn whose selection fits (`AGENTS.md` §4 requires an ablation before a 120-turn run) | The 121-turn run |

---

## 5. Surrogate audit, before implementation

`AGENTS.md` §3: before implementing any gate, ask whether it can pass while the
property it certifies is false.

| Check | Can pass falsely by | Mitigation registered here |
|---|---|---|
| B1 fact count rises | The extra facts coming from **prior probe answers that were themselves wrong** — PAPER-001 §5.1.1 records that four of five known-optimum episodes are prior answers and that this probe's earlier answers were largely wrong | Score **attribution correctness against the plant key**, not string presence. An item restated inside a wrong answer scores zero |
| B1 rises but the answer is worse | Counting items while ignoring coherence | Record the full rubric score beside the item count; both are reported, neither alone |
| B2 passes | Targeted probes being easy for both arms and insensitive | Report per-probe, not the total alone. 60 of 60 targeted facts were delivered at 1,000 turns, so a ceiling here is expected and must not be read as evidence of anything |
| G2 passes | A rerun that reproduces because nothing is stochastic in the path measured | Assert the prefix over generated tokens, not over the retrieval block |
| B3 shows zero fabrication | The scorer only looking for fabrications it expects | Scored blind against the delivered block, by an adjudicator who does not see the arm label |

---

## 6. What this does not authorize

- No parameter tuning. `A3_l0.1_r0.0_k16` is frozen; the sweep is closed.
- No third arm, no second seed, no corpus change.
- No revision of B1's thresholds after any live number exists.
- No conclusion about *breadth in general*: this is still one enumeration probe
  on one corpus, and a CONVERTS verdict would not change PAPER-001 §8.2.
- No promotion of E006 or any objective work. The residual at cosine 0.056
  remains out of scope.

---

## 7. Authorization and prerequisites

**Authorization.** Muzaffer, as program owner, is the authorizing authority.
E005's "no live run is authorized" stands until this document is approved and
that approval recorded here.

**Runtime prerequisites, not present in the repository.** The generation model
and embedding model are gitignored (`*.gguf`, `models/`), and no llama.cpp
server binary is present. LV-001 cannot be executed from a clean checkout; it
needs the machine that carries the program's runtime.

**Estimated cost.** Two 121-turn runs plus a 35-turn ablation per arm, at the
recorded throughput. Scoring is three blind passes over 14 probes per arm.

---

## 8. Reporting

Whatever the outcome, LV-001 reports:

1. The verdict from B1's table, quoted from §3 rather than restated.
2. Per-probe scores for both arms, committed before any mechanism log is opened
   (`AGENTS.md` §4: git order is the evidence).
3. What PAPER-001 must change. If **CONVERTS**, §5's availability hedging is
   replaced by a measured result and §6's opening sentence is deleted. If
   **DOES NOT CONVERT** or **INVERTS**, §5.1's availability note is promoted
   from a caution to a finding, and the paper's central claim narrows from "the
   decomposition explains delivery" to "the decomposition explains delivery,
   which does not predict answers."

The third row is the point of pre-registering it. Both outcomes are written
down now, so neither can be discovered to have been the expected one.
