# Study 003 Run Notes

## Canonical run

- Canonical archive: `run_001`
- Source execution ID: `study_003_full_002`
- Condition: Condition C / iterative construction
- Completed: 120 of 120 turns
- Result: accepted for Study 003 scoring and analysis

The source execution ID is retained in report headers for provenance. Curated artifacts are archived here under the same `run_001` convention used by Studies 001 and 002.

## Prior full run

`study_003_full_001` completed but was excluded before scoring because it emitted six promotion events rather than the three pre-registered transitions and failed to persist the opening rule. Its disposition is recorded in `../../protocol_deviation_full_001.md`.

## Runtime deviation

The accepted run used Qwen3.6 27B NVFP4 through a local llama.cpp server with a 262,144-token context. See `../../protocol_deviation_nvfp4_server.md`.

## Artifact policy

This canonical archive includes lightweight CSV metrics, LTM observational logs, rubric evidence, and analysis. Heavy databases, constructed prompts, snapshots, and JSONL turn/retrieval logs remain local and are excluded from version control, matching the repository's established artifact policy.
