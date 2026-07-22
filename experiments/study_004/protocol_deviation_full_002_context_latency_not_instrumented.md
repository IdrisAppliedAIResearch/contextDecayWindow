# Study 004 — Protocol Deviation: Context Latency Not Instrumented

**Run:** `study_004_full_002`

**Discovered:** 2026-07-21, after the v4 rubric score lock

**Scope:** observational measure only; no confirmatory criterion changed

## Registered measure

The pre-registration requested a per-turn context-construction wall-time delta
against Study 003 to characterize the cost of parallel STM/LTM retrieval.

## Deviation

The executed runner did not emit a context-construction timer. Its performance
CSV records model-generation elapsed time through tokens/second and estimated
TTFT, not retrieval/arbitration/context-render elapsed time. The registered
latency delta therefore cannot be calculated from the run artifacts.

## Impact

This omission does not affect Bar 1, Bar 2, Bar 3, response scoring,
provenance, deduplication, displacement analysis, promotion analysis, or
consolidation purity. It leaves one observational measure unavailable.

End-to-end duration is not substituted: v4 took 44m54s versus 34m33s for the
same-settings v3 control, but v4 generated 95,170 tokens versus 75,102
(+26.72%) and had different response lengths/context loads. That wall-clock
difference cannot isolate retrieval latency.

## Required correction for a future run

Add monotonic timers around STM query, LTM query, joint await, arbitration, and
context rendering; record both tier durations and total critical-path duration
per turn. The instrumentation must be committed and ablated before any future
latency comparison.
