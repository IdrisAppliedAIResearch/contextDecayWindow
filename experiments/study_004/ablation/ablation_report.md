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
