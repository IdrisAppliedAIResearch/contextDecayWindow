# EC-001 — External Calibration on LongMemEval

**Type:** Evaluation specification. External benchmark adoption. Not a mechanism study.
**Repository:** `contextDecayWindow` · `experiments/external/longmemeval/`
**Branch:** `ec/001-longmemeval`
**Status:** DRAFT — ready for handoff on commit
**Depends on:** CC-002 (`episodic` installable, PR #28) · LV-001 (PR #35) · E006 Part 1 (gate returned fail-closed)
**Companions:** `PAPER_001.md` · `RETRIEVAL_MECHANISM_LEDGER.md` · `LITERATURE_LANDSCAPE.md` §4

---

## 0. Why this, and why now

**The program has never been calibrated against anything outside itself.** Study 003
retired external baselines in favour of self-comparison. Nothing restored them.
Adoption was decided in principle in `LITERATURE_LANDSCAPE.md` §4 and deferred at
every decision point since.

Three recent results converged on making it the only remaining move:

1. **LV-001** measured availability against live correctness for the first time and
   found 16/16 offline become 1.5/8 live. Every number in the program's record before
   that is an availability count.
2. **E006 Part 1** failed closed: the rarity diagnostic that would have settled the
   corpus objection cannot be run, because rarity scores exist for 6 of 76
   fact-bearing episodes across three unreconciled variants. The categorical
   "IDF ranks them worse than density" claim is withdrawn.
3. **The corpus objection is therefore unresolved by any internal measurement.** It
   can only be settled on a corpus this program did not build.

**This document is not a mechanism experiment.** It changes nothing in the library.
It measures what the shipped component does on someone else's data.

---

## 1. The benchmark

<cite index="10-1">LongMemEval is a benchmark for five core long-term memory abilities of chat assistants: information extraction, multi-session reasoning, temporal reasoning, knowledge updates, and abstention, with 500 curated questions embedded in freely scalable user-assistant chat histories.</cite> ICLR 2025; arXiv:2410.10813; repo `xiaowu0162/LongMemEval`.

<cite index="13-1">Each instance is a 4-tuple (S, q, t_q, a), where S is a sequence of timestamped historical chat sessions, each session containing multiple user-assistant rounds, and the test query q is asked at a later time with a reference answer that is either a short phrase or a rubric for open-ended questions.</cite> <cite index="13-1">Abstention means answering "I don't know" when the required information is absent.</cite>

<cite index="16-1">Two standard sets: LongMemEval-S, roughly 115k tokens of chat history per question across 30–40 sessions; LongMemEval-M, roughly 500 sessions and 1.5M tokens.</cite>

**Difficulty is established.** <cite index="12-1">Long-context LLMs show a 30–60% performance drop on LongMemEval-S, and manual evaluation puts state-of-the-art commercial systems at 30–70% accuracy in a setting simpler than LongMemEval-S.</cite>

<cite index="15-1">The authors also formalize a memory design space in three stages — indexing, retrieval, reading — with four control points: value granularity (session, round, or compressive summary), key/indexing scheme (textual, fact-expanded, time-labeled), query form (standard or expanded), and retrieval algorithm.</cite> §5 records which of these this program is allowed to use.

**Version note.** <cite index="14-1">A LongMemEval-V2 targeting agentic context was announced in May 2026.</cite> **Use V1.** Comparability with published baselines is the entire point of adoption. Record V2's existence and the reason for not using it.

---

## 2. What this must answer

The centerpiece. Each question states what each outcome would mean, so no result can
be reinterpreted after the fact.

### Q1 — Is the cosine inversion a corpus artifact? **(Primary)**

PAPER-001 §5.2.1 reports that on this program's one enumeration probe, the four
highest-cosine episodes carry zero target facts and the last needed item sits at rank
87 of 119. §8.5 concedes the corpus is constructed and the effect may be a property of
the planted vocabulary — rare technical phrases whose component words are common.

**LongMemEval's facts are embedded in naturalistic conversation, not planted as rare
technical spans.** That is exactly the discriminating condition.

**Measurement:** for each question with annotated evidence sessions, compute the
cosine rank of every evidence session against the query. Report the rank distribution,
the fraction of questions where the top-4 carry no evidence, and the deepest
evidence rank required.

| Outcome | Meaning | Consequence |
|---|---|---|
| Inversion reproduces | Real property of conversational retrieval, not this corpus | §5.2.1 strengthens materially; E006 Part 2 becomes worth authorizing |
| Does not reproduce | Property of this program's planted vocabulary | §5.2.1 narrows to a corpus finding. **PAPER-001 must be corrected**, and chained retrieval is not indicated |
| Reproduces only on multi-session questions | Query-type-dependent, as the program suspects | The strongest possible result: eight-against-one becomes 133-against-many |

### Q2 — Where does targeted recall actually sit?

The program's targeted recall is reported at 60/60 and 16/16 offline, but LV-001's
live control scored **3.5/8**. Which of those describes the component is unknown.

LongMemEval's information-extraction questions are the external analogue. **Measure
against published baselines**, which exist for this benchmark and do not for anything
this program has run.

### Q3 — Is breadth a query type or one probe behaving oddly?

The program has **exactly one** enumeration question. Every breadth number in the
paper comes from it, and §8.2 says a single probe cannot support a claim about
enumeration in general.

<cite index="17-1">LongMemEval's multi-session reasoning questions require synthesizing fragmented information</cite> — the closest external analogue, at scale.

**This is the measurement that converts one instance into a category, or refutes it.**

### Q4 — Can the component abstain? **(Predicted failure, and that is the point)**

F3 — "no absence detection" — has been **UNCLAIMED** in the ledger since it was
written. The component always returns a block. It has no mechanism to report that
what was asked for is not there.

LongMemEval's abstention questions have ground truth for exactly this. **This is the
first opportunity to measure a known architectural gap against an external
standard**, and a clean negative is a publishable result rather than an embarrassment.

### Q5 — What happens when a fact changes? **(Never tested, and it matters for the product)**

The store is append-only and verbatim. When a user updates a fact, **both the old and
new values remain, and retrieval has no notion of supersession.**

<cite index="17-1">LongMemEval's knowledge-update questions track changing user states.</cite>
This is untested territory for the program and a direct deployment risk for the
assistant use case. A memory that confidently returns a superseded preference is
worse than one that forgets.

### Q6 — Does temporal ordering survive retrieval?

The store has turn order; retrieval has no temporal component. LongMemEval's temporal
reasoning questions test whether that matters. Also untested here.

### Q7 — How large is the availability-to-correctness gap on external data? **(The most valuable secondary result)**

LV-001 measured the gap once, on this program's corpus: 16/16 available offline,
1.5/8 correct live. §4 runs both tiers on LongMemEval deliberately so the same gap is
measured on data the program did not construct.

**No paper found in the program's literature scan reports this gap.** Every system in
the space reports end-to-end scores or recall, not the distance between them. Measuring
it on a public benchmark is a contribution independent of how the component performs.

### Q8 — Does the component survive contact with a foreign store at all?

115k tokens across 30–40 sessions against a 32,000-character budget is a compression
ratio the program has never run. Sessions are multi-round; the component's unit is a
single user/assistant exchange. **§6 records the adaptation decisions this forces**,
and any one of them can invalidate a comparison.

---

## 3. Scope

Deliberately narrow. The failure mode for benchmark adoption is a six-month
integration.

- **LongMemEval-S only.** M is ~500 sessions and 1.5M tokens; S is the standard
  comparable set. Record M as future work.
- **Full 500 questions for retrieval-only** (Tier 1). No generation, so cost is
  embedding and selection.
- **A registered subset for end-to-end** (Tier 2). Stratified across all question
  types, size set by the compute budget and **committed before any Tier 1 result is
  read**. Selecting the subset after seeing retrieval results is a surrogate failure.
- **No mechanism changes.** The shipped component as-is. If it cannot be run without
  modification, that is a finding, and §6 is where it gets recorded.

---

## 4. Two-tier evaluation — and the gap between them is a result

**Tier 1 — Retrieval only.** For each question, does the delivered block contain the
annotated evidence? Reported as recall against evidence sessions and as availability,
the program's own metric. No generation. Cheap, deterministic, directly comparable to
every number in PAPER-001 §5.

**Tier 2 — End-to-end.** Generate answers from the delivered block on the registered
subset. Score against reference answers and rubrics using the benchmark's own
protocol, not this program's rubric.

**Report Tier 1 minus Tier 2 explicitly.** That difference is the LV-001 finding
measured externally, and it is the answer to Q7. **Neither tier alone is the result.**

**Scoring discipline, carried unchanged:** scores commit before any mechanism log is
opened; reasoning-block content is never scoreable; multiple raters where the protocol
asks for them. **LV-001 ran one rater where three were required and said so in the
body — do not repeat it.**

---

## 5. What must NOT be adopted

<cite index="9-1">The benchmark's authors propose memory design optimizations: session decomposition for value granularity, fact-augmented key expansion for indexing, and time-aware query expansion for search scope.</cite>

**Fact-augmented key expansion and time-aware query expansion require LLM calls.**
The Study 005 principle — no generative calls in the memory path — survived all eleven
removals and is the property that makes the component deterministic, offline, and
provenance-preserving.

**Run the baseline configuration.** State explicitly in the report that the authors'
optimizations were available and deliberately not used, and why. A comparison against
their optimized numbers is not like-for-like and must be labelled.

Session decomposition is a granularity choice rather than an LLM call and may be
evaluated — but it is a **change to the component**, so it belongs in a follow-on, not
here.

---

## 6. Adaptation hazards — record every decision, each can invalidate the comparison

The benchmark's data model and the component's do not match. Every reconciliation is a
judgment call and **must be committed before results, with its alternative named**.

| Hazard | Decision needed | Why it can invalidate |
|---|---|---|
| **Session vs episode** | A session has multiple rounds; the component's unit is one exchange | Choosing session-as-episode changes the cost accounting and the selection granularity. Both directions are defensible; the choice must be stated, not slipped in |
| **Timestamps** | Instances carry session timestamps; the store has turn order only | Discarding them is a decision affecting Q6 directly |
| **Budget** | 32,000 characters against ~115k tokens of history | The program's budget was tuned on a 121-turn corpus. Using it unchanged is one choice; matching a published baseline's context size is another |
| **Recency window** | N is tuned for a single continuous conversation | Sessions are discontinuous. "Recent" may not mean what it means here |
| **Embedder** | Qwen3-Embedding-0.6B, pinned | Published baselines use different encoders. **Not like-for-like**, and §7.2's call-shape finding says even the same embedder moves results |
| **Abstention** | The component cannot abstain | Decide before running whether an empty or low-confidence block is scored as abstention. Deciding after is a surrogate failure |

**Register all six as a committed adaptation record before the first run.** A
comparison whose adaptation decisions were made while looking at results is not a
calibration.

---

## 7. Registered predictions

Committed so they can be wrong on the record. The author's prior in this program is
poor — nine predictions, most wrong on mechanism.

1. **Q1 — the inversion does NOT reproduce as strongly. ~55%.** LongMemEval's facts
   sit in naturalistic language, and the program's hardest facts are rare technical
   phrases whose components are common. That lexical property is the most plausible
   mechanism. **This prediction is unfavourable to PAPER-001 §5.2.1 and is registered
   for that reason.**
2. **Q4 — abstention near-total failure, under 20%.** The component has no absence
   mechanism. It will return a block and the model will answer from it.
3. **Q5 — knowledge updates fail badly.** Append-only with no supersession returns
   both values; the model has no signal about which is current.
4. **Q2 — information extraction is the component's best category**, and lands
   materially below published baselines that use LLM-assisted indexing.
5. **Q7 — the availability-to-correctness gap reproduces and is large.** LV-001's gap
   was not a corpus artifact.
6. **Q3 — multi-session reasoning is weak**, consistent with the breadth failures.

**The uncomfortable consequence, stated now:** predictions 1 through 6 are, taken
together, a poor showing. If they hold, the honest report is that a deterministic
no-LLM memory component underperforms LLM-assisted systems on most axes, with the
corpus objection partly sustained. **That is a legitimate result and the program
should publish it**, but it should be anticipated rather than discovered.

---

## 8. Surrogate audit

| Check | Certifies | Can it pass falsely? | Mitigation |
|---|---|---|---|
| Tier 1 recall | the component works | **Yes — LV-001 proved exactly this** | Tier 2 is mandatory; the gap is the headline |
| Evidence session retrieved | the answer is available | Yes — a session can be retrieved and the answering fact truncated out of the block | Check fact presence in the delivered block, not session identity |
| Inversion does not reproduce | corpus artifact confirmed | Yes — adaptation choices could suppress it | §6's decisions committed first; report rank distributions, not summary statistics |
| Comparable to published baselines | like-for-like | **Yes, and it is not** | Different embedder, different budget, no LLM indexing. Label every comparison |
| Abstention scored | the gap is measured | Yes — depends entirely on §6's abstention decision | Decide and commit before running |

**Accepted residual:** one benchmark, one runtime, one embedder, single run. This
removes self-referentiality; it does not add variance estimates. **The program still
has no error bars.**

---

## 9. Secondary output — the instrument audit

`LITERATURE_LANDSCAPE.md` §5 decided the program's differentiated asset is its
measurement work, not its architecture. The probe-order/answerability validator —
which caught three of this program's own degradation probes requesting facts before
they were planted — can run across LongMemEval at near-zero marginal cost, because the
data must be loaded anyway.

**Scope to the defensible:** probe ordering, answerability from stated evidence, fact
presence. Not subjective quality judgments. Findings per-benchmark with reproducible
scripts. No rankings.

**Frame as "we broke ours first."** The self-audit — 19 scores corrected, the only
VALIDATED verdict lost, a withdrawn IDF claim, LV-001 killing the shipped
configuration — is what earns standing to check anyone else's instrument.

**Both outcomes publish.** Problems found are immediately consequential; nothing found
is a genuine validation.

**Do not let this dominate.** It is a by-product of loading the data. Q1 through Q8
are the reason for the work.

---

## 10. Deliverables

- [ ] Adaptation record (§6), all six decisions committed before the first run
- [ ] Tier 2 subset registered before any Tier 1 result is read
- [ ] Predictions (§7) committed — SHA recorded
- [ ] Tier 1: full 500, recall and availability, per question type
- [ ] Cosine rank distribution of evidence sessions (Q1) — the primary result
- [ ] Tier 2: registered subset, benchmark's own scoring protocol, multiple raters
- [ ] **Tier 1 minus Tier 2 gap, reported explicitly** (Q7)
- [ ] Per-ability breakdown: extraction, multi-session, temporal, knowledge update, abstention
- [ ] Comparison to published baselines, with every non-comparability labelled
- [ ] PAPER-001 §5.2.1, §8.2, and §8.5 updated with the measured result **in either
      direction**, per the pre-registered both-outcomes-publish rule
- [ ] Probe-order validator run across the benchmark; findings recorded
- [ ] Ledger updated: F3 (absence detection) now has an external measurement

---

*Drafted August 2, 2026. LongMemEval: Wu, Wang, Yu, Zhang, Chang & Yu, ICLR 2025,
arXiv:2410.10813, `xiaowu0162/LongMemEval`. Program state: LV-001 returned
`A3_l0.1_r0.0_k16` to not-promoted; shipping default is per-item cosine ranking;
E006 Part 2 unauthorized; suite green at 1,007.*
