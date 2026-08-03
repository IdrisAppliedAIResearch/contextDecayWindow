# EC-001 — External Calibration on LongMemEval

**Pre-registration:** `EC_001_longmemeval_calibration.md` at
`b595b05e1469c67277844d4bd97f77c89a20772b`  
**Adaptation record:** `a65c2566e55a2063bd1904065032f86c5d0e23a9`  
**Status:** COMPLETE  
**Primary outcome:** COSINE INVERSION DOES NOT REPRODUCE AS A DOMINANT
LONGMEMEVAL PATTERN  
**Scoring outcome:** CODEX-SUBSTITUTED INTEGRITY ONLY — NOT AN OFFICIAL OR
BENCHMARK-COMPARABLE LONGMEMEVAL SCORE

---

## 1. Result

The shipped component ran without mechanism changes over all 500 cleaned
LongMemEval-S questions and generated answers for the prospectively registered
140-question subset. The external data reject the broad reading of the
program's internal cosine inversion: only **69 of 470 answerable questions
(14.7%)** place every evidence session below the top four, rather than the top
four all being empty on the program's one enumeration probe. Across 890
annotated evidence sessions, the median rank is 2, the 95th percentile is 23,
and the deepest observed evidence rank is 49.

Retrieval performance is nevertheless weak. A delivered block contains at
least one exact annotated answer turn on **79 of 470 answerable questions
(16.8%)**, and contains all annotated answer turns on **20 of 470 (4.3%)**.
Evidence-session identity is more permissive: any-session recall is 109 of 470
(23.2%), while all-session recall is 34 of 470 (7.2%).

End-to-end, the three-rater consensus plus independent AI adjudication returns:

- **28 of 140 (20.0%)** on the deliberately equal-quota subset;
- **12.22%** after post-stratifying the seven per-stratum accuracies to the
  verified 500-question benchmark distribution.

These are **Codex-substituted integrity scores** under Amendment 010. The
official LongMemEval GPT-4o evaluator was not available, GPT-5.4 has no
immutable API snapshot or fixed hosted seed, and the adjudicator was GPT-5.5
rather than a human. Neither number may be reported as an official LongMemEval
score or placed directly against published LongMemEval system scores.

---

## 2. Q1 — the primary cosine-inversion result

The pre-registration distinguishes three outcomes. The first — a general
reproduction of the inversion — does not occur. The third — reproduction only
on multi-session questions — also does not occur.

| Stratum | Questions | Top four contain no evidence | Deepest evidence rank |
|---|---:|---:|---:|
| Knowledge update | 72 | 5 (6.9%) | 27 |
| Multi-session | 121 | 13 (10.7%) | 42 |
| Single-session assistant | 56 | 4 (7.1%) | 22 |
| Single-session preference | 30 | 10 (33.3%) | 30 |
| Single-session user | 64 | 16 (25.0%) | 30 |
| Temporal reasoning | 127 | 21 (16.5%) | 49 |
| **All answerable** | **470** | **69 (14.7%)** | **49** |

The complete evidence-session rank distribution has median 2, p90 14, p95 23,
and maximum 49. Multi-session is not the exceptional category: its top-four
failure rate is below the overall rate, while single-session preference and
single-session user are highest.

This does not prove the internal inversion was caused by rare planted
vocabulary. EC-001 changed corpus, history structure, ranking unit, and query
population together. It does establish the registered discriminating result:
the striking internal pattern — four of four top episodes empty and the last
needed item at rank 87 of 119 — is not a dominant property of naturalistic
LongMemEval questions under the carried embedder.

The rank measurement is session-level without changing the component:
each session receives the maximum cosine of its exchange episodes, with stable
chronological and session-id tie breaks. Whole-session embeddings were not
introduced.

---

## 3. Tier 1 — retrieval and availability

Abstention questions have no answer location in cleaned V1, so their evidence
recall and availability are null by registration. They remain in the 500-item
processing count and enter Tier 2 scoring.

| Stratum | n | Any evidence session | All evidence sessions | Any exact answer turn | All exact answer turns |
|---|---:|---:|---:|---:|---:|
| Knowledge update | 72 | 27.8% | 0.0% | 22.2% | 0.0% |
| Multi-session | 121 | 28.1% | 0.0% | 24.0% | 0.0% |
| Single-session assistant | 56 | 33.9% | 33.9% | 12.5% | 12.5% |
| Single-session preference | 30 | 3.3% | 3.3% | 3.3% | 3.3% |
| Single-session user | 64 | 15.6% | 15.6% | 9.4% | 9.4% |
| Temporal reasoning | 127 | 19.7% | 3.1% | 15.7% | 4.7% |
| **All answerable** | **470** | **23.2%** | **7.2%** | **16.8%** | **4.3%** |

The session/turn split matters. Retrieving a session is not sufficient when the
exact answer-bearing exchange is absent from the returned block. Thirty
evidence-session hits disappear between any-session recall (109) and any-turn
availability (79), directly reproducing the surrogate hazard registered before
the run.

