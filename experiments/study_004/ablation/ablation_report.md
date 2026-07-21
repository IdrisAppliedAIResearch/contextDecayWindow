# Study 004 — 35-Turn Ablation Report

## Attempt 1: `ablation_35_001`

**Date:** July 21, 2026
**Code under test:** `94471c4` (`Verify Study 004 synthetic end-to-end gate`)
**Status:** NO-GO

The real-script ablation completed all 35 iterative turns. The registered runtime, consolidation, first promotion boundary, purity instrumentation, tagged prompts, and per-turn logs behaved as expected. The read-path integration gate failed: although turn 31 promoted nine episodes, turns 32–35 emitted zero LTM arbitration candidates and no episode reached `<retrieved_ltm>`.

| Check | Expected | Actual | Pass? |
|---|---|---|---|
| GPU speed (UD-Q6_K_XL) | > 30 tok/s | 36.63 minimum; 38.72 average tok/s | Yes |
| Consolidation fires | At least once | Fired at turns 10, 20, and 30; one same-domain pair merged at turn 20 | Yes |
| Topic count at turn 35 | Trending toward the [3,10] band pace | Two canonical topic IDs after two of four scripted domains began | Yes |
| Cross-domain merges | Zero (`consolidation_purity.csv`) | Zero | Yes |
| First LTM promotion | At ≈ turn 31 | Turn 31: 30 episodes evaluated, 9 promoted | Yes |
| Decoupled Association computed | Max-per-topic Association logged | The first batch correctly used the registered empty-LTM case, so all 30 A values were 0.0. The plan's single-topic parenthetical is inapplicable before the first write; S4_006 independently verified the multi-topic max. | Yes |
| Parallel retrieval active | Both tiers queried from ≈ turn 32 | Both tier functions executed, but all LTM results were suppressed before arbitration by overlap with N | No |
| LTM episode reaches context | ≥ 1 post-31 LTM-provenance episode | Zero LTM-context episodes on turns 32–35 | **No** |
| Dedup correct | No episode ID twice; sane duplicate count | No duplicate IDs; all counts zero because no candidate survived | Yes, not exercised here |
| Degenerate fallback | Low-STM turn or S4-T-010 re-run | S4-T-010 direct equality test passed in the 473-test pre-run suite | Yes |
| Tagged blocks | All five each turn; empties self-closing | All five on all 35 prompts; empty LTM blocks self-closing | Yes |
| `arbitration_events.csv` | Populated, all fields | Exact header plus 35 rows | Yes |
| No promotion during any probe | N/A below turn 112 | No probe turns in range | N/A |

### Root cause

All nine turn-31 promotions were also members of the ten-episode N recency set on every turn from 32 through 35. `RetrievalEngine` removed every LTM candidate whose ID appeared in N, and `build_tagged_context` independently gave recency broad precedence over LTM. That behavior over-applied the pre-registration's narrower rule: recency precedence is binding only for N∩K intra-STM overlap. The binding LTM rule requires an LTM or `both` survivor to render once in `<retrieved_ltm>` with provenance metadata. Because N members are refreshed after retrieval, the promoted set can remain in N indefinitely; this is starvation, not a transient four-turn horizon effect.

The run also exposed a separate deterministic labeling defect. Consolidation merged `topic_1` into `topic_2` at turn 20; the turn-31 topic allocator used `len(topics)+1` and created a second canonical topic also labeled `topic_2`. Topic IDs remained distinct, so scoring and purity logic were not conflated, but logs and context metadata became ambiguous.

### Required remediation

1. Preserve the registered intra-STM N∩K recency rule, but let an LTM-selected episode take LTM placement over N so its provenance is not erased and the episode still appears exactly once.
2. Allocate topic labels monotonically within a run so consolidation cannot cause a label to be reused.
3. Add regression tests for both failures, re-run the S4_006 synthetic verification because the read path changes, then re-run this 35-turn ablation from scratch under a new run ID.

**DECISION: NO-GO — LTM-context integration failed. Reason: recency overlap starved every promoted episode before arbitration. Fix required before proceeding.**

---

## Attempt 2: `ablation_35_002`

**Date:** July 21, 2026
**Code under test:** `b848ec1` (`Revalidate Study 004 synthetic gate after remediation`)
**Status:** GO

