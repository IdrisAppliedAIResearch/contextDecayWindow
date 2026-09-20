# Read-only GPU utilization probe

2026-09-06, requested by the user during the authorized cap repair. Thirty NVML samples at two-second intervals, with no additional inference requests, are preserved in `artifacts/confirmation/continuation004/gpu_telemetry.json`.

The RTX5090 used20,389–20,392MiB (about19.9GiB) of VRAM. Median GPU utilization was97%, range93–98%; median memory-controller utilization64%; median power507.225W. The earlier idle snapshot reported11,812MiB free, about11.5GiB. This is one decoding interval, not a throughput benchmark or a general utilization guarantee.

There is VRAM headroom worth testing for batching, while the single-request decoder is already active. These counters alone cannot establish whether batching improves total throughput or preserves answers. A controlled batching benchmark should measure total tokens/second, per-request latency, memory and seeded answer identity. The registered scored run remains single-slot; changing it would require a separate runtime amendment. No batching or thinking-mode change was performed for this probe.
# Batching follow-up — 2026-09-06

The authorized Amendment005 benchmark is complete. On the same eight development prompts repeated twice, serial/two/four-slot execution took65.18/67.21/67.67 seconds. Peak device VRAM was19,140/20,510/23,243 MiB; median GPU utilization97% in every configuration. All48 calls reached EOS and each configuration repeated itself exactly, but both batched configurations changed one response relative to serial. Serial was selected. See `amendments/AMENDMENT_005_RUNTIME_LOCK.md` and `artifacts/amendment005/selection.json`.

This applies to the new native thinking-off interface and the measured short-answer workload. It is not a general rejection of batching or a controlled attribution of the improvement to thinking alone.

---
