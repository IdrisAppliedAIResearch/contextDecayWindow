# Selection, Not Capacity

### A measured decomposition of retrieval failure in conversational memory, and what survived eleven negative results

**Idris Applied AI Research** · independent, non-profit
Repository: `contextDecayWindow` · Licence: CC BY 4.0
Draft — PAPER-001, Pass 1 skeleton

---

> **Status of this draft.** Pass 1 of the seven-pass authoring loop: headings,
> abstract, and figure captions. Captions are written before the figures they
> describe. Body sections carry their argument in outline and their committed
> sources; prose lands in Pass 3. Numbers shown here are verified against
> committed artifacts in `paper/notes/EVIDENCE_INDEX.md`.

---

## Abstract

*(One paragraph, Pass 3. Must carry: the category declaration up front; the
three-way decomposition — pool, objective, similarity floor — with each bound;
the inversion result stated at its measured width, not wider; 6/17 → 12/17
against the 14/17 bar and the 15/17 known optimum; 14/17 reachable in 5,058 of
32,000 characters; and the subtraction result. The n=1 declaration belongs in
the abstract, not only in Limitations.)*

**Placeholder claim set for Pass 3:**

- This is a single-program experience report. One corpus, one probe set, one
  model, one quantization, one machine, one seed. No error bars anywhere.
- On this corpus, the four highest-cosine episodes carry none of the enumeration
  probe's target facts, while on all eight targeted probes cosine ordering
  places every needed item inside rank 2.
- Deployed selection delivered 6 of 17 facts while spending 31,946 of 32,000
  characters. An exact optimum reaches 14 of 17 in 5,058 characters.
- Replacing per-item cosine ranking with a set-level coverage objective reaches
  12 of 17 across 4 of 4 domains at 31,569 characters, preserving 16 of 16
  targeted items.
- The residual is a floor, not a tuning problem: 0 of 146 configurations select
  the last oracle episode, which needs a query cosine of 0.225 and has 0.056.
- What survived eleven studies is smaller than what the field builds, and its
  deployable properties are consequences of the negative results.

---

## 1. Introduction

**1.1 The problem.** A long conversation forces a trade: carry the transcript and
pay for it, or summarize and lose detail permanently.

**1.2 What this paper is.** A case study of one program's eleven pre-registered
efforts — ten numbered studies plus one registered exploratory bakeoff — with
the diagnostics and component work that followed. Every result published as
found.

**1.3 The category declaration.** Stated here, not deferred to Limitations. The
program has never been externally calibrated: Study 003 retired external
baselines in favour of self-comparison and nothing restored them. Declaring the
category is what makes n=1 legitimate rather than a defect.

**1.4 Contributions.**

1. A measured decomposition of where retrieval failure lives, with three
   constraints separated and each independently bounded.
2. The measurement that supports it: a per-fact known optimum computed on the
   same store under exact serialized-cost accounting.
3. A subtraction result — what eleven studies removed, and why what remains is
   deployable *because* of what was removed.
4. A published correction record, including one near miss by a diagnostic
   written to catch exactly that failure class.

**1.5 What this paper does not claim.** No comparison to HippoRAG, Mem0, Zep, or
Letta — none were run. No general claim about similarity retrieval. The
inversion is an observation on one corpus, offered with the experiment that
would test it elsewhere (§9.5).

---

## 2. Related work

Convergence and grounding, never derivation. Studies 001–010 predate the
program's first literature scan and are committed with SHAs showing it; stated
once, plainly, without overselling independence.

- **HippoRAG** — entity-centric indexing, and the authors' own ICML follow-up
  naming that as the limitation. Relevant because this program's hardest
  repeated failure (F4) is a span in which spaCy finds zero entities.
- **GraphRAG, SGMem, CodaRAG** — explicit structure over retrieved units.
- **Letta, Mem0, Zep** — deployed conversational-memory systems.
- **LoCoMo, LongMemEval** — the benchmarks this program adopted in principle and
  never ran. Named here as the calibration gap, not as related work it competes
  with.

