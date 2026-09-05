# BEAM-001 Amendment 003 - GPU local embedder

**Status:** `AUTHORIZED BLOCKER REPAIR - PREFLIGHT CHARACTERIZED`  
**Date:** August 28, 2026  
**Supersedes:** Amendments 001 and 002 for Part 1 embedding only  
**Author direction:** use the local embedder and load it to the GPU

## 1. Trigger

The amended OpenAI input gate stopped before any API request. Thirty-five of
59,210 exact public-store episode texts exceed the embeddings endpoint's
8,192-token per-input limit; the longest is 26,954 `cl100k_base` tokens. The
base design forbids truncating, splitting, merging or dropping episode content.
The committed disposition is `EMBEDDING_INPUT_NOT_IDENTIFIED` at
`b56e3ccc`.

The author then directed BEAM-001 to use the registered local embedder with GPU
acceleration.

## 2. Part 1 embedder

All three arms return to the base design's model artifact:

- model: `Qwen3-Embedding-0.6B-Q8_0.gguf`;
- model SHA-256:
  `06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439`;
- runtime: `llama-cpp-python` 0.3.25 with CUDA compute capability 12.0;
- device: NVIDIA RTX 5090;
- `n_gpu_layers=-1`;
- `n_ctx=32768`;
- `n_batch=2048`;
- `n_ubatch=512`;
- one exact UTF-8 text per embedding call; and
- float32 output width 1,024.

The public `episodic-chat` source remains unchanged. A study-private callable
with the pinned model-file SHA is passed to public `EpisodeStore`; all episode
formation still enters through `EpisodeStore.append()`. Its content-addressed
cache is populated before store construction and is read-only during context
construction.

The future reader and judge reservation from Amendment 001 remains
`gpt-4o-mini-2024-07-18` at temperature 0.0. Part 1 still makes no generation,
judge or OpenAI API call.

## 3. Preflight characterization

At the pinned source and environment before implementation:

- GPU model load: 0.582 seconds;
- longest real episode: key
  `f52f820509c5b290965ac9f33eb5d54f840751d2d0dc8db8e8792120e0a29834`;
- longest Qwen-tokenizer length: 26,960, within 32,768;
- longest GPU embedding time: 0.359 seconds;
- output: 1,024 finite float32 values with nonzero norm;
- longest-vector SHA-256:
  `e81c77ddef7f75529bf147cea16337d90688bd634f931e4f7fbff38bb1d91825`;
- repeated longest-vector bytes: identical; and
- GPU sentinel SHA-256:
  `a52c6019c79957d0ea3af9bb15d863a826f825deebc9f7aa03232e31e601df3a`.

GPU and the carried CPU call are not byte-identical. On the fixed sentinel,
CPU/GPU cosine is 0.9996604323, maximum absolute component difference is
0.2198467255, CPU SHA-256 is
`baecf77627380f36f75a69c4454b064d886133f04255c5e5b4d3f24f00e7c4b8`,
and GPU SHA-256 is the value above. Therefore the GPU path is a changed vector
runtime, not an execution-only speedup.

## 4. Claims and anchors

The BEAM arm names from Amendment 001 change to:

- A0 `CC80_QWEN_GPU_COMMON`;
- C0 `STATIC_ASPECT_QWEN_GPU_COMMON`; and
- T1 `PARENT_OPPORTUNITY_ASPECT_QWEN_GPU_COMMON`.

They compare the registered architectures under one shared GPU vector runtime.
They are not byte-identical HH-003 payload reproductions and cannot establish a
direct deployed CPU operating-point comparison.

Before full BEAM context construction:

1. tokenize every exact episode and question with the loaded Qwen tokenizer and
   prove each fits 32,768 without truncation;
2. reproduce the committed GPU sentinel and longest-vector SHA-256 values;
3. reopen the cache read-only and reproduce every cached vector digest without
   loading a second model;
4. satisfy the pure-function CC80, static-ASPECT, packing, rendering, recency
   and TC-014 opportunity anchors from Amendment 001; and
5. run a shuffled question order and reproduce every completed payload digest.

The original HH-003 CPU payload anchors remain historical controls and are not
claimed by this amended run.

## 5. Runtime checkpoint

After local tests and the two registered GPU vector anchors pass, launch the
remaining cache population as a detached, resumable process. Record PID,
secret-free command, model/runtime hashes, progress, logs, failure sentinel,
GPU utilization samples and cache integrity under the runtime artifact
directory. The agent stops polling after launch health is established.

No mixed CPU/GPU cache, fallback truncation, partial offload, multi-window
pooling, API embedding, model sweep or parameter tuning is permitted.
