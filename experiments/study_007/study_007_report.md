> **CORRECTION (2026-07-26):** Treatment remains 12.0; control corrects 10.5 -> **10.0**. The PARTIAL 2/3 verdict is unchanged. Original claims remain below. See `../audits/scoring_integrity/audit_report.md`.

# Study 007 — Information-Expressed, Diversity-Floored Retrieval

## contextDecayWindow · Idris Applied AI Research

**Status:** COMPLETE — **PARTIAL**
> **CORRECTION — read this first.** The diagnosis in *The finding* below is
> **wrong** and is superseded by
> `evaluation/position_and_grounding_analysis.md`. This report claimed the model
> had all four domains' facts and substituted background knowledge. Item-level
> checking of the committed logs shows the opposite: at Q11 the model used **10
> of the 10** rubric-critical items in its context, invented none, and the
> "background knowledge" it was accused of substituting was itself retrieved.
> The block carried only 10 of 17 rubric items. **The bottleneck is still
> retrieval, not the model's use of context**, and Study 008 should target the
> diversity floor rather than prompting. The corrected sections are marked below.
**Pre-registration:** `experiments/study_007/pre_registration.md` (locked at `d920fd8`)
**Amendments:** 001 (delivered information), 002 (floor-cost criterion), 003 (rater protocol)
**Treatment:** `runs/study_007_full_001` · **Control:** `controls/count_budget_seeded/run_001`

---

## Summary

Study 007 changed how much and what kind of long-term memory reaches the model,
and nothing else. Formation shipped unmodified from Study 006.

**It worked, and it did not matter.**

The treatment delivered 33,406 characters of long-term memory at the breadth
probe against the control's 13,130, with material from all four domains present
where the control had one. Then it scored 0.0 on that probe — the same score the
control got, and the same score Study 006 got.

| Bar | Criterion | Result |
|---|---|---|
| **3 — Formation** | 4/4 domains, offset-verbatim, zero junk, zero inference calls | **PASS** |
| **1 — Breadth recovery** | Q11 ≥ 0.5 ∧ Q14 ≥ 0.5 ∧ sum ≥ 1.5 | **FAIL** (0.0, 0.5) |
| **2 — Targeted recall** | Q1–Q13 ≥ control, Cat 1–3 not below | **PASS** (12.0 vs 10.5) |

Bar 1 failed **with four-domain coverage confirmed in the probe-turn log**. That
is a pre-registered outcome with a pre-registered meaning:

> **This is a genuinely new finding** — the bottleneck is neither formation nor
> retrieval but the model's use of provided context. Next study targets context
> presentation/prompting, not memory.

The memory architecture is no longer the limiting factor for breadth recall.

---

## What changed, and what the arms actually differed by

**Changed — LTM retrieval only:**

| Element | Study 006 / control | Study 007 treatment |
|---|---|---|
| LTM budget unit | count of records (top-M = 5) | **32,000 characters** |
| Coverage across domains | incidental | **floor of 1 per topic, then similarity fill** |
| Arbitration | tier-neutral count-ranking | **tier-budgeted, floor selections protected** |
| Span/episode redundancy | identifier dedup only | **containment dedup added** |

**Carried unchanged and verified:** the whole formation stage, STM retrieval
(N + K), topic assignment, tagged context blocks, runtime, seed, response budget.
The STM path and the formation files show a zero diff against `origin/main`.

**Cross-arm equality:** turns 1–31 are byte-identical between arms. The first
divergence is turn 32 — the first turn after the dream pass at 31 gives the
treatment a non-empty LTM to budget over. The arms differ where and only where
the retrieval policy differs.

---

## Results

### Bar 3 — Formation non-regression: PASS

| Measure | Treatment | Control |
|---|---:|---:|
| Domains formed | **4/4** | 4/4 |
| Content records | 200 | 200 |
| Non-content records | 0 | 0 |
| Unfaithful at recorded offsets | 0 | 0 |
| Inference calls in dreaming | 0 | 0 |

