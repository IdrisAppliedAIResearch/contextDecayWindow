# Study 004 — Synthetic End-to-End Verification Report

**Date:** July 21, 2026
**Status:** PASS
**Accepted run:** `synthetic_verification_005`
**Condition:** `iterative`
**Fixture:** `synthetic_study004_script.json` (fixture-only; not Study 004 run data)
**Study 004 pre-registration SHA:** `1b9eb204e32b6b7cb32dfce4cb647cfc7f0e4d0f`

## Result

The 22-turn synthetic script completed through the full Study 004 architecture with real Qwen3-Embedding-0.6B embeddings, real consolidation, real Qwen3.6-27B-UD-Q6_K_XL emotional scoring and generation, and real STM ∥ LTM arbitration. All S4_006 checks passed. This result restores the S4_006 gate after the first S4_007 ablation exposed recency-overlap starvation; it authorizes a fresh S4_007 retry, not the full 120-turn run.

The accepted run produced four canonical topics. Promotion batches ran at turns 5, 9, and 13, followed by the designated end-of-session flush at turn 18. Before the flush batch, LTM contained episodes from two distinct topics. Turns 19–22 formed the probe block, with consolidation firing at turn 20.

`synthetic_verification_005` ran after remediation commit `0b1f989`. Unlike the superseded run, it explicitly exercised LTM-over-N placement: promoted episodes began reaching arbitration at turn 6, and 34 individual LTM-context rows were emitted without duplication. This directly verifies the integration path that failed in `ablation_35_001`.

## Verification

| Check | Evidence | Result |
|---|---|---|
| Parallel retrieval | The file-backed path used the jointly awaited STM and LTM tier queries. Both tiers returned arbitration candidates together on turns 15–18 and 21–22; the concurrency barrier regression test also passed. | PASS |
| Dedup | Turn 21 received seven STM and three LTM candidates, removed one duplicate, and emitted nine unique episodes. The survivor carried `both` provenance and appeared once. | PASS |
| Provenance in context | Turn 15 rendered STM-only episodes under `<retrieved_stm>` and promoted episodes under `<retrieved_ltm>` with `promoted_at_turn` and `trigger_type`. The 34 individual LTM-context rows exactly equal the sum reported by the per-turn arbitration log. | PASS |
| Degenerate fallback | At turn 6, `stm_candidates=0` and `ltm_candidates=1`. The final episode-ID order exactly matched the direct LTM-only similarity ranking. No STM-empty branch exists in arbitration. | PASS |
| Association decoupling | The turn-18 frozen snapshot contained two LTM topic centroids. For all six evaluated episodes, logged Association exactly matched an independent max-over-topic-centroids recomputation and differed from global-centroid Association. Maximum recomputation error was `0.00e+00`. | PASS |
| Bypass exclusion | No promotion or filter-trigger row attributed an all-or-nothing event to Association. Observed all-or-nothing triggers were Novelty or Repetition only. | PASS |
| Turn-111-equivalent flush | At turn 18, `topic_4` evaluated six episodes and promoted one through the shared `end_of_session_flush` path. No promotion event occurred during turns 19–22. | PASS |
| Probe guard | At turn 20, three proposed probe-bridged merges were rejected and logged as `probe_bridge_blocked`; connecting similarities were `0.566137`, `0.461988`, and `0.459657`. | PASS |
| Cross-domain merge instrument | `consolidation_purity.csv` was created with all registered fields. No cross-domain merge was accepted in the run. The clean same-domain and deliberately mixed-domain instrumentation regression tests both passed. | PASS |
| Tagged rendering | All five registered blocks appeared exactly once in every one of the 22 constructed prompts. Empty rule, recency, STM, and LTM blocks used self-closing tags. | PASS |
| Logs | `arbitration_events.csv` contains the exact registered header and 22 data rows. `ltm_context_episodes.csv`, promotion analysis, purity, retrieval, turn, metric, snapshot, and constructed-prompt artifacts were all populated. | PASS |

## Association recomputation detail

The batch snapshot used for the turn-18 flush contained promoted episodes from `topic_1` and `topic_2`. The diagnostic `global_association` column records the counterfactual Study 003 score without influencing any promotion decision.

| Episode turn | Per-topic max A | Global-centroid A | Unequal? |
|---:|---:|---:|---|
| 13 | 0.316921 | 0.401561 | Yes |
| 14 | 0.372522 | 0.395555 | Yes |
| 15 | 0.339301 | 0.416267 | Yes |
| 16 | 0.421405 | 0.382531 | Yes |
| 17 | 0.307902 | 0.406377 | Yes |
| 18 | 0.290955 | 0.387748 | Yes |

This confirms that the multi-topic case was exercised rather than the documented single-topic complement degeneracy.

## Breadth behavior

The miniature breadth queries at turns 19 and 22 both elicited all four planted records:

| Code | Planted number | Responsible person |
|---|---|---|
| AX-17 | 43.7 milliseconds | Dr. Livia Noor |
| BX-29 | 68 percent hydration | Tomas Ilyin |
| CY-41 | 14-day escrow release | Counsel Amara Voss |
| DZ-53 | 17.2 degrees Celsius | Ren Ito |

This is an observability check for the synthetic gate, not a substitute for the pre-registered Study 004 rubric scoring.

## Test evidence

The remediation-focused retrieval, tagged-context, consolidation, and topic-manager suite completed with **58 passed**. The repository-wide suite completed with **476 passed**. Coverage includes the concurrency barrier, direct LTM-only equality, no-double-vote retrieval path, LTM-over-N provenance retention, tagged-context snapshots, monotonic topic labels, frozen Association snapshot, bypass exclusion, flush ordering, probe-bridge rejection, and clean/mixed-domain purity tests.

## Attempt disposition

- `synthetic_verification_001` failed before turn 1 because the Windows console used a non-UTF-8 output encoding. It produced no study observations and is excluded.
- `synthetic_verification_002` and `synthetic_verification_003` were partial launch-orchestration attempts that overlapped on the single-slot inference server. Both process trees were stopped and both attempts are excluded.
- `synthetic_verification_004` completed all 22 turns and originally closed S4_006. It is superseded because the later real-script ablation exposed an LTM-over-N integration case that run 004 did not catch.
- `synthetic_verification_005` ran alone on remediation commit `0b1f989`, completed all 22 turns in 1 minute 58 seconds, and is the sole accepted synthetic run for the current architecture.

Synthetic run directories remain ignored test artifacts. The fixture, runner entry point, implementation changes, tests, and this report are committed; no synthetic output is treated as Study 004 run data.

## Decision

**S4_006 PASS — all registered mechanisms fired and all checks passed. Proceed to S4_007 35-turn ablation.**
