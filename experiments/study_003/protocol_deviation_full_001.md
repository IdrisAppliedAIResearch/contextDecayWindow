# Study 003 — Full Run 001 Protocol Deviation

**Recorded:** July 19, 2026, after completion of `study_003_full_001`.

## Run status

The iterative condition completed all 120 turns without a crash and its raw artifacts are preserved unchanged. It is not accepted as the confirmatory Study 003 run.

## Observed deviations

1. `promotion_events.csv` contains six events at turns 31, 61, 91, 112, 114, and 118. The locked protocol expects exactly three events at the scripted domain boundaries near turns 31, 61, and 91. Turns 112–120 are rubric probes within the final scripted phase; their references to earlier domains were incorrectly treated as new phase transitions.
2. The rule store contains zero rows. On turn 1, the server model acknowledged the two persistent rules but omitted the requested `<rule_detection>` metadata tag. The parser's safe default converted the missing tag to `contains_rule = false`, so the episode was not pinned as a rule.
3. The turn-120 consolidation merged four topic nodes and left one final topic. This satisfies the pre-registered topic-count bar (`<= 20`) but is retained as an observational caveat because the final comprehensive probe spans all four domains.

## Disposition

Do not score or analyze this run as the Study 003 result. It remains an engineering diagnostic artifact. Apply Amendment 004, re-verify the affected behavior, and execute a fresh run under a new run ID.
