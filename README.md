# contextDecayWindow

### → [**Read the paper: *Selection, Not Capacity***](paper/PAPER_001.md) · [**Download the PDF**](paper/Selection_Not_Capacity.pdf)

A measured decomposition of retrieval failure across eleven pre-registered
efforts, what survived them, and why. Opens with a one-page executive summary;
every claim carries its committed artifact, and one headline number
[reproduces in a clean environment](paper/REPRODUCTION.md). Draft.

---

**Can a language model hold a long conversation by rebuilding a small, relevant context every turn, instead of re-reading the whole transcript or summarising it away?**

Ten pre-registered studies test that question, each adding one memory component and fixing the prior study's documented failures. Every result is published as found.

> **Status:** Study 010 stopped at G2; exploratory continuation unaudited and LTM budget-noncompliant | retrieval bakeoff complete | retrieval mechanism ledger reopened for Family CS; E005 is killed by LV-001's live targeted-regression bar, DX-001 closes NO CHANGE, and RD-001 stops before correlation because unchanged rarity scores cover only 6/76 fact-bearing episodes; chained retrieval is not authorized | CC-002 extracts the deployable component into `episodic`; CC-006 adds exact hashed vector-cache reuse | deployment closeout complete | PAPER-001 revised through RD-001 | scoring/interpretation record corrected through 2026-08-05

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
(E002) peaked at 10/17 breadth facts across 3/4 domains and preserved all 16
targeted items, so it was killed under its locked criterion. (E002's targeted
figure was published as 14/16 and corrected to 16/16 on 2026-08-01; the KILL is
unaffected. See `ERRATA.md`.) The historical
13/17 hurdle used a 60,285-character Q11 payload, while E002 was held to
32,000. Against its unchanged exact-budget baseline, segmentation improved
availability from 6/17 to 10/17 (66.7%), leaving F1 open with the best
matched-budget improvement tested. The exploratory NF4 attention diagnostic
(E001) improved Q4 cosine from 0.120422 to a best-found 0.210318 and
descriptive similarity rank from 24 to 20, but none of 714 rows reached
K=0.48. Its 266/384 selected heads were not sparse, so 0.210318 is not a
ceiling; F2 is nevertheless closed as a program disposition. E003 late
interaction was not authorized, and E002's segment counts did not validate an
absence detector for F3.

AR-001 checked whether the 14/17 breadth bar was physically achievable after
exact accounting. The exact minimum is 5,058 serialized characters across five
episodes, leaving 26,942 characters of headroom; even 17/17 costs only 7,592.
Complete standalone domain costs are civil 826, art 3,182, monetary 2,913, and
marine 824 characters. Art is the most expensive domain but still occupies
less than 10% of the budget, so E002's 3/4-domain ceiling is a selection and
ranking failure rather than a serialized-capacity limit.

E005 acted on that finding. If the gap is selection, replace per-item cosine
ranking with a set-level objective where an episode's value depends on what is
already selected. Three deployable selectors were swept over 146 configurations
at the enforced 32,000-character budget: MMR, facility location, and a
relevance-plus-cluster-diversity objective. **Every configuration beat the
committed 6/17 baseline. The best gate-passing configuration delivered 12/17
items across all four domains at 31,569 characters while preserving all 16
targeted items, and recovered 4 of the oracle's 5 episodes.** The outcome is
PROMOTION_ELIGIBLE offline; no live run is authorized, and 12/17 remains short
of the 14/17 rubric threshold and the 15/17 oracle.

Three results matter more than the headline. Facility location scored the
highest raw count, 13/17, and passed no gate, because it delivered monetary 0/4
at every setting - the per-domain check catching a selector that improved the
total by abandoning a domain. Cost scaling was predicted to be inert on a slack
budget and was not: the budget is slack for the optimum but not for a selector
registered to fill it. And on the deployed candidate pool, no configuration
covers four domains at all, so the pre-filter, not the selector, had been
setting the ceiling.

Two diagnostics then split the remaining gap in two. DR-002 found that cosine
ordering is the wrong prior for the enumeration probe - the four highest-cosine
episodes carry none of its facts - and that the pool binds on both facts and
domains. DX-001 asked why the one remaining oracle episode, turn 90 at cosine
rank 112 carrying four monetary items, was never selected. **It is inside the
pool, and the objective declines it in all 146 configurations.** Cluster
collision, the predicted cause, is refuted: its cluster is never entered, so the
diversity term was payable in full at every step and it still lost by 0.169. To
win it needed a cosine of 0.225 against its actual 0.056. The registered
protocol's no-change branch fired, so **12/17 ships with that miss characterized
rather than tuned away**, and the objective question escalates to a proposed,
unauthorized study. The pool decides what can be seen; the objective decides
what is worth taking; each now binds on a different part of the gap.

RD-001 then tested the paper's cheapest corpus-artifact alternative. It
recovered the complete 119-episode cosine ordering under the pinned E005
embedding call, but stopped before correlation: the earlier rarity audit has
unchanged scores for only 6 of the 76 fact-bearing episodes, with three variants
and no registered primary or episode aggregation. This is a measurement-unit
failure, not a null. The vocabulary explanation remains unresolved, and E006's
conditional chained-retrieval Part 2 is not authorized.

