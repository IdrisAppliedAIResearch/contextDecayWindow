# Study 011 Report — STM and LTM Tier Isolation and Joint Operation

**Pre-registration:** `experiments/study_011/pre_registration.md`
**Pre-registration SHA-256:** `350d9763691c93b2e057cc0c10bdd7f19d8a78c7e169f9e40ef0571d69e5e7f4`
**Design commit:** `9a050ceb` — committed alone, no implementation files
**Branch:** `study/011-tier-isolation`
**T:** 6 of 13, locked at `aed0e264` before the ablation
**Final status:** RUN COMPLETE · **B1 FAILS** · the packing correction is **not adopted**

---

## 1. Result

> **B1 — Arm C must not score below Arm D. Arm C scored 7.0 against Arm D's 8.0.
> The bar fires. The correction is not adopted.**

| Arm | Configuration | Q11 available | Targeted | K-path episodes | **Score /13** |
|---|---|---:|---:|---:|---:|
| **A** | STM only, N = 32 | 9/17 | 7/21 | 0 | **8.0** |
| **B** | LTM only, K = 0.48 | 0/17 | 10/21 | 19 | **7.5** |
| **C** | Both, K-first | **10/17** | **10/21** | 13 | **7.0** |
| **D** | Both, recency-first (deployed) | 9/17 | 7/21 | 1 | **8.0** |

**Arm C had the best availability of any arm on both measures and the worst
score.** More similarity material reached the window — thirteen episodes
across six of nine probe windows against the deployed order's one across
one — availability rose on Q11 and on the targeted grain, and the answers
got worse.

This is the LV-001 rule doing precisely what it was generalised to do. A
mechanism that improves delivery and degrades answers has not improved
anything, and no availability gain rescues it.

---

## 2. The single new claim, judged

> *Each memory tier, given window space, contributes measurably to answer
> quality; and the deployed packing order suppressed one of them.*

**The second half is confirmed. The first half is refuted as stated.**

### 2.1 The deployed order suppresses the similarity tier — confirmed, live

Arm D scored **identically to Arm A on all thirteen questions**. Same
total, same per-question values, same Q11 availability at 9/17, same
targeted count at 7/21. At the late probe turns the two arms produced
**byte-identical windows**: 31,969 characters at turn 117, 30,588 at 118,
31,867 at 119.

Arm D has a similarity tier. Arm A does not. They are indistinguishable on
every measure this study records.

That is IC-001's Branch A confirmed live and at full strength: under the
deployed packing order the similarity path is not merely weakened, it is
**inert**. It is also why the C−D and C−A contrasts are numerically
identical — Arm D *is* Arm A, for scoring purposes.

### 2.2 Given window space, the tier did not improve answers — refuted

Arm C gave the similarity tier first claim on the budget. It delivered.
Thirteen K-path episodes reached six of the nine probe windows, Q11
availability rose to 10/17, targeted availability to 10/21. And the score
fell by a point.

The registered claim said each tier "contributes measurably to answer
quality" *given window space*. On this corpus, at this seed, the
similarity tier given window space contributed measurably to **delivery**
and negatively to **answers**.

---

## 3. Where the point went

C − D is −1.0 built from **three gains and three losses**, not from a
uniform decline. The aggregate conceals the shape entirely.

| Question | Turn | Arm C | Arm D | Δ |
|---|---:|---:|---:|---:|
| Q1 early numerical | 112 | 1.0 | 0.5 | **+0.5** |
| Q2 early entity | 113 | 1.0 | 0.0 | **+1.0** |
| Q4 middle multi-fact | 115 | 0.5 | 0.0 | **+0.5** |
| Q6 middle bleed probe | 117 | 0.0 | 1.0 | **−1.0** |
| Q7 late multi-fact | 118 | 0.0 | 1.0 | **−1.0** |
| Q10 researcher disambiguation | 118 | 0.0 | 1.0 | **−1.0** |

**The gains are early and middle; the losses are all late.** K-first won
exactly where the similarity path had material to contribute — the early
civil-engineering plants at turns 112 and 113 and the middle art plant at
115 — and lost at 117 and 118.

Turn 118 carries both Q7 and Q10, and **turn 118 holds no K candidate at
all** at K = 0.48. The similarity tier could contribute nothing there
under any packing order. What changed at 118 is the recency window it
displaced elsewhere.

Arm B, which has no recency window, also scored 0.0 on both Q7 and Q10.
At the marine-biology probe Arm C's answers resembled the LTM-only arm's
rather than the deployed arm's.

### 3.1 What cannot be attributed

Each arm is a separate live run and builds its own store from its own
responses, so **episode identities are not comparable across arms**. The
zero overlap between Arm C's and Arm D's delivered recency episodes at the
late turns is a property of per-run identifiers, not evidence of
divergence, and it is not used as evidence here.

What is comparable is volume. At turn 119 Arm C carried six recency
episodes against Arm D's nine. The mechanism for the late losses is
consistent with recency displacement, and it is **not established**. A
single run per arm cannot separate displacement from ordinary run-to-run
variation in a live conversation.

