# contextDecayWindow

**Can a language model hold a long conversation by rebuilding a small, relevant context every turn, instead of re-reading the whole transcript or summarising it away?**

Ten pre-registered studies test that question, each adding one memory component and fixing the prior study's documented failures. Every result is published as found.

> **Status:** Study 010 stopped at G2; exploratory continuation unaudited and LTM budget-noncompliant | retrieval bakeoff complete | retrieval mechanism ledger closed; E001/E002 killed | renderer fix complete | Q4 packing diagnostic; Branch D invalidated | scoring record corrected 2026-07-29

## The Problem

A long conversation forces a bad trade. Keep the full transcript and the model gets slower and loses the middle. Summarise it and details disappear permanently.

## The Approach

Store every exchange as an episode. Each turn, retrieve recent and semantically similar episodes and construct a small context. Then add one memory component per study and measure its effect: long-term storage, retrieval, consolidation, and budgeting.

Runs use a scripted 120-turn conversation with facts planted at known positions and a rubric locked since Study 002.

## What Has Been Tested

| # | Added | Result | Finding |
|---|---|---|---|
| 001 | Recency and similarity retrieval | PARTIAL (2/3) | Similarity fired once in 32 turns |
| 002 | Consolidation, rule pinning, 120 turns | PARTIAL (3/4) | Similarity recovered buried facts; consolidation produced 52 topics |
| 003 | LTM write path | PARTIAL (2/3) | Promotion behaved as novelty detection, not salience judgment |
| 004 | LTM read path and arbitration | PARTIAL (1/3) | Retrieval worked, but the store lacked useful planted facts |
| 005 | Permissive capture and extractive dreaming | PARTIAL | Entity and number counts selected verbosity |
| 006 | Length-normalised sentence selection | PARTIAL (1/3) | Formation reached all domains, but small records broke count budgeting |
| 007 | Information-sized retrieval budget | PARTIAL (2/3) | Best score; the model used every delivered fact |
| 008 | Rendering by selection factorial | STOPPED AT GATES | No jointly feasible operating point existed |
| 009 | Pure-STM null test and topic digest | PARTIAL; null decisive | LTM beat STM by 3.0; digest failed its offline gate |
| 010 | 1,000-turn endurance | STOPPED AT G2; EXPLORATORY CONTINUATION COMPLETE | LTM won breadth in a budget-noncompliant arm; targeted tied; Bar 3 NOT EVALUABLE |

Full reports live under `experiments/study_NNN/`.

## Retrieval Bakeoff

The registered exploratory retrieval bakeoff is a negative result on the
architectural pivot. The best 32k raw-store retrieval surfaced 8/17 Q11 facts;
explicit graphs did not advance; oracle routing added only 6.09%. Delivered
volume did help: same-seed plain STM scored 9.0/13, widened STM scored 11.0/13
with 13/17 Q11 facts, and LTM scored 12.0/13. Both widened STM and LTM failed
Q11; the entire one-point rubric gap is Q4. The first clean positive result is
more specific: widened raw STM delivered all six formation-blind facts and used
five correctly, solving the track's hardest documented availability failure.
LTM's only observed edge over matched raw volume is keeping Q4's turn-55 fact
bundle available. DR-001 reproduced the historical
blocks exactly, found that Study 010's reported 31,991/31,847 values were
undercharged content totals rather than 53,726/53,839-character serialized
blocks, violating the 32k budget by 67.9%/68.2%, and replaced repeated
diagnostic markup with a compact, content-identical episode format. AS-001
found that compact N-first packing admitted 9 of 32 candidates at 32k and 16 at
64k; rank-27 Q4 never entered. Its Branch D `PRIMACY MECHANISM LIVE`
interpretation was invalidated after output because the null could not fire in
the tested regime. A post-result diagnostic places rank-27 entry at 108,432
characters. The result indicts ranking/packing and budget jointly, not primacy
as a separate mechanism. No other LTM function has been shown to beat matched
raw volume.
No 1,000-turn run is authorized.

See `experiments/surveys/retrieval_bakeoff/retrieval_bakeoff_report.md` and
`experiments/components/q4_packing/AS_001_report.md`.

