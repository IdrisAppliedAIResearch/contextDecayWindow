# PAPER-002 — Adversarial Review, Cycle 3

Target venue: arXiv cs.CL preprint. Scope-limited adversarial pass over the
high-risk sections of `paper/PAPER_002.md`: the executive summary, §2.1, §4,
§5.1, §6 opening and §6.3, §12.1 and §12.3, and §13.

Bounds are `paper/notes/EVIDENCE_SPINE.md` (standing per number) and
`paper/notes/DO_NOT_WRITE.md` (withdrawn claims). House format follows
`paper/reviews/CYCLE_1.md`: numbered objections, each quoting the condemned
text, giving the reason, stating the required form.

Overclaim and underclaim are weighted equally.

**Status: in progress.**

---

## Objections

### Executive summary

**1. The lead sentence attaches the sealed holdout to the whole design. NF-004 is an
arm contrast on one parameter, not a system beating a control.**

> "A conversational memory layer needs no generative model calls. This one stores
> every exchange verbatim, ranks candidates by embedding similarity at the finest
> unit that stays informative, and packs a fixed character budget with a set-level
> coverage objective. Nothing in the path asks a model to write text about the store.
> **On a sealed external holdout it beats its own strongest control on evidence
> availability by a margin that is not close.**"

Three sentences describe a four-component architecture; the fourth says "it" beats a
control on a sealed holdout. The referent a reader takes is the architecture. It is
not what was measured. NF-004 held the harness, the budget, the packing rule and the
store fixed and varied the *ranking unit* between `S_SESSION_RANK` and
`P_PAIR_RANK`. The coverage objective, the recency tier and the cosine threshold —
three of the four components just named — are not on either side of that comparison.
Nothing on the sealed holdout tests them at all.

The evidence spine's own framing of C1 is "LoCoMo ranking granularity". The paper's
is "it beats its own strongest control". Those are different claims, and the second
is the one that would be quoted.

"a margin that is not close" also violates the adjective rule in `DO_NOT_WRITE.md`
§4 while giving away precision the programme actually earned: the ratio is 2.92
against a registered 2.0 bar at p = 6.19e-12. That is a stronger sentence than "not
close" and it is available.

**Required form.** Name the contrast, not the system: on a sealed external holdout,
ranking at the adjacent-pair unit rather than inheriting the session score raises
complete evidence availability from 843 to 935 of 1,098, ratio 2.92 against a
registered bar of 2.0. Do not let "it" refer to the architecture.

---

**2. "Eleven pre-registered experiments" is a withdrawn count wearing a new noun,
and the adjective is false of one of them.**

> "the **eleven** experiments that cut it down to size" (subtitle)
> "the **eleven pre-registered** experiments that reduced it to four components"
> (abstract)

`DO_NOT_WRITE.md` §1 #8 retires "eleven studies" in favour of **ten numbered studies
plus one registered exploratory bakeoff**. Renaming studies to "experiments" does not
discharge the correction; the audit's own instruction is to grep for the superseded
*value*, and the value is eleven.

Two further defects ride along. First, "pre-registered" is false of the eleventh: the
bakeoff was registered *exploratory*, which is why the spine can cite its 6.09%
oracle ceiling as a subtraction and not as a result. Second, the count is now wrong
in the other direction as well — the paper's own confirmatory tier is NF-004,
DMR-001, DMR-001C, DMR-004 and SAL-001, and its deterministic tier adds NF-005,
NF-006, NF-007, EC-001, EC-002, IC-001, AR-001, DR-002, DX-001, E005 and the cost
work. Calling the arc "eleven experiments" undercounts the actual evidentiary base by
better than half while overcounting its registration status. This is the rare defect
that is an overclaim and an underclaim in the same phrase.

**Required form.** "Ten numbered studies and one registered exploratory bakeoff," and
where the count is meant to convey scale, count the component experiments honestly or
drop the number.

---

**3. "The one operation measured here to break retrieval" — the spine says DR-002 is
not a measured comparison.**