Placement of this program: it operates on the candidate set those systems also
consume, and measures that set rather than proposing a new structure over it.

---

## 3. Method

Short. Four things a reader needs to trust the rest.

**3.1 Pre-registration and gates.** Design committed before implementation; its
SHA is the integrity anchor. Offline gates bind and run before inference.
Study 008 stopped at its pre-run gates, preventing four invalid 121-turn runs.

**3.2 Amendments.** Standalone files, never edits to a locked registration, with
a per-amendment record of whether it preceded the affected result. Twelve in the
bakeoff alone.

**3.3 Exact-cost accounting.** All character budgets charge the complete
serialized block, including per-episode tags, metadata, and separators. This is
the correction DR-001 forced (§8.2) and it is load-bearing for every number
after it.

**3.4 Determinism and leakage.** Fixed seed, one slot, no speculative decoding,
byte-identical seeded-prefix rerun. Mechanism code may not read the answer key;
measurement may. Enforced by grep, import-graph checks, and a planted test
violation.

**3.5 The control/baseline distinction.** Controls run from checked-out prior
code in a separate worktree, never by disabling features in the current runner.

---

## 4. The arc, compressed

One table. One page on the turning points. Not a narration of ten studies.

**4.1 The table.** Studies 001–010: what was added, what it scored after the
scoring audit, and the terminal diagnosis in one line each.

**4.2 Turning point one — write-time selection cannot anticipate a query.**
Five studies of promotion filters, distillation, and salience heuristics, every
one PARTIAL. Terminal diagnosis: whole-turn absolute-count salience is a
verbosity detector; density ranks the six hardest planted facts 89th–316th; IDF
ranks them worse.

**4.3 Turning point two — moving selection to query time did not recover it.**
The bakeoff's Tier 1 raw-store reachability topped out at 8/17, below the 11/17
the formation era could reach. The pivot's central premise, refuted by its own
test. Graphs did not clear their advancement gate; routing's oracle ceiling was
6.09%; ANN recall degraded at synthetic scale.

**4.4 Turning point three — the first clean positive was volume, not mechanism.**
Widened raw STM delivered all six formation-blind facts and the model used five.
No selection filter involved.

**4.5 Turning point four — query representation was not the problem either.**
Mechanical segmentation improved its exact-budget baseline from 6/17 to 10/17
and still failed its registered 14/17 bar. Attention-derived term selection, run
as an oracle, moved cosine from 0.120 to 0.210 against a 0.48 threshold.

> **Figure 1 belongs here or in §5.** Decide in Pass 3. It is the hinge between
> the arc and the decomposition, and it can only be placed once the prose around
> it exists.

---

## 5. The decomposition

The core, and the longest section.

**5.1 The target was always reachable.** AR-001 computed the exact minimum cost
of the breadth bar on the same store under exact accounting. All 17 items are
present; 76 of 119 episodes carry at least one.

**5.2 The gap is not capacity, formation, or cue quality.** Deployed selection
spent the full budget for 6/17. The exact optimum spends 16% of it for 14/17.

**5.3 Set-level selection recovers half the gap.** Replacing per-item cosine
ranking with a submodular coverage objective. What it recovers, what it costs,
and the arm that scored highest while failing every gate.

**5.4 The candidate pool binds on domain coverage.** The frozen configuration
across three pools, and the brittleness that pool size alone does not predict.

**5.5 The ordering is anti-correlated at the top — for one query type.** The
registered rule, what fired it, and §5.6's limit on how far it generalizes.

**5.6 What the inversion does not explain.** Stated at measured width. On all
eight targeted probes cosine places every needed item inside rank 2. The
inversion does not explain formation-side failures, Study 003's arithmetically
unreachable promotion route, Study 007's absent facts, Tier 3's routing oracle,
or widened STM's unfiltered 6/6.

