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

**Status: in progress.**

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
distinction present. The threshold phrasing survives at §1.3 — new objection **N3**.

---

**6 — 12 → 14 "with zero targeted losses". → FIXED in the executive summary and §6.4.**

> Exec: "takes an enumeration probe 12 to 14 of 17, **trading art coverage 2 of 4 down
> to 1 of 4** while restoring all four monetary items."
> §6.4: "The winning trace selects **no statement whose source turn is 90**… And art
> falls from 2 of 4 to 1 of 4. This is a breadth composition trade, not universal
> dominance."

Both mandatory boundaries from spine D2 now travel with the number. The abstract does
not carry either — new objection **N4**.

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

_(objections 16–30 pending)_

---

## Part 2 — Defects introduced by the rewrite

_(pending)_

---

## Part 3 — The reader test, re-answered

_(pending)_

---

## Dispositions — Cycle 4

_(pending)_
