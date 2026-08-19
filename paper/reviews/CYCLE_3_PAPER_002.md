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

### §5.1 — the NF-004 sealed holdout

**18. One word is missing from a binding scope cap, and it is the word that licenses
§6.**

> §5.1: "**Scope cap, and it is binding.** This is availability… It is not accuracy,
> and the registration authorizes no **reader, live, promotion or adoption** claim."
>
> `EVIDENCE_SPINE.md` C1: "**Scope cap, binding:** availability only. No **reader,
> live, universal-rule, promotion or adoption** claim is authorized."

Four of five terms survive. The one dropped is **universal-rule** — the only one of
the five that constrains what §6 and the abstract are allowed to do with the result.
And they do use it: the abstract calls the finding "a granularity rule confirmed on a
sealed external holdout", and §6's opening says "§5.1 confirmed **the direction**"
before §6.3 shows the direction reversing on another unit boundary.

I do not think this is deliberate. It is the exact species `DO_NOT_WRITE.md` opens by
warning about — the shorter list is the cleaner sentence, which is why it gets
written. But the deletion is load-bearing: with "universal-rule" restored, "a
granularity rule confirmed on a sealed holdout" is not a sentence this paper may
write, and §6.3's reversal stops being a curiosity and becomes the reason the cap
exists.

**Required form.** Restore the word verbatim from the registration, and add the
consequence: what was confirmed is one unit substitution — session-inherited score to
own-pair cosine — on LoCoMo, at 16,000 characters. It is not a rule about ranking
units in general, and §6.3 shows a different unit boundary on a different corpus going
the other way.

---

**19. `p = 6.19e-12` treats 1,098 records nested in six conversations as independent
draws, and the paper offers no clustering-robust companion — which it has and which
would cost it nothing.**

> "140 gains, 48 losses, 910 ties. Net +92. Gain/loss ratio 2.92 against a registered
> bar of 2.0. **One-sided exact binomial p = 6.19e-12.**"

A cs.CL reviewer will reach for this in the first pass. The 188 discordant records sit
inside six sealed conversations, and LoCoMo questions within a conversation share
speakers, topics, session structure and often evidence sessions. The exact binomial
assumes 188 independent Bernoulli trials. The effective number of independent units is
six.

The registered statistic is the registered statistic and reporting it is correct — do
not re-score. But the paper already reports the clustering-robust version and does not
recognize it as one: **every one of the six conversations is net positive** (+7, +6,
+13, +30, +15, +21). A conversation-level sign test on 6 of 6 gives one-sided
p = 0.0156. That is four orders of magnitude weaker than 6.19e-12 and it is the number
that survives the objection. Reporting both is strictly better than reporting either,
and a paper that elsewhere records a self-audit for choosing macro F1 against a
dense-boundary corpus (DMR-001C) should be the paper that volunteers this.

**Required form.** Keep the registered exact binomial, and add: at the conversation
level, 6 of 6 net positive, one-sided sign test p = 0.0156 — the effect is not carried
by one conversation, and the record-level p-value assumes an independence the corpus
does not have.

---

### §6 — granularity, and §6.3 where it reverses

**20. The measured relation between ranking unit and delivery is non-monotone. The
rule the paper states is monotone and cannot generate the shape of its own data. This
is my most serious objection to §6.**

> §6.3: "Finer *ranking* — at this unit, on this corpus — **loses 37**… That is the
> opposite sign to §6.2, on the same corpus, and the reconciliation is the size table
> in §6.1: an episode is **already small enough that its embedding stays informative**,
> and dropping to it **discards the broader context that was doing the scoring
> work**."

Read the two clean ranking-only contrasts side by side, packing held fixed in each:

| Packing held at | Coarser ranking | Finer ranking | Winner |
|---|---:|---:|---|
| Turn (§6.2, NF-005) | Episode **361** | Turn **461** | finer |
| Episode (§6.3, NF-003) | Session **388** | Episode **351** | coarser |

