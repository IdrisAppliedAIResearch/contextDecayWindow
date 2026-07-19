# Study 003 — 35-Turn Ablation Report

## Attempt 1: `ablation_35_server_retry`

**Decision:** NO-GO — promotion idempotency and topic-transition stability failed.

The run completed all 35 turns. Consolidation fired at turns 10, 20, and 30; the turn-1 rule was detected and persisted; and the LTM schema and analysis files were populated. However, 35 STM episodes produced 53 LTM rows across 29 promotion events. Promotions began before the intended cross-domain switch at turn 31 because the 0.50 assignment threshold fragmented the opening civil-engineering domain.

See `../protocol_amendment_001_ablation_remediation.md` for the corrective changes and retry criteria.
