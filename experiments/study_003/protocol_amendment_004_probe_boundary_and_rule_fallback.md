# Study 003 — Protocol Amendment 004: Probe Boundary and Rule-Detection Fallback

**Recorded:** July 19, 2026, after the invalid `study_003_full_001` run and before any rubric scoring.

## Trigger

Full Run 001 exposed two implementation mismatches with the locked design. The transition engine treated late rubric probes as new scripted topic phases, producing promotion events at turns 112, 114, and 118. The local Qwen server also omitted the rule-detection metadata tag on turn 1, causing the parser to discard an otherwise explicit persistent rule declaration.

## Amendment

1. LTM transition evaluation is active through turn 111. Turns 112–120 are the pre-declared rubric-probe block and cannot emit promotion events. They still use normal topic assignment, retrieval, storage, and consolidation. This implements the pre-registration's definition of four 30-turn phases and exactly three promotion boundaries; it does not select events based on observed scores or promotion outcomes.
2. If model-generated rule metadata is absent, a conservative deterministic fallback may classify the current user message as a persistent rule only when it contains all three signal classes: explicit rule/requirement/constraint language, conversation-wide persistence language, and a mandatory directive. The verbatim normalized user message is stored as the rule summary. Model-provided metadata remains authoritative whenever present.

No rubric criteria, planted facts, retrieval thresholds, topic thresholds, consolidation thresholds, promotion filters, filter weights, or promotion score thresholds change.

## Required re-verification

Before rerunning the full study:

1. Unit tests must confirm that all rubric turns are outside the promotion window while turn 111 remains eligible.
2. Unit tests must confirm that the fallback detects an explicit conversation-wide rule and rejects one-off formatting requests and descriptive mentions of rules.
3. The existing 35-turn ablation remains valid for the first promotion boundary because this amendment does not alter turns 1–35 except for making missing rule metadata fail-safe.

The fresh full run must use `study_003_full_002` (or another unused run ID). Acceptance still requires exactly three promotion events near turns 31, 61, and 91 and at least one persisted rule from the opening declaration.
