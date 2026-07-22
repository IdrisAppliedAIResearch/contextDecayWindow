# Study 004 — Zero-Turn Console-Encoding Launch Shell

**Date:** 2026-07-21

**Disposition:** preserved initialization shell; not a study run and not scored

The first `study_004_full_002` process invocation raised
`UnicodeEncodeError` while printing the runner's box-drawing start banner to a
CP1252 Windows stdout stream. The failure occurred before turn 1 and before any
model inference.

Verification before archival:

- `logs/turns.jsonl`: 0 bytes
- `logs/retrieval.jsonl`: 0 bytes
- `logs/context_diffs.jsonl`: 0 bytes
- Generated files: 24 header/initialization files
- Total initialized bytes: 54,794 (including an empty 53,248-byte SQLite
  schema)

The directory was moved intact to this name, the canonical run ID was freed,
and the process was relaunched with UTF-8 stdout. No scientific configuration
changed.