The information-extraction analogue — the three single-session strata combined
— reaches any-session recall on 30 of 150 questions (20.0%) and any exact-turn
availability on 14 of 150 (9.3%). The registered prediction that extraction
would be the component's best end-to-end category is not supported.

---

## 4. Tier 2 — Codex-substituted integrity

The registered subset uses 20 questions from each of seven strata. Equal
quotas enforce the requested per-stratum floor but do not reproduce the
benchmark population, so the raw micro-average is not a benchmark-distributed
aggregate.

| Stratum | Correct | Accuracy |
|---|---:|---:|
| Abstention | 17 / 20 | 85% |
| Knowledge update | 4 / 20 | 20% |
| Multi-session | 0 / 20 | 0% |
| Single-session assistant | 3 / 20 | 15% |
| Single-session preference | 0 / 20 | 0% |
| Single-session user | 4 / 20 | 20% |
| Temporal reasoning | 0 / 20 | 0% |
| **Equal-quota subset** | **28 / 140** | **20.0%** |

Post-stratifying those seven rates against the verified population counts
(64, 56, 30, 127, 72, 121, and 30) gives **12.22%**. This estimate inherits
the same evaluator substitution and single-run limitations as the raw score.

The result separates architectural capability from reader behavior. The
component emitted **zero abstention signals on all 500 questions**, exactly as
registered. The reader nevertheless answered 17 of 20 abstention questions
correctly. EC-001 therefore confirms that the component has no absence
detector, while refuting the prediction that this necessarily causes
near-total end-to-end abstention failure under this reader and prompt.

Knowledge update is weak at 4 of 20, consistent with an append-only store that
does not represent supersession. Multi-session and temporal reasoning both
score 0 of 20. The latter matters because timestamps were preserved only in
measurement sidecars, not injected into storage or retrieval.

---

## 5. Q7 — availability minus correctness

The registered exact gap uses complete answer-turn availability, not session
identity or any-turn availability. After excluding 20 abstention items and two
items whose evidence-turn labels are incomplete, 118 questions remain:

| Measure | Count | Rate |
|---|---:|---:|
| All annotated answer turns available | 8 / 118 | 6.78% |
| Correct under Codex-substituted integrity | 11 / 118 | 9.32% |
| **Tier 1 minus Tier 2** | **−3 / 118** | **−2.54 percentage points** |

The predicted large positive availability-to-correctness gap does not
reproduce. Its sign reverses. This does not mean retrieval is unnecessary:
complete exact-turn availability is a strict mechanical criterion, and one
correct answer can be produced without satisfying it. It means the registered
external measurement does not support the claim that availability is
systematically higher than correctness on this subset.

The broader presence/correctness split remains. Ten available items are wrong,
and some correct answers occur without complete marker availability. A
retrieval count and an answer score are different measurements in both
directions.

---

## 6. Answers to Q2–Q8

**Q2 — targeted recall.** The three single-session strata reach 9.3% exact-turn
availability and 7 of 60 correct on the equal-quota subset. They are not the
best non-abstention group. Direct comparison to published systems is not
authorized after Amendment 010.

**Q3 — breadth.** Multi-session reasoning is weak at both tiers: 24.0%
any-turn availability on all 121 questions and 0 of 20 correct on Tier 2. This
supports the prediction that synthesis across sessions is a category-level
weakness, while Q1 shows that top-four cosine inversion is not its general
cause.

**Q4 — abstention.** The component produces no absence signal (0 of 500), but
the reader scores 17 of 20. Component-level absence detection remains absent;
end-to-end abstention is not the predicted failure.

**Q5 — knowledge update.** Any-turn availability is 16 of 72 and Tier 2
correctness is 4 of 20. The predicted weakness appears.

**Q6 — temporal ordering.** Any-turn availability is 20 of 127, and Tier 2
correctness is 0 of 20. Turn order without timestamp-aware retrieval does not
support the tested temporal questions.

**Q7 — availability to correctness.** The registered gap is −2.54 percentage
points, not the predicted large positive gap.

**Q8 — foreign-store survival.** Integration succeeds mechanically. The
adapter losslessly processes 246,750 source turns into 124,366 episodes across
500 questions, including 1,951 irregular-session instances, and the source,
script, score, and sealed-log integrity hashes pass. Surviving the data model
does not imply answering it well.

---

## 7. Published-baseline boundary

The pre-registration required comparison to published LongMemEval baselines
with every non-comparability labelled. Amendment 010 later superseded the
scoring path after OpenAI API access failed: it forbids producing or imputing
the pinned GPT-4o benchmark-protocol score and forbids direct comparison of the
Codex-agent result with published LongMemEval scores.

Accordingly, **no numeric published-baseline comparison is reported**. The
reasons are material:

