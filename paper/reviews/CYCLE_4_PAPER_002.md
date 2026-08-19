# PAPER-002 — Adversarial Review, Cycle 4 (verification pass)

Target venue: arXiv cs.CL preprint. This is a **re-review**, not a fresh pass.
Cycle 3 raised thirty objections against `paper/PAPER_002.md`; all thirty were
accepted and the author reports all thirty applied, across commits `f851c5f4`,
`88ef093a` and `d1d118bc`. Cycle 3's closing note required this pass:
*"Structural changes required, so a Cycle 4 pass over the rewritten summary and
conclusion is warranted."*

Bounds are `paper/notes/EVIDENCE_SPINE.md` (standing per number) and
`paper/notes/DO_NOT_WRITE.md` (withdrawn claims). House format follows
`paper/reviews/CYCLE_1.md`.

Scope: the sections that were structurally rewritten — executive summary,
abstract and §1 opening, §2.1, §4.1, §5.1, §6 opening and §6.3, §8.1, §12.1,
§12.3, §13. Overclaim and underclaim weighted equally.

**Status: complete.** Fourteen of thirty Cycle 3 objections fully discharged, twelve
partial, two not fixed, none regressed. Nine new items. Twenty-one dispositions, all
sentence-level.

---

## Part 1 — Verification of the thirty Cycle 3 objections

Verdicts: **FIXED** (the claim actually weakened or the omission actually
filled), **PARTIAL** (moved but not discharged), **NOT FIXED**, **REGRESSED**
(the edit made it worse or broke something adjacent).

### Executive summary

**1 — "It" beats a control. → FIXED.**

> "ranking adjacent-turn pairs by their own cosine rather than inheriting their
> session's score raises complete evidence delivery from **843 to 935 of 1,098**…
> **One parameter varied.**"

The architecture sentence no longer carries the holdout, the contrast is named on
both sides, and "a margin that is not close" is gone in favour of 2.92 against the
registered 2.0. "One parameter varied" is the sentence the objection asked for.

---

**2 — "Eleven pre-registered experiments". → NOT FIXED.**

The abstract was corrected. Nothing else was.

> line 3, subtitle: "and the **eleven** experiments that cut it down to size"
> line 144, §1: "built and measured over **eleven pre-registered** efforts — ten
> numbered studies plus one registered exploratory bakeoff, **counted that way
> throughout**"
> line 1290, §13: "**Eleven pre-registered efforts** produced one architecture worth
> keeping"

