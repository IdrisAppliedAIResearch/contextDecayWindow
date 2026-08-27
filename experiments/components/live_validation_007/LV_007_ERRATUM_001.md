# LV-007 Erratum 001 — Reader Identity

Date: 2026-08-26

## Correction

`LV_007_PRE_REGISTRATION.md` identifies `qwen-custom:latest` as “Qwen 3.5
27.3B Q6_K.” The “Qwen 3.5” portion is false. It was inferred from Ollama's
`qwen35` architecture label, which is an implementation architecture name, not
the model release name.

The exact manifest locked and used by LV-007 is still present:

- alias: `qwen-custom:latest`
- manifest SHA-256:
  `3516cd593f43f07312d78251081d0253f68e541f3ce83681fef0305611306fc2`
- model layer SHA-256:
  `773f1bf0be0589d056ce05476a8a135b50494a3f2ecc3f8f0c4f2c3594bba02e`
- model layer size: 22,884,406,400 bytes
- Ollama-reported architecture: `qwen35`
- Ollama-reported parameters and quantization: 27.3B, Q6_K
- embedded model strings: `Qwen3.6-27B`, `Qwen3.6 27B`, and
  `Qwen/Qwen3.6-27B`

Therefore the frozen LV-007 reader is identified as Qwen3.6 27B Q6_K, not
Qwen3.5. The current `start-model` target is a separate
`Qwen3.8-27B-UD-Q4_K_XL.gguf` file.

## Scope

This erratum corrects reader identity only. It does not alter the frozen
prompts, 255 generated answers, one-cap-stop fact, hashes, or LV-007's mandatory
stop before judging. The locked pre-registration is not edited.
