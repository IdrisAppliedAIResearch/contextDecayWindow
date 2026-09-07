# Lightweight LoCoMo batching diagnostic

User authorized concurrency 1 versus 9, September 7, 2026. Timing only;
no accuracy scoring or full LoCoMo study. Use the first nine category 1–4
PAIRWISE prompts in committed LV009 prompt-file order, identically in both
arms. Historical retrieval, not the pending relevance-timeline implementation.
Run nine sequential calls on a one-slot server, then the same nine concurrently
on a nine-slot server. Exclude model loading and short calibration from timing.
Pinned Qwen reader, native thinking OFF, seed 5005, cap 4096, cache_prompt false,
32768 context per slot; all other launch/sampling settings from capacity probe.
No retries or tuning. Persist raw responses before reporting time, input/output
tokens, throughput ratio and answer identity (not correctness).

## Preflight

Part 1 uses the committed capacity exploration: nine overlapping requests fit;
synthetic prefill dominated. Here record all nine real prompt lengths and outputs.
PF1: hash source, code and runtime pins; require committed inputs.
PF2: assert slots, full GPU offload, native OFF launch/template/live calibration.
PF3: missing-gate negative fixture; committed input gate before server calls,
and committed fit/calibration gate before measured calls for each arm.
PF4: no efficacy bar; exact context fit and prior 1536 MiB reserve enforced.
PF5: same prompt content hashes and occurrence keys across arms.
PF6: retain exact historical reader text; native wrapping identical across arms.
PF7: independent calls, no retrieval feedback; disable prompt cache.
PF8: nine questions once per arm measures immediate timing, not endurance.
PF9: fixed order, tiny sample, variable decode length and historical retrieval
limit inference; memory sampling cannot exclude every transient spike.
PF10: live timing only; no availability or reader-correctness verdict.
