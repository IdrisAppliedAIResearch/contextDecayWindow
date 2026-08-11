# SUP-001 Amendment 001 - Probe Store Isolation

**Date:** 2026-08-11  
**Authorization:** The user authorized the SUP-001 research arc end to end.  
**Trigger:** Implementation-blocking contradiction discovered after the 35-turn
run lock and before any ablation vectors or decoding.

## Evidence

`SUP_001_ABLATION_RUN_LOCK.md` requires both:

1. a retained read-only cache of solo-call embeddings; and
2. appending model-generated probe answers to retrieval memory so later probes
   can retrieve them.

Probe answer text does not exist before decoding and therefore cannot be in the
pre-run read-only cache. Embedding it during a run would require unsealed model
calls and would create different later candidate identities in C0 and T1 when
their answers differ. That violates the same lock's requirement that the arms
hold candidate identities and vectors fixed.

## Change

The 35 scripted user turns and all nine reader answers remain the complete
ablation sequence and are logged in order. Retrieval memory is frozen after
the 26 pre-probe scripted exchanges. Probe questions and generated answers do
not become retrieval candidates for later probes.

The retained cache therefore contains exactly 26 episode-pair vectors and nine
query vectors, all populated before inference and reopened read-only in both
arms. Every probe still observes all planted facts and both update waves.

## Rationale

This is the smallest repair that satisfies both determinism and arm isolation.
It removes answer-to-later-answer contamination rather than introducing a new
component. The ablation tests whether the reader uses C0 versus T1 delivery,
not whether its own earlier answers become memories.

## Exclusions

- No script text, answer, prompt, model, seed, top-k, budget, criterion,
  threshold, or disposition changes.
- No outcome has been observed; no ablation vector or model call has occurred.
- The study still contains exactly 35 user turns and nine scored reader calls.
- This amendment does not authorize a 120-turn or production run.

