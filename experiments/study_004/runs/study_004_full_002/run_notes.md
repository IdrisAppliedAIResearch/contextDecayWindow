# Study 004 A005 Fresh v4 Run — Run Notes

**Run:** `study_004_full_002`

**Status:** valid, complete, scored, and analyzed

**Execution date:** 2026-07-21

## Provenance and sequence

- Pre-registration: `1b9eb204e32b6b7cb32dfce4cb647cfc7f0e4d0f`
- A005 authorization: `9fbf4f9f95a1fad6205d56664db36b9911650d41`
- Production budget implementation: `9220576`
- Fresh 35-turn GO: `cc45f05b4b8396ac30d73b382310c0f47b5f6265`
- Control score lock: `6f34069`
- Run-launch HEAD: `581b2b54262258d923a4e41b04f8e4b3bd7a604f`
- v4 rubric score lock: `8e097c0`
- Script SHA-256: `97C42E0FF612245C7CDAB3B6F6F3C1D4BD9DE5AAD14FD4519C63E37D63F93F0E`

There was no `src/`, `scripts/`, or test-code difference between production
budget commit `9220576` and launch HEAD `581b2b5`. Both `study_runner` and
`context_builder` resolved inside this main v4 worktree before launch.

Configuration: Qwen3.6 27B UD-Q6_K_XL, llama.cpp server at 262,144 context,
2,048 response tokens, inherited server sampling defaults, and the unchanged
Qwen3-Embedding-0.6B Q8_0 embedding path.

The v3 control was scored and committed before this run. The v4 rubric was then
scored and committed before probe-turn arbitration analysis opened.

## Pre-turn console launch incident

The first process invocation failed while printing the condition banner because
Windows Python selected CP1252 for stdout and could not encode box-drawing
characters. It failed before turn 1 and before inference: the turn log was zero
bytes and only initialized headers plus an empty database existed. That shell
is preserved as
`study_004_full_002_launch_failed_encoding_zero_turn`.

The canonical ID was relaunched with `PYTHONIOENCODING=utf-8` and `PYTHONUTF8=1`.
No model, script, code, budget, sampling, or study parameter changed.

## Completion checks

- 121 sequential turns
- 121 performance, context-size, and arbitration rows
- 121 full-response entries; rubric turns exactly 112–121
- 0 empty responses; 0 responses at the 2,048-token cap
- 95,170 generated tokens; 786.53 average; 1,393 maximum
- 36.9435 average tokens/s; 15.8883 minimum; 42.5980 maximum
- 11,376-token peak context at turn 116
- Promotion events: 31, 61, 91 (`transition`) and 111
  (`end_of_session_flush`)
- Final topics: 5; cross-domain merges: 0
- Assistant response context/rule/thinking-tag echoes: 0
- Runner duration: 44m54s

## Preservation and hashes

All raw logs, prompts, snapshots, responses, metrics, and the database remain
preserved locally. Following the existing Study 002/003 artifact policy, heavy
raw turn/retrieval/diff logs, constructed prompts, snapshots, and the database
are excluded from Git; full responses, curated logs, metrics, LTM analysis,
rubric artifacts, and reports are tracked.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `condition_c/responses.md` | 489,592 | `AD76BBCDBE3F8DAA84A26EBEC7AD0B05FEDF069D0A1493A9F4982DD8FCCA7C34` |
| `condition_c/rubric/responses.md` | 16,932 | `8CF9317D698985FA4A41479506C70E550678360F4586F96565ABF0F4766D1C61` |
| `condition_c/logs/turns.jsonl` | 3,566,216 | `3CB5615F9A6761EA5475D85A6372935D9BADA19C0156613DF13FC236176B1642` |
| `condition_c/logs/retrieval.jsonl` | 2,812,036 | `3E86F45BCAD6BE84C1B10BC68F9182FBC0F5328DAF78BE90F4C0AE5178B0D3C5` |
| `condition_c/logs/context_diffs.jsonl` | 3,563,221 | `A9756654BFEAE9FFA8BE699627C22F5BD729354ED3FB46CFC3C257D2A68A6B56` |
| `condition_c/logs/arbitration_events.csv` | 40,586 | `CA7ACA920E6399A2BFB386F7FF4E92A53CB904C4BABFF087F029CC818E30F256` |
| `condition_c/logs/consolidation_purity.csv` | 87 | `8CEDE4BCCAD4D87B78C49269F90DDF454359F6EBFDA11326BD9B3F52D2AA3B00` |
| `condition_c/logs/ltm_context_episodes.csv` | 44,701 | `89CD6A4A658CB8C09B00C165B3F876CBA856A7A5221D1CA2F8EF86B60926D98B` |
| `condition_c/ltm_analysis/episode_scores.csv` | 14,869 | `61445B443871A6BC75FC6AF9F5BDED98ACA46C70F41BD4B8F548E013404CDF54` |
| `condition_c/metrics/model_performance.csv` | 6,383 | `20E72960D8208834017FF1DED3C8A97B019142F53A9927AABF57DDAD9C657D6D` |
| `condition_c/study.db` | 1,462,272 | `BA6575E1335011764F43FBCCE5FF3440BAC1EE25402194E7454C3283BE63768B` |

The unrelated untracked `demo/` directory was not read, modified, staged, or
committed.
