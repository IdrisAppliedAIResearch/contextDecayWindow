# Retrieval Bakeoff Final Report

**Status:** COMPLETE THROUGH THE CORRECTED 121-TURN TIER 6 RUN

**Pre-registration SHA:** `b60b7084741eb5d30298261076b4bca78abe713a`

## Outcome

Query-time selection over the tested raw stores did not recover what write-time
formation missed: T1.2's best registered 32,000-character retrieval block
surfaced **8/17** Q11 facts, below the **11/17** formation-era ceiling it was
intended to surpass. Observed-co-activation graph retrieval did not clear its
Tier 4A advancement gate, so extraction-based Tier 4B never ran. Query routing
had an oracle upper bound of **6.09%**, below the registered 10% build
threshold. Three central pillars of the proposed architectural pivot therefore
did not advance: query-time selection sufficiency, explicit associative
structure, and routing.

What survived is delivered volume. In the clean same-seed 121-turn comparison,
Study 009 plain STM scored **9.0/13**, corrected character-matched widened STM
scored **11.0/13**, and Study 009 LTM scored **12.0/13**. Widening recovered two
of the three points, but did not reproduce LTM. The L-versus-widened-STM gap is
one binary rubric item wide: widened STM produced **13/17 correctly attributed
Q11 facts**, but the locked binary Q11 criterion scored both 13/17 and 0/17 as
zero. The 11.0 is retained without rescoring and must always be reported beside
the 13/17 item count.

The defensible conclusion is negative: the retained LTM tier is not replaceable
by any single retrieval method tested. This survey does not validate a new
architecture. It identifies a more specific problem: 17-fact enumeration has
now failed under write-time formation, query-time retrieval, and increased
delivery volume.

## Reconciling 8/17 And 13/17

The two figures do not measure the same object.

| Figure | Artifact | Measurement |
|---|---|---|
| 8/17 | `tier1/tier1_results.json`, `reachability.primary_ceiling` | Offline content in one M4 block retrieved from the compact Study 007 L store for the development turn-120 query, under an exact 32,000-character budget. |
| 13/17 | `tier6/evaluation_corrected_121/blinded_scores.json`, `scores.Q11` | End-to-end facts in the model's generated turn-120 answer after a live 121-turn widened-STM conversation with a roughly 60,000-character retrieval target. The adjudicator credited 13; the mechanical layer found 12 literal items and the adjudicator accepted “Fed” as Federal Reserve. |

The live answer can contain facts not present in the final retrieval block,
including facts repeated in earlier probe answers retained by widened STM.
Therefore 13/17 does not overturn T1.2's 8/17 single-block retrieval result, and
8/17 must not be described as a universal ceiling on end-to-end answer content.

## Q11 Surrogate Audit

Q11 cannot serve as a clean architectural bar until the mechanism can make
14/17 facts available. Its binary threshold can fail while the underlying
breadth property is nearly present: 13 correctly attributed facts and zero
facts receive the same score. In Tier 6, this threshold creates the entire
reported one-point gap between widened STM and LTM.

The score remains locked at 11.0/13. The architectural interpretation rests on
the paired observation, not the scalar alone: **11.0/13 with 13/17 Q11 facts,
versus LTM 12.0/13**. This is evidence that volume helps and that the tested raw
retrieval did not strictly match LTM under the locked rubric; it is not evidence
of a large capability gap.

## Tier Verdicts

| Tier | Verdict | Finding |
|---|---|---|
| 0 | PASS | Leakage, historical fidelity, and source-tree integrity passed. |
| 1 | NEGATIVE FOR THE PIVOT | All 17 facts existed in raw stores, but the best registered 32k retrieval block surfaced 8/17. The added N/K reinforcement hypothesis was not confirmed. |
| 2 | BOUNDED MECHANICAL RESULT | M3, M4, M5_span, and M6 advanced on exact-provenance recall. Sixty-two of 528 rows contained wrong-turn/role lexical matches, but zero violating candidates were credited; see `tier2/provenance_audit.md`. No unqualified semantic-retrieval claim is valid. |
| 3 | CLOSED | Oracle routing improved recall by 6.09%; do not build routing. |
| 4 | CLOSED AT 4A | No explicit graph configuration cleared advancement. Tier 4B did not run, so extraction-based novelty was never tested. |
| 5 | MIXED DIAGNOSTIC | Recall improved with budget; ANN recall degraded at synthetic scale; progressive search did not solve old-fact retrieval. |
| 6 | VOLUME HELPS, DOES NOT REPLACE LTM | Corrected widened STM scored 11.0/13 with 13/17 Q11 facts, versus STM 9.0 and LTM 12.0. |

