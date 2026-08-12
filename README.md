# contextDecayWindow

### → [**Read the paper: *Selection, Not Capacity***](paper/PAPER_001.md) · [**Download the PDF**](paper/Selection_Not_Capacity.pdf)

A measured decomposition of retrieval failure across eleven pre-registered
efforts, what survived them, and why. Opens with a one-page executive summary;
every claim carries its committed artifact, and one headline number
[reproduces in a clean environment](paper/REPRODUCTION.md). Draft.

---

**Can a language model hold a long conversation by rebuilding a small, relevant context every turn, instead of re-reading the whole transcript or summarising it away?**

Ten pre-registered studies test that question, each adding one memory component and fixing the prior study's documented failures. Every result is published as found.

> **Status:** Study 010 stopped at G2; exploratory continuation unaudited and LTM budget-noncompliant | retrieval bakeoff complete | retrieval mechanism ledger reopened for Family CS; E005 is killed by LV-001's live targeted-regression bar, DX-001 closes NO CHANGE, RD-001 stops before correlation because unchanged rarity scores cover only 6/76 fact-bearing episodes, and chained retrieval Rev5 is CHARACTERIZED offline at 9/17 versus X0 6/17 but misses art 0/4 and has no targeted no-regression arm | EC-001 LongMemEval complete: inversion not dominant, Codex-substituted score only | EC-002 complete: K-first packing raises any-session recall 109/470 -> 261/470 offline; no production promotion authorized | IC-001 Branch A: the same gate is closed internally — K delivered nothing at 8/8 probes under the deployed order; Q11 6/17 -> 7/17, targeted 14/21 -> 18/21, zero losses; cache clause substituted under authorized Amendment 001; no recalibration authorized | Study 011 tests both halves live and splits them: the deployed arm scores identically to recency-only on all 13 questions, so the similarity tier is inert in deployment, but K-first raises availability and scores 7.0 vs 8.0 — B1 FAILS and the packing correction is not adopted; post-unseal analysis finds the N tier is a least-recently-delivered rotation over the whole store, not a recency window, and that the rule every live run through Study 010 used was a block locked onto the conversation's first nine turns; three different rules carry that name and only the extracted library's is a window | Amendment 001 authorized and run: the instrument's run-to-run band is **3.0 points on 13**, measured by five identical arm-D replicates that score 8.0, 8.0, 8.0, 8.0 and 11.0 — a switch, not a spread, since four are byte-identical across 121 turns and the one meeting an empty server slot diverges at turn 1; Study 009's 3.0, LV-001's -2.0 and Study 011's -1.0 are all re-read as **not demonstrated**, while every offline count is untouched and B1 stays fired | CC-002 extracts the deployable component into `episodic`; CC-006 adds exact hashed vector-cache reuse | PS-001 CHARACTERIZED: the selected sparse cell stores and recovers 119/119 codes through 50% registered swaps | PS-002 stops at Part 1: best natural-language binder reaches stored codes in 190/192 rounds but retains one cycle and one spurious fixed point, so labels, answers, and live scoring are not entered | deployment closeout complete | PAPER-001 revised through Study 011 | scoring/interpretation record corrected through 2026-08-05

> **Current component status:** SUP-001 passes all offline P5/P9 supersession
> gates and the 35-turn reader ablation; no 120-turn run or adoption is automatic.

> **SUP-001 status:** `FACTUAL PASS - BYTE-IDENTITY CRITERION WITHDRAWN`.
> Explicit accessibility changes current-only retrieval 0/64->64/64,
> preserves 32/32 unchanged facts, recovers 64/64 histories, and removes all
> stale natural selections. Value-level interpretation gives C0 8/9
> and T1 9/9 with zero regressions. Explicit supersession passes integration;
> broader live evaluation remains a separate decision.

> **DMR arc status:** `STOPPED AT DMR-001 AND DMR-004`. Six implementation
> specifications separate event formation, typed pattern completion,
> encoding-context recurrence, query-obligation compilation, deterministic route
> control, and single-reader validation. DMR-001 stopped at G3, so there is no
> validated event substrate and DMR-002, DMR-003, DMR-005 and DMR-006 are
> blocked. DMR-004 was independent of those by its own header, ran to
> completion, and stopped on its sealed holdout, so there is no mechanical
> sufficiency signal either. Both formation and control are now closed by
> evidence rather than by dependency. The roadmap starts at
> `experiments/components/biological_memory/deterministic_retrieval/DMR_ARC_IMPLEMENTATION_ROADMAP.md`.

