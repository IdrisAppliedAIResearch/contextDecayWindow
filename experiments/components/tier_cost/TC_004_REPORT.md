# TC-004 Report — embedding localization does not predict beneficial splits

**Pre-registration:** `TC_004_PRE_REGISTRATION.md`, commit
`ea6847948984f5aba76ff1f60bae29a9daeca25e`, LF SHA-256
`c0478b6795661c5521a169334c466f07fbd0da4b28b171fc13ec93bd3ef339d9`
**Implementation commit:** `1fdc85d728688e412149a1cb08ba2a294c97eabd`
**Vector-seal commit:** `323dcb60`
**G0–G6 commit:** `9331c40127c42e46536c713c3c76b41f1e5a2ba3`
**G7 outcome commit:** `f8574e752d2619dd3fc64f021fe250ca6d467fa0`
**G8 integrity commit:** `d2b5ef8f2d858cfe1d30cc3c710994e95bcd1af5`
**Standing:** `REGISTERED-OFFLINE` characterization on previously observed
LoCoMo development conversations. Availability only; not confirmation.
**Disposition:** **`NO_PREDICTIVE_SIGNAL`**
**Date:** August 23, 2026
**Artifacts:** `artifacts/tc004/`, `runs/tc004/g0/`, `runs/tc004/run/`

---

## 1. The verdict

The registered embedding-localization statistic does not identify which parent
pairs benefit from replacement by their two source turns better than parent
length does.

| Primary, 16,000 chars / complete evidence | Result |
|---|---:|
| AP-evaluable questions | 53 |
| Embedding-localization AP wins / losses / ties | **21 / 31 / 1** |
| Mean embedding-localization AP | 0.1021 |
| Mean length AP | 0.0544 |
| Mean paired difference | +0.0477 |
| One-sided exact sign-test *p* | **0.9368** |
| Registered disposition | **`NO_PREDICTIVE_SIGNAL`** |

The mean and the paired direction disagree. Embedding localization has median
AP **0.0145** against length's **0.0213**, but three or more questions at the
upper tail reach AP 1.0 and lift its mean; length's maximum is 0.333. The
registered statistic is question-level wins and losses, so the outlier-weighted
mean cannot rescue 21 wins against 31 losses. Both upper and lower signal tiers
require gains to exceed losses, and neither fires.

The instrument is adequate. Fifty-three questions exceed the six-question
minimum, the positive and adverse controls exist, and the actual primary has
**96 beneficial** and **235 harmful** one-parent splits. This is a mechanism
failure under the registered test, not an empty-population or unreachable-bar
stop.

## 2. The operational curves do not supply a hidden positive result

Applying each predictor to the whole store was the locked surrogate audit. At
16,000 characters:

| Split rate | Embedding complete | Length complete | Embedding any | Length any |
|---:|---:|---:|---:|---:|
| 0% | 749 | 749 | 803 | 803 |
| 1% | **752** | 749 | **804** | 803 |
| 2% | **752** | 744 | **804** | 801 |
| 5% | 750 | 750 | 806 | **809** |
| 10% | 748 | 748 | 809 | **811** |
| 20% | 739 | **743** | **806** | 803 |
| 50% | **721** | 717 | **786** | 781 |
| 100% | 687 | 687 | 750 | 750 |

The best embedding-localization point is a descriptive **+3 complete
questions** at 1–2%. It has no registered rate-selection bar and cannot change
the primary disposition. The direction is not stable across endpoints or
rates: length is ahead on any-evidence at 5–10%, and embedding localization is
behind on complete evidence at 20%.

At 32,000, embedding localization again reaches a local +3 at 1% (813 versus
810 complete), then degrades. Full splitting converges across policies at
**754 complete / 800 any**, down from zero split's **810 / 842**. At 16,000,
full splitting is **687 / 750**, down from **749 / 803**. Splitting creates more
delivered units—median 54 to 84 at 16,000 and 111 to 170 at 32,000—but more
units are not more complete evidence.

This is the registered residual in concrete form: a candidate-level statistic
can show occasional large AP wins while false-positive splits make the complete
store worse.

## 3. The lexical ablation is worse

The evidence-free lowercase token-count localization ablation has mean AP
**0.0221**, median **0.0085**, and maximum **0.1494**. It is below both the
embedding statistic and length on mean and median. At 1% it lowers the
16,000-character complete endpoint from 749 to 744 and the 32,000 endpoint from
810 to 805. It carries no bar and supplies no alternate disposition.

The author's definition of model-free was implemented as registered: embedding
calls are allowed; LLM/generative calls are not. G5 made exactly **2,661 solo
embedding calls**—one sentinel plus 2,660 unique child texts—and zero
generation calls. G6 through G8 used only the sealed caches and made zero
embedding or generation calls.

