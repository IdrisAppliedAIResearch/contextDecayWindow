# Competitive landscape — PAPER-002 §2

**Purpose.** The positioning source for `paper/PAPER_002.md` §2 and §2.1. Every
external system named in the paper, with its citation, its verification status, its
published numbers, and the axes on which a comparison is defensible.

**The rule this file exists to enforce.** **No system in this file was ever run in
this repository.** Every number attributed to one is quoted from its publication and
carries the label `published, not run here`. `DO_NOT_WRITE.md` item 35 forbids any
comparison to HippoRAG, Mem0, Zep or Letta presented as measured. This file is built
so that the forbidden sentence has nowhere to form: the published scores and this
repository's numbers are never in the same table, and the table they share carries no
score at all.

**Why the separation is structural, not cautious.** Mem0, Zep, A-MEM and their
neighbours report **LLM-judged question-answering accuracy**. This repository reports
**deterministic evidence availability at a fixed character budget** — whether the text
carrying an answer was present in the delivered context, established with zero
generative calls during measurement. Putting a 66.88% J-score beside a 935/1,098
availability count would be a surrogate that can pass without the property it claims
to certify, which is the failure class `AGENTS.md` §3 names as this programme's
recurring one. LV-001 found the two properties pointing in opposite directions on this
repository's own corpus: the shipping configuration preserved 16/16 targeted items
offline while its live targeted score fell 3.5/8 → 1.5/8. That −2.0 gap sits inside
the measured 3.0-point instrument band and is therefore **NOT DEMONSTRATED** as a
magnitude (`EVIDENCE_SPINE.md` §4). What is not band-limited is the disposition: B2
was registered as a kill at a 0.5 tolerance, it fired, and the promotion did not
happen. The substitution is not hypothetical here. It has already been caught once.

---

## 1. Citations and verification status

**Method.** Each identifier was resolved against the arXiv API (`export.arxiv.org`) on
2026-08-18, and the returned title, author list, submission date and comment field
compared against the entry. Eleven were then re-resolved against a second index —
OpenAlex by DOI or title, ACL Anthology for LoCoMo. `verified` means both a title and
an author list came back matching. Venue is recorded with the source that states it,
because for four entries the two indexes disagree about whether the work is a preprint
or a proceedings paper.