> **DMR-001 status:** `DEGENERATE_FORMATION - G3 FAIL - CHARACTERIZED`. On the
> 2,000-episode sealed holdout, 52 of 74 events close because the size cap
> binds, a forced fraction of 0.703 against a bar of 0.35. The drift predicate
> is precise and barely fires: all 20 of its holdout boundaries match an
> annotation, while none of the 52 forced boundaries do. The locked threshold
> of 0.70 sits above the holdout's 95th drift percentile yet fires on 18.5% of
> eligible development episodes, so an absolute drift threshold is not a
> transferable quantity and the safety cap becomes the partitioner. G1, G2 and
> PF1-PF10 pass; G4 and G5 were not evaluated.

> **DMR-001B status:** `ADAPTIVE_FORMATION_TRANSFERS_OFFLINE - CHARACTERIZED`.
> Replacing the fixed drift threshold with a percentile of the conversation's
> own recent drift holds the fire-rate swing between corpora at 1.42-1.65x
> across every cell of the registered grid, where the fixed rule swung tenfold
> or died. The size cap, set to 128 as a guard, never bound once in 3,724
> episodes. Worst-family agreement rises .419 to .487, though the 1,000-turn
> family falls .733 to .583. There is no sealed holdout and the ordering
> deviation `DEVIATION_001` is recorded, so this is not confirmatory and does
> **not** unblock DMR-002.

> **DMR-001C status:** `NO_BOUNDARY_EVIDENCE - G5 FAIL, G4 CONFIRMED`. A
> genuine sealed holdout: the rule was frozen at DMR-001B's anchor before
> LongMemEval was re-fetched, and the registration commit carries no
> implementation file. Across 50 unread haystacks, 11,453 episodes and 2,128
> real session seams, the relative bar holds its per-stream fire rate at a
> p95/p05 ratio of 1.67x, confirming transfer on real conversation where the
> fixed threshold swung tenfold on synthetic scripts. Boundary agreement fails:
> precision is .837 against a .186 base rate but recall is only .253, because
> `min_event_size` 5 cannot resolve seams in six-exchange sessions, so macro F1
> .387 loses to fixed chopping at .606. Macro F1 was a poor statistic for a
> corpus with an 18.6% base rate; that defect is recorded, not re-scored.

> **DMR-004 status:** `NO_MECHANICAL_SUFFICIENCY_SIGNAL - STOP - CHARACTERIZED`.
> A model-free precedence parser over query text alone, gated on Youden's J so
> that no base rate could carry it. On a sealed holdout of 180 queries labelled
> by two blind raters, J is 0.320 against a bar of 0.50 and the false-finite
> rate is 0.188 against 0.15, so the registered joint condition fails. `LOOKUP`
> recall 0.800, span integrity 1.000 and marker independence 0-of-48 all pass.
> The misses are structural, not scattered: 12 of 31 are *"which happened first,
> A or B"* - a bounded two-item obligation the registered class set cannot name,
> flagged in writing before the compiler existed and deliberately not patched -
> and 3 more are `HISTORY` queries the compiler classifies correctly but the
> registered `NOVELTY_ONLY` mapping scores as failures. Answering "I cannot
> tell" to everything scores 0.650 accuracy against the compiler's 0.706, which
> is why accuracy was barred from passing anything. Two raters agree with each
> other at J≈0.76. Per specification §12 a model-free adaptive controller is not
> authorized, and the compiler must not be replaced with a second model call.

> **SAL-001 status:** `NO_INDEPENDENT_PROXIMITY - CHARACTERIZED`. On 92
> held-out LongMemEval sessions, adjusted neighbor AUC is 0.416 (95% interval
> 0.351-0.484; one-sided p=0.991), raw AUC 0.300, prior 0.399, and next 0.477.
> Posthoc own-exchange surprisal is 0.621: surprise stays local rather than
> transferring to neighbors. P1-P4 capture is killed; P5/P9 supersession is
> unaffected.

