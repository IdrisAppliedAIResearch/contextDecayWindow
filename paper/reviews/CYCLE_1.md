# PAPER-001 — Adversarial Review, Cycle 1

Three reviewers, written separately, each in voice, against the Pass 3 draft at
commit `b6403a22`. Section references are to `paper/PAPER_001.md`.

A review not written down did not happen. Dispositions follow each review.

---

## Reviewer A — methodologist

I have read this as someone who cares whether the comparisons mean anything. The
paper is unusually candid, which makes it worth reviewing properly rather than
rejecting on n=1. Most of my objections are about claims that are *stated more
broadly than they were measured*, which in a paper this careful about scope is a
correctable defect rather than a fatal one.

**A1. §5.2 makes a claim that is false outside the pool it was measured on. This
is my main objection.**

The draft says: "**Every one of the 146 configurations beat the deployed 6 of
17.**" No pool is named. Two paragraphs later §5.3 establishes that pool
membership is the dominant factor, so the reader has every reason to read A1's
sentence as pool-independent.

It is not. From `configuration_sweep.csv`, the minimum fact count across the 146
configurations is 7 on the 119-episode pool, **5** on the top-100 pool, and
**4** on the deployed 34-episode pool. On the deployed pool, configurations fall
*below* the baseline they are supposed to replace.

Worse for the draft: the shipped configuration itself, `A3_l0.1_r0.0_k16`,
delivers **5 of 17** on the deployed pool against A0's 6. The paper's own
headline selector, run on the pool the system actually used, is worse than the
selector it replaces.

I do not think this sinks the paper. I think it is the most interesting number
in it and the draft has hidden it by accident. It converts §5.7's ordering claim
from a plausible reading into a measured one: the objective does not help until
the pool is widened. Say that.

**A2. A0 is not pool-controlled, so §5.2 confounds selector with pool.**

`a0_baseline.json` carries no pool field. It is the deployed pipeline's own
selection under corrected accounting — deployed selector on deployed pool.
Every A1/A2/A3 number in §5.2 is measured on the 119-episode pool. The
6 → 12 comparison therefore moves two variables at once, and the paper presents
it as a selector result.

The within-pool comparison exists in your artifacts and you should use it: on
the deployed 34-pool, A0 delivers 6, the frozen A3 delivers 5, and the best of
146 delivers 13. That is a real selector effect, on one pool, with the pool held
fixed. Report that, then report the pool effect separately, which §5.3 already
does correctly.

**A3. §5.2's optimality claim rests on an unstated bound.**

"Greedy runs at 0.954–0.9996 of its own certified upper bound, so the objective
and not the search is the limit." Which bound? A data-dependent one, a
(1−1/e) worst-case one, something else? The inference "search is not the limit"
is only as good as the bound's tightness, and the draft never says what is being
certified. Also note your own `optimality_bounds.csv` marks 33 of 438 rows
non-computable — all of A1 — and the draft does not mention that the MMR arm has
no bound at all.

**A4. §5.6's "0 of 146" overstates its own resolution.**

The 146 configurations are a grid over three parameters, not 146 independent
draws. Sweeping λ at eleven values while the relevance term is 0.056 against a
0.225 requirement is not 146 chances; it is one chance repeated. Your §5.6
arithmetic already makes the stronger, cleaner argument — the shortfall is
0.169 and only 20 of 119 episodes clear the bar — so lean on that and stop
implying the count is evidence of thoroughness.

**A5. The scoring residual needs an interval or an honest refusal.**

§7.1 reports "about 16.5 expected remaining errors" from 3 disagreements in a
26-item sample. A binomial proportion of 3/26 has a 95% interval of roughly
2.4%–30%, which over 143 items is about 3 to 43 errors. Either give the
interval or say the point estimate is not usefully precise. Given this paper's
own §7.6 is about a confidence interval being misread, I would expect more care
here than anywhere else.

**A6. §4's table drops the registered bar counts.**

The digest records outcomes like "PARTIAL (2/3)" — two of three bars. The
paper's table shows only "PARTIAL". A reader cannot tell a study that missed one
bar from one that missed all three.

---

## Reviewer B — systems researcher

