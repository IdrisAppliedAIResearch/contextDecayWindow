# Amendment 001 Phase 2 — Decision Rule

**Committed before any run is scored.** This file exists so the reading of the
band is fixed while the band is still unknown. Its SHA-256 is recorded in
`band_verdict.json`; if the two disagree, the verdict is void.

**Amendment:** `experiments/study_011/amendments/AMENDMENT_001_determinism_and_noise_band.md`,
authorized 2026-08-09
**Design:** Arm D, the deployed configuration, repeated **N = 5**. Identical
corpus, identical settings, identical seed, standing runtime, temp 1.
**Committed:** 2026-08-09, before the first replicate was scored.

---

## 1. The band

The band is **max − min of the five per-run totals on Q1–Q13**, scored under the
full protocol. Not the standard deviation, not a confidence interval, not a
trimmed range. The range is chosen because n = 5 estimates a standard deviation
poorly and a range cannot be mistaken for an inferential statistic.

## 2. The rule

| Band (max−min) | Reading | Consequence for the record |
|---|---|---|
| **< 0.5** | The instrument resolves one-point differences | Committed verdicts stand as written. Study 011's −1.0 and LV-001's −2.0 are interpretable |
| **0.5 – 1.5** | One-point differences are not interpretable; three-point differences are | Study 011's −1.0 and LV-001's −2.0 are re-read as **not demonstrated**. Study 009's 3.0 and the 3.5 series improvement stand |
| **> 1.5** | Nothing below ~3 points is interpretable | **Most of the arc's scored verdicts are re-read as undetermined.** Study 009's 3.0 is marginal. `PAPER_001.md` requires a structural revision, not a caveat |
| **Runs not comparable** | e.g. an arm fails to complete | Report and stop. Do not estimate from fewer than N |

Boundaries are inclusive at the lower edge: a band of exactly 0.5 falls in the
middle row, a band of exactly 1.5 falls in the middle row, and a band of 1.51
falls in the last.

## 3. What must be reported, whatever the band

From §4.2 of the amendment, and none of it is optional:

1. Every individual run's total, **listed, not summarized**.
2. Full range: min, max, max−min.
3. Standard deviation, **with the caveat that n = 5 estimates it poorly**.
4. Per-question variability: which of the thirteen questions move across runs
   and which are stable. **A band concentrated in two questions means something
   different from a band spread across all thirteen.**
5. Rater disagreement per run, separated from run-to-run variation. These are
   two distinct noise sources and must not be pooled.

## 4. Applied uniformly, in both directions

The band is not applied selectively to results the program would prefer to keep.
A band that vindicates a verdict and a band that dissolves one are recorded the
same way, in the same commit, with the same prominence.

**Non-rescue clause, binding (§1.2).** B1 fired: Arm C scored 7.0 against Arm D's
8.0 and the packing correction is **not adopted**. That verdict is final and no
band measured here may reopen it. The band **may not be cited in support of any
adoption decision for K-first packing**. Any future adoption requires a new study
with its own pre-registration and its own bar.

This clause and §4.3's table are mirrors of each other: neither direction gets
special treatment.

## 5. Scoring protocol, fixed here as well

- Three blind raters. Blind packets and the sealed mapping committed **before**
  any rater runs.
- Calibration gate first, including the planted `NO_ANSWER` at 0.0. Never waived.
- Scores committed **before** the mapping is unsealed. Git order is the evidence.
- Rubric byte-identical to Study 011's. Criteria are not re-read against these
  answers.
- **Rater family departure, disclosed in advance:** §6.1 of the pre-registration
  requires three raters from distinct model *families*. Study 011 used three
  distinct models from one family and disclosed it. If a second family cannot be
  secured for Phase 2, the same departure is disclosed rather than absorbed.
  Shared-family bias inflates apparent agreement, and in a noise-band measurement
  inflated agreement **understates the band** — the direction that flatters the
  record. This is stated before the measurement, not after.

## 6. What this measurement cannot establish

Carried forward from §5's surrogate audit so it travels with the rule:

- Five runs **can cluster by chance and understate the true spread.** Every
  individual score is reported so a reader can see the clustering.
- The band is measured on **one configuration**. Noise may be
  configuration-dependent; applying it to other arms is an assumption, and it is
  stated wherever the band is cited.
- A tight band on Arm D says nothing about arms that diverge more.
- One corpus, one seed, one machine, one score pass.

This measures whether the instrument *can* resolve the differences the program
has been reporting. It does not establish the band for any other arm, corpus, or
budget.