> **SR-001 status:** `NO_BROAD_GAIN - CHARACTERIZED`. With source ranks fixed,
> spans reduce Q11 8/17->4/17 and targeted facts 19->17, producing 0 gains,
> 2 losses, and 22 ties. The historical span benefit requires span-level
> ranking or selection; representation alone does not earn an ablation.

> **TA-001 status:** `TARGETED_REGRESSION - CHARACTERIZED`. Q11 packed facts
> rise 7/17->9/17 and art 0/4->4/4 under matched 15-candidate and 32k limits,
> but 24 targeted queries yield 2 gains, 6 losses, and 16 ties. G5 blocks the
> 35-turn ablation, live evaluation, promotion, and adoption.

> **PS-003 status:** Safe ambiguity resolution passes, but G3 fails. Lookup
> remains `7/12`, identical to direct cosine and PS-002, with monetary at
> `1/3`. No answer generation, live score, promotion, or adoption follows.

> **E006-P3 closeout:** Query-anchored associative-frontier retrieval is
> `NO_DIFFERENTIATED_CUE - CHARACTERIZED`: 5/17 packed facts at primary
> `D=2, m=5`, versus A0's 7/17 and A1's 9/17; no targeted claim, live run,
> promotion, or adoption.

> **BA-001 causal audit:** `CHAIN_PACKING_ONLY_GAIN - CHARACTERIZED`. At
> matched 15-candidate volume, fixed-query and chained retrieval expose the
> same 9/17 facts; chaining packs 9 instead of 7. Radius-1 adjacency reaches
> turn 55 and all four art facts as an oracle ceiling. No live run or adoption.

> **E006-P3 Rev4 construct repair:** `PATTERNS_NOT_STORED - CHARACTERIZED`.
> Canonical Hebbian recurrence stores 0/119 real episode codes as fixed points
> and converges into six spurious attractors. Preflight stops at Part 1; the
> original P3 result is unchanged and Q11 is not entered.

> **PS-001 pattern-separated engram formation:**
> `SPARSE_ENGRAM_CANDIDATE_CHARACTERIZED`. Of nine deterministic sparse cells,
> only `(4096, 41)` passes G3-G5: `119/119` fixed points and exact recovery at
> one swap, 10%, 30%, and 50%. The union-biased degenerate cue cycles. This is
> code-space characterization only; no natural cue, retrieval, live run,
> promotion, or adoption follows.

> **PS-002 natural-language cue binding:** `NATURAL_CUES_NOT_BOUND -
> CHARACTERIZED`. The strongest label-blind cell reached stored engrams in
> `190/192` rounds, but one cue cycled and one reached a spurious fixed point.
> No cell emitted eight clean identities for every query, so relevance labels,
> answers, live scoring, promotion, and adoption were not entered.

