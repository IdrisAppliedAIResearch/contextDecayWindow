# EC-001 Amendment 008 — Local rater chat transport

**Study:** EC-001 External Calibration on LongMemEval  
**Registration anchor:** `b595b05e1469c67277844d4bd97f77c89a20772b`  
**Scoring amendment anchor:** `37864822e4c429412b81f67db8af4af804308b8f`  
**Phi runtime anchor:** `b1009254`  
**Status:** AUTHORIZED BEFORE ANY REAL RATER ITEM  
**Authorization:** Program author, August 3, 2026: “Go ahead. You are
authorized to make amendments.”

## Trigger and evidence

All three attempted local instruction-tuned rater families were called through
raw llama.cpp `/completion`, so none received its model-defined instruction
chat template. Phi passed three of four planted cases through that transport
and failed the reasoning-only `NO_ANSWER` case.

A controlled diagnostic changed only the transport to llama.cpp's
OpenAI-compatible `/v1/chat/completions` endpoint with one user message. The
benchmark prompt content, model, seed, binary grammar, token budget, and
expected labels were unchanged. Phi then passed all four cases.

The paired 3/4 versus 4/4 result and zero-real-item boundary are recorded in
`runs/scoring_001/phi_calibration_transport_diagnostic.json`.

## Change

For `llama_cpp` raters only:

- send one user message containing the existing benchmark label or rationale
  prompt to `/v1/chat/completions`;
- use the pinned model alias, fixed seed, temperature zero, one slot, no
  speculative decoding, and the existing token budgets;
- retain Amendment 006's exact `yes|no` grammar for first-pass label calls
  only;
- read the returned assistant message content and pass label surfaces through
  the unchanged strict parser.

The GPT-4o benchmark pass is already a chat-completions call and remains
unchanged. Reader generation remains raw `/completion` as registered.

## Rationale

The local models are instruction-tuned chat models, but the original runner
bypassed the chat template that defines how those instructions are presented.
That lets transport formatting determine calibration validity. Applying the
pinned model template restores the intended instruction surface without
changing the benchmark prompt content or accepting any failed label.

## Exclusions

- Do not change prompt text, criteria, expected calibration labels, parser,
  model, seed, order, grammar, or token budgets.
- Do not add system instructions or few-shot examples.
- Do not change GPT-4o or reader request shapes.
- Do not infer labels from the pre-amendment failed outputs.
- Re-run all four planted cases before any real item.
