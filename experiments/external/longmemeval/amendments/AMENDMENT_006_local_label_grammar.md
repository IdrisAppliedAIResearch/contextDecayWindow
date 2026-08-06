# EC-001 Amendment 006 — Local binary-label decoding grammar

**Study:** EC-001 External Calibration on LongMemEval  
**Registration anchor:** `b595b05e1469c67277844d4bd97f77c89a20772b`  
**Scoring amendment anchor:** `37864822e4c429412b81f67db8af4af804308b8f`  
**Revised runtime anchor:** `95192b73`  
**Status:** AUTHORIZED BEFORE ANY REAL RATER ITEM  
**Authorization:** Program author, August 3, 2026: “Go ahead. You are
authorized to make amendments.”

## Trigger and evidence

The replacement Llama rater reached the first planted calibration item and
returned the correct semantic label followed by an unsolicited explanation:
`yes\nThe model response contains the correct answer.` The registered strict
parser rejected that non-binary surface. The rater stopped before loading or
seeing any real benchmark packet.

The raw surface, parser outcome, model hash, and zero-real-item boundary are
recorded in
`runs/scoring_001/llama_calibration_surface_failure.json`.

## Change

For llama.cpp rater calls that request the first-pass binary label, add a
decoding grammar whose complete language is exactly lowercase `yes` or
lowercase `no`:

```text
root ::= "yes" | "no"
```

Pass the constraint through an explicit `binary_label` call parameter. Use it
for calibration label calls and real first-pass label calls only. Do not use
it for the second, label-conditioned rationale call.

The strict parser, maximum label token budget, prompt bytes, model, seed,
question order, calibration expectations, and all scoring criteria remain
unchanged. The GPT-4o benchmark-protocol call remains byte- and
request-shape-compatible with the pinned benchmark and receives no grammar.

## Rationale

The protocol requires an unambiguous exact binary surface and a separate
rationale call. Constrained local decoding enforces that already-registered
output alphabet without reinterpreting or accepting a previously invalid
surface. It prevents a formatting surrogate from blocking a semantic
calibration while preserving the calibration criterion itself.

## Exclusions

- Do not broaden `parse_binary_label`; the failed surface remains invalid.
- Do not infer a label from prefixes, explanations, log probabilities, or
  hidden reasoning.
- Do not constrain rationale calls.
- Do not add the grammar to GPT-4o or change its benchmark prompt/request.
- Do not change any calibration expected label or retry a real item.