> **PS-003 ambiguous cue resolution:** `LOOKUP_BINDING_INSUFFICIENT -
> CHARACTERIZED`. The selected five-probe, four-swap resolver emitted eight
> unanimous stored identities for all 24 queries while rejecting unsafe or
> disagreeing families. Lookup evidence remained `7/12`, exactly matching
> direct cosine and PS-002; monetary remained `1/3`. G4/G5, stress tests,
> answers, live scoring, promotion, and adoption were not reached.

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
| PS-001 | Sparse pattern-separated engram formation | CHARACTERIZED | One of nine cells stored and recovered 119/119 codes through 50% registered swaps; natural cues and retrieval remain untested |
| PS-002 | Natural-language cue binding to sparse engrams | STOPPED AT PART 1; CHARACTERIZED | Best cell reached stored codes in 190/192 rounds but retained one cycle and one spurious fixed point; relevance and answers not entered |
| PS-003 | Ambiguous natural-language cue resolution | G3 FAIL; CHARACTERIZED | Five-probe consensus safely emitted 8 identities/query, but lookup stayed 7/12, identical to cosine and PS-002; monetary 1/3 |
| BA-001 | Chained-retrieval and benchmark causal audit | CHARACTERIZED | Matched-volume chaining discovered no new facts; its 7/17 to 9/17 gain was packing only. Art was stored and directly recallable but not broadly cued |
| TA-001 | Radius-1 temporal-adjacency bridge | G5 FAIL; CHARACTERIZED | Q11 packed facts rose 7/17 to 9/17 and art 0/4 to 4/4, but targeted queries had 6 losses versus 2 gains; no ablation or live run |
| SR-001 | Source-rank-preserving extractive spans | G3 FAIL; CHARACTERIZED | Fixed-rank spans reduced Q11 8/17 to 4/17 and targeted matched facts 19 to 17, with zero gains. BA-001's span signal came from span-level ranking, not representation alone |
| SAL-001 | Independent surprisal-proximity diagnostic | G2 FAIL; CHARACTERIZED | Adjusted neighbor AUC was 0.416, raw 0.300, prior 0.399, and next 0.477. Own-exchange surprisal was 0.621 posthoc, so surprise marked content locally but did not transfer value to temporal neighbors |
| DMR-001 | Online event-context formation over pinned embeddings | G3 FAIL; DEGENERATE_FORMATION; CHARACTERIZED | The size cap, not the drift detector, did the partitioning: 52 of 74 holdout events closed on `max_event_size` and matched no annotation, while all 20 drift boundaries matched one. The locked threshold fires on 18.5% of development episodes and 1.2% of holdout episodes, so drift has no transferable scale. DMR-002 through DMR-006 are blocked |
| DMR-001B | Adaptive drift event formation | PASS; CHARACTERIZED | A percentile-of-recent-drift bar held the cross-corpus fire-rate swing at 1.42-1.65x where the fixed threshold swung tenfold, and the size cap never bound. Worst-family agreement .419 to .487; the 1,000-turn family fell .733 to .583. No sealed holdout, ordering deviation recorded, DMR-002 still blocked |
| DMR-001C | Sealed confirmation of the relative drift rule | G5 FAIL; G4 CONFIRMED | On 50 unread LongMemEval haystacks the frozen rule held its fire rate at a 1.67x p95/p05 ratio, confirming transfer. Precision .837 against a .186 base rate, but recall .253 and macro F1 .387 lost to periodic chopping at .606. min_event_size, not the threshold, is the binding constraint |
| DMR-004 | Deterministic query-obligation compiler | STOP; NO_MECHANICAL_SUFFICIENCY_SIGNAL | On 180 sealed queries labelled by two blind raters, Youden's J was .320 against a bar of .50 and the false-finite rate .188 against .15. LOOKUP recall .800, span integrity 1.000 and marker independence 0-of-48 passed. 12 of 31 misses are "which happened first, A or B", a bounded obligation the registered class set cannot name |
| SUP-001 | Explicit supersession lineage and accessibility | FACTUAL PASS; byte-identity criterion withdrawn | Current-only retrieval rose 0/64 to 64/64 with 32/32 unchanged and 64/64 histories. T1 scored 9/9 under numeric-value equivalence, with zero regressions and zero stale natural payloads; no larger run or adoption is automatic |

Full reports live under `experiments/study_NNN/`; external evaluation reports
live under `experiments/external/`.

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
failure, not a null. The vocabulary explanation remains unresolved. E006's
conditional chained-retrieval Part 2 ultimately completed under Rev5 after two
PF11 derivation failures. Its corrected zero-call Gram recurrence agrees with an
independent vector route to `9.5e-15`; all remaining gates pass. Chaining raises
single-shot `top_m` from 3/17 and deployed X0 from 6/17 to 9/17, but considers
15-20 candidates, selects 12 episodes, and still delivers 0/4 art facts. With no
targeted cosine traces, the result is `CHARACTERIZED`, not promoted or adopted.

E006 Part 3 then tested a query-anchored associative frontier over the exact
cosine top-8 graph. At the primary `D=2, m=5` cell, all three arms admitted 15
candidates, but the frontier carried only 5/17 facts, all civil, versus A0's
9 candidate/7 packed facts and A1's 9/9. Its best cell reached 6/17 and no cell
recovered an art fact. The registered disposition is
`NO_DIFFERENTIATED_CUE - CHARACTERIZED`; there is no targeted claim, live run,
promotion, adoption, or deployment change.