> "The obvious fix — prune low-similarity candidates to control cost — is **the one
> operation measured here to break retrieval**, so retention is unbounded by policy
> and the trimming knob carries an `unsafe_` prefix."

`EVIDENCE_SPINE.md` D10 states the boundary explicitly: "**This follows from the
pool's contents, not from a measured comparison** — which is why it is the load-
bearing claim of the forced order." DR-002 establishes that the deployed 34-episode
pool contains no art episode and therefore cannot reach four domains at any setting.
That is a structural fact about pool membership. The paper converts it into a
measurement, and into a uniqueness claim ("the one operation"), in the executive
summary where the qualifier is furthest away.

This matters more than it looks, because the sentence is the paper's justification
for an engineering decision (`unsafe_` prefix, unbounded retention). A design
constraint sourced to a measurement that does not exist is the exact defect Cycle 1's
B2 caught in PAPER-001.

**Required form.** State it structurally: dropping the 19 lowest-cosine of 119
candidates removes the only episodes carrying one of the four domains, so the pool
cannot reach four-domain coverage at any setting — a property of the pool's contents,
not a measured comparison of pruning policies.

---

**4. LV-001's −2.0 is asserted as a real drop. It is inside the band the same summary
declares four lines earlier.**

> "**Availability is not correctness, and one live run showed them moving in opposite
> directions.** The configuration that made six more facts available **scored *lower*
> on targeted probes** and failed its own pre-registered bar. It is **not promoted**."

`DO_NOT_WRITE.md` §2 #28 is unambiguous: "Study 009's 3.0, LV-001's −2.0, or Study
011's −1.0 asserted as demonstrated → **all inside the measured 3.0 band**." LV-001's
targeted regression is 3.5/8 → 1.5/8, a −2.0 gap, and `EVIDENCE_SPINE.md` §4 lists it
under NOT DEMONSTRATED.

The paragraph asserts it twice — "showed them moving in opposite directions" and
"scored *lower*", with the emphasis added by the author. A reader takes this as a
measured divergence. On this instrument it is not one.

The escape is available and the paper does not take it. **The bar firing is a fact
independent of the band.** B2 was registered as a kill at a 0.5 tolerance; the
observed value crossed it; the promotion died. That is a decision-procedure outcome
and it stands whether or not the underlying 2.0 points are real. The correct sentence
is about the registered bar, not about the direction of the score.

**Required form.** The configuration that made six more facts available failed its
own pre-registered targeted bar (B2, registered as a kill at 0.5 tolerance) and was
not promoted. The observed −2.0 gap sits inside the instrument's 3.0-point band and
is not itself demonstrated; the disposition does not depend on it. Then state what
*is* demonstrated about availability-vs-correctness: the two were measured, they did
not move together, and this programme had only ever measured the first.

---

**5. "No scored comparison below about three points is demonstrated" licenses the
inverse inference the spine forbids.**

> "**The instrument's run-to-run band is 3.0 points on a 13-point rubric, measured
> rather than assumed.** No *scored* comparison in this arc below about three points
> is demonstrated"

Stating the negative as a threshold invites the reader to complete it: comparisons
*above* three points are demonstrated. `EVIDENCE_SPINE.md` §4 refuses that completion
in the row it added for exactly this purpose — the corrected treatment series at
8.5 → 12.0, gap 3.5: "Exceeds the band — and **exceeding a band is not being
demonstrated**."

The band is also not a spread. The spine records it as a switch: replicates 2–5 are
byte-identical across all 121 turns, and replicate 1 — the only one to meet an empty
server slot — diverges at turn 1 from a byte-identical 757-byte prompt and never
reconverges. A quantity produced by an uncontrolled process-state switch does not
behave like measurement noise you can subtract and clear a threshold against. The
summary's phrasing implies otherwise.

