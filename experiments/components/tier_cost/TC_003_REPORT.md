# TC-003 Report — floors win the fixed orders, but the contest key carries the gain

**Pre-registration:** `TC_003_PRE_REGISTRATION.md`, commit
`863d0a677943eb2990f5a912f26429dbba0df45c`, SHA-256
`653cc575b5cc79145421dc45766059fdfb9871e17d2349ee97f92eecd36ecc60`
**G0 commit:** `8a017e052b6e5bc2629e5ac3ad94fa7b9373a511`
**Execution commit:** `8a017e052b6e5bc2629e5ac3ad94fa7b9373a511`
**Artifact commit:** `1901b73101eea66444da1b3291bc49b1bd9b267d`
**Standing:** `REGISTERED-OFFLINE` characterization — bars locked first, zero
generative calls, replayable against a retained embedding cache, on a corpus
this programme had already observed. **Not confirmation.**
**Disposition (C1, the registered headline):** **D1 — `FLOORS_WINS`**
**Isolating contrast (C5):** **D3 — `RANKED_WINS`**
**Deterministic properties:** **I1 PASS; I2 FAIL**
**Date:** August 22, 2026
**Artifacts:** `runs/tc003/g0/`, `runs/tc003/run/`,
`artifacts/tc003/preflight/`

---

## 1. The verdict

Equal-share reserved floors beat both fixed sequential orders on complete
evidence delivery at the registered 16,000-character primary:

| Contrast | Complete evidence, 868 questions | gains / losses | net | one-sided *p* | Disposition |
|---|---:|---:|---:|---:|---|
| **C1** `A_FLOORS` vs `A_N_FIRST` | **656** vs 314 | 357 / 15 | **+342** | 2.25 × 10⁻⁸⁶ | **D1 `FLOORS_WINS`** |
| **C2** `A_FLOORS` vs `A_K_FIRST` | **656** vs 461 | 258 / 63 | **+195** | 1.86 × 10⁻²⁹ | **D1 `FLOORS_WINS`** |
| **C3** `A_FLOORS` vs `A_FLAT` | 656 vs **749** | 5 / 98 | **−93** | 9.09 × 10⁻²⁴, flat direction | **D3 `FLAT_WINS`** |
| **C4** `A_FLOORS_DUAL` vs `A_DUAL` | **718** vs 472 | 266 / 20 | **+246** | 2.43 × 10⁻⁵⁶ | **D1 `FLOORS_DUAL_WINS`** |
| **C5** `A_FLOORS_DUAL` vs `A_DUAL_RANKED` | 718 vs **748** | 8 / 38 | **−30** | 4.62 × 10⁻⁶, ranked direction | **D3 `RANKED_WINS`** |
| **C6** `A_FLOORS_DUAL` vs `A_FLAT` | 718 vs **749** | 9 / 40 | **−31** | 4.63 × 10⁻⁶, flat direction | **D3 `FLAT_WINS`** |

Band **B = 4**; α = 0.01/6. Every primary contrast clears a registered
directional bar.

**C1 is positive, but C1 does not isolate the floor.** The registration fixed
the interpretation of C1 and C5 together before either split was known. C1
compares floors-plus-global-cosine-contest against a store-ordered fixed fill.
C5 holds the relevance-order lever common and isolates the reservation. C5
lands in the opposite direction: the relevance-ranked dual arm beats the floor
arm by 30 questions.

The registered reading therefore applies exactly:

> **The gain is the contest key, not the reservation.**

Reserved floors are better than either fixed order, but the floor arm still
trails the flat ranking by 93 questions. Removing recency narrows that deficit
to 31 and does not remove it. This is an allocation characterization, not an
adoption result.

## 2. The headline gains occur in the contested remainder

The phase attribution makes the C1/C5 reading mechanical rather than an
interpretive guess.

Of C1's **357 gains**:

- **339** carried evidence only through the contested remainder;
- **12** carried it through both reserved and contested admissions;
- **6** carried it only through a reservation.

So 351 of 357 C1 gains include contested evidence, while only 18 include
reserved evidence. The sequential arm's 15 gains in the other direction are
12 questions where the floor arm delivered no evidence and 3 where it delivered
reserved evidence.

