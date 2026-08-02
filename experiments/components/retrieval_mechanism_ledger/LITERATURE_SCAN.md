# Retrieval Mechanism Literature Scan

**Scan date:** July 30, 2026
**Scope:** Sources owed by `RETRIEVAL_MECHANISM_LEDGER.md`
**Source policy:** Primary papers, proceedings, and official code/model pages
**Decision companion:** `LITERATURE_LANDSCAPE.md`

This file owns candidate-mechanism prior art. `LITERATURE_LANDSCAPE.md` owns
program positioning, external benchmark adoption, and the HippoRAG
disposition. The two files are reconciled in the landscape's Section 7.

## Diversity-Aware And Coverage Selection

Maximal Marginal Relevance explicitly trades query relevance against novelty
relative to already selected documents. Submodular summarization generalizes
coverage and redundancy control, including facility-location objectives with
greedy approximation guarantees.

- Carbonell and Goldstein, 1998:
  [MMR paper](https://doi.org/10.1145/290941.291025) and
  [workshop version](https://aclanthology.org/X98-1025/).
- Lin and Bilmes, 2011:
  [Submodular summarization](https://aclanthology.org/P11-1052/).

**Verified against primary text, August 1, 2026.** Lin and Bilmes (2011)
Section 3, Theorem 2 proves `F_MMR` is **non-monotone submodular**, and notes
MMR's diminishing-returns property was "apparently unnoticed until now." MMR
carries no constant-factor greedy guarantee because its objective is **not
monotone** - not, as commonly repeated, because it is not submodular. Do not
describe MMR as non-submodular anywhere in this repository.

**Disposition:** This is a real alternative to E002, not evidence that
fixed-width mechanical segments align with information needs. E002 was killed
by its locked offline test before promotion, so no diversity selector was
imported or retrospectively substituted. The family was subsequently tested on
its own registered anchor as **E005**, which returned PROMOTION_ELIGIBLE
offline at 12/17 across 4/4 domains. See `E005_diversity_selection_protocol.md`
and `E005_POSTHOC_INTERPRETATION.md`.

## Query Decomposition And Multi-Vector Retrieval

ColBERT avoids a single pooled vector through token-level late interaction.
POQD shows that multi-vector retrieval performance depends strongly on query
decomposition and improves decomposition with an LLM and downstream retrieval
feedback. Conversational-retrieval work likewise favors learned rewriting or
contextualized query representations rather than fixed-width segmentation.

- Khattab and Zaharia, 2020:
  [ColBERT](https://arxiv.org/abs/2004.12832).
- Liu et al., 2025:
  [POQD](https://proceedings.mlr.press/v267/liu25ag.html).
- Jang et al., 2024:
  [IterCQR](https://aclanthology.org/2024.naacl-long.449/).
- Lin et al., 2021:
  [Contextualized query embeddings](https://aclanthology.org/2021.emnlp-main.77/).
- Wu et al., 2022:
  [CONQRR](https://aclanthology.org/2022.emnlp-main.679/).
- Shrestha and Aryal, 2026:
  [Multi-turn reformulation and retrieval fusion](https://aclanthology.org/2026.semeval-1.320/).

**Disposition:** The literature supports the Family QR diagnosis but not E002's
mechanical surrogate. POQD, IterCQR, and CONQRR add inference or training and
therefore violate the standing memory-path constraint. ColBERT is direct prior
art for E003, whose storage and budget costs remain unmeasured.

## Active And Mid-Generation Retrieval

FLARE retrieves from predicted future sentences when confidence is low. IRCoT
interleaves retrieval and reasoning steps. Self-RAG learns retrieval and
critique control tokens.

- Jiang et al., 2023:
  [FLARE](https://aclanthology.org/2023.emnlp-main.495/).
- Trivedi et al., 2023:
  [IRCoT](https://aclanthology.org/2023.acl-long.557/).
- Asai et al., 2024:
  [Self-RAG](https://openreview.net/forum?id=hSyW5go0v8).

**Disposition:** These are relevant if the deployment target becomes an agent,
but each couples retrieval to generation or reasoning. None preserves the
current one-shot `store.context(query, budget)` contract, so the ledger's
contract-ground rejection stands.

## Attention And Retrieval Heads

Wu et al. detect sparse retrieval heads by copy-paste behavior on independent
needle tasks; the published detector calibrates model-specific heads rather
than supplying universal head IDs. Track 1 supplies eager-attention capture but
does not contain retrieval-head calibration for Qwen3.6.

- Wu et al., 2025:
  [Retrieval Head paper](https://arxiv.org/abs/2404.15574) and
  [official detector](https://github.com/nightdessert/Retrieval_Head).
- Track 1:
  [RecursiveSelfHealingAgent](https://github.com/IdrisAppliedAIResearch/RecursiveSelfHealingAgent).

**Disposition:** A retrieval-head-only E001 arm must calibrate Qwen3.6 heads on
an independent copy task. Track 1 is prior art, not available Track 2
infrastructure.

## Carried Landscape Reference

`LITERATURE_LANDSCAPE.md` is now committed. Its Section 7 reconciles the
HippoRAG disposition, LoCoMo/LongMemEval adoption, paper positioning, and every
candidate class scanned here. No reconciliation changes an E001/E002 outcome
or authorizes E003.
