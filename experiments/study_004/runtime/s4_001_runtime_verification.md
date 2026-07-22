# Study 004 — S4_001 Runtime Verification

**Date:** July 21, 2026  
**Status:** PASS

## Accepted runtime

| Parameter | Verified value |
|---|---|
| Inference artifact | `Qwen3.6-27B-UD-Q6_K_XL.gguf` |
| llama.cpp server | build 9294 (`0f3cb3fc8`) |
| Endpoint | `http://127.0.0.1:8000/completion` |
| Health check | `/health` returned `{"status":"ok"}` |
| Context | 262,144 tokens, one server slot |
| GPU | NVIDIA GeForce RTX 5090, 32 GB |
| Flash attention | enabled |
| KV cache | Q4_0 K and V, GPU-resident |
| Runner configuration | `CDW_INFERENCE_SERVER_URL=http://127.0.0.1:8000` |

The pre-registration fixes the model, context capacity, transport, and hardware but does not fix KV-cache precision. Q4_0 is the highest tested configuration in this verification that keeps the 24.23 GiB model and the full 262k cache GPU-resident with enough headroom to clear the speed gate.

## Registered 200-token speed test

The `/completion` request used `n_predict=200`, `ignore_eos=true`, a deterministic temperature, and no streaming so the server generated exactly 200 tokens.

| Measure | Result |
|---|---:|
| Tokens generated | 200 |
| Server-reported generation speed | **44.28 tok/s** |
| End-to-end wall speed | 43.03 tok/s |
| End-to-end elapsed time | 4.648 s |
| Required floor | > 30 tok/s |
| Gate | **PASS** |

## Fit diagnostics

The initial Q8 cache configuration did not fit fully in VRAM. Configurations were tested without changing the registered model or context capacity:

| KV layout | Server generation speed | Result |
|---|---:|---|
| Q8_0 on GPU | 4.07 tok/s | Model/cache memory pressure; fail |
| Q8_0 on CPU, model on GPU | 16.43 tok/s | CPU attention bottleneck; fail |
| Q5_1 on GPU | 17.80 tok/s | Insufficient VRAM headroom; fail |
| Q4_0 on GPU | **44.28 tok/s** | Accepted; pass |

## Embedding verification

| Parameter | Verified value |
|---|---|
| Artifact | `Qwen3-Embedding-0.6B-Q8_0.gguf` |
| Device | CPU (`n_gpu_layers=0`) |
| Output dimensions | **1,024** |
| Output type | float32 |
| Finite-value check | pass |

The embedding model and dimensionality are unchanged from Study 003.
