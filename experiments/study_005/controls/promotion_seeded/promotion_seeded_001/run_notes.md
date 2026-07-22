# Study 005 Seeded Promotion Control Run Notes

**Run:** `promotion_seeded_001`

**Status:** valid, complete, scored, and analyzed

**Execution date:** 2026-07-22

## Provenance

- Accepted Study 004 base: `994a490155bcb32a388222abfa3b8f2946d62fe4`
- Seeded adapter: `a8a29aa65e55088a9dbf273deec482df9bb6c4dc`
- Main control-plan lock: `7d28ba9`
- Score lock: `1bbfad7`
- Server PID: `24428`

The adapter diff contained exactly the launcher, deterministic rule-ID change,
and its tests. Full accepted-v4 tests passed 481 tests before execution. Module
paths resolved inside the pinned control worktree and no Study 005 dream engine
was present.

## Completion checks

- 121 sequential turns
- 121 performance and context-size rows
- Peak context 10,006, below the 40,000 monitor ceiling
- 37.318 average tokens/s; 12.757 minimum tokens/s
- 83,377 generated tokens
- Runner duration 38m46s
- 14 promoted LTM records
- No strict-monitor abort

The runtime manifest was written before turn 1 and finalized with status
`complete`. The server was stopped after the run. The control scored 12.0/13.0
on Q1-Q13 and 0.0 on Q14.

## Preservation

Raw databases, JSONL logs, prompts, and snapshots remain preserved locally and
ignored by Git. Curated responses, metrics, LTM/arbitration summaries, runtime
manifest, rubric artifacts, and these notes are tracked.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `condition_c/responses.md` | 437,204 | `7ED0346938071A1C9D9360A89839BB37EF09B28DE41D9661D9A0AF210C4556FD` |
| `condition_c/rubric/responses.md` | 9,822 | `F569736814C4E524EE5C6F327A10A11205F49D85E2AFC81A540998A73215D560` |
| `control_runtime_manifest.json` | 12,964 | `5CA2CC65E29ACE297DB05E207202E3C2A6975FBDED3B3FEFCC65B1A78397628D` |

The unrelated untracked `demo/` directory was not modified or staged.
