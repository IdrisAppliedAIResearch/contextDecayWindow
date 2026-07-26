# Study 006 — Density-Normalized Span Selection in Extractive Dreaming

## contextDecayWindow — Idris Applied AI Research

**Date:** July 2026
**Status:** COMPLETE — **PARTIAL**
**Pre-registration:** `experiments/study_006/pre_registration.md` (LOCKED v1, SHA `5def302`)
**Amendment in force:** `amendments/AMENDMENT_001_selection_scale.md`
**Runtime:** llama.cpp `b9294-0f3cb3fc8`, Qwen3.6-27B-UD-Q6_K_XL, ctx 50,000, single slot, seed 5005
**Arms:** treatment `runs/study_006_full_001` · same-seed control `controls/whole_turn_seeded/run_001`

---

## Abstract

Study 005 established a faithful extractive dreaming architecture that selected
the wrong spans: whole-turn absolute-count salience preferred verbose model output
over concise user-planted facts, and only 2 of 4 domains formed. Study 006 revised
the selection policy — sentence-level spans, density normalization, and source
weighting — leaving every other component untouched.

**Formation was fixed completely. Breadth got worse.**

All four domains formed for the first time in this research program, with 100%
offset-verbatim fidelity, zero non-content records, zero inference calls in
dreaming, and better compression than Study 005 (6.55% vs 10.81% of raw). Bar 1
passed. Both breadth probes then scored 0.0, and the treatment finished 0.5 below
its same-seed control on targeted recall. Bars 2 and 3 failed.

The cause is now isolated and is not the selection policy. The treatment's store
contained planted content from all four domains; the control's contained
substantially less. At the breadth probe the treatment surfaced one term from one
domain and the control surfaced all four. Retrieval returns a fixed **number** of
records, and Study 006 made each record roughly seventeen times smaller in
information content while leaving that budget expressed as a count. Fixing
formation alone made end-to-end recall worse.

---

## 1. Outcome against the pre-registered bars

| Bar | Criterion | Result |
|---|---|---|
| **1 — Formation** | 4/4 domains, 100% offset-verbatim, zero non-content | **PASS** |
| **2 — Breadth** | Q11 ≥ 0.5 ∧ Q14 ≥ 0.5 ∧ sum ≥ 1.5 | **FAIL** (0.0, 0.0) |
| **3 — Non-regression** | Q1–Q13 ≥ same-seed control | **FAIL** (10.5 vs 11.0) |

**Verdict: PARTIAL.**

### Bar 1 — Formation (PASS)

| Domain | Formed | Facts present |
|---|---|---:|
| civil_engineering | yes | 5 of 5 |
| renaissance_art | yes | 1 of 3 |
| monetary_policy | yes | 1 of 3 |
| marine_biology | yes | 1 of 3 |

200 records, **0 non-content**, **0 unfaithful at recorded character offsets**,
**0 inference calls** across all four dream passes. Study 005 formed 2 of 4; its
promotion control formed 3 of 4.

### Bar 2 — Breadth (FAIL)

Q11 = 0.0, Q14 = 0.0. Bar 2 was evaluable for the first time — Study 005 could not
evaluate it because the store lacked the facts. Now the store has them and breadth
still fails, which is what makes this study's negative result informative rather
than merely disappointing. Section 3 diagnoses it.

### Bar 3 — Non-regression (FAIL, marginal)

Treatment 10.5 vs control 11.0. The **only** per-question regression is Q5
(treatment 0.0, control 0.5).

**Sensitivity, as the pre-registration requires.** The pre-registration states:
*"Q5 and Q8 partial credit are the softest calls in the rubric. Where a Bar 3
verdict turns on a single 0.5, the report must state the verdict's sensitivity to
that judgment rather than presenting it as a clean margin."* This verdict turns on
exactly that. Q5 asked for the pigment ground and glaze — planted as *lead white
ground* and *ultramarine glaze*. The treatment gave neither term. The control gave
neither term as such either, but hedged that pigments *"likely included azurite or
early ultramarine for blues"*, which was credited 0.5 for surfacing one planted
term. Had that hedge been scored 0.0, the arms would tie at 10.5 and Bar 3 would
pass on the ≥ criterion. **Bar 3 is reported as failed by the narrowest possible
margin on the softest available judgment, not as a clean regression.**

