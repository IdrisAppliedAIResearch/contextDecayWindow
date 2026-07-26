# Study 006 — S6-T-003 Runtime and Determinism Verification

**Date:** July 25, 2026
**Status:** PASS
**Pre-registration SHA:** `5def302`
**Verified implementation SHA:** `ef7c93b272c6040592302793ed1657a890b2da0d`
**Carried from:** `experiments/study_005/runtime/s5_001_runtime_verification.md`

## Accepted runtime

| Parameter | Verified value | Study 005 |
|---|---|---|
| Inference artifact | `Qwen3.6-27B-UD-Q6_K_XL.gguf` | same |
| Model snapshot | `5cb35eb3dcbf52dbce5f87dbc64df6aaffadcace` | same |
| llama.cpp server | `b9294-0f3cb3fc8` | build 9294 (`0f3cb3fc8`) — same |
| Endpoint | `http://127.0.0.1:8080/completion` | same |
| Context | 50,000 requested (`50,176` reported) | same |
| Server slots | 1 (`total_slots: 1`) | same |
| GPU | NVIDIA GeForce RTX 5090, 32,607 MiB, driver 610.74 | same |
| Flash attention | enabled | same |
| KV cache | Q8_0 K and V | same |
| RNG seed | 5005 | same |
| Sampling | temp 1.0, top-p 0.95, top-k 20, min-p 0.0 | same |
| Penalties | presence 0.0, repeat 1.0 | same |
| Speculative decoding | off; `/props` reported `speculative.types: none` | same |

The server launch used for both determinism phases:

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

This is the pre-registered flag set verbatim. No speculative-decoding flag is present, and
`/props` independently confirms none is configured. Full server properties are recorded in
`server_props.json`.

### Seed selection

The pre-registration fixes the seed as "recorded in run header; identical across arms" without
naming a value. **5005 is carried forward from Study 005.** The runtime table is headed "carried
from Study 005"; the Bar 3 baseline is a re-run of Study 005 code; and the determinism harness
`scripts/verify_study_005_determinism.py` already records 5005. Reusing it holds every runtime
constant fixed and introduces no unregistered parameter.

## Binding environment requirement — `PYTHONUTF8=1`

**Every Study 006 process — both arms, replay, ablation, and controls — must run with
`PYTHONUTF8=1`.**

`src/study/script_loader.py:5` opens the script with `open(path, "r")` and no `encoding`
argument. It is the only unencoded `open()` in the codebase; every other call site passes
`encoding="utf-8"`. Under the Windows default locale (cp1252) the UTF-8 script is mis-decoded,
and the em dash `—` (U+2014, `e2 80 94`) reaches the model as `â€”`
(`c3 a2 e2 82 ac e2 80 9d`). The script text is unaffected on disk; the corruption is introduced
at load time.

This was found during this task: an initial determinism run passed its own A/B gate while
feeding the model corrupted text, and was detected only by comparing against Study 005's
preserved prompt hashes. The failed run is retained at
`runtime/determinism_prefix_000_mojibake_cp1252/` rather than discarded.

Study 005's constructed prompts contain the correct em dash, so its runs had UTF-8 mode active;
the defect was latent, not introduced by Study 006. **No source change was made.** The Bar 3
control runs unmodified Study 005 code from a separate worktree and would not receive a fix to
this repository's loader, so a source patch would leave the two arms running different loader
code — a difference beyond the selection policy. The environment variable is therefore the
correct control, and it is recorded here as part of the accepted runtime. Making the loader
encoding-explicit is filed as post-study work.

## Script integrity

| Check | Value |
|---|---|
| Committed blob SHA-256 | `d8ba73fd02bfd41bec156904fb6a3328bbed3d0da8bff05e4667d2e450752f01` |
| Study 005 recorded hash | `d8ba73fd02bfd41bec156904fb6a3328bbed3d0da8bff05e4667d2e450752f01` |
| Match | **yes** |
| Turns | 121 |

