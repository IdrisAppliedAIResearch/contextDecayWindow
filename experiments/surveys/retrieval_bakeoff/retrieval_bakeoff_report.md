# Retrieval Bakeoff Final Report

**Status:** COMPLETE THROUGH THE CORRECTED 121-TURN TIER 6 RUN

**Pre-registration SHA:** `b60b7084741eb5d30298261076b4bca78abe713a`

**Scope decision:** The optional 1,000-turn confirmation was not run. The
repository owner reserved that compute decision until after review of the
corrected 121-turn result.

## Outcome

The bakeoff does not support replacing the retained LTM tier with a single
retrieval method. At the clean same-seed 121-turn comparison, Study 009 Arm S
scored 9.0/13, corrected widened STM scored 11.0/13, and Study 009 Arm L scored
12.0/13. Matching L's delivered character volume recovered two of the
three-point gap, but not the final point. Volume mattered; it was not a complete
substitute for relevance and selection behavior.

The corrected Tier 6 arm also scored 1.0 on Q14. Its losses were Q4 and Q11;
Q11 contained 13/17 correctly attributed items, one below the binary threshold.
The registered score rule makes a 1,000-turn confirmation eligible, but owner
review is required before launch.

## Tier Findings

| Tier | Status | Finding |
|---|---|---|
| 0 | PASS | Leakage, historical fidelity, and source-tree integrity passed. |
| 1 | COMPLETE | Raw-store reachability topped out at 8/17; the added N/K reinforcement hypothesis was not confirmed in either preserved S log. |
| 2 | COMPLETE WITH PROVENANCE VIOLATIONS | M3, M4, M5_span, and M6 advanced mechanically, but provenance violations limit interpretation. |
| 3 | COMPLETE | Oracle routing improved recall by only 6.09%; the registered decision was not to build routing. |
| 4 | COMPLETE AT 4A | No graph configuration cleared the binding advancement gate, so 4B was not run. |
| 5 | COMPLETE | Recall improved with budget; ANN recall degraded at synthetic scale; progressive search did not solve the old-fact problem. |
| 6 | COMPLETE AT 121 TURNS | Corrected widened STM scored 11.0/13 versus S 9.0 and L 12.0. |

## Integrity And Amendments

Twelve standalone amendments resolved executable-protocol details, corpus
ordering, Tier 5 scope, Tier 6 calibration and scoring, the 121-first decision,
the T1.3 reinforcement hypothesis, and the corrected N-order rerun. The locked
pre-registration was not edited.

The first Tier 6 run scored 6.5 but violated the registered offline/live N-order
equivalence. It remains preserved as a diagnostic, is not scored as valid
evidence, and is excluded from the architectural conclusion. The corrected run
used a committed character widening rule, a passing 111-turn equivalence gate,
two byte-identical 35-turn ablations on fresh servers, a sealed 121-turn run,
three calibrated blind scoring passes, and independent fourth-pass
adjudication before mechanism review.

## Artifacts

- Corrected score: `tier6/evaluation_corrected_121/blinded_scores.json`
- Corrected mechanism report:
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
- Gates, runs, scores, and analyses committed: PASS
- Pull request: PENDING AT REPORT COMMIT
