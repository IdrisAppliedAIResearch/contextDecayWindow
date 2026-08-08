# Study 011 — STM and LTM Tier Isolation and Joint Operation

**Type:** Pre-registration. Live 121-turn study on the arc instrument.
**Repository:** `contextDecayWindow` · `experiments/study_011/`
**Branch:** `study/011-tier-isolation`
**Status:** REGISTERED — locked on commit. This commit contains no implementation files.
**Depends on:** IC-001 (Branch A) · EC-002 (PR #40) · LV-001 (PR #35) · DR-001 · AR-001
**Companions:** `PAPER_001.md` · `CLAUDE_CONTEXT.md` · `RETRIEVAL_MECHANISM_LEDGER.md`

**Source document:** `STUDY_011_tier_isolation.md`, drafted August 6, 2026 by the program
author. Sections 0 through 10 below are that document verbatim, with two exceptions,
both required by the source document itself and both marked in place: the status line
above, and **§3.1**, which resolves the reproduction-target question §3 delegates to
the implementer. No other text is changed. Where §3.1 records a fact that contradicts
a framing in the author's text, the fact is recorded and the author's text is left
standing, per the standing rule against silent reconciliation.

---

## 0. Why this study exists

IC-001 measured that under the deployed packing order, the similarity path delivered
**zero episodes and zero characters at 8 of 8 probes** on the internal corpus. The
recency window consumed the entire budget every time.

Studies 004 through 010 were built to measure what the long-term path contributes.
Study 004's conclusion — *"the read path was mechanically flawless and delivered
nothing useful; formation, not retrieval, is the binding constraint"* — redirected the
next five studies into formation work. **That conclusion was drawn from a pipeline in
which the read path was being denied window space.**

This study does not probe. It measures, live, whether each tier works alone, whether
they work together, and what each contributes — with a **binding pre-test that both
mechanisms demonstrably deliver before any live run is authorized.**

That pre-test is the check no study in this program has ever run.

---

## 1. The single new claim

> **Each memory tier, given window space, contributes measurably to answer quality; and the deployed packing order suppressed one of them.**

Two halves, one study, because neither is interpretable alone: tier contribution
cannot be attributed without controlling packing order, and a packing-order effect is
meaningless without knowing what the tiers do.

**This is a re-measurement, not a new component.** No mechanism is added. Study 011
introduces no selector, no formation change, no threshold change.

---

## 2. Design decisions — settled here, not during implementation

| # | Decision | Value | Rationale |
|---|---|---|---|
| **D1** | Arc numbering | **Study 011** | Same instrument as 001–010: 121-turn corpus, 13-question rubric, treatment score out of 13. The corrected series 8.5 → 12.0 extends here. Reopens the arc closed at CC-002 |
| **D2** | Packing order | **A registered variable**, not a fixed setting. K-first in arms A/B/C; recency-first in arm D | Fixing it would confound tier contribution with order. Arm D is the attribution control |
| **D3** | Coverage tier | **OUT** | The deployed configuration never had one (IC-001 §7). LV-001 killed A3 live. Including it is a second new component |
| **D4** | Arms | **Four** (§3) | The minimum that isolates each tier and attributes the order effect |
| **D5** | Bar structure | **Descriptive primary, one binding kill** (§6) | The question is what the tiers do, not whether a number improved. The kill exists so a regression cannot be reported as a finding |

**D1 is the one to override if you disagree.** The alternative is `RC-001`, framing
this as a re-measurement outside the series. I recommend Study 011 because it is a
live run on the arc's own instrument and its result belongs in the same series as
Study 009's 9.0-vs-12.0 contrast.

---

## 3. Arms

Four live 121-turn runs. Same corpus, same seed, same runtime, same budget.

| Arm | Recency window | K tier | Packing order | Answers |
|---|---|---|---|---|
| **A — STM only** | N = 32 | disabled | n/a | Does the recency tier work alone? Replicates Study 009 Arm S under corrected accounting |
| **B — LTM only** | **disabled** | K = 0.48 | n/a | **Never run in this program.** Does the similarity tier work alone? |
| **C — Both, K-first** | N = 32 | K = 0.48 | K → recency | The corrected configuration |
| **D — Both, recency-first** | N = 32 | K = 0.48 | recency → K | **The deployed configuration.** Reproduction anchor and attribution control |

**Registered contrasts:**
- **C vs D** — the packing-order effect, live. IC-001 measured this offline.
- **C vs A** — the marginal contribution of the similarity tier.
- **C vs B** — the marginal contribution of the recency tier.
- **A vs B** — which tier carries more alone.

**Arm B carries a known hazard.** With no recency window the model does not see the
immediately preceding turns, so the arm may be conversationally degenerate rather than
merely worse at recall. **That is informative and must not be pre-empted with a
recency floor** — a floor makes it not an isolation. G6 (§4) catches a degenerate arm
at 35 turns rather than 121.

**Arm D's reproduction target must be identified before implementation.** IC-001's B0
gate reproduced "the committed deployed result" at 6/17 Q11, 31,946 characters, 8
episodes. **Confirm from artifacts which committed run that is** — the corrected
bakeoff Tier 6 run or Study 009 Arm L — and name it in the pre-registration. Do not
infer it from this document.

---

## 3.1 Arm D's reproduction target — resolved from artifacts

*Added by the implementer before registration, as §3 requires. Everything below is
read from committed artifacts and cited to them; nothing is inferred from the source
document.*

### 3.1.1 The named target

**G5's reproduction target is
`experiments/components/retrieval_mechanism_ledger/artifacts/e005/a0_baseline.json`.**

It carries `fact_count 6`, `domain_count 3`, per-domain `{civil 4, marine 1, monetary
1, art 0}`, `selected_episode_count 8`, `serialized_chars 31946`, `budget_chars
32000`, `payload_sha256
64b19b96b44bb4745f4543a7824a18433e49131d1eeb9a9813760f15f8afe478`, and the eight
`selected_ids` beginning `34f5bb4c`. IC-001's B0 gate asserted every one of these
fields and passed
(`experiments/internal/packing_priority/runs/ic001/b0_recency_first/b0_gate.json`).

That artifact derives from the **corrected bakeoff Tier 6 run**,
`experiments/surveys/retrieval_bakeoff/tier6/runs/tier6_live_121_corrected_001/context_matched_stm`.

### 3.1.2 Study 009 Arm L is ruled out

`experiments/study_009/evaluation/sealed_mapping.json` maps `arm_A` to
`arm_l_study_007_accepted`. Study 009's Arm L **is the accepted Study 007 condition-C
run**, preserved and re-scored, not a Study 009 run; `experiments/study_009/runs/`
contains only `arm_s`. Study 009's own report calls Arm L "a preserved earlier run".
It is not the deployed configuration and is not a reproduction target for Arm D.

### 3.1.3 The target is a re-pack, not a delivered window

**This is the part that must not be discovered at the gate.** The 31,946-character,
8-episode figure is **not** what the corrected Tier 6 run delivered live. It is that
run's frozen turn-120 candidate order re-packed offline at the enforced 32,000-character
budget. `a0_baseline.json` says so in its own `interpretation` field: *"Unchanged
corrected-run candidate order under compact exact-cost packing at the enforced
budget."*

The corrected Tier 6 run itself ran at a different budget:

| | Committed live run, turn 120 | `a0_baseline.json` (the G5 target) |
|---|---:|---:|
| Budget | 60,595 | 32,000 |
| Serialized characters | 60,285 | 31,946 |
| Episodes delivered | 17 | 8 |
| K episodes delivered | 0 | 0 |
| Payload SHA-256 | `2ba001aa…` | `64b19b96…` |

Source: `logs/context_match.jsonl` turn 120 of the corrected run, and
`experiments/surveys/retrieval_bakeoff/settings/tier6_corrected_121_settings_lock.json`,
which locks `payload_budget: 60595`, `n_cap: 32`, `k_threshold: 0.48`, and
`candidate_order: "N first, then K-only"`.

Two consequences are registered here rather than left to interpretation:

1. **G5 is an offline gate, and only an offline gate.** §4 already states that all
   gates are offline and make zero model calls. G5 therefore certifies that the
   Study 011 packer, replaying Arm D's configuration against the corrected run's
   committed candidate identities, reproduces `a0_baseline.json` on identities and
   payload SHA-256 — the same assertion IC-001's B0 gate made. It certifies harness
   fidelity. It does not certify that a live Arm D run reproduces anything.

2. **Arm D's live 121-turn run reproduces no committed live run.** §5 fixes the budget
   at 32,000 characters for all four arms, and no committed live run exists at that
   budget in this configuration. Arm D is the deployed *packing order* re-run at the
   registered budget, not a re-execution of the corrected Tier 6 run. The phrase
   "reproduction anchor" in the §3 table is true of the offline gate and false of the
   live run; the source text is left standing and the distinction is recorded here.

### 3.1.4 The live comparison point, and what it is worth

The corrected Tier 6 run is the only committed live 121-turn run in the deployed
configuration that carries a valid score:
`experiments/surveys/retrieval_bakeoff/tier6/analysis_corrected_121/score_comparison_summary.json`
records **T6 11.0/13 on Q1–Q13** and 1.0 on Q14, with
`analysis_manifest.json` classifying it `VALID_CORRECTED_121_RESULT`. (The "T6 6.5
invalid" entry in the AGENTS digest refers to the earlier, uncorrected Tier 6 run, not
this one.) The same file records S 9.0 and L 12.0.

That 11.0 is reported alongside Arm D's score as historical context **and never as a
bar**, because it was produced at budget 60,595 against Study 011's 32,000. A
difference between Arm D and T6 is a budget difference confounded with everything
else that differs between two live runs. No registered comparison uses it.

---

## 4. Pre-test — binding, offline, before any live run

**This is the study's defining feature.** Eleven studies ran without it.

All gates are offline, use committed vectors and stores, make zero model calls, and
are enforced rather than narrated (IC-001's `ModelCallGuard` pattern). **Any failure
stops the study.**

| Gate | Requirement | Certifies |
|---|---|---|
| **G1 — STM isolation** | Arm A delivers ≥1 recency episode at all 13 probes and **0 K episodes** at all 13 | The recency tier is active and the K tier is truly disabled |
| **G2 — LTM isolation** | Arm B delivers **≥1 K episode at ≥T of 13 probes** and **0 recency episodes** at all 13 | The similarity tier is active alone. **T is derived offline and locked before the ablation** (§4.1) |
| **G3 — Joint delivery** | Arm C delivers **≥1 episode from each path at ≥T of 13 probes** | **The gate that would have caught eleven studies.** Both tiers reach the window together |
| **G4 — Path non-identity** | Arm B's delivered episode set is not a subset of Arm A's at ≥T probes | The two paths select different material. Two tiers returning the same episodes is one tier |
| **G5 — Deployed reproduction** | Arm D reproduces the committed deployed result exactly: fact count, per-domain counts, character count, episode count, **episode identities and payload SHA-256** | The harness is faithful. Identity, not counts — a count can match on different episodes |
| **G6 — 35-turn ablation, all four arms** | Each arm completes 35 turns and produces coherent, scoreable output. GO/NO-GO committed | Catches a degenerate Arm B before 121 turns are spent |
| **G7 — Probe-order validator** | Every probe's required facts planted before the probe turn | Standing rule; catches the Study 010 class mechanically |

### 4.1 T must be checked for achievability before it is locked

Standing rule: *check bar achievability before use.* IC-001's B1 arm delivered K
episodes at **5 of 8** targeted probes — 3 had none even under K-first. **A threshold
requiring K at all 13 probes would fail by construction.**

**Procedure:** compute, offline from committed candidates, the maximum number of
probes at which a K episode can reach the window under each arm's configuration.
**Set T from that measurement, register it with the supporting artifact, and state it
before the ablation.** If the achievable maximum is low, say so in the
pre-registration rather than discovering it at the gate.

**T is not a target to hit.** It is the honest floor below which the arm is not
testing what it claims to test.

---

## 5. Runtime and protocol

Standing configuration, unchanged:

- Qwen3.6 27B UD-Q6_K_XL, llama.cpp build 9294 (`0f3cb3fc8`), RTX 5090 32GB
- `--ctx-size 50000`, q8_0 KV cache, ceiling monitor at 80%
- Seed 5005, `--parallel 1`, **speculative decoding off**, temp 1 / top-p 0.95 / top-k 20 / min-p 0
- Determinism spot-check is a gate
- Budget 32,000 characters, **enforced**, exact serialized cost via the post-DR-001 renderer
- Vector cache read-only where one exists; zero new embedding calls; `ModelCallGuard` armed on all entry points
- Controls on checked-out prior architecture in a separate worktree, never a flag-off runner

**Arm D is the control and must run on the deployed configuration as committed**, not
on a flag that disables K-first.

---

## 6. Measurement and bars

### 6.1 Primary outcome — live, not availability

**Scored rubric answers under `PROTOCOL_scoring_integrity.md`.** LV-001 measured
16/16 offline availability against 1.5/8 live. **Availability is reported as a
secondary diagnostic and is never the outcome.**

**Three blind raters, distinct model families, none of them the reader.** LV-001 ran
one where three were required and disclosed it. Study 011 does not repeat that.
Calibration gate: each rater must score a planted `NO_ANSWER` at 0.0. Scores commit
before any mechanism log is opened.

### 6.2 Reported per arm

1. Treatment score out of 13, per question.
2. Q11 facts available and per-domain counts.
3. The eight targeted probes, **per probe**, on the 21-item grain.
4. Episodes and characters delivered, split by path.
5. Oracle-set overlap, both AR-001 sets.
6. Paired per-question gains and losses against Arm D.

### 6.3 The one binding bar

> **B1 — Arm C must not score below Arm D.**

If correcting packing order makes the live result worse, the correction is not adopted
regardless of any availability gain. **This is the LV-001 rule generalized:** a
mechanism that improves delivery and degrades answers has not improved anything.

### 6.4 Registered descriptive comparisons — no thresholds

C−D, C−A, C−B, A−B, reported as exact paired counts with per-question detail. **No
materiality threshold is registered**, matching EC-002 and IC-001. The program holds
no variance estimate anywhere; these support no significance claim.

**Study 009's same-seed contrast (S 9.0 vs L 12.0) is the historical reference point**
and is reported alongside, with the caveat that it ran under recency-first packing and
pre-DR-001 accounting.

---

## 7. Surrogate audit

| Check | Certifies | Can it pass falsely? | Mitigation |
|---|---|---|---|
| G2/G3 K-episode counts | the LTM tier works | **Yes — a delivered episode can be irrelevant** | Pair with G4 path non-identity and with oracle overlap |
| G4 non-identity | the paths differ meaningfully | Yes — differing by one trivial episode | Require non-subset at ≥T probes, and report the overlap fraction |
| G5 reproduction | harness fidelity | **Yes — counts can match on different episodes** | Episode identities and payload SHA-256 asserted, not counts |
| Arm C beats Arm D | packing correction works | **Yes — LV-001 is the proof** | B1 is scored, live, on the rubric. Availability is never the bar |
| Targeted probes unchanged in total | no regression | Yes — aggregates hide per-probe swings | Per-probe reporting on all eight, 21-item grain |
| Arm B scores poorly | LTM is weak | **Yes — it may be conversationally degenerate rather than bad at recall** | G6 ablation; report coherence separately from recall |
| Three raters agree | the score is correct | Yes — shared bias across models | Distinct families; calibration gate; H1–H5 triggers; adjudication |

**Accepted residual:** one corpus, one seed, one runtime, single run per arm. **No
variance estimate.** Study 011 cannot establish that any difference would replicate.
State this wherever a result is cited.

---

## 8. Registered predictions

Committed so they can be wrong on the record. The author's prior in this program is
poor — ten predictions, most wrong on mechanism, most recently wrong about IC-001's
mechanism while right about its size.

1. **Arm D reproduces.** High confidence; IC-001's B0 gate already did offline.
2. **Arm C ≥ Arm D, by 0–2 points.** IC-001's availability gain was +1 fact on Q11 and
   +4 targeted items. Small, and answer scores move less than availability.
3. **Arm B is conversationally degenerate and may fail G6.** No recency window means no
   view of the preceding turns. ~40% it fails the ablation outright.
4. **Arm A ≈ Study 009's Arm S**, adjusted for corrected accounting.
5. **C − A is positive and larger than C − B.** The similarity tier contributes real
   coverage; the recency tier contributes continuity that the rubric only partly measures.
6. **G3 passes but T is low** — likely 6–9 of 13, not 13. K does not clear threshold at
   every probe even when given first claim.

**The uncomfortable one:** if Arm C beats Arm D by less than a point, the honest
reading is that the packing suppression IC-001 found was real and *did not matter much
for answers* on this corpus. That is a legitimate result and would narrow, not
overturn, Study 004's conclusion.

---

## 9. Cost and risk

**Four live 121-turn runs plus a 35-turn ablation each, plus three-rater scoring.**
This is the largest compute commitment since Study 010, and it arrives after a
decision to move toward a product. Stated plainly, as the standing rule requires.

**Risks:**
- Arm B fails G6 and the study runs three arms. Acceptable; record it.
- T is achievable only at a low value, weakening G2 and G3. Report the value, do not
  lower the gate to pass.
- A rater family is unavailable. LV-001 hit this. Identify all three before starting.
- Arm C wins on availability and loses on answers. That is B1 firing, and it is a
  result, not a failure of the study.

---

## 10. Deliverables

- [ ] Pre-registration committed before any implementation; SHA is the anchor
- [x] Arm D's reproduction target identified from artifacts and named — §3.1
- [ ] T derived offline, achievability stated, locked before the ablation
- [ ] G1–G5 and G7 passed and committed, in git order
- [ ] G6 35-turn ablation, all four arms, GO/NO-GO committed
- [ ] Four live 121-turn runs, determinism spot-check passing
- [ ] Three-rater blind scoring, calibration gate passed, scores committed before mechanism logs
- [ ] Per-arm outcomes (§6.2)
- [ ] B1 verdict
- [ ] Registered descriptive comparisons with per-question detail
- [ ] `PAPER_001.md` §5 revised **in either direction**
- [ ] Ledger, `README.md`, `AGENTS.md` digest, `ERRATA.md` if any committed number moves
- [ ] One PR

---

*Drafted August 6, 2026. IC-001 Branch A: K delivered 0 episodes at 8 of 8 probes
under the deployed order; K-first gave 7/17 Q11 and 18/21 targeted against B0's 6/17
and 14/21. EC-002: 109/470 → 261/470 any-session recall, 152 gains 0 losses. LV-001:
16/16 offline against 1.5/8 live. Study 009 reference: S 9.0 vs L 12.0.*
