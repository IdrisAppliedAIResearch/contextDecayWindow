# Study 011 — Amendment 001

## Determinism Gate Failure, and Instrument Noise-Band Characterization

**Type:** Standalone amendment. **The locked pre-registration is not edited.**
**Amends:** `experiments/study_011/pre_registration.md`, SHA-256 `350d9763691c93b2e057cc0c10bdd7f19d8a78c7e169f9e40ef0571d69e5e7f4`
**Repository:** `contextDecayWindow` · `experiments/study_011/amendments/`
**Status:** **AUTHORIZED** — August 9, 2026. Both phases may run.
**Raised:** August 7, 2026, **after results.** §1.2 states why, and what that costs.
**Authorization note:** the two corrections the implementing agent flagged on commit
were resolved in the text below before authorization, not after. The superseded
draft is `69097caa`; the resolution record is at the foot of this file.

---

## 1. What is being amended, and what is not

### 1.1 The registered gate that failed

Study 011 §5 registers: *"Determinism spot-check is a gate."*

**The gate failed.** The same 757-byte prompt, byte-identical, produced two
different responses at seed 5005 with `--parallel 1` and speculative decoding off,
in the same server process. The responses diverge at character 79 — 343 characters
against 80.

**The gate was never run in its registered position.** It was implemented and
executed last — after every arm was run, scored, unsealed and reported. Git order is
the evidence:

| Commit | |
|---|---|
| `2fd90dbe` | scores unsealed and committed |
| `29f34b30` | report written, B1 FAIL |
| `3f4bf300` | determinism spot-check *implemented* |
| `4b43ccfd` | determinism spot-check *run*; it fails |

So the deviation is not that anyone proceeded past a known failure. The failure was
not known, because the gate had not been executed. **A gate run after the fact cannot
stop anything**, which makes this the more serious of the two deviations available to
describe, and it is disclosed here rather than absorbed into the report.

What is defensible is only what happened next: the gate as written did not specify
what to do when non-reproducibility is a property of the runtime rather than a defect
in the harness, and retracting would have discarded four completed live runs whose
**offline, deterministic** results — the gates, the delivery counts, the packing
measurements, Arm D's identity to Arm A — reproduce exactly and are unaffected.
**It is still a deviation, and the sequencing failure is not excused by it.**

### 1.2 The bar does not move — permanently

> **B1 fired. Arm C scored 7.0 against Arm D's 8.0. The packing correction is not adopted. That verdict is final and this amendment cannot change it.**

This must be stated at the top because of what the amendment does next. Measuring an
instrument's noise band **after** a bar has fired, on a study whose bar fired by one
point, is structurally identical to the illegitimate pattern the program's own rules
name: *reinterpreting a bar to convert FAIL to PASS*.

**The distinction that makes this legitimate, and it is the only one:**

- **Not permitted, and not done here:** using the band to argue Arm C did not really
  lose, or to re-open adoption of K-first packing.
- **Permitted:** characterizing what a one-point difference on this instrument means,
  as a property of the instrument, applied uniformly to every committed result
  including those the program likes.

**Enforcement.** The band result may not be cited in support of any adoption decision
for K-first packing. Any future adoption of K-first requires a new study with its own
pre-registration and its own bar. This clause is part of the amendment and is binding.

### 1.3 Legitimacy test, applied honestly

| Criterion | Assessment |
|---|---|
| Corrects a measurement | **Yes.** It characterizes an instrument property that was assumed and never measured |
| Fixes a registered contradiction | **Yes.** §5 registers a gate the runtime cannot satisfy |
| Makes passing harder or neutral | **Yes.** It can only widen uncertainty. It rescues nothing — §1.2 forbids the only rescue it could perform |
| Raised before results where possible | **No.** Raised after. This is the weak clause and it is not glossed |

**Three of four.** The failing clause is disclosed, not argued away.

---

## 2. Why this is program-wide, not Study 011's problem

