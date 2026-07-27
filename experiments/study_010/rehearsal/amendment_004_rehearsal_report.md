# Study 010 Amendment 004 Rehearsal Report

**Evidence status:** post-stop exploratory
**Result:** FAIL - no full run authorized
**Execution commit:** `faa05eb`
**Arm order:** L then S

## Attempt 001

Arm L attempt `study_010_rehearsal_001` stopped before turn 1 and before any
inference call. Windows' default `cp1252` console encoding could not render the
runner's Unicode start banner. The empty initialized artifacts and launch
manifest are preserved. The process was relaunched under a new run ID with
`PYTHONUTF8=1`; no code or study parameter changed.

## Attempt 002

Arm L attempt `study_010_rehearsal_002` completed 200 turns in 15 minutes 47
seconds. Checkpoints were written at turns 100 and 200. Peak estimated context
was 13,464 tokens, below the 40,000-token monitor.

The rehearsal nevertheless failed behavioral integrity. The inference-side
rule classifier repeatedly treated the locked script's turn-local prefix,
"Stay within the [domain] thread and do not connect it to other subjects," as
a persistent cross-turn rule. By turn 200:

- 118 false rules were pinned;
- the pinned-rules block occupied an estimated 5,512 tokens;
- the first domain's Aster Viaduct scope was still active after the script
  moved to clinical epidemiology and archival history;
- the first cross-domain refusal occurred at turn 84; and
- contaminated refusal responses entered STM and LTM.

Arm S was not started. Neither 1,000-turn arm was started.

## Diagnosis

The locked 1,000-turn script contains no genuine persistent behavioral-rule
plant. Its thread-scoping clauses constrain individual filler questions and
change with each domain. The model-generated classifier output, not the
conservative lexical fallback, promoted them to the persistent rule store.

This is a rehearsal-discovered protocol blocker. Continuing would primarily
measure false-rule accumulation and refusal propagation rather than memory
endurance. A new author-authorized amendment must define a symmetric repair,
and a fresh two-arm rehearsal must pass, before a full run begins.