| # | Key | Work | Authors | Year | Venue, and who states it | Identifier | Second source | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | **Mem0 / Mem0ᵍ** | Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory | Chhikara, Khant, Aryan, Singh, Yadav | 2025 | preprint; no venue in either record | arXiv:2504.19413v1, submitted 2025-04-28 | OpenAlex `10.48550/arXiv.2504.19413`, type preprint, 5 authors matching | **verified** |
| 2 | **Zep** | Zep: A Temporal Knowledge Graph Architecture for Agent Memory | Rasmussen, Paliychuk, Beauvais, Ryan, Chalef | 2025 | preprint; arXiv comment "12 pages, 3 tables" | arXiv:2501.13956v1, submitted 2025-01-20 | OpenAlex `10.48550/arXiv.2501.13956`, type preprint, 5 authors matching | **verified** |
| 3 | **Graphiti** | — | — | — | — | — | — | **no standalone publication located.** Named in the Zep abstract as Zep's "temporally-aware knowledge graph engine" and described inside entry 2. Cite entry 2 |
| 4 | **MemGPT** | MemGPT: Towards LLMs as Operating Systems | Packer, Wooders, Lin, Fang, Patil, Stoica, Gonzalez | 2023 (v2 2024) | preprint in both indexes | arXiv:2310.08560v2, submitted 2023-10-12, revised 2024-02-12 | OpenAlex `10.48550/arXiv.2310.08560`, type preprint, 7 authors matching | **verified** |
| 5 | **Letta** | Sleep-time Compute: Beyond Inference Scaling at Test-time | Lin, Snell, Wang, Packer, Wooders, Stoica, Gonzalez | 2025 | preprint in both indexes | arXiv:2504.13171v1, submitted 2025-04-17 | OpenAlex `10.48550/arXiv.2504.13171`, type preprint, 7 authors matching | **verified.** No standalone system paper for the Letta product was located. MemGPT (entry 4) is the system paper; this is the nearest Letta-authored follow-up, and it is about idle-time precomputation rather than about the memory layer's interface |
| 6 | **A-MEM** | A-MEM: Agentic Memory for LLM Agents | Xu, Liang, Mei, Gao, Tan, Zhang | 2025 | **NeurIPS 2025**, stated by both — arXiv comment, and OpenAlex as a conference paper in *Advances in Neural Information Processing Systems 38* | arXiv:2502.12110v11, submitted 2025-02-17, revised 2025-10-08 | OpenAlex DOI `10.52202/085713-0593` | **verified, venue confirmed twice** |
| 7 | **LangMem** | — | LangChain | 2025 | — | — | — | **unresolvable.** A web search for a LangMem publication returned an SDK launch post and documentation, and no paper; no arXiv record was located. Crossref was not queried. Its only citable number is as a **baseline inside entry 1** |
| 8 | **HippoRAG** | HippoRAG: Neurobiologically Inspired Long-Term Memory for Large Language Models | Jiménez Gutiérrez, Shu, Gu, Yasunaga, Su | 2024 | **NeurIPS 2024**, stated by both — arXiv comment, and OpenAlex as a conference paper in *Advances in Neural Information Processing Systems 37* | arXiv:2405.14831v3, submitted 2024-05-23 | OpenAlex DOI `10.52202/079017-1902`; proceedings link already carried in `LITERATURE_LANDSCAPE.md` §2 | **verified, venue confirmed twice** |
| 9 | **HippoRAG 2** | From RAG to Memory: Non-Parametric Continual Learning for Large Language Models | Jiménez Gutiérrez, Shu, Qi, Zhou, Su | 2025 | **ICML 2025** per the arXiv comment. **OpenAlex holds only the preprint record** | arXiv:2502.14802v2, submitted 2025-02-20 | OpenAlex `10.48550/arXiv.2502.14802`, type preprint | **verified; venue on one source only** |
| 10 | **LongMemEval** | LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory | Wu, Wang, Yu, Zhang, Chang, Yu | 2024 (v2 2025) | **ICLR 2025** per the arXiv comment. **OpenAlex holds only the preprint record** | arXiv:2410.10813v2, submitted 2024-10-14 | OpenAlex `10.48550/arXiv.2410.10813`, type preprint | **verified; venue on one source only** |
| 11 | **LoCoMo** | Evaluating Very Long-Term Conversational Memory of LLM Agents | Maharana, Lee, Tulyakov, Bansal, Barbieri, Fang | 2024 | **ACL 2024**, Volume 1 Long Papers, pages **13851–13870**, DOI `10.18653/v1/2024.acl-long.747` | arXiv:2402.17753v1, submitted 2024-02-27 | ACL Anthology page and OpenAlex, both giving the same pages and venue | **verified, venue confirmed twice — and see §1.2** |
| 12 | **MemR³** | MemR³: Memory Retrieval via Reflective Reasoning for LLM Agents | Du, Li, Zhang, Song | 2025 | preprint; arXiv comment "16 pages, 6 figures" | arXiv:2512.20237v1, submitted 2025-12-23 | not re-resolved | **verified on arXiv only** |
| 13 | **RF-Mem** | Evoking User Memory: Personalizing LLM via Recollection-Familiarity Adaptive Retrieval | Zhang, Li, Zhang, Jia, Li, Wang, Xu, Wen, Guo, Liu, Zhao | 2026 | **ICLR 2026** per the arXiv comment. **OpenAlex holds only the preprint record** | arXiv:2603.09250v1, submitted 2026-03-10 | OpenAlex `10.48550/arXiv.2603.09250`, type preprint | **verified — with a correction, see §1.1** |
| 14 | **EviMem** | EviMem: Evidence-Gap-Driven Iterative Retrieval for Long-Term Conversational Memory | Li, He, Zhang, Gong | 2026 | preprint | arXiv:2604.27695v1, submitted 2026-04-30 | not re-resolved | **verified on arXiv only** |
| 15 | **MGRetrieval** | MGRetrieval: Memory-Guided Reflective Retrieval for Long-Term Dialogue Agents | Wang, Dong | 2026 | preprint | arXiv:2605.27437v1, submitted 2026-05-22 | not re-resolved | **verified on arXiv only** |