The episode loses from both directions. It is beaten by the unit above it and beaten
by the unit below it. The relation is U-shaped in unit size with the episode at the
minimum — and a rule of the form "**rank at the finest unit whose embedding remains
informative**" is monotone by construction. Monotone rules do not produce local
minima. Whatever is happening here, this rule does not describe it.

The offered reconciliation is also internally inconsistent in a single sentence: the
episode's embedding "stays informative" *and* dropping to it "discards the broader
context that was doing the scoring work". If the second clause is true the first is
false, and if the first is true the 37-item loss is unexplained.

There is a coherent reading the paper is one step away from, and its own numbers point
at it: what fails at the episode is not size but **boundary alignment**. A LongMemEval
episode is a retrieval-corpus artifact, neither the semantic unit the question targets
(the turn, median 298 chars) nor the topical envelope that supplies disambiguating
context (the session). Both neighbours are principled units; the episode is neither.
That reading predicts a U, it is consistent with the rho 0.484 length correlation
rather than replacing it, and it is testable.

**Required form.** State the shape before the rule. On this corpus, ranking at the
session and at the turn both beat ranking at the episode, so unit size alone does not
order the arms and the mechanism is not monotone dilution. Then either offer the rule
as a heuristic explicitly known to fail at the episode boundary, or replace it with the
alignment reading and mark that as interpretation, per the treatment §3.3 already
gives to interpretive claims.

---

**21. The same measurement is called "any exact evidence" in §6.2 and "strict
answer-episode delivery" in §6.3, and the collision lands on the exact word that
distinguishes the corrected NF-003 from its withdrawn version.**

> §6.2 table header: "**Any exact evidence**" — Episode / Episode = **351 / 465**
> §6.3 table header: "**Strict answer-episode delivery**" — Episode / Episode =
> **351 / 465**

Same arm, same corpus, same count, two names one section apart. `EVIDENCE_SPINE.md`
D1 and D15 confirm they are one measure.

This is not pedantry about labels. "Strict" is the load-bearing word in this
programme's own correction history: `DO_NOT_WRITE.md` §1 #3 retires NF-003's "49
gains, zero losses" as a **session-touch surrogate** and records that "**the strict
answer-episode measure reverses it**". A reader who notices "strict" appearing on one
table and not the other has to consider whether §6.2's numbers are the surrogate. They
are not — but the paper made them ask.

**Required form.** One name for one measure, used in both tables, and a single
sentence saying the endpoint is strict answer-episode delivery throughout §6, never
session touch.

---

**22. "The finest unit whose embedding remains informative" has no operational
definition, so the rule cannot be applied to a corpus that has not already been
measured.**

> "**rank at the finest unit whose embedding remains informative, and pack at the
> finest affordable unit.**"

The second clause is actionable: "affordable" is a character budget, and a
practitioner can compute it. The first is not. "Informative" is defined nowhere in the
paper, has no threshold, no estimator and no diagnostic. Applied prospectively it
reduces to *try the units and keep the one that wins*, which is the measurement, not a
rule derived from it.

The paper has the materials to do better and stops short. §6.1 gives median unit sizes
(2,550 / 298 / 241) and a Spearman rho of 0.484 between parent length and worse
normalized own-cosine rank. NF-005 records the mechanism as information dilution. That
is enough to state a *candidate* operational form — an approximate size band, or a
diagnostic on the distribution of own-cosine rank against parent length — and to say
plainly that this programme has not validated one.

**Required form.** Either give the rule an operational handle and label it untested, or
demote it from "rule" to what §6.3's own last sentence already concedes it is: a
posthoc characterization on an exhausted corpus. Do not carry the word "rule" into the
abstract while §6.3 carries the word "posthoc".

---

**23. The executive summary's "the same change reproduces on two more corpora" is
contradicted inside §6, on one of the two.**

> Executive summary: "**Why the unit is the lever.** The same change reproduces on two
> more corpora and the mechanism is legible."

