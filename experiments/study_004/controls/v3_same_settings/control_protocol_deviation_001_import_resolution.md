# Study 004 A005 v3 Control - Protocol Deviation 001

**Attempt:** `v3_control_001`
**Date:** July 21, 2026
**Status:** invalidated before scoring
**Disposition:** preserved diagnostic; excluded from the A005 baseline

## Trigger

The attempt completed all 121 turns, but the pre-scoring provenance audit found
artifacts impossible under the pinned v3 implementation:

1. Constructed prompts contained `<current_turn>`, `<retrieved_stm>`, and
   `<retrieved_ltm>` XML sections.
2. `logs/arbitration_events.csv` existed and contained per-turn v4 arbitration
   output.
3. The archive contained v4-only `context_sizes.csv` and root `responses.md`
   artifacts.
4. Promotion logs contained a turn-111 `end_of_session_flush`, which the pinned
   v3 `StudyRunner` does not call.

No rubric response was opened or scored before invalidation.

## Root cause

The control launcher was executed as a file with the main repository's virtual
environment. Python placed the control worktree's `scripts/` directory, not its
repository root, at `sys.path[0]`. The virtual environment's editable package
entry then resolved `src` from the main v4 workspace. Static diff review of the
v3 worktree was correct, but the launcher did not assert runtime import
provenance.

## Preservation

The untouched 121-turn output is retained locally at
`v3_control_001_invalid_import_resolution/`. Its heavy iterative artifacts are
excluded from version control under the repository's raw-artifact policy. Key
SHA-256 values at invalidation were:

- `logs/turns.jsonl`:
  `F5C74D2374067B37E26BE9D4647A40F0DB9F0143BA9D6C44D6DA6D8EB4D65E33`
- `constructed_prompts/turn_001.txt`:
  `8A39F3E76E8466F4C907357203EF5BD4DB72226E578CCE08611D59629BAC4011`
- `logs/arbitration_events.csv`:
  `B96C276163EF7456DBCD68175C5755CE33E23F383FCDD266581B40F7DB57D972`
- `responses.md`:
  `CF8ED678A0AC1D69EEE1C2E7C09C376BD0E9DC19BB547DBF00C97FB13AC28858`

## Remediation

Control-adapter commit `a78fa2b` now:

1. prepends the separate v3 worktree root before importing `src`;
2. asserts the runner and context-builder module paths are inside that root;
3. rejects XML context tags in the resolved v3 context builder; and
4. writes `control_runtime_manifest.json` before inference.

A fresh run must use `v3_control_002`. The provenance manifest and first
constructed prompt must be checked before allowing the retry to continue.
