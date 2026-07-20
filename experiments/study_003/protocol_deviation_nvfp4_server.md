# Study 003 — Protocol Deviation: NVFP4 Server Inference

**Recorded:** July 2026, before the Study 003 full run.

The locked pre-registration specifies Qwen3.6 27B Q6_K via an in-process llama.cpp provider. The local Q6_K artifact is unavailable. Study 003 will instead use the locally served `Unsloth-Qwen3.6-27B-NVFP4-A.gguf` model through llama.cpp at `http://127.0.0.1:8000`, with a 262,144-token context.

This changes quantization and serving transport, but retains the Qwen3.6 27B model family, local llama.cpp runtime, hardware scope, script, rubric, and 1,024-token response budget. Results must therefore be interpreted as conditional on NVFP4 server inference and are not a direct same-quantization replication of Study 002.

The server adapter uses llama.cpp's `/completion` endpoint, disables visible reasoning output, and prefills a closed `<think>` block so final answers and rule-detection tags fit within the response budget.

## Pre-run checks completed under this configuration

- Five-turn rule-pinning check: Turn 1 rule detected and stored; turns 2–5 included one pinned rule in constructed context.
- Twenty-turn iterative ablation: consolidation recorded at episodes 10 and 20. Topic count was 7 after turn 10 and 9 after turn 20.
- The first 20 turns contain only the civil-engineering topic, so cross-domain merge safety remains to be evaluated in the mandatory 35-turn ablation before the full run.