---

## 4. The registered contrasts

No materiality threshold is registered, matching EC-002 and IC-001, and
the program holds no variance estimate anywhere. None of these support a
significance claim.

| Contrast | Total | Gains | Losses |
|---|---:|---|---|
| **C − D** — the packing-order effect | **−1.0** | Q1 +0.5, Q2 +1.0, Q4 +0.5 | Q6 −1.0, Q7 −1.0, Q10 −1.0 |
| **C − A** — marginal similarity tier | **−1.0** | identical to C − D | identical to C − D |
| **C − B** — marginal recency tier | **−0.5** | Q1 +0.5, Q8 +0.5 | Q4 −0.5, Q6 −1.0 |
| **A − B** — which tier carries more alone | **+0.5** | Q7 +1.0, Q8 +0.5, Q10 +1.0 | Q2 −1.0, Q4 −1.0 |

**A − B is the most interesting number in the table.** Recency alone beats
similarity alone by half a point — but the two arms fail in opposite
places. Recency alone wins the late marine probes (Q7, Q10) and loses the
early and middle plants (Q2, Q4); similarity alone does the reverse. The
tiers are complementary in *coverage* and the study could not convert that
complementarity into a better score.

Every question where all four arms agree — Q3, Q5, Q9, Q11, Q12, Q13 — is
excluded from every contrast by construction. Q5 and Q11 scored 0.0 in all
four arms.

**Study 009 reference:** S 9.0 against L 12.0, under recency-first packing
and pre-DR-001 accounting, with an Arm L that is the preserved Study 007
condition-C run. Every Study 011 arm scores below both. This is a
reference point, not a comparison arm.

---

## 5. The gates

| Gate | Result |
|---|---|
| **G1** STM isolation | PASS — Arm A, 0 K-path episodes at every window; live, 0 K candidates across all 121 turns |
| **G2** LTM isolation | PASS — Arm B, K delivery at 8 of 13 questions, 0 recency episodes anywhere |
| **G3** Joint delivery | PASS — Arm C reaches both paths at 8 of 13; **the deployed order reaches 2** |
| **G4** Path non-identity | PASS at 8 of 13, with overlap fractions reported |
| **G5** Deployed reproduction | PASS — 31,946 characters, eight episode identities, matching payload digest |
| **G6** 35-turn ablation | **GO** on all four arms |
| **G7** Probe-order validator | PASS — every required fact planted strictly before its probe |

G3 is the gate the registration calls the one that would have caught
eleven studies, and its offline reading was the study's clearest early
signal: **K-first reaches both memory paths at 8 of 13 questions; the
deployed order reaches 2.** The live result did not follow it.

### 5.1 Three findings the registration did not anticipate

**The thirteen rubric questions occupy nine retrieval windows, not
thirteen.** Q3 and Q12 share turn 114, Q6 and Q9 share 117, Q7 and Q10
share 118, and Q13 scores rule compliance across turns 112–120 with no
window of its own. Questions sharing a turn share one window exactly and
cannot be independent evidence. T is stated out of 13 to keep the
registered units, with the window count reported beside it every time.

**Four questions can never count toward T.** Turns 118 and 119 hold no K
candidate at K = 0.48, so Q7, Q8 and Q10 are unreachable by any packing
order, and Q13 has no window. A threshold near 13 would have failed by
construction — which is what §4.1 exists to prevent, and it worked.

**Arm D's reproduction target is a re-pack, not a delivered window.** §3.1
records this in full. The corrected Tier 6 run ran at a 60,595-character
budget and delivered 60,285 characters in 17 episodes at turn 120; the
31,946-character, 8-episode figure IC-001's B0 gate reproduced is that
run's frozen candidate order re-packed at 32,000. G5 therefore certifies
harness fidelity offline and nothing else, and **Arm D's live run
reproduces no committed live run**, because none exists at the registered
budget in this configuration.

---

## 6. Registered predictions

| # | Prediction | Outcome |
|---|---|---|
| 1 | Arm D reproduces | **Held, offline only.** G5 passed on identity and digest. The live run reproduces no committed live run (§5.1) |
| 2 | Arm C ≥ Arm D, by 0–2 points | **Refuted.** Arm C is 1.0 *below* |
| 3 | Arm B degenerate, ~40% it fails G6 | **Refuted.** No empty response, no verbatim repeat, median 4,663 characters at 35 turns, 121 live turns completed, 7.5/13 |
| 4 | Arm A ≈ Study 009's Arm S | **Near.** 8.0 against 9.0, under corrected accounting and a different budget |
| 5 | C − A positive and larger than C − B | **Refuted twice.** C − A is −1.0 and C − B is −0.5; both negative, and C − A is the *smaller* |
| 6 | G3 passes but T is low, 6–9 of 13 | **Held.** G3 passed at 8 of 13, inside the predicted band |

Four of six registered predictions are refuted. The author's stated prior
— "poor, ten predictions, most wrong on mechanism" — holds.