Rev 4 then repaired the construct rather than the result. A learned symmetric
Hebbian recurrence passed its synthetic reachability fixture, but none of the
119 population-centered episode codes was a fixed point. All trajectories
converged with falling energy into six spurious attractors. The result is
`PATTERNS_NOT_STORED - CHARACTERIZED` and stops at Preflight Part 1 before
one-bit recovery or Q11. Balanced feature marginals were not pattern separation;
the original semantic-frontier result remains unchanged.

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

## External Calibration

EC-001 ran the unchanged shipped component over all 500 questions in cleaned
LongMemEval-S and generated answers for a prospectively registered
seven-by-20 subset. The internal cosine inversion does not reproduce as a
dominant external pattern: the top four ranked sessions contain no evidence on
69 of 470 answerable questions (14.7%), while the median evidence-session rank
is 2. That rank result does not describe delivery: 401 questions have evidence
in the top four, but only 96 retrieve any evidence session. Every block is
truncated; median composition is 16 recency, 0 non-recency K, and 1 coverage
exchange. Of 109 session hits, 91 come from recency. Exact answer-turn
availability is 79 of 470 (16.8%).

End-to-end scoring is deliberately bounded. The equal-quota subset scores
28/140 (20.0%), and post-stratification to the verified benchmark population
gives 12.22%. Both are **Codex-substituted integrity scores**, not official or
benchmark-comparable LongMemEval scores: API access to the pinned evaluator was
unavailable, so Amendment 010 substituted Phi, Mistral, and hosted GPT-5.4
raters with hosted GPT-5.5 AI adjudication. Multi-session and temporal reasoning
score 0/20; abstention scores 17/20 even though the component emits no absence
signal on any of 500 questions. F3 is therefore retired as a component
requirement under this tested reader, not marked solved as a component
capability. The registered exact
availability-minus-correctness gap is −2.54 percentage points, opposite the
predicted large positive gap.

See `experiments/external/longmemeval/EC_001_REPORT.md`.

EC-002 then held the 500 stores, exact retained vectors, threshold, selector,
and 32,000-character budget fixed and changed only packing order from
recency-first to K-first. Any evidence-session recall rose from 109/470 to
261/470: 152 paired gains and zero losses. Exact-answer-turn-any availability
rose from 79/470 to 196/470, with 119 gains and two losses. All blocks remained
truncated; delivered K episodes rose from 26 to 476. This confirms
recency-first budget exhaustion as a causal gate under the EC-001 adaptation.
It is offline availability evidence, not reader accuracy, and does not
authorize production promotion.

See `experiments/external/longmemeval/EC_002_REPORT.md`.

IC-001 asked the same question of this program's own corpus, where every study
on record ran recency-first. It replayed the corrected 121-turn run under both
orders on frozen candidate identities — no vector re-derived, no model call —
after its B0 arm reproduced the committed deployed 6-of-17 result exactly,
episode identities and payload digest included. Under the deployed order the
similarity path delivered **zero episodes and zero characters at all eight
probes**; recency consumed the whole budget every time. Under K-first it
delivers nine episodes, Q11 availability rises 6/17 to 7/17 with one gain and
no losses, and the eight targeted probes rise 14/21 to 18/21 with four gains
and no losses. The Q11 window fits twelve episodes in 31,863 characters against
the deployed eight in 31,946. The registered verdict is Branch A: part of what
PAPER-001 §5 attributed to selection is attributable to packing priority. It is
availability on one probe, authorizes no re-run of the arc, and its cache
clause is unmet pending an amendment.

See `experiments/internal/packing_priority/IC_001_REPORT.md`.

