# DA-081 Frame State-Transition Anatomy

**Status:** `POSTHOC_FRAME_STATE_TRANSITIONS_CHARACTERIZED`
**Date:** August 31, 2026
**Parent:** DA-080 result commit `df21b41f`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Does each required replaceable frame create an exact evidence-blind query-state
transition that a reader could recognize without a learned relevance score?

## Fixed Anatomy

Use the 13 sealed DA-079 residual requirements, sealed DA-078 prompts, and
sealed DA-045 frame order. Reconstruct source member text by identity. Extract
DA-074's exact untyped and role-typed query unigram/adjacent-bigram features.

Initialize cumulative state with every member in the immutable DA-078 prompt.
Replay only DA-045 `FRAME` actions in ordinal order. For each required frame
report its feature count, features new relative to the prompt, features new at
arrival after prior frames, exact-signature prior count, and the number of
earlier frames that also changed cumulative state.

Classify the required frame as `NO_QUERY_FEATURES`, `REDUNDANT_AT_ARRIVAL`, or
`NOVEL_AT_ARRIVAL`. These are descriptive states, not a stopping policy. Do not
fit a threshold, combine features into a score, inspect answer text, or alter
frame order.

Require exact 13/13 joins, source identity replay, immutable DA-078 membership,
sealed DA-045 order, byte-identical replay, and zero model, embedding, and cache
calls. No reader, stopping, transfer, delivery, or adoption claim.

## Result

Seven of 13 required frames are `NOVEL_AT_ARRIVAL`; six are
`REDUNDANT_AT_ARRIVAL`; none lacks query features. Required frames contain p50
14 exact features and add p50 one at arrival. Exact frame signatures have no
prior duplicate, but that weak identity property is common and is not a stop.

For the seven novelty cases, earlier cumulative-state changes are usually few
(population p50 0, p90 1.8). This is a local recognition signal, not a universal
rule: nearly half of required frames create no lexical state transition at all.
Replay is byte-identical; zero model, embedding, and cache calls.

Artifacts:

- `artifacts/analysis/result.json`
- `artifacts/analysis/transitions.jsonl.gz`
