# LV-008 Stop — Reader Output Cap

Date: 2026-08-26

Status: `STOPPED_BEFORE_JUDGING`

## Binding trigger

LV-008 generated and fsynced all 255 registered Qwen3.8 reader answers. The
generation-completeness gate then found one answer with `done_reason=length` at
the common 4,096-token ceiling. Section 4 and G-COMPLETE require every answer to
stop naturally and require a stop before judging when any answer ends by
length. The run therefore has no renderer result.

No retry, higher-cap continuation, blind surface, mapping join, judge call or
semantic analysis is authorized.

## Failed cell

- comparison key:
  `c0be5dc5bb6a516c1deed9f06c5c9cac280f332ce134f31733e55c3dbd4bb891`
- conversation and source index: `conv-42`, `79`
- registered stratum: breadth, category 1, offline opportunity gain
- arm: `COMMUNITY_QB`
- replicate and seed: `3`, `5008`
- prompt SHA-256:
  `b994fccfe5c7e5b6ce9db45ebc6a9dacc2e7332895879d64d63dbd0a76cabd8b`
- block SHA-256:
  `3b65d4e2baa7e900f36adeb7482c6ece4be24aa3c7ea00148fda5ac60a4294a1`
- prompt tokens: `8,959`
- output tokens: `4,096`
- wall time: `56.154` seconds

Generated answer text and benchmark gold were not opened by the operator.

## Artifact seals

- answers: 255 rows, SHA-256
  `738cefb23455e35876d9286f914aabe3c99d17e62def8ed5a88272743460ba11`
- generation summary SHA-256:
  `52e3626d9f55ac4d0b04b4db5e036e444c8032eabf53bc67567a7b37c509456a`
- stdout log SHA-256:
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- stderr log SHA-256:
  `225aea79db183d8739aaecdaf448daf4297e11ab2a0cfa88376ddb660d0cbc07`

Schedule validation: 255/255 rows, 0 missing, 0 extra, 0 duplicate, 1
truncated. The registered model remained fully GPU-resident after generation:
21,558,366,042 of 21,558,366,042 runtime bytes in VRAM.

## Interpretation boundary

Part 1's exact formerly problematic prompt naturally stopped at 12 tokens under
both tested ceilings, but that single-prompt check did not certify the full
255-call population. Its registered surrogate residual was realized by a
different breadth prompt and seed.

LV-008 makes no claim about pairwise rendering, semantic communities, question
repetition, answer correctness or adoption. LV-007 remains independently
stopped and unscored. Reader calls: 255 scheduled plus 4 Preflight. Judge and
embedding calls: zero.
