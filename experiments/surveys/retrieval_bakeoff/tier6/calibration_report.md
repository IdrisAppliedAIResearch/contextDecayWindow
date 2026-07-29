# Retrieval Bakeoff Tier 6 Calibration Report

**Status:** PASS  
**Evidence class:** Registered development-only calibration  
**Implementation commit:** `e1d08446214c6fb3ff93cbad1b23f03eff9fb145`

## Target

Study 009 Arm L's exact serialized retrieval payload was measured on development
turns 92-111. The target median is **60,595 characters**, with a per-turn range
of 59,387-62,223. The charged payload includes the deduplicated
`recent_context`, `retrieved_stm`, and `retrieved_ltm` blocks plus their
two-newline separators.

## Selection

All 60 preregistered N/K cells ran against the preserved Study 009 Arm S raw
store. The primary objective was mean absolute per-turn character error; locked
tie-breakers were maximum error, lower N, then higher K threshold.

- Selected N cap: **32**
- Selected K cosine threshold: **0.48**
- Fixed payload cap: **60,595 characters**
- Delivered median: **60,279 characters**
- Delivered range: **59,044-60,586 characters**
- Mean absolute error: **710.5 characters**
- Maximum absolute error: **2,478 characters**
- Median absolute percentage error: **1.0035%**
- Registered match gate: **PASS** (`<= 5%`)

The exhaustive target vector, candidate table, source hashes, carried embedding
model hash, and exact selected loss are locked in
`settings/tier6_context_match_settings.json`.

## Integrity

Turns 112-121, live answers, answer keys, and rubric criteria were excluded from
calibration. Source hashes were unchanged before and after execution. Static
import-graph leakage and the planted violation test both passed.
