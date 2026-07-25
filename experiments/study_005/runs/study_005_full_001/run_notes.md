# Study 005 Full Treatment Run Notes

**Run:** `study_005_full_001`

**Status:** valid, complete, scored, and analyzed

**Execution date:** 2026-07-22

## Provenance and sequence

- Pre-registration lock: `20aa7707e780543ccbe462efadf3bb1263b3813e`
- Full-run authorization: `35dcfb6`
- Control-plan lock and treatment launch HEAD: `7d28ba9`
- Score and structural lock: `1bbfad7`
- Script SHA-256:
  `D8BA73FD02BFD41BEC156904FB6A3328BBED3D0DA8BFF05E4667D2E450752F01`
- Server PID: `23384`

The treatment ran only after the seeded promotion control completed. Both arms
used fresh servers with the same command, model, context, sampling, seed, and
single-slot configuration. The server was stopped after the run.

## Completion checks

- 121 sequential turns
- 121 performance and context-size rows
- Four dream events at turns 31, 61, 91, and 111
- 12 distilled records, all faithful, zero non-content
- 121 arbitration rows
- Peak context 16,171, below the 40,000 monitor ceiling
- 36.022 average tokens/s; 9.572 minimum tokens/s
- 88,885 generated tokens
- Runner duration 40m47s
- No strict-monitor abort
- Final topics: 5; cross-domain purity events: 0

The first 30 constructed prompts and assistant responses were byte-identical
to the seeded control. Rubric scores and formation checks were committed before
dream, arbitration, retrieval, or probe-context logs were opened.

## Preservation

Raw databases, JSONL turn/retrieval/context logs, prompts, and snapshots remain
preserved locally and ignored by Git. Curated responses, dream CSVs, distilled
snapshots, arbitration/purity summaries, metrics, score artifacts, and reports
are tracked.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `condition_c/responses.md` | 458,071 | `C1E4946F428B9D4CE79A5DD51A918CD612D4AE3DDD2A4082D42389EADD41962F` |
| `condition_c/rubric/responses.md` | 13,889 | `585FC42B157470395CC6E93CB740E971A901BDCAD173791E1B72880FE6CB0A68` |
| `condition_c/logs/arbitration_events.csv` | 37,431 | `D81880F6E114C744FA393D2616A3A56222EE5E39CE30CFA7D5F1A1DA8EF222DC` |
| `condition_c/dream_analysis/episode_salience.csv` | 7,435 | `A8FC49B73FE9B15C745697A27B3E3C5C7C59B3B6E2302AE4BD5AD74C31355D9F` |
| `condition_c/study.db` | 1,953,792 | `C98EECAFCB4D579F671694C4BB28481E0D24D6D48D6D6A81BC66200F312AF04C` |

The unrelated untracked `demo/` directory was not modified or staged.
