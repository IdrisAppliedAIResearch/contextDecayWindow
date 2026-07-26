# Study 007 — S7-T-005 Runtime and Determinism Verification

**Date:** July 25, 2026
**Status:** PASS
**Pre-registration:** `experiments/study_007/pre_registration.md` (commit `d920fd8`)
**Carried from:** `experiments/study_006/runtime/s6_003_runtime_verification.md`

## Accepted runtime

Every constant is identical to Study 006, which carried them from Study 005.
Verified against `/props` on the live server, not asserted from the launch
command.

| Parameter | Verified value | Study 006 |
|---|---|---|
| Inference artifact | `Qwen3.6-27B-UD-Q6_K_XL.gguf` | same |
| Model snapshot | `5cb35eb3dcbf52dbce5f87dbc64df6aaffadcace` | same |
| llama.cpp server | `b9294-0f3cb3fc8` | same |
| Endpoint | `http://127.0.0.1:8080/completion` | same |
| Context | 50,000 requested (`50,176` reported) | same |
| Server slots | 1 (`total_slots: 1`) | same |
| KV cache | Q8_0 K and V | same |
| Flash attention | enabled | same |
| RNG seed | 5005 | same |
| Sampling | temp 1.0, top-p 0.95, top-k 20, min-p 0.0 | same |
| Penalties | presence 0.0, repeat 1.0 | same |
| Speculative decoding | off; `/props` reports `speculative.types: none` | same |

Launch command, both phases and both arms — the pre-registered flag set verbatim:

```
llama-server.exe
  -m .../snapshots/5cb35eb3dcbf52dbce5f87dbc64df6aaffadcace/Qwen3.6-27B-UD-Q6_K_XL.gguf
  --host 127.0.0.1 --port 8080
  --ctx-size 50000 --parallel 1
  --cache-type-k q8_0 --cache-type-v q8_0
  --flash-attn on --jinja --metrics
  --temp 1 --top-p 0.95 --top-k 20 --min-p 0.0
  --presence-penalty 0.0 --repeat-penalty 1.0
  --seed 5005
```

Full server properties: `server_props.json`.

**Seed.** 5005, carried forward for the third consecutive study. The
pre-registration fixes the seed as "5005 unless changed and recorded"; it is not
changed.

## Embedding model

`embedding_verification.json`. Every field is **bit-identical** to Study 006:

| Field | Value | Matches 006 |
|---|---|---|
| Artifact SHA-256 | `06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439` | yes |
| Dimensions | 1024 | yes |
| Device | CPU (`n_gpu_layers=0`) | yes |
| Probe vector SHA-256 | `209cdf473e918ac7b5e801fa93bed1ffe97f1a5604f0ea4cd825cb498091bae2` | yes |
| L2 norm | 92.18827819824219 | yes |

The probe vector matching to the byte matters more here than in previous
studies: Study 007's diversity floor and similarity fill are both driven
entirely by cosine similarity in this embedding space. A silent embedding change
would move every selection.

## Speed gate

`speed_gate.json`. Gate is > 30 tok/s single-slot.

| Measure | Value |
|---|---:|
| Turns measured | 10 |
| Minimum | **36.44 tok/s** |
| Median | 45.51 tok/s |
| Maximum | 47.93 tok/s |

PASS — the slowest turn clears the gate.

## Determinism spot-check

`scripts/verify_study_007_determinism.py`, artifacts in
`determinism_prefix_001/`. Ten seeded turns, run twice against **fresh server
processes** (pid 9016 then 26548 — the harness refuses a shared pid).

| Check | Result |
|---|---|
| Within-study: prompts identical across lifecycles | 10/10 |
| Within-study: responses identical across lifecycles | 10/10 |
| **Cross-study: prompts identical to Study 006** | **10/10** |
| **Cross-study: responses identical to Study 006** | **10/10** |
| Distilled LTM empty throughout the prefix | asserted |

### Why the cross-study check is the load-bearing one

The ten-turn prefix runs before the first dream pass, so distilled LTM is empty
and **no Study 007 retrieval code executes** — the harness asserts the empty
store rather than assuming it. The prefix is therefore a pure measurement of
everything *upstream* of the change under test.

Reproducing Study 006's prompts and responses byte for byte establishes two
things a within-study A/B cannot:

1. The runtime is the same runtime — same weights, same sampler, same seeding
   behaviour — a day later and across three server lifecycles.
2. Study 007 has changed nothing upstream of LTM retrieval. Correction 1
   rewrote the script loader and `StudyRunner.__init__`, and this is the
   evidence that neither altered a single delivered byte.

A divergence would have been a stop condition, not a curiosity.

## Correction 1 in effect

The determinism runs are the first to execute with the post-decode digest
assertion armed. Both phases passed
`d8ba73fd02bfd41bec156904fb6a3328bbed3d0da8bff05e4667d2e450752f01` before
sending a single token.

`PYTHONUTF8=1` was set, as in Study 006, for continuity of the recorded
environment. It is **no longer load-bearing**:
`tests/test_script_loader_encoding.py` runs the loader under `-X utf8=0` with a
cp1252 locale and still obtains the pre-registered digest, and the same read
without an explicit encoding digests to `5eb93a82…`, which the assertion
rejects. Correctness now lives in the code.

## Context-ceiling monitor

Active. Peak context over the prefix was ~5,982 tokens, 12% of the 50,176
reported capacity. The alert threshold is 80%.

## Verdict

**PASS.** Runtime, embeddings, speed, and determinism all verified, with
byte-level continuity to Study 006. S7_001 is complete; implementation may
proceed.
