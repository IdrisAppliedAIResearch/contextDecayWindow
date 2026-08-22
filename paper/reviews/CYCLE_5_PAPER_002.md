# PAPER-002 — Adversarial Review, Cycle 5

Target venue: arXiv cs.CL preprint. Scope-limited adversarial pass over the
material rewritten around HH-002: the **executive summary**, the **abstract's
HH-002 paragraphs**, and **§5.1–§5.9**, plus **§4.1** and **§13** read for
consistency with the new text. §§6–12 were read only where §5 touches them.
§14, §2.1, §1.2 and the two new figure captions are in scope because §5's claims
land there.

Bounds: `paper/notes/HH002_EVIDENCE_SPINE.md`,
`paper/notes/HH001_EVIDENCE_SPINE.md`, `paper/notes/EVIDENCE_SPINE.md`,
`paper/notes/COMPETITIVE_LANDSCAPE.md`, `paper/notes/DO_NOT_WRITE.md` (item 35
as amended 2026-08-21), `experiments/comparisons/hh_002/HH_002_PRE_REGISTRATION.md`,
and `AGENTS.md` §3, §8, §9. House format follows
`paper/reviews/CYCLE_3_PAPER_002.md`: numbered objections, each quoting the
condemned text, giving the reason, stating the required form.

**Overclaim and underclaim are weighted equally.** A result hedged into vagueness
is as defective as one overstated, and this cycle finds both.

**A note on the target.** `paper/PAPER_002.md` was being edited during this
review; three commits landed while the bounds were being read
(`cfc1c3da` → `0df44eaa` → `e8bf4039`), and several defects found early in the
pass were fixed before it ended. Every objection below is verified against a
pinned copy of the file at `e8bf4039` with a clean working tree —
SHA-256 `f22010eca470528770862c39b1a6e0de2724e963a1598cfeb163b67ce43d6e7b`, 1,995
lines. Line numbers are that file's. Edits after that commit are unreviewed. The
figure generator `scripts/generate_hh002_figures.py` is untracked and was also
being edited; it is cited as read at the same moment. Five things the in-flight
edits got right are recorded as credits, because the fastest way to lose them is
not to know they were load-bearing.

**Status: complete.** Twenty-four objections, five credits, dispositions below.

---

## Objections

### The shared axis — how the section reads to someone who did not run it

**1. The section's lead sentence and the abstract's rank this component against
seven rows nobody here ran. That is the claim item 35 forbids, in a grammar item
35 did not anticipate.**

> §5, line 525: "**This component scores 79.09% on LoCoMo — above every row of the
> table Mem0 published — on 4,243 prompt tokens against the 25,405 of full context
> reproduced here.**"
>
> Abstract, line 106: "It scores 79.09%, above every row of that table, on 4,243
> prompt tokens against the 25,405 of full context reproduced here. **None of the
> systems behind those rows was re-run.**"

`DO_NOT_WRITE.md` item 35 permits stating that this component scored 79.09% on the
same 1,540 questions, harness, prompt, judge and metric that produced Table 2, and
permits printing that table's rows beside it with attribution. It forbids "that
this component **beat**, **outperformed** or **trailed** Mem0, Zep, A-MEM, Mem0ᵍ or
OpenAI memory." The draft does not use those verbs. It uses a ranking predicate —
*above every row* — quantified over the whole table, which is the same proposition
with the verb removed. A reader who finishes that sentence believes this component
outperformed every system on Mem0's table. That belief is the thing the scope
exists to prevent, and the sentence produces it in the paper's two most-quoted
positions.