**Count: 15 entries. 13 verified — 10 of those against two independent indexes, 3
against arXiv alone. 2 carry no standalone publication:** Graphiti (entry 3, described
inside the Zep paper) and LangMem (entry 7, `unresolvable`). Neither is dropped and
neither is invented.

**Scope of this table.** PAPER-002 §2 also names GraphRAG, SGMem and CodaRAG under
*structure over retrieved units*. Those are cited there for a mechanism this programme
built and stopped (§10), not as memory-layer competitors, and they were outside this
file's brief. They carry no verification status here, and a reader of §2 should not
read this file as covering them.

### 1.1 Two corrections to `E006_PART2_S1_PRIOR_ART_SCAN.md`

The prior-art scan of 2026-08-10 recorded four LoCoMo-adjacent works. All four
identifiers resolve. Two entries need correcting when they are carried into the paper:

- **"RF-Mem" is the system's name, not the paper's title.** arXiv:2603.09250 is titled
  *Evoking User Memory: Personalizing LLM via Recollection-Familiarity Adaptive
  Retrieval*; RF-Mem is the mechanism named inside it. A bibliography entry keyed to
  the shorthand will not resolve.
- **RF-Mem is no longer only a preprint.** The arXiv record states **ICLR 2026**; the
  scan labelled it "2026 preprint". OpenAlex still indexes the preprint. Since the scan
  called it the *closest mechanical prior art* to E006 Part 2, a published venue
  strengthens the scan's positioning conclusion rather than weakening it.

MemR³, EviMem and MGRetrieval remain preprints, as the scan recorded.

### 1.2 LoCoMo's two abstracts do not agree, and the paper cites the corpus by name

The preprint and the camera-ready describe conversations of different sizes.

| Source | Statistics, quoted |
|---|---|
| arXiv:2402.17753v1 abstract | "each encompassing **300 turns and 9K tokens** on avg., over up to **35 sessions**" |
| ACL 2024 abstract, `2024.acl-long.747` | "**600 turns and 16K tokens** on avg., over up to **32 sessions**" |

Both were fetched and quoted; this is not a transcription slip. It matters here for two
reasons. Downstream memory papers quote the preprint figure — A-MEM's evaluation
section describes LoCoMo as "9K tokens, up to 35 sessions" — so a citation chain can
carry the smaller number without touching the published version. And this repository
ran on LoCoMo conversations itself (NF-004, six sealed conversations, 1,098 QA
records), which makes the corpus name shared between this paper and its neighbours.
**A shared corpus name is the single most likely place for a reader to infer a
head-to-head that does not exist.** See §3.2.

---

## 2. Published numbers — every row `published, not run here`

**Read this table only as a record of what other groups report.** None of it was
reproduced here, none of it was compared against anything measured here, and the
per-system caveats below the table are part of the citation.