---

## 2. What the revision did to selection

Three changes, all inside the existing extractive stage:

```
base(s)     = named_entity_count(s) + 2 × numeric_token_count(s)
density(s)  = base(s) / word_count(s)
salience(s) = density(s) × source_weight(role)     # user 1.5, assistant 1.0
```

Rank movement for the six pre-registered Study 005 near-misses:

| Domain | Turn | Study 005 | Study 006 | Selected |
|---|---:|---:|---:|---|
| renaissance_art | 55 | 18 of 30 | 29 of 393 | yes |
| renaissance_art | 56 | 30 of 30 | 101 of 393 | no |
| renaissance_art | 60 | 19 of 30 | 171 of 393 | no |
| marine_biology | 100 | 11 of 21 | **1 of 177** | yes |
| marine_biology | 101 | 15 of 21 | 31 of 177 | yes |
| marine_biology | 102 | 18 of 21 | 14 of 177 | yes |

Compression improved while record count rose 17×, because spans are sentences
where Study 005 stored whole turns:

| | Records | Chars | % of raw | Peak context |
|---|---:|---:|---:|---:|
| Study 006 treatment | 200 | 29,214 | **6.55%** | **12,169** |
| Same-seed control | 12 | 49,785 | 11.04% | 16,171 |

---

## 3. The finding: formation and retrieval budgets must be co-designed

This is the result worth carrying forward.

**Store contents** (planted terms present in distilled records):

| Domain | Treatment | Control |
|---|---|---|
| civil | Halcyon, 847, S460ML, Bekova, 92.4 | Halcyon, 847, S460ML, Bekova, 92.4 |
| art | Annunciation, Melozzo, della Rovere, 1483 | della Rovere |
| monetary | Priya Mehta, reverse repurchase, 2.3%, Federal Reserve | Federal Reserve, Taylor |
| marine | Vampyroteuthis, Watanabe, marine snow, photophore | Vampyroteuthis, Watanabe, marine snow |

**Reaching the model at Q11 (turn 120):**

| Domain | Treatment | Control |
|---|---|---|
| civil | Halcyon | Halcyon, 847, S460ML, Bekova, 92.4 |
| art | — | della Rovere |
| monetary | — | Federal Reserve, Taylor |
| marine | — | marine snow |

The treatment built the richer store and retrieved less from it. Its Q11 response
stated that *"the provided context does not contain episodes discussing Renaissance
art or monetary policy"* — while its store held `Annunciation`, `Melozzo`, `1483`,
`Priya Mehta`, `2.3%` and `reverse repurchase`.

**Mechanism.** Retrieval returns a fixed count of LTM items — 4 for the treatment,
5 for the control. Under whole-turn selection each item is an entire turn carrying
many facts across a domain, so five items give broad coverage. Under span selection
each item is one sentence, and the top-ranked spans by similarity to a breadth
query cluster within a single topic. Shrinking each record's information content
~17× while leaving the retrieval budget expressed as a *count of records* converted
a formation success into a retrieval regression.

The read path was out of scope by pre-registration and was not modified. That
constraint is what makes this diagnosis clean: nothing downstream of formation
changed, so the regression is attributable to the interaction between record
granularity and a retrieval budget that was never rescaled for it.

**This was predicted before the run.** Amendment 001 §7 recorded: *"A 200-record
store is ~17× larger than Study 005's 12. Retrieval and arbitration were exercised
at 12 records. Their behaviour at 200 is untested... This could help breadth or
hurt precision."*

---

## 4. The replay gate earned its place

The pre-registered Retrospective Replay Gate **failed at 0 of 4 domains** before
any run was spent, and the failure was informative.

The diagnosis was not the salience formula. It was that **C = 3 was carried
unchanged from Study 005 while the selection unit changed from turns to spans**:
Study 005 chose 3 records from ~30 episodes, a top-10% requirement; Study 006 chose
3 from 177–393 spans, a top-1% requirement. Span granularity multiplied the
candidate pool tenfold and the cap was never rescaled, making selection ten times
harder rather than easier.

Amendment 001 raised C to 50 and applied the coverage floor per span. Re-replay
passed 4/4, and the live run then reproduced the replay's per-fact predictions
exactly — including which six plants would remain unselected.

