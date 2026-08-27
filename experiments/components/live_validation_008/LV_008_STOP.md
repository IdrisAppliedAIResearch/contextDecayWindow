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

## Post-stop descriptive scoring

After the registered stop was sealed, the program owner explicitly directed
the agent to judge the already generated answers without creating another
study. This section does not convert LV-008 into a registered result.

The frozen blind judge completed 720/720 judgments over 240 answers. Seven judge
calls across six answers reached the resumed 512-token ceiling, but all emitted
parseable verdicts. Forcing every capped judge verdict to incorrect changes
zero answer majorities and zero item-arm majorities. The reader answer that
caused the original 4,096-token stop was judged correct by all three judges.

Item-level correct totals over the 16 primary questions:

- `PAIRWISE`: 4
- `COMMUNITY`: 5
- `COMMUNITY_QB`: 8

Descriptive paired changes:

- `COMMUNITY` versus `PAIRWISE`: 1 gain, 0 losses; the gain is breadth.
- `COMMUNITY_QB` versus `COMMUNITY`: 3 gains, 0 losses; 2 breadth and 1 targeted.
- `COMMUNITY_QB` versus `PAIRWISE`: 4 gains, 0 losses; 3 breadth and 1 targeted.

All three arms refused the category-5 item on 5/5 replicates. Containment tied
on all 16 items, showing that the semantic judge—not literal gold containment—
detected the answer gains. The combined renderer is a promising descriptive
signal on this selected LoCoMo population, not a registered verdict or an
adoption decision.

- post-stop result SHA-256:
  `c7927a500d7f0d50b8159819d4710d12966c56f188817541068bbbd56e108930`
- per-item table SHA-256:
  `aee09565b239aa906a87c3a322903f16fb271726120f052b4cfcf6e0168453ef`
- blind judgments SHA-256:
  `2e209db5bd481f98acb428addd653bfcb74f774d28c701d037b5539bebd3d011`
