# BEAM-001 Live Result

**Disposition:** `CHARACTERIZED`

**Deviations:** `DEVIATION_002`, `DEVIATION_003`, `DEVIATION_004`; registered completion gates failed.

**Diagnostic numerical disposition:** `NO_DEMONSTRATED_GAIN`

## Primary

T1-C0: 0.005180; 95% cluster bootstrap [-0.017573, 0.027653]; paired sign-flip p=0.65797034.

## A0 Guardrail

T1-A0: -0.006980; one-sided 95% lower=-0.022932.

## Arm Means

- `A0_CC80_QWEN_GPU_COMMON`: 0.481455
- `C0_STATIC_ASPECT_QWEN_GPU_COMMON`: 0.469295
- `T1_PARENT_OPPORTUNITY_ASPECT_QWEN_GPU_COMMON`: 0.474475

## Scale Guardrails

- `100K`: T1-C0 -0.009479; T1-A0 -0.014583
- `500K`: T1-C0 0.023953; T1-A0 -0.007867
- `1M`: T1-C0 -0.005217; T1-A0 -0.001747

## Category Guardrails

- `abstention`: 0.055556
- `contradiction_resolution`: 0.055556
- `event_ordering`: 0.067306
- `information_extraction`: -0.031250
- `instruction_following`: 0.004630
- `knowledge_update`: -0.087963
- `multi_session_reasoning`: -0.019213
- `preference_following`: 0.016204
- `summarization`: -0.002083
- `temporal_reasoning`: -0.006944
