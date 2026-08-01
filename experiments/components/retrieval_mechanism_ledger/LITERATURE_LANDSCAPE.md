# Long-Conversation Memory Literature Landscape

**Recovered repository edition:** 2026-07-31
**Decision scope:** Program positioning, benchmark adoption, and mechanism
dispositions
**Companion mechanism scan:** `LITERATURE_SCAN.md`

## 1. Evidence Boundary

This program studies whether a model can sustain a long conversation by
rebuilding a bounded context from stored episodes. Its evidence is a sequence
of pre-registered mechanism studies and offline component tests on one scripted
conversation lineage. Literature establishes prior art and external-validity
requirements; it does not override registered criteria or turn exploratory
results into comparative benchmarks.

This file recovers the carried landscape decisions that were referenced but
not committed. `LITERATURE_SCAN.md` is the later mechanism-specific scan. Where
the two overlap, this file owns program positioning and benchmark adoption,
while `LITERATURE_SCAN.md` owns candidate-mechanism prior art.

## 2. HippoRAG Disposition

[HippoRAG](https://proceedings.neurips.cc/paper_files/paper/2024/hash/6ddc001d07ca4f319af96a3024f6dbd1-Abstract-Conference.html)
combines an LLM-built knowledge graph with Personalized PageRank for
associative retrieval. It is relevant prior art for graph-mediated,
entity-centered memory, but it is not a drop-in comparator for this program:
HippoRAG was evaluated primarily on multi-hop question answering, whereas this
program tests long-conversation retention, targeted recall, and enumeration
under an enforced context budget.

The memory track's six hardest formation-blind facts contained rare technical
vocabulary for which the registered spaCy entity extraction returned zero
entities. Density and IDF episode ranking also failed them. Widened raw STM
made all six available and the model used five correctly. The supported
differentiation claim is therefore narrow: preserving raw episodes avoids an
entity-extraction gate that demonstrably erased these spans in this program.
This is not a head-to-head HippoRAG result, and it does not prove HippoRAG's
LLM-based graph builder would miss the same content.

**Disposition:** Do not adopt an entity-only index as the repair for F4.
Preserve the raw-delivery result as evidence for lossless capture and as a
clear distinction from entity-gated memory formation.

## 3. Benchmark Adoption

[LoCoMo](https://aclanthology.org/2024.acl-long.747/) evaluates question
answering, event summarization, and multimodal dialogue generation over
conversations averaging hundreds of turns and many sessions.
[LongMemEval](https://arxiv.org/abs/2410.10813) evaluates information
extraction, multi-session reasoning, temporal reasoning, knowledge updates, and
abstention over scalable chat histories.

The repository's scripted probes are valuable for causal diagnosis because
plant locations, retrieval traces, and failure surfaces are known. They are
not sufficient for a field-level claim of long-term conversational-memory
quality.

**Adoption decision:** Retain the scripted lineage for mechanism diagnosis.
Require LoCoMo and LongMemEval evaluation, with their native task definitions
and no tuning on test questions, before claiming general long-conversation
memory performance or comparison with external systems.

## 4. Mechanism Landscape

The later `LITERATURE_SCAN.md` closes three searches:

- diversity-aware selection through MMR and submodular coverage;
- query decomposition and multi-vector retrieval, including ColBERT and
  conversational query reformulation;
- active or mid-generation retrieval, including FLARE, IRCoT, and Self-RAG.

Those sources do not retroactively alter the ledger. MMR and facility-location
selection remain real untested alternatives for F1. Learned reformulation and
active retrieval add training, inference, or decode-loop coupling that violates
the current one-shot `store.context(query, budget)` contract. ColBERT-style
late interaction remains prior art for E003, but the ledger did not authorize
its storage and budget costs.

The E001 attention diagnostic is also reconciled with
[Wu et al.](https://arxiv.org/abs/2404.15574), who report retrieval heads as
sparse, under 5% of attention heads in the models studied. E001 selected
266/384 full-attention heads (69.3%), so its detector was not discriminating by
that external reference. The best cue came from the all-head arm. Its
0.210318044 cosine is the best found across 335 cues, not a ceiling on sharper
head selection.

## 5. Positioning Call

Position the paper as a mechanism and measurement study of bounded
long-conversation memory, not as a new state-of-the-art memory architecture.
The coherent contribution is the failure record:

- write-time formation repeatedly selected surrogates for importance;
- query-time ranking and packing failed breadth and buried identity;
- nominal character budgets concealed material serialized-cost differences;
- exact accounting changed the apparent strength of prior results;
- raw delivery was the strongest positive mechanism on the hardest spans.

The retrieval ledger sharpens that position. E002 failed its locked hurdle but
improved its own exact-budget baseline from 6/17 to 10/17. E001 improved the Q4
cue from 0.120421976 to 0.210318044 but remained far below K=0.48. The paper
should report both effect sizes and both binding criteria, avoiding the false
choice between calling a mechanism solved and calling it useless.

## 6. Claims The Literature Does Not Authorize

- No claim that this repository outperforms HippoRAG, LoCoMo systems, or
  LongMemEval systems.
- No claim that zero spaCy entities predicts failure for every entity-centric
  graph builder.
- No claim that E001's best cue is a mathematical upper bound.
- No claim that E002 validates fixed-width segmentation as a deployable
  breadth solution.
- No claim of benchmark generalization before LoCoMo and LongMemEval adoption.

## 7. Carried Decisions Reconciled With The Mechanism Scan

| Item | Landscape decision | `LITERATURE_SCAN.md` reconciliation |
|---|---|---|
| HippoRAG / entity-centric graph | Do not adopt an entity-only F4 repair; preserve raw capture | No conflict; the mechanism scan does not promote an entity index |
| LoCoMo | Adopt before external long-conversation claims | Outside the mechanism scan's narrower scope |
| LongMemEval | Adopt before external memory-system claims | Outside the mechanism scan's narrower scope |
| Diversity-aware selection | Relevant untested F1 alternative | Scan complete; no post-hoc substitution for E002 |
| Query decomposition / late interaction | Prior art, costs must be measured prospectively | Scan complete; E003 remains unauthorized |
| Active retrieval | Revisit only if the product contract becomes agentic | Scan complete; current contract rejection stands |
| Attention-head term selection | Diagnostic evidence only | Scan complete; 69.3% selection is non-sparse relative to Wu et al. |
| Paper framing | Negative-result and measurement paper with a raw-delivery positive | Mechanism scan supplies context, not a competing framing |

There is no remaining unresolved Section 7 reference. New literature should be
added to the mechanism scan first and then reflected here only if it changes a
program-level adoption or positioning decision.