The two further corpora are LongMemEval (§6.2, NF-005) and the internal 121-turn store
(§6.4, NF-006). §6.3's reversal is on **LongMemEval — one of the two named** — where a
finer ranking unit loses 37 items. The summary's word "reproduces" is doing exactly
what §6.3 exists to prevent, and it is doing it on the page where the qualifier is
absent.

Compounding it: NF-005's corpus was already observed and is capped `CHARACTERIZED` for
that reason, and NF-006 is a single enumeration probe on a constructed store whose
composition trade the summary omits (objection 6). Neither is a replication in the
sense "reproduces" carries in a cs.CL abstract.

**Required form.** "The direction holds at two further unit boundaries on two observed
corpora, and reverses at a third on one of them; §6.3." The reversal is a stronger
sentence than the reproduction, because it is what makes the rule conditional rather
than lucky.

---

### §12.1 — the instrument band

**24. UNDERCLAIM, and a factual reordering. The divergent replicate was the *first*
run in a fresh process, not the fifth. The paper's ordering hides the most useful
diagnostic in the arc.**

> "Five replicates… scored **8.0, 8.0, 8.0, 8.0 and 11.0**… **The fifth** — the only
> one to meet an empty server slot — diverges at turn 1 from a byte-identical
> 757-byte prompt and never re-converges."
>
> `EVIDENCE_SPINE.md` §1: "scored **11.0, 8.0, 8.0, 8.0, 8.0**… **replicate 1**, the
> only one meeting an empty server slot, diverges at turn 1."

The scores are reordered so the outlier reads last, and the prose then calls it "the
fifth". It was the first. On the source record, the run that met an empty slot was
the run that went first, which is what "empty slot" means.

This is not a rounding matter, and correcting it makes the paper *stronger*, not
weaker. "One of five replicates was odd" is a variance nuisance. "**The first run in a
fresh server process scores differently from every subsequent run, and diverges at
turn 1 from a byte-identical prompt**" is a structural property of the instrument with
a name, a direction and an immediate consequence: every cold-start scored run in this
arc — and §12.2 confirms none pinned process state — is a first run. That includes
Study 009's Arm S and Arm L, which §12.1 already flags as running hours apart with no
recorded PID.

The paper has found something specific and reported it as something generic.

**Required form.** Report the replicates in run order, 11.0 first. State the finding as
a first-run effect: the run meeting an empty slot diverges at turn 1 and never
reconverges; replicates 2–5 are byte-identical across all 121 turns. Then state the
consequence for the arc, which is the part that matters.

---

**25. "Three of this arc's scored verdicts fall inside the band" has no denominator,
and the fourth row of the spine's own table is missing.**

> Heading: "**most** scored comparisons here are below it"
> Body: "**three** of this arc's scored verdicts fall inside the band and are not
> demonstrated"

Two quantifiers, no total. "Most" and "three" are consistent only if the arc has four
or five scored verdicts, and the paper never says how many there are. Figure 5 is
described as drawing the band "across every scored verdict in the arc", so the
denominator exists in the build and is withheld from the prose.

The gap matters because of what sits just outside the three. `EVIDENCE_SPINE.md` §4
carries a **fourth** row that §12.1 does not: the corrected treatment series at
8.5 → 12.0, gap **3.5**, annotated "Exceeds the band — and **exceeding a band is not
being demonstrated**." That row was written into the spine precisely to block the
inference a reader makes from "three fall inside": that the rest fall outside and are
therefore fine. §12.1 names the three and stops, which is the same defect as objection
5 in the executive summary, here at its source.

**Required form.** Give the denominator — three of N — and carry the spine's fourth
row into the section verbatim, including its annotation. A gap of 3.5 on an instrument
whose band is 3.0 and whose band is a switch rather than a spread is not demonstrated
either, and the paper should be the one to say so.

---

### §12.3 — availability is not correctness

**26. "The weakness is real" is bolded at the top of the section and retracted in its
last paragraph.**

> Opening: "This was the largest structural weakness of this paper's predecessor.
> **It has now been measured, and the weakness is real.**"
> Closing: "The **−2.0 is as unreplicated as the +1**, and §12.1 applies to both."

