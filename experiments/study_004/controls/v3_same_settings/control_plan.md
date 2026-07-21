# Study 004 A005 - Same-Settings v3 Control Plan

**Status:** code-discipline verification complete; execution authorized by
A005 and the committed 35-turn GO at `cc45f05`

## Locked inputs

- Study 003 v3 base commit:
  `c4120a40ab19912a6c5d04826d11385d59cbc272`
- Dedicated control-adapter commit:
  `5adf0ea9de7d3d16346b8d498419eb2cdc695d0e`
- Control branch: `codex/study-004-a005-v3-control`
- Locked 121-turn script: `experiments/study_004/script.json`
- Script SHA-256:
  `97C42E0FF612245C7CDAB3B6F6F3C1D4BD9DE5AAD14FD4519C63E37D63F93F0E`
- Execution ID: `v3_control_001`
- Canonical control output:
  `experiments/study_004/controls/v3_same_settings/v3_control_001/`

## Same-settings configuration

- Model: Qwen3.6 27B UD-Q6_K_XL
- Server: local llama.cpp `/completion`
- Context capacity: 262,144 tokens
- Response budget: 2,048 tokens
- Sampling parameters: omitted in the request, inheriting the same server
  defaults as v4
- Embedding model: unchanged Qwen3-Embedding-0.6B Q8_0, 1,024 dimensions
- Script: the exact Study 004 121-turn script, including Q14

## Binding code-discipline audit

The control is a separate worktree from the accepted Study 003 merge commit,
not the v4 runner with feature flags. The adapter diff contains exactly two
files:

1. `src/inference/provider.py`: only the local `max_tokens` and HTTP
   `n_predict` literals change from 1,024 to 2,048.
2. `scripts/run_study_004_a005_v3_control.py`: points the pinned v3 runner to
   the locked external script and output directory and includes turn 121 in
   rubric capture.

Pre-run review found:

- zero v3 source matches for arbitration or LTM-read symbols;
- no XML context tags in the v3 context builder;
- untagged `--- PINNED RULES ---` / `--- RETRIEVED CONVERSATION HISTORY ---`
  context construction remains intact;
- 25/25 relevant inference and runner tests passed;
- the historical repository suite passed 441 tests, with only the unrelated
  Study 003 publication-figure byte-check failing in the fresh Windows
  worktree. No architecture or runtime test failed.

No other control-worktree change is permitted after this record. A dirty
worktree, unexpected diff, model mismatch, or script-hash mismatch invalidates
the launch.

## Evaluation sequence

1. Execute all 121 turns and preserve all raw responses and metrics.
2. Verify run completeness and monitoring criteria without scoring during the
   run.
3. Score Q1-Q13 against `experiments/study_002/rubric_filled.md` and Q14
   against `experiments/study_004/q14_criteria.md`.
4. Commit the full 14-question score sheet before any v4 full run.
5. Apply A005's breadth gate. If the v3 control passes both Q11 and Q14 breadth,
   stop and escalate. Otherwise lock the control as the Bar 1/Bar 2 reference
   and authorize the fresh v4 run.