| System | Benchmark | Reported number | Source |
|---|---|---|---|
| Mem0 | LoCoMo, LLM-as-a-Judge (J) | **66.88%** | arXiv:2504.19413v1 Table 2 |
| Mem0ᵍ (graph) | LoCoMo, J | **68.44%** | ibid. |
| Full-context | LoCoMo, J | **72.90%** | ibid. |
| Zep | LoCoMo, J | **65.99%** | ibid. — **run by the Mem0 authors, not by Zep's** |
| LangMem | LoCoMo, J | **58.10%** | ibid. — same caveat |
| A-MEM | LoCoMo, J | **48.38%** | ibid. — same caveat; the paper marks a re-run variant `A-Mem*` |
| OpenAI memory | LoCoMo, J | **52.90%** | ibid. |
| RAG (best variant) | LoCoMo, J | **60.53%** | ibid. |
| Mem0 | p95 total latency | **1.44 s** (search p95 0.200 s) | ibid. Table 3 |
| Mem0ᵍ | p95 total latency | **2.59 s** (search p95 0.657 s) | ibid. |
| Full-context | p95 total latency | **17.12 s** | ibid. |
| Mem0 vs full-context | latency, tokens | **91% lower p95 latency**, **>90% token saving** | arXiv:2504.19413v1 abstract |
| Mem0 vs OpenAI memory | J | **26% relative improvement** | ibid. |
| Zep | DMR accuracy | **94.8%** vs MemGPT's **93.4%** | arXiv:2501.13956v1 abstract |
| Zep | LongMemEval | **63.8%** at gpt-4o-mini, **71.2%** at gpt-4o; up to **18.5%** accuracy gain, **90%** latency reduction | ibid. |
| HippoRAG | multi-hop QA | up to **20%** over prior state of the art; **10–30× cheaper** and **6–13× faster** than IRCoT at single-step retrieval | arXiv:2405.14831v3 abstract |
| HippoRAG 2 | associative memory | **+7%** over the state-of-the-art embedding model | arXiv:2502.14802v2 abstract |
| LongMemEval | benchmark scale | **500 questions**, five memory abilities; commercial assistants and long-context LLMs show a **30% accuracy drop** | arXiv:2410.10813v2 abstract |
| LoCoMo | benchmark scale, preprint | **300 turns**, **9K tokens**, up to **35 sessions** per conversation | arXiv:2402.17753v1 abstract |
| LoCoMo | benchmark scale, published | **600 turns**, **16K tokens**, up to **32 sessions** per conversation | ACL 2024, `2024.acl-long.747` abstract — **cite this one**, see §1.2 |
| A-MEM | DialSim F1 | **3.45**, reported as **+35%** over LoCoMo's method and **+192%** over MemGPT | arXiv:2502.12110v11 |

**Three caveats that travel with this table.**

1. **The competitor rows in the Mem0 table are the Mem0 authors' runs.** Zep, LangMem
   and A-MEM scores at 65.99%, 58.10% and 48.38% are third-party reproductions
   published by a system whose own entry is in the same table. The paper must say so
   whenever it quotes them. Zep's own paper reports on DMR and LongMemEval, not on
   LoCoMo, so no author-reported Zep LoCoMo number is available to place beside it.
2. **The judge is a model.** Mem0's evaluation used GPT-4o-mini as the answering
   engine and as the judge. A J-score is a model's opinion of an answer, scored at
   one temperature by one model version.
3. **MemGPT's own abstract makes no numeric claim.** The 93.4% DMR figure is Zep's
   measurement of MemGPT, not MemGPT's of itself.

---

## 3. The commensurable axes

**No accuracy number appears in this table, by construction.** These are properties
countable from each system's own description, plus a last column naming what each one
measures — which is where the incommensurability is recorded rather than hidden.

| System | Generative calls at write | Generative calls at read | Delivered text | Replay determinism | What it measures |
|---|---|---|---|---|---|
| **This component** | **0** (one embedding per `append()`) | **0** (one embedding per `context()` query) | Stored episodes verbatim | `context()` verified byte-identical across two processes; 132 selection payloads and 3 rendered blocks reproduce by SHA-256 | Evidence availability at a fixed character budget |
| Mem0 | Extraction call per message pair, plus an update call per extracted fact (ADD / UPDATE / DELETE / NOOP), GPT-4o-mini | Vector search; search p95 0.200 s | Model-extracted memories | Bounded by generation determinism | LLM-judged QA accuracy |
| Mem0ᵍ | As above, plus graph construction | Vector plus graph search; search p95 0.657 s | Model-extracted memories and relations | Bounded by generation determinism | LLM-judged QA accuracy |
| Zep / Graphiti | Per episode: entity extraction, entity resolution, fact extraction, temporal extraction, edge invalidation — gpt-4o-mini-2024-07-18 | Embedding plus full-text plus graph search | Model-extracted entities, edges and facts | Bounded by generation determinism | QA accuracy on DMR and LongMemEval |
| MemGPT / Letta | Agent-issued function calls; the count is decided by the model, not fixed per turn | Agent-issued paging calls | Model-written memory blocks | Bounded by generation determinism | Task accuracy on document analysis and multi-session chat |
| A-MEM | Per memory: note construction with keywords, tags and a contextual description, plus link generation and memory evolution | Retrieval over generated notes | Model-written notes | Bounded by generation determinism | LLM-judged QA accuracy |
| HippoRAG / HippoRAG 2 | OpenIE triple extraction per passage at index time | Personalized PageRank over the extracted graph | Retrieved passages, indexed through extracted triples | Bounded by extraction determinism | Multi-hop QA accuracy |
| LangMem | LLM extraction and consolidation per conversation (SDK documentation) | Retrieval over extracted memories | Model-extracted memories | Not stated in a publication | No self-published benchmark located |