I build these systems. My interest is whether anything here transfers.

**B1. §6.2 makes a comparison the paper elsewhere forbids.**

"It is smaller than what this program started building and smaller than the
deployed systems named in §2." You did not measure Letta, Mem0, or Zep. §1.3
says "No comparison against HippoRAG, Mem0, Zep, or Letta; none were run," and
then §6.2 compares against them on size. Pick one. If you mean the surviving
component has fewer moving parts than systems that do entity extraction and
graph construction, say that as an architectural observation about the *listed
mechanisms*, not as a comparison of systems you never ran.

**B2. §9 says the surviving design "outperformed every mechanism this program
layered on top of it." Most of those mechanisms were never run live.**

Study 008 stopped at gates. E002 and E005 are offline availability results.
DR-002, DX-001, DX-002 are diagnostics. The bakeoff's graph and routing arms
failed offline gates. So "outperformed" is doing work that "did not clear its
gate" would do more accurately. There is no live inference run of the shipped
configuration at all — the draft says PROMOTION_ELIGIBLE *offline* nowhere in
§6, though the source report says exactly that.

That omission is the one that would embarrass you. §6 reads as though 12/17 is a
shipped system's measured performance. It is an offline availability figure with
no live run authorized.

**B3. The latency numbers have no machine.**

§6.4 gives 190 ms at 1,000 candidates and §8.8 says the absolute milliseconds
are not portable, which is the right caveat but not a substitute for stating the
hardware, the thread count, and whether this is CPU embedding. Your own source
report scopes it to "one machine, one runtime, one quantization"; the paper
should name them.

**B4. Embedder sensitivity is stronger evidence than §8.8 admits.**

§8.8 says whether the results survive a different embedder is "entirely
unmeasured". But §7.4 reports that the *same* embedder under a different call
shape produces vectors agreeing to cosine 0.999837 that flip 6 of 146 committed
payloads. That is not an absence of evidence about embedder sensitivity. That is
positive evidence that this pipeline is sensitive to perturbations far smaller
than changing models. Connect them; right now §7.4 and §8.8 sit in different
sections and neither points at the other.

**B5. 12 of 17 is scored against a rubric the authors wrote.**

Acknowledged in §8.4 for the rubric scoring, but the breadth numbers throughout
§5 are item-availability counts against an answer key the same authors planted.
The paper should be explicit that 6/17, 12/17, 14/17 and 15/17 are all
*availability* against a self-defined item set, and that availability is not
answer correctness. Your source reports say this in their boundary sections; the
paper mostly does not.

---

## Reviewer C — skeptic

I am not persuaded yet, and I want to say where the paper is most likely wrong
rather than merely unproven.

**C1. The central split rests on one enumeration probe against eight targeted
probes.**

§5.5 is the paper's best section and its most fragile. The claim is that cosine
ordering is near-optimal for lookup and anti-correlated for enumeration. The
evidence is n=8 on one side and **n=1** on the other. Every quantity that makes
the paper interesting — top-4 carrying zero, rank 87, the rank-86 rule firing —
comes from a single question on a single corpus.

§8.3 concedes this. But §5.5 and §9 both state the split as a finding about
query *types*, and one instance cannot establish a type. The honest form is that
this program has one enumeration probe, it behaves completely differently from
the eight lookup probes, and that difference is the thing worth testing. The
draft is about eighty percent of the way there and the remaining twenty percent
is where a reader stops trusting it.

**C2. Four of the five "known optimum" episodes are prior probe answers, which
makes the optimum partly a memory of the system's own output.**

§8.6 states the fact and treats it as an eligibility-rule technicality. It is
more than that. If the cheapest way to satisfy the breadth probe is to retrieve
four earlier *answers*, then a large part of what the paper calls achievability
is the system recalling things it already said, not evidence from the source
conversation. The exact optimum's 5,058 characters are cheap partly because
answers are compact restatements of facts that were expensive to state
originally.

That does not invalidate the 14/17 bound under the registered rule. It does mean
"the target was always reachable" (§5.1) is a weaker sentence than it sounds,
and the paper should say which of the five episodes are plant sources and which
are prior answers.