The control reproduces Study 006's treatment to the character (29,214). The
treatment's store differs by 716 characters, which is expected rather than a
regression: the arms diverge from turn 32, so the dream engine reads a different
conversation. The policy is identical and its output properties are identical.

### Bar 2 — Targeted recall non-regression: PASS

| | Treatment | Control |
|---|---:|---:|
| **Q1–Q13** | **12.0** | 10.5 |
| Cat 1 (Q1–Q3, early plants) | 3.0 | 3.0 |
| Cat 2 (Q4–Q6, middle plants) | **3.0** | 2.0 |
| Cat 3 (Q7–Q8, late plants) | **2.0** | 1.5 |

The diversity floor did not cost targeted recall. It gained 1.5 points, driven by
Q5 (pigment technique: 1.0 vs 0.0) and Q8 (photophore location: 1.0 vs 0.5).

**Q5 deserves attention.** `art_pigment` is one of the six plants the
pre-registration recorded as *unformed* — no span carrying it was ever selected,
and the pre-registration therefore predicted Q5 could not reach full credit. It
reached full credit anyway. The reason is Amendment 001's finding: the read path
renders a distilled record's **whole source episode**, not its selected span, so
turn 56's episode reached the model through a record selected for a different
sentence. A larger budget admits more episodes, and each episode carries facts
that were never themselves selected.

That is a real effect and it is worth naming precisely: **the information budget
partially compensates for formation gaps**, because the delivered unit is larger
than the selected unit. It is also the clearest argument that the read path's
span-versus-episode divergence should be resolved deliberately rather than left
as an accident.

### Bar 1 — Breadth recovery: FAIL

| | Q11 (turn 120) | Q14 (turn 121) | Sum |
|---|---:|---:|---:|
| Treatment | 0.0 | 0.5 | **0.5** |
| Control | 0.0 | 0.0 | 0.0 |

Required: both ≥ 0.5 and sum ≥ 1.5. The treatment improved on the control at Q14
and matched it at Q11, and fell well short of the bar.

**The attribution requirement is satisfied in the direction that matters.** The
pre-registration requires that a *pass* be backed by four-domain coverage in the
log. The failure is backed by it too:

| Turn | Treatment block | Control block |
|---|---|---|
| 120 (Q11) | 33,406 chars, 7 episodes, **all four domains** | 13,130 chars, 4 episodes, civil only |
| 121 (Q14) | 34,051 chars, 8 episodes, **all four domains** | 16,027 chars, 4 episodes, three domains |

---

## The finding — **SUPERSEDED, see `evaluation/position_and_grounding_analysis.md`**

> The claim in this section did not survive item-level checking. It is preserved
> as written, struck through in substance, because the correction is part of the
> record. The corrected finding follows immediately after.

~~The treatment's Q11 answer named all four subject areas and populated them. For
civil engineering and marine biology it used the planted facts. For the other two
it used **the model's own background knowledge** — none of which occurred in this
conversation... The store contains the facts. The retrieval delivers the facts.
The model does not use them.~~

**Why it was wrong.** The claim rested on a coverage check that counted a domain
as present if *any* planted term appeared in the block. Under that definition art
was "covered" by `Julius II` alone and monetary by `Federal Reserve` alone. Under
the definition the rubric actually scores — the domain's rubric-critical facts
are present — the Q11 block covered **two** domains, not four.

## The corrected finding

At Q11 the model used **10 of the 10** rubric-critical items in its context,
added none that were absent, and contradicted nothing:

| Turn 120 (Q11) | Count |
|---|---:|
| Rubric items in the LTM block | 10 / 17 |
| Rubric items in the answer | 10 / 17 |
| In block but unused | **0** |
| In answer but not in block | **0** |

`1483`, `Annunciation`, `Melozzo`, `della Rovere`, `Taylor Rule`, `Priya Mehta`
and `2.3%` were **absent from the context window**. The model could not have
named them.

The "background knowledge" it was accused of substituting — Cosimo de' Medici,
Ghirlandaio, the ECB, the Bank of Japan, FAIT — is **all present in the turn-120
block**. It is real conversation content, just not rubric-critical content. The
model fabricated nothing.