Both sentences are in the same eight hundred words and they do not agree. The first is
bolded, declarative, and positioned where a limitations section states its finding.
The second is the true one. A reader who takes the section's headline away takes the
one the section itself withdraws, and objection 4 shows the executive summary took the
bolded version.

The section does not need the bolded sentence, because it has better material and
already states it. What is genuinely established here does not depend on any score:

- A **pre-registered kill bar fired**. B2, tolerance 0.5, registered as a kill before
  any number existed. The disposition is a decision-procedure outcome.
- The **offline and live measurements dissociated in kind, not just in magnitude**.
  Offline the configuration preserved 16 of 16 targeted items; live, asked for the two
  formatting rules planted in turns 1 and 2, it reported it could not see the start of
  the conversation. IC-001 corroborates the availability half deterministically — the
  turn-1 and turn-2 episodes are exactly the ones the deployed fill order drops.
- **Both arms fabricated** on the domain neither retrieved, and a presence-only scorer
  credited one of them for correct pigment terms attached to the wrong artist. That is
  a demonstrated defect *in the availability measure itself*, and it does not go
  through the rubric at all.

That third item is the strongest thing in §12.3 and it is in the last paragraph, in a
subordinate clause, unbolded.

**Required form.** Replace "the weakness is real" with "the two were measured and did
not move together, and the availability measure was shown to credit a wrong answer."
Promote the fabrication finding out of the closing aside. Keep "as unreplicated as the
+1" — it is the sentence the section should be trusted for.

---

### §13 — conclusion

**27. The conclusion hands a practitioner a universal rule whose reversal it does not
mention. §6.3 is absent from §13 entirely.**

> "*Rank at the finest unit whose embedding stays informative.* **This is the result
> with sealed external confirmation** — 843 to 935 of 1,098 on withheld conversations,
> and 361 to 461 of 465 with zero losses on a second corpus."

The conclusion is where a paper's claims are extracted for citation, and this is the
sentence that will be extracted. Three things are wrong with it and they compound.

First, the rule is not the result. The result is one unit substitution — session-
inherited score to own-pair cosine, LoCoMo, 16,000 characters — under a registration
whose scope cap forbids a **universal-rule** claim (objection 18). "This is the result
with sealed external confirmation" identifies the rule with the confirmation.

Second, the 361 → 461 figure is placed inside the same sentence, joined by "and", so
the sealed-confirmation standing reads as covering both. NF-005 is
DETERMINISTIC-OFFLINE on an already-observed corpus, capped `CHARACTERIZED` for that
reason. The conjunction erases the distinction §4 exists to draw — which is objection
13's consequence arriving exactly where predicted.

Third, and worst: **§6.3 does not appear in the conclusion in any form.** The paper's
own reversal — finer ranking losing 37 items on the same corpus that supplies the
361 → 461 — is the reason the rule carries the qualifier "whose embedding stays
informative", and a practitioner reading only §13 gets the qualifier without the fact
that generated it, which makes it read as a caveat rather than as a boundary someone
crossed and measured.

**Required form.** State the confirmed substitution and its scope. Then state the
reversal in the conclusion, one sentence: on LongMemEval the same move from session to
episode loses 37 items, so the unit is not monotone and the rule is a heuristic with a
known failure point. A practitioner who is told where a rule breaks can use it. One who
is told it was confirmed on a sealed holdout will apply it at the wrong boundary.

---

**28. The closing paragraph is contradicted by §12.3, in the same paper.**

> §13, final paragraph: "The programme's own summary of eleven efforts is that **the
> model used what it received. At the hardest probe it used all ten available facts
> and invented none. The failures were delivery failures**"
>
> §12.3: "**Both arms also fabricated** on the domain neither retrieved — one
> attributing a painting to the wrong artist while still producing both correct pigment
> terms, which a presence-only scorer credits."

The last substantive sentence of the paper says the model invented nothing and the
failures were delivery failures. Ninety lines earlier the paper reports both arms of
its only live validation fabricating. Both cannot stand.