**C3. Is the inversion an artifact of how facts were planted?**

§8.5 raises this and names an experiment, which is more than most papers do. But
the experiment as named ("repeat the measurement on unscripted conversation") is
expensive and vague. A cheaper and sharper test exists inside your own data:
the six formation-blind facts are described as rare technical phrases whose
component words are common. That is a *lexical* property, and it predicts
exactly the observed effect — an embedding will place such a span far from a
query phrased in common words. Test whether the fact-bearing episodes' cosine
rank correlates with the lexical rarity of their key phrases. If it does, the
inversion is a property of the planted vocabulary and generalizes only to
corpora with similarly distinctive plants.

**C4. §6.3 is framing presented as finding.**

"The properties that make this component deployable were bought by the failures,
not by the design." I like the sentence. It is not a measurement. Determinism
follows from having no model calls; that is a fact. That the *reason* there are
no model calls is the failures is a historical narrative about this program,
true but not a result. Mark it as interpretation.

**C5. The paper never states what the model actually scored with the shipped
configuration.**

Following from B2: every headline is availability. A reader finishes §6
believing something was deployed and measured. What would change my assessment
most is a single sentence in §6 saying no live run exists.

---

## Dispositions — Cycle 1

| # | Objection | Disposition |
|---|---|---|
| A1 | "Every configuration beat 6/17" is pool-scoped | **ACCEPTED — rewrite §5.2.** State the per-pool minima (7 / 5 / 4) and state that the shipped configuration scores 5 on the deployed pool against A0's 6. Promote to §5.7 as the ordering argument |
| A2 | A0 confounds selector with pool | **ACCEPTED.** Add the within-pool comparison (A0 6, frozen A3 5, best-of-146 13, all on the 34-pool) and label the 6→12 headline as moving two variables |
| A3 | Optimality bound unstated; A1 has none | **ACCEPTED.** Name the bound, state it is data-dependent, and record that all 33 non-computable rows are the MMR arm |
| A4 | "0 of 146" implies independence | **ACCEPTED.** Demote the count, lead with the 0.169 shortfall and the 20-of-119 reading |
| A5 | Residual estimate needs an interval | **ACCEPTED.** Give the interval (~3 to 43 over 143 items) or refuse the point estimate. Given §7.6, refusing precision is the consistent move — do both: report the point estimate as the source does and attach the interval |
| A6 | Table drops bar counts | **ACCEPTED.** Restore the registered bar counts |
| B1 | §6.2 compares against unrun systems | **ACCEPTED.** Rewrite as an observation about the listed mechanisms, not the systems |
| B2 | "Outperformed"; no live run stated | **ACCEPTED, and this is the most serious of the set.** Add an explicit statement in §6 that the result is offline availability, PROMOTION_ELIGIBLE, with no live run authorized. Replace "outperformed" in §9 |
| B3 | No hardware named | **ACCEPTED.** Name the runtime, model, quantization, and that embedding is excluded from the timings |
| B4 | §7.4 is evidence for §8.8 | **ACCEPTED.** Cross-link; restate §8.8 as "positive evidence of sensitivity to perturbations smaller than a model change" |
| B5 | Availability is not correctness | **ACCEPTED.** State once in §5.1 and carry the word "availability" through §5 |
| C1 | The split rests on n=1 enumeration | **ACCEPTED.** Restate §5.5 and §9 as one probe behaving unlike eight, not as a claim about query types |
| C2 | The optimum is partly prior answers | **ACCEPTED.** Name which of the five episodes are plant sources and which are prior answers, and soften §5.1 |
| C3 | Cheaper test for the artifact hypothesis | **ACCEPTED.** Replace §8.5's named experiment with the lexical-rarity correlation, which is runnable on committed data |
| C4 | §6.3 is interpretation | **ACCEPTED.** Mark it as such |
| C5 | No live run stated | Folded into B2 |

Sixteen objections, sixteen accepted. None was rejected, which is itself a
signal about the draft: Pass 3 was written from the source reports' headline
sentences rather than from their boundary sections, and the boundary sections
are where this program keeps its scope discipline.

**Structural changes required, so Cycle 2 is mandatory.**
