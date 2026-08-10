# E006 Part 2 S1 Prior-Art Scan

**Date:** August 10, 2026
**Design anchor:** `7fa09c62`
**Design source SHA-256:** `84A5EB5B29A01F4027B4E18411F8D0D99D41C7EEA3206E4ED329063D13B35DC1`
**Stage:** S1, before Preflight or mechanism implementation
**Source policy:** Primary papers and official proceedings; preprints are labelled
**Decision:** **PASS — NO REGISTERED KILL FOUND**

## 1. Registered Question

The S1 kill condition is a published negative result for chained retrieval on
conversational memory. The scan therefore distinguishes three questions:

1. Is retrieved-result cue updating established prior art?
2. Is query drift a demonstrated failure mode, and what mitigates it?
3. Has chained or iterative retrieval produced a published negative result on
   conversational or episodic memory?

The answer is **yes**, **yes**, and **not located**, respectively. The mechanism
continues to S2 under the registered rule. This is a bounded scan, not proof that
no negative result exists.

## 2. Classical Pseudo-Relevance Feedback

Pseudo-relevance feedback (PRF) is the direct information-retrieval ancestor:
retrieve an initial set, treat it as relevant, update the query representation,
and retrieve again. Rocchio-style vector updates and RM3-style interpolation
both retain an original-query contribution while incorporating feedback.

The registered hazard is real. Li et al. experimentally control first-stage
feedback quality and show that PRF effectiveness depends materially on that
quality across lexical and dense methods. Liang et al.'s SIGIR 2026 user study
finds PRF benefits 20.9% of tested queries while degrading user experience for
25.6%; avoiding harmful feedback produces the larger gain. These are negative
results for blind PRF on some ad-hoc queries, **not** negative results for
chained conversational-memory retrieval, so they do not fire S1's kill.

Mitigations supported by this literature are:

- anchor the update to the original query rather than replacing it;
- filter or selectively apply feedback when the first pass is unreliable;
- weight feedback documents or terms by estimated relevance;
- bound feedback depth and measure drift query by query.

Rev 2 registers the first and fourth (`W_Q > 0`, bounded `D`, measured cue
cosine). E-1 and PF7 test first-pass reachability and degeneration. Rev 2 does
not add a learned or model-based relevance filter, consistent with its single
component and zero-model-call constraints.

Primary sources:

- Li et al., SIGIR 2022, [How Does Feedback Signal Quality Impact Effectiveness
  of Pseudo Relevance Feedback for Passage Retrieval?](https://doi.org/10.1145/3477495.3531822)
- Liang et al., SIGIR 2026, [Auditing Query Drift: Do Users Actually Benefit
  from Pseudo-Relevance Feedback?](https://doi.org/10.1145/3805712.3809916)
- Lv et al., TREC 2009, [A Study of Term Proximity and Document Weighting
  Normalization in Pseudo Relevance Feedback](https://trec.nist.gov/pubs/trec18/papers/uiuc.MQ.pdf)

## 3. Iterative Retrieval in LLM Pipelines

The named adjacent systems all use feedback between retrieval steps, but they
couple retrieval to generation, reasoning, learned control, or critique:

- FLARE retrieves from a predicted future sentence when generation confidence
  is low and reports superior or competitive results on four long-form tasks.
- IRCoT alternates chain-of-thought steps with retrieval and reports gains on
  four multi-hop QA datasets.
- Iter-RetGen feeds generated responses back into retrieval and reports gains
  on multi-hop QA, fact verification, and commonsense reasoning.
- Self-RAG learns retrieval and critique tokens and reports gains across QA,
  reasoning, fact verification, and long-form generation.

They establish that iterative retrieval is not novel, but none tests Rev 2's
embedding-only retrieved-episode blend under a pure context-builder contract.

Primary sources:

- Jiang et al., EMNLP 2023, [FLARE](https://aclanthology.org/2023.emnlp-main.495/)
- Trivedi et al., ACL 2023, [IRCoT](https://aclanthology.org/2023.acl-long.557/)
- Shao et al., EMNLP Findings 2023, [Iter-RetGen](https://aclanthology.org/2023.findings-emnlp.620/)
- Asai et al., ICLR 2024, [Self-RAG](https://openreview.net/forum?id=hSyW5go0v8)

## 4. Retrieved-Context Models

Howard and Kahana's Temporal Context Model and Polyn, Norman, and Kahana's
Context Maintenance and Retrieval model formalize the cognitive mechanism Rev 2
uses as grounding: context cues an item, the item reinstates associated context,
and the blended context cues the next recall. These are models of human recall,
not evidence that this repository's retrieval mechanism works.

The scan did not locate a classical information-retrieval system implementing
Howard/Kahana-style retrieved context under that name. The 2026 conversational
memory work below is the direct systems prior art.

Primary sources:

- Howard and Kahana, 2002, [A Distributed Representation of Temporal
  Context](https://doi.org/10.1006/jmla.2001.1388)
- Polyn, Norman, and Kahana, 2009, [A Context Maintenance and Retrieval Model
  of Organizational Processes in Free Recall](https://doi.org/10.1037/a0014420)

## 5. Conversational and Episodic Memory

Four recent preprints directly test iterative retrieval over long-term dialogue
or personalized memory. All report positive aggregate outcomes; none is the
registered published negative.

| Work | Mechanism | Setting | Reported direction | Relation to Rev 2 |
|---|---|---|---|---|
| MemR3 (2025 preprint) | LLM router, query refinement, evidence-gap tracking | LoCoMo | Positive over RAG and Zep | Iterative memory retrieval, but inference-driven |
| RF-Mem (2026 preprint) | Retrieve, cluster, alpha-mix query and centroids, iterate | Three personalized-memory benchmarks | Positive over one-shot and full-context baselines | **Closest mechanical prior art**; embedding-space query anchoring and iterative expansion |
| EviMem (2026 preprint) | Evidence-gap diagnosis and targeted query refinement | LoCoMo | Positive on temporal and multi-hop questions | Closed-loop conversational-memory retrieval, but inference-driven |
| MGRetrieval (2026 preprint) | Memory-guided retrieval path, LLM filtering and stopping | LoCoMo | Positive over strongest baseline | Iterative dialogue-memory retrieval, but inference-driven |

Primary sources:

- Du et al., 2025 preprint, [MemR3](https://arxiv.org/abs/2512.20237)
- Zhang et al., 2026 preprint, [RF-Mem](https://arxiv.org/abs/2603.09250)
- Li et al., 2026 preprint, [EviMem](https://arxiv.org/abs/2604.27695)
- Wang and Dong, 2026 preprint, [MGRetrieval](https://arxiv.org/abs/2605.27437)

RF-Mem removes any defensible claim that iterative query/retrieved-memory
mixing is new in the conversational-memory setting. Rev 2 already forbids an
algorithmic novelty claim, but its remaining contribution must be narrower than
the setting: this committed corpus, a deterministic zero-model-call variant,
and explicit absorbing-state discipline. This is a positioning result, not an
unregistered stop condition.

## 6. S1 Decision

**The registered kill does not fire.** No published negative for chained
retrieval on conversational or episodic memory was located. Positive preprints
now occupy both the broad setting and, in RF-Mem, a close mechanical design.

S2 is authorized to begin after this artifact and the ledger update are
committed. The accepted residual is literature-search incompleteness: absence
of a located negative is not evidence that none exists.