The narrower claim is fine and traced: 10 of 10 available facts used, none invented,
**at one probe in Study 007**. The conclusion promotes it into "the programme's own
summary of eleven efforts" and then into a claim about the failure class of the whole
arc. That promotion is what collides with §12.3.

It also matters more than an inconsistency, because "the failures were delivery
failures" is the sentence that justifies the paper's entire scope — availability
measurement as sufficient. §12.3's fabrication observation is the counterexample: on a
domain neither arm retrieved, the model generated, and the availability scorer credited
it. The paper measured the exception to its own framing and then closed on the
framing.

**Required form.** Scope the sentence to its probe, and state the counterexample beside
it: at the hardest Study 007 probe the model used all ten available facts and invented
none; in the live validation both arms fabricated on the domain neither retrieved.
Delivery was the dominant failure mode this programme measured, and it was not the only
one.

---

**29. Four withdrawn or corrected framings recur in §13 after being flagged upstream.**

Consolidated, because each is an instance already argued:

- "**Eleven pre-registered efforts**" — objection 2. Fourth occurrence in the document
  (subtitle, abstract, §1, §13), plus "eleven efforts" in the closing paragraph.
- "**It is the one operation measured here to break retrieval**" — objection 3, restated
  verbatim from the executive summary. `EVIDENCE_SPINE.md` D10 says this does not follow
  from a measured comparison. The trailing clause "even though most of the best records
  survived the cut" adds an unquantified "most" to an unmeasured claim.
- "**The systems that ship in this space spend a model call on this layer**" —
  objection 8, unsourced universal, restated.
- "**Availability and correctness were measured moving in opposite directions once**" —
  objection 4, third occurrence, and here without the retraction §12.3 supplies four
  hundred lines earlier.

One further item, new to §13: "the answer is **more than this programme expected when
it started removing things**." This is an unfalsifiable claim about the authors' prior
expectations, closing the practitioner section where a measurement belongs. It fails
`DO_NOT_WRITE.md` §4's read-aloud test — it could preface any paper in any field.

**Required form.** Fix each at its first occurrence and re-grep. `DO_NOT_WRITE.md`'s
own instruction applies: grep for the superseded value, not the superseded sentence.
Delete the expectation clause.

---

**30. UNDERCLAIM. The conclusion never names a single one of the three negative
confirmatory results.**

> "Eleven pre-registered efforts produced one architecture worth keeping, one
> externally confirmed rule about how to use it, and **a measurable account of why the
> rest did not work**."

"The rest did not work" is the conclusion's entire treatment of DMR-004, DMR-001,
DMR-001C and SAL-001 — four sealed-holdout experiments, three of them negative, each
of which killed a named mechanism with a pre-registered bar. §5 reports them properly.
§13 compresses them into a subordinate clause with no names, no bars and no numbers,
and the phrasing "did not work" invites the reading that they were abandoned rather
than that they were decided.

This is the same omission as objection 7 and it is worse here, because §13 is where a
reader decides what the paper was about. A conclusion that says *we built the best
confirmatory apparatus in this repository specifically to test a model-free adaptive
controller, and it returned Youden's J of 0.320 against a 0.50 bar, so the controller
is not authorized* describes a different and better paper than one that says the rest
did not work.

The asymmetry is the tell: the one positive confirmatory result gets its numbers in
§13 twice. The three negative ones get none.

**Required form.** Name them and give one bar each. Surprisal-proximity salience:
adjusted AUC 0.416 against ≥0.60, five of six strata below chance, registered effect in
the opposite direction. Adaptive event formation: 52 of 74 events closed by the size
cap, forced fraction 0.703 against a 0.35 bar. Model-free sufficiency: J = 0.320
against ≥0.50, beaten on raw accuracy by an always-`OPEN` control. Then the sentence
"the design is four components" has visible causes.

---

## Judgement questions

_(pending)_

---

## Dispositions — Cycle 3

_(pending)_