**5.7 The residual is a floor, not an interaction.** One episode, 0 of 146
configurations, and the predicted cause refuted.

**5.8 The three constraints, separated.**

| Constraint | Binds on | Bound |
|---|---|---|
| Candidate pool | domain coverage, and part of the fact gap | *(§5.4)* |
| Selection objective | the remaining recoverable facts | *(§5.3, §5.7)* |
| Similarity floor | the irreducible residual | *(§5.7)* |

**5.9 Why this decomposition is not reported elsewhere.** It requires a per-fact
known optimum on the same store, which requires an answer key and exact-cost
accounting. Stated as an observation about what evaluations typically carry, not
as a claim about what others could have done.

---

## 6. What survives

**6.1 The subtraction result.** Eleven studies removed more than they added. The
graveyard table, each row with the result that killed it.

**6.2 What remains.** An append-only verbatim store, a recency window, cosine
similarity retrieval for targeted queries, and a set-level coverage objective
for selection. No inference calls anywhere in the memory path.

**6.3 Why a practitioner should care.** The surviving design is deterministic,
offline, and provenance-preserving *because* the removed components were the
ones requiring model calls. The properties that make it deployable are
consequences of the negative results, not independent design choices.

**6.4 What it costs.** Bounded delivered context, cheap disk, and a latency
horizon that binds before ten thousand episodes.

---

## 7. Self-audit and corrections

Framed as *we broke ours first*. A numbered section, not a footnote. Reported at
full strength.

**7.1 The scoring-integrity audit.** 222 items re-scored, 19 changed, and the
program's only VALIDATED verdict removed.

**7.2 Rendering accounting (DR-001).** Every study on record ran over its stated
budget; a headline "saturated" figure was an undercharged content total.

**7.3 The probe-order validator.** Degradation probes requested facts before
they were planted, invalidating a published curve.

**7.4 Embedder call-shape dependence.** The same query text returns a materially
different vector depending on the shape of the embedding call. Found by a replay
gate; now a startup assertion in the shipped library.

**7.5 The latency projection error.** A pre-registered budget extrapolated 84×
past its last measured point and understated cost about fivefold.

**7.6 The near miss, and it is the most instructive.** A three-clause decision
rule implemented as a check on its terminal clause alone let a block that grew
23,000 characters read as flat. A diagnostic written to catch surrogate failures
nearly committed one.

**7.7 What the gates missed.** §9.8's question, answered here rather than
deflected.

---

## 8. Limitations

Load-bearing, first-person, and stated before a reviewer states them. Each item
names what would settle it.

8.1 n=1 corpus, single seed, no variance anywhere in the program.
8.2 No external calibration; benchmarks adopted in principle, never run.
8.3 Breadth conclusions rest on one probe.
8.4 AI-scored rubrics with AI adjudicators.
8.5 Planted facts may not represent natural conversation — open question, with
the experiment named.
8.6 The known optimum contains prior probe answers: four of five.
8.7 Amendments exist after results; the legitimacy test and record, not a claim
of cleanliness.
8.8 What else is wrong: residual scoring errors remain unreviewed, and runtime
independence is entirely unmeasured.
8.9 Horizon: 1,000 turns says nothing about 10,000.

---

## 9. Conclusion

What a practitioner takes from this. The inversion restated at its measured
width, and named as worth testing elsewhere with the experiment specified.

---

## Figures

Six. Each carries an argument no sentence carries as well. Every figure is
generated by `scripts/generate_paper_001_figures.py` from committed artifacts.
Every caption states the artifact its data came from and is self-contained: a
reader who skims only figures and captions should get the thesis.

---

### Figure 1 — Cosine rank against fact content

**Argument it carries:** the ranking that every downstream mechanism consumes
puts the answer where the pool cut discards it.

