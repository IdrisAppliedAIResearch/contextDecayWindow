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
one rubric item wide, and that item is **Q4**, not Q11. LTM received Q4's title,
artist, patron, and year and scored 1.0; widened STM received none of those four
facts and scored 0.0. Both arms scored zero on Q11. Widened STM nevertheless
produced **13/17 correctly attributed Q11 facts**; the 11.0 is retained without
rescoring and must always be reported beside that item count.

The bakeoff also produced the memory track's first clean positive result:
**widened raw-store STM delivered all six facts that every tested write-time
formation policy had missed, and the model used five in correct targeted
answers.** Raw delivery solved the program's hardest documented availability
failure. This result is stronger and more specific than the aggregate 11.0:
formation blindness was not intrinsic fact unreachability.

The defensible conclusion is therefore split. The retained LTM tier is not
replaceable by any single retrieval method tested, so the proposed architecture
does not advance as a wholesale replacement. But raw, non-entity-gated delivery
solved a failure that query-blind formation, entity counts, density, and
word-level IDF did not. The residual LTM advantage is a targeted Q4 selection
failure. Separately, 17-fact enumeration remains a shared failure.

The best-supported one-line verdict for the system as run is: **the LTM tier's
only demonstrated advantage over matched raw volume is keeping the older Q4
bundle renderable.** This is evidence for a primacy function under the current
renderer, not yet proof that a distinct primacy mechanism is required. A known
structural serialization-expansion risk may have reduced how many widened-STM
episodes fit; its Q4 effect has not been measured and that causal null must be
tested before building a pinned tier.

## Reconciling 8/17 And 13/17

The two figures do not measure the same object or the same 17-item denominator.

| Figure | Artifact | Measurement |
|---|---|---|
| 8/17 | `tier1/tier1_results.json`, `reachability.primary_ceiling` | Offline content in one M4 block retrieved from the compact Study 007 L store for the development turn-120 query, under an exact 32,000-character budget. |
| 13/17 | `tier6/evaluation_corrected_121/blinded_scores.json`, `scores.Q11` | End-to-end facts in the model's generated turn-120 answer after a live 121-turn widened-STM conversation with a roughly 60,000-character retrieval target. The adjudicator credited 13; the mechanical layer found 12 literal items and the adjudicator accepted “Fed” as Federal Reserve. |

The live answer can contain facts not present in the final retrieval block,
including facts repeated in earlier probe answers retained by widened STM.
Moreover, the six formation-blind plant concepts are not the Tier 6 Q11
rubric's 17 atomic items. Therefore 13/17 does not overturn T1.2's 8/17
single-block retrieval result, and 8/17 must not be described as a universal
ceiling on end-to-end answer content.

## Primary Positive Result: Formation-Blind Facts

These six facts were the program's hardest repeated failure. They contain rare
technical phrases whose component words are common; prior formation policies
based on entity counts, density, and word-level IDF did not select them. The
registered graph-extraction gate also recorded that spaCy found zero entities
in the `Vampyroteuthis infernalis` span, so an entity-gated index could not
construct a path to that evidence.

Widened STM delivered all six at their relevant probes. It correctly used lead
white and ultramarine glaze on Q5, marine snow on Q7, and photophores and mantle
margin on Q8. Dual mandate was present in the Q11 prompt but omitted from the
answer. Raw delivery therefore achieved **6/6 availability and 5/6 correct
use** on the exact set that defeated formation.

This is direct evidence for the program's differentiation claim: preserving
raw spans and retrieving without an entity-extraction gate can reach evidence
that entity-centric construction would omit. It is not a direct HippoRAG
benchmark, so no comparative performance claim is made. The arm-by-arm audit
is `tier6/analysis_corrected_121/formation_blind_intersection.md`.

## Q11 Surrogate Audit

Q11 cannot serve as a clean architectural bar until the mechanism can make
14/17 facts available. Its binary threshold can fail while the underlying
breadth property is nearly present: 13 correctly attributed facts and zero
facts receive the same score. It does not, however, create the reported
one-point gap: LTM also scored zero on Q11. The gap is Q4.