Across all 732 questions where `A_FLOORS` delivered any evidence, 406 were
contested-only, 293 reserved-only, and 33 used both phases. The contest is not a
small cleanup pass: it supplies evidence on most of the arm's successful
questions and on almost every question that decides C1.

C5 supplies the held-order check. Of its 38 losses, the floor arm delivered no
evidence on 25, contested evidence on 8, both phases on 4, and reserved evidence
on 1. The relevance-ranked arm wins after the reservation is isolated.

## 3. Floors remove one order and create a consequential second one

The deterministic property that motivated the design passes in its narrow
form and fails in its broad form.

| Budget | Configuration | I1: service-order invariant | I2: ownership-order invariant | Zero-floor ownership reference | Maximum symmetric difference under floors |
|---:|---|---:|---:|---:|---:|
| 16,000 | shipped | **871 / 871** | **0 / 871** | 860 / 871 | 59 |
| 16,000 | dual | **871 / 871** | 238 / 871 | **871 / 871** | 52 |
| 32,000 | shipped | **871 / 871** | 10 / 871 | 864 / 871 | 75 |
| 32,000 | dual | **871 / 871** | 522 / 871 | **871 / 871** | 90 |

**I1 passes everywhere.** All six service permutations produce the same
delivered set on every question, at both budgets and under both configurations.
The zero-floor control separates them on the exact populations registered in
PF4, so this is not invariance measured with an inert instrument.

**I2 fails.** Every question contains at least one candidate shared by two
tiers. Under floors, ownership decides which allowance pays for a shared item;
changing that convention changes the delivered set on every shipped-config
question at 16,000, and on 633 of 871 dual-config questions there. Under the
zero-floor sequential reference, the set is invariant on 860 and 871 of those
same questions respectively.

The report must therefore use the registration's narrower sentence, in its
registered words:

> **Floors make allocation independent of service order and leave it dependent
> on ownership order.**

The 16,000 shipped arm moves from a zero-floor maximum symmetric difference of
1 episode to a floors maximum of 59. Floors did not merely reveal a large
pre-existing dependence; they made ownership decide which budget is spent.

## 4. What the allocation actually delivered

Median composition, all 871 questions:

| Budget | Arm | Delivered | Recency | K | Coverage | Reserved | Contested | Everything fits |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 16,000 | `A_FLOORS` | 54 | 18 | 31 | 3 | 38 | 14 | 0 |
| 16,000 | `A_FLOORS_DUAL` | 55 | 0 | 49 | 3 | 30 | 22 | 238 |
| 32,000 | `A_FLOORS` | 110 | 32 | 53 | 20 | 88 | 16 | 0 |
| 32,000 | `A_FLOORS_DUAL` | 111 | 0 | 83 | 23 | 75 | 29 | 520 |

At the primary, the shipped floor binds on 871/871 questions for recency,
773/871 for K, and 172/871 for coverage. Under the dual configuration it binds
on 733 for K and 138 for coverage. These exactly reproduce Preflight Part 1's
name-to-behaviour distributions.

At 32,000 the recency floor binds on **0/871**, also as registered before the
run. That secondary budget is not evidence about reserving recency capacity:
all 32 recency members already fit inside its nominal third. The K and coverage
floors are the active constraints there.

## 5. The result is not one conversation or one category

Every pre-specified primary complete-evidence cut has the same sign on all six
contrasts.

| Conversation | n | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `conv-41` | 193 | +70 | +35 | −13 | +42 | −3 | −2 |
| `conv-42` | 258 | +107 | +59 | −34 | +79 | −13 | −14 |
| `conv-47` | 189 | +57 | +37 | −20 | +47 | −5 | −6 |
| `conv-48` | 228 | +108 | +64 | −26 | +78 | −9 | −9 |

| Category | n | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 107 | +19 | +5 | −24 | +20 | −7 | −6 |
| 2 | 143 | +54 | +15 | −10 | +19 | −2 | −3 |
| 3 | 42 | +5 | +4 | −3 | +5 | −1 | −1 |
| 4 | 386 | +187 | +127 | −31 | +143 | −12 | −13 |
| 5 | 190 | +77 | +44 | −25 | +59 | −8 | −8 |

The cuts are descriptive; the registered family bars apply to the full paired
population, not separately to each stratum.

## 6. Every secondary agrees where a bar exists

