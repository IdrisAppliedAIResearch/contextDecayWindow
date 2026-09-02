# DA-019 Scratchpad

## 2026-08-30 - Registration

- User authorized preserving the strongest order and permitting only protected,
  evidence-blind substitutions near the capacity boundary.
- DA-019 makes at most one post-pack swap: the final admitted linked payload may
  be replaced by the first baseline-skipped payload that fits, preserves all of
  the incumbent's unique query tokens and has no lower frozen-query cosine.
- NF control is DA-010 at 970; LongMem control is DA-016 at 188. Direct and all
  earlier linked actions are immutable. No global rescoring or refill follows.
- Zero model and zero new embedding calls. LongMem sealed-cache reads only.
- Next: commit protocol, implement identity tests, reproduce controls, and lock
  blind substitutions before evidence access.

## 2026-08-30 - PF4 stop

- Blind rule executes 571 NF-004 and 188 LongMem substitutions; it is not inert.
- Rejections: fit 8,631, lexical 359, semantic 6,786, duplicate 0.
- PF4 required every rejection family. Parent streams deduplicate neighbors
  upstream, making real duplicate rejection unreachable. `STOPPED_AT_PF4`.
- Blind replay is byte-identical at
  `b418495e649c96befa33a738a9fda0f68e56127b76f881ccc71ac4c853acd31f`.
- Evidence outcomes remain unopened. A successor must test duplicates
  synthetically and retain this rule unchanged; DA-019 cannot be repaired.