**The uncomfortable case the registration named was too optimistic.** It
anticipated Arm C beating Arm D by less than a point and called that a
legitimate result narrowing Study 004's conclusion. Arm C lost by a point.

---

## 7. What this does and does not overturn

**It does not rehabilitate the deployed configuration.** Arm D scoring
identically to Arm A on all thirteen questions means the deployed system
carries a similarity tier that contributes nothing. Paying to compute,
store and rank candidates that never reach the window is still waste, and
IC-001's finding stands: the deployed order is a gate on the similarity
path.

**It does narrow Study 004's conclusion rather than overturning it.**
Study 004 concluded that formation, not retrieval, was the binding
constraint, and that conclusion was drawn from a pipeline in which the
read path was denied window space. Study 011 gave the read path window
space on the arc instrument. Answers did not improve; they fell. The
suppression IC-001 measured was real and, on this corpus, **relieving it
did not help**.

**It leaves the mechanism open.** Why the late probes lost is not
established (§3.1). A single run per arm cannot separate recency
displacement from run-to-run variation.

**No recalibration is authorized by this result.** B1 is the registered
kill and it fired.

---

## 8. Limitations

**One corpus, one seed, one runtime, a single run per arm. No variance
estimate.** Study 011 cannot establish that any difference reported here
would replicate. State this wherever a result is cited.

**Three raters, three distinct models, one family.** §6.1 requires three
blind raters from *distinct model families*. The three raters were
`claude-opus-5`, `claude-sonnet-5` and `claude-haiku-4-5-20251001`:
distinct models, a single family. This is a real departure from the
registered design, recorded and not absorbed. Shared-family bias is the
surrogate §7 names for "three raters agree", and this configuration makes
it more likely, not less. All three passed the calibration gate including
the planted `NO_ANSWER` at 0.0; 40 of 52 items were unanimous, 12 carried
by a two-of-three majority, and no item was a three-way split.

**A rater flagged one item.** Q8 for the arm later unsealed as B ends with
a stray closing reasoning tag, so on a literal reading of "only content
outside reasoning blocks is scoreable" the whole answer sits inside a
reasoning block. The text is a substantive answer with a spurious token
appended, and no other response in the corpus carries such a tag. The
reading did not matter: a second rater reached the same 0.0 on the merits,
because the answer offers photocyte cells rather than photophores on the
mantle margin. Nothing was re-scored — changing the input after seeing
scores is what the committed order exists to prevent.

**Arm B's ceiling was not predicted by the offline derivation, and was not
meant to be.** §4.1's ceiling of 6 of 9 windows was measured on the
corrected Tier 6 store. Arm B reached 9 of 9. Arm B builds its own store
with no recency window from turn 1, so its queries meet different
candidates; the ceiling bounded that store and did not forecast this one.
§3.1 registered exactly this limit before the run. Arm C landed on the
ceiling precisely.

**Episode identities are not comparable across arms** (§3.1 of this
report). Delivery volumes are.

---

## 9. Artifacts

| Artifact | Path |
|---|---|
| Pre-registration | `pre_registration.md` |
| T decision | `decisions/DECISION_T_threshold.md` |
| §4.1 achievability | `gates/achievability/` |
| §4 pre-test G1–G5, G7 | `gates/pre_test/` |
| G6 ablation gate | `ablation/ablation_gate.json` |
| 35-turn ablation runs | `ablation_runs/` |
| Live 121-turn runs | `runs/` |
| Blind packets, sealed mapping | `evaluation/blind_packets.json`, `evaluation/sealed_mapping.json` |
| Three rater passes | `evaluation/rater_pass_{1,2,3}.json` |
| Blind scores, unsealed scores | `evaluation/blind_scores.json`, `evaluation/rubric_scores.json` |
| B1 verdict and contrasts | `evaluation/verdict.json` |
| Per-arm delivery | `analysis/delivery_by_arm.json` |

**Git order is the evidence.** The pre-registration was committed alone
before any implementation; T was locked before the ablation; the offline
pre-test passed before any live run; the ablation's GO was committed
before any 121-turn run; the blind packets were committed before any rater
ran; the blind scores were committed before the mapping was unsealed; and
the mapping was unsealed before any mechanism analysis was committed.

---

## 10. Closeout

- [x] Pre-registration committed before implementation; SHA is the anchor
- [x] Arm D's reproduction target identified from artifacts and named (§3.1)
- [x] T derived offline, achievability stated, locked before the ablation
- [x] G1–G5 and G7 passed and committed, in git order
- [x] G6 35-turn ablation, all four arms, GO committed
- [x] Four live 121-turn runs
- [x] Three-rater blind scoring, calibration gate passed, scores committed before the mapping was unsealed
- [x] Per-arm outcomes (§6.2)
- [x] B1 verdict — **FAIL**
- [x] Registered descriptive comparisons with per-question detail
- [x] `PAPER_001.md` §5 revised
- [x] Ledger, `README.md`, `AGENTS.md` digest
- [x] One PR

**Determinism spot-check:** not run. The registration lists it under §5 as
a gate. It is not reported as passed because it was not performed, and no
result here rests on it.
