# LV-007 — reader-generation stop

**Status:** stopped before blind scoring; no result  
**Date:** 2026-08-26  
**Registration commit:** `b22e2854`  
**Passing Preflight commit:** `d0a6ebdf`

## Binding stop

The registered reader schedule completed all 255 expected rows with zero
duplicates, omissions or extra schedule keys. One answer ended by length at the
common 2,048-token cap:

- comparison key
  `7fd147b3cb2deb3677b72ea650c8453b67ff7f6a2e84e36d1d887c7a14608c85`;
- `conv-42`, source index 30, category 1 breadth;
- arm `COMMUNITY`, replicate 0, seed 5005;
- 9,008 prompt tokens and exactly 2,048 generated tokens.

Section 4 and G-COMPLETE require every answer to stop naturally, and explicitly
state that any answer ending by length stops the probe before judging. The
blind surface and arm mapping were not created, gold answers were not opened,
and no answer text or outcome was inspected. LV-007 therefore has no semantic
comparison, disposition or renderer result.

The local reader model became unavailable after generation. That outage is not
used to reinterpret the registered stop: the complete schedule exists, and the
single truncation independently invalidates it.

## Sealed artifacts

- `artifacts/run/answers.jsonl`: 255 rows, SHA-256
  `da1f8f62ba571ab17660091610077b1171b72a8a529d984fbad5962f04141f22`.
- `artifacts/run/generation_summary.json`: SHA-256
  `97a428cab42d9721c9c6af2d7b648113c0f4d76a1a2cf389e9be6677db05928f`.
- Validation: 255/255 schedule keys, zero duplicates, zero missing, zero extra,
  one truncated answer.

The 254 naturally stopped answers may not be mixed with a repaired answer under
LV-007. A continuation requires a new Part 1 and pre-registration that locks a
common repaired reader cap before any regenerated answers.