Study 011's registered runtime is the program's standing runtime, carried since
Study 005: Qwen3.6 27B UD-Q6_K_XL, llama.cpp build 9294, seed 5005, `--parallel 1`,
speculative decoding off, temp 1 / top-p 0.95 / top-k 20 / min-p 0.

**Every live study in the arc ran on it.** Every one used a single run per arm. If the
runtime does not reproduce, then **every scored comparison in the program's record is
a single sample from a distribution that has never been measured** — including:

| Result | Gap | Currently reads as |
|---|---:|---|
| Study 009 same-seed contrast, S vs L | 3.0 | The arc's "clean architectural number" |
| LV-001 targeted regression | −2.0 | The kill that un-promoted A3 |
| Study 011 B1, C vs D | −1.0 | The kill in this study |
| The corrected treatment series, 8.5 → 12.0 | 3.5 | The arc's headline improvement |

**Unaffected**, and worth stating so the amendment's scope is not over-read: every
offline, deterministic result. Gate outcomes, delivery counts, character accounting,
packing measurements, EC-002's 152-gains-zero-losses, IC-001's zero-K-at-8-of-8, and
Arm D's per-question identity to Arm A with byte-identical windows at turns 117, 118,
119. **Those are identity and count comparisons, not score comparisons, and noise does
not touch them.**

---

## 3. Phase 1 — Sampling-mode determinism probe

**Cheap. Hours. Runs first because it can change Phase 2's design.**

### 3.1 Hypothesis

Stochastic sampling is the likely amplifier. Temp 1 with top-p 0.95 and top-k 20
samples from a distribution; a fixed seed makes the RNG reproducible, but GPU
reduction order is non-associative, so logits can differ in their low bits between
runs. Under stochastic sampling a low-bit difference can change the sampled token, and
once one token differs every subsequent token does.

**Under greedy decoding (temp 0) a low-bit logit difference almost never changes the
argmax.** If that is the mechanism, greedy should be reproducible where sampling is
not.

**This is a hypothesis about llama.cpp on this hardware, not an established fact.**
Phase 1 tests it.

### 3.2 Method

No 121-turn runs. A fixed prompt set, repeated generation, byte-identity comparison.

1. Fix a prompt set of at least 20 prompts drawn from committed Study 011 windows.
2. For each, generate **10 times** under the standing runtime (temp 1). Record
   byte-identity across repeats and the position of first divergence.
3. Repeat under **temp 0 / greedy**, all else identical.
4. Repeat under temp 0 in a **freshly started server process** for each generation, to
   separate within-process from across-process reproducibility.

**Report:** identity rate per condition, first-divergence position distribution, and
whether divergence is within-process, across-process, or both.

### 3.3 What Phase 1 does not authorize

**Phase 1 does not change the standing runtime.** Temp 0 is a different runtime and
would break comparability with every prior study. If greedy is reproducible, that is a
finding about what *future* studies could adopt, registered separately, with the
comparability cost stated.

**Phase 2 runs at temp 1 regardless of Phase 1's outcome**, because Phase 2's purpose
is to characterize the instrument the existing record was produced on.

---

## 4. Phase 2 — Noise band on the deployed configuration

### 4.1 Design

**Arm D, the deployed configuration, repeated N = 5 times.** Identical corpus,
identical settings, identical seed, standing runtime, temp 1.

Arm D is chosen because it is the reference arm for every registered contrast in
Study 011 and the closest thing the program has to a production configuration.

**Each run is scored under the full protocol**: three blind raters, calibration gate
including a planted `NO_ANSWER` at 0.0, blind packets committed before any rater runs,
scores committed before any mapping is unsealed.

**Rater departure carried forward and disclosed:** Study 011 used `claude-opus-5`,
`claude-sonnet-5`, and `claude-haiku-4-5-20251001` — three distinct models, **one
family**, against a registered requirement of distinct families. Phase 2 must either
secure a second family or disclose the same departure. **Shared-family bias is the
surrogate §7 of the pre-registration names for "three raters agree," and it inflates
apparent agreement**, which in a noise-band measurement means understating the band.

### 4.2 Reported