The disclaimer that follows does not repair it. It says none of those systems was
re-run — which concedes the premise and leaves the conclusion standing. And note
what changed in the executive summary between `0df44eaa` and `e8bf4039`: the
sentence "No sentence in this paper says the component beat Mem0" was removed and
replaced with a guarantee about *tests* ("no test in this paper is computed against
a quoted row", line 37). The guarantee was narrowed to the thing the draft still
satisfies. The claim that falsified the old guarantee was kept.

The defence is written down, in the figure generator that draws the same claim:

> `scripts/generate_hh002_figures.py:186` — "`"Row", not "system" -- none of the
> quoted systems was re-run, so the ordinal claim is over published numbers.
> DO_NOT_WRITE.md item 35.`"

That reasoning does not survive contact with three things. First, the rows in
both the table and the figure are labelled with system names, so an ordinal claim
over the numbers is read as an ordinal claim over the systems by every reader;
choosing the noun does not control the inference, and the scope exists to stop the
inference. Second, item 35's list is a list of claims, not of verbs — it forbids
the proposition that this component beat, outperformed or trailed those systems,
and "above every row of their table" is that proposition. Third, and substantively:
an ordinal claim over published numbers is only meaningful if those numbers are
commensurable with this one, and this study tested commensurability **twice**. On
full context it held to 0.43 points. On RAG it failed by 14.75. The rig's agreement
with that table is **demonstrated for one row and refuted for another**, and a
blanket "above every row" claims agreement with all seven on the strength of one.
The registration lists a further reason for care: upstream pinned the moving
`gpt-4o-mini` alias and this study pinned `gpt-4o-mini-2024-07-18`
(`HH_002_PRE_REGISTRATION.md` §8), so the weights that produced Table 2 are not
identifiable from here.

**Required form.** State the score, the axis and the licence, and let the printed
table do the ranking: *this component scores 79.09% on all 1,540 scored LoCoMo
questions, on the harness, answer prompt, judge and metric that produced
arXiv:2504.19413's Table 2, at 4,243 mean prompt tokens; Table 2's rows are printed
beside it with attribution and were not re-run here.* Delete "above every row" from
§5's lead, the abstract and the figure. If the paper wants a comparative sentence,
it has one it actually ran: the registered contrast against fixed-chunk RAG, and
the post-hoc contrast against full context reproduced here.

---

**2. The count of quoted rows is wrong at four sites, and the row it loses is the
one the entire section stands on.**

> Exec, line 35: "Every row but this component's and the floor is quoted from Table
> 2 and was **not** re-run here"
>
> Exec, line 79: "Six of the rows above were not run here"
>
> Abstract, line 111: "Six of the table's rows were not re-run and are quoted with
> attribution"
>
> §5.1, line 568: "Five of the **six** quoted rows…"
>
> §5.9, line 794: "**Six of the eleven rows in §5.1 were not run here.**"

§5.1's table has eleven rows. Four are measured here — this component, full context
reproduced here, this component with undated turns, and the floor. **Seven** are
quoted from Table 2: full context 72.90%, Mem0ᵍ, Mem0, Zep, RAG best variant,
OpenAI memory, A-MEM. The draft says six at three sites and, at line 35, says
something different again — that only two rows are measured here, which
mis-attributes the reproduced full-context row to Table 2 in the one sentence whose
whole job is attribution. Two counts of the same table in one executive summary,
and neither is right.

The provenance of "five" and "six" is traceable: `experiments/comparisons/hh_002/RESULTS.md`
prints a table with five quoted rows and says "Five rows are the Mem0 authors'
reproductions of other people's systems." §5.1 then added full context and RAG as
quoted rows and did not update the count. The row that falls out of the count is
the published **72.90%** — the row G-CTRL was registered against, the row §5.2
calls the licence for printing the rest. Losing it from the tally is not
arithmetic; it is losing track of which number was inherited and which was
measured, in the section whose thesis is that the difference matters.

**Required form.** Seven quoted, four measured, eleven rows, stated once and
identically at all four sites. And at line 35: *three of the eleven rows were
measured here — this component, full context reproduced here, and the floor; the
undated arm is measured here too* — or simply give the executive table the Source
column §5.1's table already has.

---

**3. "Five of the six quoted rows are the Mem0 authors' reproductions of other
people's systems" is contradicted by the Source column six lines above it.**

> §5.1, line 568: "Five of the six quoted rows are the Mem0 authors' reproductions
> of other people's systems. Zep's own paper reports DMR and LongMemEval and never
> LoCoMo."

The table's own Source column marks exactly two rows that way: Zep, "run by Mem0,
not by Zep", and A-MEM, "run by Mem0, not by A-MEM". OpenAI memory is a third by
the same logic. The other four are not other people's systems at all: Mem0 and
Mem0ᵍ are the Mem0 authors' own system, and full context and RAG are the Mem0
authors' own baselines. The sentence therefore does two things at once — it
overstates the count and it launders four rows into a category ("someone else's
system, run by a competitor") that reads as *treat these numbers with suspicion*.
The error runs in the direction that flatters this paper, which is the diagnostic
Cycle 3 applied to the old executive summary.

`HH_002_PRE_REGISTRATION.md` §9 carries the same slip ("five of the seven rows"),
so the draft inherited it rather than inventing it. That does not make it true.

**Required form.** Say what the Source column says: *of the seven quoted rows, two
are Mem0's own system, two are the Mem0 authors' own baselines, and three are the
Mem0 authors' runs of systems built by other groups — Zep, A-MEM and OpenAI memory
— not those groups' own reports.* Keep the Zep sentence; it is correct and it is
sourced to `COMPETITIVE_LANDSCAPE.md`.

---

**4. "The benchmark arms above carry the first three and not the fourth" is false.
They carry one.**

> Exec, line 76: "**The benchmark arms above carry the first three and not the
> fourth.**"

The four parts named two sentences earlier are an append-only verbatim store, a
recency window, cosine-threshold similarity retrieval, and the set-level coverage
objective. `src/analysis/hh002_arms.py` is the arm: `build_pair_candidates` cuts
the conversation into non-overlapping adjacent-turn pairs, `rank_pairs` scores every
pair by cosine and sorts by `(-score, session_order, pair_order)`, and `_pack_texts`
fills 16,000 characters greedily. **There is no recency tier in that path and no
cosine threshold** — `rank_pairs` takes no threshold argument and discards no
candidate; the budget is what stops the fill.

§5's own scope paragraph gets this right twelve lines into the section: "The arm
under test is NF-004's pair ranking at a 16,000-character budget, without §3's
set-level coverage objective" (line 546). The executive summary claims three of
four components ride on the benchmark result; the section claims one. This is
Cycle 3's objection 1 recurring on new material — a result earned by one parameter
attached to the architecture — and it matters more here than it did there, because
79.09% is the number a reader will carry away.

**Required form.** *The benchmark arms carry NF-004's pair ranking and a greedy
character-budget pack. The recency tier, the cosine threshold and the coverage
objective are not in that path, so nothing in §5 is evidence about them.* One
sentence, and it is already written in §5.

---

**5. The executive summary calls §5 a head-to-head fifty lines after saying it is
not one, and the section heading agrees with the wrong half.**

> Exec, line 37: "**This is placement on a shared axis, not a head-to-head**"
>
> Exec, line 88: "**The rest of the paper.** §5 is both head-to-heads in full."
>
> §5 heading, line 523: "## 5. The head-to-head: Mem0's benchmark, and Mem0 run
> here"

HH-001 is a head-to-head: two memory layers, one reader, one budget, 300 items,
paired. HH-002 is not, and the paper says so. Putting both under one noun in the
section title and again in the summary's closing paragraph re-authorizes the
reading the disclaimer disavows, and it does so in the two places a skimming
reader looks. The current heading is also the phrase a hostile citation will use:
*the paper's own §5 is titled "The head-to-head".*

**Required form.** Title the section for what it contains — *"Mem0's benchmark, and
Mem0 run here"* — and at line 88, *"§5 has both studies in full: the placement on
Mem0's published benchmark, and the head-to-head against Mem0 run here."* The word
"head-to-head" belongs to HH-001 and nowhere else.

---

**6. The floor's reach is marked as an inference in §5.3 and asserted as a fact in
the executive summary, the abstract and Figure 1's caption.**

> §5.3, lines 623–626 — correct: "That prompt, that model and that question set produced
> every row of Table 2, so the floor is a property of the benchmark rather than of
> any system standing on it, and **it sits under all of them**. That last step is an
> inference from shared instrumentation, not an observation: those runs were not
> watched."
>
> Exec, line 53: "That prompt, model and question set produced every row above, so
> the floor sits under all of them."
>
> Abstract, lines 117–118: "That floor is a property of the shared instrument and the
> source paper does not report it."
>
> Figure 1 caption, lines 1755–1756: "because the judge prompt, model and question set are
> shared, that floor sits under every bar in the chart."

§5.3's marker is the model form and it should be quoted back to the other three
sites verbatim. What the rig measured is that *this* answerer and *this* judge score
26.30% on an empty context. That the same holds inside runs performed by another
team, on a moving model alias, at a date this programme cannot reconstruct, is an
inference from shared instrumentation — a good one, and still an inference. Three
of the four statements of it drop the qualifier, and the one that drops it in a
figure caption is the one most likely to be reproduced without the section around
it.

The premise is also slightly stronger than the evidence: the paper reproduced the
prompts byte-exact from the upstream blobs, but `HH_002_PRE_REGISTRATION.md` §8
records a dated model pin against upstream's moving alias, so "that model" is not
established to be the same model.

**Required form.** Carry §5.3's second sentence, unchanged, to the executive
summary, the abstract and Figure 1's caption. Where the premise is stated, say
*the same prompts, byte-exact, and the same question set; the answerer and judge
are the same alias pinned to a date, which their run was not.*

---

### §5.1 — the table and what the prose does to it

**7. The sentence under the table converts a Source column into a leaderboard, and
attributes a token count measured here to a row that was not.**

> §5.1, line 573: "The component's row sits above every quoted row, and it does so
> at a sixth of the prompt tokens of the arm that **previously topped the table**."

"Previously topped the table" asserts that something now tops it, which is
objection 1 in miniature and in a place the disclaimer does not reach — the
sentence immediately after the table, where a reader looks for the takeaway.

The second half misattributes. The arm that tops Table 2 is the published
72.90% row, and Table 2 publishes no prompt-token count for it; the table prints
"—" in that cell. 25,405 is the mean prompt tokens of **full context reproduced
here** (`HH002_EVIDENCE_SPINE.md` §6, `A_FULL`). The abstract was corrected for
exactly this defect at `e8bf4039` — it now reads "against the 25,405 of full
context reproduced here" — and §5.1 was not.

**Required form.** *At 4,243 mean prompt tokens, this component's row sits at a
sixth of the 25,405 that full context reproduced here spends.* Then the post-hoc
contrast, already correctly labelled in the next paragraph. Delete the ranking
clause; Figure 1 and the table show the placement without the paper asserting it.

---

**8. "The registered contrast is §5.4's" points at a subsection that does not
contain it.**

> §5.1, line 584: "The registered contrast is §5.4's."

§5.4 reports the G-CTRL miss, the sweep and two post-hoc contrasts. The registered
contrast — `A_CDW` > `A_RAG`, `HH_002_PRE_REGISTRATION.md` §7's H1, the study's
only directional claim — appears in §5.9, at line 800. A reader following the
pointer lands on a `DESCRIPTIVE` diagnostic and a failed gate and concludes that
*that* is what was registered.

**Required form.** Point at where the number is, and better, put the number where
the pointer is — see objection 9.

---

**9. UNDERCLAIM. The study's one registered directional claim passed, decisively,
and the paper reports it once, as a caveat, stripped of every number that makes it
a result.**

> §5.9, line 799: "**The lead over full context was not registered.** §5.1 states it
> and labels it. The registered contrast is the component against fixed-chunk RAG,
> at +33.31 points."

Against this, count what the post-hoc contrast receives: the section's opening
sentence, a full paragraph in §5.1, two effect sizes and two p-values
(6.62 points, 210/108, p = 5.593e-09; +15.32 on the deterministic endpoint,
p = 9.309e-31).

Now the registered one, from `HH002_EVIDENCE_SPINE.md` §5: `A_CDW` > `A_RAG` on
`llm_score`, **+33.31 points, 558 gains against 45 losses, one-sided exact
p = 6.615e-114**, standing `REGISTERED-LIVE`; and on the model-free `f1` endpoint
**+24.16, 433 gains against 61, p = 1.949e-70**. The registration required both
endpoints to agree in sign before any directional claim could be made
(`HH_002_PRE_REGISTRATION.md` §7, H1). They agree. The bar was declared reachable
and reversible at n = 1,540 before the run. It passed.

`AGENTS.md` §9 is explicit that reporting a finding as less than it is throws the
finding away. This is the only pre-registered directional prediction in either
head-to-head study, it was locked before the first generation call, and the paper
gives it eleven words inside a list of boundaries. That is the single largest
underclaim in the section.

One caveat must travel with it, and its absence is the objection's other half: the
control in that contrast is the same `A_RAG` arm that missed its own reproduction
target by 14.75 points, and the sweep in §5.4 shows a better member of the family
at 65.32%. Stated honestly, the registered claim passed against a control this
study then showed to be mis-specified — and the post-hoc contrast against the
sweep's best variant, +13.77, is the number that covers the gap.

**Required form.** Give H1 a paragraph in §5.4, where the RAG arm already lives:
*the study registered one directional claim — this component above fixed-chunk RAG
on `llm_score`, paired by item, one-sided exact binomial, with both endpoints
required to agree. It passed: +33.31 points, 558 gains against 45, p = 6.615e-114,
with the model-free F1 endpoint agreeing at +24.16, p = 1.949e-70. The control is
the arm that missed its reproduction target by 14.75 points; against the best
variant the sweep found, the margin is 13.77 points.* Then §5.1's pointer resolves,
and §5.9 can keep its one-line summary.

---

### §5.2 — the licence

**10. UNDERCLAIM. The 0.43-point reproduction is the fact that licenses the whole
section, and the paper never names it as G-CTRL, never says which half of that gate
it is, and never assembles the gate's verdict in one place.**

> §5.2, lines 597–601: "Half a point on a 1,540-question benchmark, reproducing a figure
> published by a different team on different hardware. On the one row where nothing
> can be misconfigured, the corpus adaptation, the prompt reconstruction, the judge
> and the metric all land where theirs did. That is what puts this component's
> number on the same axis as the rest of the table — placement, and nothing more."

The paragraph is good. It is also the only place the reproduction appears, and it
never says the word G-CTRL, so a reader cannot connect it to §5.4's "**G-CTRL
failed**" two subsections later. As written, the paper reports a gate failure whose
other half is never identified as the same gate. `HH002_EVIDENCE_SPINE.md` §4
prints both rows under one heading and one verdict: `A_FULL` −0.43 within, `A_RAG`
−14.75 not within, **G-CTRL: FAILED**. A reviewer reading the paper alone cannot
reconstruct that.

The under-claiming is the larger half. The registration says a headline number from
a widely-cited paper failing to reproduce is worth publishing; the mirror is worth
publishing too, and the paper owns it: on the one row of Table 2 that has nothing
to configure, an independent rig, different hardware, a reconstructed prompt chain
and a re-pinned judge landed **0.43 points** away, with the judge itself moving
0.06 points across two scorings of the same sealed answers. That is the strongest
externally checkable claim in the document and it is delivered in a subordinate
clause.

**Required form.** Name the gate and give both halves in §5.2: *G-CTRL registered
two reproduction targets at ±3.0 points, fixed before any number existed. Full
context reproduced at 72.47% against 72.90% — 0.43 points, inside tolerance. RAG at
500/k=1 did not (§5.4), so the gate's verdict is FAIL, and the axis this section
uses is the one the passing half licenses: the row with nothing to configure.*
Then §5.4's "G-CTRL failed" reads as the same object rather than a second one.

---

### §5.3 — the floor

**11. "Its own paper never reports" is a claim about a paper this programme did not
audit.**

> §5.3 heading, line 606: "### 5.3 LoCoMo has a 26-point floor that its own paper
> never reports"

What the evidence supports is that **arXiv:2504.19413 reports no floor** — that is
what `HH002_EVIDENCE_SPINE.md` and `HH_002_FINDINGS.md` §4 say, and the body says
it correctly. "Its own paper" points at Maharana et al. 2024, the LoCoMo paper,
which is a different document; `COMPETITIVE_LANDSCAPE.md` entry 11 records that
paper's venue and its two disagreeing abstracts and records no check for a
no-memory baseline in it. The heading is an unsourced universal of the species
Cycle 3 objection 8 and 11 caught twice before, and it is unnecessary: the sourced
version is equally strong.

**Required form.** *"LoCoMo has a 26-point floor, and the paper that published the
table does not report it"* — the wording the draft had two commits ago, which is
exactly what the spine supports.

---

**12. §5.3 calls the floor a property of the benchmark; §5.6 calls it a property of
the reader and the grader. Both are in §5, and §5.6 is right.**

> §5.3, line 624: "the floor is a property of the benchmark rather than of any
> system standing on it"
>
> §5.6, lines 731–734: "The floor arm scored **zero** here. That is the one number
> HH-002 overturned… **The floor is a property of the reader and the grader, not of
> the corpus.**"

HH-001's no-memory arm scored 0.000 on the same corpus. The floor is 26.30% with
GPT-4o-mini answering and GPT-4o-mini judging under the vendor's generous prompt,
and 0.000 with a local 27B reader under this programme's judge. §5.6's sentence is
the one the two studies jointly establish, and it is the sharper finding — the
number moves the whole way from 0 to 26.30 on the reader/judge pair alone. §5.3's
sentence generalizes it to "the benchmark", and the heading generalizes further to
LoCoMo the corpus, which §5.6 then refutes eleven paragraphs later.

**Required form.** In §5.3: *the floor is a property of the instrument — this
answerer, this judge, this prompt — and not of any system standing on it; because
Table 2's rows were produced with that instrument, the same floor sits under them,
an inference from shared instrumentation.* Then §5.6's paragraph confirms it
instead of contradicting it, and can say so.

---

**13. The stratum with the highest floor is the one stratum the paper does not
print, and the deflation is applied to everyone else's rows.**

> §5.3, line 628: "The floor is not uniform either — **32.34% on open-domain**, 841
> of the 1,540 questions and the largest stratum by far, against **11.21% on
> temporal**. A benchmark whose biggest category is a third answerable by guessing
> measures less than its headline suggests, and **every system quoted on it inherits
> that**."

Two defects, both directional.

First, the floor by stratum is 21.28 / 11.21 / **38.54** / 32.34
(`HH002_EVIDENCE_SPINE.md` §3b). The highest is multi-hop at **38.54%** — the
category where guessing should be hardest, and the one where this component and
full context both score 55.21%, leaving 16.67 points of headroom above an empty
context. The paper prints the largest stratum and the smallest floor and omits the
largest floor. It is the number a hostile reader will find first, it complicates
the guessability account, and it is one cell of a table the paper already has.

Second, "every system **quoted** on it inherits that". The deflation is scoped to
the rows this paper did not run. This component's 79.09% sits on the same
instrument and inherits the same generosity — `AGENTS.md` §3's surrogate rule is
precisely that a rubric score can pass without the property it certifies, and §5.3
has just demonstrated the mechanism on its own judge. The paper does supply the
honest version in the table below (52.79 above the floor), but the sentence that
names who is affected leaves itself out.

**Required form.** Print all four strata, name 38.54% on multi-hop as the highest
and say what it does to the headroom there, and end the sentence *"and every row on
it inherits that, this component's included."*

---

### §5.4 — the RAG miss

**14. "The published 60.53% sits inside it" is an interval statement doing the work
of a reproduction. No configuration reproduced that row.**

> §5.4, line 663: "**The sweep spans 26 points — wider than the gap between the top
> and bottom halves of Table 2 — and the published 60.53% sits inside it.** A row
> that moves that far on a configuration choice names a family, not a number."

The four sweep values are 65.32, 50.65, 45.78, 39.16. The nearest to 60.53 is
65.32, **4.79 points away** — outside the registered ±3.0 tolerance. The second
nearest is 9.88 points away. So the correct statement is that the published value
falls *between* two configurations this rig ran and was *reproduced by none of
them*. As written, a reader concludes the family explanation settles the miss; it
does not, and the difference is the whole question of whether §5.4 is an account or
a rescue.

The section is otherwise honest about this — "The explanation does not cancel the
failure" (line 667) is exactly right, and is credited below. This one sentence
undoes it, because it is the sentence that carries the explanation.

A rider: the heading's "more than the table's whole spread" is checkable and true
(26.16 against 24.52 from 72.90 to 48.38), but the body's "wider than the gap
between the top and bottom halves of Table 2" is not a defined quantity. Use the
heading's version in both places.

**Required form.** *Four configurations were run and none reproduces 60.53% within
the registered ±3.0 tolerance; the published value falls between the best variant
found here (65.32%) and the next (50.65%). The row names a family this rig can
bracket but did not hit, and the gate stays failed.*

---

### §5.5 — the timestamp ablation

**15. "Less than the judge's own run-to-run spread" is contradicted by the only
spread the paper states.**

> §5.5, line 694: "**The whole overall gap is one stratum**, and Figure 2 shows it.
> The other three move by less than the judge's own run-to-run spread in two cases
> out of three."

The only judge spread in the paper is §5.2's: **0.06 points**, three items of
1,540. The three deltas are −0.71, −2.08 and +0.36. All three exceed 0.06. Under
the sentence as written, the count is zero out of three, not two.

There is a defensible computation behind the claim and the paper does not show it:
three flipped items scale differently per stratum — 3/96 = 3.13 points on
multi-hop, 3/282 = 1.06 on single-hop, 3/841 = 0.36 on open-domain. On that
reading, −0.71 and −2.08 sit inside their strata's bound and +0.36 sits exactly at
it, which is "two cases out of three" only by rounding. A reader cannot reconstruct
any of this from the text.

**Required form.** Either show the per-stratum bound — *three judge flips is up to
3.13 points at n = 96 and 0.36 at n = 841, so two of the three non-temporal deltas
fall inside their stratum's judge bound and open-domain sits at it* — or state the
deltas flatly and say the per-stratum judge spread was not measured. The finding
(one stratum carries the whole effect) survives either way.

---

**16. The dated/undated arms were registered; the contrast between them is post-hoc,
and the prose does not distinguish them.**

> §5.5, line 683: "HH-002 ran both renderings, **registered in advance**, and
> predicted the gap would sit in the temporal category."

`HH_002_PRE_REGISTRATION.md` §5 registers `A_CDW_NOTS` as a secondary **arm**; §7
registers exactly one directional **claim**, and it is not this one.
`HH002_EVIDENCE_SPINE.md` §5 accordingly marks `A_CDW` vs `A_CDW_NOTS` **post-hoc**
at +7.53. The draft attaches "registered in advance" to a sentence whose object is
the gap, three lines above a table of that gap — and §5.1 labels its own post-hoc
contrast scrupulously in the equivalent position. The two subsections do not treat
the same situation the same way.

The underclaim rides along: prediction 5 of the registration named the direction
*and the stratum*, sealed before the run, and it came true at +36.45 on temporal
with nothing elsewhere. Registration §10 says predictions carry no standing, which
is the honest frame — and a sealed prediction that specific, hitting that
precisely, is worth stating with the frame attached rather than blurring into
"registered in advance".

**Required form.** *Both renderings were registered as arms; the contrast between
them is post-hoc. Prediction 5, sealed before the run, named the direction and the
temporal category, and carries no standing by the registration's own terms — it
landed at +36.45 on temporal and inside the judge's own bound on the rest.*

---

### §5.9 and the figures

**17. Figure 1's caption asserts a shared measurement over the rows it then says
were not measured, and the rendered image carries the ranking claim in its title.**

> Figure 1 caption, line 1749: "*Every system scored on the same 1,540 LoCoMo
> questions, the same harness, the same judge.*"
>
> `scripts/generate_hh002_figures.py:191` — the on-canvas title:
> `f"{rate('A_CDW'):.2f}% — above every row of the table Mem0 published"`

The caption's italic line is the strongest form of the head-to-head claim in the
document: it says all eleven bars were *scored* on the same questions, harness and
judge. Four were. The caption itself concedes this three sentences later ("Grey
rows are quoted from Table 2 and were not re-run"), so the caption contradicts
itself inside eight lines, and the half a reader keeps is the italic one because it
sits directly under the title.

The figure's own title is worse, because it travels furthest from the paper. A PNG
lifted into a slide or a thread carries the title and the legend and nothing else,
and its title makes the comparative claim of objection 1 with no attribution
attached — in a figure whose bars are labelled "Mem0", "Zep" and "A-MEM", which is
where the "row, not system" defence finally fails. The figure's construction is
otherwise the best work in this material — measured rows and quoted rows are
colour-separated, the legend reads "arXiv:2504.19413 Table 2, quoted with
attribution", the floor is drawn across everything, and the title is composed from
the measured value rather than typed — which is exactly why the sentence template
should not undo it. Only the template needs to change.

A rider on provenance: the Figures preamble says each caption carries its artifact
hashes and that `figure_manifest_002.json` "records all 33 inputs", but Figures 1
and 2 are recorded in a second manifest, `figure_manifest_hh002.json`, which the
preamble does not name.

**Required form.** Retitle the figure to what it shows — *"Where this component
lands on the table arXiv:2504.19413 published"*, the caption's own headline — and
rewrite the italic line as *"This component and three controls scored here on the
1,540 LoCoMo questions of arXiv:2504.19413's harness; the grey rows are quoted from
its Table 2 and were not re-run."* Name the second manifest in the preamble.

---

**18. §5.1 reproduces Table 2 minus one row, silently, while the section quantifies
over "every row of that table".**

> §5.1's table, lines 554–566 — seven quoted rows, no LangMem.

`COMPETITIVE_LANDSCAPE.md` §2 lists **LangMem at 58.10%** among Table 2's LoCoMo
rows, with the caveat that it is the Mem0 authors' run and that LangMem has no
resolvable publication. The word "LangMem" appears nowhere in the paper at
`e8bf4039`. Dropping it does not change any ranking — it sits below this component
— but a paper that reprints a published table and asserts a property of *every row*
of it must reprint every row or say which it omits and why. The landscape file
supplies the why in one clause.

**Required form.** Add the row with its attribution, or add a line under the table:
*"Table 2's LangMem row (58.10%) is omitted here; `COMPETITIVE_LANDSCAPE.md` records
that no LangMem publication could be resolved, and it is citable only as a baseline
inside Mem0's table."*

---

### Consistency with §4.1, §13, §14, §2.1 and §1.2

**19. §4.1's assignment table claims to be complete and has no HH-002 row.**

> §4.1, line 444: "**The assignment, in full, so this table is checkable without
> leaving the paper.**"
>
> Line 448, the only §5 entry: "| HH-001 — head-to-head against Mem0, +7.7 points
> (§5) | REGISTERED-LIVE | This reader, this corpus, this budget, this pair of
> configurations. Never confirmation |"

Eighteen results are graded and the one supplying §5.1's headline is not among
them. HH-002 has a standing — `REGISTERED-LIVE`, assigned in
`HH002_EVIDENCE_SPINE.md` §3 for five arms — and the RAG sweep has another,
`DESCRIPTIVE`, which §5.4 states in prose. §4.1 was Cycle 3's most serious ask and
Cycle 4's best-repaired section; shipping the new headline outside the machinery
built to grade it is the one thing that undoes both. It is also the table a hostile
reviewer will check first, precisely because the paper invites them to.

**Required form.** Two rows, in the same voice as the others:
*HH-002 — this component on the published LoCoMo table, 79.09% (§5.1) |
REGISTERED-LIVE | One replicate per arm; corpus exhausted; the one registered
directional claim is against fixed-chunk RAG. The 6.62 over reproduced full context
is post-hoc and its sign was mispredicted*, and *HH-002 RAG sweep, 39.16–65.32%
(§5.4) | DESCRIPTIVE | Built after the registered target missed; no configuration
reproduces the published row within tolerance.*

---

**20. §13.10 says LoCoMo was read twice. HH-002 is the third read and by far the
largest.**

> §13.10, lines 1641–1644: "**LoCoMo is now spent too**: NF-004 read the six holdout
> conversations and HH-001 read them again. §5 is `REGISTERED-LIVE` for that reason
> and cannot become confirmatory."

HH-002 read **all ten conversations and all 1,540 scored questions**. The
subsection's own conclusion is strengthened by it and the subsection does not know
it happened. "§5 is `REGISTERED-LIVE`" is now singular where §5 holds two studies,
and §5.9 already says "both studies are `REGISTERED-LIVE`". A limitations section
that has not been re-read against the new material is exactly the failure
`AGENTS.md` §9.1 names: a blocking claim carried forward after the evidence beneath
it changed.

**Required form.** *NF-004 read the six holdout conversations, HH-001 read them
again, and HH-002 read all ten and every scored question in them. Both studies in
§5 are `REGISTERED-LIVE` for that reason and neither can become confirmatory.*

---

**21. §14 says the programme has not shown that any of it makes a reader answer
better. §5 measures a reader answering, on 1,540 questions, and the executive
summary says so.**

> §14, line 1703: "**What this programme has not shown** is that any of it makes a
> reader answer better. Availability and correctness were measured moving in
> opposite directions once, and that result stands unrescued."
>
> Exec, line 84: "LoCoMo fits a modern context window, so this measures cost and
> **accuracy**, not reach"

Both head-to-heads score end-to-end answers. HH-002's registered contrast is a
reader-accuracy contrast at +33.31 points; HH-001's is +7.7 with a deterministic
endpoint agreeing. The conclusion's sentence was true of the arc before §5 existed
and is now contradicted by the section the paper opens with.

The precise claim §14 wants is still available and is narrower: no experiment here
shows that **the availability gains measured offline** — 12 → 14 of 17, 843 → 935
of 1,098 — convert into better answers; LV-001 is the one attempt and it failed its
own bar. That is a statement about the *offline-to-correctness link*, not about
whether the layer helps a reader at all.

**Required form.** *What this programme has not shown is that the offline
availability gains convert: no experiment here connects an availability
improvement to a correctness improvement, and the one that tried failed its own
registered bar. §5 measures answers directly and finds the layer ahead of its
controls; it does not isolate which component earned that.*

---

**22. §14 and §1.2 do not mention HH-002 at all, and §14 still opens on the count
`DO_NOT_WRITE.md` retired.**

> §14, line 1650: "**Eleven pre-registered efforts** produced one architecture worth
> keeping…"
>
> §1.2's five contributions: the granularity rule, the decomposition, the known
> optimum, the subtraction result, the correction record.

Three defects in one place.

The count is Cycle 4's objection 2, still open at the site Cycle 4 flagged, and it
is now wrong in a second direction: HH-001 and HH-002 are both pre-registered with
commitments hashed before the first generation call, so "eleven pre-registered
efforts" undercounts registered work while using the phrasing
`DO_NOT_WRITE.md` §1 #8 retired.

The conclusion's competitor paragraph reports HH-001 ("On 300 questions, one reader
and a matched budget…") and nothing from HH-002 — no 79.09%, no 1,540 questions, no
0.43-point reproduction, no floor, neither failed gate. A reader who reads the
abstract and the conclusion, which is most readers, gets the paper's largest
evaluation from the abstract only.

The contributions list has the same hole. If placement on a published benchmark
with a reproduced control is a contribution, list it with its standing; if it is
not, §5's lead sentence should not be the loudest claim in the document.

**Required form.** Fix the count ("ten numbered studies, one registered exploratory
bakeoff, and two registered head-to-head studies", or drop the number). Add one
contribution to §1.2 naming the reproduction, the placement and the floor, with
`REGISTERED-LIVE` attached. Add two sentences to §14's practitioner section: the
0.43-point reproduction and what it licenses, and both failed gates.

---

**23. §2.1 refuses a comparison the paper now makes properly. UNDERCLAIM.**

> §2.1, lines 283–286: "Placing those two in one column would be exactly the substitution
> this programme's own operating manual names as its recurring failure — *a
> surrogate that can pass without the property it claims to certify*. **We do not
> place them in one column.**"

That paragraph was written when this programme had only deterministic evidence
availability to offer against everyone else's judged accuracy, and it was right.
HH-002 changed the fact: the component now has a judged-accuracy number produced by
the same harness, prompt, judge and metric, with the ceiling row reproduced to 0.43
points. §5.1 places it in one column with theirs, correctly, and §2.1 — the section
whose job is to say what is and is not comparable — still tells the reader the paper
refuses to.

The surrogate warning is not obsolete; it applies to the *availability* numbers,
which still must never share a column with a judged score. The paragraph now needs
to distinguish two measures rather than refuse one.

**Required form.** *Two measures are reported here. Judged answer accuracy on
LoCoMo is comparable to Table 2's column and is placed there, because the harness,
prompt, judge and metric were reproduced and the ceiling row came back within 0.43
points (§5.2). Deterministic evidence availability is not comparable to it and
never shares a column with it: 935 of 1,098 is not a score.*

---

**24. Nothing separates §5's 79.09% from §6.1's 935 of 1,098, and they are now
adjacent.**

`COMPETITIVE_LANDSCAPE.md` §3.2 names the exact sentence this arrangement invites —
"Any sentence pairing a published LoCoMo or LongMemEval score with an NF-004,
NF-005, EC-001 or DMR-001C number, however hedged… the corpus name is shared and
the endpoint is not. This is the specific sentence a reader will construct if the
paper leaves the two adjacent." §5 ends at line 812 and §6.1's sealed-holdout
result opens at line 822. Both say LoCoMo. One is a judged answer rate over 1,540
questions; the other is a count of records whose evidence text was present in a
delivered block, with no model in the loop. The paper never says they are different
quantities, and §5's scope paragraph names NF-004 as the arm under test, which
makes the collision likelier rather than less likely.

**Required form.** One sentence at the end of §5 or the start of §6: *the 79.09%
here and the 935 of 1,098 in §6.1 are different endpoints on the same corpus — a
judged answer rate against a deterministic count of evidence availability — and
neither converts into the other.*

---

## Credits — five things the rewrite got right that must not be lost

**C1. §5.3's contamination sentence is the model form for the whole paper.**

> "Guessability alone accounts for it, without any need to suppose the model has
> seen the corpus… **No contamination probe was run against this reader, so
> contamination is unmeasured here rather than excluded.**"

The registration pre-committed the opposite reading — above 5% "means gpt-4o-mini
knows the corpus". The draft states its alternative account, and then states that
the registered account was not tested. That is what a claim looks like when the
author knows which way the error cuts. One addition would strengthen it at no cost:
`A_NONE` scores exact_match 0.71% and f1 0.153 (`HH002_EVIDENCE_SPINE.md` §3), which
is evidence against literal recall and is already in the spine.

**C2. "The explanation does not cancel the failure" (§5.4, line 667)** — the
sentence that keeps §5.4 an account rather than a rescue. Objection 14 is about the
one clause that pulls the other way; this sentence is why the rest of the
subsection survives the charge.

**C3. §5.4's granularity hedge.** "Size and count move together here, so this does
not isolate which one carries it; it points the same way as §7 through a mechanism
§7 never tested, and **inherits none of §7's standing**." An earlier draft credited
this post-hoc, `DESCRIPTIVE`, single-replicate contrast to §7's result. The hedge
names the confound and refuses the transfer. Keep the wording; note only that §7's
own standing is `REGISTERED-OFFLINE` and `DESCRIPTIVE` per §4.1 — the confirmatory
result is §6.1's — so if a later edit reaches for "§7's confirmatory standing", it
is reaching for something §4.1 denies.

**C4. §5.3's floor table is restricted to rows measured here, and says why.** "Only
rows measured on this rig appear in that column… subtracting it from a row whose
strata were never published would be arithmetic wearing the clothes of a
measurement." This is `DO_NOT_WRITE.md` item 35's third prohibition honoured
exactly, including the reason. 40.58 appears nowhere in the document.

**C5. The costs that run the other way are stated at full strength.** §5.7's
"Mem0 is the cheapest memory arm per question — 3,392 prompt tokens against this
component's 4,009", §5.8's storage and replicate-agreement paragraph, and the
executive summary's "Two other arms beat this component on cost". Underclaim and
overclaim being weighted equally cuts both ways, and this is the paper reporting
against itself without cushioning.

---

## Dispositions — Cycle 5

Twenty-four objections: fourteen overclaim or accuracy, five underclaim, five
contradiction or structural. Five credits recorded.

| # | Section | Objection | Kind | Recommended |
|---|---|---|---|---|
| 1 | §5 lead, abstract | "Above every row of that table" — a ranking predicate over seven unrun rows | **Forbidden (item 35)** | **ACCEPT — most serious.** Delete. State score, axis, licence; let the table rank |
| 2 | Exec ×2, abstract, §5.1, §5.9 | Quoted rows counted as six; there are seven, and the lost row is the licence row | Accuracy | **ACCEPT.** Seven quoted, four measured, one number at all sites |
| 3 | §5.1 | "Five of the six quoted rows are… other people's systems" contradicts the Source column | Accuracy | **ACCEPT.** Two own-system, two own-baseline, three third-party |
| 4 | Exec | "Carry the first three and not the fourth" — the arm carries one | Overclaim | **ACCEPT.** `hh002_arms.py` has no recency tier and no threshold. Use §5's own scope sentence |
| 5 | Exec, §5 heading | "Both head-to-heads" against "not a head-to-head" | Contradiction | **ACCEPT.** Retitle §5; reserve the word for HH-001 |
| 6 | Exec, abstract, Fig 1 | The floor's reach asserted where §5.3 marks it an inference | Overclaim | **ACCEPT.** Carry §5.3's sentence to all three |
| 7 | §5.1 | "Previously topped the table"; 25,405 attributed to a quoted row | Overclaim + accuracy | **ACCEPT.** The abstract's corrected wording already exists |
| 8 | §5.1 | "The registered contrast is §5.4's" — it is in §5.9 | Broken pointer | **ACCEPT.** Resolve by moving the result into §5.4 |
| 9 | §5.1 / §5.9 | H1 passed at +33.31, 558/45, p = 6.615e-114, both endpoints agreeing — reported as a caveat | **Underclaim** | **ACCEPT — most serious underclaim.** Give it a paragraph, with the mis-specified control attached |
| 10 | §5.2 | The 0.43 never named as G-CTRL; the gate's two halves never assembled | **Underclaim** + structural | **ACCEPT.** Name the gate, give both targets and the FAIL verdict |
| 11 | §5.3 heading | "Its own paper never reports" — unaudited universal | Unsourced | **ACCEPT.** Restore "the paper that published the table" |
| 12 | §5.3 vs §5.6 | Floor called a property of the benchmark, then of the reader and grader | Contradiction | **ACCEPT.** §5.6 is right; §5.3 follows it |
| 13 | §5.3 | Multi-hop floor 38.54% omitted; deflation scoped to "quoted" rows only | Omission | **ACCEPT.** Print four strata; "every row… this component's included" |
| 14 | §5.4 | "The published 60.53% sits inside it" — nothing reproduced it within tolerance | Overclaim | **ACCEPT.** Four ran, none within ±3.0; bracketed, not hit |
| 15 | §5.5 | "Less than the judge's run-to-run spread" — all three exceed 0.06 | Accuracy | **ACCEPT.** Show the per-stratum bound or drop the comparison |
| 16 | §5.5 | Registered arms vs post-hoc contrast conflated; sealed prediction 5 blurred | Standing + **underclaim** | **ACCEPT.** Separate arm from contrast; state prediction 5 with "no standing" |
| 17 | Figure 1 | Caption asserts all rows "scored… same harness, same judge"; image title carries the ranking claim | Overclaim | **ACCEPT.** Retitle the figure; rewrite the italic line; name the second manifest |
| 18 | §5.1 | LangMem (58.10%) dropped from a reprinted table under an "every row" claim | Omission | **ACCEPT.** Print it or say why not, per `COMPETITIVE_LANDSCAPE.md` |
| 19 | §4.1 | The "in full" assignment table has no HH-002 row | Structural | **ACCEPT — most serious structural.** Two rows, in the same voice |
| 20 | §13.10 | "NF-004… and HH-001 read them again" — HH-002 is the third and largest read | Stale | **ACCEPT.** Name it; pluralize the §5 standing |
| 21 | §14 | "Not shown that any of it makes a reader answer better" — §5 measures exactly that | Contradiction | **ACCEPT.** Narrow to the offline-to-correctness link |
| 22 | §14, §1.2 | No HH-002 anywhere in the conclusion or contributions; "eleven pre-registered efforts" survives | **Underclaim** + retired count | **ACCEPT.** Cycle 4's objection 2, third cycle open |
| 23 | §2.1 | "We do not place them in one column" — the paper now does, correctly | **Underclaim** | **ACCEPT.** Distinguish the two measures instead of refusing one |
| 24 | §5 / §6 boundary | 79.09% and 935 of 1,098 adjacent, both "LoCoMo", never distinguished | Structural | **ACCEPT.** One sentence, per `COMPETITIVE_LANDSCAPE.md` §3.2 |
| C1–C5 | §5.3, §5.4, §5.7, §5.8, Exec | Contamination unmeasured-not-excluded; failure not cancelled; granularity confound named; floor subtraction refused; costs against itself | **Credit** | **NOTED.** Model forms; do not lose them in a later pass |

**The three most serious**

1. **Objection 1 — the ranking predicate, in §5's lead sentence, the abstract and
   the figure title.** `DO_NOT_WRITE.md` item 35 was amended *today* to permit
   exactly one thing and forbid a short list; "above every row of that table" is the
   forbidden comparison with the verb changed, and it is the first sentence of the
   section and the second sentence of the abstract's HH-002 paragraph. That the
   executive summary's guarantee was narrowed from "no sentence says the component
   beat Mem0" to "no test is computed against a quoted row" while the claim stayed is
   the part a hostile reader will quote. The rig's agreement with Table 2 is
   demonstrated for one row and refuted for another; a claim quantified over all
   seven is not available on that evidence, and the paper does not need it.
2. **Objection 9 with 10 — the two facts that license the section are the two most
   quietly stated.** The registered directional claim passed at 558 gains against 45,
   p = 6.615e-114, with the model-free endpoint agreeing, and it appears once, in a
   list of caveats, without a single one of those numbers. The reproduction that
   licenses printing the table at all — 0.43 points, on the row that cannot be
   mis-specified, with a judge moving 0.06 — is never connected to the gate it half
   satisfies. Meanwhile the post-hoc contrast whose sign the registration mispredicted
   gets the opening sentence and two p-values. That is the evidentiary weighting
   inverted, and correcting it costs nothing and strengthens everything.
3. **Objection 19 with 21 and 22 — the new headline is outside the machinery that
   grades the old ones.** §4.1 claims a complete assignment and omits HH-002; §13.10
   does not know it read the corpus; §14 asserts the programme has not measured
   reader accuracy in a paper that now opens with 1,540 judged answers; §1.2 does not
   list it as a contribution. §4 exists to be the honesty mechanism, and a headline
   result that never enters it is the single easiest thing for a reviewer to hold up.

**Is the section within its evidence?** In its body, largely yes. Every numeral in
§5 traces to `HH002_EVIDENCE_SPINE.md` or `HH001_EVIDENCE_SPINE.md`; the forbidden
40.58 and the 92.5% comparison appear nowhere; the floor-adjusted column is
correctly restricted to measured rows and says why; both failed gates are now named
as failures in §5.3, §5.4, the executive summary and the abstract; and §5.3's
contamination sentence and §5.4's "the explanation does not cancel the failure" are
better than what most papers write in that position. The residue is concentrated in
three places: the sentences written to lead — §5's opener, the abstract's, the
figure's title, the sentence under §5.1's table — where the ranking claim lives; the
counts and attributions of the quoted rows, which are wrong in the same direction at
five sites; and everything downstream of §5 that has not been re-read since HH-002
existed, which is §4.1, §13.10, §14, §2.1 and §1.2.

**Verdict.** The section earned a stronger claim than it is making and is making a
different, weaker-founded one instead. Fixing objection 1 costs the paper nothing it
measured; fixing objections 9 and 10 gives it back more than it loses.

**A Cycle 6 pass is warranted, and narrowly.** Objection 19 is a structural change —
two rows in §4.1's assignment table — and objections 21 to 23 require rewriting
sentences in three sections that were not in this cycle's scope and are now
contradicted by it. Everything else is a sentence-level edit at a named line. Cycle
4's prescription applies again and was again not run: for each corrected value, grep
the *value* and fix every site. "Six" and "five" as counts of quoted rows would have
closed at five sites on that pass alone.

---

**Reviewed at** commit `e8bf4039` on branch `study/hh-002-vendor-faithful`, against
a pinned copy of `paper/PAPER_002.md`, SHA-256
`f22010eca470528770862c39b1a6e0de2724e963a1598cfeb163b67ce43d6e7b`. The file was
under active edit during the review (`cfc1c3da` → `0df44eaa` → `e8bf4039`); edits
after `e8bf4039` are unreviewed. Read in full: the executive summary, the abstract,
§1.2, §1.3, §2.1, §4.1, §4.2, §5.1–§5.9, §13.1–§13.10, §14, and the Figures section;
`paper/notes/HH002_EVIDENCE_SPINE.md`, `paper/notes/HH001_EVIDENCE_SPINE.md`,
`paper/notes/DO_NOT_WRITE.md`, `paper/notes/COMPETITIVE_LANDSCAPE.md`,
`experiments/comparisons/hh_002/HH_002_PRE_REGISTRATION.md`,
`experiments/comparisons/hh_002/HH_002_FINDINGS.md`,
`experiments/comparisons/hh_002/RESULTS.md`, `AGENTS.md` §3, §8, §9,
`paper/reviews/CYCLE_3_PAPER_002.md` and `paper/reviews/CYCLE_4_PAPER_002.md`.
Checked by reading source: `src/analysis/hh002_arms.py` (objection 4),
`scripts/generate_hh002_figures.py` and `paper/figures/figure_manifest_hh002.json`
(objection 17).
