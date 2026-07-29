# Decision 001 - Audit Study 010 Context-Peak Provenance

**Date:** 2026-07-29
**Type:** post-publication traceability audit; no inference
**Authorization:** user request in the DR-001 review

## Trigger

DR-001 established that Study 010's LTM selector undercharged serialized blocks.
The Study 010 report separately cites a peak of 27,154 estimated context tokens
as evidence that both 1,000-turn runs stayed below the 40,000-token monitor.
That deployment-facing claim must be checked against the committed serialized
prompts rather than assumed to share the LTM accounting defect.

## Decision

Add a deterministic offline audit that, for every turn in both Study 010 arms:

1. reads the committed `constructed_prompt` artifact;
2. removes only the runner-appended `\n\nAssistant:` generation cue;
3. recomputes the registered estimator as `len(prompt) // 4`;
4. compares the result with the committed `context_sizes.csv` value; and
5. reports each arm's peak turn, serialized character count, and estimate.

The audit must hash every input it reads and must not edit any Study 010 run
artifact.

## Interpretation Boundary

A complete match establishes that the logged context trajectory was calculated
from the serialized prompt, not from the undercharged LTM content total. It does
not establish an exact model-tokenizer count. The LTM budget violation remains
a separate defect and is not excused by a passing prompt-telemetry audit.