1. Every individual run's total, **listed, not summarized**.
2. Full range: min, max, max−min.
3. Standard deviation, **with the caveat that n = 5 estimates it poorly**.
4. Per-question variability: which of the thirteen questions move across runs and which
   are stable. **A band concentrated in two questions means something different from a
   band spread across all thirteen.**
5. Rater disagreement per run, separated from run-to-run variation. These are two
   distinct noise sources and must not be pooled.

### 4.3 Decision rule — commits before any run is scored

| Band (max−min) | Reading | Consequence for the record |
|---|---|---|
| **< 0.5** | The instrument resolves one-point differences | Committed verdicts stand as written. Study 011's −1.0 and LV-001's −2.0 are interpretable |
| **0.5 – 1.5** | One-point differences are not interpretable; three-point differences are | Study 011's −1.0 and LV-001's −2.0 are re-read as **not demonstrated**. Study 009's 3.0 and the 3.5 series improvement stand |
| **> 1.5** | Nothing below ~3 points is interpretable | **Most of the arc's scored verdicts are re-read as undetermined.** Study 009's 3.0 is marginal. `PAPER_001.md` requires a structural revision, not a caveat |
| **Runs not comparable** | e.g. an arm fails to complete | Report and stop. Do not estimate from fewer than N |

**Applied uniformly.** The band is not applied selectively to results the program would
prefer to keep. §1.2's prohibition on rescuing Arm C is the mirror of this clause:
neither direction gets special treatment.

---

## 5. Surrogate audit

| Check | Certifies | Can it pass falsely? | Mitigation |
|---|---|---|---|
| Band computed from N runs | the instrument's true spread | **Yes — five runs can cluster by chance and understate it** | Report every individual score and the full range; treat the SD as indicative only |
| Band measured on Arm D | applies to all arms | **Yes — noise may be configuration-dependent** | State as a limitation. The band is measured on one configuration and applied to others by assumption |
| Three raters agree | scoring is stable | Yes — one family inflates agreement | §4.1; separate rater disagreement from run-to-run variation in reporting |
| Temp 0 reproduces in Phase 1 | the mechanism is identified | Yes — could reproduce for an unrelated reason | Test within-process and across-process separately (§3.2.4) |
| Band < 0.5 | prior verdicts are safe | Yes — a tight band on Arm D says nothing about arms that diverge more | Same limitation as row 2; state it wherever the band is cited |

**Accepted residual:** n = 5 on one configuration on one corpus. This measures whether
the instrument *can* resolve the differences the program has been reporting. It does
not establish the band for any other arm, corpus, or budget.

---

## 6. Cost, and what it buys

Phase 1 is hours. Phase 2 is **five live 121-turn runs plus three-rater scoring** —
comparable to Study 011 itself, arriving after a decision to move toward a product.
Stated plainly, as the standing rule requires.

**What it buys:** the ability to say whether any scored study in this program measured
what it claimed. Without it, every future scored study inherits the same problem, and
the paper's entire §5 rests on differences the instrument may not resolve.

**Sequencing note:** if Phase 1 shows greedy decoding is reproducible, the highest-value
follow-on is a separately registered decision about whether the program's future
runtime moves to temp 0 — accepting the comparability break with eleven studies in
exchange for an instrument that can reproduce a run. **That decision is not made here.**

---

## 7. Deliverables

- [x] This amendment committed and **explicitly authorized** before any phase runs
- [x] §1.2's non-rescue clause recorded in `verdict.json` and the Study 011 report
- [x] Phase 1: identity rates and divergence positions, all conditions
- [x] Phase 2 decision rule committed before any run is scored — SHA recorded
- [x] Phase 2: five runs, every individual score listed
- [x] Full range, per-question variability, rater disagreement reported separately
- [x] Band verdict against §4.3
- [x] **Uniform retrospective application** to Study 009, LV-001, Study 011, and the
      corrected series — in whichever direction the band points
- [x] `PAPER_001.md` §8 limitations revised; structural revision if the band exceeds 1.5
- [x] `ERRATA.md` entries for any committed verdict whose reading changes
- [x] Ledger, `README.md`, `AGENTS.md` digest; one PR

