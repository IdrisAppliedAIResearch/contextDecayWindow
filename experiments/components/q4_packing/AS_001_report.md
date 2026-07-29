# AS-001 - Q4 Packing Re-Analysis Report

**Type:** offline artifact analysis; not a study
**Status:** PASS; Branch D
**Verdict:** PRIMACY MECHANISM LIVE
**Design anchor:** `7c90235a`
**Amendments:** `e6b05b55`, `6fa435b5`, `aaed920f`
**Implementation:** `9a76a72c`, `3b5026fc`, `810b76ca`
**Evidence:** `f6d5d79c`

## Outcome

Compact rendering does not recover Q4's turn-55 episode under the unchanged
N-first character packer. At the retained 32,000-character point, 9 of 32 N
candidates fit and turn 55 remains absent with `S' - 27 = -18`. At the largest
locked sensitivity point, 64,000 characters, only 16 candidates fit. Rank 27
does not enter anywhere in the 16k-64k range.

The binding rule therefore selects Branch D: **PRIMACY MECHANISM LIVE**. The Q4
gap is a late-rank N-first packing exclusion, not an artifact of verbose episode
tags. A pinned durable-fact tier remains a testable proposal, not a validated
replacement; it requires a separate pre-registered CC-001 study.

## Results

| Budget | Fitted episodes | Serialized chars | Source chars | Turn 55 |
|---:|---:|---:|---:|---|
| 16,000 | 5 | 15,664 | 15,266 | absent |
| 20,000 | 6 | 19,500 | 19,033 | absent |
| 24,000 | 7 | 23,907 | 23,371 | absent |
| 28,000 | 7 | 26,037 | 25,500 | absent |
| 32,000 | 9 | 31,742 | 31,067 | absent |
| 36,000 | 10 | 35,643 | 34,899 | absent |
| 40,000 | 11 | 39,684 | 38,872 | absent |
| 48,000 | 13 | 47,503 | 46,552 | absent |
| 64,000 | 16 | 63,086 | 61,928 | absent |

The historical renderer and selection replayed exactly: 15 episodes, 59,708
serialized characters, identity order match, and payload SHA-256
`a161131b1f9352792656ffdda6f073d388244f722aafcb7ee8f007c7660b0721`.
This separates the new result from harness drift.

Because turn 55 is unavailable at every point, none of its four Q4 identity
facts is available in the packed payload. This is an availability finding only;
no answer was generated or rescored.

## Integrity

All three amendments were raised before packing output:

| Amendment | Trigger before result? | Legitimacy |
|---|---|---|
| 001 | YES | Replaces an ignored, uncommitted database with committed-log reconstruction; decision rule unchanged |
| 002 | YES | Corrects the seal's mixed LF/CRLF measurement unit; no content mismatch accepted |
| 003 | YES | Corrects an irreproducible derived cosine; both old and new values fail the same K threshold |

The corrected cosine is 0.12042197585105896, not the previously reported
0.16612689197063446. The reconstructed candidate vector exactly matches the
original local vector. `ERRATA.md` preserves the correction.

The historical mechanism seal is `FAIL_MISSING_COMMITTED_DB`: `study.db` was
listed but never committed. All 264 tracked mechanism entries match either
canonical LF bytes or deterministic CRLF materialization, with zero content
mismatches. AS-001 uses only committed logs, and the missing database does not
enter its evidence path.

Two separate processes produced byte-identical candidate CSV, source
verification JSON, result JSON, and report Markdown. No generative inference,
conversation run, mechanism change, or score change occurred.

## Deliverables

- [x] Decision rule committed before post-fix packing output.
- [x] Source provenance audited and amendments committed before output.
- [x] Historical payload reproduced exactly.
- [x] 32-candidate pre/post cost manifest.
- [x] Exact 32k result and complete 16k-64k sensitivity frontier.
- [x] Mechanical Branch D verdict.
- [x] Deterministic repeat.
- [x] `README.md`, `AGENTS.md`, `ERRATA.md`, and memory update.
- [ ] Independent stacked analysis PR.
