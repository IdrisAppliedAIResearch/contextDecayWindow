# NF-008 Design Brief - Live Item-Level Reader Validation

**Status:** `DESIGN ONLY - NOT REGISTERED - NOT EXECUTABLE`  
**Prepared:** August 13, 2026  
**Predecessor:** NF-006 availability result and NF-007 coverage-family stop  
**Authorization boundary:** documentation preparation only; no implementation,
capture, generation, scoring, or inference is authorized

## Decision question

Does the NF-006 own-statement context that contains 14/17 Q11 facts cause a
reader to use more correct Q11 facts than the episode context that contains
12/17, under an otherwise identical prompt and runtime?

This is a reader study, not another retrieval study. It changes no memory
component and does not optimize Q11 availability. The internal corpus and probe
are exhausted, so the maximum evidential status remains `CHARACTERIZED`; the
value is causal interpretation of two already frozen contexts, not fresh-corpus
confirmation.

## Why this is next

NF-006 reaches its registered 14/17 availability bar with zero targeted losses.
NF-007 then closes the carried count-of-cluster-entry coverage family: sealed T1
already touches all 16 clusters, while the art-majority regions are sampled at
5.4% versus 33.0% for cluster 0. BA-001, DR-002, and TA-001 independently show
that art is stored but not broadly similar to Q11, and that adjacency can reach
it only by trading away targeted safety.

The remaining product-relevant uncertainty is therefore downstream: whether a
two-item availability gain changes what the reader says. The 3.0-point band on
the 13-point rubric cannot resolve that contrast. Item-level use over 17 frozen
facts is a different count instrument. Study 007 demonstrated the measurement
shape by finding 10/10 available facts used with no invention; Study 011
Amendment 001 supplies the established minimum of five identical replicates.

## Frozen candidate comparison

The eventual registration may compare only these already committed NF-006 Q11
arms at probe turn 120:

| Arm | Frozen mechanism | Availability | Purpose |
|---|---|---:|---|
| `C0_EPISODE` | episode ranking and episode packing | 12/17 | reader control |
| `T1_OWN_STATEMENT` | own-statement ranking and statement packing | 14/17 | reader treatment |

The selection seal, order, exact character costs, and payload digests are in
`nf_006/artifacts/g6_g7_selection_seal.json`; availability is in
`nf_006/artifacts/g8_g9_measurement.json`. A registration must reconstruct and
hash the exact rendered prompts before inference. It may not rerank, repack,
change the budget, add adjacency, or alter either retrieval block.

## Proposed measurement shape

This section is preparation, not a lock.

- Generate one Q11 answer from each frozen arm in at least five identical
  replicates, carrying Study 011 Amendment 001's minimum replication count.
- Score a 17-bit correct-fact-use vector for every answer, outside reasoning
  blocks, with a rationale for every bit.
- Report correct delivered facts used, delivered facts omitted, correct facts
  stated without delivery, contradictions, and inventions separately.
- Preserve each answer and item vector before unsealing arm labels or mechanism
  traces. Pair comparisons by registered replicate schedule, not by choosing a
  favorable run.
- Keep the 13-point rubric secondary or omit it. Its measured 3.0-point band is
  not the primary instrument for a two-item availability contrast.

Correctness and support are separate axes. A model can state a correct item from
pretraining without using the delivered evidence, or receive an item and omit
it. The registration must define both before any answer exists.

## Claims available and unavailable

A positive registered result could support: under the frozen reader and prompt,
the NF-006 context composition increases item-level fact use. A null could show
that the two-item availability gain does not move this reader instrument at the
registered replication depth.

Neither branch establishes a general reader effect, official benchmark score,
fresh-corpus confirmation, production adoption, or the value of an untested
art-recovery mechanism. Cross-run majority voting or best-of-five selection is
not an available outcome unless prospectively registered, and neither should be
used for the primary comparison.

## Explicitly deferred alternative

Statement-grain radius-1 adjacency is a grounded availability successor because
TA-001 recovered art 0/4 to 4/4 and whole-episode collateral caused its targeted
failure. It is not part of NF-008. Adding it would change a retrieval component,
return to an exhausted availability endpoint, and require its own Part 1 and
registration on a separate branch.
