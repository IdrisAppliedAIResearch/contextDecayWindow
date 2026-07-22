# Study 004 A005 Same-Settings v3 Control — Run Notes

**Run:** `v3_control_002`

**Status:** valid and complete; rubric score locked separately

**Execution date:** 2026-07-21

## Provenance

- Study 003 v3 base: `c4120a40ab19912a6c5d04826d11385d59cbc272`
- Control adapter: `a78fa2bd68586a90eae7455ef422bce0cf54608e`
- Control branch: `codex/study-004-a005-v3-control`
- Script SHA-256: `97C42E0FF612245C7CDAB3B6F6F3C1D4BD9DE5AAD14FD4519C63E37D63F93F0E`
- Response budget: 2,048 tokens
- Model: Qwen3.6 27B UD-Q6_K_XL
- Runtime manifest resolves `study_runner` and `context_builder` inside
  `C:\Users\muzaf\PycharmProjects\contextDecayWindow-a005-v3-control`.
- The control worktree was clean at adapter commit `a78fa2b` after completion.

The control used the pinned v3 implementation directly. It did not use the v4
runner with features disabled. No arbitration file, context-size file, v4 root
response file, LTM read-path artifact, or turn-111 end-of-session flush was
created. Promotion events occurred only at turns 31, 61, and 91.

## Completion and monitoring checks

- Turn records: 121, sequential turns 1–121
- Performance rows: 121
- Constructed prompts: 121
- Database snapshots: 121
- Rubric response headings: turns 112–121 exactly
- Empty responses: 0
- Responses at the 2,048-token cap: 0
- Maximum output: 1,434 tokens
- Average output: 620.68 tokens
- Peak estimated context: 9,251 tokens
- Throughput: 14.4802 minimum, 39.1619 average, 42.9255 maximum tokens/s
- Wall-clock duration reported by the runner: 34m33s

The low minimum throughput is the 48-token turn-113 response and is not paired
with an empty or capped result. No pre-registered monitoring stop condition was
met.

## Generated-response anomaly

Turns 17, 22, 28, 41, and 112 retain a literal `<rule_detection>` fragment in
the stored assistant response; turn 112 also repeats its correct two-item
answer around a residual `</think>` marker. These are generated response text
from v3's existing rule-detection output protocol, not v4 memory-tier wrappers:
the pinned v3 context builder still uses plain `--- PINNED RULES ---` and
`--- RETRIEVED CONVERSATION HISTORY ---` delimiters, and no v4 arbitration or
read path executed. The fragments were intermittent, did not cause truncation,
and did not meet the stop rule. Turn 112 remains unambiguous for Q1 scoring.

## Preservation and artifact hashes

All raw responses, retrieval logs, prompts, snapshots, metrics, and the database
remain preserved under this run directory. Following the repository's existing
Study 002/003 artifact policy, heavy logs, constructed prompts, snapshots, and
the database are retained locally but excluded from Git; metrics, LTM-analysis
CSVs, the runtime manifest, rubric responses, score lock, and these notes are
tracked.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `control_runtime_manifest.json` | 771 | `AF26D743A7DA0FDEE518D24C0D51ED8ED6E9906E32D99E4DD3D21734C60D0B7D` |
| `iterative/logs/turns.jsonl` | 3,573,041 | `0AAA72CB9F40AFEE0F7FCEA0C99B8FADA74BF27FE40C3873EA91ED199C6AD7E8` |
| `iterative/logs/retrieval.jsonl` | 3,067,762 | `B77EC40FFEA6BA885CF0E4DB8A65ABD0586302C9D22CD29CD2B90994FD53429D` |
| `iterative/logs/context_diffs.jsonl` | 1,045,506 | `77466DFBB6E1CB620CCCC8EF68E49BEF4055F0493649151C6617AB3D50D4A5D5` |
| `iterative/rubric/responses.md` | 11,719 | `6A12E724E618366A6D4AA8F4C5487B31002FF6ADF71C4B0F22AD26B91553D9AF` |
| `iterative/metrics/model_performance.csv` | 6,347 | `94CF0DEFBAA18DB6AFCCDEE496680BFCC6E90DD18EC0AB736C05C7EF565E27D0` |
| `iterative/study.db` | 1,441,792 | `3EF550A377EC9FA5E736A94939C4636F5106BD5276E7E25A2A94F56FC13645B8` |

The scoring source is the hashed, unedited rubric response artifact above.