> **Figure 1. On this corpus, the enumeration probe's target facts sit outside
> the top of the cosine ranking, and the deployed pool cut removes an entire
> domain.** Horizontal axis: cosine rank against the turn-120 breadth query,
> over the 119 eligible episodes. Vertical axis: Q11 target facts carried by
> that episode. The four highest-ranked episodes carry zero facts; the first
> fact-bearing episode is at rank 5 and the last still-needed item does not
> appear until rank 87. The five episodes of AR-001's 15-fact known optimum are
> marked at ranks 14, 20, 22, 86 and 112. Both contributors of the art domain
> lie at ranks 50 and 86, so the deployed 34-episode pool (first vertical line)
> contains no art episode at any setting and cannot reach four domains; the
> 100-episode pool (second line) excludes the rank-112 episode carrying four
> monetary items. **Only the 16 episodes whose ranks are committed are plotted**
> — the 15 selected by the primary configuration plus the rank-112 miss;
> per-episode ranks for the remaining 103 candidates were not committed, and
> recomputing them requires the carried embedder under E005's nine-query batched
> call, which is not in the repository. The rank-5, rank-87 and top-four
> readings are committed structural values, drawn as annotations rather than
> inferred from the plotted points. Sources: `dr_002/selection_ranks.csv`,
> `dx001/cost_comparison.csv`, `dr_002/generality_batched.json`; rank 20
> supersedes the published 21 per `ERRATA.md`, 2026-08-01.

---

### Figure 2 — The budget efficiency gap

**Argument it carries:** the constraint is not capacity. The tallest bar is also
the narrowest.

> **Figure 2. Delivered facts against characters spent: the known optimum is one
> sixth the width and taller.** Each bar is one selection over the same store at
> the same enforced 32,000-character budget. The deployed baseline delivers 6 of
> 17 items for 31,946 characters. The set-level coverage configuration delivers
> 12 of 17 across all four domains for 31,569. AR-001's exact optimum delivers
> 14 of 17 for 5,058 characters — 16% of the budget, leaving 26,942 characters
> unused — and its greedy variant reaches 15 of 17 for 5,455. The bar for the
> registered 14/17 threshold is drawn for reference; no deployable selection
> reaches it. The optimum is not achievable by a deployable retriever: it is
> computed with the answer key and is a bound, not a method. Sources:
> `e005/a0_baseline.json`, `e005/e005_results.json`,
> `ar_001/achievability.json`.

---

### Figure 3 — Pool ablation

**Argument it carries:** the pre-filter, not the selector, sets the domain
ceiling — and pool size does not predict what removal costs.

> **Figure 3. Widening the candidate pool from the deployed 34 episodes to the
> full 119, with the selector frozen, moves the same configuration from 5 of 17
> items across 2 domains to 12 of 17 across 4.** Grouped bars: facts delivered,
> domains covered, and overlap with the five-episode known optimum, at pools of
> 34, 100 and 119 candidates. Everything except pool membership is held fixed —
> same store, same renderer, same embedding, configuration `A3_l0.1_r0.0_k16`.
> The middle group is the one to read twice: dropping only the 19 lowest-cosine
> episodes costs three facts, the entire art domain, and *all* overlap with the
> known optimum, even though four of its five episodes survive the cut. The
> selector clusters over the pool, so removing the tail reshuffles the objective
> rather than removing options. This is a frozen-configuration readout, not a
> sweep: the best of 146 configurations reaches 13 of 17 on all three pools, and
> the pool's binding effect shows in domains rather than in that maximum.
> Source: `DR_002_report.md` §1; per-configuration values in
> `e005/pool_secondaries.csv`.

---

### Figure 4 — The corrected arc

**Argument it carries:** the program's own record was wrong in its favour, and
the correction is published rather than absorbed.

