# LV-002 Amendment 001 — seal a closed-think prefill

**Status:** locked before any C0/T1 treatment generation  
**Date:** 2026-08-26  
**Parent registration SHA-256:**
`34ddd063b7c17873ae92b59f929bd788b7f66fb66d53c910a81d270bd619254a`

## Trigger

The first Preflight attempt passed prompt reproduction, contamination,
determinism and GPU checks but failed `G-PROMPT`. Ollama 0.33.0 accepted
`think:false` and nevertheless emitted a visible `<think>` trace in raw mode.
The seeded prefix and nine floor/judge responses reached the registered token
limit while reasoning instead of answering. Commit `b1b0e75a` preserves the
failed attempt. No C0/T1 treatment answer was generated.

## Authorized correction

Append these exact bytes to every reader and judge prompt before sealing and
generation:

```text
\n<think>\n</think>\n
```

This is the same closed-think prefill carried by HH-001's reader. It implements
the registration's already-locked requirement that thinking be disabled; it
does not change the question, memory block, gold reference, judge rubric,
sampling, seed, token limit, arms, population, schedule, bar or disposition.

A one-call instrument check on a floor prompt that had previously exposed raw
thinking returned exactly `I don't know.` in six tokens with `done_reason=stop`.
That call is diagnostic and cannot enter the outcome.

## Required replay

The old prompt seal is superseded. Implementation must place the suffix inside
the hashed prompt bytes, rebuild and commit all prompt digests, then rerun every
Preflight check including the full floor. The prior passing subchecks are not
carried by assumption. Any remaining truncation stops the study.
