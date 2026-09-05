# BEAM-001 Amendment 015 - Deterministic score replay

**Status:** post-result implementation correction  
**Date:** 2026-08-28  
**Audit anchor:** `317b7104`  
**Amends:** score serialization implementation only

## 1. Finding

After all 360 judgments sealed and the characterized result was opened, local
score replay alternated between result SHA-256 values
`ccf8ebe9b94ed7285a12b44bd1d5d90f0e6e4d7afa03885b1ddb7d11d9cbdb79`
and
`df6da2df9143d22ae88d95b80b7da7b04c7bf23d832eead193ac2bba905b2e69`.
All 1,080 question scores were byte-identical. The scorer averaged each
conversation's four question ids by iterating a Python set, allowing process
hash order to alter floating-point accumulation order.

The observed difference is confined to last-bit arithmetic, including
T1-A0 values `-0.006979717813051144` and `-0.006979717813051146`. Printed
metrics, intervals, p-value, guardrail decisions and
`NO_DEMONSTRATED_GAIN` are unchanged.

## 2. Correction

Sort each conversation's four question ids before computing every arm mean.
No input, judgment, score, estimator, seed, threshold, statistic or output
precision changes. Regenerate `question_scores.jsonl`, `results.json` and the
result report, then require identical hashes across explicit
`PYTHONHASHSEED=1,2,3,4` replays.

This correction does not remove or alter `DEVIATION_002` through
`DEVIATION_004`; the result remains `CHARACTERIZED`.
