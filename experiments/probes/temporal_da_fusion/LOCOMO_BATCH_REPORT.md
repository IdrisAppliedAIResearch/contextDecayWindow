# LoCoMo lightweight batching result

Plan b483b398; implementation 2f703973; inputs 7f5e2cde; live calibration/fit
gates e7de3538 and 06806c0a; raw outputs 1e29e7be. Timing diagnostic only.

The same nine historical LV009 PAIRWISE questions took **37.44 seconds serially
and 38.20 seconds at concurrency nine**. Batched throughput was 0.9802 times
serial, approximately 2% lower. No speed benefit was observed in this sample.
First serial question took 3.94 seconds; the complete concurrent wave took38.20.
Startup and calibration are excluded. Timing includes request/persistence and
up to roughly0.2 seconds of completion polling per arm.

Both arms processed103,942 input tokens (11,191–11,952 per question), with
native thinking OFF, seed5005, cap4096 and32,768 context per slot. Outputs were
172 tokens serial versus234 batched;8/9 answers were byte-identical. No accuracy
scoring was performed. Different answer lengths limit fixed-work comparisons.

The committed audit verifies identical prompts and comparison keys, zero prompt
cache reuse, EOS/no truncation on all18 answers, and actual peak active slots1/9.
Minimum free VRAM was13,208/2,282 MiB respectively; all66 model layers were on GPU.
Both owned servers stopped. Missing-gate rejection ran before network calls;
short arithmetic calibration repeated identically in both arms.

This is one fixed-order wave of nine questions selected without answer labels,
using existing retrieval prompts, not the new uncapped timeline. It establishes
that fitting nine requests does not itself yield a throughput improvement here.
It does not establish the fastest batch size, endurance, accuracy equivalence,
or full-corpus timing. Keep capacity and speed claims separate in the LoCoMo
design; nine remains a capacity option, not a demonstrated speed optimization.

PF1–PF6 evidence: input_gate.json, gate_1.json, gate_9.json and audit.json under
locomo_batch_artifacts. PF7: no feedback/cache reuse. PF8–PF10: limitations above;
no efficacy bars, availability verdict or correctness claim. Historical payload
digests are checked before native wrapping, which is identical across arms.