**Cause.** `k_min = 1` gives each topic exactly one episode, chosen by similarity
to the query. For a "list everything" query that winner is a topic *overview*:
art got turn 31 (patronage survey) while its facts live in turns 55/56/60;
monetary got turn 69 while its facts live in 61/62/65. All three fill slots then
went to civil, because fill is uncapped global similarity and civil had the most
episodes. The floor guaranteed **topic presence, not fact presence**.

- **Study 006** could not have answered Q11 — two domains reached the model.
- **Study 007** also could not have answered Q11 — four *topics* reached the
  model but only two topics' *facts*.

The bottleneck has not left the memory architecture. It moved from formation to
retrieval, and it is still in retrieval.

**Bar 1's attribution branch was mis-triggered.** The pre-registered failure
table routes "Bar 1 fails *with* four-domain coverage" to a context-use finding
and "Bar 1 fails *without* it" to "budget or floor insufficient — compare live
retrieval to the replay prediction." The second row is correct. There was no
divergence from the replay because **the replay gate used the same permissive
coverage criterion**: it too passes on `Julius II`. That is a fifth instance of
this study's recurring failure class — a criterion checking that a unit is
present while what matters is what the unit contains.

**Why the earlier diagnosis was wrong, and how that was caught.** The
pre-registration attributed Study 006's failure to a collapse in delivered
information — ≈ 584 characters versus the control's ≈ 20,700, a ~35× gap.
Measurement before implementation refuted it (Amendment 001): the real figures
were 13,130 versus 21,805, a factor of 1.66. The read path renders whole source
episodes, so the 146-character mean span size never described what was delivered.
Had that gone uncorrected, the study would have locked `B_ltm = 4,000` — *cutting*
delivery threefold — and produced a confident, wrong conclusion.

---

## What the offline gates bought

Both gates ran before any run was spent, and both changed the study.

**The replay gate** first reported that **no parameter pair satisfied both gates**
— the pre-registered "do not run" condition. The diagnosis was not the policy.
The targeted fixture's criterion 3 bounded the floor's cost in **slots**, which
assumes uniform record size; rendered episodes span 500–6,238 characters. The
floor spent exactly its permitted 3 other-domain slots, but those averaged 4,048
characters against marine's 3,673, so they displaced 3.31 marine slots — and 3.31
costs a fourth. Amendment 002 re-derived the criterion in characters plus one
record of bin-packing slack.

That was the **fourth** instance of one failure class in this study — a budget
expressed as a count of items whose size varies. The others: `B_ltm` itself
(Amendment 001); the `LTM_TOP_M` truncation in `_score_ltm_rows`, which would have
made the floor inoperative while appearing to work; and Study 004's arbitration
cap. All four were found before the run, three of them by the stage-interface
check that Correction 4 introduced for exactly this purpose.

**A prediction recorded before the run, and confirmed.** Amendment 002 §6 stated
that at the locked parameters the floor is *not* what produces four-domain
coverage — `k_min = 0` also reaches 4/4 at `B_ltm = 32,000`, and the floor is
causally load-bearing only at 24,000–28,000 with `k_min = 2`, where the targeted
fixture fails badly. So a Bar 1 pass was to be credited to the budget, not the
floor. Bar 1 did not pass, and the coverage the log shows is attributable to the
budget. The floor's contribution is visible in Bar 2 instead, where it costs
nothing and the budget gains 1.5 points.

**Where the replay was right and wrong.** It predicted four-domain coverage at
both probes; the live run delivered exactly that. It could not predict the
scores, and the gap between "coverage achieved" and "breadth recalled" is the
study's finding.

---

## Limitations

- **The rater was an agent, not a human** (Amendment 003). Correction 2's other
  two components were met in full and were not met at all in Study 006: scoring
  preceded every mechanism log, verifiable from git order, and arm identity was
  masked with the assignment derived from a hash of the response files.
  Blinding protects against directional bias, not inference — an agent that knows
  the study can often infer arm identity from a four-domain answer. **Re-scoring
  the committed responses with a human rater is the single cheapest improvement
  available to this study's evidence, and needs no new run.**
