# EC-001 Amendment 007 — Second rater replacement

**Study:** EC-001 External Calibration on LongMemEval  
**Registration anchor:** `b595b05e1469c67277844d4bd97f77c89a20772b`  
**Scoring amendment anchor:** `37864822e4c429412b81f67db8af4af804308b8f`  
**First replacement anchor:** `063de46d693e6e5c1afca0c43b90a777b4956aff`  
**Local grammar anchor:** `bf57479c`  
**Status:** AUTHORIZED BEFORE ANY REAL RATER ITEM  
**Authorization:** Program author, August 3, 2026: “Go ahead. You are
authorized to make amendments.”

## Trigger and evidence

After Amendment 006 enforced the exact binary surface, the Llama replacement
passed the exact-positive, partial-negative, and reasoning-only `NO_ANSWER`
calibration cases but substantively rejected the correct abstention response.
The rater stopped before loading or seeing any real benchmark packet.

The full result is recorded in
`runs/scoring_001/llama_calibration_semantic_failure.json`.

## Change

Replace only the `llama` rater family with a `phi` family rater. Lock the exact
replacement model, quantization, source revision, file hash, server
properties, and seed in a third runtime record before calibration.

The provisioned replacement is `bartowski/phi-4-GGUF` at repository revision
`19cd65f97c2f1712a81c506611d3f9c94b16a1e1`, file
`phi-4-Q5_K_M.gguf`, expected SHA-256
`b4b1ecedddfdd25a9c44c10a77bb118bcbb6a9004234286c7d4a4510c907f073`.
The downloaded bytes must match before the runtime record can pass.

The three rater families become GPT-4o, Phi, and Mistral. Qwen remains
excluded as the reader family, and GPT-5 remains the separate adjudicator.
The local binary-label grammar from Amendment 006 applies unchanged.

## Rationale

Llama failed the semantic calibration after its output-format issue was
removed, so retaining it would knowingly invalidate abstention scoring.
Replacement occurs before any real rater item and changes no observed answer,
packet, prompt, parser, criterion, trigger, or aggregation rule.

## Exclusions

- Do not weaken or reinterpret the abstention calibration.
- Do not tune on, inspect, or retry any real item with a failed family.
- Do not change GPT-4o, Mistral, the adjudicator, reader, subset, packets, or
  mechanical-zero decisions.
- Phi must pass all four planted cases before any real scoring call.
