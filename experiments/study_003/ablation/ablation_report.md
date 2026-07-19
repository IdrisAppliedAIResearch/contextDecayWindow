# Study 003 — 35-Turn Ablation Report

## Attempt 1: `ablation_35_server_retry`

**Decision:** NO-GO — promotion idempotency and topic-transition stability failed.

The run completed all 35 turns. Consolidation fired at turns 10, 20, and 30; the turn-1 rule was detected and persisted; and the LTM schema and analysis files were populated. However, 35 STM episodes produced 53 LTM rows across 29 promotion events. Promotions began before the intended cross-domain switch at turn 31 because the 0.50 assignment threshold fragmented the opening civil-engineering domain.

See `../protocol_amendment_001_ablation_remediation.md` for the corrective changes and retry criteria.

## Attempt 2: `ablation_35_amendment_001`

**Decision:** NO-GO — topic-transition stability still failed.

The run completed 35 turns. Idempotency passed: `ltm_episodes` contained 9 rows with 9 distinct `episode_id` values. Rule persistence, schema population, analysis outputs, and consolidation logs also passed. However, the amended 0.45 assignment threshold still fragmented the civil-engineering phase; promotion events occurred from turn 3 and nonzero promotion occurred before the cross-domain switch at turn 31. The run must not authorize the 120-turn study.