**Required form.** Two clauses, not one. The band is 3.0 points and no scored
comparison in this arc is demonstrated on this instrument; a gap larger than the band
is not thereby demonstrated either, because the band is a process-state switch rather
than a spread, and no study in the arc pinned process state.

---

**6. The internal 12 → 14 is stated with "zero targeted losses" and without the
composition trade that the spine marks as mandatory.**

> "On the internal store the same move takes an enumeration probe from **12 to 14 of
> 17 with zero targeted losses.**"

Both halves are true and together they mislead. `EVIDENCE_SPINE.md` D2 attaches two
boundaries that "must travel with this number", and one of them is a loss: art falls
**2/4 → 1/4**, and against C0 the tally is "3 gains, **1 loss**, net +2". The zero
applies to the *targeted* gate (21/21 vs 21/21), a different measurement. A reader of
the sentence as written concludes the move is free. It is not; it is a breadth
composition trade, which is the spine's own wording and the more interesting fact.

The second mandatory boundary — the registered T1 trace selects no statement whose
source turn is 90, so DX-001's carrier is still unresolved — is also absent.

**Required form.** 12 → 14 of 17 with 21 of 21 targeted items preserved, one domain
gained (monetary 1/4 → 4/4) and one lost (art 2/4 → 1/4): a composition trade, not
dominance.

---

**7. UNDERCLAIM. Three of the five confirmatory results are negative, and the summary
does not say so.**

The executive summary's confirmatory content is NF-004 and nothing else. DMR-004,
DMR-001, DMR-001C and SAL-001 do not appear. `EVIDENCE_SPINE.md` §2 makes the point
the summary drops: "**Three of the five are negative, which is the point: the
surviving design is small because these were built well and returned nothing.**"