- **Bar 2's margin does not turn on a judgment call**, unlike Study 006's Bar 3.
  The one judgment call recorded (control Q7, which does not restate the
  researcher the question names) moves the control from 10.5 to 10.0 and changes
  no verdict. Dual scoring under Correction 3 changed nothing: no answer in
  either arm has credit depending on a hedged formulation.
- **`B_ltm` and `k_min` were calibrated on the replay data**, so the replay cannot
  independently validate them. The targeted fixture was authored before the sweep
  and constrains rather than fits them; the live run is out-of-sample.
- **The read path renders episodes, not spans.** This study optimizes a budget
  over an element whose rendered form is a whole source episode, so its
  conclusions about budget sizing do not transfer unchanged to a span-rendering
  read path. Rejected as a concurrent change (Amendment 001 §6); it is the
  leading candidate for a separate study.
- **Four domains is a small, balanced case.** A per-topic floor scales linearly
  with topic count; with many topics the floor would consume the budget. Only 10
  of 90 LTM turns even had all four topics present.
- **Six plants remain unformed**, bounding Q1–Q13 below 13.0 regardless of
  retrieval — though Q5 shows the budget partially compensating for this.
- **Source weighting remains script-correlated** (carried verbatim from Study
  006): the planted facts are user-authored, so the weight aligns with the answer
  key. Unresolved and out of scope here.
- Single scripted run per arm, one seed, one rater.

---

## Next study — **CORRECTED**

The original proposal here was a prompting study. **That is the wrong target.**
Prompting a model that already used 10 of 10 available items cannot supply the 7
items that were absent from its context.

Ranked by what the evidence supports:

1. **Make the diversity floor fact-aware, or raise it.** `k_min = 1` is the
   direct cause: one episode per topic, chosen by similarity to a query that
   favours summaries over specifics. Either raise `k_min` — the sweep showed
   `k_min = 2` at `B_ltm` 24k–28k makes the floor causal, at a targeted-recall
   cost that must be re-measured — or select the floor episode by expected
   information content rather than by query similarity alone.
2. **Cap fill per topic, or reserve a fill quota.** Three of three fill slots
   went to civil at Q11. The no-cap rule was a deliberate pre-registered choice;
   this is the first evidence it costs breadth.
3. **Strengthen both gate criteria** to require a domain's rubric-critical facts
   rather than any planted term. The replay gate currently passes on `Julius II`.
4. **Ordering is worth one cheap test, but is not the lead hypothesis.** See the
   position analysis: a clean null at Q11, a confounded signal at Q14.
5. **Resolve the span-versus-episode rendering divergence** as its own study. It
   currently helps (Q5) by accident.

Do not revisit formation. The 1,000-turn endurance study remains deferred.

---

## Verification

- **629 tests pass**; 71 new against Study 006's 558 baseline, across character
  budgeting, floor/fill selection, containment dedup and refill, arbitration
  assembly and floor protection, budget logging, bar evaluation, and the
  encoding correction.
- **Correction 1 is real, not declared**: reading the script under `-X utf8=0`
  without an explicit encoding digests to `5eb93a82…`, which the new assertion
  rejects against the recorded `d8ba73fd…`. Correctness no longer depends on
  `PYTHONUTF8`.
- **Determinism**: a 10-turn seeded prefix is identical across two fresh server
  lifecycles **and** 10/10 identical to Study 006's recorded hashes, establishing
  that nothing upstream of LTM retrieval changed.
- **Read-only replay**: 270 Study 006 artifacts SHA-256 hashed before and after
  the calibration sweep, byte-identical.
- **Control integrity**: 12 launch guards, zero diff against Study 006's accepted
  `a2fb66a`, module paths resolving inside the control worktree, and the run
  reproducing Study 006's probe blocks to the character.
- **Budget never exceeded** on any of 121 turns; mean utilization 96.9%.
