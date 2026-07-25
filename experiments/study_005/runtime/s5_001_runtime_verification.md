# Study 005 - S5_001 Runtime Verification

**Date:** July 22, 2026
**Status:** PASS
**Pre-registration SHA:** `20aa7707e780543ccbe462efadf3bb1263b3813e`
**Verified implementation SHA:** `f8796fd541125dd39164bb2bd815e9afe52484ab`

## Accepted runtime

| Parameter | Verified value |
|---|---|
| Inference artifact | `Qwen3.6-27B-UD-Q6_K_XL.gguf` |
| llama.cpp server | build 9294 (`0f3cb3fc8`) |
| Endpoint | `http://127.0.0.1:8080/completion` |
| Context | 50,000 requested (`50,176` reported), one server slot |
| GPU | NVIDIA GeForce RTX 5090, 32 GB, driver 610.74 |
| Flash attention | enabled |
| KV cache | Q8_0 K and V |
| RNG seed | 5005 |
| Sampling | temp 1.0, top-p 0.95, top-k 20, min-p 0.0 |
| Penalties | presence 0.0, repeat 1.0 |
| Speculative decoding | off; `/props` reported `speculative.types: none` |
| Study script SHA-256 | `d8ba73fd02bfd41bec156904fb6a3328bbed3d0da8bff05e4667d2e450752f01` |

The exact server launch used for both determinism phases was:

```powershell
C:\Users\muzaf\.unsloth\llama.cpp\build\bin\Release\llama-server.exe `
  -m C:\Users\muzaf\.cache\huggingface\hub\models--unsloth--Qwen3.6-27B-MTP-GGUF\snapshots\5cb35eb3dcbf52dbce5f87dbc64df6aaffadcace\Qwen3.6-27B-UD-Q6_K_XL.gguf `
  --host 127.0.0.1 --port 8080 `
  --ctx-size 50000 --parallel 1 `
  --cache-type-k q8_0 --cache-type-v q8_0 `
  --flash-attn on --jinja --metrics `
  --temp 1 --top-p 0.95 --top-k 20 --min-p 0.0 `
  --presence-penalty 0.0 --repeat-penalty 1.0 `
  --seed 5005
```

No speculative-decoding flag was present. The server prints a checkpoint-capability warning for this MTP model and then reports that no speculative implementation is configured; `/props` independently confirmed that speculative decoding was disabled.

## Context speed gate

Each configuration generated exactly 200 tokens from the same prompt and seed. Both fresh-server responses had SHA-256 `6c1c9f03e3b4f42c0e8c4538d31b286e8019820710ad66b3bb3513a3973cefbc`.

| Requested context | Generation speed | Predicted time | Result |
|---:|---:|---:|---|
| 120,000 | 45.677 tok/s | 4,378.576 ms | PASS |
| 50,000 | **45.771 tok/s** | 4,369.559 ms | PASS; retained by neutral-case rule |

Both configurations exceeded the required 30 tok/s floor. The difference was operationally neutral, so the pre-registered neutral-case rule retained 50,000 for VRAM headroom.

## Determinism diagnosis

The first diagnostic reused one server lifecycle and mismatched turns 2-10. A second diagnostic correctly used fresh server processes but mismatched responses at turns 2 and 4-10. Its turn-2 prompt diff isolated the only input difference to the random UUID rendered in `<rule id="...">`.

The opaque rule ID was model-visible despite carrying no semantic information. Rule IDs and Study 005 distilled-record IDs were therefore changed to content-derived UUIDv5 values. Episode UUIDs and complete stored provenance remain unchanged. A direct server probe also confirmed that two identical prompts return identical text and report seed 5005 under the registered CLI-only seed; no unregistered request seed was added.

## Determinism gate

The accepted check ran the same ten-turn Study 005 prefix in two independent runner and server lifecycles:

| Check | Result |
|---|---|
| Server PIDs | 13376, 9028 (distinct) |
| Constructed prompts | **10/10 byte-identical** |
| Assistant responses | **10/10 byte-identical** |
| Dream events through turn 10 | 0 in both phases |
| Distilled records through turn 10 | 0 in both phases |
| Peak estimated context | 5,982 tokens (11.96% of selected capacity) |
| 80% context ceiling | not approached |
| Gate | **PASS** |

The machine-readable per-turn prompt and response hashes are in `determinism_prefix_003/determinism_report.json`. Raw benchmark, server, prompt, and failed-diagnostic artifacts remain local and ignored; the failures are disclosed above rather than silently discarded.

## Embedding verification

| Parameter | Verified value |
|---|---|
| Artifact | `Qwen3-Embedding-0.6B-Q8_0.gguf` |
| Device | CPU (`n_gpu_layers=0`) |
| Dimensions | 1,024 |
| Output type | float32 |
| Finite-value check | pass |
| Verification-vector SHA-256 | `d3860b2d2fb3ffb250b41c3b612ba67728b41bbe48c49ad9e6e81ac8a45cd186` |

The embedding artifact and dimensionality are unchanged from Study 004.