**The script is unchanged from Study 005.** One caveat governs how the hash must be computed:
this clone has `core.autocrlf=true`, so the working-tree file carries 495 CRLF line endings and
hashes to `8015c8eb89838c6aae4fd342af06ddb13cfd07f64dcdfa750ade54e375c4dd43`. All 495 carriage
returns are pretty-print whitespace between JSON tokens; **no CR occurs inside any string value**,
the parsed objects are identical, and the canonical serialization hashes to
`66e845ae80bb7b7848db51549e9a85ea50b4ee2efe220ddde9ffe9e00c917fb1`.

The pre-registration requires the run header's script hash to be "asserted equal to the Study 005
script hash." That assertion must be computed over **LF-normalized (committed-blob) bytes**, not
raw working-tree bytes, or it will fail spuriously on any Windows checkout. Recorded here so the
S6-T-016 and S6-T-017 launchers implement it correctly.

## Context speed gate

200 tokens generated from a fixed prompt at seed 5005, `cache_prompt: false`.

| Measure | Value |
|---|---|
| Tokens predicted | 200 |
| Generation speed | **49.207 tok/s** |
| Predicted time | 4,064.434 ms |
| Floor | 30 tok/s |
| Result | **PASS** |

Study 005 measured 45.771 tok/s at the same context size. The prompt and response hashes are in
`speed_gate.json`. Study 005's benchmark prompt was not preserved (`benchmark_*/` is ignored and
only server logs survive), so its `6c1c9f03…` response hash is **not reproducible** and no
cross-study hash comparison is claimed for this gate. Cross-study continuity is instead
established by the determinism prefix below, which is a stronger check.

## Determinism gate

The same ten-turn Study 005 prefix was run in two independent runner and server lifecycles.

| Check | Result |
|---|---|
| Server PIDs | 24132, 16672 (distinct) |
| Constructed prompts | **10/10 byte-identical** |
| Assistant responses | **10/10 byte-identical** |
| Dream events through turn 10 | 0 in both phases |
| Distilled records through turn 10 | 0 in both phases |
| Peak estimated context | 5,982 tokens (11.96% of capacity) |
| 80% context ceiling | not approached; strict monitoring active |
| Gate | **PASS** |

### Cross-study reproduction (beyond the pre-registered requirement)

Both phases were additionally compared against Study 005's accepted prefix
(`experiments/study_005/runtime/determinism_prefix_003/`):

| Check | Result |
|---|---|
| Prompts identical to Study 005 | **10/10** |
| Responses identical to Study 005 | **10/10** |
| Peak estimated context | 5,982 — identical to Study 005 |

The Study 006 runtime reproduces Study 005's seeded prefix exactly, byte for byte, three days
later across separate server processes. This is stronger evidence than the pre-registration
requires (which asks only for self-consistency across two phases) and confirms that model,
build, flags, seed, script, and code path are all unchanged. It is also what exposed the
encoding defect above.

Machine-readable per-turn hashes are in `determinism_report.json`. Raw prefix artifacts remain
local and ignored.

## Embedding verification

| Parameter | Verified value |
|---|---|
| Artifact | `Qwen3-Embedding-0.6B-Q8_0.gguf` |
| Artifact SHA-256 | `06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439` |
| Artifact bytes | 639,150,592 |
| Device | CPU (`n_gpu_layers=0`) |
| Dimensions | 1,024 |
| Output type | float32 |
| Finite-value check | pass |
| Probe vector SHA-256 | `209cdf473e918ac7b5e801fa93bed1ffe97f1a5604f0ea4cd825cb498091bae2` |

Studies 004 and 005 recorded a verification-vector hash but did not preserve the probe text, so
their `d3860b2d…` value is **not reproducible** and no cross-study vector comparison is claimed.
The artifact file hash is recorded here instead — it is checkout-independent and establishes
continuity forward. Dimensionality, dtype, device, and finiteness match Study 005. Full detail in
`embedding_verification.json`.

## Acceptance

| S6-T-003 criterion | Result |
|---|---|
| Flags + seed recorded | PASS |
| Server build hash recorded | PASS — `b9294-0f3cb3fc8` |
| Embedding model unchanged | PASS |
| Speed floor > 30 tok/s single-slot | PASS — 49.207 tok/s |
| Prefix replay identical | PASS — 10/10, and 10/10 vs Study 005 |
| Context-ceiling monitor active | PASS — strict monitoring, peak 11.96% |

**S6-T-003: PASS.** Sprint S6_001 is complete.
