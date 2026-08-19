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

## Judgement questions

_(pending)_

---

## Dispositions — Cycle 3

_(pending)_
