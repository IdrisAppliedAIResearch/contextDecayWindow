# LV-008 Part 1 Exploration — Reader Continuation

Date: 2026-08-26

Status: `RUNTIME_VIABLE`

## Purpose

LV-007 stopped before judging because one of its 255 `qwen-custom` reader answers
reached the common 2,048-token output cap. This exploration asks whether the
currently available Qwen3.8 reader provides a deterministic, non-speculative
runtime for a fresh replication of the three frozen renderers. It does not
repair, complete, or reinterpret LV-007.

No benchmark labels, gold answers, generated answer text, blind surface, or
judge were opened. The program retained only response hashes and transport
metadata.

## Anchors

- LV-007 frozen prompts SHA-256:
  `dc40d134e0e281fd0a064371620ce2a9a99f8f4a39855d3f32072ca9a844e9d9`
- LV-007 reader answers SHA-256:
  `da1f8f62ba571ab17660091610077b1171b72a8a529d984fbad5962f04141f22`
- LV-007 generation summary SHA-256:
  `97a428cab42d9721c9c6af2d7b648113c0f4d76a1a2cf389e9be6677db05928f`
- LV-007 stop record SHA-256:
  `d1497d7aadc47f6f4afb67361d5f3face895dc6d07142dffefbfbb9412b74957`
- Exploration script SHA-256:
  `dbe005b9f6c71f79d5f0233f09f8ec678a4a5adc583b5c3a9c981d2c4a7888f9`
- Exploration artifact SHA-256:
  `a8a3873e0a6358cc9b610bbae637aed844c24bb5a0ed979c91d57ae1aa2fa3ea`

## Runtime identity

- Server: llama.cpp `b10360-90e6a9131`, `127.0.0.1:8000`
- Model: `Qwen3.8-27B-UD-Q4_K_XL.gguf`, Q4_K, 27.3B parameters
- Context: 200,192 tokens
- Parallel slots: one
- Speculative decoding: disabled in the custom launch; server default reported
  `none`

The protected `start-model` definition was not edited. Its spawned server was
replaced by a separate direct launch so the study runtime could omit
speculative decoding.

## Behavioral identity

LV-007's stopped schedule contains all 255 planned reader answers and exactly
one capped answer: `COMMUNITY`, replicate 0, seed 5005, comparison key
`7fd147...08c85`. Under the new reader, this exact 9,008-token prompt produced
33 output tokens and an EOS stop.

The locked LV-007 registration incorrectly called that reader Qwen3.5 by
mistaking its `qwen35` architecture label for a model version. The frozen
manifest actually resolves to a Q6_K blob whose embedded metadata identifies
`Qwen3.6-27B`; see `LV_007_ERRATUM_001.md`.

At both output caps, two same-seed repeats were byte-identical. The response
hash was also identical across the 2,048- and 4,096-token caps. Thus the cap is
not binding on this trace under Qwen3.8; changing the reader changes the
observed failure state.

## Distribution

| Cap | Calls | Prompt tokens | Output tokens | Stop | Warm wall time | Response identity |
|---:|---:|---:|---:|---|---:|---|
| 2,048 | 2 | 9,008 each | 33 each | EOS/EOS | 12.183 s | identical |
| 4,096 | 2 | 9,008 each | 33 each | EOS/EOS | 12.271–12.304 s | identical |

The first 2,048 call included a 588.365-second cold model load and is excluded
from the warmed latency range, not from the artifact.

Speculative counters were zero before and after all four calls: zero draft
tokens, zero accepted draft tokens, and zero draft verification steps.

## Degenerate and absorbing states

- Output-cap absorption: any answer reaching the common cap makes the new run
  invalid before blind judging.
- Reader-change absorption: the Qwen3.8 Q4_K_XL outputs cannot fill the missing
  Qwen3.6 Q6_K cell or complete LV-007. A valid continuation must regenerate all
  arms and replicates under the same new reader.
- Warm-cache absorption: the first request includes model loading; latency from
  that request cannot certify steady-state generation cost.

## Surrogate audit

This exploration can pass while the intended renderer claim is false. One
prompt stopping naturally and replaying exactly does not prove that all 255
reader calls will stop naturally, that the reader is fully GPU resident, or
that compact grouping improves answers. Those remain explicit Preflight and
live-run requirements.

## Consequence

A new registration may compare the three already frozen LV-007 prompt arms
under Qwen3.8. It must call the exercise a reader replication, use a common
output cap for every arm, regenerate the full answer schedule, and prohibit any
reuse of LV-007 answers or result language.
