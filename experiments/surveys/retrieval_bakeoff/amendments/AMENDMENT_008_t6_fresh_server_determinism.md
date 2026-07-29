# Amendment 008: Tier 6 Fresh-Server Determinism

**Date:** 2026-07-28  
**Status:** Binding before the second valid ablation and live inference  
**Applies to:** T6.1 runtime only

## Trigger And Evidence

The standing protocol requires a byte-identical seeded prefix rerun. The first
35-turn Tier 6 ablation began on a freshly launched llama.cpp server. A proposed
second run reused that same server process. Its turn-1 prompt was byte-identical
to the first run, but the generated answer differed:

- First run answer SHA-256:
  `265ddd79f2cb6f029fcf1d116780285731d228ceaa06e0646d0c5baecc2953f4`
- Reused-server answer SHA-256:
  `9675ab02bc05cf3fd2f8e73e5d406b4e4a14ed1a03eea5b79979d8d5877198ad`

No retrieval state, rule UUID, or prior generated content can explain a turn-1
difference. The server's seeded RNG stream is initialized at process start and
had already advanced through the first ablation. Reusing one process therefore
does not reproduce the registered initial seeded state.

The invalid shared-server attempt was stopped after 11 turns and retained under
`tier6/ablations/tier6_ablation_b`. It is not evidence.

## Change

Each valid independent generation run starts on a freshly launched server
process with the same registered binary, model, build, command, seed, one-slot
setting, context capacity, cache types, sampling parameters, and absence of
speculative decoding.

- Valid ablation A and valid ablation B must record different server PIDs.
- The verifier fails unless their prompts and answers are byte-identical for all
  35 turns.
- The 121-turn live run must use a third fresh server PID, different from both
  valid ablation PIDs.
- Model SHA-256, server build hash, and guarded properties must remain identical
  across all three processes.

The corrected second run uses a new run ID. The invalid shared-server attempt is
never substituted or counted.

## Rationale

This restores the registered meaning of "same seed": each independent run begins
from the same RNG state. It strengthens the determinism gate and changes no
retrieval, generation, scoring, or success criterion.

## Exclusions

This amendment does not change the selected N/K settings, character cap, script,
model, seed, sampler, number of turns, response budget, scoring protocol, or
score-before-logs order. It does not excuse any answer or prompt mismatch after
fresh-server restart.

## Authorization

The repository owner authorized necessary amendments for genuine execution
blockers. This amendment repairs a runtime contradiction discovered before live
inference and does not make any criterion easier.