Study 011 put that finding on the arc instrument, live: four 121-turn runs at
one seed — recency alone, similarity alone, both with similarity first, and the
deployed order — behind a binding offline pre-test that no previous study had
run, and scored blind by three raters who never saw which arm produced which
answer. **The suppression is confirmed and the correction is rejected.** The
deployed arm scored identically to the recency-only arm on all thirteen
questions, with the same availability and byte-identical windows at three
consecutive late probes: in deployment the similarity tier contributes nothing
at all. Giving it first claim on the budget delivered thirteen K-path episodes
against one, raised Q11 availability 9/17 to 10/17 and targeted 7/21 to 10/21 —
and **scored 7.0 against 8.0**. Bar B1 fired; the correction is not adopted.
The loss is late-probe rather than uniform, and both losses at the marine probe
fall on a turn that holds no similarity candidate at all, so the displacement
mechanism is consistent but not established. Three of six registered predictions
are refuted outright and a fourth is withdrawn as unscorable.

**And then the instrument was measured, and it does not resolve any of it.**
Amendment 001, authorized August 9, ran the deployed configuration five times
under an identical corpus, settings, seed and runtime, back to back in one
server process. Four scored **8.0**; one scored **11.0**. The band is **3.0
points on a 13-point rubric**, against a decision rule committed before the
replicates ran. It is not a spread but a switch: four of the five are
byte-identical across all 121 turns, and the fifth — the only one that met an
empty server slot — diverges at turn 1 and never re-converges, reproducing the
exact divergence that raised the amendment. Applied uniformly and in both
directions, **Study 009's 3.0-point memory-tier contrast, LV-001's −2.0 kill and
Study 011's own −1.0 kill are all inside the band and none is demonstrated.**
Only the 3.5-point corrected series exceeds it, and exceeding a band is not the
same as being demonstrated. Not demonstrated is not refuted: these may be real,
and one run per arm could never have said. Every offline result — delivery
counts, character accounting, packing measurements, the replays below — is
untouched, because those are counts and identities rather than scores. B1 stays
fired and the packing correction stays unadopted; the band may not be cited to
revive it.

**Mechanism analysis after the mapping was unsealed found that the tier is not
what the arc calls it.** The N tier does not select by recency. Its key sorts the
whole store by delivery history — never-delivered material first, then the
episode delivered longest ago — so it is a least-recently-delivered coverage
rotation, and the only place recency appears is the name of the block it renders
into. Replay reproduces the live ranking on 120 of 120 testable turns per arm: the
delivered set overlaps a true window of the same size by 0.29, 36% of deliveries
are older than the cap could reach, and the rotation touches every one of the 120
reachable episodes. It survived eleven studies because for the first 32 turns the
tier genuinely is a window, and after that its first line is still the previous
turn. Three different rules carry the name, and the only genuine window is in the
extracted library, which no scored live study ran. Contrasts where both arms carry
the tier — including B1 — are untouched; what changes is that the similarity tier
was being asked to improve on a baseline that already reaches everything.

**And the rule before it was worse.** Every live run through Study 010 used a
different key, which ranks the freshest delivery highest — and `retrieve()`
refreshes everything it delivered, so the block re-selects itself every turn.
From turn 11 it holds the same nine episodes, source turns 1 through 9, plus
whichever episode has not been delivered before. Study 009's Arm S held that for
111 consecutive turns; Study 010's arms held it across 999. Replay reproduces
the logged ranking exactly on 17 run directories, of which 12 lock. Mean overlap
with a true window of the same size 0.205; 111 of 120 episodes delivered exactly
once. Study 009's 3.0-point LTM result does not change — Arm L carries the
identical block turn for turn, so the contrast still isolates LTM — but the
baseline it beat was not a recency baseline. Nothing in the program establishes
what a correctly-implemented window would score, in either direction.

The determinism spot-check bounds all of it. Re-running one arm under identical
settings gave a byte-identical prompt at turn 1 and a **different answer** —
seed 5005, `--parallel 1`, speculative decoding off. The mechanism reproduces
exactly where it can be tested, but that is one turn, because a differing
answer changes the store and every prompt after it. So a one-point difference
on a 13-point rubric, one run per arm, sits inside an unmeasured noise band:
B1 fired on the committed numbers as a registered bar must, and the defensible
claim is that the correction did not demonstrate an improvement, not that it is
worse. The program's standing rule requiring a byte-identical seeded prefix
rerun is not satisfiable on this runtime. Offline results are unaffected and
reproduce exactly.

See `experiments/study_011/study_011_report.md`.

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