The retry ran from a fresh database after remediation commit `0b1f989` and the accepted post-remediation synthetic run `synthetic_verification_005`. It completed all 35 iterative turns. Every applicable S4_007 check passed, including the previously failing real-script LTM placement path.

| Check | Expected | Actual | Pass? |
|---|---|---|---|
| GPU speed (UD-Q6_K_XL) | > 30 tok/s | 36.14 minimum; 38.81 average tok/s | Yes |
| Consolidation fires | At least once | Fired at turns 10, 20, and 30; one same-domain pair merged at turn 20 | Yes |
| Topic count at turn 35 | Trending toward the [3,10] band pace | Two canonical topics after two of four domains began, pacing to four; distinct labels `topic_2` and `topic_3` | Yes |
| Cross-domain merges | Zero (`consolidation_purity.csv`) | Zero | Yes |
| First LTM promotion | At ≈ turn 31 | Turn 31: 30 episodes evaluated, 9 promoted; no earlier event | Yes |
| Decoupled Association computed | Max-per-topic Association logged | The first batch used the pre-registered empty-LTM case: all 30 A and counterfactual global-A values were 0.0. S4_006 independently verified the multi-topic max and the unit suite verifies the single-topic case. | Yes |
| Parallel retrieval active | Both tiers queried from ≈ turn 32 | Concurrent tier path active; five LTM candidates returned on every turn 32–35 | Yes |
| LTM episode reaches context | ≥ 1 post-31 LTM-provenance episode | Five per turn on turns 32–35; 20 individually logged rows with promotion metadata | Yes |
| Dedup correct | No episode ID twice; sane duplicate count | Every final set unique. `duplicates_removed=0` is sane because K_stm was empty on turns 32–35; the accepted synthetic run exercised a nonzero overlap. | Yes |
| Degenerate fallback | Low-STM turn or S4-T-010 re-run | On each turn 32–35, K_stm was empty and final ordering exactly equaled direct LTM-only similarity rank | Yes |
| Tagged blocks | All five each turn; empties self-closing | All five on all 35 prompts; LTM metadata rendered on turns 32–35 | Yes |
| `arbitration_events.csv` | Populated, all fields | Exact registered header plus 35 rows | Yes |
| No promotion during any probe | N/A below turn 112 | No probe turns in range and no post-31 promotion event | N/A |

The sprint plan's parenthetical expectation of a single-topic LTM snapshot on the turn-31 batch is impossible on the first-ever promotion batch: the pre-registration requires a frozen batch-start snapshot, which is empty before those writes. The higher-authority pre-registration therefore yields A = 0.0 at turn 31. The accepted synthetic run covers the required ≥2-topic case, and the unit suite covers the single-topic complement case.

### Carried Study 003 checks

| Check | Actual | Result |
|---|---|---|
| Rule detection and persistence | Turn-1 rule detected; one `rule_store` row points to the turn-1 episode | PASS |
| Promotion idempotency | 9 LTM rows, 9 distinct episode IDs | PASS |
| LTM schema population | No null required score/provenance fields; all embeddings are 4,096 bytes (1,024 float32 values) | PASS |
| Transition stability | Exactly one promotion event at turn 31; none on turns 1–30 | PASS |
| Consolidation observability | Three `consolidation_events.csv` rows and matching topic metrics | PASS |
| Analysis outputs | 30 episode-score rows, 9 filter-trigger rows, and one promotion-summary row | PASS |

### Remediation confirmation

The retry confirms both attempt-1 fixes without introducing a parameter or ranking change:

1. LTM-selected episodes retain LTM provenance and placement when they also qualify for N. N∩K recency precedence remains unchanged for intra-STM overlap.
2. Topic labels advance monotonically within the run. The post-consolidation Renaissance topic was created as `topic_3`, not a second `topic_2`.

The repository-wide post-remediation suite passed **476 tests**. The raw ablation directory remains an ignored execution artifact; this report is the committed gate record.

DECISION: GO — all applicable checks passed; synthetic verification (S4_006) covered flush/guard/decoupling/Q14. Full 120-turn run authorized.

---

## Attempt 3 (A005): `ablation_35_a005_001`