---

*Drafted August 7, 2026; authorized August 9, 2026. Study 011: A 8.0, B 7.5, C 7.0, D 8.0; B1 FAIL, correction not
adopted. Determinism: byte-identical 757-byte prompt, divergence at character 79, seed
5005. Arm D scored identically to Arm A on all thirteen questions with byte-identical
windows at turns 117, 118, 119 — unaffected by this amendment.*

---

## Resolution record — the two flagged corrections, resolved before authorization

*The implementing agent flagged two corrections on commit and left the author's
text standing, per the standing rule against silent repair. Both concerned §1.3's
honesty ledger, so both were resolved in the text above **before** the amendment
was authorized. The superseded draft is commit `69097caa`; this record states what
changed so the diff is not the only account of it.*

**1. §1.1 mischaracterized the deviation, in the study's favour — corrected.** The
draft said "the study proceeded past a failed gate and scored four arms." That is
not what happened, and it describes the lesser failure. The determinism spot-check
was not run before the arms at all: it was implemented and executed after every arm
was run, scored, unsealed and reported (`2fd90dbe` → `29f34b30` → `3f4bf300` →
`4b43ccfd`). §1.1 now states the actual deviation — **a registered gate was not run
in its registered position** — and says why that is worse: a gate run late cannot
stop anything.

**2. The date was wrong, in the direction that flattered the amendment — corrected.**
The draft's header and footer said **August 6, 2026**, but the results it cites
(A 8.0, B 7.5, C 7.0, D 8.0) did not exist until August 7, and the determinism
failure it is built on was measured on August 7 (`4b43ccfd`). Both now read
**August 7, 2026**. §1.3's *"raised before results where possible"* still answers
**No**; the correction removes an inconsistency, not the failing clause.

**Neither correction changed any phase, method, decision rule, or the §1.2
non-rescue clause.** Authorization on August 9, 2026 covers Phase 1 and Phase 2 as
written above, and nothing else.

---

## Execution record

| Deliverable | Artifact |
|---|---|
| §1.2 non-rescue clause recorded | `experiments/study_011/evaluation/verdict.json`, `experiments/study_011/study_011_report.md` |
| Phase 1 | `experiments/study_011/runtime/phase_1_sampling_determinism.json` |
| Phase 2 decision rule, committed before scoring | `experiments/study_011/noise_band/DECISION_RULE.md` |
| Phase 2 runs | `experiments/study_011/noise_band/runs/` |
| Phase 2 scoring | `experiments/study_011/noise_band/evaluation/` |
| Band verdict and uniform application | `experiments/study_011/noise_band/band_verdict.json`, `experiments/study_011/noise_band/NOISE_BAND_REPORT.md` |

### Phase 1's outcome, recorded against this amendment's own premises

*The text above is left as authorized. Phase 1 undercuts two of its statements, and
those are recorded here rather than edited into the argument that produced them.*

**820 generations, five conditions, zero divergence** — including twenty replays of
the exact 757-byte prompt whose divergence §1.1 cites, all of which reproduced the
ablation's committed response byte for byte.

- **§1.3's second row** grades this amendment as fixing a registered contradiction
  because "§5 registers a gate the runtime cannot satisfy." On the evidence the gate
  *is* satisfiable in a fresh process. The row is left as graded; the legitimacy case
  now rests on the first row alone — an instrument property that was assumed and never
  measured, which Phase 1 measured.
- **§2's premise** — "if the runtime does not reproduce, then every scored comparison
  in the record is a single sample from a distribution that has never been measured" —
  has a false antecedent on this evidence. The distribution is still unmeasured, which
  is what Phase 2 is for, but not for the reason §2 gives.

Neither changes a phase, a method, the §4.3 decision rule, or the §1.2 non-rescue
clause. The observation §1.1 rests on stands: two different answers to a byte-identical
prompt are committed and are not retracted. Phase 1 places it as an **outlier of
unidentified cause**, not as a property of seeded sampling.