This is the paper's strongest structural claim and it is missing from the only page
most readers will finish. DMR-004 in particular is described in the spine as "the
strongest confirmatory construction in the repository" — sealed 180-query holdout,
two blind raters, PF3 verifying commit ordering from git history, a registration
commit carrying exactly one file, and a registered statistic (Youden's J) chosen
*because* raw accuracy would have been beaten by an always-`OPEN` degenerate control
at 0.650. It returned J = 0.320 against a 0.50 bar and killed a model-free adaptive
controller. A programme that builds an apparatus that good in order to shoot down its
own mechanism has earned a line in its own summary.

The summary's fourth bullet spends its space on "no competing system was run here",
which is a disclaimer. The kills are evidence.

**Required form.** Add one line to the summary: five results carry a sealed holdout;
three of them are negative and each killed a named mechanism — surprisal-proximity
salience, adaptive event formation, and a model-free sufficiency controller. The
design is four components because the apparatus removed the rest.

---

**8. "The systems that ship in this space spend a language-model call on exactly this
layer" is an unsourced universal, and it carries the paper's framing.**

> "**The systems that ship in this space spend a language-model call on exactly this
> layer.** The question this paper answers is not whether the deterministic version
> wins. It is how much of the layer survives without the call."

The framing sentence that makes the whole paper make sense rests on a universally
quantified claim about an unnamed population, in a summary that four lines later says
"No competing system was run here." `DO_NOT_WRITE.md` §2 #35 forbids presenting any
comparison to HippoRAG, Mem0, Zep or Letta as measured. This one is not presented as
measured — it is presented as a fact of the field, which is a weaker guard, because
"the systems that ship in this space" is a class the paper never enumerates and
cannot have surveyed exhaustively.

There is a defensible version. `EVIDENCE_SPINE.md` D14 records something firmer and
first-hand: LongMemEval's own authors' LLM-assisted indexing and time-aware query
expansion "**were available and deliberately not adopted**, because they add
generative calls to the memory path." That is a decision this programme made and can
document, on a named system, rather than a census of a field.

**Required form.** Name the systems and cite their published descriptions, or make
the claim about the named mechanisms rather than about "the systems that ship". The
`COMPETITIVE_LANDSCAPE.md` note exists; the summary should inherit its specificity.

---

### §2.1 — what is and is not being compared

**9. The table is licensed as "arithmetic on published descriptions" for one row and
then carries four more rows that are nothing of the kind.**

> "What is comparable is architectural, and **the axes are countable from either
> system's own description**"
>
> | Failure mode | An episode is not delivered | An episode is not delivered, **or is delivered as a wrong paraphrase** |
> | Replayability | … | **Bounded by generation determinism** |

The paragraph after the table concedes the point for one row — "**That first row** is
the one comparison this paper can make without running anything" — but the sentence
introducing the table has already generalized to all five, and the rows themselves
carry no per-row standing.

Row 1 is countable: Mem0's `1 + n`, Graphiti's five per-episode calls. Row 5 is
sourced: they report judged accuracy. Rows 2, 3 and 4 are not countable from anyone's
description. "Delivered as a wrong paraphrase" is a **failure mode asserted of systems
that were not run**, and it is the least flattering cell in the table. "Bounded by
generation determinism" is an inference about implementations this paper has not read.
A reader who accepts the framing sentence accepts all five rows on the authority
earned by one.

**Required form.** Mark the table per row, the way §4 marks results: rows 1 and 5
counted from published descriptions; rows 2–4 stated as architectural consequences
that follow from spending a generative call, not as measured properties of named
systems. Or delete rows 2–4 and keep the two that survive their own standard.

---

**10. The paper prints the forbidden juxtaposition, both numbers included.**

> "The forbidden sentence has the form *\"on LoCoMo, that system reports **66.88%**
> and this component reaches **935 of 1,098**\"* — both halves true, the juxtaposition
> meaningless."

This is the best-intentioned paragraph in the section and it does the damage it warns
against. The construction is the one this programme has already learned about from a
different direction — printing a thing in order to say you have not used it does not
undo having printed it. Once the sentence exists in the preprint, it is quotable,
screenshottable and indexable, stripped of its "forbidden" frame. On arXiv it will be
read by people skimming for a number to put in a slide, and this paragraph hands them
a formatted one.

The 66.88% is also the section's only competitor figure quoted inline, and §2.1's own
next paragraph warns that several such figures "appear in **Mem0's own comparison
table** and are Mem0's reproductions rather than author-reported results." The paper
therefore prints a number whose provenance it flags two paragraphs later as the kind
requiring care.

**Required form.** Describe the shape of the forbidden sentence without instantiating
it: *a sentence placing a judged-accuracy percentage beside this paper's availability
count is meaningless, because the denominators count different events.* Zero numerals
required.

---

**11. "Every system above consumes a candidate set produced upstream by similarity
ranking" is a universal claim about architectures the paper has not run, and it is the
placement claim.**

> "**The placement is narrow.** Every system above consumes a candidate set produced
> upstream by similarity ranking. This paper measures that set."

This carries the paper's entire claim to relevance, and it is asserted over a list
that includes HippoRAG — which §2 itself describes two hundred words earlier as
building "a knowledge graph over extracted entities and retrieves **by traversal**".
Traversal over a graph is the alternative to similarity ranking, not an instance of
it. Graphiti's edge-invalidation and temporal-extraction path is likewise not
downstream of a cosine ranking in the sense this paper measures.

The claim may hold for Mem0 and Letta. It is stated of "every system above".

**Required form.** Name the systems for which it holds and say so; for the graph
systems, state the weaker and still useful version — that a similarity-ranked
candidate set is one of the standard upstream stages in this space, and this paper
measures that stage.

---

**12. Two small framing defects that read as hedge drift.**

> §2.1: "the question is **rarely** whether the deterministic version wins"
> Executive summary: "The question this paper answers is **not** whether the
> deterministic version wins"

The same committed framing sentence appears in two strengths eighty lines apart. One
of them is wrong. "Rarely" is also a frequency claim over a population of deployment
decisions this paper has no data on.

> "A mechanism that **recovers most of it** and still loses a head-to-head is a
> finding, and one this paper is not in a position to report either way."

"Recovers most of it" presupposes the quantity the sentence then declines to report.
The clause is doing the work of a result while disclaiming that it is one.

**Required form.** Pick one strength for the framing sentence and use it in both
places. Replace "recovers most of it" with the conditional it actually is: whether
this component recovers most of the layer is not measured here.

---

### §4 — how results are graded

**13. The taxonomy is defined inside the paper and *applied* outside it. An arXiv
reader gets the vocabulary and not the assignment. This is my most serious objection
to §4.**

> "Four levels. **Applied once, here, so the prose does not hedge sentence by
> sentence.** The full assignment for every number in this paper is in
> `paper/notes/EVIDENCE_SPINE.md`."

The device's whole justification is that hedging moves out of the prose and into one
place. But the one place is a repository note, not a section of the preprint. The
consequence is precise and bad: in §5 through §13 a reader encounters hundreds of
numbers, four standing levels, and **no marking on any individual number**. 843 → 935
(CONFIRMATORY), 361 → 461 (DETERMINISTIC-OFFLINE, and capped `CHARACTERIZED` because
the corpus was already observed), 12 → 14 (DETERMINISTIC-OFFLINE), 375/388/351
(posthoc on an exhausted corpus, explicitly "**not** a registered universal law") and
7.0 vs 8.0 (NOT DEMONSTRATED) are all set in the same typography, in adjacent
sections, with the same declarative voice.

§4 says the taxonomy "licenses the confident voice everywhere else". It cannot license
what it does not reach. As submitted, the confident voice is uniform and the standings
are not, and the only artifact that distinguishes them is one the venue will not
receive.

This is also the mechanism by which the taxonomy could function as laundering, and it
is not a hypothetical: the paper's *strongest* label attaches to one result, and the
prose habit it authorizes attaches to all of them.

**Required form.** Carry the standing to the point of use. A one-word tag on each
results subsection heading, or a bracketed label on each headline number, or — the
cheapest fix — an appendix table in the preprint itself listing every headline number
against its level. `EVIDENCE_SPINE.md` §1–§4 is already that table; ship it.

---

**14. The taxonomy has no level for the results that make up most of the paper, so
they inherit DETERMINISTIC-OFFLINE and its "state as measured" licence.**

> | **DETERMINISTIC-OFFLINE** | Zero generative calls; counts and identities, not
> scores; byte-identical on replay | **As measured, with the corpus named.** Not a
> benchmark score |

Four levels sound exhaustive. They are not. Between "sealed holdout with bars locked
first" and "corrected in ERRATA" there is exactly one positive level, and it is
defined by *how the number was computed* rather than by *whether anything was
committed before it existed*. Everything deterministic therefore lands there
regardless of its epistemic position, and the spine's own per-result caps show how
wide that range is:

- NF-005 — capped `CHARACTERIZED` **because the corpus was already observed**.
- NF-003 — "**posthoc characterization on an exhausted corpus. Not a registered
  universal law.**"
- NF-007 — an **instrument stop**: the registered instrument could not distinguish
  treatment from control.
- AR-001 — computed **with the answer key**; "bounds, not methods".
- EC-002 — "A0 is a reproduction under recomputed embeddings, **not a byte-exact
  replay**."

All five are DETERMINISTIC-OFFLINE and all five may therefore be stated "as measured".
An exploratory posthoc reading of an exhausted corpus and a preregistration-free
oracle bound computed from the answer key receive the same presentational licence as
a byte-identical 500-store counterfactual replay. That is the laundering channel, and
it is not the band level — it is the missing level above it.

**Required form.** Add a fifth level, or subdivide the second: *deterministic and
registered before the number existed* versus *deterministic and posthoc / on an
observed corpus / computed with the key*. §4.3's mechanism-versus-instrument stop
distinction is already the right instinct; extend the same discipline to positive
results.

---

**15. DETERMINISTIC-OFFLINE requires "byte-identical on replay". The external
calibration results do not satisfy it and are presented at that standing anyway.**

> §4.1: "Zero generative calls; counts and identities, not scores; **byte-identical on
> replay**"
> §8.1: "The 500 stores from the external calibration run, replayed with only the
> packing order changed… No reader inference, no embedding call."
> §8.3: "The suppression is confirmed — it is an offline count, **byte-identically
> replayable**"

`EVIDENCE_SPINE.md` D4 says the opposite in as many words: "**Scope cap:** A0 is a
reproduction under recomputed embeddings, **not a byte-exact replay**. **EC-001 is
permanently unreplayable at bit granularity** — its cache was not retained, and
CC-006's protection is prospective only."

§8.1 omits the cap entirely and §8.3 asserts the property the cap denies. The +32.3
point result may well survive — recomputed embeddings are a small perturbation — but
this programme has measured that a perturbation of cosine 0.999837 flips 6 of 146
committed payloads, so "small perturbation, therefore fine" is precisely the inference
its own §11.3 forbids.

**Required form.** Carry D4's scope cap into §8.1, and in §8.3 write "an offline count
under a recomputed-embedding reproduction of the deployed arm" rather than
"byte-identically replayable". If the intended claim is that the *counterfactual* half
replays byte-identically while the baseline half does not, say that — it is a real and
defensible distinction and the current wording erases it.

---

**16. §4.2 states the integrity machinery as uniformly achieved; the arc's record is
that it was achieved unevenly, and §4.2 points the reader at the wrong section.**

> "Registration commits contain no implementation files, **which is checkable and was
> checked**."
> "**A gate is trusted to stop only after showing that its tested population and its
> non-stopping alternative were capable of existing**… §5.4 and §11.5 each report
> one."
> "**Sealed scoring.** Three blind passes with registered adjudication triggers."

Three problems, in increasing order.

First, the spine documents the registration-commit check for two studies by name —
DMR-004 ("registration commit carrying exactly one file") and DMR-001C ("carries no
file under `src/` or `tests/`, verified with `git show --stat`"). NF-004's entry gives
a SHA and no such verification. "Was checked" is stated of all.

Second, the reachability sentence is stated as the programme's standing practice, and
§11.6 lists **four** cases where it did not hold — including the one found while this
paper was being written, on the sealed holdout's own corpus-lock constant. §4.2's
cross-reference sends the reader to §5.4 and §11.5. The section that actually
inventories the failures is **§11.6**, and it is not named.

Third, "three blind passes" is presented as an integrity guarantee with no indication
that the raters are language models. §5.2 does this correctly — "two blind raters —
neither human, see §12.8" — which shows the paper knows the move and did not make it
where the machinery is introduced.

**Required form.** Quantify: name the studies whose registration commits were
file-checked. Restate reachability as the rule the programme adopted *after* the
failures, cross-referenced to §11.6. Append "— none human, see §12.8" to the sealed
scoring paragraph, matching §5.2.

---

**17. CREDIT, entered because it makes objection 4 worse. §8.3 is the correct
handling of an in-band result and the executive summary does not follow it.**

> §8.3: "its **−1.0 margin is *inside* the band and therefore not demonstrated in
> either direction**. The programme's registration forbids citing the band to revive
> the rejected correction, and this paper does not. What is established is that
> packing order is a delivery gate. What is not established is that reversing it
> improves answers."

This is the paragraph the rest of the paper should be measured against: the offline
fact, the live verdict, the band, the refusal to use the band in either direction, and
a clean statement of what survives. Study 011's −1.0 is handled exactly right.

It is entered as an objection rather than praise because the same paper, four hundred
lines earlier, asserts LV-001's −2.0 as a real drop in its most-read paragraph
(objection 4). The two in-band results receive opposite treatments, and the one that
gets the loose treatment is the one in the executive summary.

**Required form.** Rewrite the executive summary's availability-versus-correctness
bullet in §8.3's voice.

---

## Judgement questions

_(pending)_

---

## Dispositions — Cycle 3

_(pending)_
