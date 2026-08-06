# EC-001 Amendment 005 — Rater replacement after calibration failure

**Study:** EC-001 External Calibration on LongMemEval  
**Registration anchor:** `b595b05e1469c67277844d4bd97f77c89a20772b`  
**Scoring amendment anchor:** `37864822e4c429412b81f67db8af4af804308b8f`  
**Initial runtime anchor:** `2480595f`  
**Status:** AUTHORIZED AFTER READER GENERATION, BEFORE ANY REAL RATER ITEM  
**Authorization:** Program author, August 3, 2026: “Go ahead. You are
authorized to make amendments.”

## Trigger and evidence

The locked Gemma rater failed the binding planted calibration gate before the
rater loaded or saw any real benchmark packet. It correctly labeled the
exact-positive, partial-negative, and reasoning-only `NO_ANSWER` cases, but
labeled the correct abstention response `no` instead of `yes`.

The complete four-case result and the zero-real-item boundary are recorded in
`runs/scoring_001/gemma_calibration_failure.json`.

## Change

Replace only the `gemma` rater family with a `llama` family rater. Lock the
exact replacement model, quantization, source revision, file hash, server
properties, and seed in a new runtime record before retrying calibration.

The provisioned replacement is
`bartowski/Meta-Llama-3.1-8B-Instruct-GGUF` at repository revision
`bf5b95e96dac0462e2a09145ec66cae9a3f12067`, file
`Meta-Llama-3.1-8B-Instruct-Q6_K_L.gguf`, expected SHA-256
`9bf5598b3cc6c5804c520aa6349266d2e2c9a22402e157bd9b187dc34806dad6`.
The downloaded bytes must match before the revised runtime record can pass.

The three rater families therefore become GPT-4o, Llama, and Mistral. Qwen
remains excluded because it is the reader family. GPT-5 remains the separate
adjudicator family.

## Rationale

Calibration is a pre-scoring validity gate. Preserving a rater known to fail
the abstention criterion would allow the scoring process to pass while the
claimed ability to apply the benchmark rubric is false. Replacement preserves
three-family independence without changing any item, prompt, label parser,
criterion, trigger, aggregation rule, or observed reader answer.

## Exclusions

- Do not weaken, remove, or reinterpret the failed abstention calibration.
- Do not retry Gemma with prompt changes or inspect real answers to tune it.
- Do not change the GPT-4o benchmark pass, Mistral pass, adjudicator, reader,
  subset, scoring packets, or mechanical-zero decisions.
- The Llama replacement must pass all four planted cases before any real item.