- cleaned V1 histories rather than the original ICLR histories;
- Qwen3-Embedding-0.6B Q8_0 rather than published retrievers;
- an exact 32,000-character returned-block ceiling rather than published token
  or top-k limits;
- exchange-level storage with no LLM key expansion or time-aware query
  expansion;
- a Qwen3.6 27B reader and Codex-substituted evaluator panel rather than the
  benchmark's pinned evaluator.

The benchmark authors' LLM-assisted indexing and time-aware query expansions
were available and deliberately not adopted. They add generative calls to the
memory path and would change the shipped deterministic component. Session
decomposition was also not adopted because it changes storage granularity.

This is an external stress test and calibration of failure modes, not a system
leaderboard entry.

---

## 8. Instrument audit

The prospectively registered mechanical audit emits 358 findings:

| Predicate | Findings |
|---|---:|
| Nonchronological adjacent session timestamps | 211 |
| Session timestamp not before question timestamp | 76 |
| Answer session without an answer-marked turn | 32 |
| Abstention item with an answer-session identifier | 30 |
| Abstention item with an answer-marked turn | 9 |

These are predicate hits, not 358 adjudicated benchmark defects. One item may
trigger multiple predicates, and some patterns may be intentional properties of
the cleaned construction. The defensible result is the reproducible inventory:
the benchmark contains timestamp and answer-location relationships that a
consumer cannot safely infer away.

The audit is framed as a by-product because this program first invalidated and
corrected its own scoring, budget, and probe-order claims. It is not a ranking
of benchmark quality.

---

## 9. Integrity and amendments

The design commit contains only the specification. All six adaptation decisions,
the Tier 2 subset, and the audit predicates commit before Tier 1 results. Tier 1
scores commit before the sealed mechanism log. Reader answers and masked rater
packets commit before rater outputs, trigger preparation, adjudication, identity
unsealing, or final aggregation.

Reader determinism passes a byte-identical seeded-prefix rerun. Tier 1 source
integrity passes with unchanged dataset and script hashes. The generation
runtime records llama.cpp build `b9294-0f3cb3fc8`, one slot, seed 5005, and no
speculative decoding.

Three blind rater families — Phi, Mistral, and hosted GPT-5.4 — produce 120
unanimous final labels. Six disagreements trigger H2, and 14 unanimous blind
controls trigger H5. Hosted GPT-5.5 independently adjudicates all 20 triggered
items. GPT-5.4 passes its planted calibration, and both hosted stage outputs
pass their mechanical validators before acceptance.

Ten standalone amendments record schema repairs, scoring reconciliation, local
rater failures and replacements, chat transport, and the final hosted
substitution. None changes reader answers, rubric content, subset membership,
mechanical-zero decisions, or criteria after an affected result is opened.

The final adjudicator is AI, not human. Hosted model identity rests on the
user-attested desktop display selection inherited by a fresh child; there is no
immutable API model id, build hash, temperature, or seed for GPT-5.4 or GPT-5.5.

---

## 10. Limitations

- One reader, one embedder, one seed, one machine, no variance estimate.
- The rank comparison changes corpus and ranking unit together; it rejects
  dominant generalization, not every possible vocabulary explanation.
- Exact answer-turn matching is stricter than semantic availability and cannot
  by itself certify what the reader knew.
- Equal Tier 2 quotas deliberately overrepresent small strata. The 20.0% raw
  score is not benchmark-distributed.
- The 12.22% post-stratified estimate applies observed rates from 20 items per
  stratum and has no uncertainty interval.
- Codex-substituted scoring is not the benchmark's official evaluator.
- AI adjudication does not satisfy a human-adjudication claim.
- Cleaned V1 differs from the original histories behind published results.
- LongMemEval-M, LoCoMo, alternative embedders, optimized indexing, and repeated
  seeds remain untested.

---

## 11. Artifact index

| Artifact | Commit |
|---|---|
| Pre-registration | `b595b05e` |
| Adaptation record | `a65c2566` |
| Tier 2 subset and instrument-audit registration | `cfcf4c01` |
| Tier 1 scores, summary, audit, and integrity record | `08e90fa3` |
| Sealed Tier 1 mechanism log | `7511ebc` |
| Tier 2 reader answers | `cc59584c` |
| Masked scoring packets | `e1878d7e` |
| Phi rater | `53fb26fc` |
| Mistral rater | `06b6b3dd` |
| GPT-5.4 rater and calibration | `f15b0401` |
| Adjudication triggers | `fbdb17ed` |
| GPT-5.5 adjudications | `9863a4a7` |
| Codex-substituted final scores | `e59f86cd` |

Downloaded model resources are recorded by exact path, byte count, source
revision, and SHA-256 in `EC_001_CLEANUP_MANIFEST.json`. The study-created
model files are eligible for later deletion after closeout validation, but the
manifest requires separate explicit user confirmation; EC-001 performs no
automatic cleanup.