At 16,000, any-evidence delivery gives the same dispositions as the primary:
C1 +351, C2 +213, C3 −71, C4 +251, C5 −22, C6 −24.

At 32,000, complete evidence gives C1 +125, C2 +73, C3 −52, C4 +112, C6 −4;
any evidence gives +124, +79, −31, +104, and +2 respectively. C1 through C4
keep the primary direction and disposition. C6 is `D0a` on both endpoints:
inside the 10-question band, which is a power statement and not equivalence.

**C5 at 32,000 is descriptive by registration.** It has 9 discordant pairs
against B = 10, so no possible split could clear the band. Observed complete
evidence is 806 vs 811 (net −5); any evidence is 844 vs 843 (net +1). Neither
receives a disposition, and neither may be used to revise the primary C5 result.

The C3 wrapper-matched robustness pass is byte-for-byte identical in its
statistics at both budgets and endpoints. Charging the flat arm 18 fewer
characters leaves the primary complete split at 656 vs 749, 5 gains and 98
losses. The wrapper does not explain the flat arm's lead.

## 7. Preflight and gates

| Check | Outcome |
|---|---|
| PF1 | Pass. Dataset and cache digests asserted; 2,247 cache hits, 0 misses; every source hashed in each run header |
| PF2 | Pass with one registered name failure. The allocator reduced byte-for-byte to both committed packers on 3,484 checks. At 32,000 the recency floor never binds, so “reserved recency floor” does not describe that secondary behaviour |
| PF3 | Pass. G0 committed at `8a017e05` before the run opened evidence labels; `run_precondition.json` records that commit and gate digest |
| PF4 | Pass with one registered exception. All primary branches were reachable; C5 at 32,000 was proved unreachable and registered `DESCRIPTIVE` before the run |
| PF5 | Pass. Candidate, question, and delivered-item keys are stable content identities |
| PF6 | Pass. Twenty inherited cells reproduced both their transcribed values and committed artifacts exactly |
| PF7 | Pass. No feedback; every degenerate “everything fits” population was measured on the full corpus |
| PF8 | Not applicable: full-population offline replay over 871 questions, not a sampled ablation |
| PF9 | The residuals survive: availability is not use; the global contest changes a second lever; ownership order remains; the 32,000 recency floor is inert |
| PF10 | No live claim. This is availability characterization only |

G0 also re-ran all 3,484 zero-floor identities and both positive controls. It
reported no mismatch. The full run made zero model or inference calls, had zero
cache misses, and its artifact manifest verifies every output file.

## 8. What this establishes, and what it does not

**Established on this observed corpus:**

- an equal-share floors-plus-cosine-contest allocator delivers complete
  evidence more often than both fixed sequential orders;
- the global cosine contest, not the reservation, carries the demonstrated
  gain;
- service-order invariance holds exactly;
- ownership-order invariance does not, and floors make that order materially
  consequential;
- neither floor configuration beats the flat cosine arm at the primary.

**Not established:**

- **No shipping decision.** TC-002's registration and `PAPER_002.md` §9.3
  already separate availability from adoption; TC-006 owns the reader.
- **No answer-quality claim.** LV-001 measured that availability can fail to
  become correct use.
- **No best floor vector.** Equal shares was the one zero-parameter rule. A
  sweep is a new policy-level study and remains unauthorized.
- **No result about a real recency window.** This is allocation among the tiers
  as they exist on a finished transcript.
- **No confirmation.** LoCoMo development was already observed by three prior
  arc studies.
- **No eighth arm.** A floors arm with a relevance-ordered K tier is the
  obvious combined configuration and was explicitly excluded. This result does
  not authorize adding it post hoc.

## 9. Rule 4 dependency re-read

TC-003 has reported, so `TC_ARC_ROADMAP.md` Rule 4 fires. The dependency log is
updated in the same commit as this report, as §10 of the registration requires.

**Nothing is blocked.** TC-004's span-labelled corpora still exist; TC-005's
pool-size/latency series still exists; TC-006 may begin by measuring its own
fact-use instrument's spread. TC-003's verdict is not a missing artifact and
cannot block another study.

What changes is interpretation, not runnability. The floor proposal does not
isolate an availability gain, and the flat arm remains ahead. TC-006 now has an
additional frozen context pair separated by a registered 342-question complete-
evidence margin, but it still needs the finer reader instrument its own first
task is designed to measure.
