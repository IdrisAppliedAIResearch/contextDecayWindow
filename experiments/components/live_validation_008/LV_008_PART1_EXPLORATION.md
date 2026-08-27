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
  `1a947cfe58519e64a142f7ba622cc405d6b87e45b3cf0ebe5239518236b86e6a`
- Exploration artifact SHA-256:
  `6092121c1459be2516f3e7a2fde1557541c00d93c7fce199e65ef4def65e77e1`

## Runtime identity

- Server: Ollama `0.33.0`, `127.0.0.1:11434`
- Alias: `lv008-qwen38-q4:latest`, manifest digest
  `281d02f0ad1a4b4928fcf1450e6bd1bb88e0d57c0051df03a993265ec6662adc`
- Source file: `Qwen3.8-27B-UD-Q4_K_XL.gguf`, SHA-256
  `bee238bbeb3dc0a34bde4d0dedbaee1f98c009e8bb4226f03070054c12fb1372`
- Ollama runtime metadata: Q4_K_S, 27.3B parameters, 65,536-token context
- GPU residency: 21,558,366,042 of 21,558,366,042 runtime bytes in VRAM
- Speculative decoding: not enabled or exposed by the frozen Ollama API call

The protected `start-model` definition was not edited. The study alias was
imported separately from the exact GGUF and is served by Ollama.

## Behavioral identity

LV-007's stopped schedule contains all 255 planned reader answers and exactly
one capped answer: `COMMUNITY`, replicate 0, seed 5005, comparison key
`7fd147...08c85`. Under the new reader, this exact 9,008-token prompt produced
12 output tokens and a natural stop.

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
| 2,048 | 2 | 9,008 each | 12 each | stop/stop | 0.268–0.292 s | identical |
| 4,096 | 2 | 9,008 each | 12 each | stop/stop | 0.284–0.286 s | identical |

The model was already resident before this final four-call replay. The process
record proves full VRAM residency before and after the calls.

## Degenerate and absorbing states

- Output-cap absorption: any answer reaching the common cap makes the new run
  invalid before blind judging.
- Reader-change absorption: the Qwen3.8 Q4_K_XL outputs cannot fill the missing
  Qwen3.6 Q6_K cell or complete LV-007. A valid continuation must regenerate all
  arms and replicates under the same new reader.
- Warm-cache absorption: the measured calls used a resident prompt cache;
  latency cannot certify cold-start or distinct-prompt throughput.

## Surrogate audit

This exploration can pass while the intended renderer claim is false. One
prompt stopping naturally and replaying exactly does not prove that all 255
reader calls will stop naturally or that compact grouping improves answers.
Those remain explicit Preflight and live-run requirements.

## Consequence

A new registration may compare the three already frozen LV-007 prompt arms
under Qwen3.8. It must call the exercise a reader replication, use a common
output cap for every arm, regenerate the full answer schedule, and prohibit any
reuse of LV-007 answers or result language.