The score remains locked at 11.0/13. The paired observation is still required:
**11.0/13 with 13/17 Q11 facts, versus LTM 12.0/13 with the same binary Q11
failure**. This is evidence that volume helps. The remaining scored difference
is narrower: widened STM failed to select Q4's identity bundle.

## Q4 Primacy Trace

Q4's complete title-artist-patron-year bundle was planted at turn 55, 60 turns
before the turn-115 probe; the patron was reiterated at turn 60. In widened
STM, turn 55 ranked 27th inside the 32-item N candidate cap. The fixed
60,595-character payload filled after the first 15 N episodes, excluding turn
55 from the rendered window. Its cosine to the Q4 probe was 0.166, below the
0.48 K threshold, so similarity retrieval did not rescue it.

This is a structural N-first packing failure after a late N rank, not raw-store
absence and not exclusion from the N candidate cap. LTM's residual point came
from keeping that older identity bundle renderable. The evidence therefore
supports a primacy interpretation under the renderer used in the bakeoff, not
a demonstrated advantage from graph structure, routing, or another selection
mechanism. It does not distinguish a necessary primacy mechanism from a
serialization artifact that caused only 15 of 32 N candidates to fit.

## Tier Verdicts

| Tier | Verdict | Finding |
|---|---|---|
| 0 | PASS | Leakage, historical fidelity, and source-tree integrity passed. |
| 1 | NEGATIVE FOR THE PIVOT | All 17 facts existed in raw stores, but the best registered 32k retrieval block surfaced 8/17. The added N/K reinforcement hypothesis was not confirmed. |
| 2 | BOUNDED MECHANICAL RESULT | M3, M4, M5_span, and M6 advanced on exact-provenance recall. Sixty-two of 528 rows contained wrong-turn/role lexical matches, but zero violating candidates were credited; see `tier2/provenance_audit.md`. No unqualified semantic-retrieval claim is valid. |
| 3 | CLOSED | Oracle routing improved recall by 6.09%; do not build routing. |
| 4 | CLOSED AT 4A | No explicit graph configuration cleared advancement. Tier 4B did not run, so extraction-based novelty was never tested. |
| 5 | MIXED DIAGNOSTIC | Recall improved with budget; ANN recall degraded at synthetic scale; progressive search did not solve old-fact retrieval. |
| 6 | POSITIVE ON FORMATION-BLIND AVAILABILITY; DOES NOT REPLACE LTM | Widened STM delivered all six formation-blind facts and correctly used five. It scored 11.0/13 versus STM 9.0 and LTM 12.0; Q4 is the residual gap. |

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

The immediate question is whether Q4's exclusion reflects a mechanism gap or
the known structural expansion of episodes during serialization. That defect
must be measured and repaired independently, with a byte-identical pre-fix
replay and an identity-preserving post-fix replay. Then an offline, pre-committed
packing analysis must test whether the turn-55 bundle enters the corrected
window across the re-derived budget range. Neither step changes this bakeoff's
score or observed result.

Only if Q4 remains excluded after that null should a new pre-registered study
compare a small, always-rendered durable-fact set against widened raw STM under
the same context budget. It should measure update correctness, stale-fact
replacement, pin budget, and targeted recall, while adding no graph, router,
coverage selector, or inference call. If corrected serialization admits Q4,
there is no basis for a pinned-tier study; if Q4 enters only under an achievable
budget or packing change, that cheaper mechanism should be studied instead.

Enumeration is a second, architecture-spanning question, not the explanation
for the one-point gap. It merits a separate design that fixes delivered content
and varies requested fact count to distinguish utilization and response
planning from retrieval omission.

## Artifacts

- Tier 1 reachability: `tier1/tier1_results.json`
- Tier 2 provenance audit: `tier2/provenance_audit.md`
- Corrected Tier 6 score: `tier6/evaluation_corrected_121/blinded_scores.json`
- Corrected Tier 6 mechanism report:
  `tier6/analysis_corrected_121/tier6_121_mechanism_evaluation.md`
- Formation-blind plant and score-gap audit:
  `tier6/analysis_corrected_121/formation_blind_intersection.md`
- Q4 machine-readable exclusion trace:
  `tier6/analysis_corrected_121/q4_exclusion_trace.json`
- Q4 follow-up scope decision:
  `decisions/DECISION_002_q4_rendering_followup_scope.md`
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