**The sharp axis is column two.** Every system listed spends at least one generative
call on the layer this component runs with none, and for Mem0 the count is `1 + n` per
message pair, where `n` is the number of facts the extractor returned. That difference
is countable from published descriptions without running anything.

### 3.1 This component's cost and envelope, for the same axes

Deterministic, from `EVIDENCE_SPINE.md` §3 D11 and D12. Measured on one machine:
llama.cpp with a 27B generation model at UD-Q6_K_XL, Qwen3-Embedding-0.6B over SQLite
with `sqlite-vec`, one slot, fixed seed.

- **Selection latency: 190 ms at 1,000 candidates**, exponent **1.25** over 50–1,000,
  with clustering taking **81%** of it and rising from 37%. Timings exclude embedding.
  Comfortable to a few thousand episodes; unusable in an interactive loop somewhere
  before 10,000.
- **Storage: 4,743 bytes per turn at the margin**, 86% of it embeddings — about
  **48 MB at 10,000 turns**.
- **Budget enforcement:** replaying 1,000 committed episodes at a 32,000-character
  budget, **0 of 1,000 turns breach**. It also **truncates on 895 of those turns**,
  dropping up to 70 episodes and wanting up to 65,864 characters. Both readings
  belong together.

**One correction that must not be dropped when this is quoted.** "No inference calls
anywhere in the memory path" is a withdrawn sentence (`DO_NOT_WRITE.md` item 1). The
claim is **no generative model calls**. An embedding model is resident: `append()`
embeds every episode and `context()` embeds every query. Determinism holds **given a
pinned embedder**, and there is positive evidence of fragility there — the same
embedder given the same text under a different call shape returns a vector agreeing to
cosine 0.999837 that flips 6 of 146 committed payloads.

### 3.2 The same two corpus names appear on both sides, and mean different runs

This is the highest-risk confusion in the whole positioning section, because nothing
in a corpus name signals which endpoint was scored.

| Corpus | What the cited systems run on it | What this repository ran on it |
|---|---|---|
| **LoCoMo** | The benchmark's QA task, answered by a model and scored by a model. Mem0's evaluation used GPT-4o-mini as answerer and as judge | **NF-004**: six sealed conversations, 1,098 fully resolvable canonical QA records, 16,000-character budget, **0 model calls and 0 embedding calls during measurement**. The endpoint is whether the evidence text was present, not whether an answer was right |
| **LongMemEval** | The benchmark's five memory abilities, scored for answer accuracy. Zep reports 63.8% at gpt-4o-mini and 71.2% at gpt-4o | **EC-001** on LongMemEval-S with a **Codex-substituted** evaluator, because the pinned GPT-4o evaluator was unavailable. Amendment 010 forbids placing its 20.0% and 12.22% figures against any published LongMemEval result. **NF-005** and **DMR-001C** used the corpus deterministically, with no scoring model at all |

Two consequences follow, and both are binding. A sentence of the form "on LoCoMo, X
reports 66.88% and this component reaches 935/1,098" is forbidden even though both
halves are true, because the denominators count different events. And the one place
this repository holds a LongMemEval number that looks like a benchmark score is exactly
the place where the evaluator was substituted.

---

## 4. Prose the paper can adapt

Mem0, Zep, A-MEM and LangMem all place a language model inside the write path. Mem0's
ingestion runs an extraction call on each message pair and then an update call per
extracted fact, choosing among ADD, UPDATE, DELETE and NOOP; Graphiti, the engine
under Zep, runs entity extraction, entity resolution, fact extraction, temporal
extraction and edge invalidation on each episode; A-MEM writes a note with keywords,
tags and a contextual description for every memory and then evolves the links between
them. HippoRAG and HippoRAG 2 move the call to index time, extracting OpenIE triples
per passage before any query arrives. The component studied here runs that layer with
zero generative calls. It embeds, ranks, selects and packs, and it delivers the stored
text unchanged.