## Amendment Legitimacy

“Before results” is recorded per amendment, not asserted globally.

| Amendment | Before affected result? | Legitimacy note |
|---|---|---|
| 001 | Yes | Executable offline protocol locked before harness code and registered results. |
| 002 | No | Triggered by the first T1-T3 output; corrected arithmetic and added diagnostic attribution without rerunning retrieval or easing advancement. |
| 003 | Yes | Graph execution details locked before graph implementation and results. |
| 004 | Yes | Clarified the 121/1,000 corpus order before Tier 6 implementation and live output. |
| 005 | Yes | Tier 5 policy locked after upstream Tier 4, but before Tier 5 implementation and results. |
| 006 | Yes | Comparison-scope repair locked before Tier 5 execution. |
| 007 | Yes | Tier 6 character calibration target locked before implementation, ablation, and live scoring. |
| 008 | No | Triggered by an invalid shared-server ablation mismatch; repaired determinism before any valid ablation or live run. |
| 009 | Yes | New-arm scoring triggers locked before the first Tier 6 live run and score. |
| 010 | No | Written after the invalid run's 6.5 score; governed only a proposed 1,000-turn extension and did not alter the 121-turn score. |
| 011 | No | Written after 6.5; changed sequencing to evaluate the short run before spending more compute, without changing its score. |
| 012 | No for original T1.3/T6; yes for supplement/rerun | Added the reinforcement hypothesis after the original T1.3 result and authorized a new diagnostic. It also repaired the discovered N-order violation before the corrected equivalence gate, ablations, run, or score. |

The Tier 6 calibration and new-arm scoring amendments were not raised after the
6.5 score: Amendments 007 and 009 preceded the first live run. Amendments
010-012 were post-result and are labeled as such.

## Scope And Numbering

The locked pre-registration defines conceptual **Tiers 0 through 6**. It does
not register Tiers 7-9. The `RB_001`-`RB_009` labels belonged to the execution
sprint/task layer, not to additional scientific tiers; the two namespaces do
not map one-to-one. This report closes the registered Tier 0-6 battery,
including gate-closed work, rather than claiming that three unreported tiers
exist.

The bakeoff is exploratory and not arc-numbered. No result in it becomes
confirmatory through repetition. The optional 1,000-turn run is held. If ever
authorized, its defensible question is narrower: **does the observed volume
effect persist or invert when rendering expansion saturates the context
window?** That question requires a new pre-registration and cannot be described
as confirmation of this survey.

## Integrity

The first Tier 6 run scored 6.5 but violated the registered offline/live N-order
equivalence. It remains preserved as a diagnostic, is not scored as valid
evidence, and is excluded from the architectural conclusion. The corrected run
used a committed character-widening rule, a passing 111-turn equivalence gate,
two byte-identical 35-turn ablations on fresh servers, a sealed 121-turn run,
three calibrated blind scoring passes, and independent fourth-pass
adjudication before mechanism review.

Study 010's post-stop continuation and the invalid Tier 6 diagnostic are
classified separately in `decisions/DECISION_001_post_stop_exploration.md`.

## Next Question

The next question is no longer where selection should live. It is why
high-cardinality enumeration breaks when targeted recall succeeds. A new study
should isolate enumeration load rather than introduce another memory component:
hold source facts, retrieval content, and delivered characters fixed; vary only
the number of independently attributable facts requested, their domain spread,
and whether the model must enumerate or answer targeted subqueries. Measure the
item-level recall curve before applying any binary threshold. That design can
separate retrieval omission, context utilization, and response-planning
capacity.

## Artifacts

- Tier 1 reachability: `tier1/tier1_results.json`
- Tier 2 provenance audit: `tier2/provenance_audit.md`
- Corrected Tier 6 score: `tier6/evaluation_corrected_121/blinded_scores.json`
- Corrected Tier 6 mechanism report:
  `tier6/analysis_corrected_121/tier6_121_mechanism_evaluation.md`
- Corrected run: `tier6/runs/tier6_live_121_corrected_001/`
- Invalid diagnostic run: `tier6/runs/tier6_live_121/`
- T1.3 supplement: `tier1/t1_3_reinforcement/t1_3_reinforcement_report.md`
- Amendment record: `amendments/`

## Closeout Checklist

- Pre-registration SHA recorded: PASS
- Root README updated: PASS
- Root AGENTS digest updated: PASS
- ERRATA review: NO CHANGE REQUIRED
- Memory update added: PASS
- Gates, runs, scores, analyses, and bounded provenance audit committed: PASS
- Pull request: OPEN, SAME SURVEY BRANCH