Three of the four sites `DO_NOT_WRITE.md` §1 #8 governs still carry the retired
value, and the subtitle is the first line a reader sees. §1's sentence is now
self-refuting: it asserts eleven pre-registered efforts, concedes in the same breath
that one of them was exploratory, and then claims the honest count is used
"throughout" while the line above it and the conclusion below it both say eleven.
The audit's own instruction — grep the superseded *value* — was not run; `grep -n -i
eleven` finds all three in one command.

This is the cheapest unfixed objection in the set and the most visible.

---

**3 — "The one operation measured here to break retrieval". → PARTIAL.**

Fixed where it was quoted. Left standing where it originates.

> Exec summary, now correct: "the deployed shortlist holds no representative of one
> of four domains, so no rule reaches it from there — **a fact about its contents,
> not a comparison**."
> §13, now correct: "That is a fact about the shortlist's contents rather than a
> measured comparison."
> §7.2, line 808, unchanged: "**It is the one operation this programme measured to
> break retrieval.**"

§7.2 now contains the correction and the defect four sentences apart — "That is not
a measured comparison; it is a fact about the shortlist's contents", and then the
condemned sentence as the subsection's closing line. The uniqueness quantifier is
also still unmeasured: no census of operations was run, so "the one operation" is a
claim about every other operation as well.

---

**4 — LV-001's −2.0 asserted as a real drop. → FIXED in the executive summary.**

> "The configuration making six more facts available **failed its registered
> no-regression bar, registered as a kill**; status **not promoted**. The shortfall's
> size sits inside the band and is not demonstrated either way — **the bar firing does
> not depend on it.**"

This is §8.3's voice, which is what objection 17 asked for. The disposition is
sourced to the decision procedure and the score is explicitly detached from it. See
objection 29 for §13, where the old form survives.

---

**5 — "Below about three points" licenses the inverse inference. → FIXED in the
executive summary.**

> "**Three of four scored comparisons fall inside it and are not demonstrated; the
> fourth merely exceeds it, which is not the same thing.** … It is a switch, not a
> spread."

Denominator supplied, the spine's fourth row carried, switch-versus-spread
distinction present. The threshold phrasing survives at §1.3 — new objection **N8**.

---

**6 — 12 → 14 "with zero targeted losses". → FIXED in the executive summary and §6.4.**

> Exec: "takes an enumeration probe 12 to 14 of 17, **trading art coverage 2 of 4 down
> to 1 of 4** while restoring all four monetary items."
> §6.4: "The winning trace selects **no statement whose source turn is 90**… And art
> falls from 2 of 4 to 1 of 4. This is a breadth composition trade, not universal
> dominance."

Both mandatory boundaries from spine D2 now travel with the number. The abstract does
not carry either — filed under new objection **N9**.

---

**7 — Three of five confirmatory results are negative (underclaim). → FIXED.**

> "**What five sealed experiments bought.** Five results carry a sealed holdout with
> bars locked before the number existed, and **three are negative**… That is why the
> surviving design has four components rather than a dozen."

The same fact is now stated three times — executive summary, §4.1's assignment table,
§5's opening — and named per mechanism in §13. This was the strongest underclaim in
Cycle 3 and it is fully discharged.

---

**8 — "The systems that ship in this space". → FIXED.**

> "**Mem0, Zep, Letta and Graphiti each spend at least one generative call on this
> layer by their own published descriptions.**"

The universal is gone; four named systems, sourced. Checked against
`COMPETITIVE_LANDSCAPE.md`'s call-site table: Zep/Graphiti and MemGPT/Letta both have
rows describing per-episode or agent-issued generative calls, so "at least one" holds
for all four. One thinness worth recording rather than objecting to: Letta's row
notes that no standalone Letta system paper was located and cites MemGPT, so "their
own published descriptions" reaches Letta through its predecessor.

---

### §2.1 — the comparison boundary

**9 — The table's licence is issued once and spent five times. → PARTIAL.**

The per-row marking was added. The sentence that caused the problem was not removed.

> Still, immediately above the table: "What is comparable is architectural, and **the
> axes are countable from either system's own description**"
> Now, immediately below it: "**Only the first row is arithmetic on published
> descriptions.** … The remaining rows are not of that kind and **should not inherit
> its licence**."

The paper prints a claim and its refutation on either side of the same table. The
second paragraph is exactly right — rows two and three marked as measured here with
the competitor column stated in principle, row four marked as an admitted rather than
observed failure mode, row five marked a definition. All of that work is undone for a
skimming reader by the framing sentence, which still says all five axes are countable
from published descriptions. Delete the clause; the paragraph below replaces it.

---

**10 — The forbidden juxtaposition is printed. → FIXED.**

> "The sentence to refuse has the shape *\"on LoCoMo, system X reports [their
> accuracy] and this component reaches [our delivery count]\"* — both halves true, the
> juxtaposition meaningless, and **it is not written out here with real numerals
> precisely because it would then be quotable**."

Zero numerals, shape preserved, reason stated. `grep -n 66.88` over the paper returns
nothing.

---

**11 — "Every system above consumes a candidate set produced upstream by similarity
ranking". → PARTIAL.**

> "**Most systems above** consume a candidate set produced upstream by similarity
> ranking, and this paper measures that set. The claim is not universal even across
> the short list: **HippoRAG retrieves by graph traversal**, as §2 says two paragraphs
> earlier, so the measurement here bears on it only where a similarity-ranked
> candidate set feeds the traversal."

The universal quantifier is gone and the counterexample the objection named is handled
explicitly and well. What remains is that "most" is still a frequency claim over unrun
architectures, and the required form asked for the systems to be *named*. The paper
has the material — `COMPETITIVE_LANDSCAPE.md` carries a per-system retrieval column —
so naming them here costs one clause. Downgraded from overclaim to imprecision, but
not discharged.

---

**12 — "Rarely" versus "not"; "recovers most of it". → FIXED.**

> §2.1: "**the question this paper answers is not whether the deterministic version
> wins.** It is how much of the layer survives without the call."
> Exec: "**The question here is not whether the deterministic version wins** — none
> was run — but how much of the layer survives without the call."

One strength, both places. And the presupposition is gone:

> "A mechanism that **recovers a usable share of it** and still loses a head-to-head
> **would be** a finding, and this paper is not in a position to report that
> comparison in either direction."

The clause is now counterfactual, so it no longer does the work of a result. "A usable
share" is vague, but it sits inside a hypothetical and quantifying it would require
the measurement the sentence declines to claim. Correct as written.

---

### §4.1 — the standing taxonomy

**13 — The taxonomy is defined in the paper and applied outside it. → FIXED.**

> "**The assignment, in full, so this table is checkable without leaving the paper.**"

Seventeen rows, each naming the result, its standing, its section and its binding
limit. This was Cycle 3's most serious objection and the fix is the right one: an
arXiv reader now gets the assignment, not only the vocabulary. Two defects in the
execution are new and are filed as **N1** and **N2** rather than against this
objection.

---

**14 — No level between CONFIRMATORY and DETERMINISTIC-OFFLINE. → FIXED.**

> "**Five levels, separated by when the claim was committed relative to the number,
> not by how the number was computed. Determinism is cheap; commitment order is what
> a result cannot buy back afterwards.**"
> "The second and third levels were one level in an earlier draft, and collapsing them
> was a real defect: it let a byte-identical 500-store replay, a posthoc reading of an
> exhausted corpus, and a bound computed with the answer key all inherit the same
> phrase."

The split is REGISTERED-OFFLINE (pre-registered, bars first, corpus already observed)
against DESCRIPTIVE (the reading chosen after the number, or a bound computed with the
key). Re-keying the whole taxonomy from *how computed* to *when committed* is a larger
change than the objection asked for and a better one.

All four REGISTERED-OFFLINE assignments were checked against their source reports:
NF-005 registers at `04d37138`, NF-006 at `ebb3ebf3`, and EC-002 and IC-001 each carry
a named pre-registration file in their report headers. The registration half of the
assignment holds in every case.

---

**15 — EC-001/EC-002 do not meet "byte-identical on replay". → PARTIAL.**

§8.1 was fixed:

> "One qualifier travels with this: the deployed arm is a **reproduction under
> recomputed embeddings, not a byte-exact replay** — the original run's embedding cache
> was not retained, and that run is **permanently unreplayable at bit granularity**."

§8.3 was not, and it is fourteen lines further down the same section:

> "The suppression is confirmed — it is an offline count, **byte-identically
> replayable**, and §12.1's noise band does not touch it."

The objection quoted this sentence and required its replacement. The section now
asserts and denies the same property about the same result within one screen. Cycle 3
supplied the escape — say that the counterfactual half replays byte-identically while
the baseline half does not — and it was not taken.

The rewrite also created a second instance of the same contradiction one level up. See
**N1**.

---

### §4.2 — the integrity machinery

**16 — Machinery stated as uniformly achieved; wrong cross-reference; raters not
identified. → NOT FIXED.**

`git diff 95000acd HEAD -- paper/PAPER_002.md` does not touch §4.2. All three
sentences the objection quoted are byte-identical to the reviewed draft:

> "Registration commits contain no implementation files, **which is checkable and was
> checked**."
> "A gate is trusted to stop only after showing that its tested population and its
> non-stopping alternative were capable of existing… **§5.4 and §11.5 each report
> one.**"
> "**Sealed scoring.** Three blind passes with registered adjudication triggers."

The first is still stated of every study when the spine names two — DMR-004 and
DMR-001C. The cross-reference still points at §5.4 and §11.5 while §11.6 is the
section that inventories the failures, and §11.6 now carries a *fifth* case found on
the sealed holdout itself, which makes the omission worse than when Cycle 3 raised it.
The rater sentence still does not say the raters are not human, in a paper whose §5.2
and §12.8 both say so.

This objection was accepted and then not implemented. It is the only one in the set
with no partial credit anywhere.

---

### §5.1 — the sealed holdout

**17 (credit) — §8.3's handling of an in-band result. → HONOURED.**

§8.3's paragraph is intact, and the executive summary's availability-versus-correctness
bullet is now written in its voice (objection 4). The credit converted into the fix it
was entered to motivate.

---

**18 — "Universal-rule" dropped from a binding scope cap. → FIXED.**

> "the registration authorizes **no reader, live, universal-rule, promotion or adoption
> claim**. The `universal-rule` term is the one that governs §6 and §13: this confirms
> **one substitution on one corpus, not a law about granularity**. §12.3 is where the
> accuracy distinction has teeth, and **§6.3 is where the universality one does**."

Restored verbatim from the registration, with the consequence Cycle 3 asked for and a
forward pointer to the reversal. Better than the required form.

---

**19 — `p = 6.19e-12` assumes independence across six clusters. → FIXED.**

> "**That p assumes the questions are independent, and they are not** — they cluster
> within six conversations. The registered statistic is not re-scored, but a
> conservative alternative is reported beside it: treating each conversation as a
> single observation, all six are net positive, one-sided sign test **p = 0.0156**.
> Six observations is what the sealed design actually bought, and it still clears 0.05."

Both statistics, the registered one unmoved, and the honest sentence about what six
sealed conversations buy. `EVIDENCE_SPINE.md` §7.15 was added to trace it. This is the
cleanest fix in the set.

---

### §6 — granularity and its reversal

**20 — The relation is non-monotone; the rule is monotone. → PARTIAL.**

The shape is now stated, and stated first:

> "**State the shape before stating any rule, because the shape is not monotone.** On
> one corpus, at a fixed packing unit, the episode loses in both directions: the turn
> beats it 461 to 361, and the session beats it 388 to 351. A candidate unit that is
> worse than both its parent and its child cannot be produced by any rule of the form
> *finer is better* or *coarser is better*. **Whatever governs this is not a monotone
> function of granularity, and this programme has not identified it.**"

That is the objection's main ask, discharged, and declining to adopt the alignment
reading rather than asserting it as interpretation is the right call.

What was not fixed is the self-contradicting reconciliation, which survives verbatim
in the paragraph immediately above:

> "an episode is **already small enough that its embedding stays informative**, and
> dropping to it **discards the broader context that was doing the scoring work**. A
> source turn is small enough that its embedding is *sharp*."

Cycle 3's point was that these two clauses cannot both be true. The added third
sentence makes the incoherence sharper rather than resolving it: if the episode's
embedding stays informative and the turn's is sharper still, the paragraph has just
explained why the turn should win — which it does, 461 to 361, two subsections
earlier. The paper then says, correctly, that it has not identified the mechanism.
Delete the reconciliation and the section is right; keep it and §6.3 offers an
explanation it disowns four lines later.

---

**21 — Same measure, two names. → PARTIAL.**

The "strict" collision is gone — §6.3's header no longer carries the word that
`DO_NOT_WRITE.md` §1 #3 makes load-bearing. But the two tables still name one measure
two ways:

> §6.2 header: "**Any exact evidence**" — Episode / Episode = **351 / 465**
> §6.3 header: "**Exact answer-episode delivery**" — Episode / Episode = **351 / 465**

Same arm, same corpus, same count, two labels one subsection apart. And the required
single sentence — that the endpoint throughout §6 is answer-episode delivery and never
session touch — was not added. A reader who has reached §11.5 knows the surrogate
exists and has no statement that §6 does not use it.

---

**22 — "Informative" has no operational definition. → FIXED.**

> "**rank at a unit small enough that its embedding is dominated by the material
> answering the query**… The first clause needs an operational test to be a rule
> rather than a restatement, and **it does not have one here** — 'dominated by' is
> measured after the fact by whether delivery improved. Two proxies are available and
> **neither was registered**… Both are descriptions of these corpora, not thresholds
> anyone should carry."
> "This is a **posthoc characterization on an exhausted corpus, not a registered
> universal law**."

Operational handle offered, marked untested, and the word "rule" demoted in the same
subsection. `EVIDENCE_SPINE.md` §7.16 was added to trace the 240–300 band. Residual,
not an objection: §6's own heading and §1.2's contribution 1 both still read "the
finest informative unit", which is the phrase the subsection retires.

---

**23 — "Reproduces on two more corpora". → PARTIAL.**

Removed from the executive summary and replaced by the reversal, exactly as required:

> "**Finer is not monotonically better, and our own data refutes it.**… The episode
> loses to both its parent and its child — a shape no monotone rule generates."

The condemned verb then reappears twice further in:

> §1.2, contribution 1: "confirmed prospectively on six withheld LoCoMo conversations
> and **reproduced on two further corpora** with the size mechanism measured rather
> than asserted."
> §13: "**reproduced at** 361 to 461 of 465 on a second corpus and 12 to 14 of 17
> internally."

§13's is survivable because the reversal paragraph follows immediately. §1.2's is not:
it is a contributions list, it says "reproduced on two further corpora" with no
qualifier, and one of those two corpora is where the direction reverses. The
executive-summary fix was a move, not a repair.

---

### §12.1 — the instrument band

**24 — The divergent replicate was the first run (underclaim + accuracy). → PARTIAL.**

§12.1 and the abstract were both corrected, and the finding was promoted the way the
objection asked:

> §12.1: "scored **11.0, 8.0, 8.0, 8.0 and 8.0**, in that order… **The one that
> diverges is replicate one — the first run in a fresh server process**… Stated that
> way it is sharper than 'one of five was odd', and it reaches further: **every scored
> run in this arc that began on a cold server sits on the divergent side of that
> switch**, and no study in the arc pinned process state."

Figure 5's caption was not corrected and still carries the old ordering:

> "five replicates… that scored **8.0, 8.0, 8.0, 8.0 and 11.0**"

The paper now states the sequence two ways, and the figure caption is the version that
hides the finding. §12.1's own text says the run order *is* the finding, so this is not
a cosmetic mismatch.

---

**25 — "Three of N" with no N; the spine's fourth row missing. → PARTIAL.**

The denominator arrived:

> "**three of this arc's four scored verdicts fall inside the band and are not
> demonstrated**: the memory-tier contrast at 3.0, the live-validation targeted
> regression at −2.0, and the tier-isolation result at −1.0."

The fourth row did not. §12.1 names three of four and never says what the fourth is or
what it means. The annotation the objection asked to be carried verbatim exists in the
paper twice — in the executive summary ("the fourth merely exceeds it, which is not the
same thing") and in Figure 5's caption ("The corrected treatment series at +3.5 sits
outside it, and exceeding a band is not the same as being demonstrated") — but not in
the section that Cycle 3 identified as the defect's source, and not anywhere that
names the 8.5 → 12.0 series. A reader of §12.1 alone still completes the inference the
spine added that row to block.

---

### §12.3 — availability is not correctness

**26 — "The weakness is real" retracted in the same section. → PARTIAL.**

The promotion happened and it is well done:

> "**The finding that survives the band is not the score.** Both arms fabricated
> confidently on the domain neither retrieved… which a presence-only scorer credits as
> a hit. **That is an identity, not a rating, so §12.1 does not touch it**, and it is
> the more durable result of the two."

That paragraph gives the section a band-independent basis it did not have, which is
more than the objection asked for. But the sentence Cycle 3 condemned is untouched:

> "This was the largest structural weakness of this paper's predecessor. **It has now
> been measured, and the weakness is real.**"

and the section still closes with "The −2.0 magnitude is as unreplicated as the +1 and
neither is demonstrated". The ordering decides what a reader attaches "measured" to:
the bolded claim is immediately followed by the bar table carrying the −2.0, and the
fabrication finding is four paragraphs later. Move the fabrication sentence up, or
rewrite the opening to name it, and the objection closes.

---

### §13 — conclusion

**27 — The rule handed to practitioners without §6.3. → PARTIAL, and mostly fixed.**

§6.3 is now in the conclusion as its own paragraph, which was the objection's core:

> "*And do not read that as 'finer is always better', because this paper's own data
> refutes it.* On the same LongMemEval corpus, moving the ranking unit from the session
> to the episode **loses 37 items**… The episode loses from both sides, which no
> monotone rule can produce. **The confirmed result is the specific substitution above,
> on units of roughly 240 to 300 characters.**"

The second half of the objection was not addressed. The sentence before it still runs
three results of two standings under one confirmation:

> "This is the substitution with **sealed external confirmation** — 843 to 935 of 1,098
> on withheld conversations, **reproduced at 361 to 461 of 465 on a second corpus and
> 12 to 14 of 17 internally**."

843 → 935 is CONFIRMATORY. 361 → 461 and 12 → 14 are REGISTERED-OFFLINE by the paper's
own §4.1 table, capped as characterization on already-observed corpora. Joining them
inside one sentence governed by "sealed external confirmation" is the exact erasure §4
exists to prevent, in the paragraph most likely to be quoted. §4.1's new table makes
this cheap to fix: it is one clause.

---

**28 — "Invented none / the failures were delivery failures" versus §12.3. → PARTIAL.**

The first half is fixed, and well:

> "at the one probe where it was measured item by item, the model used all ten
> available facts and invented none. **That is a statement about one probe and it does
> not generalize: §12.3 records the counterexample**, where both live arms fabricated
> confidently on the domain neither of them retrieved."

The second half survives as the paper's final substantive claim, one sentence later:

> "**So the failures measured here were delivery failures**, and delivery turned out to
> be a selection problem…"

The paper concedes a measured failure that was not a delivery failure and then, in the
next sentence, says the failures measured here were delivery failures. Cycle 3 supplied
the form that survives its own counterexample: *delivery was the dominant failure mode
this programme measured, and it was not the only one.* One word — "dominant" — closes
this.

---

**29 — Four flagged framings recur in §13. → PARTIAL, item by item.**

- "**Eleven pre-registered efforts**" — **NOT FIXED.** Still the conclusion's first
  three words. See objection 2.
- "**The one operation measured here to break retrieval**" — **FIXED in §13**, which
  now reads "a fact about the shortlist's contents rather than a measured comparison".
  Survives at §7.2. See objection 3.
- "**The systems that ship in this space**" — **FIXED.** Four systems named, sourced to
  published descriptions.
- "**Availability and correctness were measured moving in opposite directions once**" —
  **NOT FIXED, and worsened.** The current text is: "Availability and correctness were
  measured moving in opposite directions once, **and that result stands unrescued**."
  The added clause promotes an in-band gap to a standing result, in the section where
  §12.3's qualifiers are furthest away. The executive summary was rewritten for exactly
  this and §13 was not. One mitigating fact the author should know: the phrase is the
  spine's own — `EVIDENCE_SPINE.md` §5 item 3 reads "**Availability is not correctness.**
  Measured, by LV-001, moving in opposite directions." The bounds file is licensing the
  sentence `DO_NOT_WRITE.md` #28 forbids, so the fix belongs in both files.
- "the answer is **more than this programme expected when it started removing things**"
  — **NOT FIXED.** Unchanged, closing the practitioner section. Still an unfalsifiable
  claim about the authors' priors and still fails the read-aloud test.

---

**30 — The negative confirmatory results unnamed in the conclusion (underclaim). →
FIXED.**

> "**Three of the five sealed results were negative, and they are why the list above is
> short.** A deterministic stopping controller reached Youden's J of **0.320** against a
> registered **0.50**. An absolute-threshold event segmenter closed **52 of 74** events
> on its size cap against a **0.35** bar, and its relative successor then lost to
> chopping every four episodes regardless of content. A surprisal-proximity capture
> signal scored AUC **0.416** against a **0.60** bar, below chance in five of six
> strata. Each was pre-registered against a sealed holdout, and **each closed a line
> this programme wanted to keep.**"

Every number checks against spine C2, C3, C4 and C5. The DMR-001C half is included,
which the objection did not ask for. This is the largest single improvement in the
rewrite.

---

### Part 1 tally

| Verdict | Count | Objections |
|---|---:|---|
| **FIXED** | **14** | 1, 4, 5, 6, 7, 8, 10, 12, 13, 14, 18, 19, 22, 30 |
| **PARTIAL** | **12** | 3, 9, 11, 15, 20, 21, 23, 24, 25, 26, 27, 28 |
| **NOT FIXED** | **2** | 2, 16 |
| **REGRESSED** | **0** | — |
| Credit honoured | 1 | 17 |
| Split verdict | 1 | 29 (2 fixed, 3 not) |

Objection 29 is counted once as PARTIAL above and its five items are also counted
inside objections 2, 3 and 8 where they originate, so the table sums to 29 plus the
credit.

No objection was regressed in the sense of a number moving the wrong way. Every
PARTIAL has the same shape: **the fix was applied at the site Cycle 3 quoted and not
at the other sites carrying the same claim.** That is a single process defect, not
twelve editorial ones — the review was worked as a list of quotations rather than a
list of claims, which is the failure mode `DO_NOT_WRITE.md` opens by naming ("grep for
the superseded value, not for the superseded sentence").

---

## Part 2 — Defects introduced by the rewrite

Nine, numbered N1–N9. Six are consequences of the two structural changes Cycle 3
required — the five-level taxonomy and the compressed executive summary — which is
what a re-review is for.

---

### The taxonomy

**N1. The new REGISTERED-OFFLINE level requires a property its own assignment table
denies for one of the four results it grades. Most serious of the new items.**

> §4.1, the level: "**REGISTERED-OFFLINE** | Pre-registered with bars locked first,
> zero generative calls, **byte-identical on replay** — but run on a corpus already
> observed, so it cannot confirm"
> §4.1, the assignment, eight rows later: "EC-002 — packing priority, 109→261 (§8.1) |
> REGISTERED-OFFLINE | Reproduction under recomputed embeddings, **not** a byte-exact
> replay"

The definition and the assignment contradict each other inside one section. This is
Cycle 3 objection 15 reappearing at a higher altitude: the old level carried the same
"byte-identical on replay" clause, EC-002 was graded into it anyway, and the split
inherited the clause verbatim.

The fix is one word in the definition, not a re-grading. Everything EC-002 needs is
determinism of the *counterfactual* arm plus a named reproduction of the baseline;
"deterministic on replay, with any reproduction boundary named in the limit column"
covers all four rows and matches what §8.1 now says. Leaving it as written hands a
reviewer a checklist item the paper fails against its own checklist.

---

**N2. `EVIDENCE_SPINE.md` still carries the retired four-level taxonomy, and the paper
points at it twice as the authority.**

> §4.1's closing line: "`paper/notes/EVIDENCE_SPINE.md` **carries the same assignment**
> with each number's artifact path and hash."
> Appendix A: "Every number in this paper with its artifact, its SHA prefix where one
> exists, and **its standing under §4.1's taxonomy**."
> `EVIDENCE_SPINE.md` §1, unchanged: "**Four levels.**… | **DETERMINISTIC-OFFLINE** |
> Zero generative model calls; counts and identities rather than scores; byte-identical
> on replay…"
> `EVIDENCE_SPINE.md` §3 heading, unchanged: "## 3. DETERMINISTIC-OFFLINE"

The spine grades fifteen results under a level name the paper no longer has, and the
paper tells a reader the two agree. The spine was updated for objections 19 and 22 —
§7.15 and §7.16 were added — so the file was open and the taxonomy section was not
touched.

This matters more than a stale cross-reference because the spine is a *gate*, not a
reference: `scripts/check_paper_002_claims.py` reads it, `AGENTS.md` §8 requires
claims to trace to it, and its opening sentence is "a number may appear in PAPER-002
only with its standing honoured". A standing that no longer exists cannot be honoured.
Fix the spine, not the paper.

---

**N3. "The assignment, in full" is not in full, and one of its seventeen rows points at
the wrong section.**

> §4.1: "**The assignment, in full, so this table is checkable without leaving the
> paper.**"

Headline numbers carrying no row: the shipped configuration's **12 of 17** and the
deployed baseline's **6 of 17** (§7.1, and Figure 6), the **5 of 17** on the deployed
pool that makes §7.3's ordering argument, EC-001's **109 of 470** and the median
evidence rank of 2 that §7.5 uses to narrow the internal inversion, §6.5's rejected
binding-ratio scope condition, and every number in §9's cost envelope — which does
carry a section-level `Standing: DESCRIPTIVE` but is absent from the table that claims
completeness.

Separately, the NF-007 row reads "coverage floor inert **(§6.4)**". §6.4 is NF-006. In
the whole paper NF-007 appears only as an unnamed bullet in §11.6 — "a cluster-floor
study stopped as inert" — so the table sends a reader to a subsection about a different
study to check a result the paper never states.

Either drop "in full" and say "every result this paper states a standing for", or add
the six missing rows. The second is better: §7.3's 5 of 17 is a one-run DESCRIPTIVE
count doing load-bearing work in the conclusion, and it is exactly the kind of number
the table exists to mark.

---

**N4. §8's section-level standing label covers a subsection the assignment table grades
differently.**

> §8 opening: "**Standing: REGISTERED-OFFLINE.**"
> §4.1 table: "Study 011 tier isolation, −1.0 **(§8.3)** | NOT DEMONSTRATED"

§8.3 is inside §8 and its result is a scored live comparison. §8.3's own prose is
correct and says "not demonstrated in either direction", so the harm is bounded — but
the section header now asserts a standing for material the paper grades two levels
lower. Section-level labels were introduced by this rewrite; §6.1's handles the same
situation correctly ("REGISTERED-OFFLINE for NF-005 and NF-006; DESCRIPTIVE for
NF-003's three-arm reading in §6.3"). Apply §6.1's form to §8.

---

### The compressed executive summary

Checked claim by claim against the pre-compression version at `95000acd`. Two caps did
not survive.

**N5. The cost envelope lost its single-machine qualifier.**

> Before: "**190 ms at 1,000 candidates**, 81% of it in clustering and that share still
> rising. **On this hardware** the design is comfortable to a few thousand episodes and
> unusable in an interactive loop somewhere before ten thousand."
> Now: "**190 ms at 1,000 candidates**, 81% of it clustering and rising — comfortable
> to a few thousand episodes, unusable interactively before ten thousand."

"On this hardware" was three words and it was the whole scope of the claim. Spine D11
is explicit: "One machine. **Only the exponent and the clustering share plausibly
transfer.**" As compressed, the executive summary states an absolute operating envelope
for the design. §9 still carries the qualifier; the page most readers finish does not.
This is the compression risk landing exactly where it was predicted to.

---

**N6. The executive summary asserts the determinism property without the condition it
holds under, and never says an embedding model is resident.**

> "**The claim.** A conversational memory layer needs no generative model calls."
> "`context()` is a pure function of store state, query and budget, **byte-identical
> across two processes**; 132 committed payloads reproduce their SHA-256."

`DO_NOT_WRITE.md` §1 #1 is the first and highest-risk entry in the file, and it has two
halves. The paper honours the first everywhere — "generative" is present in all three
executive-summary sentences that need it. The second half is "**An embedding model must
be resident**… Determinism holds **given a pinned embedder**", and no sentence in the
executive summary carries it. §3.2 carries it properly and at length.

In fairness this predates the rewrite — the pre-Cycle-3 summary had the same gap and
Cycle 3's reader test credited the summary with a property it does not have. It is
raised here because a summary rewritten for honesty and then compressed is the moment
to close it, and because it costs one clause: *an embedding model is resident and the
guarantee is conditional on pinning it.*

---

**N7. The two supporting corpora appear in the executive summary at the headline
result's apparent standing.**

> "**The headline result.**… sealed until the bars were locked… **The result is bounded
> to evidence availability and authorizes no reader, accuracy or universal-rule
> claim.**"
> "**Why the unit is the lever.**… exact delivery goes **361 to 461 of 465**, 100 gains
> and no losses. Internally the same move takes an enumeration probe **12 to 14 of 17**"

The caps attach to the sealed result. The next paragraph gives two more results in the
same voice, with no indication that both corpora were **already observed**, that NF-005
is capped as characterization for that reason, or that NF-006 is one probe. The last
fact does arrive four bullets later — "Internal breadth rests on one enumeration probe"
— which leaves the LongMemEval number as the one with no cap anywhere on the page.

This is objection 13's defect surviving in the one place §4.1's new table cannot reach.
The fix is a clause: *both on corpora already observed, so measured rather than
confirmed.* Six words buy back the distinction the whole of §4 exists to draw.

---

### Residue at other sites

**N8. §1.3 keeps the threshold phrasing the executive summary was corrected for.**

> "**No scored difference below about three points in this arc is claimed as real**;
> §12.1 gives the measurement."

Objection 5's inverse inference — *so differences above three points are real* — is
invited here in the section titled "What this paper does not claim". The executive
summary now blocks it in one sentence ("the fourth merely exceeds it, which is not the
same thing") and that sentence should be reused verbatim.

---

**N9. §1.2's contributions list is now the least-qualified statement of the granularity
result anywhere in the paper.**

> "**A granularity rule with a sealed external confirmation** (§5, §6). Ranking at the
> **finest informative unit**, confirmed prospectively on six withheld LoCoMo
> conversations and **reproduced on two further corpora** with the size mechanism
> measured rather than asserted."

Three retired framings in two sentences: the rule identified with the confirmation
(objection 27), "reproduced on two further corpora" (objection 23), and "the finest
informative unit" after §6.3 has retired the phrase for having no operational test
(objection 22). §6.3 is not referenced. A contributions list is second only to the
abstract for extraction, and this one was not visited.

Also filed here rather than as its own item: the **abstract** states "12 to 14 of 17
with 21 of 21 targeted items preserved" and carries neither of spine D2's two mandatory
boundaries, which is objection 6's condemned construction surviving one section from
where it was fixed.

---

**One style note, not an objection.** The executive summary says "**our own data**
refutes it" where §13 says "this paper's own data refutes it" and the rest of the
document says "this programme". The abstract's "We report" makes first person
admissible; the inconsistency is worth one pass. The Pass-6 banned list greps clean at
zero hits, and `scripts/check_paper_002_claims.py` passes both gates at HEAD, so no
number introduced by the rewrite is untraced.

---

## Part 3 — The reader test, re-answered

*Would a reader who read only the executive summary come away with an accurate
picture?*

**Cycle 3: no, on seven counts. Cycle 4: yes on all seven. Three smaller errors remain,
and the diagnostic Cycle 3 drew from them still holds.**

Cycle 3's seven, in its own order:

| # | What the reader got wrong then | Now |
|---|---|---|
| 1 | A four-component architecture beat a control on a sealed holdout | **Closed.** "One parameter varied", with the contrast named on both sides |
| 2 | The granularity rule is general and reproduces on two more corpora | **Closed.** The reversal has its own bullet and the word "reproduces" is gone from the page |
| 3 | Availability and correctness were measured moving in opposite directions | **Closed.** The bar firing carries the disposition; the shortfall is marked in-band |
| 4 | A scored gap above three points is demonstrated | **Closed.** "the fourth merely exceeds it, which is not the same thing" |
| 5 | Pruning the pool was measured to break retrieval | **Closed.** "a fact about its contents, not a comparison" |
| 6 | The internal 12 → 14 was free | **Closed.** The art trade is in the same sentence as the gain |
| 7 | Three of five sealed results are negative — not learned | **Closed.** Its own bullet, and named per mechanism in §13 |

Seven for seven, and none of them cost a number. Cycle 3's claim that the summary
needed the body's claims rather than weaker ones was correct.

What the reader now gets wrong, three items:

1. **They believe the determinism is unconditional and that no model of any kind is
   resident.** The page says "needs no generative model calls" and "byte-identical
   across two processes" and never says an embedding model must be resident or that the
   guarantee is conditional on pinning it (N6).
2. **They believe the latency envelope is a property of the design.** "Comfortable to a
   few thousand episodes, unusable interactively before ten thousand" is a
   one-machine measurement whose qualifier was cut in compression (N5).
3. **They believe the LongMemEval and internal results stand where the sealed one
   stands.** Both are on corpora already observed and the page does not say so (N7).

And one item that is not in the summary but is on the same page: the **subtitle** still
reads "the eleven experiments", so the first line a reader sees carries the count
`DO_NOT_WRITE.md` retired (objection 2).

**The diagnostic.** Cycle 3's sharpest observation was not that the summary was wrong
but that its errors were *directional* — six overstatements and one omission, none
running the other way, which is not what honest imprecision looks like. Re-run on the
current text: of the three remaining errors, all three make the component look stronger
or more general than measured. None runs the other way. The magnitude collapsed —
these are three clauses against seven substantive misreadings — but the sign did not.

That is worth saying plainly rather than filing as a compliment. The residue is small
enough that it is no longer evidence of a framing problem; it is evidence that
compression removes qualifiers and nobody re-read the compressed page against the
bounds files. The remedy is mechanical: take the executive summary alone, and for each
number in it, find its row in §4.1's new assignment table and check that the cap in
that row appears on the page. Three of the nine numbers fail that check today.

---

## Dispositions — Cycle 4

Twenty-one items. Fourteen are Cycle 3 objections not fully discharged; nine are new.
None requires retracting a number, changing a figure's data, or re-running anything.
Severity is **HIGH** where a claim in the paper currently exceeds its evidence or
contradicts another claim in the paper, **MEDIUM** where a required qualifier is absent
from a high-traffic location, **LOW** for precision and cross-references.

| # | Site | Item | Severity | Required |
|---|---|---|---|---|
| 2 | Subtitle, §1, §13 | "Eleven pre-registered" survives at three of four sites | **HIGH** | Re-grep the value. "Ten numbered studies and one registered exploratory bakeoff" or drop the count |
| 16 | §4.2 | Integrity machinery stated as uniformly achieved; §11.6 not cross-referenced; raters not identified | **HIGH** | Name the two file-checked registrations; point at §11.6; append "— none human, see §12.8" |
| 29d | §13 | "moving in opposite directions once, and that result stands unrescued" | **HIGH** | Rewrite in §12.3's voice. Correct `EVIDENCE_SPINE.md` §5 item 3, which licenses it |
| N1 | §4.1 | REGISTERED-OFFLINE requires byte-identical replay; EC-002's own row denies it | **HIGH** | "Deterministic on replay, with any reproduction boundary named in the limit column" |
| N2 | Spine, §4.1, App. A | Spine still carries the retired four-level taxonomy the paper points at | **HIGH** | Update `EVIDENCE_SPINE.md` §1 and §3 to the five levels. It is a gate, not a reference |
| 15 | §8.3 | "byte-identically replayable" contradicts §8.1 fourteen lines up | **HIGH** | Say which half replays byte-identically and which is a reproduction |
| 3 | §7.2 | "the one operation this programme measured to break retrieval" | MEDIUM | Delete. §7.2's own preceding sentence is the correct form |
| 20 | §6.3 | The reconciliation sentence still contradicts itself | MEDIUM | Delete it. The shape paragraph that follows is sufficient |
| 26 | §12.3 | "the weakness is real" still opens the section, above the −2.0 table | MEDIUM | Open with the fabrication finding, which is band-independent |
| 27 | §13 | CONFIRMATORY and REGISTERED-OFFLINE results joined under one "sealed external confirmation" | MEDIUM | One clause separating the withheld corpus from the two observed ones |
| 28 | §13 | "the failures measured here were delivery failures", one sentence after its counterexample | MEDIUM | Insert "dominant". One word |
| 29e | §13 | "more than this programme expected when it started removing things" | MEDIUM | Delete. Fails the read-aloud test |
| 23 / N9 | §1.2 | Contributions list carries three retired framings and no §6.3 pointer | MEDIUM | Rewrite against §6.3 and §5.1's scope cap |
| 24 | Figure 5 caption | Replicates still ordered "8.0, 8.0, 8.0, 8.0 and 11.0" | MEDIUM | Run order, matching §12.1 and the abstract |
| 25 | §12.1 | Fourth scored verdict named nowhere in the section | MEDIUM | Carry the 8.5 → 12.0 row and its annotation into §12.1 |
| N5 | Exec summary | Cost envelope lost "on this hardware" | MEDIUM | Restore three words |
| N6 | Exec summary | Determinism stated without the resident-embedder condition | MEDIUM | One clause, per `DO_NOT_WRITE.md` §1 #1 |
| N7 | Exec summary | NF-005 and NF-006 carry no standing on the page | MEDIUM | "both on corpora already observed" |
| N3 | §4.1 | "In full" omits six headline results; NF-007 row cites §6.4 | LOW | Add the rows or drop "in full"; fix the pointer |
| N4 | §8 | Section-level standing label covers a NOT DEMONSTRATED subsection | LOW | Use §6.1's split-label form |
| 9 | §2.1 | "the axes are countable from either system's own description" now contradicted below the table | LOW | Delete the clause |
| 11 | §2.1 | "Most systems above" — unnamed majority over unrun systems | LOW | Name them from `COMPETITIVE_LANDSCAPE.md` |
| 21 | §6.2 / §6.3 | One measure, two table headers; no statement that §6 never uses session touch | LOW | One name, one sentence |
| N8 | §1.3 | Threshold phrasing the executive summary was corrected for | LOW | Reuse the summary's sentence |

**The three most serious**

1. **N2 with N1 — the standing machinery does not close.** The paper ships a five-level
   taxonomy and an in-paper assignment table, which was Cycle 3's most serious ask and
   is the rewrite's best work. It then points at a bounds file grading fifteen results
   under a level that no longer exists, and defines one of its own levels by a property
   one of its graded results provably lacks. An honesty mechanism that does not
   type-check is the one thing a hostile reviewer will spend a paragraph on, and both
   halves are a few lines of editing.
2. **Objection 2 — the retired count is in the subtitle.** `DO_NOT_WRITE.md` retired
   "eleven studies"; the paper's second line says "the eleven experiments", §1 asserts
   eleven were pre-registered while conceding one was exploratory, and §13 opens with
   it. The correction landed in the abstract only. This is the single most quotable
   surface in the document and the fix is a grep.
3. **Objection 16 — accepted and not implemented.** §4.2 is byte-identical to the
   reviewed draft. It states three integrity properties as uniformly achieved, points
   the reader away from the section that inventories where they were not, and
   introduces the rater machinery without saying the raters are models — in a paper
   that says so correctly in two other places. §11.6 has since grown a fifth case, on
   the sealed holdout's own corpus lock, which makes the missing cross-reference worse
   than it was.

**Is the paper within its evidence?** In the body and in §4.1's assignment table, yes —
every number checks against the spine, both claim gates pass at HEAD, the slop list
greps to zero, and §5.1, §6.3, §8.3, §11.6 and §12.3 are each at or below what their
artifacts support. The residue is concentrated in the places that were rewritten last
and re-read least: the subtitle, §1.2, §1.3, §4.2, §7.2, three clauses in the executive
summary, and the closing paragraphs of §13.

**No structural change is required, so a Cycle 5 full pass is not warranted.** Every
item above is a sentence-level edit at a named line, plus one bounds-file update.
What is warranted is the pass Cycle 3 prescribed and this cycle shows was not run: for
each retired claim, grep the *value* and fix every site, not the site the review
quoted. Twelve of the fourteen partials in Part 1 would have closed on that pass alone.

---

**Reviewed at** `d1d118bc` on branch `paper-rework`, against the Cycle 3 draft at
`95000acd`. Read in full: `paper/PAPER_002.md` (all sections, figures, appendices and
provenance), `paper/reviews/CYCLE_3_PAPER_002.md`, `paper/notes/EVIDENCE_SPINE.md`,
`paper/notes/DO_NOT_WRITE.md`, `paper/reviews/CYCLE_1.md`, and
`paper/notes/COMPETITIVE_LANDSCAPE.md` §§ on citation verification and call sites.
Checked by execution: `scripts/check_paper_002_claims.py` (both gates PASS),
`git diff 95000acd HEAD -- paper/PAPER_002.md` (248 insertions, 126 deletions),
registration SHAs for the four REGISTERED-OFFLINE results in their source reports.