## 4. The failure is broad, but the mean is unstable

Only `conv-41` has more embedding AP wins than losses. The other three
conversations are negative on the paired direction:

| Conversation | n | wins / losses / ties | Mean embedding AP | Mean length AP |
|---|---:|---:|---:|---:|
| `conv-41` | 11 | 7 / 4 / 0 | 0.2841 | 0.0687 |
| `conv-42` | 18 | 5 / 12 / 1 | 0.0259 | 0.0432 |
| `conv-47` | 9 | 3 / 6 / 0 | 0.0439 | 0.0603 |
| `conv-48` | 15 | 6 / 9 / 0 | 0.0950 | 0.0538 |

Category 1 ties 8 wins to 8 losses with one tie. Categories 2–5 are all
negative on paired direction. Questions with one evidence ID—the largest cut,
31 of 53—have **9 wins and 22 losses**. Two-ID questions reverse at 8/5, but
that cut is descriptive and does not repair the full population.

Three planned candidate-covariate AP cuts are not assigned a numeric result:
parent-length quartile, child-length ratio, and parent cosine. The registration
did not define how a question-level AP should be assigned to a candidate-level
stratum when its ranked list spans several values, nor did it define bins for
the latter two variables. Choosing that convention after G7 would be a post-run
parameter. This affects no bar or disposition; the omission is recorded rather
than silently repaired.

## 5. Gates and integrity

| Gate | Outcome |
|---|---|
| G0 | Registration first-commit and LF hash exact; child cache unopened |
| G1 | Four conversations, 882 records, 871 unique resolved questions, 868 complete-evaluable, 1,365 parents, 1,297 splittable, 68 singleton, 2,660 child texts, 2,592 absent vectors |
| G2 | Evidence-blind mechanism/import audit passes; planted import and evidence access both fail |
| G3 | 20,904 standing-row fields reproduce TC-003; zero split equals `A_FLAT` on 1,742 question-budget cells |
| G4 | 22 TC-004 tests pass; full suite 2,168 passes before capture |
| G5 | Sentinel exact; 2,660 solo vectors sealed, 2,661 calls including sentinel, zero LLM/generation calls; read-only reopen 2,660 hits/0 misses |
| G6 | Two 622,250-cell evidence-blind replays produce identical selection digest `0967510f…`; zero cache misses |
| G7 | G0 commit is an ancestor; selection digest exact; outcome committed before diagnostics |
| G8 | Outcome replay byte-identical; disposition table applied once; zero measurement calls |

The child cache has file SHA-256
`2725af7df48850ffe28f945e452593fd74847d7f87afe7aa7daf00321c5393a9`
and canonical content SHA-256
`26fc3410f1f5fbb05342a67cb2a973dcc6ff18cda6b0dd1bff1ea84149561413`.

G3 caught one measurement-layer distinction before G5: the carried CSV stores
resolved-ID completeness even on the three rows excluded from the complete
endpoint because they have unresolved IDs. The comparator now reproduces that
row field while the registered 868-question endpoint continues to exclude
those rows. All standing aggregates and identities are exact.

## 6. What this establishes, and what it does not

**Established on this observed corpus and pinned embedder:**

- max-child-minus-parent embedding cosine does not beat parent length on the
  registered paired predictor statistic;
- beneficial candidate splits exist, but harmful ones are more numerous;
- a few high-AP questions can raise mean AP while most paired questions favor
  the baseline;
- splitting every pair increases unit count and reduces evidence availability;
- the lexical no-embedding ablation is worse still.

**Not established:**

- **No claim that chunking cannot work.** This tests one source-turn boundary
  and one prospective split predictor.
- **No optimum chunk size or rate.** The 1% descriptive local maximum was not a
  registered optimization endpoint.
- **No reader-quality claim.** Availability is not use; TC-006 owns that.
- **No raw-length causality.** Splitting changes localization, wrapper cost,
  ranking, and packing together.
- **No production decision.** The result neither adopts nor deletes a memory
  representation.
- **No confirmation.** LoCoMo development was already observed.

## 7. Rule 4 dependency re-read

TC-004 has reported, so the roadmap's Rule 4 was re-read before any TC-005
registration. Nothing is blocked.

TC-005 still has the required 50-to-1,000 current-implementation pool-size and
latency series. TC-004 changes no cluster assignment or pool identity and
consumes none of that artifact. TC-006 still has multiple frozen context pairs
with known availability margins; its missing instrument-spread measurement is
still its own first task, not an upstream block.

TC-004's negative disposition is a result, not a missing artifact. It closes
this registered embedding-localization predictor on this store. It does not
close candidate granularity as a research family and does not authorize a
different split rule post hoc.
