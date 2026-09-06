# Amendment 005 runtime lock

2026-09-06. Implements authorized design-only amendment **6603aca3** under original registration **2e047c41c80748b16f0e6df15dcc70ac54145598**. Selection was made without confirmation answer review or mechanism unsealing.

## Part 1 result

Eight fixed development prompts, two identical-seed passes per configuration (48 total unscored calls), all complete at EOS:

| Slots | Total seconds for 16 calls | Repeat byte identity | Identity with serial | Peak GPU memory, MiB |
|---|---:|---|---|---:|
| 1 | 65.1801 | 8/8 | 8/8 | 19,140 |
| 2 | 67.2060 | 8/8 | 7/8 | 20,510 |
| 4 | 67.6695 | 8/8 | 7/8 | 23,243 |

Serial responses used 3–4 output tokens. Each batched configuration produced 46 tokens on the first prompt, versus 3 serially; the other seven matched. Each configuration repeated itself exactly, but neither batched configuration passed cross-configuration identity or the >=10% speed gain criterion. GPU median utilization was 97% in all three; sample counts 32/33/34. These device counters and this small workload do not prove batching cannot help other workloads. Here prompt processing dominates very short decoding.

The native template's thinking-off assistant boundary contains a closed thinking segment, while thinking-on ends at an open segment. Both use actual chat role delimiters. The prior raw completion did not wrap the instruction in the native role template. This repair therefore changes the reader prompt interface as well as making thinking control explicit; it is not an isolated causal test of thinking.

## Frozen runtime

Select **one slot**, 32,768 context tokens, 16,384 output-token cap, cache_prompt=false. Use the same pinned Qwen3.8-27B model, executable and loaded library files as preserved in `artifacts/amendment005/verified_runtime_pins.json`. Use the launch command from `artifacts/amendment005/slots1/launch.json`, with a new PID and logs. Native server reasoning off, reasoning budget zero, template enable_thinking=false; apply-template then raw completion of the exact sealed rendered bytes. Preserve the carried prompt payload except its old trailing empty-think suffix. Sampler unchanged. No further tuning based on confirmation outputs.

This selected runtime applies identically to all four arms and five seeds. All answers are regenerated; neither stopped attempt contributes scores. Population, retrieval, references, aliases by full prompt+seed, logical IDs, agent-scoring protocol and statistical bars remain unchanged. All original artifacts remain immutable.

## Executed preflight evidence and remaining gates

`artifacts/amendment005/input_manifest.json`, per-slot prompt stores/schedules/templates, raw responses/results/GPU logs and `selection.json` provide PF1/PF2/PF5/PF6/PF8/PF9 runtime evidence. `verified_runtime_pins.json` verifies 16 runtime entries against the prior hashes. `restart_preflight.json` executes reachable selection/completion branches, capped-wave draining, uncertain-journal preservation and missing-input rejection before any model request (PF3/PF4). Original source regeneration and clean pinned controls run in the shared prerequisite check (PF6/PF7). No response writeback occurs. The full source/vector hash and every prompt's token fit are required in the subsequent committed input gate, followed by largest-prompt seeded calibration before measurement. The full reader-completeness and scoring gates remain binding (PF10).

The no-tag and replay checks are instrument checks, not evidence of answer correctness or absence of internal computation. No confirmation mechanism verdict is available. All results here are unscored runtime characterization on previously exposed development prompts.