> **Figure 4. Treatment scores before and after the scoring-integrity audit: 19
> of 222 re-scored items changed, and the program's only VALIDATED verdict
> disappeared.** Paired points per study arm, original against corrected, for
> Studies 002C through 009L. The largest single fall is Study 002's iterative
> arm, 13.0 to 8.5, where a truncated reasoning block had been credited as a
> complete response; Study 002 A falls 8.0 to 5.5, and Study 001 loses the
> VALIDATED verdict it had held. Corrected treatment values are 8.5, 11.5, 6.5,
> 11.0, 9.0, 12.0 and 12.0. These points are **not a controlled series** —
> runtime and response budgets changed across it — and the only clean
> architectural comparison in the program is Study 009's same-seed pair, 9.0
> without the memory tier against 12.0 with it. Study 010 was outside the audit
> and is not plotted. Source:
> `audits/scoring_integrity/corrected_scores/arm_totals.json`.

---

### Figure 5 — Selector comparison

**Argument it carries:** the highest-scoring selector was the worst one, and
only a per-domain check could tell.

> **Figure 5. The selector with the highest raw fact count passed no gate.**
> Arms A0 (deployed baseline), A1 (MMR), A2 (facility location), A3 (relevance
> plus cluster diversity) and A4 (the carried known optimum), each showing
> facts delivered, domains covered, and targeted items preserved, with the
> monetary domain broken out. A2 leads on count at 13 of 17 and delivers
> monetary 0 of 4 at every one of its settings, so it fails the per-domain gate
> everywhere; A3's 12 of 17 across 4 of 4 domains is what ships. Every one of
> the 146 configurations beats the deployed 6 of 17, so the comparison that
> matters is between selectors rather than against the baseline. Targeted
> preservation is not a differentiator — 137 configurations preserve 16 of 16 —
> which is itself the finding: the failure is confined to enumeration. Sources:
> `e005/configuration_sweep.csv`, `e005/per_domain_counts.csv`,
> `e005/a0_baseline.json`, `ar_001/achievability.json`.

---

### Figure 6 — Growth and cost

**Argument it carries:** the growth was in the harness, not the component; and
the cost curve that replaced a projection was five times the projection.

> **Figure 6. Left: the context leak belonged to the study runner, not to the
> extracted component. Right: a projection extended 84× past its data
> understated cost about fivefold.** Left panel: the 95th percentile of the
> retrieved-STM block per 100-turn bucket over the final 500 turns of the
> 1,000-turn run. In the study harness the block rises 23,238 characters in arm
> L and 28,701 in arm S, still setting records in the last bucket; replayed
> through the extracted library at the same 32,000-character budget, the
> delivered block moves +18 characters and breaches the budget on 0 of 1,000
> turns. The library truncates on 895 of those turns — the block is bounded
> because it is enforced, not because the demand is small. Right panel: measured
> median selection latency against candidate count, 50 to 1,000, with the
> withdrawn linear projection overlaid. Measured cost at 1,000 candidates is
> 190 ms against roughly 40 ms projected; the empirical exponent is 1.25 over
> 50–1,000 where the earlier sweep found 0.96 over 20–119, and clustering's
> share rises from 37% to 81%. Values beyond 1,000 candidates are projections
> and are drawn dashed. Sources: `dx002/dx002_results.json`,
> `cc003/ge0_growth_gate.json`, `cc005/latency_curve.csv`,
> `cc005/latency_components.csv`.

---

## Appendices

- **A. Claim-to-artifact table.** Every claim in the paper with its committed
  SHA and artifact path. Produced in Pass 2; any claim that could not be traced
  was cut or demoted before Pass 3.
- **B. Study table.** Studies 001–010 with bars, outcomes, and report paths.
- **C. Amendment record.** Every amendment with its before/after-result status.
- **D. Corrections index.** The full set, cross-referenced to `ERRATA.md`.
- **E. Reproduction.** Installing `episodic` in a clean environment and
  reproducing at least one headline number, verified end to end in Pass 7.
- **F. Spec reconciliation.** Where this paper's numbers differ from the
  authoring specification, and why the artifact won.