That difference is countable from published descriptions. What follows from it is not
a performance claim. The published systems report LLM-judged question-answering
accuracy — Mem0 at 66.88% on LoCoMo against a full-context ceiling of 72.90%, Zep at
63.8% on LongMemEval with gpt-4o-mini — and this paper reports whether the text
carrying an answer was present in a 16,000-character context window, counted without a
model in the loop. Those are different measures of different objects. The programme's
own operating manual names its recurring failure as a surrogate that can pass without
the property it certifies, and this repository has already caught one: LV-001's
shipping configuration preserved 16 of 16 targeted items offline, then fired the kill
bar registered for its live targeted probes at a 0.5 tolerance and was not promoted.
The size of that live loss is inside the instrument's 3.0-point band and is not
demonstrated. What the run did settle is the distinction: preserving an item's
availability and preserving the answer that depends on it are not the same property,
and this programme had measured only the first. A single column holding both a J-score
and an availability count would be that substitution with a ruler drawn on it. The
corpus names make this easy to get wrong: NF-004 ran on six sealed LoCoMo
conversations, so the word LoCoMo appears on both sides of the comparison and marks
two different runs on either side of it.

What can be said instead is architectural. The component's `context()` is a pure
function of store state, query and budget, verified byte-identical across two
processes, with 132 committed selection payloads and 3 rendered blocks reproducing
their SHA-256. A pipeline whose memories are written by a generation call inherits that
call's determinism, and none of the papers cited here claims byte-level replay. The
delivered text is the stored episode rather than a paraphrase of it, so the failure
mode is an episode that was not delivered, never an episode delivered as a wrong
sentence. Cost is reported on both sides and the two figures do not subtract: Mem0's
p95 total latency of 1.44 s is end to end and includes generation, while this
component's 190 ms at 1,000 candidates is selection on one machine with embedding
excluded, of which clustering is 81%. Storage here is 4,743 bytes per turn at the
margin, 86% of it embeddings.

The framing the programme committed to before it had any external result still holds.
Nobody has built a memory layer whose formation, ranking, routing and stopping are all
deterministic, and the industry comparison spends a language-model call on exactly that
layer. So the question is rarely whether the deterministic version wins. It is how much
of the layer survives without the call. A mechanism that recovers most of it and still
loses a head-to-head is a finding, and reporting it as a failure throws the finding
away. This paper is not in a position to report that head-to-head either way, and it
does not pretend otherwise.

One boundary is load-bearing. The LongMemEval authors' LLM-assisted indexing and
time-aware query expansion were available to this programme and were deliberately not
adopted, because they add generative calls to the memory path and would change the
component under test. Some of the distance between this component's external numbers
and published ones is that choice, and this paper does not get to claim the choice was
free.

---

## 5. Claims this document does not license

Written as prohibitions so they can be grepped for.