A provenance follow-up also withdraws the categorical claim that IDF ranked the
hard plants worse than density. Mean IDF did so for all five eligible spans, but
maximum IDF improved two and summed IDF per word improved one; no variant was
registered as primary. See `ERRATA.md`.

See `experiments/components/retrieval_mechanism_ledger/RETRIEVAL_MECHANISM_LEDGER_REPORT.md`,
`experiments/components/retrieval_mechanism_ledger/artifacts/ar_001/AR_001_report.md`,
`experiments/components/retrieval_mechanism_ledger/E005_POSTHOC_INTERPRETATION.md`,
and `experiments/components/retrieval_mechanism_ledger/DX_001_PART2_DISPOSITION.md`.
RD-001 is recorded in
`experiments/components/retrieval_mechanism_ledger/RD_001_report.md`.

## The Extracted Library

CC-002 moved the deployable memory component into `episodic/`, an
installable package with a public store, report, config, and embedding-cache
API (`EpisodeStore`, `ContextReport`, `EpisodicConfig`, `EmbeddingCache`) and zero experiment machinery; the
harness now imports the library and is its largest test. Extraction is
certified behavior-preserving, not assumed: all 132 committed A3
selection records and all three committed DR-001 serialized blocks
reproduce their SHA-256 byte-for-byte through the library (T3/T4), the
full suite runs green with the harness consuming it (T6, 804 tests), and
`store.context()` is byte-identical across processes (T7). The two
reproduction hazards found by gates in this program ship as contract
requirements, not documentation: the embedder call-shape sentinel is
asserted on every store open (H1, from DX-001), and candidate-pool
trimming exists only under an `unsafe_` name carrying the DR-002 finding
(H2). The library README makes measured claims only, each row with its
artifact hash.

See `episodic/README.md` and
`experiments/components/library_extraction/CC_002_library_extraction.md`.

CC-006 closes a second reproducibility hazard. A model-artifact hash and the
H1 solo-call sentinel do not certify every vector byte: EC-002 recomputed the
same nominal embeddings and moved one evidence rank plus one coverage
selection. `EmbeddingCache` now retains exact float32 vectors, records both
the SQLite file hash and a canonical text-to-vector content hash, and refuses
read-only misses. C1-C9 pass. The retained EC-002 cache adopts unchanged at
96,585 entries with zero model calls. The guarantee is prospective: EC-001's
unretained original cache remains permanently unreplayable at bit granularity.

See `experiments/components/embedding_cache/CC_006_report.md`.

## Deployment Closeout

The four remaining component obligations are closed, preceded by the
diagnostic that gated them.

**DX-002 asked whether Study 010's context was still growing at turn
1,000.** The record held a peak — 27,154 estimated tokens — and a peak
cannot answer that. Decomposing all 2,000 committed prompts into their
parts, under a gate that every prompt reconstructs byte-exactly, returned
**Branch B**: the budgeted LTM block saturates at ~52–54k characters from
turn 500, but the unbudgeted `<retrieved_stm>` block never does. Its 95th
percentile rose 23,238 characters in arm L and 28,701 in arm S over the
final five 100-turn buckets and held the record in the last bucket of both
arms. Rule pinning, the named suspect, contributed exactly zero — and was
disabled before the run, so it is untested rather than cleared.

The diagnostic first returned Branch A, on a rule that only asked whether
the terminal slope's confidence interval contained zero. It does, for every
part in both arms. Branch A is a conjunction whose third clause is *no
unbudgeted component climbing*, and checking only the slope let a block
that grew 23,000 characters read as flat — the interval was measuring
statistical power and was read as evidence of boundedness.

**CC-003 makes the budget a ceiling.** The leak turned out to be the Study
010 runner's, not the library's: replaying the same 1,000 episodes through
`episodic`, the delivered block never exceeds its budget and its p95 moves
+18 characters. Enforcement closed three real gaps — the ceiling used to
raise rather than degrade at budgets too small for one episode, `truncated`
carried no content, and the drop order had no name — and is certified inert
at the operating point: 132/132 committed payload SHAs and 12/17 · 4/4 ·
16/16 at 31,569 of 32,000 characters, unchanged.

**CC-004 makes restart a guarantee.** The durability point is stated — when
`append()` returns, the episode is on disk — and tested against real
process kills, not simulations. `context()` returns a byte-identical block
across restart, corruption is refused at open, and 100 restart cycles leave
no drift.

**CC-005 states a growth policy and builds nothing.** Disk is cheap at
4,743 bytes per turn. Latency binds: 190 ms at 1,000 candidates, 81% of it
clustering. That measurement corrects a published claim — DR-002's timing
sweep covered 20–119 candidates, not the "20–3,000" the library README
cited, and projections from it understate the cost at 1,000 candidates
about fivefold. Trimming the pool remains the one fix measured to break
retrieval, so retention stays unbounded and the horizon is stated instead.

See `experiments/components/deployment_closeout/`.

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
