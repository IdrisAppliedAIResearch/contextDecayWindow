# LV-008 Preflight

Date: 2026-08-26

Status: `PASS`

Registration commit: `f5c86b73`  
Implementation commit: `a57c7313`

## Seals

- Registration SHA-256:
  `8b19ee2b922731f34802e250b8100d113dc9099f33bdee6b0d02ebddf4d0cd62`
- Implementation script SHA-256:
  `290299837fe49e7012cae5a7ecb7db156296b7de9518ccb68a2963074d604c14`
- Test SHA-256:
  `fa6545fc1ac1d1e658a439a2be081378fb380bb9b6a80fa61d421fb2b6754f2c`
- Prompt seal SHA-256:
  `dc40d134e0e281fd0a064371620ce2a9a99f8f4a39855d3f32072ca9a844e9d9`
- Preflight artifact SHA-256:
  `65aabef85801a9527607c50c01b639ace6cab53d3861dfbcc95b2a32de07fe2d`

## Outcome

- PF1: all seven registered input anchors passed, including the exact Qwen3.8
  source file and Ollama manifest.
- PF2/G-PROMPTS: all 51 prompt strings and the complete gzip seal reproduced
  LV-007 byte-for-byte. The 17 rows contain the exact three named mechanisms.
- PF3: registration preceded implementation; mapping access was rejected;
  append-flush-fsync is enforced.
- PF4: every disposition and sign guard is reachable. A one-token live control
  ended by length, proving the binding cap-stop branch can fire.
- PF5: all 17 comparison keys are unique and content-derived.
- PF6: the Part 1 Qwen3.8 response reproduced at 12 output tokens and SHA-256
  `d993af43c78fee1775ba2f2d3f864c71a8d1dbc4615119307ce4f43dc875bdef`.
- PF7/G-GPU: two same-seed real prompt repeats were byte-identical. Ollama
  reported 21,558,366,042 of 21,558,366,042 runtime bytes in VRAM.
- PF8: five reader replicates and 16 primary items can expose a large conversion
  on this selected population, not small effects or transfer.
- PF9: compactness, exact evidence preservation and judge agreement remain
  surrogates; live blind answer scoring is still required.
- PF10: no structural or availability result is treated as a reader verdict.
- G-CONTEXT: maximum frozen prompt size is 44,772 UTF-8 bytes; the executed
  prefix used 8,754 tokens, both below 65,536.

Focused implementation tests: 5 passed.  
Preflight calls: 4 reader, 0 judge, 0 embedding.

The full 255-answer schedule is authorized. No scheduled answer existed when
this record was written.
