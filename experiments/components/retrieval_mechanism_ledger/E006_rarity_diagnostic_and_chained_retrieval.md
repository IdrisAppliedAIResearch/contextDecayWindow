# E006 - Lexical Rarity Diagnostic, and Conditional Chained Retrieval

**Type:** Diagnostic (Part 1) + conditional mechanism experiment (Part 2). One document, gated.
**Repository:** `contextDecayWindow` - `experiments/components/retrieval_mechanism_ledger/`
**Branch:** `e006/rarity-diagnostic` (Part 2 branches only if authorized)
**Status:** **PART 1 AUTHORIZED - Part 2 does not exist until Part 1 returns and Muzaffer authorizes it**
**Authorization:** Muzaffer, August 3, 2026, in the request to execute the attached implementation specification end to end before PAPER-001 ships.
**Depends on:** LV-001 (PR #35) - DR-002 - DX-001 - AR-001 - PAPER-001 Section 5.5.1
**Companions:** `RETRIEVAL_MECHANISM_LEDGER.md` - `PAPER_001.md`

---

## 0. Why this document is gated

Part 2 proposes chained retrieval - an iterative, self-cueing mechanism grounded in
free-recall research. It is a multi-week arc touching the delivery path.

Part 1 is a correlation on two already-committed artifact sets. Hours, not weeks.

**Part 1 can make Part 2 pointless.** If the retrieval inversion is a property of the
planted vocabulary rather than of retrieval, then no retrieval mechanism - chained,
segmented, or otherwise - addresses it, and the honest next step is a corpus, not an
architecture. PAPER-001 Section 5.5.1 already names this as *the single measurement that
would most change how much Section 5.2.1 deserves.*

**LV-001 is one day old and sets the standing hazard.** A3 preserved 16 of 16
targeted items offline and delivered 1.5 of 8 live, a -2.0 regression at four times
the registered tolerance, because the coverage objective spent its budget on domain
spread and dropped the conversation's opening. Any mechanism that touches selection
is presumed to carry that exposure until measured live. **Part 2 is therefore
expensive by construction**, which is the second reason to gate it.

---

# PART 1 - RARITY DIAGNOSTIC (RD-001)

Offline. No inference, no new run, no embedding calls beyond those already committed.

## 1.1 The question

> **Does an episode's cosine rank against the breadth query track the lexical rarity of its key phrases?**

The program's own description of its hardest facts is that they are *rare technical
phrases whose component words are common* - `photophores`, `mantle margin`,
`lead white`, `ultramarine glaze`, `marine snow`, `dual mandate`. That is a lexical
property, and it predicts the observed effect directly: an embedding places such a
span far from a query phrased in ordinary words.

Two readings of the same data, and they have opposite consequences:

| Reading | If true | Consequence |
|---|---|---|
| **Vocabulary** | Rank tracks rarity | Section 5.2.1 is a finding about this corpus's planted vocabulary. It generalizes only to corpora whose target facts are similarly distinctive. **No retrieval mechanism fixes it.** |
| **Retrieval** | Rank does not track rarity | The corpus objection weakens considerably. The inversion is a property of retrieval on conversational stores, and mechanism work is warranted |

## 1.2 Measurement

1. **Assemble the fact-bearing set.** The 76 of 119 eligible episodes carrying at
   least one breadth item, from the committed store.
2. **Cosine ranks.** Committed for 16 of 119 (PAPER-001 Section 8.8). **State plainly which
   ranks exist.** Recomputing the rest requires the carried embedder under the
   batched call shape of Section 7.2, which is not in the repository.
   - If the full ranking cannot be recovered, **run the correlation on the committed
     16 and report n=16 as the headline limit**, not as a footnote. A correlation on
     16 points is weak evidence and must be labelled as such.
   - If the embedder can be recovered under the pinned batched shape, recover the
     full 119 and say so, with the call-shape assertion passing.
3. **Rarity scores.** From the earlier IDF/rarity audit - already committed. Use the
   same scores that ranked the six hard plants *worse* than density, unchanged. Do
   not recompute with a new corpus statistic; that would be a different measurement.
4. **Correlate** rank against rarity across the fact-bearing set. Report Spearman
   with a confidence interval, the scatter, and the six hard plants marked
   individually.
5. **Report the six separately.** They are the program's named blind spot. Where they
   sit in the scatter matters more than the aggregate coefficient.

## 1.3 Decision rule - commits before any coefficient is computed

Git-verifiable, per standing protocol.

| Branch | Condition | Verdict | Consequence |
|---|---|---|---|
| **A** | Rank tracks rarity - monotone relationship, interval excluding zero, six plants in the predicted region | **VOCABULARY** | The inversion is a corpus property. **Part 2 is NOT authorized.** The honest next step is an external corpus (LongMemEval), not a mechanism. Update PAPER-001 Sections 5.5.1 and 8.5 with the measured result |
| **B** | No relationship - interval containing zero *and* the six plants unremarkable in the scatter | **RETRIEVAL** | The corpus objection weakens. Part 2 becomes eligible for authorization, but is not automatically authorized |
| **C** | Mixed - aggregate weak, six plants strongly patterned, or vice versa | **ESCALATE** | Do not resolve toward either. Report the split and bring it to review |
| **D** | n=16 only, and the interval is uninformative at that n | **UNDERPOWERED** | Report as unresolved. **Do not read an underpowered null as Branch B.** Either recover the full ranking or record the limit |

**Branch D is the likely one and must not be laundered into B.** A wide interval on
16 points is the exact shape of the DX-002 near miss - statistical power read as
evidence of absence. Say so in the report.

## 1.4 Surrogate audit

| Check | Certifies | Can it pass falsely? | Mitigation |
|---|---|---|---|
| Correlation coefficient | rarity explains rank | **Yes** - rank is driven by whole-episode text, not the key phrase alone | Report episode length and phrase-position controls; a phrase-level effect inside a long episode may be swamped |
| Null result | inversion is not vocabulary | **Yes - at n=16 especially** | Branch D exists for this. Interval width reported before the point estimate |
| Six plants in predicted region | the mechanism is identified | Yes - six points can pattern by chance | Report all fact-bearing points; the six are an annotation, not the sample |
| Committed rarity scores | a valid rarity measure | Yes - IDF over this corpus is not general lexical rarity | State the measure's provenance and its known limitation: it already failed as a *ranking* signal here |

**Accepted residual:** even Branch B does not establish that retrieval is the cause.
It removes one alternative explanation. Say that wherever the result is cited.

## 1.5 Deliverables

- [ ] Decision rule committed before any coefficient is computed - SHA recorded
- [ ] Statement of which cosine ranks exist and which do not
- [ ] Correlation with interval, scatter, six plants marked
- [ ] Length and phrase-position controls
- [ ] Branch verdict
- [ ] PAPER-001 Sections 5.5.1 and 8.5 updated with the measured result, either way
- [ ] Ledger entry

---

# PART 2 - CHAINED RETRIEVAL (CONDITIONAL, UNAUTHORIZED)

> **This part is a proposal, not a plan.** It exists only if Part 1 returns Branch B
> *and* Muzaffer authorizes it. Do not implement, do not branch, do not scope sprints
> before both conditions hold.

## 2.1 The mechanism

**One retrieval system under different cue conditions, not two systems.**

The free-recall literature does not describe a targeted-recall mechanism and an
enumeration mechanism. It describes retrieval succeeding to the degree the cue
overlaps what was encoded (Tulving & Thomson, encoding specificity, 1973). Targeted
recall has a strong external cue. Free recall has almost none, so it manufactures
one: retrieve an item, and that item's context becomes the cue for the next.
Formalized in the Temporal Context Model (Howard & Kahana, 2002) and as repeated
sampling with cue update in SAM (Raaijmakers & Shiffrin, 1981).

**Architecturally:** retrieve, then use retrieved episodes as the next query, iterate
to a bounded depth, union the results, then select.

**Why this and not category cueing.** Bousfield (1953) showed free recall clusters by
category and that category cues outperform free recall. The architectural form of
that is: generate domain labels, retrieve per domain. **That is the topic layer**,
which collapsed 52 topics for one 120-turn conversation and 12 domains into 2 at
1,000 turns. It is in the graveyard with a scale failure attached. Chained retrieval
is the mechanism this program has *not* tried.

**Distinguish from E002.** E002 split the *query* into segments. This chains from
*retrieved episodes*. Different operation, different failure surface.

## 2.2 Prior art - scan owed before authorization

Pseudo-relevance feedback is the classical IR form of this and is decades old
(Rocchio; RM3). Query expansion from retrieved documents is standard. **The scan must
establish what is known about PRF's failure mode - query drift - before anything is
built**, and whether iterative retrieval has been reported on conversational memory
specifically. Unscanned as of this document.

**Do not claim novelty for chaining.** If E006 has a contribution it is the setting,
not the mechanism.

## 2.3 The two hazards, stated before design

**H-1 - Amplification of a bad first pass.** DR-002 measured that the four
highest-cosine episodes carry zero target facts. Chaining uses the first pass as the
cue for the second. **Starting wrong goes further wrong**, and query drift is PRF's
documented failure mode. Any design must include a first-pass quality gate.

**H-2 - The LV-001 exposure.** A3 preserved 16/16 targeted offline and scored 1.5/8
live. Chained retrieval adds machinery to the delivery path and carries the same
exposure. **Offline availability is not an acceptable primary outcome for Part 2.**

## 2.4 Non-negotiable design constraints

Registered now so they cannot be relaxed later.

1. **Live evaluation is the primary outcome.** Not availability. A mechanism that
   improves availability and is not run live has not been tested, per LV-001.
2. **The targeted bar is a kill.** Q1-Q8 must not fall more than 0.5 against the
   control, live. This is the LV-001 rule unchanged and it kills regardless of any
   breadth gain.
3. **The opening-turns probe is added.** LV-001's mechanism was legible: the coverage
   objective dropped the conversation's opening and the system reported having no
   record of it. That specific failure gets its own probe.
4. **Bounded depth, bounded cost.** Depth is a registered parameter with a stated
   latency budget. Measured, not projected - the CC-005 correction found a
   pre-registered projection running 84x past its data and understating cost 5x.
5. **No inference calls in the memory path.** The Study 005 principle, preserved
   across all eleven removals. Chaining must be embedding-only.
6. **Single new component.** Chained retrieval only. No coverage objective, no
   segmentation, no topic layer riding along.
7. **Multiple raters.** LV-001 ran one where the protocol asks for three, and said so.
   Part 2 does not repeat it.

## 2.5 What would make Part 2 not worth running

Record these now, before enthusiasm accrues:

- Part 1 returns Branch A or D.
- The prior-art scan finds chained retrieval reported on conversational memory with a
  negative result.
- The first-pass quality gate fails - if the first pass cannot surface *any*
  fact-bearing episode, there is nothing to chain from.
- Latency at bounded depth exceeds the interactive budget. The current selection cost
  is already 190 ms at 1,000 candidates with clustering at 81% and rising; chaining
  multiplies pool traversals.

---

## 3. Sequencing

1. **Part 1 (RD-001).** Hours. Offline. Gates everything.
2. **Muzaffer's authorization decision.** Explicit, on the record. Branch B is
   necessary and not sufficient.
3. **Prior-art scan.** Only if authorized.
4. **Part 2 pre-registration.** A separate document with its own gates, bars, and
   achievability check - not this one.

**One honest note on cost.** Part 2 is a multi-week research arc with a live-run
requirement, arriving after a decision to move toward a product. That trade is
Muzaffer's to make and should be made deliberately rather than by momentum. Part 1
is cheap enough that it need not be part of that decision.

---

*Drafted August 2, 2026. Part 1 authorized August 3, 2026. LV-001 PR #35:
A3 not promoted, B2 FAIL -2.0 live, B1 WEAK +1. Shipping default reverts to
per-item cosine ranking. AR-001: 14/17 at 5,058 of 32,000 characters. DR-002:
top four cosine episodes carry zero target facts; oracle episodes at ranks 14,
20, 22, 86, 112. DX-001: floor at 0.056 against 0.225 required.*
