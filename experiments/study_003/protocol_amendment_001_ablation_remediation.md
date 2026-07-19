# Study 003 — Protocol Amendment 001: Ablation Remediation

**Recorded:** July 2026, after the completed 35-turn pre-run ablation.

## Trigger

The retry ablation completed 35 turns but did not meet the pre-run gate. It recorded 29 promotion events and 53 LTM rows from 35 STM episodes. The same STM episode could be promoted repeatedly when a fragmented topic was revisited. In addition, the 0.50 topic-assignment threshold fragmented the continuous civil-engineering opening into multiple topics, causing promotion to begin before the intended cross-domain transition near turn 31.

## Amendments

1. `ltm_episodes.episode_id` is now unique. Promotion is idempotent: an STM episode already stored in LTM is excluded from later promotion batches.
2. The topic-assignment threshold is reduced from **0.50 to 0.45**. This is a targeted stability adjustment for the pre-registered expectation that turns 1–30 constitute one civil-engineering domain. The consolidation threshold remains 0.45.

The four filter definitions, weights, weighted threshold, all-or-nothing threshold, script, rubric, model-family deviation, and 120-turn study scope are unchanged.

## Required re-verification

Run a fresh 35-turn iterative ablation. A GO decision requires: no duplicate LTM episode IDs, no promotion before the first genuine cross-domain transition, promotion at the turn-31 transition, rule persistence, consolidation logs, and no observed cross-domain merge.
