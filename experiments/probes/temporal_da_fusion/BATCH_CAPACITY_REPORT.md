# GPU reader concurrency capacity

Engineering diagnostic complete, 2026-09-07. Plan commit `ece1f77d`; logging repair `bc234073`; executed code `a2a26e56`; input gate `9a126730`; raw capture `748f2a38`. User explicitly authorized batching in place of the standing serial default for this probe. No study scores changed and no LoCoMo answers generated.

**Recommend nine concurrent requests at 32768 tokens per slot.** Nine passed two simultaneous long-input waves with minimum free dedicated VRAM 2282 MiB. Ten loaded successfully but left only938 MiB, below the predeclared1536 MiB reserve, and was stopped before stress. Ten is an observed startup allocation, not an OOM or a validated operating configuration; this does not establish an absolute hardware maximum with zero reserve.

## Configuration and results

RTX5090,32607 MiB physical VRAM reported by nvidia-smi, driver610.74, Windows WDDM. Current runtime reports a smaller available total; free-memory decisions use its measured free field, not subtraction from the physical total. Qwen3.8-27B UD-Q4_K_XL and llama-server b10360-90e6a9131 are stream-hash verified against the carried E pins. All66/66 layers offloaded, model GPU buffer16128.01 MiB; q8_0 KV1088 MiB per slot. Actual allocation grows approximately1366 MiB per additional slot, including other state. Native thinking off, budget0, explicit false template switch, seed5005, no speculative decoding, cachefalse. Short native arithmetic response reproduced exactly twice at every stress-tested concurrency.

| Concurrent slots | Minimum free MiB under load | Seconds per wave (two waves) |
|---|---:|---|
|1|13210|10.82 /10.82|
|2|11844|21.10 /21.16|
|3|10476|31.35 /31.46|
|4|9110|41.58 /42.21|
|5|7744|51.89 /52.88|
|6|6380|62.22 /62.95|
|7|5014|72.48 /73.64|
|8|3648|82.85 /85.51|
|9|2282|92.92 /97.83|
|10|Not stressed;938 idle|Stopped below reserve|

All90 stress calls consumed27920 uncached input tokens and produced exactly64 forced output tokens without context truncation. There were18 short calibration calls in addition. `ignore_eos=true` deliberately makes stress terminate at its64-token limit; these are not incomplete study answers. Prompt hashes are distinct by slot and repeat exactly across waves. Independent log audit verifies overlapping active slot lifetimes1–9 and all slots released. Allocated context remains32768 per slot throughout, rather than being divided down as concurrency rises. Logical token batch2048 and physical microbatch512 were retained; neither is the parallel-request count.

At nine slots use `--parallel 9 --ctx-size 294912`, keeping the carried model, q8_0 K/V, native-off flags and continuous batching. The future client must maintain up to nine independent in-flight requests, persist each request/response separately, and stop scheduling on uncertain failures. A larger context per request requires capacity revalidation; never shrink retrieval to preserve this batch count.

## Interpretation and limitations

This establishes short-load capacity, not a ninefold speedup. Aggregate throughput was0.0924 requests/s serial and0.0944 at nine, roughly2.1% higher in this synthetic workload, without a significance claim. Long-input prefill dominates and interrupts early-slot decoding while later prompts are processed. Shorter real LoCoMo prompts and longer judge outputs may behave differently; estimate their throughput in calibration. No token-batch/microbatch tuning was performed.

The synthetic stress input is a token-array capacity fixture with a distinct prefix and an explicit closed-thinking assistant suffix, not a scored natural dialogue or byte-identical HH001 reader prompt. Short calibration uses the valid native chat template. The stress fixture does not certify reader correctness or serial/batched output identity. Only64 output tokens were decoded, not sustained4096-token generation. The full32768-slot allocation leaves room for the planned4096 output allowance, but long-duration endurance and full LoCoMo prompt fit remain registration gates. WDDM telemetry was sampled approximately every half-second; desktop usage can change. No CPU offload was observed; sampled VRAM alone is not a proof against all driver paging behavior.

PF1 pins/input gate, PF2 allocation logs/properties, PF3 missing-gate fixture/commit order, PF4 headroom boundary fixtures, PF5 prompt digests, PF6 carried launch option identity, PF7 distinct uncached slots/overlap audit, PF8 two near-window waves, PF9 limitations above and PF10 no correctness verdict are recorded in raw artifacts and `batch_capacity_audit.json`. The initial attempt stopped before inference because verbosity3 omitted the offload log; preserved separately and repaired with verbosity5. All owned servers stopped. No active inference remains.

Artifacts: `batch_capacity_artifacts/` initial stopped attempt; `batch_capacity_artifacts_retry/` complete captures and logs; `batch_capacity_audit.json` independent checks; `batch_capacity.py` runner; `batch_capacity_audit.py` audit.