| Forbidden | Why |
|---|---|
| Any statement that this component **beats, matches, approaches or trails** Mem0, Mem0ᵍ, Zep, Graphiti, MemGPT, Letta, A-MEM, LangMem, HippoRAG or HippoRAG 2 | **None was run here.** `DO_NOT_WRITE.md` item 35. No shared instrument exists on which the words *beats* or *trails* have a referent |
| Any table, figure or sentence placing a published J-score or accuracy beside an availability count from this repository | Different measures of different objects. `AGENTS.md` §3's surrogate class, demonstrated live by LV-001 |
| "Zep scores 65.99% on LoCoMo" without attribution to the Mem0 authors' run | It is a third-party reproduction published by a competing system, and Zep's own paper reports DMR and LongMemEval instead |
| "MemGPT scores 93.4% on DMR" as MemGPT's claim | MemGPT's abstract makes no numeric claim. 93.4% is Zep's measurement of MemGPT |
| "This component is cheaper / faster than Mem0" | The 190 ms figure is selection on one machine excluding embedding; Mem0's 1.44 s is end-to-end p95 including generation. Not the same quantity |
| "No inference calls in the memory path" | Withdrawn. `DO_NOT_WRITE.md` item 1. Write **no generative model calls**, and state that an embedding model is resident |
| "Deterministic memory is a new idea" / any novelty claim for the mechanism | `DO_NOT_WRITE.md` §4: the paper never calls its own contribution novel. RF-Mem (ICLR 2026) already occupies iterative query/retrieved-memory mixing in the conversational-memory setting, per `E006_PART2_S1_PRIOR_ART_SCAN.md` §5 |
| "Entity-centric indexing fails" as a general claim | The supported statement is narrow: six target facts sit in spans where **this programme's registered spaCy extractor returned zero entities**. That is not evidence about HippoRAG's LLM-based graph builder. `LITERATURE_LANDSCAPE.md` §2 |
| "This component generalizes to long-conversation memory" on the strength of LongMemEval | `LITERATURE_LANDSCAPE.md` §3: LoCoMo was unrun at that decision, and EC-001's evaluator was **Codex-substituted**. The 20.0% and 12.22% figures may not be placed against any published LongMemEval result (Amendment 010) |
| Any sentence pairing a published LoCoMo or LongMemEval score with an NF-004, NF-005, EC-001 or DMR-001C number, however hedged | The corpus name is shared and the endpoint is not. §3.2. This is the specific sentence a reader will construct if the paper leaves the two adjacent |
| "LoCoMo conversations average 300 turns and 9K tokens" | That is the **preprint** abstract. The ACL 2024 version says **600 turns and 16K tokens over up to 32 sessions**. §1.2 |
| Citing "LangMem" to a paper | **Unresolvable.** No publication record was located. Cite the SDK, or cite it as a baseline inside Mem0's Table 2 |
| Citing "Graphiti" to a paper | No standalone publication located. Cite the Zep paper, which names and describes it |
| Citing arXiv:2603.09250 as "RF-Mem, 2026 preprint" | The title is *Evoking User Memory: Personalizing LLM via Recollection-Familiarity Adaptive Retrieval* and the record states **ICLR 2026** |
| Treating the absence of a published deterministic-memory competitor as evidence of priority | `E006_PART2_S1_PRIOR_ART_SCAN.md` §6: absence of a located negative is not evidence that none exists. The same applies to absence of a located system |

---

## 6. Provenance

Compiled 2026-08-18 on branch `paper-rework`. Identifiers resolved against the arXiv
API on that date, and eleven of them re-resolved against OpenAlex or the ACL Anthology.
Venue statements are attributed in the table to the index that states them. Published
numbers quoted from each work's abstract or its results tables. This repository's
numbers quoted from `paper/notes/EVIDENCE_SPINE.md`, which is the only admissible
source for them.

**What was not verified, recorded rather than papered over.**

- **Semantic Scholar returned nothing usable.** Its batch endpoint rejected the GET
  form used (HTTP 404, POST-only), and the single-paper endpoint returned HTTP 429.
  No entry carries a Semantic Scholar confirmation. Crossref was not queried.
- **Three entries rest on arXiv alone** — MemR³, EviMem, MGRetrieval. Their titles,
  authors and dates matched the record; no second index was consulted.
- **Four venue statements rest on an arXiv comment field alone** — HippoRAG 2 (ICML
  2025), LongMemEval (ICLR 2025), RF-Mem (ICLR 2026), and A-MEM's comment before
  OpenAlex confirmed it. An author-supplied comment is a claim about acceptance, not a
  proceedings record. OpenAlex indexes the first three as preprints.
- **Mem0's PDF did not parse.** Its Table 2 and Table 3 values were read from the arXiv
  HTML rendering of v1, not from the PDF.
- **OpenAlex's abstract text for the LongMemEval record did not match the paper** — it
  described an unrelated system — so nothing from that field was used. The title,
  authors, type and DOI from the same record did match and were used.
- **No LoCoMo or LongMemEval leaderboard was consulted**, so the published scores in
  §2 are each system's self-report or Mem0's reproduction, with no third-party
  arbitration behind either.
