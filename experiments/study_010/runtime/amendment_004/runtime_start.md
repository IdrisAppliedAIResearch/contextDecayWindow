# Study 010 Amendment 004 Runtime Start

**Evidence status:** post-stop exploratory
**Execution commit before runtime record:** `f71c7ad`
**Started:** July 27, 2026
**PID:** `18180`
**Server build:** `b9294-0f3cb3fc8`
**Endpoint:** `http://127.0.0.1:8080`

## Artifacts

| Artifact | SHA-256 |
|---|---|
| `C:\Users\muzaf\.unsloth\llama.cpp\build\bin\Release\llama-server.exe` | `3827a6b634a88073dc63b97edf6e0dc575d33ecf58268803ece0ed23216095fa` |
| `C:\Users\muzaf\.cache\huggingface\hub\models--unsloth--Qwen3.6-27B-MTP-GGUF\snapshots\5cb35eb3dcbf52dbce5f87dbc64df6aaffadcace\Qwen3.6-27B-UD-Q6_K_XL.gguf` | `f3b4a622e06e8ade06ec5c0eb9b40ed7c9bd707b5fada46c0215f4ab4a6bc32b` |

## Launch Command

```text
llama-server.exe
  -m C:\Users\muzaf\.cache\huggingface\hub\models--unsloth--Qwen3.6-27B-MTP-GGUF\snapshots\5cb35eb3dcbf52dbce5f87dbc64df6aaffadcace\Qwen3.6-27B-UD-Q6_K_XL.gguf
  --host 127.0.0.1 --port 8080
  --ctx-size 50000 --parallel 1
  --cache-type-k q8_0 --cache-type-v q8_0
  --flash-attn on --jinja --metrics
  --temp 1 --top-p 0.95 --top-k 20 --min-p 0.0
  --presence-penalty 0.0 --repeat-penalty 1.0
  --seed 5005
```

## Guarded Properties

The server reported model alias `Qwen3.6-27B-UD-Q6_K_XL.gguf`,
`total_slots=1`, `n_ctx=50176`, `seed=5005`, and
`speculative.types=none`. Standard output and error are retained beside this
record as `server.stdout.log` and `server.stderr.log`.