## Retrieval Mechanism Ledger

The query-representation ledger is closed. Exhaustive mechanical segmentation
(E002) peaked at 10/17 breadth facts across 3/4 domains and preserved 14/16
targeted items, so it was killed. The exploratory NF4 attention diagnostic
(E001) improved Q4 cosine from 0.120422 to 0.210318 and descriptive similarity
rank from 24 to 20, but none of 714 cues reached K=0.48. E003 late interaction
was not run because the Q4-only diagnostic cannot supply its required breadth
bound.

See `experiments/components/retrieval_mechanism_ledger/RETRIEVAL_MECHANISM_LEDGER_REPORT.md`.

## Renderer Correctness

DR-001 is a component fix, not a study. Pre-fix replay reproduced Study 010
Q13/Q14 character-for-character. Post-fix replay preserved every selected
episode identity, order, and source message while reducing the same blocks from
53,726 to 37,619 characters and 53,839 to 37,545. Production LTM selection now
charges the exact complete serialized block. The registered 32,000-character
allocation, N cap 32, per-domain floor, and containment policy were re-derived
and retained. AS-001 found that compact rendering does not bring the rank-27 Q4
episode into the window anywhere in the locked 16k-64k sweep, but its
architectural decision rule was invalid. The separate Study
010 context peak is traceable to the full serialized prompts: all 2,000 rows
recompute under the registered `characters // 4` estimator, with L peaking at
27,154 and S at 17,541. These are estimates, not exact tokenizer counts.

See `experiments/components/rendering_expansion/DR_001_report.md`.

## What We Learned

**The model uses what it receives.** At the hardest probe it used 10 of 10 available facts and invented none. Failures were delivery failures.

**Formation was harder than retrieval.** Deciding what deserved memory took four studies to solve.

**Selection heuristics chose correlates.** Novelty selected spikes, entity counts selected verbosity, and density selected topic overviews.

**Offline gates save expensive runs.** Study 008 stopped before inference because replay proved no registered configuration could work.

**Measurements can be unwinnable.** The breadth question requires 14 of 17 facts, while only 11 are reachable in the current architecture.

## Reading This Repository

Read a study in this order:

1. `study_NNN_report.md` - outcome, mechanism, failures, and implications.
2. `pre_registration.md` - design committed before the run; its SHA is the anchor.
3. `amendments/` - authorized mid-study changes.
4. `runs/` - logs, scores, and mechanism analyses.

Also read:

- `ERRATA.md` before quoting any number.
- `experiments/audits/scoring_integrity/` for the 2026-07-26 corpus audit.
- `AGENTS.md` before contributing; it is the operating manual and study digest.

## Corrected Numbers

The 2026-07-26 audit re-scored all 222 committed scores across Studies 001-009;
19 changed. Study 002 C fell from 13.0 to 8.5 because a truncated reasoning
block had been credited as a complete response; Study 002 A fell from 8.0 to
5.5. Study 001 lost the program's only VALIDATED verdict.

Corrected treatment scores are **8.5, 11.5, 6.5, 11.0, 9.0, 12.0, 12.0** for Studies 002 C, 003, 004, 005, 006, 007, and 009 L. Runtime and response budgets changed across that series. The clean architectural comparison is Study 009's same-seed result: **9.0 without LTM and 12.0 with it.**

The residual figure is an extrapolation, not an observed count: 3 disagreements
in the 26-item control sample (11.54%) projected across 143 unreviewed items
gives 16.5 expected errors, reported informally as about 20. Final adjudication
used AI reviewers rather than human reviewers. Study 010 was outside the audit;
its exploratory 21.5/23 and 16.5/23 are not directly comparable to this
corrected series.

## Runtime

Local inference uses llama.cpp with Qwen3.6 27B UD-Q6_K_XL, one slot, fixed seed, and speculative decoding disabled. Embeddings use Qwen3-Embedding-0.6B; storage uses SQLite and sqlite-vec. Exact flags are registered per study and recorded in run headers.

*Idris Applied AI Research | independent, non-profit | failures published with the results*