**Date:** July 21, 2026
**Code under test:** `9220576` (`Apply Study 004 A005 response budget`)
**Amendment:** A005, locked at `9fbf4f9`
**Status:** GO

This fresh run repeated the mandatory 35-turn gate after A005 changed the
generation configuration from a 1,024-token response budget to 2,048 tokens.
It started from a new database and completed all 35 iterative turns. Every
applicable S4_007 check passed, and no response reached the amended ceiling.

| Check | Expected | Actual | Pass? |
|---|---|---|---|
| A005 response budget | 2,048 tokens; no consecutive truncation | Maximum output 1,357 tokens (691-token margin); zero cap events and zero empty responses | Yes |
| GPU speed (UD-Q6_K_XL) | > 30 tok/s | 35.62 minimum; 38.84 average tok/s | Yes |
| Consolidation fires | At least once | Fired at turns 10, 20, and 30; one same-domain pair merged at turn 20 | Yes |
| Topic count at turn 35 | Trending toward the [3,10] band pace | Two canonical topics after two of four domains began, with distinct labels `topic_2` and `topic_3` | Yes |
| Cross-domain merges | Zero (`consolidation_purity.csv`) | Zero | Yes |
| First LTM promotion | At approximately turn 31 | Turn 31: 30 episodes evaluated, 9 promoted; no earlier event | Yes |
| Decoupled Association computed | Max-per-topic Association logged | The frozen first-batch snapshot was empty, so all 30 Association and counterfactual global-Association values were 0.0, as pre-registered | Yes |
| Parallel retrieval active | Both tiers queried from approximately turn 32 | Concurrent tier path active; five LTM candidates returned on every turn 32-35 | Yes |
| LTM episode reaches context | At least 1 post-31 LTM-provenance episode | Five per turn on turns 32-35; 20 individually logged rows with promotion metadata | Yes |
| Dedup correct | No episode ID twice; sane duplicate count | All 35 final sets matched logged sizes and contained unique IDs. `duplicates_removed=0` is sane because K_stm was empty on turns 32-35; S4_006 covers nonzero overlap | Yes |
| Degenerate fallback | Low-STM turn or S4-T-010 re-run | On turns 32-35, STM K was empty and the arbitration output order exactly matched the LTM-only order | Yes |
| Tagged blocks | All five each turn; empties self-closing | All five sections occurred exactly once in all 35 prompts; no malformed block; turns 32-35 rendered LTM promotion metadata | Yes |
| `arbitration_events.csv` | Populated, all fields | Exact registered header plus 35 rows; all final-size and LTM-count cross-checks matched | Yes |
| No promotion during any probe | N/A below turn 112 | No probe turns in range and no post-31 promotion event | N/A |

### A005 generation check

The pre-commit 4,096-ceiling replay had measured natural completion at 1,225,
1,277, and 1,050 tokens for the three prompts that triggered the failed
1,024-token run. This fresh stochastic gate independently stayed below 1,357
tokens across all 35 turns. The larger response ceiling did not reduce runtime
below the registered speed floor or push constructed context above the 20,000
token monitoring threshold; peak estimated context was 9,235 tokens.

### Carried Study 003 checks

| Check | Actual | Result |
|---|---|---|
| Rule detection and persistence | Turn-1 rule detected; one `rule_store` row points to the turn-1 episode | PASS |
| Promotion idempotency | 9 LTM rows, 9 distinct episode IDs | PASS |
| LTM schema population | No null required score/provenance fields; every embedding is 4,096 bytes (1,024 float32 values) | PASS |
| Transition stability | Exactly one promotion event at turn 31; none on turns 1-30 | PASS |
| Consolidation observability | Three consolidation rows at turns 10, 20, and 30, matching topic metrics | PASS |
| Analysis outputs | 30 episode-score rows, 9 filter-trigger rows, and one promotion-summary row | PASS |
| Archive completeness | 35 responses, 35 context-size rows, 35 turn rows, and 35 arbitration rows | PASS |

The repository-wide A005 suite passed **481 tests** before this run. The raw
ablation directory remains an ignored execution artifact; this report is the
committed gate record.

DECISION: GO - all applicable A005 35-turn checks passed. The same-settings v3 control run is authorized as the next binding step; no fresh v4 full run is authorized until the control is scored and its amended breadth gate is evaluated.