Two things are worth recording about how the amendment was chosen:

- **An alternative that passed the gate was rejected.** Softening normalization to
  `base/√words` reached 4/4, but broke the adversarial fixture: the plant stopped
  outranking the long diffuse decoys, because √ normalization moves the policy
  partway back toward Study 005's absolute counting. The fixture was authored
  before the failure and was not modified, so it constrained the amendment rather
  than the reverse.
- **Source weighting was left untouched.** Weight sweeps to 6.0 and user-only
  candidacy were evaluated and rejected; both tune the parameter most correlated
  with this script's answer key, and neither reached 4/4 anyway.

---

## 5. Limitations

**Source weighting is script-correlated** (carried verbatim from the decision
record). Weighting user spans above assistant spans is defensible in general, but
in *this* script the planted facts are user-authored, so the weight is also
conveniently aligned with the answer key. This study cannot separate "user content
is genuinely more valuable" from "user content happens to be where this script hid
the answers." A script with model-authored target facts would be needed.

**C = 50 was selected using the replay data.** The pre-registration sanctions
re-deriving parameters from replay evidence, but the consequence stands: the replay
gate validated C = 3, rejected it, and was then used to choose the replacement, so
it cannot independently validate C = 50. Mitigating this: the amendment changes one
value with a structural argument that holds independently of the outcome, and the
adversarial fixture and the live run remained out-of-sample.

**Rubric scoring deviated from the pre-registered procedure.** The pre-registration
specifies manual scoring by a single human rater with scores committed before any
dreaming, retrieval or arbitration log is opened. Neither condition was met: the
rater was an agent, and had computed Bar 1 formation before scoring. Scoring used
only each arm's `rubric/responses.md` against the locked criteria, and a written
rationale is recorded per question in `evaluation/rubric_scores.json` so a human
rater can audit or replace every score. Bar 3 turns on one such judgment (§1).

**Single scripted run per arm, one seed, one rater.** A controlled paired result,
not population-level performance.

**Six plants remain unreachable.** `art_pigment`, `art_patron_role`,
`monetary_taylor`, `monetary_fed`, `marine_photophores` and `marine_feeding` were
not selected at any defensible cap. Q5 and Q8 depend on two of them; both scored
below full credit, as predicted at lock.

---

## 6. What the next study should do

The specification is now unusually concrete, because Study 006 isolated the
bottleneck rather than merely moving it.

1. **Express the retrieval budget in information, not record count.** A token or
   character budget, or a per-domain quota, rather than "top-K records". This is
   the direct fix for §3 and does not require changing formation.
2. **Retrieval diversity is now correctly triggered.** Its pre-registered trigger
   was Bar 1 pass + Bar 2 fail. That has now occurred, for the first time, against
   a store that demonstrably contains the answers.
3. **Do not revisit selection.** Formation is solved: 4/4 domains, 100%
   offset-verbatim, zero non-content, better compression. Study 006's changes
   should be carried forward unmodified.

---

## 7. Artifacts

| Artifact | Path |
|---|---|
| Pre-registration | `pre_registration.md` (SHA `5def302`) |
| Amendment 001 | `amendments/AMENDMENT_001_selection_scale.md` |
| Decision record | `decisions/DECISION_selection_policy_study006.md` |
| Plant key | `q_facts_key.md` |
| Runtime verification | `runtime/s6_003_runtime_verification.md` |
| Replay gate (fail → pass) | `replay/replay_report.md` |
| Adversarial fixture | `tests/adversarial_selection_fixture.json` |
| Ablation + GO | `ablation/ablation_report.md` |
| Treatment run | `runs/study_006_full_001/` |
| Same-seed control | `controls/whole_turn_seeded/run_001/` |
| Scores + rationale | `evaluation/rubric_scores.json` |
| Bar results | `evaluation/study_006_results.json` |
| LTM analysis | `runs/study_006_full_001/condition_c/ltm_analysis/analysis_report.md` |

**Binding environment note:** every Study 006 process ran with `PYTHONUTF8=1`.
`src/study/script_loader.py` opens the script without an encoding argument, so
under the Windows cp1252 default the model silently receives mojibake. See
`runtime/s6_003_runtime_verification.md`.
