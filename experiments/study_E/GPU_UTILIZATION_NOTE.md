# Read-only GPU utilization probe

2026-09-06, requested by the user during the authorized cap repair. Thirty NVML samples at two-second intervals, with no additional inference requests, are preserved in `artifacts/confirmation/continuation004/gpu_telemetry.json`.

The RTX5090 used20,389–20,392MiB (about19.9GiB) of VRAM. Median GPU utilization was97%, range93–98%; median memory-controller utilization64%; median power507.225W. The earlier idle snapshot reported11,812MiB free, about11.5GiB. This is one decoding interval, not a throughput benchmark or a general utilization guarantee.

There is VRAM headroom worth testing for batching, while the single-request decoder is already active. These counters alone cannot establish whether batching improves total throughput or preserves answers. A controlled batching benchmark should measure total tokens/second, per-request latency, memory and seeded answer identity. The registered scored run remains single-slot; changing it would require a separate runtime amendment. No batching or thinking-mode change was performed for this probe.
